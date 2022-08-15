import os
import re

import utils
import profile
import trace_consistency


def simple_test(process_idx: int):
    """ Clang O3 vs. Emcc O0 + wasm-opt O3
        Mainly focus on the functionality errors
    """
    file_idx = 0
    while True:
        tmp_file_idx = file_idx
        file_idx += 1
        # print(tmp_file_idx)
        c_path = os.path.join('./find_wasm_opt_bug', 'test{}-{}.c'.format(process_idx, tmp_file_idx))
        utils.get_one_csmith(c_path)

        wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
        elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O3')

        wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O3')

        # lightweight checking
        output1, status = utils.run_single_prog(elf_path)
        output2, status = utils.run_single_prog("node {}".format(js_path))

        # heavyweight checking
        # glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3', need_compile=False)

        if output1 != output2:
            continue
        else:
            status, output = utils.cmd("rm ./find_wasm_opt/test{}-{}.*".format(process_idx, tmp_file_idx))

    # print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))


def trace_test(process_idx: int):
    """ Clang O3 vs. Emcc O0 + wasm-opt O3
        Mainly focus on the under-optimization issues
    """
    file_idx = 0
    while True:
        tmp_file_idx = file_idx
        file_idx += 1
        # print(tmp_file_idx)
        c_path = os.path.join('./find_wasm_opt', 'test{}-{}.c'.format(process_idx, tmp_file_idx))
        utils.get_one_csmith(c_path)

        wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
        elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O3')

        wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O3')

        # lightweight checking
        output1, status = utils.run_single_prog(elf_path)
        output2, status = utils.run_single_prog("node {}".format(js_path))

        # heavyweight checking
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3', need_compile=False)

        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                status, output = utils.cmd("mv ./find_wasm_opt/test{}-{}.* ./find_wasm_opt/under_opt".format(process_idx, tmp_file_idx))
            else:
                status, output = utils.cmd("mv ./find_wasm_opt/test{}-{}.* ./find_wasm_opt/func_bug".format(process_idx, tmp_file_idx))

        status, output = utils.cmd("rm ./find_wasm_opt/test{}-{}.*".format(process_idx, tmp_file_idx))

    # print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))


if __name__ == '__main__':
    # simple_test(0)
    trace_test(0)
