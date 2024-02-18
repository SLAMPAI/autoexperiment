from omegaconf import OmegaConf, DictConfig, ListConfig
from itertools import product
from dataclasses import dataclass, fields

@dataclass
class JobDef:
   # key/value pairs of the params used to generate the config file
   # from the template
   params: dict = None
   # resulting config file used for job
   # after applied to the template
   config: str = ""
   # name of the job
   name: str = ""
   # regexp to extract job id from the output file
   job_id_regexp: str = "Job Id:([0-9]+)"
   # output file path of the job
   output_file: str = "slurm.out"
   # command to run for the job
   cmd: str = "sbatch run.sbatch"
   # path to sbatch script
   sbatch_script: str = "run.sbatch"
   # secs to wait before checking if job is done/frozen/etc
   check_interval_secs: int = 60*15
   # command to check if job should be started or not (ignored if empty)
   start_condition_cmd: str = ""
   # string to check if job is done in the output file
   termination_str: str = ""
   # command to check to terminate the job (alternative to termination_str)
   termination_cmd: str = ""
   # if true, print more logging info
   verbose: bool = True
 
def product_recursive(cfg):
   """
   do cartesian product recursively

   product_recursive(x,y,z) = product( product_recursive(x), product_recursive(y), product_recursive(z))

   recursion happens when we have possibilities, this is only the case when we have list
   list is either a plain list, or list of dicts where dict has single key and a value, basically
   just like a list where we name items
   """
   vals_all = []
   for k, v in cfg.items():
      # variables vale can be either a list or a single value
      # if single value, convert to list of single element
      if type(v) in (str, int, float):
         vs = [(k, v)]
      # if dict, also single value but where the value is a tuple of kv items
      elif type(v) == DictConfig:
         vs = [(k, tuple(v.items()))]
      # only when it is list that we consider that there are multiple values
      elif type(v) == ListConfig:
         # two types of lists:
         # 1) list of dicts, where dict has single key, and a value, [{'x':...}, {'y':...}, {'z':...}], 
         #    basically, this is just like a list where we name items
         # 2) plain list [x,y,z]
         if all(type(vi) == DictConfig and len(vi)==1 for vi in v):
            # list of dicts
            vs = [(k, _key(vi), kvs) for vi in v for kvs in product_recursive(_value(vi))]
         else:
            # plain list
            vs = [(k, vi) for vi in v]
      else:
         print(type(v))
         raise ValueError(v)
      vals_all.append(vs)
   return product(*vals_all)

def _key(d):
   return list(d.keys())[0]

def _value(d):
   return list(d.values())[0]

def generate_job_defs(path):
   """
   Returns a list of JobDef from a config file (config.yaml)
   the JobDef list can directly be used by the manager to schedule/manage the jobs
   """
   cfg = OmegaConf.load(path)
   jobs = []
   for vals in product_recursive(cfg):
      # params will store the key-value pairs
      # of all the variables that can be used
      # in the template
      params = {}
      for *ks, v in vals:
         # each variable is a tuple of keys followed by the value
         # we can have multiple keys because we can have deep branches of possibitilies
         # so as many keys as we go deep
         # (k1, k2, ..., v)

         # we just set in params the value of the key as the value of the next key
         # i.e. k1 -> k2, k2 -> k3, etc
         for ki, kin in zip(ks[0:-1], ks[1:]):
            params[ki] = kin
         # last key goes to the actual value
         params[ks[-1]] = v
      # replace any reference by its value and
      # inject the dict-based variables directly into params
      # keep doing until no refenrece needs to be replaced
      # by its value
      while True:
         old_params = params.copy()
         for k, v in old_params.items():
            
            # replace the variable by its value
            # if in params 
            if type(v) == str and v in old_params:
               v = old_params[v]

            # expand the dicts directly in params
            if type(v) == tuple:
               for ki, vi in v:
                  params[ki] = vi
         if old_params == params:
            break
      
      # if value of a variable is a template format (e.g., '{dataset}_{lr}'), replace the keys
      # by the values.
      # keep doing until no key needs to be replaced
      while True:
         old_params = params.copy()
         for k, v in params.items():
            try:
               params[k] = old_params[k].format(**old_params)
            except Exception:
               pass
         if old_params == params:
            break
      # at this point, we can use the template file to generate the config file
      # by replacing all the keys from 'params' with their values in the template
      # file.
      tpl = open(params['template']).read()
      config = tpl.format(**params)
      # auto generate the name of the job from the full set of params
      # if 'name' is not present in 'params', otherwise just use the value of 'name'
      # from params.
      name = params.get('name', _auto_name(params))
      # Define the 'JobDef' structure, which is directly used by the manager
      # to schedule/manaage the jobs
      jobdef = JobDef(config=config, name=name, params=params)
      # These are directly used by the manager (e.g. check_interval_secs, name, etc)
      for field in fields(jobdef):
         if field.name in params:
            setattr(jobdef, field.name, params[field.name])
      jobs.append(jobdef)
   return jobs


def _auto_name(params):
    """
    Generate a name for the job from the dictionary of the params
    """
    name = ""
    keys = sorted(params.keys())
    for k in keys:
        v = params[k]
        name += f"{k}={v}_"
    return name[:-1]
