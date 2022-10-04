# Run all integrated tests in PBAS, wait for them in parallel, report their results.
# Has to be run from testing/integrated where it is placed.

import threading
import subprocess
import os
import time
# substitute given template PBS script with given directory

# dictionary:
# {swrap_main} - main swrap executable, e.g. smpiexec
# {singulerity_image} - image to use, any specification accepted by the singularity
# {n_nodes} - number of nodes to run the test, for the comunnication tests we always use distinct node for each process
# {script_file} - command to run in the image
# ...

# make and submit PBS script, return the job ID

# run and wait for the job, 
def substitute_template(tmpl_file, config):
    """
    Sunstitute to the 'template' text file the 'config' dictionary,
    using standard python string substitution. Result is written into uniquely named file
    with name composed of the dict values.
    resulting file name is retunned
    """
    values_str = '_'.join([str(v) for v in config.values()])
    pbs_script=f"{tmpl_file}_{values_str}.sh"
    with open(tmpl_file, "r") as f:
        template = f.read()
    with open(pbs_script, 'w') as f:
        f.write(template.format(**config))
    return pbs_script

def job_finished(

def run(folder, name, image, n_nodes, timeout=5*60):
    os.chdir(folder)
    
    config = dict(
            swrap_main='smpiexec.py',
            singularity_image=image,
            n_nodes=n_nodes,
            script_file=name
        )
    pbs_script = substitute_template('../charon_pbs_template.sh', config)
    proc = subprocess.run(['qsub', pbs_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    job, stderr = proc.communicate()
    if proc.returncode != 0:
        raise Exception(f"qsub error code {proc.returncode} for script: {pbs_script}\nSTDERR:\n{stderr}")
    timeout_time = time.time() + timeout
    while  not job_finished(job):
        time.sleep(10)
        if time.time() > timeout_time:
            return False
    # TODO: somehow get result status of the processes and verify all are OK.
    return True
        
    

# converting singularity started 19.38
# seems to write into ${HOME}/singularity
# finished 19.44

def main():
    run('01_mpi4py', 'script.py', 'docker://flow123d/geomop-gnu', 2)

if __name__ == "__main__":
    main()
