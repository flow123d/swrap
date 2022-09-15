FROM ubuntu:20.04

RUN apt update && apt install -y \
  wget \
  gcc \
  g++ \
  make \
  libpsm2-dev \
  git

# install mpich
RUN wget -nv http://www.mpich.org/static/downloads/3.4.2/mpich-3.4.2.tar.gz && \
  tar xzf mpich-3.4.2.tar.gz && \
  mkdir /mpich-install && \
  cd mpich-3.4.2 && \
  ./configure --prefix=/mpich-install --with-device=ch4:ofi --disable-fortran && \
  make -j4 && \
  make install

ENV PATH /mpich-install/bin:$PATH

# install OSU Micro-Benchmarks
RUN mkdir -p /git/github.com/ULHPC && \
  cd /git/github.com/ULHPC && \
  git clone https://github.com/ULHPC/tutorials.git && \
  cd tutorials && \
  make setup && \
  cd /git/github.com/ULHPC && \
  git clone https://github.com/ULHPC/launcher-scripts.git

RUN mkdir -p /tutorials/OSU-MicroBenchmarks && \
  cd /tutorials/OSU-MicroBenchmarks && \
  ln -s /git/github.com/ULHPC/tutorials/parallel/mpi/OSU_MicroBenchmarks/ ref.ulhpc.d && \
  ln -s ref.ulhpc.d/Makefile . && \
  ln -s ref.ulhpc.d/scripts .

ENV OSU_VERSION 5.5

RUN cd /tutorials/OSU-MicroBenchmarks && \
  mkdir src && \
  cd src && \
  wget -nv --no-check-certificate http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-${OSU_VERSION}.tar.gz && \
  tar xvzf osu-micro-benchmarks-${OSU_VERSION}.tar.gz

RUN cd /tutorials/OSU-MicroBenchmarks/ && \
  mkdir build.mpich && \
  cd build.mpich && \
  ../src/osu-micro-benchmarks-${OSU_VERSION}/configure CC=mpicc CFLAGS=-I$(pwd)/../src/osu-micro-benchmarks-${OSU_VERSION}/util --prefix=$(pwd) && \
  make -j4 && make install
