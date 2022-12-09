import os
import sys
import time

# setting path
sys.path.append('../../../src/swrap')
import sexec, pbs_utils
from sexec import flush_print

# test QSTAT
res = pbs_utils.qstat(["-u", "pavel_exner"])
flush_print("qstat res: ", res)

# test QSTAT with JSON output
res = pbs_utils.qstat(["-f", "-Fjson", "-u", "pavel_exner"])
flush_print("qstat res: ", res)

# test QSUB
# after ssh user end up in HOME, use abs paths
job_file = os.path.abspath("../test_flow123d/test_flow123d_jobX.sh")
# res = pbs_utils.qsub(job_file)
res = pbs_utils.qsub(job_file, ["-u", "pavel_exner"])
flush_print("qsub res: ", res)

time.sleep(5)

# test QSTAT - there should be new job waiting in a queue
res = pbs_utils.qstat(["-u", "pavel_exner"])
flush_print("qstat res: ", res)
