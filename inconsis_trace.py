""" Test: try to find a missed optimization opportunity example """

import os
import re
import sys

import utils
import trace_consistency


def get_one_csmith(c_path: str):
    utils.csmith_generate(c_path)  # with size limit
    while not utils.udf_checking(c_path):  # undefined behaviour check
        utils.csmith_generate(c_path)


def main():
    file_idx = 22
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


if __name__ == '__main__':
    main()
