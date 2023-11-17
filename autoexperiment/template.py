from omegaconf import OmegaConf
from itertools import product
from dataclasses import dataclass

@dataclass
class JobDef:
   config: str = ""
   name: str = ""
   job_id_regexp: str = "Job Id:([0-9]+)"
   output_file: str = "slurm.out"
   cmd: str = "sbatch run.sbatch"
   check_interval_secs: int = 60*15
   start_condition: str = ""
   termination_str: str = ""
   verbose: bool = True
   resume_job_id: int = None


def generate_job_defs(path, exp_name=None):
   cfg = OmegaConf.load(path)
   defs = cfg.defs
   jobs = []
   for name, exp in cfg.experiments.items():
      if exp_name and name != exp_name:
         continue
      vals_all = []
      kvs = list(exp.items())
      kvs = kvs + [("set", name)]

      for k, v in kvs:
         if type(v) == str:
            v = [v]
         else:
            pass
         vs = []
         for vi in v:
             vi = (k, vi)
             vs.append(vi)
         vals_all.append(vs)
    
      for vals in product(*vals_all):
         params = {}
         for k, v in cfg.common.items():
            params[k] = v
         

         for k, v in vals:
            if v in defs:
               params[k] = v
               for kd, vd in defs[v].items():
                 params[kd] = str(vd)
            else:
               params[k] = str(v)
         
         while True:
            old_params = params.copy()
            for k, v in params.items():
               try:
                  params[k] = params[k].format(**params)
               except Exception:
                  pass
            if old_params == params:
               break
  
         tpl = open(cfg.common.template).read()
         config = tpl.format(**params)
         name = params.get('name', _auto_name(params))
         jobdef = JobDef(config=config, name=name)
         for k, v in cfg.common.items():
            setattr(jobdef, k, str(v).format(**params) if type(v) == str else v)
         jobs.append(jobdef)
   return jobs

def _auto_name(params):
    name = ""
    for k, v in params.items():
        name += f"{k}={v}_"
    return name[:-1]