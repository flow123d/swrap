#!/bin/bash

rm ./tst_stderr
echo "Running test"
./swrap.sh -d=tst_stderr -b="a:b,c:d" -e=A,B -m -s IMG CMD

echo "Test completed"

if cmp tst_stderr -- <<END
DEBUG: 'tst_stderr'
CONT_BIND_LIST: a:b c:d
CONT_ENV_LIST: A B
MPIEXEC: 'mpiexec'
SCRATCH_INPUT_DIR: '/home/jb/workspace/endorse/submodules/swrap/src/swrap'
IMAGE_URL: 'IMG'
COMMAND: CMD
END
then
    echo "Success"
else
    echo "Fail"
fi

