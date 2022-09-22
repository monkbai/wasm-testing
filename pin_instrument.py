import re
import os
import sys

import lcs
import pintool
import utils
import config
import profile


def print_glob_addr(glob_objs: list, glob_addr_file: str):
    with open(glob_addr_file, 'w') as f:
        for addr, (name, wasm_addr) in lcs.PtrItem.clang_objs_dict.items():
            f.write(hex(addr) + '\n')
        f.close()


def print_func_arg_size(func_objs: list, param_dict: dict, func_param_file: str):
    with open(func_param_file, 'w') as f:
        for obj in func_objs:
            obj = obj[1]
            func_name = obj["DW_AT_name"]

            if "DW_AT_low_pc" not in obj:
                continue

            if ' ' in obj["DW_AT_low_pc"]:
                func_addr = int(obj["DW_AT_low_pc"].strip('()').split(' ')[1], 16)
            else:
                func_addr = int(obj["DW_AT_low_pc"].strip('()'), 16)

            if func_name not in param_dict.keys():
                param_list = []
            else:
                param_list = param_dict[func_name]

            # if len(param_list) == 0:
            #     continue

            f.write(hex(func_addr) + '\n')
            f.write(str(len(param_list)) + '\n')
            arg_print_count = 0
            for param in param_list:
                arg_type = param["DW_AT_type"]
                arg_type = arg_type.replace('const ', '')
                arg_type = arg_type.replace('unsigned ', '')  # we only care about the size
                arg_type = arg_type.replace('signed ', '')
                if mat := re.search(r'\(0x[\da-fA-F]+\s"([\w\s]+)"\)', arg_type):
                    arg_type = mat.group(1)
                    if "int64" in arg_type or "long long" in arg_type:
                        arg_size = 8
                    elif "int32" in arg_type or arg_type == 'int':
                        arg_size = 4
                    elif "int16" in arg_type or "short" in arg_type:
                        arg_size = 2
                    elif "int8" in arg_type or "char" in arg_type:
                        arg_size = 1
                    elif 'char' not in arg_type and 'short' not in arg_type and 'int' not in arg_type and 'long' not in arg_type:
                        arg_size = 8  # ignore complex structure/union
                    else:
                        assert False, "var type: {} not implemented".format(arg_type)
                elif '[' in arg_type or '*' in arg_type:  # array or pointer
                    arg_size = config.pointer_size
                else:
                    assert False, "arg type: {} not implemented".format(arg_type)
                f.write(str(arg_size) + '\n')
                arg_print_count += 1
            assert arg_print_count == len(param_list), "Error: not all function arguments handled"
        f.close()


def instrument(c_src_path: str, glob_objs: list, func_objs: list, param_dict: dict, elf_path: str, input_str=""):
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
            if "DW_AT_low_pc" in obj:
                addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
                f.write(hex(addr) + '\n')
        f.close()

    # Preparation 3: print start addresses of functions with return values
    with open(ret_func_addr_file, 'w') as f:
        for obj in func_objs:
            obj = obj[1]
            if "DW_AT_type" in obj and "DW_AT_low_pc" in obj:
                low_addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
                high_addr = int(obj["DW_AT_high_pc"].strip('()'), 16)
                f.write("{}:{}".format(hex(low_addr), hex(high_addr)) + '\n')
        f.close()

    # Preparation 4: print function argument types to file
    print_func_arg_size(func_objs, param_dict, param_file)

    # run pin_tool, get raw trace
    # pintool.get_raw_trace(elf_path, glob_addr_file, func_addr_file, ret_func_addr_file, param_file, trace_path)
    # use m32 instead
    pintool.get_raw_m32trace(elf_path, glob_addr_file, func_addr_file, ret_func_addr_file, param_file, trace_path, input_str)

    return trace_path


def main():
    # test
    c_src_path = "/home/tester/Documents/WebAssembly/examples/test1090_re.c"
    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path)
    (wasm_func_objs, wasm_param_dict, wasm_func_names_list), \
        (clang_func_objs, clang_param_dict, clang_func_names_list) = profile.collect_funcs(c_src_path)

    elf_path, dwarf_path = profile.clang_dwarf(c_src_path)

    raw_trace_path = instrument(c_src_path, clang_globs, clang_func_objs, clang_param_dict, elf_path)


if __name__ == '__main__':
    main()
