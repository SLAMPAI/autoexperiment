#!/bin/bash
# Usage: finished_convert_eval.sh RUN_DIR LOG_FILE
# Returns 1 if conversion is done, else 0. Blocks until training finishes.

LOG_FILE=$1
RUN_DIR=$2

SCRIPT_DIR="$(dirname "$0")"
convert_pending=$("$SCRIPT_DIR/pending_convert_eval.sh" "$RUN_DIR")
train_count=$(grep -E "after training is done|KeyError" "$LOG_FILE" 2>/dev/null | wc -l)

if [ "$train_count" -gt 0 ]; then train_done=1; else train_done=0; fi
echo $(( (1 - convert_pending) * train_done ))
