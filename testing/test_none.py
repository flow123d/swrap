from swrap.pbs_utils import make_pbs_wrappers

def test_pbs_wrappers():
    make_pbs_wrappers('sandbox', 'hostname', {'/host/dir':'/cont/dir', '/H/':'/C/'})
