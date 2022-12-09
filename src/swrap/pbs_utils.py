import os
# import subprocess

import sexec
from sexec import flush_print


def run_in_ssh(arg_list, init_dir=None):
    """
    Run command through ssh on PBS host machine.
    :param arg_list: list of arguments
    :param init_dir: if not None, then change to init_dir before running command
    """
    hostname = os.popen('hostname').read()
    pbs_host = os.environ['PBS_O_HOST']
    flush_print("Hostname: ", hostname, "PBS_O_HOST: ", pbs_host)

    if init_dir is None:
        command_list = ["ssh", pbs_host, *arg_list, "2>&1"]
    else:
        cdcom = "'cd " + init_dir + " ; " + " ".join(arg_list) + " 2>&1'"
        command_list = ["ssh", pbs_host, cdcom]

    command = " ".join(command_list)
    flush_print(command)
    return os.popen(command).read()


def qstat(arg_list):
    """
    Run qstat through ssh on PBS host machine.
    :param arg_list: optional arguments passed to qstat (e.g. -u <user_name>)

    Note: use qstat -f -Fjson for output in JSON
    """
    return run_in_ssh(["qstat", *arg_list])


def qsub(job_file, arg_list=None):
    """
    Run qsub through ssh on PBS host machine.
    :param job_file: PBS job file
    :param arg_list: additional arugments passed to qsub (e.g. -u <user_name>)
    """
    job_dir = os.path.dirname(job_file)
    if arg_list is None:
        return run_in_ssh(["qsub", job_file], init_dir=job_dir)
    else:
        return run_in_ssh(["qsub", *arg_list, job_file], init_dir=job_dir)
