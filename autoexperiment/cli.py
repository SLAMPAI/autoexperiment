"""Console script for autoexperiment."""
from clize import run as clize_run
import sys
import os
from autoexperiment.template import generate_job_defs
from autoexperiment.manager import manage_jobs_forever


def main():
    return clize_run([build, run, build_and_run])


def build(config):
    """
    Generate sbatch scripts from a yaml config file that
    defines a set of experiments to do.
    """
    if not config:
         print("Please specify a config file")
         return 1
    jobdefs = generate_job_defs(config)
    for jobdef in jobdefs:
       os.makedirs(os.path.dirname(jobdef.sbatch_script), exist_ok=True)
       print(jobdef.sbatch_script)
       with open(f"{jobdef.sbatch_script}", "w") as f:
          f.write(jobdef.config)
       os.makedirs(os.path.dirname(jobdef.output_file), exist_ok=True)

def run(config, *params, dry=False):
    """
    Manage/schedule jobs corresponding to a config file after
    having generated the sbatch scripts.
    This step requires the 'build' step to have been done first.
    """
    if not config:
         print("Please specify a config file")
         return 1
    jobdefs = generate_job_defs(config)
    if params:
        # filter jobs by params
        params_dict = {}
        for param in params:
            assert "=" in param, "Invalid param format. Please use key=value."
            key, value = param.split("=")
            params_dict[key] = value
        jobdefs = [jobdef for jobdef in jobdefs if all(str(jobdef.params.get(k)) == v for k, v in params_dict.items())]
    if dry:
        for jobdef in jobdefs:
            print(jobdef.params["name"])
        return
    manage_jobs_forever(jobdefs)

def build_and_run(config, *params, dry=False):
    """
    do both above at the same time, for simplicity
    """
    build(config)
    run(config, *params, dry=dry)

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
