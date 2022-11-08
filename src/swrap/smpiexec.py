import os
import sys
import shutil
import argparse
import subprocess

from argparse import RawTextHelpFormatter

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from tools import flush_print, oscommand, create_ssh_agent, create_known_hosts_file


def arguments():
    parser = argparse.ArgumentParser(
        description='Auxiliary executor for parallel programs running inside (Singularity) container under PBS.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true',
                        help='use testing files and print the final command')
    parser.add_argument('-i', '--image', type=str, required=True,
                        help='Singularity SIF image or Docker image (will be converted to SIF)')
    parser.add_argument('-B', '--bind', type=str, metavar="PATH,...", default="", required=False,
                        help='comma separated list of paths to be bind to Singularity container')
    parser.add_argument('-m', '--mpiexec', type=str, metavar="PATH", default="", required=False,
                        help="path (inside the container) to mpiexec to be run, default is 'mpiexec'")
    parser.add_argument('-s', '--scratch_dir', type=str, metavar="PATH", default="", required=False,
                        help='''
                        directory path, where SCRATCHDIR is, overwrite SCRATCHDIR from environment;
                        ''')
    parser.add_argument('-c', '--scratch_copy', type=str, metavar="PATH", default="", required=False,
                        help='''
                        directory path, its content will be copied to SCRATCHDIR;
                        ''')
    # if file path, each user defined path inside the file will be copied to SCRATCHDIR
    parser.add_argument('prog', nargs=argparse.REMAINDER,
                        help='''
                        mpiexec arguments and the executable, follow mpiexec doc:
                        "mpiexec args executable pgmargs [ : args executable pgmargs ... ]"

                        still can use MPMD (Multiple Program Multiple Data applications):
                        -n 4 program1 : -n 3 program2 : -n 2 program3 ...
                        ''')

    # create the parser for the "prog" command
    # parser_prog = parser.add_subparsers().add_parser('prog', help='program to be run and all its arguments')
    # parser_prog.add_argument('args', nargs="+", help="all arguments passed to 'prog'")

    # parser.print_help()
    # parser.print_usage()
    args = parser.parse_args()
    return args


def main():
    flush_print("================== smpiexec.py START ==================")
    current_dir = os.getcwd()
    args = arguments()

    # get debug variable
    debug = args.debug
    # get program and its arguments
    prog_args = args.prog[1:]

    # get program and its arguments, set absolute path
    if os.path.isfile(args.image):
        image = os.path.abspath(args.image)
    elif args.image.startswith('docker://'):
        image = args.image
    else:
        raise Exception("Invalid image: not a file nor docker hub link: " + args.image)

    flush_print("Hostname: ", os.popen('hostname').read())
    # mprint("os.environ", os.environ)

    ###################################################################################################################
    # Process node file and setup ssh access to given nodes.
    ###################################################################################################################

    pbs_job_id = os.environ['PBS_JOBID']
    flush_print("PBS job id: ", pbs_job_id)
    pbs_job_aux_dir =  os.path.join(current_dir, pbs_job_id + '_job')
    # create auxiliary job output directory
    os.makedirs(pbs_job_aux_dir, mode=0o775)
    
    # get nodefile, copy it to local dir so that it can be passed into container mpiexec later
    if debug:
        node_file = "testing_hostfile"
    else:
        flush_print("getting host file...")
        orig_node_file = os.environ['PBS_NODEFILE']
        node_file = os.path.join(pbs_job_aux_dir, os.path.basename(orig_node_file))
        shutil.copy(orig_node_file, node_file)
        # mprint(os.popen("ls -l").read())

    node_names = create_known_hosts_file(current_dir, node_file, debug=debug)

    # mprint(os.environ)
    create_agent = 'SSH_AUTH_SOCK' not in os.environ
    if not create_agent:
        create_agent = os.environ['SSH_AUTH_SOCK'] == ''

    if create_agent:
        create_ssh_agent()
    assert 'SSH_AUTH_SOCK' in os.environ
    assert os.environ['SSH_AUTH_SOCK'] != ""

    ###################################################################################################################
    # Create Singularity container commands.
    ###################################################################################################################

    flush_print("assembling final command...")

    scratch_dir_path = None
    if args.scratch_dir:
        scratch_dir_path = args.scratch_dir
    elif 'SCRATCHDIR' in os.environ:
        scratch_dir_path = os.environ['SCRATCHDIR']
    if scratch_dir_path and args.scratch_copy:
        flush_print("Using SCRATCHDIR:", scratch_dir_path)

        flush_print("copying to SCRATCHDIR on all nodes...")
        username = os.environ['USER']
        # get source files
        source = None
        if os.path.isdir(args.scratch_copy):
            # source = args.scratch_copy + "/."
            # paths = [os.path.join(args.scratch_copy,fp) for fp in os.listdir(args.scratch_copy)]
            # source = ' '.join(paths)
            source = args.scratch_copy
        else:
            raise Exception("--scratch_copy argument is not a valid directory: " + args.scratch_copy)
            # with open(args.scratch_copy) as fp:
            #   paths = fp.read().splitlines()
            #   source = ' '.join(paths)

        if source is None or source is []:
            flush_print(args.scratch_copy, "is empty")

        # create tar
        source_tar_filename = 'scratch.tar'
        source_tar_filepath = os.path.join(current_dir, source_tar_filename)
        command = ' '.join(['cd', source, '&&', 'tar -cvf', source_tar_filepath, '.', '&& cd', current_dir])
        oscommand(command)

        for node in node_names:
            destination_name = username + "@" + node
            destination_path = destination_name + ':' + scratch_dir_path
            command = ' '.join(['scp', '-o', 'UserKnownHostsFile=known_hosts', source_tar_filepath, destination_path])
            oscommand(command)

            #command = ' '.join(['ssh', destination_name, 'cd', scratch_dir_path, '&&', 'tar --strip-components 1 -xf', source_tar_filepath, '-C /'])
            command = ' '.join(['ssh', '-o', 'UserKnownHostsFile=known_hosts', destination_name, '"cd', scratch_dir_path, '&&', 'tar -xf', source_tar_filename,
                                '&&', 'rm ', source_tar_filename, '"'])
            oscommand(command)

        # remove the scratch tar
        oscommand(' '.join(['rm', source_tar_filename]))


    # A] process bindings, exclude ssh agent in launcher bindings
    bindings = "-B " + os.environ['SSH_AUTH_SOCK']
    # possibly add current dir to container bindings
    # bindings = bindings + "," + current_dir + ":" + current_dir
    bindings_in_launcher = ""
    if args.bind != "":
        bindings = bindings + "," + args.bind
        bindings_in_launcher = "-B " + args.bind

    if scratch_dir_path:
      bindings = bindings + "," + scratch_dir_path
      if args.bind == "":
        bindings_in_launcher = "-B "+ scratch_dir_path
      else:
        bindings_in_launcher = bindings_in_launcher + "," + scratch_dir_path

    sing_command_list = ['singularity', 'exec', bindings, image]
    sing_command = ' '.join(sing_command_list)
    sing_command_in_launcher = ' '.join(['singularity', 'exec', bindings_in_launcher, image])

    flush_print('sing_command:', sing_command)
    flush_print('sing_command_in_ssh:', sing_command_in_launcher)

    # B] prepare node launcher script
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
    oscommand('chmod +x ' + launcher_path)

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
    mpiexec_args = [mpiexec_path, '-f', node_file, '-launcher-exec', launcher_path]

    # F] join all the arguments into final singularity container command
    final_command_list = [*sing_command_list, *mpiexec_args, *prog_args]

    ###################################################################################################################
    # Final call.
    ###################################################################################################################
    if scratch_dir_path and args.scratch_copy:
      flush_print("Entering SCRATCHDIR:", scratch_dir_path)
      os.chdir(scratch_dir_path)

    flush_print("current directory:", os.getcwd())
    # mprint(os.popen("ls -l").read())
    flush_print("final command:")
    flush_print("=================== smpiexec.py END ===================")
    if not debug:
        flush_print("================== Program output START ==================")
        if scratch_dir_path:
            sing_tmp = os.path.join(scratch_dir_path, "singularity_tmp")
        else:
            sing_tmp = os.path.join(os.environ['HOME'], "singularity_tmp")
        os.makedirs(sing_tmp, exist_ok = True)
        proc = subprocess.run(final_command_list, env={**os.environ, "SINGULARITY_TMPDIR": sing_tmp})

        flush_print("=================== Program output END ===================")
    exit(proc.returncode)

if __name__ == "__main__":
    main()