#!/bin/bash
#PBS -S /bin/bash
#PBS -l select=2:ncpus=2:mem=4gb
#PBS -l place=scatter
#PBS -l walltime=00:01:00
#PBS -q charon_2h
#PBS -N swrap_03a
#PBS -j oe

# TEST
# - access qstat command within the singularity container through ssh to pbs host
# - error test case commented out

cd $PBS_O_WORKDIR || exit
pwd

# collect arguments:

# singularity exec script path
SING_SCRIPT="$HOME/workspace/swrap/src/swrap/sexec.py"
# singularity SIF image path (preferably create in advance)
SING_FLOW="$HOME/workspace/flow123d_images/flow123d_geomop-gnu:2.0.0.sif"

# ERROR CASES:
# qstat not found inside singularity container
# PROG="qstat -u pavel_exner"

# program and its arguments
PROG="ssh -x ${PBS_O_HOST} qstat -u pavel_exner"

# main call
python3 $SING_SCRIPT -i $SING_FLOW -- $PROG
