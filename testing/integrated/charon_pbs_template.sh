#!/bin/bash
#PBS -S /bin/bash
#PBS -l select={n_nodes}:ncpus=2:mem=4gb
#PBS -l place=scatter
#PBS -l walltime=00:01:00
#PBS -q charon_2h
#PBS -j oe

# Template parameters
# ===================
# swrap_main={swrap_main} - main swrap executable, e.g. smpiexec
# singularity_image={singularity_image} - image to use, docker repository can be used
# n_nodes={n_nodes} - number of nodes to run the test, for the comunnication tests we always use distinct node for each process
# script_file={script_file} - command to run in the image

set -x

which python3

cd $PBS_O_WORKDIR || exit
pwd

# collect arguments:

# singularity_exec_mpi script path
SING_SCRIPT="../singularity_exec_mpi.py"

# singularity SIF image path (preferably create in advance)
SING_FLOW="$HOME/workspace/flow123d_images/flow123d_geomop-gnu:2.0.0.sif"

# possibly set container mpiexec path
# IMG_MPIEXEC="/usr/local/mpich_3.4.2/bin/mpiexec"

# program and its arguments
PROG="-n 4 python3 -m mpi4py $PBS_O_WORKDIR/test_01_script.py"

# main call
python3 {swrap_main} -i {singularity_image} -- -n {n_nodes} {script_file}
# python3 $SING_SCRIPT -i $SING_FLOW -m $IMG_MPIEXEC -- $PROG

