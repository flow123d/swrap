import os
import sys
import subprocess

import sexec
from sexec import flush_print
import smpiexec


"""
    Script which calls a program in prepared environment by swrap.
"""
if __name__ == "__main__":
    flush_print("================== smpiexec_step.py START ==================")
    parser = smpiexec.create_argparser()
    args = parser.parse_args()

    flush_print("Hostname: ", os.popen('hostname').read().strip())
    # mprint("os.environ", os.environ)

    pbs_job_aux_dir = os.path.join(os.environ['PBS_O_WORKDIR'], os.environ['PBS_JOBID'] + '_job')
    flush_print("PBS job aux dir: ", pbs_job_aux_dir)

    smpiexec_wrap = os.path.join(pbs_job_aux_dir, "smpiexec")
    flush_print("current directory:", os.getcwd())

    flush_print("=================== smpiexec_step.py END ===================")

    flush_print("=================== Program output START ===================")
    sexec.oscommand([smpiexec_wrap, *prog_args])
    flush_print("==================== Program output END ====================")
