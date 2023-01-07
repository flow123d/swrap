import os
# import subprocess

from swrap.utils import flush_print, oscommand
from pathlib import Path

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


def make_wrapper(dir, cmd, host_addr, binds):
    host_addr=host_addr.strip("\n")
    bind_replace="""
    PWD_REL="${{PWD#{1}}}"
    if [ "$PWD_REL" != "$PWD" ]
    then
        PWD_HOST="{0}$PWD_REL"
    fi
    """
    Path(dir).mkdir(parents=True, exist_ok=True)
    #pwd_replace_binds = [bind_replace.format(host_dir, cont_dir) for host_dir, cont_dir in binds]
    # TODO: support bindings with path different on host and container
    pwd_replace_binds=[]
    content=[
        "#!/bin/bash",
        "set -x",
        "PWD=\"`pwd`\"",
        "PWD_HOST=\"${PWD}\"",
        *pwd_replace_binds,
        f'ssh {host_addr} "cd \'$PWD_HOST\'; {cmd} $*"'
    ]
    cmd_path = os.path.join(dir, cmd)
    with open(cmd_path, "w") as f:
        f.write("\n".join(content))
    os.chmod(cmd_path, 0o777)

def make_pbs_wrappers(dir, binds):
    host_addr = os.environ.get('PBS_O_HOST', None)
    if host_addr is None:
        host_addr = oscommand('hostname')
    make_wrapper(dir, 'qstat', host_addr, binds)
    make_wrapper(dir, 'qsub', host_addr, binds)
