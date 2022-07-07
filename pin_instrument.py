import re
import os
import sys

import pintool
import utils
import config
import profile


def print_glob_addr(glob_objs:list, glob_addr_file: str):
    with open(glob_addr_file, 'w') as f:
        for obj in glob_objs:
            obj = obj[1]
            addr = int(obj["DW_AT_location"].strip('()').split(' ')[1], 16)
            var_type = obj["DW_AT_type"]
            if mat := re.search(r'\(0x[\da-fA-F]+\s"(\w+)\[(\d+)]"\)', var_type):
                var_type = mat.group(1)
                var_num = int(mat.group(2))
                if "int64" in var_type:
                    step_size = 8
                elif "int32" in var_type:
                    step_size = 4
                elif "int16" in var_type:
                    step_size = 2
                elif "int8" in var_type:
                    step_size = 1
                else:
                    assert False, "var type: {} not implemented".format(var_type)

                for i in range(var_num):
                    f.write(hex(addr + i * step_size) + '\n')
            elif '[' not in var_type:
                f.write(hex(addr) + '\n')
            else:
                assert False, "var type: {} not implemented".format(var_type)
        f.close()


def instrument(c_src_path: str, glob_objs: list, func_objs: list, param_dict: dict, elf_path: str):
    c_src_path = os.path.abspath(c_src_path)
    glob_addr_file = c_src_path + '.globs'
    func_addr_file = c_src_path + '.funcs'
    ret_func_addr_file = c_src_path + '.retfuncs'
    param_file = c_src_path + '.param'
    trace_path = c_src_path + '.trace'

    # Preparation 1: print global variable addresses to file
    print_glob_addr(glob_objs, glob_addr_file)

    # Preparation 2: print function start addresses to file
    with open(func_addr_file, 'w') as f:
        for obj in func_objs:
            obj = obj[1]
            addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
            f.write(hex(addr) + '\n')
        f.close()

    # Preparation 3: print start addresses of functions with return values
    with open(ret_func_addr_file, 'w') as f:
        for obj in func_objs:
            obj = obj[1]
            if "DW_AT_type" in obj.keys():
                addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
                f.write(hex(addr) + '\n')
        f.close()

    # Preparation 4: print function argument types to file
    # TODO

    # run pin_tool, get raw trace
    pintool.get_raw_trace(elf_path, glob_addr_file, func_addr_file, ret_func_addr_file, './todo', trace_path)

    return trace_path


def main():
    # test
    c_src_path = "/home/lifter/Documents/WebAssembly/examples/test1090_re.c"
    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path)
    (wasm_func_objs, wasm_param_dict, wasm_func_names_list), \
        (clang_func_objs, clang_param_dict, clang_func_names_list) = profile.collect_funcs(c_src_path)

    elf_path, dwarf_path = profile.clang_dwarf(c_src_path)

    raw_trace_path = instrument(c_src_path, clang_globs, clang_func_objs, clang_param_dict, elf_path)


if __name__ == '__main__':
    main()