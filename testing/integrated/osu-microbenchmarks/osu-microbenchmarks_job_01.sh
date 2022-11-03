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
prog="/tutorials/OSU-MicroBenchmarks/build.mpich_psm/libexec/osu-micro-benchmarks/mpi/one-sided/osu_get_latency"
# prog="/tutorials/OSU-MicroBenchmarks/build.mpich_psm/libexec/osu-micro-benchmarks/mpi/one-sided/osu_get_bw"

# TEST running mpich with psm (installed by Radek Srb)

rs_home="/auto/liberec3-tul/home/radeksrb"
PATH=$rs_home/sing/mpich_psm-install/bin:$PATH ; export PATH

which mpiexec
mpiexec --version
mpiexec -f $PBS_NODEFILE "$rs_home$prog"
