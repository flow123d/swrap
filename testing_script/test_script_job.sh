#!/bin/bash
#PBS -S /bin/bash
#PBS -l select=2:ncpus=2:mem=4gb
#PBS -l place=scatter
#PBS -l walltime=00:01:00
#PBS -q charon_2h
#PBS -N sing_mpi_test
#PBS -j oe

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
PROG="-n 4 python3 -m mpi4py $PBS_O_WORKDIR/script2.py"

# main call
python3 $SING_SCRIPT -i $SING_FLOW -- $PROG
# python3 $SING_SCRIPT -i $SING_FLOW -m $IMG_MPIEXEC -- $PROG



# example with python virtual environment
# 1) create SIF image
#   >> cd ..
#   >> singularity build flow123d_geomop-gnu:2.0.0.sif docker://flow123d/geomop-gnu:2.0.0
# 2) create virtual environment within container
#   >> singularity shell flow123d_geomop-gnu:2.0.0.sif
#   >> cd testing_script
#   >> ./setup_python_environment.sh
# 3) use auxiliary python_script_runner.sh to run the script in venv
# PROG="-n 4 $PBS_O_WORKDIR/python_script_runner.sh"
