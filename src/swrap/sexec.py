from typing import *
import os
import shutil
import argparse
import subprocess
#import attrs
import socket

from utils import flush_print, oscommand
from pbs_utils import make_pbs_wrappers



def process_image_url(image_path: str) -> str:
    if os.path.isfile(image_path):
        image = os.path.abspath(image_path)
    elif image_path.startswith('docker://'):
        image = image_path
    else:
        raise Exception("Invalid image: not a file nor docker hub link: " + image_path)
    return image


class SingularityCall:
    def __init__(self, image, command, debug=False):
        self.image: str = process_image_url(image)
        # singularity image url
        self.command: List[str] = command
        # command to call in the container with its arguments
        self.bindings: List[str] = []
        self.env_dict: Dict[str, str] = {}
        self.debug: bool = False

    def append_path(self, add_path):
        append_path_list = self.env_dict.get('APPEND_PATH', "").split(":")
        append_path_list.append(add_path)
        append_path_list = ":".join(append_path_list)
        self.env_dict['APPEND_PATH'] = append_path_list

    def prepend_path(self, add_path):
        append_path_list = self.env_dict.get('PREPEND_PATH', "").split(":")
        append_path_list.insert(0, add_path)
        append_path_list = ":".join(append_path_list)
        self.env_dict['PREPEND_PATH'] = append_path_list

    def form_bindings(self):
        # currently we olny support binding of the same paths in host and in container
        return self.bindings

    def form_env_list(self):
        return [f"{key}={str(value)}" for key, value in self.env_dict.items()]

    def cmd_list(self):
        sing_command = ['singularity', 'exec',
                        '-B', ",".join(self.form_bindings()),
                        '--env', ",".join(self.form_env_list()),
                        self.image,
                        *self.command]

        # F] join all the arguments into final singularity container command
        return  sing_command

    def call(self):
        flush_print("current directory:", os.getcwd())
        # mprint(os.popen("ls -l").read())
        flush_print("final command:", *self.cmd_list())
        flush_print("=================== smpiexec.py END ===================")
        if not self.debug:
            flush_print("================== Program output START ==================")
            # proc = subprocess.run(final_command_list)
            final_command = " ".join(self.cmd_list())
            oscommand(final_command)
            flush_print("=================== Program output END ===================")
        # exit(proc.returncode)


def copy_and_read_node_file(directory):
    orig_node_file = os.environ.get('PBS_NODEFILE', None)
    if orig_node_file is None:
        node_file = os.path.join(directory, "nodefile")
        hostname = socket.gethostname()
        flush_print(f"Warning: missing PBS_NODEFILE variable. Using just local node: {hostname}.")
        with open(node_file, "w") as f:
            f.write(hostname)    
    else:
        # create a copy
        node_file = os.path.join(directory, os.path.basename(orig_node_file))
        shutil.copy(orig_node_file, node_file)
       
    flush_print("reading host file...")

    # read node names
    with open(node_file) as fp:
        node_names_read = fp.read().splitlines()
        # remove duplicates
        node_names = list(set(node_names_read))
    return node_file, node_names


def create_ssh_agent():
    """
    Setup ssh agent and set appropriate environment variables.
    :return:
    """
    create_agent = 'SSH_AUTH_SOCK' not in os.environ
    if not create_agent:
        create_agent = os.environ['SSH_AUTH_SOCK'] == ''
    if not create_agent:
        return

    flush_print("creating ssh agent...")
    p = subprocess.Popen('ssh-agent -s',
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         shell=True, universal_newlines=True)
    outinfo, errinfo = p.communicate('ssh-agent cmd\n')
    # print(outinfo)

    lines = outinfo.split('\n')
    for line in lines:
        # trim leading and trailing whitespace
        line = line.strip()
        # ignore blank/empty lines
        if not line:
            continue
        # break off the part before the semicolon
        left, right = line.split(';', 1)
        if '=' in left:
            # get variable and value, put into os.environ
            varname, varvalue = left.split('=', 1)
            flush_print("setting variable from ssh-agent:", varname, "=", varvalue)
            os.environ[varname] = varvalue

    assert 'SSH_AUTH_SOCK' in os.environ
    assert os.environ['SSH_AUTH_SOCK'] != ""


def process_known_hosts_file(ssh_known_hosts_file, node_names):
    flush_print("host file name:", ssh_known_hosts_file)

    ssh_known_hosts = []
    if os.path.exists(ssh_known_hosts_file):
        with open(ssh_known_hosts_file, 'r') as fp:
            ssh_known_hosts = fp.readlines()
    else:
        flush_print("creating host file...")
        dirname = os.path.dirname(ssh_known_hosts_file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    flush_print("connecting nodes...")
    ssh_known_hosts_to_append = []
    for node in node_names:
        # touch all the nodes, so that they are accessible also through container
        os.popen('ssh ' + node + ' exit')
        # add the nodes to known_hosts so the fingerprint verification is skipped later
        # in shell just append # >> ~ /.ssh / known_hosts
        # or sort by 3.column in shell: 'sort -k3 -u ~/.ssh/known_hosts' and rewrite
        ssh_keys = os.popen('ssh-keyscan -H ' + node).readlines()
        ssh_keys = list((line for line in ssh_keys if not line.startswith('#')))
        for sk in ssh_keys:
            splits = sk.split(" ")
            if not splits[2] in ssh_known_hosts:
                ssh_known_hosts_to_append.append(sk)

    flush_print("finishing host file...")
    with open(ssh_known_hosts_file, 'a') as fp:
        fp.writelines(ssh_known_hosts_to_append)


def prepare_scratch_dir(scratch_source, node_names):
    if scratch_source == "":
        return os.getcwd()
    
    scratch_dir_path = os.environ.get('SCRATCHDIR', None)
    if scratch_dir_path is None:
        return os.getcwd()
    
    
    flush_print("Using SCRATCHDIR:", scratch_dir_path)

    flush_print("copying to SCRATCHDIR on all nodes...")
    username = os.environ['USER']
    # get source files
    source = None
    if os.path.isdir(scratch_source):
        # source = scratch_source + "/."
        # paths = [os.path.join(scratch_source,fp) for fp in os.listdir(scratch_source)]
        # source = ' '.join(paths)
        source = scratch_source
    else:
        raise Exception("--scratch_copy argument is not a valid directory: " + scratch_source)
        # with open(scratch_source) as fp:
        #   paths = fp.read().splitlines()
        #   source = ' '.join(paths)

    if source is None or source is []:
        flush_print(scratch_source, "is empty")

    # create tar
    current_dir = os.getcwd()
    source_tar_filename = 'scratch.tar'
    source_tar_filepath = os.path.join(current_dir, source_tar_filename)
    command = ' '.join(['cd', source, '&&', 'tar -cvf', source_tar_filepath, '.', '&& cd', current_dir])
    oscommand(command)

    # copy to scratch dir on every used node through ssh
    for node in node_names:
        destination_name = username + "@" + node
        destination_path = destination_name + ':' + scratch_dir_path
        command = ' '.join(['scp', source_tar_filepath, destination_path])
        oscommand(command)

        # command = ' '.join(['ssh', destination_name, 'cd', scratch_dir_path, '&&', 'tar --strip-components 1 -xf', source_tar_filepath, '-C /'])
        command = ' '.join(['ssh', destination_name, '"cd', scratch_dir_path, '&&', 'tar -xf', source_tar_filename,
                            '&&', 'rm ', source_tar_filename, '"'])
        oscommand(command)

    # remove the scratch tar
    oscommand(' '.join(['rm', source_tar_filename]))
    return scratch_dir_path


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
    parser.add_argument('-s', '--scratch_copy', type=str, metavar="PATH", default="", required=False,
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


def setup_aux_dir():
    current_dir = os.getcwd()
    pbs_job_id = os.environ.get('PBS_JOBID', f"pid_{os.getpid()}")
    flush_print("PBS job id: ", pbs_job_id)
    pbs_job_aux_dir =  os.path.join(current_dir, pbs_job_id + '_job')
    # create auxiliary job output directory
    os.makedirs(pbs_job_aux_dir, mode=0o775)
    return pbs_job_aux_dir
    
    
def main():
    flush_print("================== smpiexec.py START ==================")
    args = arguments()


    sing = SingularityCall(args.image, args.prog, debug=args.debug)
    ###################################################################################################################
    # Process node file and setup ssh access to given nodes.
    ###################################################################################################################

    flush_print("Hostname: ", os.popen('hostname').read())
    # mprint("os.environ", os.environ)
    pbs_job_aux_dir = setup_aux_dir()

    # get nodefile, copy it to local dir so that it can be passed into container mpiexec later
    node_file, node_names = copy_and_read_node_file(pbs_job_aux_dir)
        

    # Get ssh keys to nodes and append it to $HOME/.ssh/known_hosts
    ssh_known_hosts_to_append = []
    if sing.debug:
        # ssh_known_hosts_file = 'testing_known_hosts'
        ssh_known_hosts_file = 'xxx/.ssh/testing_known_hosts'
    else:
        assert 'HOME' in os.environ
        ssh_known_hosts_file = os.path.join(os.environ['HOME'], '.ssh/known_hosts')
    process_known_hosts_file(ssh_known_hosts_file, node_names)

    # mprint(os.environ)
    create_ssh_agent()

    ###################################################################################################################
    # Create Singularity container commands.
    ###################################################################################################################

    flush_print("assembling final command...")
    scratch_dir_path = prepare_scratch_dir(args.scratch_copy, node_names)


    # A] process bindings, exclude ssh agent in launcher bindings
    common_bindings = ["/etc/ssh/ssh_config", "/etc/ssh/ssh_known_hosts", "/etc/krb5.conf"]
    sing.bindings.extend(common_bindings)
    sing.bindings.append(os.environ['SSH_AUTH_SOCK'])
    # possibly add current dir to container bindings
    # bindings = bindings + "," + current_dir + ":" + current_dir
    if args.bind != "":
        sing.bindings.append(args.bind)

    if scratch_dir_path:
        sing.bindings.append(scratch_dir_path)


    make_pbs_wrappers(pbs_job_aux_dir, sing.bindings)
    sing.append_path(pbs_job_aux_dir)

    ###################################################################################################################
    # Final call.
    ###################################################################################################################
    if scratch_dir_path:
      flush_print("Entering SCRATCHDIR:", scratch_dir_path)
      os.chdir(scratch_dir_path)

    sing.call()

if __name__ == "__main__":
    main()
