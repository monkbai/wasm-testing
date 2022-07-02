import os
import re
import sys
import utils
import config


def compile_llvm_ir(c_src_path: str):
    c_src_path = os.path.abspath(c_src_path)
    dir_path = os.path.dirname(c_src_path)
    ll_path = os.path.join(dir_path, 'tmp.ll')

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.clang_dwarf_cmd2.format(c_src_path, ll_path))

    utils.project_dir = tmp_dir
    return ll_path


def get_global_vars(c_src_path: str):
    glob_vars_list = []

    ll_path = compile_llvm_ir(c_src_path)
    with open(ll_path, 'r') as f:
        ll_txt = f.read()
        ll_txt = ll_txt[:ll_txt.find('define')]
        lines = ll_txt.split('\n')
        for l in lines:
            l = l.strip()

            if l.startswith('@') and 'global' in l:
                var_name, var_type = reg_global_var(l)
                glob_vars_list.append((var_name, var_type))

    utils.cmd('rm {}'.format(ll_path))
    return glob_vars_list


def reg_global_var(line: str):
    mat = re.match("@([\.\w]+) = (\w+ )*global ((i\w+)|\[.*?\])", line)
    var_name = mat.group(1)
    var_type = mat.group(3)
    return var_name, var_type


# ========================================
# parsing LLVM IR is not robust
# turn to DWARF info
# deprecate above functions
def emscripten_dwarf(c_src_path: str):
    c_src_path = os.path.abspath(c_src_path)
    dir_path = os.path.dirname(c_src_path)
    assert c_src_path.endswith('.c')
    wasm_path = c_src_path[:-2] + '.wasm'
    js_path = c_src_path[:-2] + '.js'
    dwarf_txt_path = wasm_path + '.dwarf'

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    stdout, stderr = utils.cmd_emsdk(config.emcc_cmd.format(c_src_path, wasm_path, js_path))
    status, output = utils.cmd(config.dwarfdump_cmd.format(wasm_path, dwarf_txt_path))

    utils.project_dir = tmp_dir

    return wasm_path, js_path, dwarf_txt_path


def 


if __name__ == '__main__':
    get_global_vars("/home/lifter/Documents/WebAssembly/examples/test1090_re.c")

