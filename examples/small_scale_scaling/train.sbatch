#!/bin/bash -x
#SBATCH --account=laionize
#SBATCH --nodes={nodes}
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=24
#SBATCH --time=06:00:00
#SBATCH --partition=booster
#SBATCH --output={output_file}
#SBATCH --job-name={name}
ml purge
export TRANSFORMERS_CACHE=cache
export TRANSFORMERS_OFFLINE=1
source /p/project/ccstdl/laion/mamba/bin/activate experimental-torch-nightly
export CUDA_VISIBLE_DEVICES=0,1,2,3
export MASTER_PORT=12802
master_addr=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export MASTER_ADDR=$master_addr"i"
echo "MASTER_ADDR="$MASTER_ADDR
export PYTHONPATH="$PYTHONPATH:$PWD/src"
srun --cpu_bind=none,v --accel-bind=gn python -u src/training/main.py \
    --save-frequency 1 \
    --zeroshot-frequency 1 \
    --train-data="{train_data}" --dataset-type webdataset\
    --train-num-samples={train_num_samples} \
    --warmup 2000 \
    --batch-size={batch_size} \
    --report-to=tensorboard \
    --epochs={epochs} \
    --workers=8 \
    --model {model} \
    --name {name} \
    --logs {logs} \
    --seed 0 \
    --ddp-static-graph \
    --local-loss \
    --gather-with-grad \
    --lr {lr} \
    --save-most-recent \
    --precision amp_bfloat16 \
    --grad-checkpoint \
    --grad-clip-norm 1 \
    --resume latest
