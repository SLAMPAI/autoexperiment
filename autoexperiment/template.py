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
   Generate all possible combinations of parameters in a config file.

   Returns a list of dicts where:
   each dict is a group set of params (and their values) that occur together
   the keys are tuples constructed from the nested structure, the values are the corresponding values

   - a param is either a single key=value, a list of params, or a dict of params
   - dict of params result in cartesian product of the values of the params, e.g.:

      ```
      d:
         x:[1,2]
         y:[3,4]
      ```
      this is a dict with keys x and y, values [1,2] and [3,4].
      the dict will result in:
      [{(d,x):1,(d,y):3}, {(d,x):1,(d,y):4}, {(d,x):2,(d,y):3}, {(d,x):3, (d,y):4}]
   - list of params result in a union of the values, e.g.:

      ```
      - x: 
         val: [1,2]
         r: 5
      - y:
         val: [3,4]
         r: 6
      ```
      will result in:
      [{(x,val):1, (x,r): 5}, {(x,val):2, (x,r): 5}, {(y,val):3,(x,r): 6}, {(y,val):4,(x,r): 6}]
      i.e., x has two values, y has two values. we just concatenate all the values (2+2=4 values).


      notice, if we remove the dash (-) like the following:

      ```
      x: 
         val: [1,2]
         r: 5
      y:
         val: [3,4]
         r: 6
      ```
      we have a dict, so it is different semantics (that is, cartesian product), (2*2 = 4 values) it will result in:

      [{(x,val:1), (x,r):5}, {(x,val):2, (x,r):5}] X [{(y,val):3, (y,r):6}, {(y,val):4, (y,r):6}]  = [
         {(x,val:1), (x,r):5, (y,val):3, (y,r):6},
         {(x,val:1), (x,r):5, (y,val):4, (y,r):6},
         {(x,val:2), (x,r):5, (y,val):3, (y,r):6},
         {(x,val:2), (x,r):5, (y,val):4, (y,r):6},
      ]
   """
   if type(cfg) in (str, int, float):
      return [{tuple(): cfg}]
   elif type(cfg) == ListConfig:
      if all(type(vi) == DictConfig and len(vi) == 1 for vi in cfg):
         all_vals = []
         for kv in cfg:
            k = _first_key(kv)
            v = _first_val(kv)
            vals = [_add_key(k, vi) for vi in product_recursive(v)]
            all_vals.extend(vals)
         return all_vals
      elif all(type(vi) in (str, int, float) for vi in cfg):
         return  [{tuple(): vi} for vi in cfg]
      else:
         raise ValueError()
   elif type(cfg) == DictConfig:
      vals_all = []
      for k, v in cfg.items():
         vs = [ _add_key(k, vi) for vi in product_recursive(v)]
         vals_all.append(vs)
      vals_all = product(*vals_all)
      vals_all = [_merge(vi) for vi in vals_all]
      return vals_all
   else:
      raise ValueError(f"Unexpected type {type(cfg)}")

def _add_key(k, vi):
   return { (k,)+kii: vii for kii, vii in vi.items()}

def _first_key(kv):
   return list(kv.keys())[0]

def _first_val(kv):
   return list(kv.values())[0]

def _merge(ds):
   d = {}
   for di in ds:
      d.update(di)
   return d

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
      for ks, v in vals.items():
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
      # if value of a variable is a template format (e.g., '{dataset}_{lr}'), replace the keys
      # by the values.
      # keep doing until no key needs to be replaced
      while True:
         old_params = params.copy()
         for k, v in params.items():
            try:
               params[k] = old_params[k].format(**old_params)
            except Exception as ex:
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
