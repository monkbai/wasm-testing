#!/usr/bin/env python3
import os
import stat


import utils
import config
import trace_consistency


def generate_test_sh(test_sh_path: str, c_file: str, gt_file: str, check_type="functionality"):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)

    c_file = os.path.basename(c_file)
    test_sh_path = os.path.abspath(test_sh_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest_trace.py {} {} {}\n".format(pwd, c_file, check_type, gt_file)
    with open(test_sh_path, 'w') as f:
        f.write(sh_txt)
    os.chmod('test.sh', 0o777)

    return test_sh_path


def generate_ground_truth(c_src_path: str, gt_path: str, clang_opt_level='-O0', emcc_opt_level='-O2'):
    obj_lists = trace_consistency.trace_check(c_src_path, clang_opt_level, emcc_opt_level)
    utils.obj_to_json(obj_lists, gt_path)


creduce_path = config.creduce_path


def reduce_c(c_path: str, reduced_path: str, check_type="functionality", clang_opt_level='-O0', emcc_opt_level='-O2'):
    # TODO: this function should be able to be parallel?
    reduced_path = os.path.abspath(reduced_path)
    if os.path.exists(reduced_path):
        print('"{}" already exists.'.format(reduced_path))
        return

    reduced_wasm = reduced_path[:reduced_path.rfind('.c')] + '.wasm'
    reduced_js = reduced_path[:reduced_path.rfind('.c')] + '.js'
    reduced_out = reduced_path[:reduced_path.rfind('.c')] + '.out'
    ground_truth_path = reduced_path[:reduced_path.rfind('.c')] + '.gt.json'
    test_sh_path = reduced_path[:reduced_path.rfind('.c')] + '.sh'

    c_path = os.path.abspath(c_path)
    status, output = utils.cmd('cp {} {}'.format(c_path, reduced_path))

    generate_ground_truth(reduced_path, ground_truth_path, clang_opt_level, emcc_opt_level)

    generate_test_sh(test_sh_path, reduced_path, ground_truth_path, check_type)

    print('start reducing {}...'.format(c_path))
    # move to the target directory
    base_dir = os.path.dirname(reduced_path)
    utils.project_dir, base_dir = base_dir, utils.project_dir
    status, output = utils.cmd(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    if status != 0:
        print('failed to reduce {}:\n'.format(c_path), output)
    # restore utils project_dir
    utils.project_dir, base_dir = base_dir, utils.project_dir


def reduce(error_dir='./errorcases'):
    files = os.listdir(error_dir)
    files.sort()
    for f in files:
        if f.endswith('.c') and '_re' not in f and not os.path.exists(f[:-2]+'_re.c'):
            c_path = os.path.join(error_dir, f)
            reduced_path = c_path[:-2] + '_re.c'
            reduce_c(c_path, reduced_path)


if __name__ == '__main__':
    reduce_c('./debug_cases/test336.c', './debug_cases/test336_re.c', check_type="functionality", clang_opt_level='-O0', emcc_opt_level='-O2')
    reduce()
