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
    file_idx = 1
    while True:
        c_path = os.path.join('./missopt_cases', 'test{}.c'.format(file_idx))
        # get_one_csmith(c_path)
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path)
        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                break
            output1, status = utils.run_single_prog("./missopt_cases/test{}.out".format(file_idx))
            output2, status = utils.run_single_prog("node ./missopt_cases/test{}.js".format(file_idx))
            if output1.strip() != output2.strip():
                status, output = utils.cmd(
                    "cp ./missopt_cases/test{}.c ./tmp2_cases/test{}.c".format(file_idx, file_idx))
        else:
            status, output = utils.cmd("cp ./missopt_cases/test{}.c ./tmp_cases/test{}.c".format(file_idx, file_idx))

        status, output = utils.cmd("rm ./missopt_cases/test{}*".format(file_idx))
        file_idx += 1
    print(file_idx)


if __name__ == '__main__':
    main()