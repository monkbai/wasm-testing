""" Test: try to find a missed optimization opportunity example """

import os
import re
import sys

import utils
import add_extern
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


def main(dir_path='./testcases'):
    file_idx = 1121  # this one timeout --> undefined behaviour?
    file_idx = 1821  # check: pointed_objs --> get_wasm_strs
    file_idx = 0
    while file_idx < 2000:
        c_path = os.path.join(dir_path, 'test{}.c'.format(file_idx))
        # get_one_csmith(c_path)
        if not os.path.exists(c_path):
            file_idx += 1
            continue

        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')
        output1, status = utils.run_single_prog("./testcases/test{}.out".format(file_idx))
        output2, status = utils.run_single_prog("node ./testcases/test{}.js".format(file_idx))
        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                f1 = os.path.join(dir_path, 'test{}.c'.format(file_idx))
                f2 = os.path.join(dir_path + '/under_opt_clang', 'test{}.c'.format(file_idx))
                status, output = utils.cmd("cp {} {}".format(f1, f2))
            else:
                pass
                # f1 = os.path.join(dir_path, 'test{}.c'.format(file_idx))
                # f2 = os.path.join(dir_path + '/O3_FPs', 'test{}.c'.format(file_idx))
                # status, output = utils.cmd("cp {} {}".format(f1, f2))
        elif len(glob_correct) != 0 or len(func_correct) != 0:
            if output1 == output2:
                print("same checksum.")
                f1 = os.path.join(dir_path, 'test{}.c'.format(file_idx))
                f2 = os.path.join(dir_path + '/func_bug_clang/O3_FPs', 'test{}.c'.format(file_idx))
                status, output = utils.cmd("cp {} {}".format(f1, f2))
            else:
                f1 = os.path.join(dir_path, 'test{}.c'.format(file_idx))
                f2 = os.path.join(dir_path + '/func_bug_clang', 'test{}.c'.format(file_idx))
                status, output = utils.cmd("cp {} {}".format(f1, f2))

        # input('continue?')
        status, output = utils.cmd("rm {}/test{}.c.*".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/test{}.out".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/*.js".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/*.wasm".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/*.wat".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/*.dwarf".format(dir_path, file_idx))
        status, output = utils.cmd("rm {}/*.trace".format(dir_path, file_idx))
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


def extern_check():
    file_idx = 0
    fp_case_ids = []
    tp_case_ids = []
    while file_idx < 2000:
        c_path = os.path.join('./testcases/under_opt_gcc', 'test{}.c'.format(file_idx))
        if not os.path.exists(c_path):
            file_idx += 1
            continue
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3')

        glob_name_list = []
        for g_p in glob_perf:
            if ':' in g_p:
                g_p = g_p[:g_p.find(':')]
            glob_name_list.append(g_p)

        new_c_path = os.path.join('./testcases/under_opt_gcc', 'test{}_ex.c'.format(file_idx))
        add_extern.add_extern_specifier(c_path, new_c_path, glob_name_list)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(new_c_path, clang_opt_level='-O3', emcc_opt_level='-O3')

        if len(glob_correct) == 0 and len(func_correct) == 0 and (len(glob_perf) != 0 or len(func_perf) != 0):
            tp_case_ids.append(file_idx)
            print(file_idx)
        else:
            fp_case_ids.append(file_idx)
            status, output = utils.cmd("mv ./testcases/under_opt_gcc/test{}.c {}".format(file_idx, "./testcases/under_opt_gcc/extern_FPs/"))
            status, output = utils.cmd("mv ./testcases/under_opt_gcc/test{}_ex.c {}".format(file_idx, "./testcases/under_opt_gcc/extern_FPs/"))

        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}.c.*".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}_ex.c.*".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}.out".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/test{}_ex.out".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.js".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.wasm".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.wat".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.dwarf".format(file_idx))
        status, output = utils.cmd("rm ./testcases/under_opt_gcc/*.trace".format(file_idx))
        file_idx += 1
    print("fp_list: {}\n{}".format(len(fp_case_ids), fp_case_ids))
    print("tp_list: {}\n{}".format(len(tp_case_ids), tp_case_ids))


if __name__ == '__main__':
    # m32_check()
    # extern_check()
    # exit(0)
    main('./testcases')
