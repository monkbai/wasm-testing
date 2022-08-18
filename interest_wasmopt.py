#!/usr/bin/env python3

import os
import sys

import utils
import profile
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


def update_ground_truth(gc_list: list, fc_list: list, go_list: list, fo_list: list):
    # TODO: should we update the ground truth each time?
    # Try and see what happen
    glob_corr_list = ['crc32_context', 'g_61']
    func_corr_list = ['transparent_crc']
    glob_perf_list = []
    func_perf_list = []
    if len(gc_list) > len(glob_corr_list) or len(fc_list) > len(func_corr_list) or \
            len(go_list) > len(glob_perf_list) or len(fo_list) > len(func_perf_list):
        utils.obj_to_json([gc_list, fc_list, go_list, fo_list], gt_json_path)


def preserved_keywords(c_path: str, key_list: list):
    with open(c_path, 'r') as f:
        txt = f.read()
        for k in key_list:
            if k not in txt:
                return False
        return True


def main(tmp_c: str, interest_type='optimization', clang_opt_level='-O3', emcc_opt_level='-O0', wasm_opt_option="-O3"):
    tmp_c = os.path.abspath(tmp_c)

    if not utils.udf_checking(c_path=tmp_c):
        exit(-1)
    if not utils.compile_checking(c_path=tmp_c, opt_level=clang_opt_level):
        exit(-1)
    if not utils.crash_checking(c_path=tmp_c, opt_level=clang_opt_level):
        exit(-1)
    if not preserved_keywords(tmp_c, []):
        exit(-1)

    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(tmp_c, opt_level=emcc_opt_level)
    elf_path, dwarf_path = profile.clang_dwarf(tmp_c, opt_level=clang_opt_level)

    # output1, status1 = utils.run_single_prog(elf_path)
    # output2, status2 = utils.run_single_prog("node {}".format(js_path))

    wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level=wasm_opt_option)

    glob_correct_inconsistent_list, \
        func_correct_inconsistent_list, \
        glob_perf_inconsistent_list, \
        func_perf_inconsistent_list = trace_consistency.trace_check(tmp_c, clang_opt_level, emcc_opt_level, need_compile=False)

    if interest_type.startswith('function'):
        if len(glob_correct_inconsistent_list) > 0 or len(func_correct_inconsistent_list) > 0:
            if not list_compare(glob_corr_list, glob_correct_inconsistent_list) or \
                    not list_compare(func_corr_list, func_correct_inconsistent_list):
                exit(-1)
            # extra check: if current case is interesting
            # and also the inconsistent_list subsumes ground truth (i.e., new var/func are detected during reducing)
            # then we update the ground truth lists
            update_ground_truth(glob_correct_inconsistent_list, func_correct_inconsistent_list,
                                glob_perf_inconsistent_list, func_perf_inconsistent_list)
            exit(0)  # exit with zero when the case is still interesting
        else:
            exit(-1)
    elif interest_type.startswith('optimization'):
        if len(glob_perf_inconsistent_list) > 0 or len(func_perf_inconsistent_list) > 0:
            if not list_compare(glob_perf_list, glob_perf_inconsistent_list) or \
                    not list_compare(func_perf_list, func_perf_inconsistent_list):
                # So we do not need to update ground truth for under-opt issue?
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
gt_json_path = ""


def get_ground_truth(json_path: str):
    global glob_corr_list, func_corr_list, glob_perf_list, func_perf_list
    glob_corr_list, func_corr_list, glob_perf_list, func_perf_list = utils.json_to_obj(json_path)


if __name__ == '__main__':
    # get_ground_truth('test319.consis.json')
    # main('./debug_cases/test319.c', interest_type='functionality', clang_opt_level='-O2', emcc_opt_level='-O2')
    # main('./tmp.c', interest_type='functionality', clang_opt_level='-O0', emcc_opt_level='-O2')

    if len(sys.argv) == 7:
        gt_json_path = sys.argv[3]
        get_ground_truth(sys.argv[3])
        check_type = sys.argv[2]
        clang_opt = sys.argv[4]
        emcc_opt = sys.argv[5]
        wasm_opt = sys.argv[6]
        if sys.argv[2].startswith('function'):
            main(sys.argv[1]) # not implemented
        elif sys.argv[2].startswith('optimization'):
            main(sys.argv[1], check_type, clang_opt, emcc_opt, wasm_opt)
        else:
            exit(-1)
    else:
        exit(-1)
