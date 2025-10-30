#!/bin/bash
# Check if cooldown TRAIN phase has finished.
# Usage: cooldown_train.sh LOGS EXP_NAME CD_SCALE
# Returns 1 if training is done, else 0.

LOGS=$1
EXP_NAME=$2
CD_SCALE=$3

train_count=$(grep "after training is done" "$LOGS/$EXP_NAME/cooldown_s$CD_SCALE/slurm_train.out" 2>/dev/null | wc -l)
if [ "$train_count" -gt 0 ]; then
  echo 1
else
  echo 0
fi
