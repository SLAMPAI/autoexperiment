#!/bin/bash

#SBATCH --time=00:15:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gpus-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --account=AIFAC_L01_028
#SBATCH --partition=boost_usr_prod
#SBATCH --qos=boost_qos_dbg
#SBATCH --threads-per-core=1
#SBATCH --job-name=test3_lr0.01_iters10
#SBATCH --output=/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/%x-%j.out
#SBATCH --error=/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/%x-%j.err

# For quick tests on max 2 nodes: #SBATCH --qos=boost_qos_dbg
# For large node numbers (> 64 nodes): a dd #SBATCH --qos=boost_qos_bprod

######################################################################
# PATHS
#
# out_dir/
# ├── slurm_output/
# │   ├── %n-%j-%a-TIMESTAMP.err
# │   └── %n-%j-%a-TIMESTAMP.out
# └── checkpoints/
#     └── %n/
#         ├── tensorboard/
#         ├── wandb/
#         ├── iter_0001000/
#         ├── iter_0002000/
#         └── ...
#
# MEGATRON_CACHE_BASE/
# └── USER/
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
[[ -e "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid.out" ]] && mv -f "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid.out" "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid-$timestamp.out"
[[ -e "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid.err" ]] && mv -f "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid.err" "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/$logid-$timestamp.err"

# SOURCE CLUSTER SETUP SCRIPT
SETUP_SCRIPT=/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/cluster/setup_leonardo.sh
chmod +x $SETUP_SCRIPT
source $SETUP_SCRIPT

# OUTPUT_DIR
CHECKPOINT_PATH="/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs/checkpoints/$SLURM_JOB_NAME"
TENSORBOARD_DIR="${CHECKPOINT_PATH}/tensorboard"
WANDB_DIR="${CHECKPOINT_PATH}/wandb"
mkdir -p "/leonardo/home/userexternal/najroldi/oellm/dev/autoexperiment/examples/oellm_sweep/logs" "$CHECKPOINT_PATH" "$TENSORBOARD_DIR" "$WANDB_DIR"

######################################################################
# MEGATRON ARGUMENTS
######################################################################

# Megatron arguments are injected when template is rendereed
ARGS="--wandb-exp-name test3_lr0.01_iters10 --wandb-project oellm-train --train-iters 10 --lr-decay-iters 2 --lr-wsd-decay-iters 2 --data-path /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_0 /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_1 /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_2 /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_3 /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_4 /leonardo_work/AIFAC_L01_028/najroldi/datasets/Nemotron-cc-2024-HQ-real-synth-mix/GPT-NeoX/merged_5 --seq-length 2048 --max-position-embeddings 2048 --micro-batch-size 25 --global-batch-size 100 --vocab-file /leonardo_work/AIFAC_L01_028/najroldi/models/EleutherAI/gpt-neox-20b/vocab.json --merge-file /leonardo_work/AIFAC_L01_028/najroldi/models/EleutherAI/gpt-neox-20b/merges.txt --num-workers 8 --split 99,1,0 --num-layers 5 --hidden-size 160 --ffn-hidden-size 640 --num-attention-heads 4 --init-method-std 0.02 --position-embedding-type rope --rotary-base 10000 --rotary-percent 1.0 --num-query-groups 8 --attention-dropout 0.0 --hidden-dropout 0.0 --normalization RMSNorm --norm-epsilon 1e-05 --bf16 --swiglu --use-flash-attn --disable-bias-linear --overlap-param-gather --overlap-grad-reduce --tensor-model-parallel-size 1 --pipeline-model-parallel-size 1 --context-parallel-size 1 --sequence-parallel --use-distributed-optimizer --distributed-backend nccl --distributed-timeout-minutes 10 --optimizer adam --adam-beta1 0.9 --adam-beta2 0.95 --adam-eps 1e-08 --min-lr 0.0 --lr-decay-style WSD --lr-wsd-decay-style linear --clip-grad 1.0 --weight-decay 0.05 --profile-ranks 0 --profile-step-start 5 --profile-step-end 12 --eval-interval 72661 --eval-iters 1 --log-interval 2 --log-progress --log-throughput --tensorboard-queue-size 5 --ckpt-format torch --save-interval 10 --lr 0.01"

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
