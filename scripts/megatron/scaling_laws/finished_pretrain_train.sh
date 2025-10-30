#!/bin/bash
# Check if pretrain TRAIN phase has finished.
# Usage: pretrain_train.sh LOGS EXP_NAME
# Returns 1 if training is done, else 0.

LOGS=$1
EXP_NAME=$2

train_count=$(grep -E "after training is done|KeyError" "$LOGS/$EXP_NAME/slurm_train.out" 2>/dev/null | wc -l)
if [ "$train_count" -gt 0 ]; then
  echo 1
else
  echo 0
fi
