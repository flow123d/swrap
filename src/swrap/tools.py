import os
import sys
import subprocess


def flush_print(*margs, **mkwargs):
    print(*margs, file=sys.stdout, flush=True, **mkwargs)


def oscommand(command_string):
    flush_print(command_string)
    flush_print(os.popen(command_string).read())


def create_ssh_agent():
    """
    Setup ssh agent and set appropriate environment variables.
    :return:
    """
    flush_print("creating ssh agent...")
    p = subprocess.Popen('ssh-agent -s',
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         shell=True, universal_newlines=True)
    outinfo, errinfo = p.communicate('ssh-agent cmd\n')
    # print(outinfo)

    lines = outinfo.split('\n')
    for line in lines:
        # trim leading and trailing whitespace
        line = line.strip()
        # ignore blank/empty lines
        if not line:
            continue
        # break off the part before the semicolon
        left, right = line.split(';', 1)
        if '=' in left:
            # get variable and value, put into os.environ
            varname, varvalue = left.split('=', 1)
            flush_print("setting variable from ssh-agent:", varname, "=", varvalue)
            os.environ[varname] = varvalue


def create_known_hosts_file(script_dir, node_file, debug=False):
    # Get ssh keys to nodes and append it to known_hosts
    ssh_known_hosts_to_append = []
    if debug:
        # ssh_known_hosts_file = 'testing_known_hosts'
        ssh_known_hosts_file = 'xxx/.ssh/testing_known_hosts'
    else:
        # assert 'HOME' in os.environ
        ssh_known_hosts_file = os.path.join(script_dir, 'known_hosts')

    flush_print("host file name:", ssh_known_hosts_file)

    ssh_known_hosts = []
    if os.path.exists(ssh_known_hosts_file):
        with open(ssh_known_hosts_file, 'r') as fp:
            ssh_known_hosts = fp.readlines()
    else:
        flush_print("creating host file...")
        dirname = os.path.dirname(ssh_known_hosts_file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    flush_print("reading host file...")
    with open(node_file) as fp:
        node_names_read = fp.read().splitlines()
        # remove duplicates
        node_names = list(dict.fromkeys(node_names_read))

    flush_print("connecting nodes...")
    for node in node_names:
        # touch all the nodes, so that they are accessible also through container
        os.popen('ssh ' + node + ' exit')
        # add the nodes to known_hosts so the fingerprint verification is skipped later
        # in shell just append # >> ~ /.ssh / known_hosts
        # or sort by 3.column in shell: 'sort -k3 -u ~/.ssh/known_hosts' and rewrite
        ssh_keys = os.popen('ssh-keyscan -H ' + node).readlines()
        ssh_keys = list((line for line in ssh_keys if not line.startswith('#')))
        for sk in ssh_keys:
            splits = sk.split(" ")
            if not splits[2] in ssh_known_hosts:
                ssh_known_hosts_to_append.append(sk)

    flush_print("finishing host file...")
    with open(ssh_known_hosts_file, 'a') as fp:
        fp.writelines(ssh_known_hosts_to_append)

    return node_names
