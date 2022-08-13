""" Test: try to find a missed optimization opportunity example """

import os
import re
import sys

import utils
import profile
import trace_consistency


def get_one_csmith(c_path: str):
    utils.csmith_generate(c_path)  # with size limit
    while not utils.udf_checking(c_path) or not utils.crash_checking(c_path, opt_level='-O0'):  # undefined behaviour check
        utils.csmith_generate(c_path)


def main():
    file_idx = 261
    while file_idx < 1001:
        c_path = os.path.join('./inconsis_trace/testcases', 'test{}.c'.format(file_idx))
        get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O0', emcc_opt_level='-O2')
        output1, status = utils.run_single_prog("./inconsis_trace/testcases/test{}.out".format(file_idx))
        output2, status = utils.run_single_prog("node ./inconsis_trace/testcases/test{}.js".format(file_idx))
        if len(glob_correct) == 0 and len(func_correct) == 0:
            if output1.strip() != output2.strip():
                status, output = utils.cmd(
                    "cp ./inconsis_trace/testcases/test{}.c ./inconsis_trace/FNs/test{}.c".format(file_idx, file_idx))
        else:
            if output1.strip() != output2.strip():
                status, output = utils.cmd("cp ./inconsis_trace/testcases/test{}.c ./inconsis_trace/bug_cases/test{}.c".format(file_idx, file_idx))
            else:
                status, output = utils.cmd(
                    "cp ./inconsis_trace/testcases/test{}.c ./inconsis_trace/FPs/test{}.c".format(file_idx, file_idx))

        status, output = utils.cmd("rm ./inconsis_trace/testcases/test{}.c.*".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/test{}.out".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/*.js".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/*.wasm".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/*.wat".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/*.dwarf".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/testcases/*.trace".format(file_idx))
        file_idx += 1
    print(file_idx)


def fix_recheck():
    fixed_list = []
    file_idx = 0
    while file_idx < 270:
        c_path = os.path.join('./inconsis_trace/FPs', 'test{}.c'.format(file_idx))
        if not os.path.exists(c_path):
            file_idx += 1
            continue
        # get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O0', emcc_opt_level='-O2')
        output1, status = utils.run_single_prog("./inconsis_trace/FPs/test{}.out".format(file_idx))
        output2, status = utils.run_single_prog("node ./inconsis_trace/FPs/test{}.js".format(file_idx))
        if len(glob_correct) == 0 and len(func_correct) == 0:
            fixed_list.append(file_idx)
        else:
            print(file_idx)

        status, output = utils.cmd("rm ./inconsis_trace/FPs/test{}.c.*".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/test{}.out".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/*.js".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/*.wasm".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/*.wat".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/*.dwarf".format(file_idx))
        status, output = utils.cmd("rm ./inconsis_trace/FPs/*.trace".format(file_idx))
        file_idx += 1
    print(fixed_list)


def m32_check(dir_path: str):
    # Re-run the experiment with -m32 option
    fp_list = []  # False Positives due to w/o -m32 option
    tp_list = []
    file_idx = 0  # 1634 floating point exception
    while file_idx < 2000:
        c_path = os.path.join(dir_path, 'test{}.c'.format(file_idx))
        if not os.path.exists(c_path):
            file_idx += 1
            continue

        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O0', emcc_opt_level='-O2')

        if len(glob_correct) == 0 and len(func_correct) == 0 and len(glob_perf) == 0 and len(func_perf) == 0:
            utils.cmd("mv {} {}".format(c_path, os.path.join(dir_path, "m32_FPs")))
            fp_list.append(file_idx)
        else:
            tp_list.append(file_idx)

        file_idx += 1
    print("fp_list: {}\n{}".format(len(fp_list), fp_list))
    print("tp_list: {}\n{}".format(len(tp_list), tp_list))


def main_emi(dir_path="/home/tester/Documents/EMI/DecFuzzer/testcases_emi"):
    for i in range(200):
        for j in range(10):
            c_path = os.path.join(dir_path, 'test{}-{}.c'.format(i, j))

            out_path = c_path[:-2] + '.out'
            js_path = c_path[:-2] + '.js'

            glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path,
                                                                                             clang_opt_level='-O0',
                                                                                             emcc_opt_level='-O2')

            wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O2')
            output1, status = utils.run_single_prog(out_path)
            output2, status = utils.run_single_prog("node {}".format(js_path))
            if len(glob_correct) == 0 and len(func_correct) == 0:
                if output1.strip() != output2.strip():
                    f1 = os.path.join(dir_path + '/func_bug_FNs', 'test{}-{}.c'.format(i, j))
                    status, output = utils.cmd("cp {} {}".format(c_path, f1))
            else:
                if output1.strip() != output2.strip():
                    f1 = os.path.join(dir_path + '/func_bug_clang15', 'test{}-{}.c'.format(i, j))
                    status, output = utils.cmd("cp {} {}".format(c_path, f1))
                else:
                    f1 = os.path.join(dir_path + '/func_bug_FPs', 'test{}-{}.c'.format(i, j))
                    status, output = utils.cmd("cp {} {}".format(c_path, f1))


if __name__ == '__main__':
    # fix_recheck()
    # m32_check("./debug_cases/")
    # exit(0)

    # main()
    main_emi()

