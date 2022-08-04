#!/usr/bin/env python3
""" Deprecated """

import os
import sys

import utils
import trace_consistency


def list_compare(list1: list, list2: list):
    # list1 should be the ground truth
    if len(set(list1).intersection(list2)) != len(list1):
        return False
    return True


def list_compare_strict(list1: list, list2: list):
    # list1 should be the ground truth
    if len(list2) != len(list1):
        return False
    if len(set(list1).intersection(list2)) != len(list1):
        return False
    return True


def update_ground_truth():
    # TODO: should we update the ground truth each time?
    pass


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
    elif "tentative array" in output:
        exit(-1)


def main(tmp_c: str, interest_type='functionality', clang_opt_level='-O0', emcc_opt_level='-O2'):
    tmp_c = os.path.abspath(tmp_c)
    # TODO: what if do not keep <func_1>
    # with open(tmp_c, 'r') as f:
    #     if 'func_1' not in f.read():
    #         exit(-1)  # keep func_1
    udf_checking(c_path=tmp_c)
    if not utils.crash_checking(c_path=tmp_c, opt_level=clang_opt_level):
        exit(-1)

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


glob_corr_list = ['crc32_context', 'g_61']
func_corr_list = ['transparent_crc']
glob_perf_list = []
func_perf_list = []


def get_ground_truth(json_path: str):
    global glob_corr_list, func_corr_list, glob_perf_list, func_perf_list
    glob_corr_list, func_corr_list, glob_perf_list, func_perf_list = utils.json_to_obj(json_path)


if __name__ == '__main__':
    # get_ground_truth('test319.consis.json')
    # main('./debug_cases/test319.c', interest_type='functionality', clang_opt_level='-O2', emcc_opt_level='-O2')
    # main('./tmp.c', interest_type='functionality', clang_opt_level='-O0', emcc_opt_level='-O2')

    if len(sys.argv) == 4:
        get_ground_truth(sys.argv[3])
        if sys.argv[2].startswith('function'):
            main(sys.argv[1])
        elif sys.argv[2].startswith('optimization'):
            main(sys.argv[1], sys.argv[2], '-O3', '-O3')
        else:
            exit(-1)
    else:
        exit(-1)
