#!/bin/bash
#SBATCH --job-name={name}
#SBATCH --time=00:05:00
#SBATCH --nodes={nnodes}
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --account=AIFAC_L01_028
#SBATCH --partition=boost_usr_prod
#SBATCH --threads-per-core=1
#SBATCH --output={output_file}
#SBATCH --qos=boost_qos_dbg

# For quick tests on max 2 nodes: #SBATCH --qos=boost_qos_dbg
# For large node numbers (> 64 nodes): add #SBATCH --qos=boost_qos_bprod

# Test script for AutoExp with Full YAML integration.

echo "Dummy job, with name: {name}"

