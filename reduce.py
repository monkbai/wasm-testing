#!/usr/bin/env python3
import os
import stat
import time
from multiprocessing import Pool


import utils
import config
import test_wasm_opt
import trace_consistency


def generate_test_sh(test_sh_path: str, c_file: str, gt_file: str, check_type="functionality"):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)

    c_file = os.path.basename(c_file)
    test_sh_path = os.path.abspath(test_sh_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest_trace.py {} {} {}\n".format(pwd, c_file, check_type, gt_file)
    with open(test_sh_path, 'w') as f:
        f.write(sh_txt)
    os.chmod(test_sh_path, 0o777)

    return test_sh_path


def generate_crash_test_sh(test_sh_path: str, c_file: str, check_type="crash"):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)

    c_file = os.path.basename(c_file)
    test_sh_path = os.path.abspath(test_sh_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest.py {} {}\n".format(pwd, c_file, check_type)
    with open(test_sh_path, 'w') as f:
        f.write(sh_txt)
    os.chmod(test_sh_path, 0o777)

    return test_sh_path


def generate_wasmopt_test_sh(test_sh_path: str, c_file: str, gt_file: str, check_type="optimization", clang_opt='-O3', emcc_opt='-O0', wasm_opt='-O3'):
    f_path = os.path.realpath(__file__)
    pwd = os.path.dirname(f_path)

    c_file = os.path.basename(c_file)
    test_sh_path = os.path.abspath(test_sh_path)
    sh_txt = "#!/bin/bash\npython3 {}/interest_wasmopt.py {} {} {} {} {} {}\n".format(pwd, c_file, check_type, gt_file, clang_opt, emcc_opt, wasm_opt)
    with open(test_sh_path, 'w') as f:
        f.write(sh_txt)
    os.chmod(test_sh_path, 0o777)

    return test_sh_path


def generate_ground_truth(c_src_path: str, gt_path: str, clang_opt_level='-O0', emcc_opt_level='-O2'):
    obj_lists = trace_consistency.trace_check(c_src_path, clang_opt_level, emcc_opt_level)
    utils.obj_to_json(obj_lists, gt_path)


def generate_wasmopt_ground_truth(c_src_path: str, gt_path: str, clang_opt='-O3', emcc_opt='-O0', wasm_opt='-O3'):
    obj_lists = test_wasm_opt.single_test(c_src_path, clang_opt, emcc_opt, wasm_opt, run_flag=False)
    utils.obj_to_json(obj_lists, gt_path)


creduce_path = config.creduce_path


def reduce_crash(c_path: str, reduced_path: str, check_type="crash", clang_opt_level='-O0', emcc_opt_level='-O0'):
    reduced_path = os.path.abspath(reduced_path)
    if os.path.exists(reduced_path):
        # print('"{}" already exists.'.format(reduced_path))
        return

    reduced_wasm = reduced_path[:reduced_path.rfind('.c')] + '.wasm'
    reduced_js = reduced_path[:reduced_path.rfind('.c')] + '.js'
    reduced_out = reduced_path[:reduced_path.rfind('.c')] + '.out'
    test_sh_path = reduced_path[:reduced_path.rfind('.c')] + '.sh'

    c_path = os.path.abspath(c_path)
    status, output = utils.cmd('cp {} {}'.format(c_path, reduced_path))

    generate_crash_test_sh(test_sh_path, reduced_path, check_type)

    print('start reducing {}...'.format(c_path))
    # move to the target directory
    base_dir = os.path.dirname(reduced_path)
    utils.project_dir, base_dir = base_dir, utils.project_dir
    # print(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    status, output = utils.cmd(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    if status != 0:
        print('failed to reduce {}:\n'.format(c_path), output)
    # restore utils project_dir
    utils.project_dir, base_dir = base_dir, utils.project_dir
    print("{} reduced.".format(c_path))


def reduce_c(c_path: str, reduced_path: str, check_type="functionality", clang_opt_level='-O0', emcc_opt_level='-O2'):
    # TODO: this function should be able to be parallel?
    reduced_path = os.path.abspath(reduced_path)
    if os.path.exists(reduced_path):
        # print('"{}" already exists.'.format(reduced_path))
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
    # print(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    status, output = utils.cmd(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    if status != 0:
        print('failed to reduce {}:\n'.format(c_path), output)
    # restore utils project_dir
    utils.project_dir, base_dir = base_dir, utils.project_dir
    print("{} reduced.".format(c_path))


def reduce_wasmopt(c_path: str, reduced_path: str, check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3'):
    reduced_path = os.path.abspath(reduced_path)
    if os.path.exists(reduced_path):
        # print('"{}" already exists.'.format(reduced_path))
        return

    reduced_wasm = reduced_path[:reduced_path.rfind('.c')] + '.wasm'
    reduced_js = reduced_path[:reduced_path.rfind('.c')] + '.js'
    reduced_out = reduced_path[:reduced_path.rfind('.c')] + '.out'
    ground_truth_path = reduced_path[:reduced_path.rfind('.c')] + '.gt.json'
    test_sh_path = reduced_path[:reduced_path.rfind('.c')] + '.sh'

    c_path = os.path.abspath(c_path)
    status, output = utils.cmd('cp {} {}'.format(c_path, reduced_path))

    generate_wasmopt_ground_truth(reduced_path, ground_truth_path, clang_opt_level, emcc_opt_level, wasm_opt_level)

    generate_wasmopt_test_sh(test_sh_path, reduced_path, ground_truth_path, check_type, clang_opt_level, emcc_opt_level, wasm_opt_level)

    print('start reducing {}...'.format(c_path))
    # move to the target directory
    base_dir = os.path.dirname(reduced_path)
    utils.project_dir, base_dir = base_dir, utils.project_dir
    # print(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    status, output = utils.cmd(creduce_path + ' ./{} '.format(os.path.basename(test_sh_path)) + os.path.basename(reduced_path))
    if status != 0:
        print('failed to reduce {}:\n'.format(c_path), output)
    # restore utils project_dir
    utils.project_dir, base_dir = base_dir, utils.project_dir
    print("{} reduced.".format(c_path))


def reduce(error_dir='./testcases/func_bug_gcc/'):
    files = os.listdir(error_dir)
    files.sort()
    for f in files:
        if f.endswith('.c') and '_re' not in f and not os.path.exists(f[:-2]+'_re.c'):
            c_path = os.path.join(error_dir, f)
            reduced_path = c_path[:-2] + '_re.c'
            reduce_c(c_path, reduced_path, check_type="functionality", clang_opt_level='-O0', emcc_opt_level='-O3')


def reduce_opt(error_dir='./testcases/under_opt_gcc/'):
    files = os.listdir(error_dir)
    files.sort()
    for f in files:
        if f.endswith('.c') and '_ex' not in f and '_re' not in f and not os.path.exists(f[:-2]+'_re.c'):
            c_path = os.path.join(error_dir, f)
            reduced_path = c_path[:-2] + '_re.c'
            c_path = c_path[:-2] + '_ex.c'
            reduce_c(c_path, reduced_path, check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O3')


def reduce_wasmopt_dir(dir_path='./find_wasm_opt/under_opt/0-1000/'):
    files = os.listdir(dir_path)
    files.sort()
    for f in files:
        c_path = os.path.join(dir_path, f)
        if f.endswith('.c') and '_re' not in f and not os.path.exists(c_path[:-2]+'_re.c'):
            reduced_path = c_path[:-2] + '_re.c'
            reduce_wasmopt(c_path, reduced_path, check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3')


def worker(sleep_time: int):
    time.sleep(sleep_time * 5)
    try:
        # reduce()
        # reduce_opt()
        reduce_wasmopt_dir()
    except Exception as e:
        pass


if __name__ == '__main__':
    reduce_wasmopt("./find_wasm_opt/0-1000/test9-104.c", "./find_wasm_opt/0-1000/test9-104_re.c", check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3')
    exit(0)
    # reduce_c('./testcases/func_bug_clang/test1072.c', './testcases/func_bug_clang/test1072_re.c', check_type="functionality", clang_opt_level='-O0', emcc_opt_level='-O2')
    # reduce_crash('./test8-78.c', './test8-78_re.c', check_type="crash", clang_opt_level='-O0', emcc_opt_level='-O0')

    # reduce_wasmopt('./test13-3.c', './test13-3_re.c', check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3')
    # reduce_wasmopt('./test11-9985.c', './test11-9985_re.c', check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3')
    # reduce_wasmopt('./test1-643.c', './test1-643_re.c', check_type="optimization", clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_level='-O3')
    # reduce()
    # reduce_opt()
    # exit(0)

    with Pool(32) as p:
        p.starmap(worker, [(i,) for i in range(32)])
