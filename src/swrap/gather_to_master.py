import os
import sys

import sexec
from sexec import flush_print, oscommand, ssh_command


def gather_to_master(node_names, sub_dir, verbose=False, clear=True):
    """
        Auxiliary function for copying files from slave nodes to master node.
        Supposes using SCRATCHDIR.
    """
    scratch_dir_path = None
    if 'SCRATCHDIR' in os.environ:
        scratch_dir_path = os.environ['SCRATCHDIR']
        flush_print("SCRATCHDIR:", scratch_dir_path)
    else:
        flush_print("SCRATCHDIR", "not found in os.environ.")
        exit(0)

    hostname = os.popen('hostname').read().strip()
    username = os.environ['USER']

    # destination_name = username + "@" + hostname
    # destination_path = destination_name + ':' + scratch_dir_path
    destination_path = os.path.join(scratch_dir_path, sub_dir)

    for node in node_names:
        if node == hostname:
            continue

        flush_print("Node:", node)
        source_name = username + "@" + node

        # print scratchdir content
        if verbose:
            ssh_command(source_name, ['cd', scratch_dir_path, '&&', 'ls -aR'])

        # create tar on node
        node_tar_filename = node + ".tar"
        node_tar_filepath = os.path.join(scratch_dir_path, node_tar_filename)
        tar_args = '-cvf' if verbose else '-cf'
        ssh_command(source_name, ['cd', destination_path, '&&', 'tar', tar_args, node_tar_filepath, '.'])

        # copy tar to master node
        oscommand(['scp', source_name + ':' + node_tar_filepath, scratch_dir_path])

        if clear:
            ssh_command(source_name, ['rm', node_tar_filepath])

        # untar on master
        tar_args = ['tar', '--skip-old-files', '--directory', sub_dir, '-xf']
        oscommand(['cd', scratch_dir_path, '&&', *tar_args, node_tar_filename])

        if clear:
            oscommand(['cd', scratch_dir_path, '&&', 'rm', node_tar_filename])


def create_parser():
    parser = sexec.create_base_argparser()

    parser.add_argument('-c', '--clear', action='store_true', default=False, help='clear temporary tarballs')
    parser.add_argument('subdir', nargs=1, help="Subdirectory to copy to SCRATCHDIR.")

    # parser.print_help()
    # parser.print_usage()
    return parser


def main():
    flush_print("================== gather_to_master.py START ==================")
    parser = create_argparser()
    args = parser.parse_args()

    ###################################################################################################################
    # Copy from slaves to master.
    ###################################################################################################################

    flush_print("Hostname: ", os.popen('hostname').read())
    node_names = sexec.read_node_files_from_auxdir()

    flush_print("Gather from slaves to master...")
    gather_to_master(node_names, args.subdir, verbose=args.verbose, clear=args.clear)

    flush_print("================== gather_to_master.py END ==================")


if __name__ == "__main__":
    main()
