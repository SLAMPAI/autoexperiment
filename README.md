# autoexperiment

Launch and manage batch of SLURM experiments easily
\
# How to install

- `git clone https://github.com/SLAMPAI/autoexperiment`
- `python setup.py develop`

# How to use

## Step 1: write a `template.sbatch` to define sbatch template

```bash
#!/bin/bash -x
#SBATCH --account=cstdl
#SBATCH --nodes={nodes}
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=24
#SBATCH --time=01:00:00
#SBATCH --partition=dc-gpu
#SBATCH --output={output_file}
echo "Job Id:$SLURM_JOB_ID"
ml purge
export TRANSFORMERS_CACHE=cache
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES=0,1,2,3
export MASTER_PORT=12802
master_addr=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export MASTER_ADDR=$master_addr"i"
echo "MASTER_ADDR="$MASTER_ADDR
export PYTHONPATH="$PYTHONPATH:$PWD/src"
srun --cpu_bind=none,v --accel-bind=gn python -u src/training/main.py \
    --save-frequency 1 \
    --imagenet-val "/p/fastdata/mmlaion/imagenet_val" \
    --zeroshot-frequency 1 \
    --train-data="{train_data}"  --dataset-type webdataset\
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
    --lr 0.001 \
    --save-most-recent \
    --precision amp_bfloat16 \
    --grad-checkpoint \
    --resume latest
```


## Step 2: write a `config.yaml` file for defining experiments

```yaml
defs:

  datacomp:
    train_data: "/path/{0000000..0139827}.tar"
  laion2b:
    train_data: "/path/{00000..23295}.tar"
  s32:
    model: ViT-S-32
    batch_size: 1024
  m32:
    model: ViT-M-32
    batch_size: 1024
  
common:
  template: template.sbatch
  output_file: "{logs}/{name}/slurm.out"
  job_id_regexp: "Job Id:(\\d+)"
  sbatch_script: "sbatch/{name}.sbatch"
  cmd: "sbatch {sbatch_script}"
  termination_str: "Eval Epoch: {epochs}"
  check_interval_secs: 600
experiments:
  set1:
      dataset: [datacomp, laion2b]
      model: [s32, m32]
      epochs: [1]
      logs: "logs/{set}"
      name: "{set}_{dataset}_{model}_{epochs}"
      nodes: [1]
      train_num_samples: [12_800_000]

```

## Step 3 : run all the jobs together with autorestart ability

First, we generate sbatch scripts:

`autoexperiment build config.yaml`

```bash
> ls sbatch
set1_datacomp_ViT-M-32_1.sbatch  set1_datacomp_ViT-S-32_1.sbatch  set1_laion2b_ViT-M-32_1.sbatch  set1_laion2b_ViT-S-32_1.sbatch
```


Then, we run all the jobs

`autoexperiment run config.yaml`


