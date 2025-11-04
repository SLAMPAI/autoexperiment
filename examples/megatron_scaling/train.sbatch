#!/bin/bash

#SBATCH --time=00:15:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gpus-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --account={account}
#SBATCH --partition={partition}
#SBATCH --qos={qos}
#SBATCH --threads-per-core=1
#SBATCH --job-name={job_name}
#SBATCH --output={out_dir}/%x-%j.out
#SBATCH --error={out_dir}/%x-%j.err

# For quick tests on max 2 nodes: #SBATCH --qos=boost_qos_dbg
# For large node numbers (> 64 nodes): a dd #SBATCH --qos=boost_qos_bprod

######################################################################
# PATHS
#
# {out_dir}/
# ├── slurm_output/
# │   ├── %n-%j-%a-{TIMESTAMP}.err
# │   └── %n-%j-%a-{TIMESTAMP}.out
# └── checkpoints/
#     └── %n/
#         ├── tensorboard/
#         ├── wandb/
#         ├── iter_0001000/
#         ├── iter_0002000/
#         └── ...
#
# {MEGATRON_CACHE_BASE}/
# └── {USER}/
#     ├── MEGATRON_CACHEDIR/
#     ├── APPTAINER_CACHEDIR/
#     └── APPTAINER_TMPDIR/
#
# This is a template, variables in brackets are meant to be replaced.
#
######################################################################

######################################################################
# PATHS and ENV VARS
######################################################################

# Bash "strict mode" (see http://redsymbol.net/articles/unofficial-bash-strict-mode/)
set -euo pipefail

# When slurm reschedules a job that ended on node failure, it will run
# with the same job ID, clobbering the original logs. Rename the logs
# and include timestamp to avoid this.
timestamp=$(date +%Y-%m-%d_%H-%M-%S)
logid="${SLURM_JOB_NAME}-${SLURM_JOBID}"
[[ -e "{out_dir}/$logid.out" ]] && mv -f "{out_dir}/$logid.out" "{out_dir}/$logid-$timestamp.out"
[[ -e "{out_dir}/$logid.err" ]] && mv -f "{out_dir}/$logid.err" "{out_dir}/$logid-$timestamp.err"

# SOURCE CLUSTER SETUP SCRIPT
SETUP_SCRIPT={cluster_setup_script}
chmod +x $SETUP_SCRIPT
source $SETUP_SCRIPT

# OUTPUT_DIR
CHECKPOINT_PATH="{out_dir}/checkpoints/$logid"
TENSORBOARD_DIR="${CHECKPOINT_PATH}/tensorboard"
WANDB_DIR="${CHECKPOINT_PATH}/wandb"
mkdir -p "{out_dir}" "$CHECKPOINT_PATH" "$TENSORBOARD_DIR" "$WANDB_DIR"

######################################################################
# MEGATRON ARGUMENTS
######################################################################

# Megatron arguments are injected when template is rendereed
ARGS={megatron_args}

# Append args depending on path
ARGS+=(
    --load "${CHECKPOINT_PATH}"
    --save "${CHECKPOINT_PATH}"
    --tensorboard-dir "${TENSORBOARD_DIR}"
    --wandb-save-dir "${WANDB_DIR}"
    --data-cache-path "${MEGATRON_CACHE}"
)

######################################################################
# RUN
######################################################################

# CMD="${MEGATRON_PATH}/pretrain_gpt.py ${ARGS[@]}"
CMD="${MEGATRON_PATH}/pretrain_gpt.py ${ARGS[*]}"

echo '=============== CMD: ==============='
echo $CMD
echo '===================================='

cd $MEGATRON_PATH

srun \
    --wait=60 \
    --cpus-per-task=$SLURM_CPUS_PER_TASK \
    --threads-per-core=1 \
    --kill-on-bad-exit=1 \
    --jobid $SLURM_JOBID \
    bash -c \
    "singularity exec --nv --bind $BIND_DIRS $CONTAINER \
    python -u -m torch.distributed.run \
      --nproc-per-node $SLURM_GPUS_PER_NODE \
      --nnodes $SLURM_NNODES \
      --rdzv_endpoint $MASTER_ADDR:$MASTER_PORT \
      --rdzv_backend static \
      --max_restarts 0 \
      --tee 3 \
      --node_rank \$SLURM_PROCID \
      --role \$SLURMD_NODENAME: \
      $CMD"

echo "END $SLURM_JOBID: $(date)"
