import re
import warnings
from omegaconf import DictConfig, ListConfig
from itertools import product
from dataclasses import dataclass, fields
from collections import defaultdict
import warnings


@dataclass
class JobDef:
   # key/value pairs of the params used to generate the config file
   # from the template
   params: dict = None
   # resulting config file used for job
   # after applied to the template
   config: str = ""
   # name of the job, have to be UNIQUE, used to identify a job, and have to be assigned to SLURM jobname in the SBATCH script.
   name: str = ""
   # output directory of the job: used by the manager together with `name`
   out_dir: str = ""
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
 
MANDATORY_FIELDS =[
   "name",
   "template",
   "out_dir",
   "cmd",
   "sbatch_script",
]
PREFIXES = [
  'autoexp',
  'slurm',
  'args',
]


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
      will result in:
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
      [
         {(x,val:1), (x,r):5, (y,val):3, (y,r):6},
         {(x,val:1), (x,r):5, (y,val):4, (y,r):6},
         {(x,val:2), (x,r):5, (y,val):3, (y,r):6},
         {(x,val:2), (x,r):5, (y,val):4, (y,r):6},
      ]
   """
   if type(cfg) in (str, int, float, bool):
      return [{tuple(): cfg}]
   elif type(cfg) == ListConfig:
      if all(type(vi) == DictConfig and len(vi) == 1 for vi in cfg):
         # list of dicts where each dict has a single key and a value:
         all_vals = []
         for kv in cfg:
            k = _first_key(kv)
            v = _first_val(kv)
            vals = [_add_key(k, vi) for vi in product_recursive(v)]
            all_vals.extend(vals)
         return all_vals
      elif all(type(vi) in (str, int, float, bool) for vi in cfg):
         # list of str/int/float values
         return  [{tuple(): vi} for vi in cfg]
      else:
         # list of something else?
         raise ValueError(f"list should either be of str/int/float values, or list of dicts with a single key/value, got:{cfg}")
   elif type(cfg) == DictConfig:
      vals_all = []
      for k, v in cfg.items():
         vs = [ _add_key(k, vi) for vi in product_recursive(v)]
         vals_all.append(vs)
      vals_all = product(*vals_all)
      vals_all = [_merge(vi) for vi in vals_all]
      return vals_all
   else:
      raise ValueError(f"Unexpected type {type(cfg)}, should be either str or int or float or ListConfig or DictConfig")

def _add_key(k, vi):
   """
   insert the key k to the list of keys of each dict element
   """
   return { (k,)+kii: vii for kii, vii in vi.items()}

def _first_key(kv):
   """
   get the first key of a dict
   """
   return list(kv.keys())[0]

def _first_val(kv):
   """
   get the first val of a dict
   """
   return list(kv.values())[0]

def _merge(ds):
   """
   Merge a list of dicts into one dict
   """
   d = {}
   for di in ds:
      d.update(di)
   return d

def params_to_args(params: dict) -> list[str]:
    """
    Turn a dictionary of args into argument-style strings.

    Rules:
      - bool True  -> just the flag
      - bool False -> skip
      - list/tuple -> flag followed by all values
      - scalar     -> flag + value
    """
    args = []
    for key, value in params.items():
        # Skip intermediate vars
        if key.startswith("_"):
            continue
        # Weirdly some Megatron args have both hypens and underscores.
        # Treat those separately, hyphenate all the others.
        if key == 'override_opt_param_scheduler':
           flag = f"--override-opt_param-scheduler"
        elif key == 'use_checkpoint_opt_param_scheduler':
           flag = f"--use-checkpoint-opt_param-scheduler"
        else:
           flag = f"--{key.replace('_','-')}"
        if isinstance(value, bool):
            if value:
                args.append(flag)
        elif isinstance(value, (list, tuple, ListConfig)):
            args.append(flag)
            args.extend(map(str, value))
        else:
            args.extend([flag, str(value)])
    return args


def substitute(s, params):
   """
      Replace placeholders like {args.lr} in string `s` using values from `params`.
      Works with flat keys (e.g. 'args.lr').

      Example:
         s = "{model_size}_{slurm.nnodes}_{args.lr}"
         params = {"model_size": '10M', "slurm.nnodes": 2, "args.lr": 1
         -> 10M_2_1
    """
   for k, v in params.items():
      s = re.sub(rf"{{\s*{re.escape(k)}\s*}}", str(v), s)
   return s


def resolve_templates_expr(params, verbose=0):
   """
   If value of a variable is a template format (e.g., '{dataset}_{lr}') or an expression e.g. 'expr({lr} * 0.001))', 
   replace the values by the evaluated expression.
   keep doing until no value needs to be evaluated.

   Args:
      params (dict): Dictionary of key–value pairs possibly containing template strings.
      verbose (int, optional): Controls warning verbosity.
   Returns:
      dict: The updated `params` dictionary.
   """
   params = params.copy()
   while True:
      old_params = params.copy()
      evaled_params = {k: v for k, v in old_params.items() if not _is_expr(v)}
      for k in params.keys():
         # if the value is not a string, we skip it
         # as we only evaluate strings
         if type(old_params[k]) != str:
            continue
         
         try:
            params[k] = substitute(old_params[k], evaled_params)
         except Exception as ex:
            # exception happens when some variables needed in the template do not exist (yet) in `evaled_params`, or expression is invalid.
            # Here, we skip the exceptions, as some variables can be later evaled in next iterations,
            # but we make sure to throw a warning
            if verbose > 0:
               msg = (f"Cannot set value for {old_params[k]}' (Exception: {ex})")
               if verbose == 2:
                  msg += f" with params {evaled_params}"
               warnings.warn(msg)
         
         # get the (possible) new value of the variable
         v = params[k]
         ## evaluate expressions
         try:
            if _is_expr(v):
               params[k] = _eval_expr(v)
         except Exception as ex:
            # exception happens when some variables needed in the template do not exist (yet) in `evaled_params`, or expression is invalid.
            # Here, we skip the exceptions, as some variables can be later evaled in next iterations,
            # but we make sure to throw a warning.
            if verbose > 0:
               warnings.warn(f"Cannot set value for '{k}' with expression '{v}' (Exception: {ex})")
      if old_params == params:
         break
   
   return params


def check_unresolved_placeholders(params):
    """
    Check for unresolved placeholders like {var} in config parameter values.
    """
    unresolved = {
        k: v for k, v in params.items()
        if isinstance(v, str) and re.search(r"{[^{}]+}", v)
    }

    if unresolved:
      raise ValueError(f"Cannot resolve YAML at placeholders: {unresolved}")


def check_unresolved_in_tpl(tpl):
    """Raise if sbatch template still has unresolved {var} (not ${var})."""
    unresolved = re.findall(r"(?<!\$)\{[^{}]+\}", tpl)
    if unresolved:
        raise ValueError(
            f"Unresolved placeholders in sbatch template: {unresolved}"
        )

def render_tpl(tpl, params):
   """Replace {var} placeholders without touching ${var}."""
   placeholders = {m[1] for m in re.finditer(r"\{(\w+)\}", tpl)}
   for k, v in params.items():
      if k in placeholders:
         tpl = tpl.replace(f"{{{k}}}", str(v))
   return tpl
 

def _prepend_section_to_values(cfg):
    """
    For each section in PREFIXES (e.g. autoexp, slurm, args),
    find placeholders like {var} in its string values and rewrite
    them as {section.var} — unless they already contain a dot.
    """
    for prefix in PREFIXES:
        section = cfg[prefix]
        updated = {}
        for k, v in section.items():
            if isinstance(v, str):
                for m in re.findall(r"\{([^{}]+)\}", v):  # find {ANYTHING}
                    if "." not in m:  # skip already qualified
                        v = v.replace(f"{{{m}}}", f"{{{prefix}.{m}}}")
            updated[k] = v
        cfg[prefix] = DictConfig(updated)
    return cfg


def generate_job_defs(cfg, verbose=0):
   """
   Returns a list of JobDef from a config file (config.yaml)
   the JobDef list can directly be used by the manager to schedule/manage the jobs
   """
   jobs = []

   # Ensure placeholders specify the corresponding section name.
   cfg = _prepend_section_to_values(cfg)

   # We split the config in two parts:
   # - experiments part, to be resolved into multiple experiments
   # - autoexp and template part, which does not need expansion
   exp_cfg = cfg.pop('experiments', {})
   
   # Flatten one part of the config, prepend section names to keys.
   flat_cfg = {}
   for prefix in PREFIXES:
      for k, v in cfg.pop(prefix, {}).items():
            flat_cfg[f'{prefix}.{k}'] = v
   if not cfg.is_empty:
      raise ValueError('Invalid configuration provided.')

   # For each combination of experiments config, we create a separate job.
   for vals in product_recursive(exp_cfg):
      # params will store the key-value pairs of all the variables that can be used in the template
      params = {}
      for ks, v in vals.items():
         # each variable is a tuple of keys and the value
         # we can have multiple keys because we can have deep branches of possibitilies
         # so as many keys as we go deep (k1, k2, ..., v)

         # we just set in params the value of the key as the value of the next key
         # i.e. k1 -> k2, k2 -> k3, etc
         for ki, kin in zip(ks[0:-1], ks[1:]):
            params[ki] = kin
         # last key goes to the actual value
         params[ks[-1]] = v
      
      # Add config from other sections. Params has higher priority.
      params = flat_cfg | params

      # Resolve template and expressions in the config.
      params = resolve_templates_expr(params, verbose)
      check_unresolved_placeholders(params)
      
      # at this point, we can use the template file to generate the config file
      # by replacing all the keys from 'params' with their values in the template
      # file.
   
      # Groups params by their prefix into nested dictionaries.
      grouped_params = defaultdict(dict)
      for k, v in params.items():
          if "." in k:
              prefix, subkey = k.split(".", 1)
              if prefix not in PREFIXES:
                  raise ValueError(f'Found argument with invalid prefix: {prefix}.')
              grouped_params[prefix][subkey] = v

      # Render templated sbatch script.
      tpl = open(grouped_params['autoexp']['template']).read()
      tpl = render_tpl(tpl, grouped_params['slurm'])
      megatron_args = " ".join(params_to_args(grouped_params['args']))
      tpl = tpl.replace("{megatron_args}", f'"{megatron_args}"')
      check_unresolved_in_tpl(tpl)

      # auto generate the name of the job from the full set of params
      # if 'name' is not present in 'params', otherwise just use the value of 'name'
      # from params. TODO (nico): change!
      name = grouped_params['autoexp'].get('name', _auto_name(grouped_params['slurm']))
      # Define the 'JobDef' structure, which is directly used by the manager
      # to schedule/manaage the jobs
      jobdef = JobDef(config=tpl, name=name, params=grouped_params)
      
      # Populate jobdef dataclass from params, enforcing required fields.
      for field in fields(jobdef):
         for params in grouped_params.values():
            if field.name in params:
               setattr(jobdef, field.name, params[field.name])
               break
         else:
            if field.name in MANDATORY_FIELDS:
               raise ValueError(f"Field '{field.name}' is a not provided, but is MANDATORY")
      
      jobs.append(jobdef)
   _check_name_uniqueness(jobs)
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

def _is_expr(e):
   return type(e) == str and e.startswith("expr(") and e.endswith(")")

def _eval_expr(e):
   assert _is_expr(e)
   start = len("expr(")
   end = -1
   return eval(e[start:end])

def _check_name_uniqueness(jobdefs):
    """
    Check that all job names are unique.
    """
    names = [jobdef.name for jobdef in jobdefs]
    if len(names) != len(set(names)):
        raise ValueError("Job names must be unique. Found duplicates: {}".format(
            [name for name in set(names) if names.count(name) > 1]))
