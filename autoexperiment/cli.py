"""Console script for autoexperiment."""
from clize import run
import sys
import os
from autoexperiment.template import generate_job_defs
from autoexperiment.manager import manage_jobs_forever


def main():
    run(launch)

def launch(config):
    if not config:
         print("Please specify a config file")
         return 1
    jobdefs = generate_job_defs(config)
    for jobdef in jobdefs:
       with open(f"{jobdef.sbatch_script}", "w") as f:
          f.write(jobdef.config)
       os.makedirs(os.path.dirname(jobdef.output_file), exist_ok=True)
    manage_jobs_forever(jobdefs)
    return 0


if __name__ == "__main__":
    sys.exit(run(main))  # pragma: no cover
