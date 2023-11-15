import os
import subprocess

import sexec
from sexec import flush_print
import smpiexec_prepare


def create_argparser():
    parser = sexec.create_base_argparser()
    sexec.add_sexec_args(parser)
    smpiexec_prepare.add_mpiexec_arg(parser)

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
    return parser


def main():
    flush_print("================== smpiexec.py START ==================")
    current_dir = os.getcwd()
    parser = create_argparser()
    args = parser.parse_args()

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
    if args.debug:
        orig_node_file = "testing_hostfile"
    else:
        orig_node_file = os.environ['PBS_NODEFILE']
    node_file = sexec.copy_node_file(orig_node_file, pbs_job_aux_dir)
    node_names = sexec.read_node_file(node_file)

    # Get ssh keys to nodes and append it to $HOME/.ssh/known_hosts
    ssh_known_hosts_to_append = []
    if args.debug:
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
    launcher_path = smpiexec_prepare.prepare_mpiexec_launcher(pbs_job_aux_dir, pbs_job_id, sing_command_in_launcher)

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
    mpiexec_args = smpiexec_prepare.prepare_mpiexec_runner(current_dir, mpiexec_path, node_file, launcher_path)
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
    if not args.debug:
        flush_print("================== Program output START ==================")
        # proc = subprocess.run(final_command_list)
        final_command = " ".join(final_command_list)
        sexec.oscommand(final_command)

        flush_print("=================== Program output END ===================")
    # exit(proc.returncode)


if __name__ == "__main__":
    main()
