#!/bin/bash

# Container image
CONTAINER="/leonardo_work/AIFAC_L01_028/container_images/container_images/pytorch_24.09-py3_leonardo.sif"

# Leonardo project directory
PROJECT_DIR="/leonardo_work/AIFAC_L01_028"
PROJECT_FAST_DIR="/leonardo_scratch/fast/AIFAC_L01_028"

# Path to Megatron-LM repo
MEGATRON_PATH="/leonardo_work/AIFAC_L01_028/najroldi/Megatron-LM"

# MEGATRON CACHE
MEGATRON_CACHE_BASE="/leonardo_scratch/large/userexternal"

# CACHE
MEGATRON_CACHE_FOLDER="${MEGATRON_CACHE_BASE}/${USER}"
export MEGATRON_CACHE="${MEGATRON_CACHE_FOLDER}/MEGATRON_CACHEDIR"
mkdir -p "$MEGATRON_CACHE_FOLDER"
mkdir -p "$MEGATRON_CACHE"

# APPTAINER CACHE
export APPTAINER_CACHEDIR="${MEGATRON_CACHE_FOLDER}/APPTAINER_CACHEDIR"
export APPTAINER_TMPDIR="${MEGATRON_CACHE_FOLDER}/APPTAINER_TMPDIR"
mkdir -p $APPTAINER_CACHEDIR
mkdir -p $APPTAINER_TMPDIR

# Directories to map into the container
BIND_DIRS="${PROJECT_DIR},${PROJECT_FAST_DIR},${MEGATRON_PATH},${MEGATRON_CACHE_FOLDER}"

######################################################################
# ENV VARS and SETTING
######################################################################

# No connection on compute nodes
export WANDB_MODE="offline"

# DISTRIBUTED SETUP
MASTER_ADDR=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -n 1)  # master node hostname
MASTER_ADDR="$(nslookup "$MASTER_ADDR" | grep -oP '(?<=Address: ).*')"  # IP numeric address
export MASTER_ADDR="$MASTER_ADDR"
export MASTER_PORT=12345
echo "MASTER_ADDR:MASTER_PORT set to: ${MASTER_ADDR}:${MASTER_PORT}"

# NCCL settings to improve distributed training stability (handling flipping links, irresponsive nodes, etc)
# waiting for 120s in case nodes become irresponsive giving a chance to recover
export NCCL_IB_TIMEOUT=120
export TRITON_LIBCUDA_PATH=/usr/local/cuda/lib64/stubs
export CUDA_DEVICE_MAX_CONNECTIONS=1
export OMP_NUM_THREADS=1
