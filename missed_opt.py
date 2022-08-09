""" Test: try to find a missed optimization opportunity example """

import os
import re
import sys

import utils
import trace_consistency


def get_one_csmith(c_path: str):
    utils.csmith_generate(c_path)  # with size limit
    while not utils.crash_checking(c_path, opt_level='-O0'):  # undefined behaviour check is overly strict
        utils.csmith_generate(c_path)
    # while not utils.udf_checking(c_path) or not utils.crash_checking(c_path, opt_level='-O0'):  # undefined behaviour check
    #     utils.csmith_generate(c_path)


def main_test():
    file_idx = 291
    while True:
        c_path = os.path.join('./find_fo', 'test{}.c'.format(file_idx))
        #  get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')
        # output1, status = utils.run_single_prog("./missopt_cases/test{}.out".format(file_idx))
        # output2, status = utils.run_single_prog("node ./missopt_cases/test{}.js".format(file_idx))
        if len(glob_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                if len(func_perf) != 0:
                    print(file_idx)
                    break

        status, output = utils.cmd("rm ./find_fo/test{}*".format(file_idx))
        file_idx += 1
    print(file_idx)


def main():
    file_idx = 1121  # this one timeout --> undefined behaviour?
    file_idx = 1821  # check: pointed_objs --> get_wasm_strs
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


def m32_check():
    file_idx = 0
    fp_case_ids = []
    tp_case_ids = []
    while file_idx < 2000:
        c_path = os.path.join('./testcases/under_opt_gcc', 'test{}.c'.format(file_idx))
        if not os.path.exists(c_path):
            file_idx += 1
            continue
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')
        if len(glob_correct) == 0 and len(func_correct) == 0 and (len(glob_perf) != 0 or len(func_perf) != 0):
            tp_case_ids.append(file_idx)
            print(file_idx)
        else:
            fp_case_ids.append(file_idx)
            status, output = utils.cmd("mv ./testcases/under_opt_gcc/test{}.c {}".format(file_idx, "./testcases/under_opt_gcc/m32_FPs/"))

        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}.c.*".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}.out".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.js".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.wasm".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.wat".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.dwarf".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.trace".format(file_idx))
        file_idx += 1
    print("fp_list: {}\n{}".format(len(fp_case_ids), fp_case_ids))
    print("tp_list: {}\n{}".format(len(tp_case_ids), tp_case_ids))


if __name__ == '__main__':
    m32_check()
    exit(0)
    main()
