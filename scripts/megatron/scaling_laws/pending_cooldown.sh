#!/bin/bash

# Script to find a checkpoint directory and create a symbolic link to it.
#
# Arguments:
#   $1: LOGS directory path
#   $2: Experiment name (EXP_NAME)
#   $3: Iteration number (ITER)
#   $4: Cooldown scale (CD_SCALE)

# Assign arguments to variables
LOGS="$1"
EXP_NAME="$2"
ITER="$3"
CD_SCALE="$4"

# Construct the find command.  Crucially handles the wildcard expansion correctly.
# The shell expands {ITER} before find is even executed.  So we *must* put
# iter_* in single quotes.
path_out=$(find "${LOGS}/${EXP_NAME}/checkpoints" -maxdepth 1 -type d -name "iter_[0]*${ITER}" 2>/dev/null)

# Check if a matching directory was found and create the symlink.
if [[ -n "$path_out" ]]; then
  sleep 5
  mkdir -p "${LOGS}/${EXP_NAME}/cooldown_s${CD_SCALE}/checkpoints"
  ln -s "$path_out" "${LOGS}/${EXP_NAME}/cooldown_s${CD_SCALE}/checkpoints/"
  echo "$ITER" > "${LOGS}/${EXP_NAME}/cooldown_s${CD_SCALE}/checkpoints/latest_checkpointed_iteration.txt"
  echo 1
else
  echo 0
fi

exit 0