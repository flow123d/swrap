# Run all integrated tests in PBAS, wait for them in parallel, report their results.
# Has to be run from testing/integrated where it is placed.
from queue import Queue, Empty
from functools import partial
import sys
import threading
import subprocess
import os
import time
import json
import re
import attrs
from concurrent.futures import ThreadPoolExecutor

# substitute given template PBS script with given directory

# dictionary:
# {swrap_main} - main swrap executable, e.g. smpiexec
# {singulerity_image} - image to use, any specification accepted by the singularity
# {n_nodes} - number of nodes to run the test, for the comunnication tests we always use distinct node for each process
# {script_file} - command to run in the image
# ...

# make and submit PBS script, return the job ID

# run and wait for the job,

class change_cwd:
    """
    Context manager that change CWD, to given relative or absolute path.
    """
    def __init__(self, path: str):
        self.path = path
        self.orig_cwd = ""

    def __enter__(self):
        if self.path:
            self.orig_cwd = os.getcwd()
            os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.orig_cwd:
            os.chdir(self.orig_cwd)


def name_from_arguments(tmpl_file, args):
    """
    PBS script named by the arguments.
    :param args:
    :return:
    """
    def strip(s):
        strip_before_slash = re.sub(r'^.*/', '', s)
        strip_after_space = re.sub(r'\s.*$', '', strip_before_slash)
        return strip_after_space

    values_str = '_'.join([strip(str(v)) for v in args])
    return f"{tmpl_file}_{values_str}.sh"

def substitute_template(tmpl_file, config):
    """
    Sunstitute to the 'template' text file the 'config' dictionary,
    using standard python string substitution. Result is written into uniquely named file
    with name composed of the dict values.
    resulting file name is retunned
    """
    #pbs_script = name_from_arguments(tmpl_file, config.values())
    args_hash = hash(config.values())
    pbs_script = f"pbs_{hex(args_hash)[2:8]}.sh"
    with open(tmpl_file, "r") as f:
        template = f.read()
    with open(pbs_script, 'w') as f:
        f.write(template.format(**config))
    return pbs_script




@attrs.define
class JobState:
    state: str          # single letter PBS code
    return_code: int    # PBS reported return code
    output_path: str    # path to redirected combined stdout and stderr
    timeout : bool = False

    def get_output(self):
        with open(self.output_path, 'r') as f:
            stdout = f.read()
        return stdout

@attrs.define
class Run:
    _counter = 0
    @classmethod
    def create(cls, *args, **kwargs):
        cls._counter += 1
        print(args, kwargs)
        return cls(cls._counter, *args, **kwargs)
    id: int
    command : str
    n_nodes: int = 1
    timeout: float = 5 * 60
    ref_return_code: int = 0
    image : str = attrs.field(kw_only=True)
    queue : Queue = attrs.field(kw_only=True)
    pool : ThreadPoolExecutor = attrs.field(kw_only=True)
    check_fn = attrs.field(kw_only=True)
    @check_fn.default
    def _make_check_fn(self):
        return self.default_check_fn


    def call_qstat(self, id_str):
        #return subprocess.run(['qstat', '-xf', '-F', 'json', id_str], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return subprocess.CompletedProcess([], returncode=0, stdout=
        """
        {"Jobs':{123:{"
            "job_state" : "F",
            "Output_Path" : ""
        }}}
        """)
    def call_qsub(self, pbs_script):
        #return subprocess.run(['qsub', pbs_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return subprocess.CompletedProcess([], returncode=0, stdout=f"{self.id}")

    def job_state(self, id_str):
        """
        (BULLSEYE)jan_brezina@charon:~/_testing/swrap/testing/integrated/01_mpi4py$ qstat -xf -F json 12860476.meta-pbs.metacentrum.cz
    {
        "timestamp":1664911414,
        "pbs_version":"19.0.0",
        "pbs_server":"meta-pbs.metacentrum.cz",
        "Jobs":{
            "12860476.meta-pbs.metacentrum.cz":{
                "Job_Name":"swrap_01",
                "Job_Owner":"jan_brezina@META",
                "job_state":"R",
                "queue":"charon_2h",
                "server":"meta-pbs.metacentrum.cz",
                "Checkpoint":"u",
                "ctime":"Tue Oct  4 21:23:20 2022",
                "Error_Path":"charon.nti.tul.cz:/storage/liberec3-tul/home/jan_brezina/_testing/swrap/testing/integrated/01_mpi4py/swrap_01.e12860476",
                "exec_host":"charon24/0*2+charon21/0*2",
                "exec_host2":"charon24.nti.tul.cz:15002/0*2+charon21.nti.tul.cz:15002/0*2",
                "exec_vnode":"(charon24:ncpus=2:mem=4194304kb)+(charon21:ncpus=2:mem=4194304kb)",
                "Hold_Types":"n",
                "Join_Path":"oe",
                "Keep_Files":"n",
                "Mail_Points":"a",
                "mtime":"Tue Oct  4 21:23:33 2022",
                "Output_Path":"charon.nti.tul.cz:/storage/liberec3-tul/home/jan_brezina/_testing/swrap/testing/integrated/01_mpi4py/swrap_01.o12860476",
                "Priority":0,
                "qtime":"Tue Oct  4 21:23:20 2022",
                "Rerunable":"True",
                "Resource_List":{
                    "mem":"8gb",
                    "mpiprocs":4,
                    "ncpus":4,
                    "nodect":2,
                    "place":"scatter",
                    "select":"2:ncpus=2:mem=4gb:mpiprocs=2:ompthreads=1",
                    "soft_walltime":"00:01:00",
                    "walltime":"00:01:00"
                },
                "stime":"Tue Oct  4 21:23:33 2022",
                "Shell_Path_List":"/bin/bash",
                "substate":41,
                "Variable_List":{
                    "PBS_O_HOME":"/storage/liberec3-tul/home/jan_brezina",
                    "PBS_O_LANG":"en_US.UTF-8",
                    "PBS_O_LOGNAME":"jan_brezina",
                    "PBS_O_PATH":"/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/software/meta-utils/public:/usr/bin",
                    "PBS_O_SHELL":"/bin/bash",
                    "PBS_O_WORKDIR":"/storage/liberec3-tul/home/jan_brezina/_testing/swrap/testing/integrated/01_mpi4py",
                    "PBS_O_SYSTEM":"Linux",
                    "PBS_O_QUEUE":"charon_2h",
                    "PBS_O_HOST":"charon.nti.tul.cz",
                    "PBS_RESC_MEM":4294967296,
                    "TORQUE_RESC_MEM":4294967296,
                    "PBS_NUM_PPN":2,
                    "PBS_NCPUS":2,
                    "TORQUE_RESC_PROC":2,
                    "PBS_NGPUS":0,
                    "PBS_RESC_TOTAL_MEM":8589934592,
                    "TORQUE_RESC_TOTAL_MEM":8589934592,
                    "PBS_RESC_TOTAL_PROCS":4,
                    "TORQUE_RESC_TOTAL_PROCS":4,
                    "PBS_NUM_NODES":2,
                    "PBS_RESC_TOTAL_WALLTIME":60,
                    "TORQUE_RESC_TOTAL_WALLTIME":60
                },
                "comment":"Job run at Tue Oct 04 at 21:23 on (charon24:ncpus=2:mem=4194304kb)+(charon21:ncpus=2:mem=4194304kb)",
                "etime":"Tue Oct  4 21:23:20 2022",
                "run_count":1,
                "eligible_time":"00:00:00",
                "Submit_arguments":"job.sh",
                "project":"_pbs_project_default",
                "Submit_Host":"charon.nti.tul.cz",
                "credential_id":"jan_brezina@META",
                "credential_validity":"Wed Oct  5 21:19:59 2022"
            }
        }
    }

        :return:
        """
        # print(" ".join(['qstat', '-xf', '-F json', id_str]))
        proc = self.call_qstat(id_str)
        if proc.returncode != 0:
            raise Exception(f"qstat error code {proc.returncode}:\nSTDERR:\n{proc.stderr.decode('utf-8')}")
        # print(proc.stdout)
        stat = json.loads(proc.stdout)
        job_stat = next(iter(stat['Jobs'].values()))

        # assert job_stat['job_state'] != 'M'

        return_code = job_stat.get('Exit_status', None)  # ??
        job_stdout_path = job_stat['Output_Path'].split(':')[1]
        #job_stderr_path = job_stat['Error_Path']

        # Using -j oe, both merged to standard output. Need only to extract that.
        state = JobState(job_stat['job_state'], return_code, job_stdout_path)
        return state

    def pbs_script(self):
        script_dir = os.path.abspath(os.path.dirname(__file__))
        config = dict(
            swrap_main=os.path.join(script_dir, '../../src/swrap/smpiexec.py'),
            singularity_image=self.image,
            n_nodes=self.n_nodes,
            script_file=self.command
        )
        return substitute_template('../charon_pbs_template.sh', config)

    def pbs_submit(self):
        self.pbs_script = self.pbs_script()
        proc = call_qsub(self.pbs_script)
        if proc.returncode != 0:
            raise Exception(
                f"qsub error code {proc.returncode} for script: {self.pbs_script}\nSTDERR:\n{proc.stderr.decode('utf-8')}")
        job_id = proc.stdout.decode('utf-8').strip(' \n\t')
        self.short_id = re.sub(r'\..*$', '', job_id)
        print(f"[{self.id}] Queued {self.short_id}, {self.pbs_script}: {self.command} @ {self.n_nodes}")
        timeout_time = time.time() + timeout
        while True:
            self.state = job_state(job_id)
            assert self.state.state != 'M'
            if self.state.state == 'F':
                break
            if time.time() > timeout_time:
                self.state.timeout = True
                break
            time.sleep(10)
        if self.state.timeout:
            err_msg = "Timeout."
        else :
            err_msg = self.check_fn(self.state, ref_return_code)
        self.summary(err_msg)
        print(f"[{self.state}]", end=" ")

# def progress(command, image, n_nodes, hash, job, status, time):
#     str_time = time.strftime('%H:%M:%S', time.gmtime(wall_time))
#     print(f"\bTEST {command} IN {image}; n={n_nodes} | {hash}, {job}, {status}, {str_time}\n")

    def summary(self, err_msg):
        if err_msg is None:
            result = "Succeed:"
            err_msg = ""
        else:
            if self.state.timeout:
                result = "Timed out:"
            else:
                result = "Failed:"
            err_msg = f"{err_msg}\n{self.state.get_output()}"
        msg = f"[{self.id}] {result} {self.short_id}, {self.pbs_script}: {self.command} @ {self.n_nodes}\n{err_msg}"
        self.queue.put((self.id, msg))

    @staticmethod
    def default_check_fn(state, ref_return_code):
        """
        Check state
        :param state:
        :return:
        """
        if state.return_code != ref_return_code:
            return f"Error: return code {state.return_code} != {ref_return_code}"
        return None


def run_thread(*args, **kwargs):
    r = Run.create(*args, **kwargs)
    r.pool.submit(r.pbs_submit)

def run_common(**config):
    def r(*args, **kwargs):
        config.update(kwargs)
        run_thread(*args, **config)
    return r

def report(print_queue):
    messages = []
    while True:
        try:
            messages.append(print_queue.get_nowait())
            print_queue.task_done()
        except Empty:
            break
    for id, msg in sorted(messages):
        print(msg)

# TODO: report success / failure
def main():
    print_queue = Queue()
    with ThreadPoolExecutor() as p:
        image = 'docker://flow123d/geomop-gnu:2.0.0'
        r = partial(run_thread, queue=print_queue, pool=p, image=image)
        with change_cwd('01_mpi4py'):
            r('ls -l',  n_nodes=2)
            r('script.py', n_nodes=2)

    report(print_queue)

if __name__ == "__main__":
    main()
