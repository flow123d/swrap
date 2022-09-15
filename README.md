# singularity_exec_mpi
Testing execution of parallel program inside singularity on HPC clusters.

The core of this repository is the file **singularity_exec_mpi.py**,
which enables running parallel programs inside singularity container on a cluster,
without any dependency on cluster provided modules, including mpi library.
The `mpiexec` command is called inside the container.


Dir `osu-microbenchmarks` contains results of two OSU micro-benchmarks (latency `osu_get_latency` and bandwidth `osu_get_bw` tests)
(https://ulhpc-tutorials.readthedocs.io/en/latest/parallel/mpi/OSU_MicroBenchmarks/),
which were executed in different setups:
- with no container, with own mpich build
- with mpich lib provided by cluster module and benchmarks run inside container
- all built and run inside container
