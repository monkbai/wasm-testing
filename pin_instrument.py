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
            addr = int(re.search(r"DW_OP_addr (\w+)", obj["DW_AT_location"]).group(1), 16)
            var_type = obj["DW_AT_type"]
            var_type = var_type.replace('volatile ', '')
            if mat := re.search(r'\(0x[\da-fA-F]+\s"(\w+)((\[\d+])+)"\)', var_type):
                var_type = mat.group(1)
                array_dim = mat.group(2)
                array_dim = array_dim.replace('[', '')
                array_dim = array_dim.split(']')
                var_num = 1
                for dim in array_dim:
                    dim = dim.strip()
                    if len(dim) > 0:
                        var_num *= int(dim)
                if "int64" in var_type:
                    step_size = 8
                elif "int32" in var_type:
                    step_size = 4
                elif "int16" in var_type:
                    step_size = 2
                elif "int8" in var_type:
                    step_size = 1
                elif 'char' not in var_type and 'short' not in var_type and 'int' not in var_type and 'long' not in var_type:
                    continue  # ignore complex structure/union
                else:
                    assert False, "var type: {} not implemented".format(var_type)

                for i in range(var_num):
                    f.write(hex(addr + i * step_size) + '\n')
            elif '[' not in var_type:  # record pointer values, but ignore them during trace consistency checking
                f.write(hex(addr) + '\n')
            elif 'const' in var_type:
                continue
            elif '*' in var_type and '[' in var_type:
                continue  # pointer array -> too complex, ignore
            else:
                assert False, "var type: {} not implemented".format(var_type)
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
            for param in param_list:
                arg_type = param["DW_AT_type"]
                arg_type = arg_type.replace('const ', '')
                if mat := re.search(r'\(0x[\da-fA-F]+\s"(\w+)"\)', arg_type):
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
                        continue  # ignore complex structure/union
                    else:
                        assert False, "var type: {} not implemented".format(arg_type)
                elif '[' in arg_type or '*' in arg_type:  # array or pointer
                    arg_size = 8
                else:
                    assert False, "arg type: {} not implemented".format(arg_type)
                f.write(str(arg_size) + '\n')
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
            if "DW_AT_low_pc" in obj:
                addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
                f.write(hex(addr) + '\n')
        f.close()

    # Preparation 3: print start addresses of functions with return values
    with open(ret_func_addr_file, 'w') as f:
        for obj in func_objs:
            obj = obj[1]
            if "DW_AT_type" in obj and "DW_AT_low_pc" in obj:
                addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
                f.write(hex(addr) + '\n')
        f.close()

    # Preparation 4: print function argument types to file
    print_func_arg_size(func_objs, param_dict, param_file)

    # run pin_tool, get raw trace
    pintool.get_raw_trace(elf_path, glob_addr_file, func_addr_file, ret_func_addr_file, param_file, trace_path)

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
