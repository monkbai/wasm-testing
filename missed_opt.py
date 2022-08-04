""" Test: try to find a missed optimization opportunity example """

import os
import re
import sys

import utils
import trace_consistency


def get_one_csmith(c_path: str):
    utils.csmith_generate(c_path)  # with size limit
    while not utils.udf_checking(c_path) or not utils.crash_checking(c_path, opt_level='-O0'):  # undefined behaviour check
        utils.csmith_generate(c_path)


def main_test():
    file_idx = 27
    while True:
        c_path = os.path.join('./missopt_cases', 'test{}.c'.format(file_idx))
        get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')
        output1, status = utils.run_single_prog("./missopt_cases/test{}.out".format(file_idx))
        output2, status = utils.run_single_prog("node ./missopt_cases/test{}.js".format(file_idx))
        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                break

            if output1.strip() != output2.strip():
                status, output = utils.cmd(
                    "cp ./missopt_cases/test{}.c ./tmp2_cases/test{}.c".format(file_idx, file_idx))
        else:
            if output1.strip() != output2.strip():
                status, output = utils.cmd("cp ./missopt_cases/test{}.c ./tmp_cases/test{}.c".format(file_idx, file_idx))

        status, output = utils.cmd("rm ./missopt_cases/test{}*".format(file_idx))
        file_idx += 1
    print(file_idx)


def main():
    file_idx = 945
    while file_idx < 2000:
        c_path = os.path.join('./testcases', 'test{}.c'.format(file_idx))
        # get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')
        # output1, status = utils.run_single_prog("./testcases/test{}.out".format(file_idx))
        # output2, status = utils.run_single_prog("node ./testcases/test{}.js".format(file_idx))
        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                status, output = utils.cmd("cp ./testcases/test{}.c ./testcases/under_opt_gcc/test{}.c".format(file_idx, file_idx))
        elif len(glob_correct) != 0 or len(func_correct) != 0:
            status, output = utils.cmd("cp ./testcases/test{}.c ./testcases/func_bug_gcc/test{}.c".format(file_idx, file_idx))

        status, output = utils.cmd("rm ./testcases/test{}.c.*".format(file_idx))
        status, output = utils.cmd("rm ./testcases/test{}.out".format(file_idx))
        status, output = utils.cmd("rm ./testcases/*.js".format(file_idx))
        status, output = utils.cmd("rm ./testcases/*.wasm".format(file_idx))
        status, output = utils.cmd("rm ./testcases/*.wat".format(file_idx))
        status, output = utils.cmd("rm ./testcases/*.dwarf".format(file_idx))
        status, output = utils.cmd("rm ./testcases/*.trace".format(file_idx))
        file_idx += 1
    print(file_idx)


if __name__ == '__main__':
    main()
