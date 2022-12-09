import os
# import subprocess

import sexec
from sexec import flush_print


def run_in_ssh(arg_list, init_dir=None):
    hostname = os.popen('hostname').read()
    pbs_host = os.environ['PBS_O_HOST']
    flush_print("Hostname: ", hostname, "PBS_O_HOST: ", pbs_host)

    if init_dir is None:
        command_list = ["ssh", pbs_host, *arg_list]
    else:
        cdcom = "'cd " + init_dir + " ; " + " ".join(arg_list) + "'"
        command_list = ["ssh", pbs_host, cdcom]

    command = " ".join(command_list)
    flush_print(command)
    return os.popen(command).read()


def qstat(arg_list):
    # use qstat -f -Fjson for output in JSON
    return run_in_ssh(["qstat", *arg_list])


def qsub(job_file, arg_list=None):
    job_dir = os.path.dirname(job_file)
    if arg_list is None:
        return run_in_ssh(["qsub", job_file], init_dir=job_dir)
    else:
        return run_in_ssh(["qsub", *arg_list, job_file], init_dir=job_dir)
