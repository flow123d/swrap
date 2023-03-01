#!/bin/bash
#
# TODO: 
# - debug output to given file, practical for wrapper (mpiexec, qsub, qstat) debugging, need suitable print function
# 
set -x

# Default debug output.
STDERR="/dev/stderr"

# Global variables
# DEBUG - path to the redirection of debug messages
# IMAGE_URL

function cleanup () {
    [ -n "${JOB_AUX_DIR}" ] && rm -r ${JOB_AUX_DIR}
}

trap "cleanup" EXIT


function arg_assignment_split() {
    RESULT_ARG=${1%=*}
    if [ "$RESULT_ARG" == "$1" ]
    then  
        RESULT_VALUE=
    else
        RESULT_VALUE="${1#*=}"
    fi
}

function split_to_array () {
    # USAGE: split_to_array <delimiter> <input_string>
    # split a strng
    delimiter=$1
    input=$2
    readarray -td${delimiter} RESULT <<<"${input}${delimiter}"; unset 'RESULT[-1]'
}

function error () {
    # Report error and exit.
    # Usage: error "The error message"
    
    echo -e "ERROR: $1"
    exit 1
}

function check_var () {
    # Check that given var is nonempty (check global variables at beginning of a function.
    varname=$1
    [ -z "${!varname}" ] && error "Use of uninitialized var: $varname"
}

function check_indexed_array () {
    # TODO: check indexed array type
    varname=$1
    [[ -v ${varname}[@] ]] && error "Use of uninitialized array: $varname"
}


function dbg () {
    if [ -n "$DEBUG" ]
    then
        echo "$@" >>"$DEBUG"
    fi
}

function dbgvar {
    varname=$1
    shift
    dbg "$varname: '${!varname}'"
}

function dbgarray {
    local varname=$1
    local -n array="$varname"
    args=""
    for item in "${array[@]}"
    do args+=" '$item'"
    done
    dbg "$varname:" $args
}



function print_usage() {
cat << EOF
  
Usage:  
  
    Execute COMMAND under PBS:
    endorse [-d[=PATH]] [-b=<path>] [-e=<var>] [-m=[<mpiexec>]] [-s=<workdir>]  <image_url> <command> [<options>]

    
Options:
-d, --debug[=LOG_PATH] 
    Output debug messages to stderr or to the file given by the LOG_PATH.  
    
-b, --bind=<BIND LIST>
    Comma separated list of directory binds. Single bind format follows the Docker -v options, i.e.  host dir:container dir[options].

-e, --env=<ENV LIST>
    Comma separated list of the exported environment variables to introduce into the container environment.

-m, --mpiexec[=MPIEXEC_PATH]
    Creat a wrapper of mpiexec in the contiainer that manage lunching child mpi processes 
    in the same container through the cals: SSH -> swrap -> container -> mpiexec.
    Optionaly MPIEXEC_PATH provides path to the mpiexec in the container to use.
    ? mpi host file

-s, scratch_copy[=INPUT_DIR]
    Every local process copy content of current directory or directory given by INPUT_DIR to the directory given by SCRATCHDIR
    environment variable provided by PBS. Copy is done through 'scp' to caluculation nodes.
    
Used environment variables:

PBS_JOBID
PBS_NODEFILE
SSH_KNOWNHOSTS

    
EOF

# TODO direct run endorse_mlmc.py 

}

    
function parse_arguments() {
    while [ "${1#-}" != "$1" ]      # arg starts with '-'
    do
    arg_assignment_split "$1"       # produce $RESULT_ARG and $RESULT_VALUE
    arg="$RESULT_ARG"
    value="$RESULT_VALUE"
    shift
    case $arg in
        -d|--debug)
        DEBUG=${value:-$STDERR}
        ;;  
        -b|--bind)
        split_to_array "," "$value"
        CONT_BIND_LIST=( "${RESULT[@]}" )
        # one item in docker-like format: host_dir:container_dir[:options]
        ;;
        -e|--env)
        split_to_array "," "$value"
        CONT_ENV_LIST=( "${RESULT[@]}" )
        # contains exported variable names
        ;;
        -m|--mpiexec)
        DEFAULT_MPIEXEC="mpiexec"
        MPIEXEC=${value:-$DEFAULT_MPIEXEC}
        ;;
        -s|--scratch_copy)
        SCRATCH_INPUT_DIR=${value:-`pwd`}    
        ;;
        -h|--help)
        print_usage
        exit 0
        ;;
        *)
        print_usage
        error "Invalid argument '$arg'"
        ;;
    esac
    done
    
    if [ -z "$1" ]
    then
        print_usage
        error "Missing image url."
    fi
    IMAGE_URL="$1"
    shift
    if [ -z "$1" ]
    then
        print_usage
        error "Missing command."
    fi
    COMMAND_WITH_ARGS=("$@")
}


function read_pbs () {
    # read PBS variables, proceed with defaults if running without PBS
    PBS_JOBID=${PBS_JOBID:-"pid_$$"}    
    dbg "PBS_JOBID: '$PBS_JOBID'"
    
    # read PBS_NODEFILE
    declare -a NODE_NAMES
    if [ -z "${PBS_NODEFILE}" ]; then
        # default just local node
        NODE_NAMES+=($(hostname))
    else
        readarray -t NODE_NAMES <${PBS_NODEFILE}
    fi
    dbg "NODE_NAMES list: ${NODE_NAMES[@]}"
}

function setup_aux_dir () {
    # setup aux job dir
    check_var PBS_JOBID
    JOB_AUX_DIR="$(pwd)/${PBS_JOBID}_job"        
    mkdir -p -m=775 "$JOB_AUX_DIR"    
    
}




function ssh_batch () {
    #no_strict_key_check=-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
    ssh -o BatchMode=yes "$@"
}



function update_ssh_known_hosts_file () {
# def process_known_hosts_file(ssh_known_hosts_file, node_names):
#     flush_print("host file name:", ssh_known_hosts_file)
# 
#     ssh_known_hosts = []
#     if os.path.exists(ssh_known_hosts_file):
#         with open(ssh_known_hosts_file, 'r') as fp:
#             ssh_known_hosts = fp.readlines()
#     else:
#         flush_print("creating host file...")
#         dirname = os.path.dirname(ssh_known_hosts_file)
#         if not os.path.exists(dirname):
#             os.makedirs(dirname)
# 
#     flush_print("connecting nodes...")
#     ssh_known_hosts_to_append = []
#     for node in node_names:
#         # touch all the nodes, so that they are accessible also through container
#         os.popen('ssh ' + node + ' exit')
#         # add the nodes to known_hosts so the fingerprint verification is skipped later
#         # in shell just append # >> ~ /.ssh / known_hosts
#         # or sort by 3.column in shell: 'sort -k3 -u ~/.ssh/known_hosts' and rewrite
#         ssh_keys = os.popen('ssh-keyscan -H ' + node).readlines()
#         ssh_keys = list((line for line in ssh_keys if not line"".startswith('#')))
#         for sk in ssh_keys:
#             splits = sk.split(" ")
#             if not splits[2] in ssh_known_hosts:
#                 ssh_known_hosts_to_append.append(sk)
# 
#     flush_print("finishing host file...")
#     with open(ssh_known_hosts_file, 'a') as fp:
#         fp.writelines(ssh_known_hosts_to_append)


    local ssh_knownhosts_file="${SSH_KNOWNHOSTS:-${HOME}/.ssh/known_hosts}"
    check_indexed_array NODE_NAMES
    if [ ! -f "$ssh_knownhosts_file" ]
    then
        # create default known_hosts file
        mkdir -p "${ssh_knownhosts_file%/*}"
        touch "${ssh_knownhosts_file}"
    fi
    
    (
        # lock file descriptor 
        flock -w 30 223
        cp "$ssh_knownhosts_file" ~/.ssh/_tmp_hosts
        for node in "${NODE_NAMES[@]}";do
            # touch all the nodes, so that they are accessible also through container
            # TODO: should we do this in separate loop after updationg known_hosts ??
            # point of thi is to fail early
            ssh_batch $node exit
            ssh-keyscan -H $node 2>&1  >> ~/.ssh/_tmp_hosts
        done
        sort -u ~/.ssh/_tmp_hosts >"$ssh_knownhosts_file"
        rm ~/.ssh/_tmp_hosts
    ) 223>${HOME}/.ssh/_swrap_lock
}


function create_ssh_agent () {
# def create_ssh_agent():
#     """
#     Setup ssh agent and set appropriate environment variables.
#     :return:
#     """
#     create_agent = 'SSH_AUTH_SOCK' not in os.environ
#     if not create_agent:
#         create_agent = os.environ['SSH_AUTH_SOCK'] == ''
#     if not create_agent:
#         return
# 
#     flush_print("creating ssh agent...")
#     p = subprocess.Popen('ssh-agent -s',
#                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
#                          shell=True, universal_newlines=True)
#     outinfo, errinfo = p.communicate('ssh-agent cmd\n')
#     # print(outinfo)
# 
#     lines = outinfo.split('\n')
#     for line in lines:
#         # trim leading and trailing whitespace
#         line = line.strip()
#         # ignore blank/empty lines
#         if not line:
#             continue
#         # break off the part before the semicolon
#         left, right = line.split(';', 1)
#         if '=' in left:
#             # get variable and value, put into os.environ
#             varname, varvalue = left.split('=', 1)
#             flush_print("setting variable from ssh-agent:", varname, "=", varvalue)
#             os.environ[varname] = varvalue
# 
#     assert 'SSH_AUTH_SOCK' in os.environ
#     assert os.environ['SSH_AUTH_SOCK'] != ""

    if [ -z ${SSH_AUTH_SOCK} ]; then    
        cmds=$(ssh-agent -s)
        eval $cmds 
    fi
    
    dbg "SSH_AUTH_SOCK: '${SSH_AUTH_SOCK}'"
    dbg "SSH_AGENT_PID: '${SSH_AGENT_PID}'"
}


function make_wrapper () {
    # TODO: for docker make transplation of PWD
    # use a aux file with bindings, read it into associative array, lookup in it
    cmd=$1
    full_cmd=$(command -v $cmd)    
    cat <<WRAPPER
#!/bin/bash
set -x
#PWD="\$(pwd)"
PWD_HOST="\`pwd\`"        
ssh $HOST_ADDR "cd '$PWD_HOST'; $full_cmd \$@"
WRAPPER
}

# 
# def process_image_url(image_path: str) -> str:
#     if os.path.isfile(image_path):
#         image = os.path.abspath(image_path)
#     elif image_path.startswith('docker://'):
#         image = image_path
#     else:
#         raise Exception("Invalid image: not a file nor docker hub link: " + image_path)
#     return image
# 
# 
# class SingularityCall:
#     def __init__(self, image, command, venv="", debug=False):
#         self.image: str = process_image_url(image)
#         # singularity image url
#         self.command: List[str] = command
#         print("command with args:", command)
#         # command to call in the container with its arguments
#         self.venv:str = os.path.abspath(venv) if venv else ""
#         self.bindings: List[str] = []
#         self.env_dict: Dict[str, str] = {}
#         self.debug: bool = False
# 
#     def append_path(self, add_path):
#         append_path_list = self.env_dict.get('APPEND_PATH', "").split(":")
#         append_path_list.append(add_path)
#         append_path_list = ":".join(append_path_list)
#         self.env_dict['APPEND_PATH'] = append_path_list
# 
#     def prepend_path(self, add_path):
#         append_path_list = self.env_dict.get('PREPEND_PATH', "").split(":")
#         append_path_list.insert(0, add_path)
#         append_path_list = ":".join(append_path_list)
#         self.env_dict['PREPEND_PATH'] = append_path_list
# 
#     def form_bindings(self):
#         # currently we olny support binding of the same paths in host and in container
#         return self.bindings
# 
#     def form_env_list(self):
#         self.env_dict['SWRAP_SINGULARITY_VENV'] = self.venv
#         return [f"{key}={str(value)}" for key, value in self.env_dict.items()]
# 
#     def cmd_list(self):
#         if len(self.venv) > 0:
#             self.prepend_path(os.path.join(os.path.abspath(self.venv), 'bin'))
#         sing_command = ['singularity', 'exec',
#                         '-B', ",".join(self.form_bindings()),
#                         '--env', ",".join(self.form_env_list()),
#                         self.image,
#                         *self.command]
# 
#         # F] join all the arguments into final singularity container command
#         return  sing_command
# 
#     def call(self):
#         flush_print("current directory:", os.getcwd())
#         # mprint(os.popen("ls -l").read())
#         flush_print("final command:", *self.cmd_list())
#         flush_print("=================== smpiexec.py END ===================")
#         if not self.debug:
#             flush_print("================== Program output START ==================")
#             # proc = subprocess.run(final_command_list)
#             oscommand(self.cmd_list())
#             flush_print("=================== Program output END ===================")
#         # exit(proc.returncode)
# 
# 
# 
# 
# 
# 
# 
# 
# def prepare_scratch_dir(scratch_source, node_names):
#     if scratch_source == "":
#         return os.getcwd()
#     
#     scratch_dir_path = os.environ.get('SCRATCHDIR', None)
#     if scratch_dir_path is None:
#         return os.getcwd()
#     
#     
#     flush_print("Using SCRATCHDIR:", scratch_dir_path)
# 
#     flush_print("copying to SCRATCHDIR on all nodes...")
#     username = os.environ['USER']
#     # get source files
#     source = None
#     if os.path.isdir(scratch_source):
#         # source = scratch_source + "/."
#         # paths = [os.path.join(scratch_source,fp) for fp in os.listdir(scratch_source)]
#         # source = ' '.join(paths)
#         source = scratch_source
#     else:
#         raise Exception("--scratch_copy argument is not a valid directory: " + scratch_source)
#         # with open(scratch_source) as fp:
#         #   paths = fp.read().splitlines()
#         #   source = ' '.join(paths)
# 
#     if source is None or source is []:
#         flush_print(scratch_source, "is empty")
# 
#     # create tar
#     current_dir = os.getcwd()
#     source_tar_filename = 'scratch.tar'
#     source_tar_filepath = os.path.join(current_dir, source_tar_filename)
#     oscommand(['tar', '-cvf', source_tar_filepath], cwd=source)
# 
#     # copy to scratch dir on every used node through ssh
#     for node in node_names:
#         destination_name = username + "@" + node
#         destination_path = destination_name + ':' + scratch_dir_path
#         oscommand(['scp', source_tar_filepath, destination_path])
# 
#         # command = ' '.join(['ssh', destination_name, 'cd', scratch_dir_path, '&&', 'tar --strip-components 1 -xf', source_tar_filepath, '-C /'])
#         oscommand(['ssh', destination_name, f'cd "{scratch_dir_path}" && tar -xf "{source_tar_filename}" && rm "source_tar_filename"'])
# 
#     # remove the scratch tar
#     oscommand(['rm', source_tar_filename])
#     return scratch_dir_path



    
#     
#     
#     
# def main():
#     flush_print("================== smpiexec.py START ==================")
#     args = arguments()
# 
# 
#     sing = SingularityCall(args.image, args.prog, args.venv, debug=args.debug)
#     ###################################################################################################################
#     # Process node file and setup ssh access to given nodes.
#     ###################################################################################################################
# 
#     flush_print("Hostname: ", os.popen('hostname').read())
#     # mprint("os.environ", os.environ)
#     pbs_job_aux_dir = setup_aux_dir()
# 
#     # get nodefile, copy it to local dir so that it can be passed into container mpiexec later
#     node_file, node_names = copy_and_read_node_file(pbs_job_aux_dir)
#         
# 
#     # Get ssh keys to nodes and append it to $HOME/.ssh/known_hosts
#     ssh_known_hosts_to_append = []
#     if sing.debug:
#         # ssh_known_hosts_file = 'testing_known_hosts'
#         ssh_known_hosts_file = 'xxx/.ssh/testing_known_hosts'
#     else:
#         assert 'HOME' in os.environ
#         ssh_known_hosts_file = os.path.join(os.environ['HOME'], '.ssh/known_hosts')
#     process_known_hosts_file(ssh_known_hosts_file, node_names)
# 
#     # mprint(os.environ)
#     create_ssh_agent()
# 
#     ###################################################################################################################
#     # Create Singularity container commands.
#     ###################################################################################################################
# 
#     flush_print("assembling final command...")
#     scratch_dir_path = prepare_scratch_dir(args.scratch_copy, node_names)
# 
# 
#     # A] process bindings, exclude ssh agent in launcher bindings
#     common_bindings = ["/etc/ssh/ssh_config", "/etc/ssh/ssh_known_hosts", "/etc/krb5.conf"]
#     sing.bindings.extend(common_bindings)
#     sing.bindings.append(os.environ['SSH_AUTH_SOCK'])
#     # possibly add current dir to container bindings
#     # bindings = bindings + "," + current_dir + ":" + current_dir
#     if args.bind != "":
#         sing.bindings.append(args.bind)
# 
#     if scratch_dir_path:
#         sing.bindings.append(scratch_dir_path)
# 
# 
#     make_pbs_wrappers(pbs_job_aux_dir, sing.bindings)
#     sing.append_path(pbs_job_aux_dir)
# 
#     ###################################################################################################################
#     # Final call.
#     ###################################################################################################################
#     if scratch_dir_path:
#       flush_print("Entering SCRATCHDIR:", scratch_dir_path)
#       os.chdir(scratch_dir_path)
# 
#     sing.call()
# 
# if __name__ == "__main__":
#     main()


# TODO: add aux dir to path
# ? mount users home ?

function call_docker() {
    if ! docker image inspect $IMAGE_URL &> /dev/null; then        
        docker pull $IMAGE_URL
    fi
    
    local env_vars="-euid=$uid -egid=$gid -ewho=$uname -ehome=/mnt/$HOME"    
    #local host_workdir=`pwd`
    #local rel_home="${host_workdir#$HOME/}"
    #local home_first_subdir="${rel_home%%/*}"
    #local abs_first_subdir="$HOME/$home_first_subdir"
    
    local binds="-v$(pwd):$(pwd)"
    # --rm  remove container after completion
    # mount current dir (shuld include JOB_AUX_DIR) 
    
    # assert
    [[ -d "$JOB_AUX_DIR" && "$JOB_AUX_DIR" = $(pwd)* ]] || error "JOB_AUX_DIR not subdir of PWD"
    
    
    docker run --rm -u $(id -u):$(id -g) $env_vars ${CONT_ENV_LIST[@]/#/-e } $binds ${CONT_BIND_LIST[@]/#/-v} -w $(pwd) $IMAGE_URL "${COMMAND_WITH_ARGS[@]}"
}


function call_singularity() {
    # prepare singularity image: download, convert, (install) 
    LOCAL_IMAGE="$ENDORSE_WORKSPACE/endorse_ci_${tag}.sif"
    if [ ! -f $LOCAL_IMAGE ]
    then
        singularity build  $ENDORSE_IMAGE "docker://$IMAGE_URL"  
    fi
    
    # call 
    singularity exec ${CONT_ENV_LIST[@]/#/-e } $LOCAL_IMAGE ${COMMAND_WITH_ARGS[@]}
}


function call_container {
    # We automaticaly bind:    
    # - PWD (including JOB_AUX_DIR)

    
    if [ -x `command -v docker` ]; then
        call_docker
    elif [ -x `command -v singularity` ]; then            
        call_singularity
    else
        error "No container tool. Not supported."
    fi

}


# =================== MAIN

WORKDIR=`pwd`
parse_arguments "$@"

# Report parsed arguments
dbgvar DEBUG
dbgarray CONT_BIND_LIST
dbgarray CONT_ENV_LIST
dbgvar MPIEXEC
dbgvar SCRATCH_INPUT_DIR
dbgvar IMAGE_URL
dbgarray COMMAND_WITH_ARGS


# read PBS_JOBID and NODE_NAMES array
read_pbs

# set JOB_AUX_DIR, create aux dir
setup_aux_dir

update_ssh_known_hosts_file

# export: SSH_AUTH_SOCK, SSH_AGENT_PID
create_ssh_agent

make_wrapper qstat
make_wrapper qsub

call_container 
