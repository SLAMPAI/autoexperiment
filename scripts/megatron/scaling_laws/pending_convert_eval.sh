#!/bin/bash

# Script to monitor for unconverted checkpoints and return count
#
# Arguments:
#   $1: LOGS directory path
#   $2: Experiment name (EXP_NAME)
#   $3: Optional: minimum iteration number to consider
#
# Returns:
#   Count of remaining unconverted checkpoints

# Assign arguments to variables
# LOGS="$1"
# EXP_NAME="$2"
RUN_DIR="$1"
MIN_ITER="${3:-0}"

# Checkpoint directories
CHECKPOINT_DIR="${RUN_DIR}/checkpoints"
CONVERTED_TRACKING_DIR="${RUN_DIR}/converted_checkpoints"
IN_PROGRESS_TRACKING_DIR="${RUN_DIR}/in_progress_checkpoints"

# Create tracking directories if they don't exist
mkdir -p "$CONVERTED_TRACKING_DIR"
mkdir -p "$IN_PROGRESS_TRACKING_DIR"

# echo "Checking for unconverted checkpoints..."
# echo "Checkpoint directory: $CHECKPOINT_DIR"

# Check if checkpoint directory exists
if [[ ! -d "$CHECKPOINT_DIR" ]]; then
    # echo "Checkpoint directory does not exist: $CHECKPOINT_DIR"
    echo 0
    exit 0
fi

# Find all checkpoint iterations (only directories, handle zero-padded numbers)
AVAILABLE_ITERS=$(find "$CHECKPOINT_DIR" -maxdepth 1 -type d -name "iter_*" -printf "%f\n" 2>/dev/null | sed 's/iter_0*//' | sort -n)

if [[ -z "$AVAILABLE_ITERS" ]]; then
    # echo "No checkpoints found in $CHECKPOINT_DIR"
    echo 0
    exit 0
fi

# echo "Available iterations: $(echo $AVAILABLE_ITERS | tr '\n' ' ')"

# Count unconverted checkpoints that meet criteria
UNCONVERTED_COUNT=0
for iter in $AVAILABLE_ITERS; do
    # Skip if below minimum iteration
    if [[ $iter -lt $MIN_ITER ]]; then
        continue
    fi
    
    # Skip if already converted or in progress
    if [[ -f "$CONVERTED_TRACKING_DIR/iter_$iter.done" || -f "$IN_PROGRESS_TRACKING_DIR/iter_$iter.lock" ]]; then
        continue
    fi
    
    # Check if the checkpoint is complete (has model_optim_rng.pt in rank 0 folder)
    # Handle zero-padded directory names
    CHECKPOINT_PATH="$CHECKPOINT_DIR/iter_$(printf "%07d" $iter)"
    
    # Look for the rank 0 checkpoint file in possible subdirectories
    RANK_0_FOUND=false
    for subdir in "mp_rank_00" "mp_rank_00_000" "mp_rank_00_dp_000" "mp_rank_00_000_dp_000"; do
        if [[ -f "$CHECKPOINT_PATH/$subdir/model_optim_rng.pt" ]]; then
            # Also check file size is stable (not being written)
            FILESIZE1=$(stat -c%s "$CHECKPOINT_PATH/$subdir/model_optim_rng.pt" 2>/dev/null || echo "0")
            sleep 2
            FILESIZE2=$(stat -c%s "$CHECKPOINT_PATH/$subdir/model_optim_rng.pt" 2>/dev/null || echo "0")
            if [[ "$FILESIZE1" == "$FILESIZE2" && "$FILESIZE1" -gt 0 ]]; then
                RANK_0_FOUND=true
                break
            fi
        fi
    done
    
    if [[ "$RANK_0_FOUND" == "true" ]]; then
        # echo "Found convertible checkpoint: iter_$iter"
        ((UNCONVERTED_COUNT++))
    fi
done

# Return 1 if there are unconverted checkpoints, 0 if none
if [[ $UNCONVERTED_COUNT -gt 0 ]]; then
    echo 1
    exit 0
else
    echo 0
    exit 0
fi