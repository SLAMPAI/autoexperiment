#!/bin/bash
# Check if cooldown CONVERT_EVAL phase has finished.
# Usage: cooldown_convert_eval.sh RUN_DIR LOGS EXP_NAME CD_SCALE
# Returns 1 if conversion is done, else 0. Blocks until training finishes.

RUN_DIR=$1
LOGS=$2
EXP_NAME=$3
CD_SCALE=$4

convert_done=$(/p/project1/ccstdl/porian1/Megatron-LM-Open-Sci/configs/convert_helper.sh "$RUN_DIR")
train_count=$(grep "after training is done" "$LOGS/$EXP_NAME/cooldown_s$CD_SCALE/slurm_train.out" 2>/dev/null | wc -l)

if [ "$train_count" -gt 0 ]; then train_done=1; else train_done=0; fi
echo $(( (1 - convert_done) * train_done ))
