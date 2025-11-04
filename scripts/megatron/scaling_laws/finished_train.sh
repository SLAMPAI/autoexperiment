#!/bin/bash
# Usage: finished_train.sh LOG_FILE
# Returns 1 if training is done, else 0.

LOG_FILE=$1

train_count=$(grep -E "after training is done|KeyError" "$LOG_FILE" 2>/dev/null | wc -l)
if [ "$train_count" -gt 0 ]; then
  echo 1
else
  echo 0
fi
