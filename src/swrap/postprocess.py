import os
import sys

import sexec
from sexec import flush_print, oscommand


def main():
    flush_print("================== postprocess.py START ==================")
    current_dir = os.getcwd()
    sub_dir = sys.argv[1]
    dest_dir = sys.argv[2]

    ###################################################################################################################
    # Process node file.
    ###################################################################################################################

    flush_print("Hostname: ", os.popen('hostname').read())
    # mprint("os.environ", os.environ)

    pbs_job_id = os.environ['PBS_JOBID']
    flush_print("PBS job id: ", pbs_job_id)
    pbs_job_aux_dir = os.path.join(current_dir, pbs_job_id + '_job')

    # get nodefile, copy it to local dir so that it can be passed into container mpiexec later
    if debug:
        orig_node_file = "testing_hostfile"
    else:
        orig_node_file = os.environ['PBS_NODEFILE']
    node_file = os.path.join(pbs_job_aux_dir, os.path.basename(orig_node_file))
    node_names = read_node_file(node_file)

    ###################################################################################################################
    # Copy from scratchdir.
    ###################################################################################################################

    flush_print("Copying from scratchdir...")

    scratch_dir_path = None
    if 'SCRATCHDIR' in os.environ:
        scratch_dir_path = os.environ['SCRATCHDIR']
        flush_print("SCRATCHDIR:", scratch_dir_path)
    else:
        flush_print("SCRATCHDIR", "not found in os.environ.")
        exit(0)

    username = os.environ['USER']
    for node in node_names:
        source_name = username + "@" + node

        # create tar on node
        node_tar_filename = "node.tar"
        node_tar_filepath = os.path.join(scratch_dir_path, node_tar_filename)
        command = ' '.join(['ssh', source_name, '"cd', scratch_dir_path, '&&', 'tar -cvf', node_tar_filepath, sub_dir, '"'])
        oscommand(command)

        # copy tar to frontend
        source_path = source_name + ':' + node_tar_filepath
        command = ' '.join(['scp', source_path, dest_dir])
        oscommand(command)

        command = ' '.join(['cd', dest_dir, '&&', 'tar -xf', node_tar_filename, '&&', 'rm ', source_tar_filename])
        oscommand(command)


if __name__ == "__main__":
    main()