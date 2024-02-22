#!/bin/bash -x
#SBATCH --account=laionize
#SBATCH --nodes={nodes}
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=12
#SBATCH --time=02:00:00
#SBATCH --partition=booster
#SBATCH --output={output_file}
echo "Job Id:$SLURM_JOB_ID"
ml purge
source /p/project/ccstdl/laion/mamba/bin/activate experimental-torch-nightly
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python 
export CUDA_VISIBLE_DEVICES=0,1,2,3
srun --cpu_bind=v --cpus-per-task=12 clip_benchmark  eval --model {model} --pretrained {logs}/{name}/checkpoints/*.pt --dataset wds/imagenet1k wds/mscoco_captions --dataset_root '/p/fastdata/mmlaion/vtab_plus_wds/{{dataset}}' --output '{logs}/{name}/checkpoints/{{dataset}}_{{pretrained}}_{{model}}_{{language}}_{{task}}.json' --skip_existing --distributed
