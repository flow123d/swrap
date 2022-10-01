from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

if rank == 0:
    data = {'a': 1, 'b': 3.14}
    print("P0 sending to P1: {}", data)
    req = comm.isend(data, dest=1, tag=11)
    req.wait()
    
    data = {'c': 2, 'd': 6.28}
    print("P0 sending to P2: {}", data)
    req = comm.isend(data, dest=2, tag=12)
    req.wait()
    print("P0 finished")
elif rank == 1:
    req = comm.irecv(source=0, tag=11)
    data = req.wait()
    print("P1 received: {}", data)
    
    data["a"] = 3
    data["b"] = 3*3.14
    print("P1 sending to P3: {}", data)
    req = comm.isend(data, dest=3, tag=13)
    req.wait()
    print("P1 finished")
elif rank == 2:
    req = comm.irecv(source=0, tag=12)
    data = req.wait()
    print("P2 received: {}", data)
    print("P2 finished")
elif rank == 3:
    req = comm.irecv(source=1, tag=13)
    data = req.wait()
    print("P3 received: {}", data)
    print("P3 finished")
