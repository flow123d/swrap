#!/bin/bash

N_TST=1
function check () {
    tst_name="$1"
    shift
    
    # read stdin
    input=$(cat)
    
    output_name="./tst_stderr_${tst_name}"
    
    rm "$output_name"
    echo "RUN #${N_TST}: $tst_name"
    ./swrap.sh -d="$output_name" "$@" &
    subproc_pid=$!
    echo "Last cmd: $subproc_pid"
    wait $subproc_pid
    echo "DONE #${N_TST}: $tst_name"

    # substitute PID in input
    substituted_input=$(eval "echo \"$input\"")

    if echo "$substituted_input" | diff "$output_name" - 
    then
        echo "Success"
    else
        echo "Fail" 
    fi
    #rm "$output_name"
    N_TST=$((N_TST+1))
}

IMG=alpine

function test_local {
name="test_local"
rm 'file 1' 'file 2'
check "$name" -b="a:b,c:d" -e=A,B -m -s $IMG touch "file 1" "file 2"<<END
DEBUG: './tst_stderr_$name'
CONT_BIND_LIST: 'a:b' 'c:d'
CONT_ENV_LIST: 'A' 'B'
MPIEXEC: 'mpiexec'
SCRATCH_INPUT_DIR: '/home/jb/workspace/endorse/submodules/swrap/src/swrap'
IMAGE_URL: '$IMG'
COMMAND_WITH_ARGS: 'touch' 'file 1' 'file 2'
PBS_JOBID: 'pid_\${subproc_pid}'
NODE_NAMES list: $(hostname)
SSH_AUTH_SOCK: '/run/user/1000/keyring/ssh'
SSH_AGENT_PID: ''
END
# check command effect
[ -f 'file 1' ] || echo "Missing touched 'file 1'."
[ -f 'file 2' ] || echo "Missing touched 'file 2'."
}


function test_pbs_artificial {
name="test_pbs_artificial"
rm 'file 1' 'file 2'
export PBS_JOBID=1234
export PBS_NODEFILE=tst_nodefile
check "$name" -b="a:b,c:d" -e=A,B -m -s $IMG CMD ARG1 ARG2 <<END
DEBUG: './tst_stderr_2'
CONT_BIND_LIST: a:b c:d
CONT_ENV_LIST: A B
MPIEXEC: 'mpiexec'
SCRATCH_INPUT_DIR: '/home/jb/workspace/endorse/submodules/swrap/src/swrap'
IMAGE_URL: 'IMG'
COMMAND: CMD ARG1 ARG2
PBS_JOBID: '1234'
NODE_NAMES list: charon21.nti.tul.cz charon22.nti.tul.cz
SSH_AUTH_SOCK: '/run/user/1000/keyring/ssh'
SSH_AGENT_PID: ''
END
# check command effect
[ -f 'file 1' ] || echo "Missing touched 'file 1'."
[ -f 'file 2' ] || echo "Missing touched 'file 2'."
}


# TODO: use a mock mpi app from swrap to make real test
function test_pbs_real {
export PBS_JOBID=1234
export PBS_NODEFILE=tst_nodefile
check "local configuration" -b="a:b,c:d" -e=A,B -m -s $IMG CMD ARG1 ARG2 <<END
DEBUG: './tst_stderr_2'
CONT_BIND_LIST: a:b c:d
CONT_ENV_LIST: A B
MPIEXEC: 'mpiexec'
SCRATCH_INPUT_DIR: '/home/jb/workspace/endorse/submodules/swrap/src/swrap'
IMAGE_URL: 'IMG'
COMMAND: CMD ARG1 ARG2
PBS_JOBID: '1234'
NODE_NAMES list: charon21.nti.tul.cz charon22.nti.tul.cz
SSH_AUTH_SOCK: '/run/user/1000/keyring/ssh'
SSH_AGENT_PID: ''
END
}



test_local
test_pbs_artificial
if [ command -v qsub ]; then
    test_pbs_real
fi
