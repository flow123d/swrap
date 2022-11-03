#!/bin/bash
#PBS -S /bin/bash
#PBS -l select={pbs_select}
#PBS -l place={pbs_place}
#PBS -l walltime={pbs_walltime}
#PBS -q {pbs_queue}
#PBS -j oe

# Template parameters
# ===================
# pbs_select = {pbs_select}      
# pbs_place = {pbs_place}       
# pbs_walltime = {pbs_walltime}
# pbs_queue = {pbs_queue}
# wrapper = {wrapper}           # main swrap executable, e.g. smpiexec
# image = {image}               # image to use, docker repository can be used
# command = {command}           # parameters to the manager in the image

# !!!! Do not use braces for the shell, braces enclosed are the template variables (using Python string formating)

set -x

# intial directory is usaully $HOME
# echo "Inital current dir: `pwd`"

# change to the directore where the qsub was started (in or case that should be dir of the pbs_script)
echo "PBS workdir: $PBS_O_WORKDIR"
cd "$PBS_O_WORKDIR" || ( echo "Misising dir: $PBS_O_WORKDIR" && exit 1)

which python3


# collect arguments:

# singularity_exec_mpi script path
#SING_SCRIPT="../singularity_exec_mpi.py"

# singularity SIF image path (preferably create in advance)
#SING_FLOW="$HOME/workspace/flow123d_images/flow123d_geomop-gnu:2.0.0.sif"

# possibly set container mpiexec path
# IMG_MPIEXEC="/usr/local/mpich_3.4.2/bin/mpiexec"

# program and its arguments
#PROG="-n 4 python3 -m mpi4py $PBS_O_WORKDIR/test_01_script.py"

# main call
    python3 {wrapper} -i {image} -- {command}
# python3 $SING_SCRIPT -i $SING_FLOW -m $IMG_MPIEXEC -- $PROG

