from mpi4py import MPI


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0:
    # error
    print("P{} zero division.".format(rank))
    a = 2 / 0

print("P{} finished".format(rank))
