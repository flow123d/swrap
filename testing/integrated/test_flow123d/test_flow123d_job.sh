#!/bin/bash
#PBS -S /bin/bash
#PBS -l select=2:ncpus=2:mem=4gb:scratch_ssd=16gb
#PBS -l place=scatter
#PBS -l walltime=00:01:00
#PBS -q charon_2h
#PBS -N sing_flow_test
#PBS -j oe

set -x

which python3

# run from pbs script directory
cd $PBS_O_WORKDIR || exit
pwd
# ls -l

# collect arguments:
# singularity_exec_mpi script path
SING_SCRIPT="../singularity_exec_mpi.py"
# singularity SIF image path (preferably create in advance)
SING_FLOW="$HOME/workspace/flow123d_images/flow123d_geomop-gnu:2.0.0.sif"
# SING_FLOW="$HOME/workspace/flow123d_images/flow123d_3.0.5_92f55e826.sif"

# container mpiexec path (if not defined, default 'mpiexec' is used)
IMG_MPIEXEC="/usr/local/mpich_3.4.2/bin/mpiexec"
# program and its arguments
PROG="-n 4 flow123d 01_dirichlet.yaml -o output_flow"

# directory with input files, all will be copied to $SCRATCHDIR
SCRATCH_COPY="$PBS_O_WORKDIR/input"
# file contains list of input files, all will be copied to $SCRATCHDIR
# not enabled now
# SCRATCH_COPY="$PBS_O_WORKDIR/scratch_files"

python3 $SING_SCRIPT -i $SING_FLOW -s $SCRATCH_COPY -m $IMG_MPIEXEC -- "$PROG"

# possibly copy the results from scratch
if [ ! -d "$PBS_O_WORKDIR/output" ]; then
  mkdir $PBS_O_WORKDIR/output
fi
ls -l $SCRATCHDIR
cp -r $SCRATCHDIR/.  $PBS_O_WORKDIR/output/

clean_scratch
