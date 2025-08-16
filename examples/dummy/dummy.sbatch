#!/bin/bash -x
#SBATCH --account=cstdl
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:01:00
#SBATCH --partition=dc-cpu
#SBATCH --job-name={name}
echo "FINISHED JOB"
