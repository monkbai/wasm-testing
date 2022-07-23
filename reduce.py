#!/usr/bin/env python3
""" Deprecated """

import os
import stat


import utils
import config
import trace_consistency


def generate_test_sh():
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest.py tmp.c functionality\n".format(pwd, pwd)
    with open('test.sh', 'w') as f:
        f.write(sh_txt)
    os.chmod('test.sh', 0o777)


def generate_perf_test_sh():
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest.py tmp.c optimization\n".format(pwd, pwd)
    with open('test.sh', 'w') as f:
        f.write(sh_txt)
    os.chmod('test.sh', 0o777)


def generate_ground_truth():
    pass


creduce_path = config.creduce_path


def reduce_c(c_path: str, reduced_path: str):
    reduced_path = os.path.abspath(reduced_path)
    reduced_wasm = reduced_path[:reduced_path.rfind('.c')] + '.wasm'
    reduced_js = reduced_path[:reduced_path.rfind('.c')] + '.js'
    reduced_out = reduced_path[:reduced_path.rfind('.c')] + '.out'

    c_path = os.path.abspath(c_path)
    status, output = utils.cmd('cp {} {}'.format(c_path, './tmp.c'))

    generate_test_sh()
    print('reducing {}...'.format(c_path))
    status, output = utils.cmd(creduce_path + ' ./test.sh tmp.c')
    if status != 0:
        print(c_path, '\n', output)

    status, output = utils.cmd('cp {} {}'.format('./tmp.c', reduced_path))
    status, output = utils.cmd('cp {} {}'.format('./tmp.wasm', reduced_wasm))
    status, output = utils.cmd('cp {} {}'.format('./tmp.js', reduced_js))
    status, output = utils.cmd('cp {} {}'.format('./tmp.out', reduced_out))

    status, output = utils.cmd('rm ./tmp.c')
    status, output = utils.cmd('rm ./tmp.out')
    status, output = utils.cmd('rm ./tmp.wasm')
    status, output = utils.cmd('rm ./tmp.js')


def reduce(error_dir='./errorcases'):
    files = os.listdir(error_dir)
    files.sort()
    for f in files:
        if f.endswith('.c') and '_re' not in f and not os.path.exists(f[:-2]+'_re.c'):
            c_path = os.path.join(error_dir, f)
            reduced_path = c_path[:-2] + '_re.c'
            reduce_c(c_path, reduced_path)


if __name__ == '__main__':
    reduce_c('./test1023.c', './test1023_re.c')
    reduce()
