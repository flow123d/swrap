#!/bin/bash
#PBS -S /bin/bash
#PBS -l select=2:ncpus=1:mem=1gb
#PBS -l place=scatter:excl
#PBS -l walltime=00:05:00
#PBS -q charon_2h
#PBS -N sing_mpi_test
#PBS -j oe

set -x

which python3

# run from the repository directory
cd "/auto/liberec3-tul/home/pavel_exner/workspace/singularity_tryout_4" || exit
pwd

#paths inside container:
prog="/tutorials/OSU-MicroBenchmarks/build.mpich/libexec/osu-micro-benchmarks/mpi/one-sided/osu_get_latency"
# prog="/tutorials/OSU-MicroBenchmarks/build.mpich/libexec/osu-micro-benchmarks/mpi/one-sided/osu_get_bw"

# TEST running mpiexec OUTside of container
module add mpich-3.0.2-gcc
mpiexec -f $PBS_NODEFILE singularity exec osu-microbenchmarks.sif $prog
