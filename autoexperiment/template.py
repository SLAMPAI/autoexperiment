from omegaconf import OmegaConf
from itertools import product
from dataclasses import dataclass

@dataclass
class JobDef:
   # key/value pairs of the params used to generate the config file
   # from the template
   params = None
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
   # secs to wait before checking if job is done/frozen/etc
   check_interval_secs: int = 60*15
   # command to check if job should be started or not (ignored if empty)
   start_condition: str = ""
   # string to check if job is done in the output file
   termination_str: str = ""
   # if true, print more logging info
   verbose: bool = True
 

def generate_job_defs(path, exp_name=None):
   cfg = OmegaConf.load(path)
   defs = cfg.defs
   jobs = []
   for name, exp in cfg.experiments.items():

      # select one of the experiment sets
      if exp_name and name != exp_name:
         continue
   
      
      vals_all = []
      kvs = list(exp.items())
      kvs = kvs + [("set", name)]
      # iterate over all the variables defined in the experiment
      for k, v in kvs:
         # can be either a list or a single value
         # if single value, convert to list of single element
         if type(v) in (str, int, float):
            v = [v]
         else:
            pass
         vs = []
         for vi in v:
             vi = (k, vi)
             vs.append(vi)
         vals_all.append(vs)
      # 'vals_all' contain a list
      # where each element is a tuple
      # and each tuple is a (key, value) pair
      # where key is the name of the variable
      # and value is a list of possible values for that variable
      # values can either be raw values (number, string) or one
      # of the keys defined in the 'defs' section

      # do the cartesian product of all the variables
      for vals in product(*vals_all):

         # params will contain the key-value pairs
         # of all the variables that can be used
         # in the template
         params = {}

         # include the common variables
         for k, v in cfg.common.items():
            params[k] = v

         # for each variable, if its value is a name defined in 'defs' section,
         # then include all the key/values defined in 'defs' section corresponding
         # to the name in 'defs' section.
         # also include in the params the variable name as key
         # and the name of the variable in 'defs' section as a value.
         # if value of the variable is not in 'defs' section, simply include the name of the variable
         # as key and the value as value
         for k, v in vals:
            if v in defs:
               params[k] = v
               for kd, vd in defs[v].items():
                 params[kd] = str(vd)
            else:
               params[k] = str(v)
         
         # the values in 'params' support dependency to other variables via
         # {NAME}. Thus, we iterate over all the variables and use the str format
         # to replace all the variables with their values. We do this until
         # no more {NAME} are found.
         while True:
            old_params = params.copy()
            for k, v in params.items():
               try:
                  params[k] = params[k].format(**params)
               except Exception:
                  pass
            if old_params == params:
               break
         # at this point, we can use the template to generate the config file
         # from the 'params' dictionary
         tpl = open(cfg.common.template).read()
         config = tpl.format(**params)
         # auto generate the name of the job from the full set of params
         # if  'name' is not present in 'params'
         name = params.get('name', _auto_name(params))

         # Define the JobDef structure, which is used by the manager
         # to schedule/manaage the jobs
         jobdef = JobDef(config=config, name=name)
         jobdef.params = params

         # include the common variables in the jobdef
         for k, v in cfg.common.items():
            setattr(jobdef, k, str(v).format(**params) if type(v) == str else v)
         jobs.append(jobdef)
   return jobs

def _auto_name(params):
    name = ""
    keys = sorted(params.keys())
    for k in keys:
        v = params[k]
        name += f"{k}={v}_"
    return name[:-1]
