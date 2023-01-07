import os
import sys


def flush_print(*margs, **mkwargs):
    print(*margs, file=sys.stdout, flush=True, **mkwargs)


def oscommand(command_string):
    flush_print(command_string)
    stdout=os.popen(command_string).read()
    flush_print(stdout)
    return stdout