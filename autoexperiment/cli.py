"""Console script for autoexperiment."""
from clize import run as clize_run
import sys
import os
from autoexperiment.template import generate_job_defs
from autoexperiment.manager import manage_jobs_forever


def main():
    return clize_run([build, run])


def build(config, *, exp:str=None):
    """
    Generate sbatch scripts from a yaml config file that
    defines a set of experiments to do.
    """
    if not config:
         print("Please specify a config file")
         return 1
    jobdefs = generate_job_defs(config, exp_name=exp)
    for jobdef in jobdefs:
       with open(f"{jobdef.sbatch_script}", "w") as f:
          f.write(jobdef.config)
       os.makedirs(os.path.dirname(jobdef.output_file), exist_ok=True)
    return 0

def run(config, *, exp:str=None):
    """
    Manage/schedule jobs corresponding to a config file after
    having generated the sbatch scripts.
    This step requires the 'build' step to have been done first.
    """
    if not config:
         print("Please specify a config file")
         return 1
    jobdefs = generate_job_defs(config, exp_name=exp)
    manage_jobs_forever(jobdefs)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
