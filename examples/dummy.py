from autoexperiment.manager import manage_jobs_forever
from autoexperiment.template import JobDef

dummy="""#!/bin/bash -x
#SBATCH --account=cstdl
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:01:00
#SBATCH --partition=dc-cpu
echo "FINISHED JOB $1"
"""
with open("dummy.sbatch", "w") as fd:
    fd.write(dummy)

nb_jobs = 3
jobs = [
    JobDef(
        cmd=f"sbatch --output slurm_{i}.out dummy.sbatch {i}",
        output_file=f"slurm_{i}.out",
        check_interval_secs=2, 
        termination_str="FINISHED JOB", name=f"Job {i}"
    ) 
    for i in range(nb_jobs)
]
manage_jobs_forever(jobs)
