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


def main(tmp_c: str):
    tmp_c = os.path.abspath(tmp_c)
    # TODO: what if do not keep <func_1>
    # with open(tmp_c, 'r') as f:
    #     if 'func_1' not in f.read():
    #         exit(-1)  # keep func_1
    udf_checking(c_path=tmp_c)

    glob_correct_inconsistent_list, \
        func_correct_inconsistent_list, \
        glob_perf_inconsistent_list, \
        func_perf_inconsistent_list = trace_consistency.trace_check(tmp_c)

    glob_list = ['crc32_context', 'g_13']
    func_list = ['transparent_crc']
    if len(glob_correct_inconsistent_list) > 0 or len(func_correct_inconsistent_list) > 0:
        if not list_compare(glob_list, glob_correct_inconsistent_list) or \
                not list_compare(func_list, func_correct_inconsistent_list):
            exit(-1)
        exit(0)
    else:
        exit(-1)


if __name__ == '__main__':
    # main('./missopt_cases/test1.c')
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        exit(-1)
