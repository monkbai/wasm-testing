#!/usr/bin/env python3
import os
import stat


import utils
import config
import trace_consistency


def generate_test_sh(c_file: str, gt_file: str):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest_trace.py {} functionality {}\n".format(pwd, c_file, gt_file)
    with open('test.sh', 'w') as f:
        f.write(sh_txt)
    os.chmod('test.sh', 0o777)


def generate_perf_test_sh(c_file: str, gt_file):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest_trace.py {} optimization {}\n".format(pwd, c_file, gt_file)
    with open('test.sh', 'w') as f:
        f.write(sh_txt)
    os.chmod('test.sh', 0o777)


def generate_ground_truth(c_src_path: str, gt_path: str, clang_opt_level='-O0', emcc_opt_level='-O2'):
    c_src_path = './tmp.c'
    obj_lists = trace_consistency.trace_check(c_src_path, clang_opt_level, emcc_opt_level)
    utils.obj_to_json(obj_lists, gt_path)


creduce_path = config.creduce_path


def reduce_c(c_path: str, reduced_path: str, clang_opt_level='-O0', emcc_opt_level='-O2'):
    # TODO
    reduced_path = os.path.abspath(reduced_path)
    if os.path.exists(reduced_path):
        print('"{}" already exists.'.format(reduced_path))
        return

    reduced_wasm = reduced_path[:reduced_path.rfind('.c')] + '.wasm'
    reduced_js = reduced_path[:reduced_path.rfind('.c')] + '.js'
    reduced_out = reduced_path[:reduced_path.rfind('.c')] + '.out'
    ground_truth_path = reduced_path[:reduced_path.rfind('.c')] + '.gt.json'

    c_path = os.path.abspath(c_path)
    status, output = utils.cmd('cp {} {}'.format(c_path, reduced_path))

    generate_ground_truth(reduced_path, ground_truth_path, clang_opt_level, emcc_opt_level)

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
