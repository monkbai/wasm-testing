#!/usr/bin/env python3
""" Deprecated """

import os
import sys

import utils
import trace_consistency


def list_compare(list1: list, list2: list):
    if len(list2) != len(list1):
        return False
    if len(set(list1).intersection(list2)) != len(list1):
        return False
    return True


def udf_checking(c_path: str):
    """ Checking for undefined behaviors
        1. Assigned value is garbage or undefined [clang-analyzer-core.uninitialized.Assign]
        2. The right operand of '>>' is a garbage value [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. The result of the left shift is undefined because the right operand is negative [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. warning: more '%' conversions than data arguments [clang-diagnostic-format-insufficient-args]
    """
    status, output = utils.cmd("clang-tidy-12 {} -- -I/home/tester/Documents/csmith/runtime".format(c_path))
    if 'Assigned value is garbage or undefined' in output:
        exit(-1)
    elif 'garbage value' in output:
        exit(-1)
    # elif 'is undefined' in output:
    #     exit(-1)
    elif "more '%' conversions than data arguments" in output:
        exit(-1)


def main(tmp_c: str, interest_type='functionality', clang_opt_level='-O0', emcc_opt_level='-O2'):
    tmp_c = os.path.abspath(tmp_c)
    # TODO: what if do not keep <func_1>
    # with open(tmp_c, 'r') as f:
    #     if 'func_1' not in f.read():
    #         exit(-1)  # keep func_1
    udf_checking(c_path=tmp_c)

    glob_correct_inconsistent_list, \
        func_correct_inconsistent_list, \
        glob_perf_inconsistent_list, \
        func_perf_inconsistent_list = trace_consistency.trace_check(tmp_c, clang_opt_level, emcc_opt_level)

    if interest_type.startswith('function'):
        if len(glob_correct_inconsistent_list) > 0 or len(func_correct_inconsistent_list) > 0:
            if not list_compare(glob_corr_list, glob_correct_inconsistent_list) or \
                    not list_compare(func_corr_list, func_correct_inconsistent_list):
                exit(-1)
            exit(0)
        else:
            exit(-1)
    elif interest_type.startswith('optimization'):
        if len(glob_perf_inconsistent_list) > 0 or len(func_perf_inconsistent_list) > 0:
            if not list_compare(glob_perf_list, glob_perf_inconsistent_list) or \
                    not list_compare(func_perf_list, func_perf_inconsistent_list):
                exit(-1)
            exit(0)
        else:
            exit(-1)
    else:
        exit(-1)


glob_corr_list = []
func_corr_list = []
glob_perf_list = ['g_48[3][7]', 'g_48[3][8]', 'g_48[3][5]', 'g_48[3][6]', 'g_48[3][3]', 'g_48[3][4]', 'g_48[3][1]', 'g_48[3][2]', 'g_48[2][8]', 'g_48[3][0]', 'g_48[2][6]', 'g_48[2][7]', 'g_48[2][4]', 'g_48[2][5]', 'g_48[2][2]', 'g_48[2][3]', 'g_48[2][0]', 'g_48[2][1]', 'g_48[1][7]', 'g_48[1][8]', 'g_48[1][5]', 'g_48[1][6]', 'g_48[1][3]', 'g_48[1][4]', 'g_48[1][1]', 'g_48[1][2]', 'g_48[0][8]', 'g_48[1][0]', 'g_48[0][6]', 'g_48[0][7]', 'g_48[0][4]', 'g_48[0][5]', 'g_48[0][2]', 'g_48[0][3]', 'g_48[0][0]', 'g_48[0][1]']
func_perf_list = []


if __name__ == '__main__':
    # main('./inconsis_trace/bug_cases/test179.c')
    main('./tmp.c', interest_type='optimization', clang_opt_level='-O3', emcc_opt_level='-O3')
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        if sys.argv[2].startswith('function'):
            main(sys.argv[1])
        elif sys.argv[2].startswith('optimization'):
            main(sys.argv[1], sys.argv[2], '-O3', '-O3')
        else:
            exit(-1)
    else:
        exit(-1)
