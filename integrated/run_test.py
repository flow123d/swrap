"""
Execution of the swrap integrated tests.

Usage:
    python3 run_test.py 
    python3 run_test.py <named test case> <case 2> ...
    python3 run_test.py <test directory>
    
    Without parameters current directory is tested covering all cases from 'config.yaml' file.
    If in a directory with a 'config.yaml' the parameter is interpreted as the name(s) of the test cases to run.
    If in a directory without 'config.yaml' the parameter is interpreted as name(s) of the directories to run in.
"""
import sys
from typing import *
from dataclasses import dataclass
from queue import Queue, Empty
from functools import partial
import subprocess
import os
import time
import json
import re
import ctypes
import yaml
from concurrent.futures import ThreadPoolExecutor

test_script_dir = os.path.abspath(os.path.dirname(__file__))


# substitute given template PBS script with given directory

# dictionary:
# {swrap_main} - main swrap executable, e.g. smpiexec
# {singulerity_image} - image to use, any specification accepted by the singularity
# {n_nodes} - number of nodes to run the test, for the comunnication tests we always use distinct node for each process
# {script_file} - command to run in the image
# ...

# make and submit PBS script, return the job ID

# run and wait for the job,

############################################ General tools
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


def dict_merge(a, b):
    c = a.copy()
    c.update(b)
    return c


def hash_all(x):
    if type(x) is dict:
        x = list(x.items())
    if isinstance(x, (list, tuple)):
        return hash(tuple((hash_all(i) for i in x)))

    return hash(x)



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
    #print(pbs_script, list(config.values()))
    with open(tmpl_file, "r") as f:
        template = f.read()
    return template.format(**config)



@dataclass
class JobState:
    state: str          # single letter PBS code
    return_code: int    # PBS reported return code
    output_path: str    # path to redirected combined stdout and stderr
    timeout : bool = False

    def get_output(self):
        with open(self.output_path, 'r') as f:
            stdout = f.read()
        return stdout

def check_timeout(state: JobState):
    if state.timeout:
        return f"Error: reached walltime limit."

def check_return_code(state: JobState, ref_return_code: int) -> str:
    """
    Check the return code == ref_return_code
    """
    if state.return_code != ref_return_code:
        return f"Error: return code {state.return_code} != {ref_return_code}"


def check_find_stdout_regex(state: JobState, regex: str) -> str:
    """
    Check if output contains regular expression.
    """
    if re.search(regex, state.get_output()) is None:
        return f"Error: output don't contain regular expression: {regex}"


# def as_list(x):
#     if type(x) is list:
#         return x
#     else:
#         return [x]
#
def get_check_fn(name):
    try:
        this_mod = sys.modules[__name__]
        return getattr(this_mod, name)
    except AttributeError:
        raise AttributeError("Unknown check function: ", name)

def normalize_args(args) -> Tuple[Any]:
    if args is None:
        return ()
    elif type(args) is list: # tuple can result from YAML
        return tuple(args)
    else:
        # single value
        return (args,)

def parse_time(walltime: str) -> int:
    """
    HH:MM:SS -> time in seconds
    """
    h,m,s = (time.strptime(walltime, '%H:%M:%S'))[3:6]
    return 60 * (60 * h + m) + s


class Run:
    _counter = 0
    _default_config=dict(
            name='pbs_script',
            # base name of the pbs_script (and workdir possibly)
            image='docker://flow123d/geomop-gnu:2.0.0',
            # image to run in
            wrapper='smpiexec',
            # wrapper to test, currently just mpiexec
            # located in src/swrap folder
            pbs_select=1,
            # PBS select option: "-l select={pbs_select}"
            pbs_place='scatter',
            # PBS place option: "-l place={pbs_place}"; default = scatter
            pbs_queue='charon_2h',
            # PBS queue to use
            pbs_walltime='00:10:00',
            # PBS walltime, HH:mm:ss
            checkers={'check_return_code': [0]}
    )


    def __init__(self, queue: Queue, config: Dict[str, Any]):
        """
        TODO:
        - modify
        :param config:
        :return:
        """

        Run._counter += 1
        self.id = Run._counter
        config['wrapper'] = os.path.join(test_script_dir, "../src/swrap/", config['wrapper'])
        self.config = dict_merge(Run._default_config, config)

        self.checkers = [(get_check_fn(fn), normalize_args(args))  for fn, args in config['checkers'].items()]
        self.checkers.insert(0, (check_timeout, ()))
        self.timeout = parse_time(config['pbs_walltime'])
        self.cwd = os.getcwd()
        self.queue = queue

        # internal
        self.pbs_script: str = ""      # generated pbs_script
        self.short_id : str = ""        # shortened job ID
        self.state : JobState = None    # results of the run

    def mock_qstat(self, id_str):
        # Mockup implementation:
        sout = """
            {"Jobs":{"123":{ "job_state" : "F", "Output_Path" : "meta:example_qsub_json_output.json" }}}
         """.encode('utf-8')
        return subprocess.CompletedProcess([], returncode=0, stdout=sout)

    def call_qstat(self, id_str):
        # return self.mock_qstat(id_str)
        return subprocess.run(['qstat', '-xf', '-F', 'json', id_str], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def mock_qsub(self, pbs_script):
        sout = f"{self.id}".encode('utf-8')
        return subprocess.CompletedProcess([], returncode=0, stdout=sout)

    def call_qsub(self, pbs_script):
        # return self.mock_qsub(pbs_script)
        return subprocess.run(['qsub', self.abs_pbs_script], cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


    def job_state(self, id_str: str) -> JobState:
        """
        Run qstat and extracts essential informations.
        :return:
        """
        # print(" ".join(['qstat', '-xf', '-F json', id_str]))
        proc = self.call_qstat(id_str)
        if proc.returncode != 0:
            raise Exception(f"qstat error code {proc.returncode}:\nSTDERR:\n{proc.stderr.decode('utf-8')}")
        # print(proc.stdout)
        stat = json.loads(proc.stdout)
        job_stat = next(iter(stat['Jobs'].values()))

        assert job_stat['job_state'] != 'M'

        return_code = job_stat.get('Exit_status', None)  # ??
        job_stdout_path = job_stat['Output_Path'].split(':')[1]
        #job_stderr_path = job_stat['Error_Path']

        # Using -j oe, both merged to standard output. Need only to extract that.
        state = JobState(job_stat['job_state'], return_code, job_stdout_path)
        return state

    def xpbs_script(self):
        template = os.path.join(test_script_dir, 'charon_pbs_template.sh')
        script_content =  substitute_template(template , self.config)
        
        
        name_base = self.config['name']
        args_hash = ctypes.c_size_t(hash_all(self.config)).value
        script_file = f"{name_base}_{hex(args_hash)[2:8]}.sh"
        abs_script = os.path.join(self.cwd, script_file)
        with open(abs_script, 'w') as f:
            f.write(script_content)
        return abs_script, script_file

    def pbs_submit(self):
        """ TODO: make it work from any directory:
        0. we must safe current dir in Run constructor
        1. template must by specified as abs path
        2. pbs_script must be produced at abs_path
        3. qsub must be executed in the path of the pbs_script
        """
        print("Print submit:", self.cwd, self.config)
        self.abs_pbs_script, self.pbs_script = self.xpbs_script()
        proc = self.call_qsub(self.abs_pbs_script)
        if proc.returncode != 0:
            raise Exception(
                f"qsub error code {proc.returncode} for script: {self.pbs_script}\nSTDERR:\n{proc.stderr.decode('utf-8')}")
        self.job_id = proc.stdout.decode('utf-8').strip(' \n\t')
        
        self.short_id = re.sub(r'\..*$', '', self.job_id)
        print(f"[{self.id}] Queued {self.short_id}, {self.pbs_script}: {self.config['command']} ")

        timeout_time = time.time() + self.timeout
        while True:
            self.state = self.job_state(self.job_id)
            assert self.state.state != 'M'
            if self.state.state == 'F':
                break
            if time.time() > timeout_time:
                self.state.timeout = True
                break
            time.sleep(10)
        err_msg = None
        for check_fn, args in self.checkers:
            err_msg = check_fn(self.state, *args)
            if err_msg is not None:
                break
        self.summary(err_msg)
        print(f"[{self.id}] done")
        
# def progress(command, image, n_nodes, hash, job, status, time):
#     str_time = time.strftime('%H:%M:%S', time.gmtime(wall_time))
#     print(f"\bTEST {command} IN {image}; n={n_nodes} | {hash}, {job}, {status}, {str_time}\n")

    def summary(self, err_msg):
        if err_msg is None:
            result = "Succeed:"
            err_msg = ""
            success = True
        else:
            if self.state.timeout:
                result = "Timed out:"
            else:
                result = "Failed:"
            err_msg = f"{err_msg}\n{self.state.get_output()}"
            success = False
        msg = f"[{self.id}] {result} {self.short_id}, {self.pbs_script}: {self.config['command']} \n{err_msg}"
        self.queue.put((self.id, msg, success))


def report(print_queue):
    messages = []
    all_success = True
    while True:
        try:
            messages.append(print_queue.get_nowait())
            print_queue.task_done()
        except Empty:
            break
    for id, msg, success in sorted(messages):
        print(msg)
        if not success:
            all_success = False
    return all_success


def parse_arguments():
    """
    List of pairs (dir, case) to possibly test.
    """
    if len(sys.argv) == 1:
        return [(os.getcwd(), None)]
    
    cases = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            abs_dir = os.path.abspath(os.path.join(os.getcwd(), a))
            cases.append((abs_dir, None))
        else:
            cases.append((os.getcwd(), a))
    return cases

def get_dirs():
    """
    get directory to run in either given or current
    """
    if len(sys.argv) > 1:
        dir = sys.argv[1]
        os.chdir(dir)
    else:
        dir = "."
    return dir

def read_cases():
    with open("config.yaml", "r") as f:
        content = yaml.safe_load(f)
    common_dict = content['common']
    cases = [dict_merge(common_dict, c) for c in content['cases']]
    return cases

def submit_case(pool, futures, print_queue, case):
    print("Prepare case: ", case)
    run = Run(print_queue, case)
    futures.append(pool.submit(run.pbs_submit))
    print(20*"=", "\n")
    
    
# TODO: report success / failure
def main():
    dir_cases = parse_arguments()
    print_queue = Queue()
    futures = []
    with ThreadPoolExecutor() as p:
        for d, case_name in dir_cases:
            os.chdir(d)
            cases = read_cases()
            if case_name is not None:
                cases = [x for x in cases if x.get('name', "") == case_name]
            for the_case in cases:
                submit_case(p, futures, print_queue, the_case)

        for f in futures:
            print(f.result())
        all_success = report(print_queue)
        if not all_success:
            exit(1)


if __name__ == "__main__":
    main()
