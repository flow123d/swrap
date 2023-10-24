import os
import sys

import sexec
from sexec import flush_print, oscommand, ssh_command


def gather_to_master(node_names, sub_dir, clear=True):
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
        # ssh_command(source_name, ['cd', scratch_dir_path, '&&', 'ls -aR'])

        # create tar on node
        node_tar_filename = node + ".tar"
        node_tar_filepath = os.path.join(scratch_dir_path, node_tar_filename)
        ssh_command(source_name, ['cd', destination_path, '&&', 'tar -cvf', node_tar_filepath, '.'])

        # copy tar to master node
        oscommand(['scp', source_name + ':' + node_tar_filepath, scratch_dir_path])

        if clear:
            ssh_command(source_name, ['rm', node_tar_filepath])

        # untar on master
        tar_args = ['tar', '--skip-old-files', '--directory', sub_dir, '-xf']
        oscommand(['cd', scratch_dir_path, '&&', *tar_args, node_tar_filename])

        if clear:
            oscommand(['cd', scratch_dir_path, '&&', 'rm', node_tar_filename])


if __name__ == "__main__":
    flush_print("================== gather_to_master.py START ==================")
    sub_dir = sys.argv[1]

    ###################################################################################################################
    # Copy from slaves to master.
    ###################################################################################################################

    flush_print("Hostname: ", os.popen('hostname').read())
    node_names = sexec.read_node_files_from_auxdir()

    flush_print("Gather from slaves to master...")
    gather_to_master(node_names, sub_dir, clear=True)

    flush_print("================== gather_to_master.py END ==================")
