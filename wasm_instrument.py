import os
import re
import copy

import utils
import config
import profile
import wasm_code


def wasm2wat(wasm_path: str):
    wasm_path = os.path.abspath(wasm_path)
    dir_path = os.path.dirname(wasm_path)
    assert wasm_path.endswith('.wasm')
    wat_path = wasm_path[:-5] + '.wat'

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.wasm2wat_cmd.format(wasm_path, wat_path))

    utils.project_dir = tmp_dir

    with open(wat_path, 'r') as f:
        return f.read()


def wat2wasm(wasm_path: str, wat_txt: str):
    wasm_path = os.path.abspath(wasm_path)
    dir_path = os.path.dirname(wasm_path)
    assert wasm_path.endswith('.wasm')
    wat_path = wasm_path[:-5] + '.wat'

    with open(wat_path, 'w') as f:
        f.write(wat_txt)

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.wat2wasm_cmd.format(wat_path, wasm_path))

    utils.project_dir = tmp_dir


# ==========================


def get_type_id(type_sec: str):
    idx = type_sec.rfind("  (type (;")
    tmp = type_sec[idx:].strip()
    mat = re.match(r"\(type \(;(\d+);\) ", tmp)
    last_id = int(mat.group(1))
    return last_id


def add_type(type_sec: str):
    last_id = get_type_id(type_sec)
    type_sec += wasm_code.wasm_type_def.format(last_id+1, last_id+2)

    return type_sec, [last_id+1, last_id+2]


def get_data_offset(func_sec: str):
    idx = func_sec.rfind("  (data $")
    tmp = func_sec[idx:].strip()
    mat = re.search(r"\(i32.const (\d+)\) \"(.*?)\"", tmp)
    offset = int(mat.group(1))
    data_str = mat.group(2)
    appro_len = len(data_str) - 2 * data_str.count('\\')
    return offset, appro_len


def add_data_str(func_sec: str):
    data_offset, appro_len = get_data_offset(func_sec)
    next_offset = data_offset + appro_len * 2
    idx = func_sec.rfind(')')
    func_sec = func_sec[:idx] + wasm_code.wasm_data_str.format(next_offset, next_offset+10) + func_sec[idx:]

    return func_sec, [next_offset, next_offset+10]


def add_utility_funcs(type_sec: str, type_ids: list, data_offsets: list):
    # print functions
    type_sec += wasm_code.wasm_myprint_i32w.format(type_ids[1], data_offsets[0])
    type_sec += wasm_code.wasm_myprint_i32v.format(type_ids[1], data_offsets[1])

    # store functions
    type_sec += wasm_code.wasm_instrument_i32store.format(type_ids[0])

    return type_sec


def _instrument_func_line(func_txt: str):
    new_func_txt = ''
    lines = func_txt.split('\n')
    idx = 0
    while idx < len(lines):
        l = lines[idx].strip()
        prefix_space = ' ' * lines[idx].find(l)

        if l == 'i32.store':
            l = prefix_space + "call $instrument_i32store  ;; i32.store"
            new_func_txt += l + '\n'
            idx += 1
            continue
        new_func_txt += lines[idx] + '\n'
        idx += 1
    return new_func_txt


def extract_func_define(func_sec: str, idx: int):
    # cannot be implemented with regular expression
    func_sec = func_sec[idx:]
    assert func_sec.startswith("(func $")
    bracket_depth = 0
    end_idx = 0
    while end_idx < len(func_sec):
        if func_sec[end_idx] == '(':
            bracket_depth += 1
        elif func_sec[end_idx] == ')':
            bracket_depth -= 1

        if bracket_depth == 0:
            end_idx += 1
            break
        end_idx += 1
    return func_sec[:end_idx]


def instrument_glob_write(wat_txt, func_objs: list):
    # func names list:
    func_names = []
    for obj in func_objs:
        obj = obj[1]
        func_names.append(obj["DW_AT_name"].strip('()').strip('"'))

    idx = wat_txt.find('  (func ')
    type_sec = wat_txt[:idx]
    type_sec, type_ids = add_type(type_sec)

    func_sec = wat_txt[idx:]
    func_sec, data_offsets = add_data_str(func_sec)

    type_sec = add_utility_funcs(type_sec, type_ids, data_offsets)

    # traverse all user-defined functions, and instrument all *.store instructions
    new_func = copy.deepcopy(func_sec)
    it = re.finditer(r"\(func \$(\w+) ", func_sec)
    for match in it:
        start_idx = match.start()
        func_define = extract_func_define(func_sec, start_idx)
        assert func_define.count("(func $") == 1, "error: incorrect regexp"
        func_name = match.group(1)
        if func_name in func_names:
            # instrument
            new_func_define = _instrument_func_line(func_define)
            new_func = new_func.replace(func_define, new_func_define)
        else:
            continue

    return type_sec + new_func


def instrument(wasm_path: str, glob_objs: list, func_objs: list, new_wasm_path: str):
    wat_txt = wasm2wat(wasm_path)

    new_wat_txt = instrument_glob_write(wat_txt, func_objs)

    wat2wasm(new_wasm_path, new_wat_txt)


def main():
    # test
    c_src_path = "/home/lifter/Documents/WebAssembly/examples/test1090_re.c"
    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path)
    (wasm_func_objs, wasm_param_dict, wasm_func_names_list), \
        (clang_func_objs, clang_param_dict, clang_func_names_list) = profile.collect_funcs(c_src_path)
    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_src_path)

    instrument(wasm_path, wasm_globs, wasm_func_objs, wasm_path)


if __name__ == '__main__':
    # instrument_glob_write("/home/lifter/Documents/WebAssembly/examples/test1090_re.wasm")
    main()
