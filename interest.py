#!/usr/bin/env python3
import os
import sys
import subprocess
from threading import Timer

import utils
import profile


def main(tmp_c: str, interest_type='crash', clang_opt_level='-O0', emcc_opt_level='-O0'):
    if not interest_type.startswith("crash"):
        exit(-1)

    tmp_c = os.path.abspath(tmp_c)
    if not utils.udf_checking(c_path=tmp_c):
        exit(-1)
    if not utils.compile_checking(c_path=tmp_c, opt_level=clang_opt_level):
        exit(-1)
    if not utils.crash_checking(c_path=tmp_c, opt_level=clang_opt_level):
        exit(-1)

    tmp_out = tmp_c[:tmp_c.rfind('.')] + '.out'
    tmp_wasm = tmp_c[:tmp_c.rfind('.')] + '.wasm'
    tmp_js = tmp_c[:tmp_c.rfind('.')] + '.js'
    utils.cmd("rm {}".format(tmp_out))
    utils.cmd("rm {}".format(tmp_wasm))
    utils.cmd("rm {}".format(tmp_js))

    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(tmp_c, opt_level=emcc_opt_level)
    elf_path, dwarf_path = profile.clang_dwarf(tmp_c, opt_level=clang_opt_level)

    # check compilation results
    if not os.path.exists(tmp_out) or not os.path.exists(tmp_js) or not os.path.exists(tmp_wasm):
        exit(-1)

    output1, status1 = utils.run_single_prog(elf_path)
    output2, status2 = utils.run_single_prog("node {}".format(js_path))

    if status1 or status2:
        exit(0)  # case 1: one program did not exit normally
    elif output1.strip() != output2.strip():
        exit(0)  # case 2: inconsistent output

    # try with wasm-opt and check again
    wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O4')
    # output1, status1 = utils.run_single_prog(elf_path)
    output2, status2 = utils.run_single_prog("node {}".format(js_path))

    if status1 or status2:
        exit(0)  # case 1: one program did not exit normally
    elif output1.strip() != output2.strip():
        exit(0)  # case 2: inconsistent output

    exit(-1)


if __name__ == '__main__':
    main('./test8-78_re.c', "crash", '-O0', '-O0')
    if len(sys.argv) == 3:
        if sys.argv[2].startswith('crash'):
            main(sys.argv[1], sys.argv[2], '-O0', '-O0')
        else:
            exit(-1)
    else:
        exit(-1)
