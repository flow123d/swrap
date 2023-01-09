import os
import subprocess

import sexec
from sexec import flush_print


def prepare_mpiexec_launcher(pbs_job_aux_dir, pbs_job_id, sing_command_in_launcher):
    flush_print("creating launcher script...")
    launcher_path = os.path.join(pbs_job_aux_dir, "launcher_" + pbs_job_id + ".sh")
    launcher_log = '| adddate >> ' + os.path.join(pbs_job_aux_dir, 'launcher_' + pbs_job_id + '.log')
    # https://stackoverflow.com/questions/20572934/get-the-name-of-the-caller-script-in-bash-script
    launcher_lines = [
        '#!/bin/bash',
        '\n',
        'adddate() {',
        '    awk \'{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }\'',
        '}\n',
        'PARENT_COMMAND=$(ps -o args= $PPID)',
        'echo "" ' + launcher_log,
        'echo "parent call: $PARENT_COMMAND" ' + launcher_log,
        'echo $(hostname) ' + launcher_log,
        'echo $(pwd) ' + launcher_log,
        'echo "\$@: $@" ' + launcher_log,
        'echo "ssh parameters: $1 $2" ' + launcher_log,
        'echo "launcher command: ${@:3}" ' + launcher_log,
        'echo "singularity container: $SINGULARITY_NAME" ' + launcher_log,
        '\n',
        'ssh $1 $2 ' + sing_command_in_launcher + ' ${@:3}',
        'echo "ssh exit status: " $? ' + launcher_log
    ]
    with open(launcher_path, 'w') as f:
        f.write('\n'.join(launcher_lines))
    sexec.oscommand('chmod +x ' + launcher_path)
    return launcher_path


def prepare_mpiexec_runner(destination, mpiexec_path, node_file, launcher_path):
    mpiexec_args = [mpiexec_path, '-f', node_file, '-launcher-exec', launcher_path]
    flush_print("creating mpiexec and mpirun wrappers...")
    mpiexec_wrap = os.path.join(destination, "mpiexec")
    mpirun_wrap = os.path.join(destination, "mpirun")
    lines = [
        '#!/bin/bash',
        '\n',
        #'PARENT_COMMAND=$(ps -o args= $PPID)',
        #'echo "parent call: $PARENT_COMMAND" ',
        'echo "\$@: $@"',
        ' '.join(mpiexec_args) + ' $@',
    ]
    with open(mpiexec_wrap, 'w') as f:
        f.write('\n'.join(lines))
    with open(mpirun_wrap, 'w') as f:
        f.write('\n'.join(lines))
    sexec.oscommand('chmod +x ' + mpiexec_wrap)
    sexec.oscommand('chmod +x ' + mpirun_wrap)
    return mpiexec_args


def main():
    flush_print("================== smpiexec.py START ==================")
    current_dir = os.getcwd()
    args = sexec.arguments()

    # get debug variable
    debug = args.debug
    # get program and its arguments
    prog_args = args.prog[1:]

    # get program and its arguments, set absolute path
    image = sexec.process_image_path(args.image)

    ###################################################################################################################
    # Process node file and setup ssh access to given nodes.
    ###################################################################################################################

    flush_print("Hostname: ", os.popen('hostname').read())
    # mprint("os.environ", os.environ)

    pbs_job_id = os.environ['PBS_JOBID']
    flush_print("PBS job id: ", pbs_job_id)
    pbs_job_aux_dir =  os.path.join(current_dir, pbs_job_id + '_job')
    # create auxiliary job output directory
    os.makedirs(pbs_job_aux_dir, mode=0o775)
    
    # get nodefile, copy it to local dir so that it can be passed into container mpiexec later
    if debug:
        orig_node_file = "testing_hostfile"
    else:
        orig_node_file = os.environ['PBS_NODEFILE']
    node_file, node_names = sexec.copy_and_read_node_file(orig_node_file, pbs_job_aux_dir)

    # Get ssh keys to nodes and append it to $HOME/.ssh/known_hosts
    ssh_known_hosts_to_append = []
    if debug:
        # ssh_known_hosts_file = 'testing_known_hosts'
        ssh_known_hosts_file = 'xxx/.ssh/testing_known_hosts'
    else:
        assert 'HOME' in os.environ
        ssh_known_hosts_file = os.path.join(os.environ['HOME'], '.ssh/known_hosts')
    sexec.process_known_hosts_file(ssh_known_hosts_file, node_names)

    # mprint(os.environ)
    sexec.create_ssh_agent()

    ###################################################################################################################
    # Create Singularity container commands.
    ###################################################################################################################

    flush_print("assembling final command...")

    scratch_dir_path = None
    if 'SCRATCHDIR' in os.environ:
        scratch_dir_path = sexec.prepare_scratch_dir(args.scratch_copy, node_names)


    # A] process bindings, exclude ssh agent in launcher bindings
    common_bindings = ["/etc/ssh/ssh_config", "/etc/ssh/ssh_known_hosts", "/etc/krb5.conf"]
    bindings = [*common_bindings, os.environ['SSH_AUTH_SOCK']]
    # possibly add current dir to container bindings
    # bindings = bindings + "," + current_dir + ":" + current_dir
    bindings_in_launcher = [*common_bindings]
    if args.bind != "":
        bindings.append(args.bind)
        bindings_in_launcher.append(args.bind)

    if scratch_dir_path:
        bindings.append(scratch_dir_path)
        bindings_in_launcher.append(scratch_dir_path)

    sing_command = ['singularity', 'exec', '-B', ",".join(bindings), image]
    sing_command_in_launcher = ' '.join(['singularity', 'exec', '-B', ",".join(bindings_in_launcher), image])

    flush_print('sing_command:', *sing_command)
    flush_print('sing_command_in_ssh:', sing_command_in_launcher)

    # B] prepare node launcher script
    launcher_path = prepare_mpiexec_launcher(pbs_job_aux_dir, pbs_job_id, sing_command_in_launcher)

    # C] set mpiexec path inside the container
    # if container path to mpiexec is provided, use it
    # otherwise try to use the default
    mpiexec_path = "mpiexec"
    if args.mpiexec != "":
        mpiexec_path = args.mpiexec

    # test_mpiexec = os.popen(sing_command + ' which ' + 'mpiexec').read()
    # # test_mpiexec = os.popen('singularity exec docker://flow123d/geomop:master_8d5574fc2 which flow123d').read()
    # mprint("test_mpiexec: ", test_mpiexec)
    # if mpiexec_path == "":
    #     raise Exception("mpiexec path '" + mpiexec_path + "' not found in container!")

    # D] join mpiexec arguments
    mpiexec_args = prepare_mpiexec_runner(scratch_dir_path, mpiexec_path, node_file, launcher_path)
    # mpiexec_args = [mpiexec_path, '-f', node_file, '-launcher-exec', launcher_path]

    # F] join all the arguments into final singularity container command
    final_command_list = [*sing_command, *mpiexec_args, *prog_args]

    ###################################################################################################################
    # Final call.
    ###################################################################################################################
    if scratch_dir_path:
      flush_print("Entering SCRATCHDIR:", scratch_dir_path)
      os.chdir(scratch_dir_path)

    flush_print("current directory:", os.getcwd())
    # mprint(os.popen("ls -l").read())
    flush_print("final command:", *final_command_list)
    flush_print("=================== smpiexec.py END ===================")
    if not debug:
        flush_print("================== Program output START ==================")
        # proc = subprocess.run(final_command_list)
        final_command = " ".join(final_command_list)
        sexec.oscommand(final_command)

        flush_print("=================== Program output END ===================")
    # exit(proc.returncode)

if __name__ == "__main__":
    main()
