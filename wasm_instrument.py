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
    if status != 0:
        assert False, "Error: failed to recompile wat file\n"+output

    utils.project_dir = tmp_dir


# ==========================

instrument_id = 0
callee_names_list = []


def get_instrument_id():
    global instrument_id
    instrument_id += 1
    return instrument_id - 1


def get_type_id(type_sec: str):
    idx = type_sec.rfind("  (type (;")
    tmp = type_sec[idx:].strip()
    mat = re.match(r"\(type \(;(\d+);\) ", tmp)
    last_id = int(mat.group(1))
    return last_id


def add_type(type_sec: str):
    last_id = get_type_id(type_sec)

    type_count = wasm_code.wasm_type_def.count('{}')
    offset_list = []
    for i in range(type_count):
        offset_list.append(last_id + i + 1)

    type_sec += wasm_code.wasm_type_def.format(*offset_list)

    return type_sec, offset_list


def get_data_offset(func_sec: str, with_skip=False):
    idx = func_sec.rfind("  (data $")
    tmp = func_sec[idx:].strip()
    mat = re.search(r"\(i32.const (\d+)\) \"(.*?)\"", tmp)
    offset = int(mat.group(1))
    data_str = mat.group(2)
    appro_len = len(data_str) - 2 * data_str.count('\\')
    if with_skip:
        appro_len += 1024 + 256  # To avoid conflicts with uninitialized variables
    return offset, appro_len


def add_data_str(func_sec: str):
    data_offset, appro_len = get_data_offset(func_sec, with_skip=True)
    # some variables are not explicitly defined in .wat, 4096 --> avoid collision
    next_offset = data_offset + appro_len + 4096
    idx = func_sec.rfind(')')

    str_count = wasm_code.wasm_data_str.count('{}')
    offset_list = []
    for i in range(str_count):
        offset_list.append(next_offset + i*12)

    func_sec = func_sec[:idx] + \
               wasm_code.wasm_data_str.format(*offset_list) + \
               func_sec[idx:]

    return func_sec, offset_list


def add_data_str2(func_sec: str, func_objs: list):
    data_offset, appro_len = get_data_offset(func_sec)
    next_offset = data_offset + appro_len * 2
    idx = func_sec.rfind(')')

    func_name_str = ''
    func_name2offset = dict()
    for obj in func_objs:
        obj = obj[1]
        func_name = obj["DW_AT_name"].strip('()').strip('"')
        func_name_str += wasm_code.wasm_func_names_str.format(func_name, next_offset, func_name)
        func_name2offset[func_name] = next_offset
        next_offset += len(func_name) + 3  # $, \0a, and \00

    func_sec = func_sec[:idx] + func_name_str + func_sec[idx:]

    return func_sec, func_name2offset


def add_data_str3(func_sec: str, func_objs: list):
    data_offset, appro_len = get_data_offset(func_sec)
    next_offset = data_offset + appro_len * 2
    idx = func_sec.rfind(')')

    func_name_str = ''
    func_name2offset = dict()
    for obj in func_objs:
        obj = obj[1]
        func_name = obj["DW_AT_name"].strip('()').strip('"')
        func_name_str += wasm_code.wasm_func_return_str.format(func_name, next_offset, func_name)
        func_name2offset[func_name] = next_offset
        next_offset += len(func_name) + 3  # $, \0a, and \00

    func_sec = func_sec[:idx] + func_name_str + func_sec[idx:]

    return func_sec, func_name2offset


def add_utility_funcs(type_sec: str, type_ids: list, data_offsets: list, stdout_addr: int, opt_level='-O2'):
    if opt_level.endswith('O0'):
        type_sec += wasm_code.wasm_vfiprintf.format(type_ids[7])
        type_sec += wasm_code.wasm_iprintf.format(type_ids[6], stdout_addr)
    # print functions
    type_sec += wasm_code.wasm_myprint_i32w.format(type_ids[0], data_offsets[0], data_offsets[1])
    type_sec += wasm_code.wasm_myprint_i32v.format(type_ids[1], data_offsets[2])
    type_sec += wasm_code.wasm_myprint_i32p.format(type_ids[1], data_offsets[3])
    type_sec += wasm_code.wasm_myprint_i64p.format(type_ids[2], data_offsets[4])
    type_sec += wasm_code.wasm_myprint_i64v.format(type_ids[2], data_offsets[5])
    type_sec += wasm_code.wasm_myprint_i32r.format(type_ids[3], data_offsets[6])
    type_sec += wasm_code.wasm_myprint_i64r.format(type_ids[9], data_offsets[8])
    type_sec += wasm_code.wasm_myprint_i32id.format(type_ids[1], data_offsets[7])
    type_sec += wasm_code.wasm_myprint_call.format(type_ids[1])

    # store functions
    type_sec += wasm_code.wasm_instrument_i32store.format(type_ids[0])
    type_sec += wasm_code.wasm_instrument_i32store16.format(type_ids[0])
    type_sec += wasm_code.wasm_instrument_i32store8.format(type_ids[0])
    type_sec += wasm_code.wasm_instrument_i64store.format(type_ids[4])
    type_sec += wasm_code.wasm_instrument_i64store32.format(type_ids[4])
    type_sec += wasm_code.wasm_instrument_i64store16.format(type_ids[4])
    type_sec += wasm_code.wasm_instrument_i64store8.format(type_ids[4])
    type_sec += wasm_code.wasm_instrument_i32store_off.format(type_ids[5])
    type_sec += wasm_code.wasm_instrument_i32store16_off.format(type_ids[5])
    type_sec += wasm_code.wasm_instrument_i32store8_off.format(type_ids[5])
    type_sec += wasm_code.wasm_instrument_i64store_off.format(type_ids[8])
    type_sec += wasm_code.wasm_instrument_i64store32_off.format(type_ids[8])
    type_sec += wasm_code.wasm_instrument_i64store16_off.format(type_ids[8])
    type_sec += wasm_code.wasm_instrument_i64store8_off.format(type_ids[8])
    # TODO: f32.store, f64.store are not implemented yet

    return type_sec


def get_return(func_txt: str):
    r_num = 0
    mat = re.search(r"\(result( [if]\d+)+\)", func_txt)
    if mat:
        r_num = mat.group(1).count(' ')
        return r_num, mat.group(1).strip()
    return r_num, ''


def _instrument_return(func_txt: str, func_name: str, func_name2offset: dict):
    r_num, r_type = get_return(func_txt)

    lines = func_txt.strip().split('\n')
    l = lines[-1].strip()
    prefix_space = ' ' * lines[-1].find(l)

    assert r_num <= 1  # currently, webassembly only support one return value or no return value

    idx = func_txt.rfind(')')
    if r_type == "i32":
        l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
        l += prefix_space + "i32.const {}\n".format(func_name2offset[func_name]) + prefix_space + "call $myprint_call\n"
        l += prefix_space + "call $myprint_i32r"
        func_txt = func_txt[:idx] + '\n' + l + func_txt[idx:]
    elif r_type == "i64":
        l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
        l += prefix_space + "i32.const {}\n".format(func_name2offset[func_name]) + prefix_space + "call $myprint_call\n"
        l += prefix_space + "call $myprint_i64r"
        func_txt = func_txt[:idx] + '\n' + l + func_txt[idx:]
    elif r_num > 0:
        assert False, "return value type not implemented"

    return func_txt


def _instrument_func_line(func_txt: str):
    new_func_txt = ''
    lines = func_txt.split('\n')
    idx = 0
    while idx < len(lines):
        l = lines[idx].strip()
        end_bracket = False
        if l.endswith(')'):
            end_bracket = True
            l = l.strip(')')
        prefix_space = ' ' * lines[idx].find(l)

        if l == 'i32.store':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i32store  ;; i32.store"
        elif l == 'i32.store16':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i32store16  ;; i32.store16"
        elif l == 'i32.store8':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i32store8  ;; i32.store8"

        elif l == 'i64.store':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i64store  ;; i64.store"
        elif mat := re.match(r'i64\.store align=(\d+)', l):  # the same instrumentation as i64.store
            # the alignment will be handled in generalize_wasm_trace()
            align_num = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i64store  ;; i64.store"
        elif l == 'i64.store32':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i64store32  ;; i64.store32"
        elif l == 'i64.store16':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i64store16  ;; i64.store16"
        elif l == 'i64.store8':
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "call $instrument_i64store8  ;; i64.store8"

        elif mat := re.match(r'i32\.store offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i32store_off  ;; " + lines[idx].strip()
        elif mat := re.match(r'i32\.store16 offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i32store16_off  ;; " + lines[idx].strip()
        elif mat := re.match(r'i32\.store8 offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i32store8_off  ;; " + lines[idx].strip()

        elif mat := re.match(r'i64\.store offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i64store_off  ;; " + lines[idx].strip()
        elif mat := re.match(r'i64\.store32 offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i64store32_off  ;; " + lines[idx].strip()
        elif mat := re.match(r'i64\.store16 offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i64store16_off  ;; " + lines[idx].strip()
        elif mat := re.match(r'i64\.store8 offset=(\d+)', l):
            addr_offset = int(mat.group(1))
            l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
            l += prefix_space + "i32.const {}\n".format(addr_offset) + prefix_space + "call $instrument_i64store8_off  ;; " + lines[idx].strip()

        elif mat := re.match(r'call\s\$(\w+)', l):
            callee_name = mat.group(1)
            if callee_name in callee_names_list:
                l = prefix_space + "i32.const {}\n".format(get_instrument_id()) + prefix_space + "call $myprint_i32id\n"
                l += lines[idx]
            else:
                l = prefix_space + l
        else:
            l = prefix_space + l

        if end_bracket:
            if l.rfind(';;') != -1:
                l += '\n' + prefix_space
            l += ')'
        new_func_txt += l + '\n'

        idx += 1
    return new_func_txt


def _instrument_func_call(func_txt: str, func_name: str, func_name2offset: dict, func_obj: dict, param_dict: dict):
    new_func_txt = ''
    lines = func_txt.split('\n')
    idx = 0

    start_flag = 0
    while idx < len(lines):
        l = lines[idx].strip()
        prefix_space = ' ' * lines[idx].find(l)

        if not l.startswith('(') and not start_flag:
            # print function name
            l = prefix_space + "i32.const {}\n".format(
                func_name2offset[func_name]) + prefix_space + "call $myprint_call\n"

            # use the wasm function definition, instead of dwarf info
            if mat := re.search(r"\(param ([if0-9\s]+)\)", lines[0]):
                params = mat.group(1).split(' ')
                for param_idx in range(len(params)):
                    l += prefix_space + 'local.get {}\n'.format(param_idx)
                    p = params[param_idx]
                    if p == 'i64':
                        l += prefix_space + 'call $myprint_i64p\n'
                    elif p == 'i32':
                        l += prefix_space + 'call $myprint_i32p\n'
                    else:
                        assert False, "param type '{}' not implemented".format(p)

            '''
            # print function parameters
            if func_obj["DW_AT_name"] in param_dict.keys():
                params = param_dict[func_obj["DW_AT_name"]]
                param_idx = 0
                while param_idx < len(params):
                    param = params[param_idx]
                    l += prefix_space + 'local.get {}\n'.format(param_idx)
                    param_type = param["DW_AT_type"]
                    if 'int64' in param_type:
                        l += prefix_space + 'call $myprint_i64p\n'
                    elif 'char*' in param_type or '"int"' in param_type:  # pointer in wasm is i32
                        l += prefix_space + 'call $myprint_i32p\n'
                    elif 'int32' in param_type or 'int16' in param_type or 'int8' in param_type:  # smallest unit is i32
                        l += prefix_space + 'call $myprint_i32p\n'
                    else:
                        assert False, "param type not implemented"
                    param_idx += 1
            '''

            # original first line
            l += lines[idx]
            new_func_txt += l + '\n'
            idx += 1
            start_flag = 1
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


def instrument_glob_write(wat_txt, stdout_addr, func_objs: list, opt_level='-O2'):
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

    type_sec = add_utility_funcs(type_sec, type_ids, data_offsets, stdout_addr, opt_level)

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


def instrument_func_call(wat_txt, func_objs: list, param_dict: dict):
    # func names list:
    func_names = []
    for obj in func_objs:
        obj = obj[1]
        func_names.append(obj["DW_AT_name"].strip('()').strip('"'))

    idx = wat_txt.find('  (func ')
    type_sec = wat_txt[:idx]

    func_sec = wat_txt[idx:]
    func_sec, func_name2offset = add_data_str2(func_sec, func_objs)
    func_sec, func_return2offset = add_data_str3(func_sec, func_objs)

    # traverse all user-defined functions, and instrument all *.store instructions
    new_func = copy.deepcopy(func_sec)
    it = re.finditer(r"\(func \$(\w+) ", func_sec)
    for match in it:
        start_idx = match.start()
        func_define = extract_func_define(func_sec, start_idx)
        assert func_define.count("(func $") == 1, "error: incorrect regexp"
        func_name = match.group(1)
        if func_name in func_names:
            for obj in func_objs:
                obj = obj[1]
                if obj["DW_AT_name"].strip('()').strip('"') == func_name:
                    break
            assert obj["DW_AT_name"].strip('()').strip('"') == func_name
            # instrument
            new_func_define = _instrument_func_call(func_define, func_name, func_name2offset, obj, param_dict)
            new_func_define = _instrument_return(new_func_define, func_name, func_return2offset)
            new_func = new_func.replace(func_define, new_func_define)
        else:
            continue

    return type_sec + new_func


def instrument(wasm_path: str, glob_objs: list, func_objs: list, param_dict: dict, new_wasm_path: str, opt_level='-O2'):
    global callee_names_list, instrument_id
    instrument_id = 0
    callee_names_list = []

    for obj in glob_objs:
        obj = obj[1]
        if obj["DW_AT_name"].strip('()').strip('"') == '__stdout_FILE':
            stdout_addr = obj["DW_AT_location"]
            stdout_addr = int(re.match(r"\(DW_OP_addr\s0x([\w]+)\)", stdout_addr).group(1), 16)

    for obj in func_objs:
        obj = obj[1]
        callee_names_list.append(obj["DW_AT_name"].strip('()').strip('"'))

    wat_txt = wasm2wat(wasm_path)

    new_wat_txt = instrument_glob_write(wat_txt, stdout_addr, func_objs, opt_level)

    new_wat_txt = instrument_func_call(new_wat_txt, func_objs, param_dict)

    # if opt_level.strip().endswith('O0'):
    #     new_wat_txt = new_wat_txt.replace('$iprintf', '$printf')  # iprintf and printf are different

    wat2wasm(new_wasm_path, new_wat_txt)


def run_wasm(js_path: str):
    js_path = os.path.abspath(js_path)
    output_path = js_path + '.trace'
    dir_path = os.path.dirname(js_path)

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.nodejs_cmd.format(js_path, output_path))

    utils.project_dir = tmp_dir

    return output_path


def main():
    # test
    c_src_path = "/home/tester/Documents/WebAssembly/examples/test1090_re.c"
    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path)
    (wasm_func_objs, wasm_param_dict, wasm_func_names_list), \
        (clang_func_objs, clang_param_dict, clang_func_names_list) = profile.collect_funcs(c_src_path)
    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_src_path)

    instrument(wasm_path, wasm_globs, wasm_func_objs, wasm_param_dict, wasm_path)


if __name__ == '__main__':
    # instrument_glob_write("/home/tester/Documents/WebAssembly/examples/test1090_re.wasm")
    main()
