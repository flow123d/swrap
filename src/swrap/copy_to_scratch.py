import os
import sys
import shutil
import argparse
import subprocess

from sexec import flush_print
import sexec


"""
    Auxiliary script for copying files to all scratchdirs on all nodes.
    Supposes using SCRATCHDIR.
"""
if __name__ == "__main__":
    flush_print("================== copy_to_scratch.py START ==================")
    local_path = sys.argv[1]

    flush_print("Hostname:", os.popen('hostname').read())
    node_names = sexec.read_node_files_from_auxdir()

    flush_print("Copy to scratchdir...")
    sexec.prepare_scratch_dir(local_path, node_names)

    flush_print("================== copy_to_scratch.py END ==================")
