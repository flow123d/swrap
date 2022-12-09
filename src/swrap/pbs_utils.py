import os
import subprocess

import sexec
from sexec import flush_print


def run_in_ssh(*args):
    hostname = os.popen('hostname').read()
    pbs_host = os.environ['PBS_O_HOST']
    flush_print("Hostname: ", hostname, "PBS_O_HOST: ", pbs_host)

    command_list = ["ssh", "-x", pbs_host, *args]
    command = " ".join(command_list)
    flush_print(command)
    return os.popen(command).read()


def qstat(*args):
    # use qstat -f -Fjson for output in JSON
    command_list = ["qstat", *args]
    return run_in_ssh(command_list)


def qsub(*args):
    # use qstat -f -Fjson for output in JSON
    command_list = ["qsub", *args]
    return run_in_ssh(command_list)
