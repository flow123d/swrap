import os
import sys

import sexec
from sexec import flush_print, oscommand, ssh_command


def distribute_to_slaves(node_names, sub_dir, clear=True):
    """
        Auxiliary function for copying files from master node to all slave nodes.
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

    # create tar on master
    tar_filename = "master.tar"
    tar_filepath = os.path.join(scratch_dir_path, tar_filename)
    oscommand(['cd', os.path.join(scratch_dir_path, sub_dir), '&&', 'tar -cvf', tar_filepath, '.'])

    for node in node_names:
        if node == hostname:
            continue

        flush_print("Node:", node)
        destination_name = username + "@" + node

        # copy tar to slave node
        oscommand(['scp', tar_filepath, destination_name + ':' + scratch_dir_path])

        ssh_command(destination_name, ['cd', scratch_dir_path, '&&', 'mkdir', '-p', sub_dir])
        tar_args = ['tar', '--skip-old-files', '--directory', sub_dir, '-xf', tar_filename]
        ssh_command(destination_name, ['cd', scratch_dir_path, '&&', *tar_args])

        if clear:
            ssh_command(destination_name, ['rm', tar_filepath])

        ssh_command(destination_name, ['cd', scratch_dir_path, '&&', 'ls -aR'])

    if clear:
        oscommand(['rm', tar_filepath])


if __name__ == "__main__":
    flush_print("================== distribute_to_slaves.py START ==================")
    sub_dir = sys.argv[1]

    ###################################################################################################################
    # Copy from master to slaves.
    ###################################################################################################################

    flush_print("Hostname:", os.popen('hostname').read())
    node_names = sexec.read_node_files_from_auxdir()

    flush_print("Copy from master to slaves...")
    distribute_to_slaves(node_names, sub_dir)

    flush_print("================== distribute_to_slaves.py END ==================")
