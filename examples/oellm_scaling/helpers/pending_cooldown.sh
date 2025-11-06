#!/bin/bash

# Script to find a checkpoint directory and create a symbolic link to it.
# Search for a checkpoint directory and 
#
# Arguments:
#   $1: LOGS directory path
#   $2: Experiment name (EXP_NAME)
#   $3: Iteration number (ITER)
#   $4: Cooldown scale (CD_SCALE)

# Assign arguments to variables
CKPT_FOLDER="$1"
STABLE_NAME="$2"
DECAY_NAME="$3"
ITER="$4"

# Read folder
READ_FOLDER="${CKPT_FOLDER}/${STABLE_NAME}"
WRITE_FOLDER="${CKPT_FOLDER}/${DECAY_NAME}"

# Construct the find command.  Crucially handles the wildcard expansion correctly.
# The shell expands {ITER} before find is even executed.  So we *must* put
# iter_* in single quotes.
path_out=$(find "${READ_FOLDER}" -maxdepth 1 -type d -name "iter_[0]*${ITER}" 2>/dev/null)

# Check if a matching directory was found and create the symlink.
if [[ -n "$path_out" ]]; then
  sleep 5
  mkdir -p "${WRITE_FOLDER}"
  ln -s "$path_out" "${WRITE_FOLDER}"
  echo "$ITER" > "${WRITE_FOLDER}/latest_checkpointed_iteration.txt"
  echo 1
else
  echo 0
fi

exit 0