import sys
import subprocess

def flush_print(*margs, **mkwargs):
    print(*margs, file=sys.stdout, flush=True, **mkwargs)


def oscommand(command_list, **kwargs):
    flush_print("Executing: ", command_list)
    stdout = subprocess.check_output(command_list, **kwargs)
    str_out = stdout.decode("utf-8")
    flush_print(str_out)
    return str_out
        

    

