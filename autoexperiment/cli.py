"""Console script for autoexperiment."""
from omegaconf import OmegaConf
from clize import run as clize_run
from clize.parameters import multi
import sys
import os
import warnings
from subprocess import call
from autoexperiment.template import generate_job_defs
from autoexperiment.manager import manage_jobs_forever


def main():
    return clize_run([build, run, build_and_run, for_each])


def build(config, *, fix:('f', multi()), verbose=1):
    """
    Generate sbatch scripts from a yaml config file that
    defines a set of experiments to do.
    """
    if not config:
         print("Please specify a config file")
         return 1
    cfg = OmegaConf.load(config)
    if fix:
        for param in fix:
            assert "=" in param, "Invalid param format. Please use key=value."
            key, value = param.split("=")
            cfg[key] = value       
    jobdefs = generate_job_defs(cfg, verbose=verbose)
    for jobdef in jobdefs:
       _assert_job_name(jobdef.config, jobdef.name)
       os.makedirs(os.path.dirname(jobdef.sbatch_script), exist_ok=True)
       print(f"Building '{jobdef.sbatch_script}'...")
       with open(f"{jobdef.sbatch_script}", "w") as f:
          f.write(jobdef.config)
       os.makedirs(os.path.dirname(jobdef.output_file), exist_ok=True)
       
       # Save sbatch script to logs directory as well
       _save_sbatch_to_logs(jobdef, verbose)

def _assert_job_name(config:str, name:str):
    # check if there is a line containing `#SBATCH --job-name={name}`
    if f"#SBATCH --job-name={name}" not in config:
        raise ValueError("Please add #SBATCH --job-name={name} to your sbatch templates")

def _save_sbatch_to_logs(jobdef, verbose=1):
    """
    Save the sbatch script to the logs directory alongside the original location.
    """
    # Extract logs directory from output_file path
    logs_dir = os.path.dirname(jobdef.output_file)
    
    # Create a descriptive name for the sbatch file
    # Try to extract mode from the jobdef.name or use a default
    sbatch_filename = _get_sbatch_filename_for_logs(jobdef)
    logs_sbatch_path = os.path.join(logs_dir, sbatch_filename)
    
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # Copy the sbatch content to logs directory
    if verbose >= 1:
        print(f"Saving sbatch script to logs: '{logs_sbatch_path}'")
    
    with open(logs_sbatch_path, "w") as f:
        f.write(jobdef.config)

def _get_sbatch_filename_for_logs(jobdef):
    """
    Generate a descriptive filename for the sbatch script in logs directory.
    """
    # Try to extract mode from job name (e.g., "exp_TRAIN" -> "train.sbatch")
    name_parts = jobdef.name.split('_')
    if len(name_parts) > 1:
        mode = name_parts[-1].lower()
        return f"{mode}.sbatch"
    
    # Fallback: use the basename of the original sbatch_script
    return os.path.basename(jobdef.sbatch_script)

def run(config, *params, dry=False, verbose=1, max_jobs:int=None, fix:('f', multi())):
    """
    Manage/schedule jobs corresponding to a config file after
    having generated the sbatch scripts.
    This step requires the 'build' step to have been done first.
    
    :param max_jobs: Maximum total jobs in SLURM queue (any state)
    """
    if not config:
         print("Please specify a config file")
         return 1
    cfg = OmegaConf.load(config)
    if fix:
        for param in fix:
            assert "=" in param, "Invalid param format. Please use key=value."
            key, value = param.split("=")
            cfg[key] = value
    jobdefs = generate_job_defs(cfg, verbose=verbose)
    if params:
        # filter jobs by params
        params_dict = {}
        for param in params:
            assert "=" in param, "Invalid param format. Please use key=value."
            key, value = param.split("=")
            params_dict[key] = value.split(",")
        jobdefs = [jobdef for jobdef in jobdefs if all(str(jobdef.params.get(k)) in vs for k, vs in params_dict.items())]
    if dry:
        for jobdef in jobdefs:
            print(jobdef.params["name"])
        return
    manage_jobs_forever(jobdefs, max_jobs=max_jobs, verbose=verbose)

def build_and_run(config, *params, dry=False, verbose=1, max_jobs:int=None, fix:('f', multi())):
    """
    do both above at the same time, for simplicity
    """
    build(config, fix=fix, verbose=verbose)
    run(config, *params, dry=dry, verbose=verbose, fix=fix, max_jobs=max_jobs)

def for_each(config, cmd):
    jobdefs = generate_job_defs(config)
    for jobdef in jobdefs:
        cmd_ = cmd.format(**jobdef.params)
        call(cmd_, shell=True)

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
