import os
import re
import time
from subprocess import call, check_output
from dataclasses import dataclass
import asyncio

cmd_check_job_in_queue = "squeue -j {job_id}"
cmd_check_job_running = "squeue -j {job_id} -t R"


@dataclass
class Job:
    cmd: str
    output_file_template: str = "slurm-{job_id}.out"
    check_interval_secs: int = 60*15
    start_condition: str = ""
    termination_str: str = ""
    verbose: bool = True
    resume_job_id: int = None

   
def manage_jobs_forever(jobs):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[manage_job(job) for job in jobs]))

async def manage_job(job):
    cmd = job.cmd
    output_file_template = job.output_file_template
    check_interval_secs = job.check_interval_secs
    start_condition = job.start_condition
    termination_str = job.termination_str
    verbose = job.verbose
    resume_job_id = job.resume_job_id
    while True:

        if start_condition:
            if verbose:
                print("Checking start condition...")
            if int(check_output(start_condition, shell=True)) == 0:
                if verbose:
                    print(f"Start condition returned 0, not starting, retrying again in {check_interval_secs//60} mins.")
                await asyncio.sleep(check_interval_secs)
                continue

        if verbose:
            print("Launch a new job")
            print(cmd)
        if resume_job_id is not None:
            job_id = resume_job_id
            resume_job_id = None
        else:
            # launch job
            output = check_output(cmd, shell=True).decode()
            # get job id
            job_id = get_job_id(output)
            if job_id is None:
                if verbose:
                    print("Cannot find job id in:")
                    print('"'+output+'"')
                    print(f"Retrying again in {check_interval_secs//60} mins...")
                await asyncio.sleep(check_interval_secs)
                continue

        if verbose:
            print("Current job ID:", job_id)
        while True:
            # Infinite-loop, check each `check_interval_secs` whether job is present
            # in the queue, then, if present in the queue check if it is still running
            # and not frozen. The job is relaunched when it is no longuer running or
            # frozen. Then the same process is repeated.

            try:
                data = check_output(cmd_check_job_in_queue.format(job_id=job_id), shell=True).decode()
            except Exception as ex:
                # Exception after checking, which means that the job id no longer exists.
                # In this case, we wait and relaunch, except if termination string is found
                if verbose:
                    print(ex)
                if check_if_done(output_file_template.format(job_id=job_id), termination_str):
                    if verbose:
                        print("Termination string found, finishing")
                    return
                if verbose:
                    print(f"Retrying again in {check_interval_secs//60} mins...")
                await asyncio.sleep(check_interval_secs)
                break
            # if job is not present in the queue, relaunch it directly, except if termination string is found
            if str(job_id) not in data:
                if check_if_done(output_file_template.format(job_id=job_id), termination_str):
                    if verbose:
                        print("Termination string found, finishing")
                    return
                break
            # Check first if job is specifically on a running state (to avoid the case where it is on pending state etc)
            data = check_output(cmd_check_job_running.format(job_id=job_id), shell=True).decode()
            if str(job_id) in data:
                # job on running state
                output_file = output_file_template.format(job_id=job_id)
                if not os.path.exists(output_file):
                    if verbose:
                        print("Output file not found, waiting...")
                    await asyncio.sleep(check_interval_secs)
                    continue
                if verbose:
                    print("Check if the job is freezing...")
                # if job is on running state, check the output file
                output_data_prev = get_file_content(output_file)
                # wait few minutes
                await asyncio.sleep(check_interval_secs)
                # check again the output file
                output_data = get_file_content(output_file)
                # if the file did not change, then it is considered
                # to be frozen
                # (make sure there are is output before checking)
                if output_data and output_data_prev and output_data == output_data_prev:
                    if verbose:
                        print("Job frozen, stopping the job then restarting it")
                    call(f"scancel {job_id}", shell=True)
                    break
            else:
                # job not on running state, so it is present in the queue but in a different state
                # In this case, we wait, then check again if the job is still on the queue
                await asyncio.sleep(check_interval_secs)
 

def check_if_done(logfile, termination_str):
    return os.path.exists(logfile) and (termination_str != "") and re.search(termination_str, open(logfile).read())

def get_file_content(output_file):
    return open(output_file).read()

def get_job_id(s):
    try:
        return int(re.search("Submitted batch job ([0-9]+)", s).group(1))
    except Exception:
        return None