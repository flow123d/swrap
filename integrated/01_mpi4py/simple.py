from mpi4py import MPI
import hashlib
import random
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

seed = hashlib.sha256(str(rank).encode()).digest()
random.seed(seed)

rand_max = 1000_000
num_sends = 100_000
num_iter = 10

for i in range(num_iter):
    sum = 0
    for j in range(1, num_sends + 1):
        data_out = random.randrange(rand_max)
        dest = (rank + j) % size
        req = comm.isend(data_out, dest=dest)
        req.wait()

        req = comm.irecv()
        data_in = req.wait()
        sum += data_out
        sum += data_in
        sum %= 275_604_541

    recvbuf = np.empty(1, dtype=int)
    sendbuf = sum * np.ones(size, dtype=int)
    comm.Reduce_scatter(sendbuf, recvbuf)

    print("[{}] {}".format(rank, recvbuf[0]))

print("P{} finished".format(rank))
