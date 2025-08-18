import os
import re
import sys
import time

from subprocess import call, check_output, DEVNULL, CalledProcessError
from dataclasses import dataclass
import asyncio

cmd_check_job_in_queue = "squeue -j {job_id}"
cmd_check_job_running = "squeue -j {job_id} -t R"
cmd_check_job_id_by_name = "squeue --me -n '{job_name}' --format %i"


class JobLimitsManager:
    def __init__(self, max_jobs=None):
        self.max_jobs = max_jobs
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.lock)
        
        # Single counter: total jobs submitted to SLURM (any state)
        self.jobs_submitted = 0
        
    async def wait_for_slot(self):
        """Wait until we can submit a new job to SLURM"""
        if not self.max_jobs:
            return  # No limit set
            
        async with self.condition:
            while self.jobs_submitted >= self.max_jobs:
                await self.condition.wait()
    
    async def job_submitted(self):
        """Called when we successfully submit a job to SLURM"""
        async with self.condition:
            self.jobs_submitted += 1
    
    async def job_finished(self):
        """Called when job is completely done and removed from SLURM"""
        async with self.condition:
            if self.jobs_submitted > 0:
                self.jobs_submitted -= 1
            self.condition.notify_all()  # Wake waiting jobs

def manage_jobs_forever(jobs, max_jobs:int=None, verbose=0):
    """
    Manage a list of jobs forever, relaunching them if they are frozen or not running anymore.
    """
    limits_manager = JobLimitsManager(max_jobs) if max_jobs is not None else None
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[
        manage_job(job, limits_manager, verbose=verbose) for job in jobs
    ]))


async def manage_job(job, limits_manager=None, verbose=0):
    """
    Manage a single job, relaunching it if it is frozen or not running anymore.
    """
    cmd = job.cmd
    output_file = job.output_file
    check_interval_secs = job.check_interval_secs
    start_condition_cmd = job.start_condition_cmd
    termination_str = job.termination_str
    termination_cmd = job.termination_cmd
    stderr = sys.stderr if verbose >= 2 else DEVNULL

    # Get job id from the queue based on the name
    data = check_output(cmd_check_job_id_by_name.format(job_name=job.name), shell=True, stderr=stderr).decode()
    job_ids = [line for line in data.split("\n") if re.match('[0-9]+', line)]

    if len(job_ids) == 0:
        existing_job_id = None
    elif len(job_ids) == 1:
        # only extract job id if there are no duplicate names
        existing_job_id = int(job_ids[0])
    else: 
        # more than one job found with same name
        # TODO can fail if different autoexp sessions use same names, one must ensure that it is not the case!
        print(f"Found duplicate jobs with same name: '{job.name}': {job_ids}. Please fix your YAML config to have only unique names.")
        return

    while True:
        if check_if_done(output_file, termination_str=termination_str, termination_cmd=termination_cmd, verbose=verbose):
            if limits_manager:
                await limits_manager.job_finished()
            print(f"Job '{job.name}' is finished")
            return
        if start_condition_cmd:
            # if start condition is provided, check it first by running it in a shell
            # if it outputs 0 (false), do not start the job and wait and check again, 
            # otherwise, start the job
            if verbose:
                print(f"Checking start condition of {job.name}...")
            value = int(check_output(start_condition_cmd, shell=True, stderr=stderr))
            if value != 1:
                if verbose:
                    print(f"Start condition returned {value}, not starting for {job.name}, retrying again in {check_interval_secs//60} mins.")
                await asyncio.sleep(check_interval_secs)
                continue

        if existing_job_id is not None:
            if verbose:
                print(f"Resume {job.name} from job id: {existing_job_id}")
            job_id = existing_job_id
            existing_job_id = None
            
            # Count existing job toward our limits
            if limits_manager:
                await limits_manager.job_submitted()
        else:
            # Wait for job slot before launching
            if limits_manager:
                await limits_manager.wait_for_slot()
                if verbose:
                    print(f"Slot available, launching job for {job.name}")
            
            # launch job
            try:
                output = check_output(cmd, shell=True, stderr=stderr).decode()
                if verbose:
                    print(f"Launch a new job for {job.name}")
                # get job id
                job_id = get_job_id(output)
                if job_id is not None and limits_manager:
                    await limits_manager.job_submitted()
            except CalledProcessError:
                job_id = None
            
            if job_id is None:
                if verbose:
                    print(f"Cannot find job id in: {output} for {job.name}")
                    print(f"Retrying again in {check_interval_secs//60} mins...")
                await asyncio.sleep(check_interval_secs)
                continue

        if verbose:
            print(f"Current job id for {job.name}: {job_id}")
        while True:
            # Infinite-loop, check each `check_interval_secs` whether job is present
            # in the queue, then, if present in the queue check if it is still running
            # and not frozen. The job is relaunched when it is no longuer running or
            # frozen. Then the same process is repeated.

            try:
                data = check_output(cmd_check_job_in_queue.format(job_id=job_id), shell=True, stderr=stderr).decode()
            except Exception as ex:
                # Exception after checking, which means that the job id no longer exists.
                # In this case, we wait and relaunch, except if termination string is found
                if limits_manager:
                    await limits_manager.job_finished()
                if verbose:
                    print(ex)
                if check_if_done(output_file, termination_str=termination_str, termination_cmd=termination_cmd, verbose=verbose):
                    print(f"Job '{job.name}' is finished")
                    return
                # Job will be relaunched 
                if verbose:
                    print(f"Retrying again in {check_interval_secs//60} mins for {job.name}...")
                await asyncio.sleep(check_interval_secs)
                break
            # if job is not present in the queue, relaunch it directly, except if termination string is found
            if str(job_id) not in data:
                if limits_manager:
                    await limits_manager.job_finished()
                if check_if_done(output_file, termination_str=termination_str, termination_cmd=termination_cmd, verbose=verbose):
                    print(f"Job '{job.name}' is finished")
                    return
                # Job will be relaunched directly
                break
            # Check first if job is specifically on a running state (to avoid the case where it is on pending state etc)
            data = check_output(cmd_check_job_running.format(job_id=job_id), shell=True, stderr=stderr).decode()
            if str(job_id) in data:
                # job on running state
                print(f"Job '{job.name}' is running...(ID:{job_id})")
                if not os.path.exists(output_file):
                    if verbose:
                        print(f"Output file not found for {job.name}, waiting...")
                    await asyncio.sleep(check_interval_secs)
                    continue
                if verbose:
                    print(f"Check if the job is freezing for {job.name}...")
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
                        print(f"Job frozen for {job.name}, stopping the job then restarting it")
                    call(f"scancel {job_id}", shell=True, check=True)
                    if limits_manager:
                        await limits_manager.job_finished()
                    break
            else:
                # job not on running state, so it is present in the queue but in a different state
                # In this case, we wait, then check again if the job is still on the queue
                await asyncio.sleep(check_interval_secs)
 

def check_if_done(logfile, termination_str='', termination_cmd='', verbose=0):
    return (
        (os.path.exists(logfile) and (termination_str != "") and re.search(termination_str, open(logfile).read())) or 
        (termination_cmd and int(check_output(termination_cmd, shell=True, stderr=sys.stderr if verbose >=2 else DEVNULL)) == 1)
    )

def get_file_content(output_file):
    return open(output_file, errors='ignore').read()

def get_job_id(s):
    try:
        return int(re.search("Submitted batch job ([0-9]+)", s).group(1))
    except Exception:
        return None
