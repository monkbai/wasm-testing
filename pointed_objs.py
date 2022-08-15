"""
    Generate mapping between str addresses in wasm and str addresses in elf
"""
import re
import os

import nm
import lcs
import utils
import profile
import trace_consistency

# ==================
# Get .rodata string mappings
# ==================


def get_elf_strs(elf_path: str):
    str_dict = dict()

    status, output = utils.cmd("objdump -h {}".format(elf_path))
    if mat := re.search(r"\.rodata\s+(\w+)\s+(\w+)", output):
        seg_size = int(mat.group(1), 16)
        seg_base = int(mat.group(2), 16)

    status, output = utils.cmd("readelf -W -p .rodata {} > {}".format(elf_path, 'rodata.tmp'))
    with open('rodata.tmp', 'r', encoding='utf-8', errors='ignore') as f:
        try:
            while line := f.readline():
                if mat := re.search(r"\[\s+(\w+)]\s+(.+)\n", line):
                    offset = int(mat.group(1), 16)
                    str_value = mat.group(2)
                    str_value = str_value.replace('\\n', '\n')
                    str_dict['"{}"'.format(str_value)] = seg_base + offset
        except UnicodeDecodeError as err:
            pass
    return str_dict


def get_wasm_strs(wat_path: str):
    str_dict = dict()

    with open(wat_path, 'r') as f:
        lines = f.readlines()
        for l in lines:
            l = l.strip()
            if mat := re.match(r'\(data\s\$\.rodata\s\(i32\.const\s(\d+)\)\s"(.+)"\)', l):
                base_addr = int(mat.group(1))
                whole_str = mat.group(2)
                if '\\00\\00\\00\\00' in whole_str:  # TODO: not very safe
                    whole_str = whole_str[:whole_str.find('\\00\\00\\00\\00')]
                whole_str = whole_str.replace('\\00', '\00')
                whole_str = whole_str.replace('\\0a', '\n')

                idx = 0
                while idx < len(whole_str):
                    start_idx = idx
                    end_idx = start_idx + 1
                    while end_idx < len(whole_str) and whole_str[end_idx] != '\00':
                        end_idx += 1
                    if end_idx != len(whole_str):
                        str_value = whole_str[start_idx:end_idx]
                    else:
                        str_value = whole_str[start_idx:]

                    addr = base_addr + start_idx
                    str_dict['"{}"'.format(str_value)] = addr

                    idx = end_idx + 1
    return str_dict


def get_str_mapping(clang_elf_path: str, wat_path: str):
    clang_str_dict = get_elf_strs(clang_elf_path)
    wasm_str_dict = get_wasm_strs(wat_path)

    str_mapping = []

    for str_val, addr in wasm_str_dict.items():
        if str_val in clang_str_dict:
            str_mapping.append((str_val, addr, clang_str_dict[str_val]))

    return str_mapping


# ==================
# Get global variable mappings
# ==================

def get_glob_mapping(c_src_path: str, clang_opt_level='-O0', emcc_opt_level='-O2', need_compile=True):
    globs_mapping = []

    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path, clang_opt_level, emcc_opt_level, need_compile)

    wasm_globs_dict = dict()
    trace_consistency.clear_glob_array_dict()
    for obj in wasm_globs:
        obj = obj[1]
        obj_list, (min_addr, max_addr, step_size) = trace_consistency.get_name_and_addr(obj)
        for name, addr in obj_list:
            wasm_globs_dict[name] = addr

    clang_globs_dict = dict()
    # first using nm to get reliable symbol names and addresses
    nm_addr = []
    elf_path = c_src_path[:-2] + '.out'
    nm_list = nm.get_nm_list(elf_path, clang_globs)
    for addr, name in nm_list:
        clang_globs_dict[name] = addr
        nm_addr.append(addr)
    # then try to parse dwarf info to get others
    trace_consistency.clear_glob_array_dict()
    for obj in clang_globs:
        obj = obj[1]
        obj_list, (min_addr, max_addr, step_size) = trace_consistency.get_name_and_addr(obj)
        for name, addr in obj_list:
            if name not in clang_globs_dict and addr not in nm_addr:
                clang_globs_dict[name] = addr

    for glob_name, addr in wasm_globs_dict.items():
        if glob_name in clang_globs_dict:
            globs_mapping.append((glob_name, addr, clang_globs_dict[glob_name]))

    trace_consistency.clear_glob_array_dict()
    return globs_mapping, wasm_globs_dict, clang_globs_dict


# ==================
# Get global variable mappings
# ==================


def get_pointed_objs_mapping(c_path: str, elf_path: str, wat_path: str, clang_opt_level='-O0', emcc_opt_level='-O2', need_compile=True):
    """ this function aims to remove overlapped global variables """
    mapping_dict, wasm_objs_dict, clang_objs_dict = _get_pointed_objs_mapping(c_path, elf_path, wat_path, clang_opt_level, emcc_opt_level, need_compile)
    lcs.FuncItem.set_dict(mapping_dict, wasm_objs_dict, clang_objs_dict)
    lcs.PtrItem.set_dict(mapping_dict, wasm_objs_dict, clang_objs_dict)

    mapping_dict, wasm_objs_dict, clang_objs_dict = _get_pointed_objs_mapping(c_path, elf_path, wat_path, clang_opt_level, emcc_opt_level, need_compile)
    return mapping_dict, wasm_objs_dict, clang_objs_dict


def _get_pointed_objs_mapping(c_path: str, elf_path: str, wat_path: str, clang_opt_level='-O0', emcc_opt_level='-O2', need_compile=True):
    globs_mapping, wasm_globs_dict, clang_globs_dict = get_glob_mapping(c_path, clang_opt_level, emcc_opt_level, need_compile)
    str_mapping = get_str_mapping(elf_path, wat_path)

    wasm_objs_dict = dict()
    clang_objs_dict = dict()
    mapping_dict = dict()

    mapping_list = globs_mapping + str_mapping
    for name, wasm_addr, clang_addr in mapping_list:  # this for loop removes overlap (inconsciently)
        wasm_objs_dict[wasm_addr] = (name, clang_addr)
        clang_objs_dict[clang_addr] = (name, wasm_addr)
        mapping_dict[(wasm_addr, clang_addr)] = name
        mapping_dict[(clang_addr, wasm_addr)] = name
    for wasm_name, wasm_addr in wasm_globs_dict.items():
        if wasm_addr not in wasm_objs_dict:
            wasm_objs_dict[wasm_addr] = (wasm_name, 0)
    for clang_name, clang_addr in clang_globs_dict.items():
        if clang_addr not in clang_objs_dict:
            clang_objs_dict[clang_addr] = (clang_name, 0)
    return mapping_dict, wasm_objs_dict, clang_objs_dict


def main():
    c_path = "/home/tester/Documents/WebAssembly/wasm-compiler-testing/debug_cases/test1001.c"
    elf_path = "/home/tester/Documents/WebAssembly/wasm-compiler-testing/debug_cases/test1001.out"
    wat_path = "/home/tester/Documents/WebAssembly/wasm-compiler-testing/debug_cases/test1001.wat"
    print(get_pointed_objs_mapping(c_path, elf_path, wat_path))


if __name__ == '__main__':
    main()
