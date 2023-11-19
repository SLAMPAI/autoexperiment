# autoexperiment

Launch and manage batch of SLURM experiments easily

# How to install

- `git clone https://github.com/SLAMPAI/autoexperiment`
- `pip install -r requirements.txt`
- `python setup.py develop`

 How to use

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
  # here we define reusable components, each component translate to a number
  # of variables that are instantiated in the template file.
  # e.g. if we define a 'datacomp' section, and use it in defining experiments (below),
  # all the values defined under take their corresponding value, e.g. `train_data` will be replaced
  # by "/path/{0000000..0139827}.tar" in the sbatch template file.
  # Here, we have only 'train_data', but we can have a list of variables.

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
  # here we define common variables to all experiments

  # path to the sbatch template file, this is the basic squeleton of all sbatch files, where variables to be replaced are written as {NAME} (see above)
  template: template.sbatch 
  
  # path of the standard output file, it is important as it is used for checking three important things:
  # 1 - if the job is frozen (if no change in during `check_interval_secs` secs)
  # 2 - the SLURM job id (`job_id_regexp`), this is important if, for some reason, 
  # the `autoexperiment run <CONFIG>` process is terminated and we want to resume it 
  # while we still have running jobs in SLURM. If it happens, just relaunch 
  # `autoexperiment run <CONFIG>` again, and it will find automatiaclly the SLURM job ids 
  # and continue as before, instead of launching new ones.
  # 3 - to find if the termination string (`termination_str`) appeared, this is used to 
  # stop restarting the jobs forever (remember that we have a max time limit in SLURM, 
  # so we restart the job as much as needed until we find the `termination_str`)
  output_file: "{logs}/{name}/slurm.out"
  
  # it is IMPORTANT that in the sbatch script (`template.sbatch`), we have a way to display
  # the SLURM job id (see explanation above), here we define the regexp used to 
  # find the SLURM job id.
  job_id_regexp: "Job Id:(\\d+)"
  # it is IMPORTANT to define the `termination_str`, it is a regexp used to detect
  #  if a job is finished, otherwise, it will be restarted FOREVER.
  termination_str: "Eval Epoch: {epochs}"

  # path of sbatch scripts that are generated from the `template`
  # each experiment will have a dedicated sbatch script.
  sbatch_script: "sbatch/{name}.sbatch"

  # command to run for each job.
  cmd: "sbatch {sbatch_script}"

  # check the status jobs each number of secs, to restart them if needed
  check_interval_secs: 600

experiments:
  # in experiments, we define a list of named set of experiments
  # in each set (here, we only define a single one, `set1`), we
  # simply do the cartesian product of all the parameters defined in it
  # each member of the product will define a single sbatch script, i.e.
  # a single job. all the variables defined in the set will be replaced
  # with their value in the template (here, `template.sbatch`)
  set1:
      # variables can either be a list or a single value
      dataset: [datacomp, laion2b]
      model: [s32, m32]
      epochs: 1 
      logs: "logs/{set}"
      nodes: 1
      train_num_samples: [12_800_000]
      # each experiment will have a name, which we can define in any way
      # we want. 
      # it will be used in the template (`template.sbatch` here) but also to make 
      # the sbatch script name.
      name: "{set}_{dataset}_{model}_{epochs}"


```

## Step 3 : run all the jobs together with autorestart ability

First, we generate sbatch scripts:

`autoexperiment build config.yaml`

```bash
> ls sbatch
set1_datacomp_ViT-M-32_1.sbatch  set1_datacomp_ViT-S-32_1.sbatch  set1_laion2b_ViT-M-32_1.sbatch  set1_laion2b_ViT-S-32_1.sbatch
```


Then, we run all the jobs

```bash
> autoexperiment run config.yaml
Check if the job is freezing for set1_datacomp_ViT-M-32_1...
Check if the job is freezing for set1_laion2b_ViT-S-32_1...
Check if the job is freezing for set1_laion2b_ViT-M-32_1...
Check if the job is freezing for set1_datacomp_ViT-S-32_1...
Check if the job is freezing for set1_datacomp_ViT-M-32_1...
Check if the job is freezing for set1_laion2b_ViT-S-32_1...
Check if the job is freezing for set1_laion2b_ViT-M-32_1...
Check if the job is freezing for set1_datacomp_ViT-S-32_1...
Check if the job is freezing for set1_datacomp_ViT-M-32_1...
Check if the job is freezing for set1_laion2b_ViT-S-32_1...
Check if the job is freezing for set1_laion2b_ViT-M-32_1...
Termination string found for set1_datacomp_ViT-S-32_1, finishing
Termination string found for set1_datacomp_ViT-M-32_1, finishing
Termination string found for set1_laion2b_ViT-S-32_1, finishing
Termination string found for set1_laion2b_ViT-M-32_1, finishing
````

