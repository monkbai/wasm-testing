import os
import re
import sys

import utils
import config


def compile_llvm_ir(c_src_path: str):
    """ Deprecated """
    c_src_path = os.path.abspath(c_src_path)
    dir_path = os.path.dirname(c_src_path)
    ll_path = os.path.join(dir_path, 'tmp.ll')

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.clang_ir_cmd2.format(c_src_path, ll_path))

    utils.project_dir = tmp_dir
    return ll_path


def get_global_vars(c_src_path: str):
    """ Deprecated """
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
def emscripten_dwarf(c_src_path: str, opt_level='-O2'):
    if c_src_path.endswith('.c') and c_src_path.count(".c") == 1:
        c_src_path = os.path.abspath(c_src_path)
        dir_path = os.path.dirname(c_src_path)
        wasm_path = c_src_path[:-2] + '.wasm'
        js_path = c_src_path[:-2] + '.js'
        dwarf_txt_path = wasm_path + '.dwarf'
    else:
        files = c_src_path.split(' ')
        dir_path = os.path.dirname(files[0])
        wasm_path = os.path.join(dir_path, "tmp.wasm")
        js_path = os.path.join(dir_path, "tmp.js")
        dwarf_txt_path = os.path.join(dir_path, "tmp.wasm.dwarf")

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    stdout, stderr = utils.cmd_emsdk(config.emcc_dwarf_opt_cmd.format(opt_level, c_src_path, wasm_path, js_path))
    status, output = utils.cmd(config.dwarfdump_cmd.format(wasm_path, dwarf_txt_path))
    stderr = stderr.decode('utf-8')
    if status and "wasm-ld: error: initial memory too small" not in stderr:
        print("Warning: failed to generate WASM code. {}".format(wasm_path))
        print(stderr)

    utils.project_dir = tmp_dir

    return wasm_path, js_path, dwarf_txt_path


def clang_dwarf(c_src_path: str, opt_level='-O0'):
    if c_src_path.endswith('.c') and c_src_path.count(".c") == 1:
        c_src_path = os.path.abspath(c_src_path)
        dir_path = os.path.dirname(c_src_path)
        out_path = c_src_path[:-2] + '.out'
        dwarf_txt_path = out_path + '.dwarf'
    else:
        files = c_src_path.split(' ')
        dir_path = os.path.dirname(files[0])
        out_path = os.path.join(dir_path, "tmp.out")
        dwarf_txt_path = os.path.join(dir_path, "tmp.out.dwarf")

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.clang_dwarf_opt_cmd.format(opt_level, c_src_path, out_path))
    if status:
        print("Warning: failed to generate x86 code.")
    status, output = utils.cmd(config.dwarfdump_cmd.format(out_path, dwarf_txt_path))

    utils.project_dir = tmp_dir

    return out_path, dwarf_txt_path


def clang_dwarf_withoutput(c_src_path: str, opt_level='-O0'):
    """ used in utils for compilation checking """
    c_src_path = os.path.abspath(c_src_path)
    dir_path = os.path.dirname(c_src_path)
    assert c_src_path.endswith('.c')
    out_path = c_src_path[:-2] + '.out'
    dwarf_txt_path = out_path + '.dwarf'

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output1 = utils.cmd(config.clang_dwarf_opt_cmd.format(opt_level, c_src_path, out_path))
    status, output2 = utils.cmd(config.dwarfdump_cmd.format(out_path, dwarf_txt_path))

    utils.project_dir = tmp_dir

    return out_path, dwarf_txt_path, output1


def obj_str_split(obj_str: str):
    prefix_idx = len(re.match(r"\s+",obj_str).group())
    tmp_lines = obj_str.split('\n')
    obj_attr_list = []
    idx = 0
    while idx < len(tmp_lines):
        l = tmp_lines[idx]
        while (idx+1) < len(tmp_lines) and len(re.match(r"\s+", tmp_lines[idx+1]).group()) > prefix_idx:
            l += '\n' + tmp_lines[idx+1]
            idx += 1
        obj_attr_list.append(l+'\n')
        idx += 1
    return obj_attr_list


def parse_dwarf_obj(obj_str: str):
    mat = re.match(r"(0x\w+):", obj_str)
    obj_addr = mat.group(1)
    obj_str = obj_str[11:].strip()
    lines = obj_str.split('\n')
    obj_type = lines[0].strip()

    obj_dict = dict()
    obj_dict["addr"] = obj_addr
    obj_dict["type"] = obj_type

    obj_str = obj_str[obj_str.find('\n')+1:]
    obj_attr_list = obj_str_split(obj_str)

    for attr_str in obj_attr_list:
        mat = re.search(r'(DW_\w+)\t(\([^\r]*?\))\n', attr_str)
        attr = mat.group(1)
        value = mat.group(2)
        obj_dict[attr] = value

    # obj_str = obj_str[obj_str.find('\n'):].strip()  # skip the first line
    # while mat := re.match(r"(DW_\w+)\t(\([^\[\n\r]*(\s+\[[^)\n\r]+\)[^)\n\r]*)*.*\))", obj_str):
    #     attr = mat.group(1)
    #     value = mat.group(2)
    #     obj_dict[attr] = value
    #
    #     obj_str = obj_str.replace(mat.group(), '')
    #     obj_str = obj_str.strip()
    return obj_addr, obj_type, obj_dict


def traverse_dwarf(dwarf_path: str, filter='DW_OP_addr'):
    glob_objs = []
    var_names_list = []
    with open(dwarf_path, 'r') as f:
        dwarf_txt = f.read()
        dwarf_objs = dwarf_txt.split('\n\n')
        for obj in dwarf_objs:
            if not obj.startswith('0x') or "DW_TAG_variable" not in obj or "DW_AT_name" not in obj:
                continue

            obj_addr, obj_type, obj_dict = parse_dwarf_obj(obj)
            if obj_type == "DW_TAG_variable" and \
                    "DW_AT_name" in obj_dict.keys() and \
                    "DW_AT_location" in obj_dict.keys() and filter in obj_dict["DW_AT_location"]:
                glob_objs.append((obj_addr, obj_dict))
                var_names_list.append(obj_dict["DW_AT_name"])
    return glob_objs, var_names_list


def replace_abstract_origin(dwarf_obj: str):
    """
    DW_AT_abstract_origin:
      Inline instances of inline subprograms
      Out-of-line instances of inline subprograms
      https://dwarfstd.org/doc/DWARF4.pdf
    :param dwarf_obj:
    :return:
    """
    # seems we should handle this case as well
    if mat := re.search(r'DW_AT_abstract_origin\s\((\w+) "(\w+)"\)', dwarf_obj):
        # transform it to DW_AT_name, so the traverse function can handle this as well
        obj_name = mat.group(2)
        name_str = 'DW_AT_name	("{}")'.format(obj_name)
        dwarf_obj = dwarf_obj.replace(mat.group(), name_str)

    if "DW_TAG_inlined_subroutine" in dwarf_obj:
        dwarf_obj = dwarf_obj.replace("DW_TAG_inlined_subroutine", "DW_TAG_subprogram")

    return dwarf_obj


def get_func_obj_start_addr(obj_str: str):
    if mat := re.search(r"DW_AT_low_pc	\(([0-9A-Fa-fxX]+)\)", obj_str):
        low_pc = int(mat.group(1), 16)
        return low_pc


def get_func_obj_range(obj_str: str):
    if mat := re.search(r"DW_AT_low_pc	\(([0-9A-Fa-fxX]+)\)", obj_str):
        low_pc = int(mat.group(1), 16)
        if mat := re.search(r"DW_AT_high_pc	\(([0-9A-Fa-fxX]+)\)", obj_str):
            high_pc = int(mat.group(1), 16)
            return low_pc, high_pc
    return -1, -1


def traverse_dwarf_subprogs(dwarf_path: str):
    func_objs = []
    param_dict = dict()
    func_names_list = []

    func_start_addr_set = set()  # filter func_objs, remove functions with the same start address (only keep one)
    func_range_set = set()  # filter func_objs, remove functions inside other functions  (inlined)

    def in_func_ranges(l_pc: int, h_pc: int):
        if l_pc == 0 and h_pc == 0:  # due to optimization passes of wasm-opt
            return False
        for low, high in func_range_set:
            if low <= l_pc < h_pc <= high:
                return True
        return False

    current_func = dict()
    current_func_valid = False
    with open(dwarf_path, 'r') as f:
        dwarf_txt = f.read()
        dwarf_objs = dwarf_txt.split('\n\n')
        for obj in dwarf_objs:
            obj = replace_abstract_origin(obj)  # only part of the function calls are inlined

            if not obj.startswith('0x') or "DW_AT_name" not in obj:
                continue
            if "DW_TAG_subprogram" not in obj and "DW_TAG_formal_parameter" not in obj:
                continue

            obj_addr, obj_type, obj_dict = parse_dwarf_obj(obj)
            if obj_type == "DW_TAG_subprogram":
                start_addr = get_func_obj_start_addr(obj)
                low_pc, high_pc = get_func_obj_range(obj)
                current_func_valid = False
                if start_addr is not None and (start_addr not in func_start_addr_set or start_addr == 0) and not in_func_ranges(low_pc, high_pc):
                    func_objs.append((obj_addr, obj_dict))
                    func_names_list.append(obj_dict["DW_AT_name"])
                    current_func_valid = True

                    func_start_addr_set.add(start_addr)
                    func_range_set.add((low_pc, high_pc))
                current_func = obj_dict
            elif obj_type == "DW_TAG_formal_parameter":

                if "DW_AT_type" not in obj or not current_func_valid:  # or "DW_AT_low_pc" not in current_func:
                    continue  # skip parameter in inlined function

                if current_func["DW_AT_name"] in param_dict.keys():
                    param_dict[current_func["DW_AT_name"]].append(obj_dict)
                else:
                    param_dict[current_func["DW_AT_name"]] = [obj_dict]
    return func_objs, param_dict, func_names_list


def get_wasm_globs(c_src_path: str, emcc_opt_level='-O2', need_compile=True):
    if need_compile:
        wasm_path, js_path, wasm_dwarf_txt_path = emscripten_dwarf(c_src_path, opt_level=emcc_opt_level)
    else:
        assert c_src_path.endswith('.c')
        wasm_path = c_src_path[:-2] + '.wasm'
        js_path = c_src_path[:-2] + '.js'
        wasm_dwarf_txt_path = wasm_path + '.dwarf'

    wasm_glob_objs, wasm_name_list = traverse_dwarf(wasm_dwarf_txt_path)
    return wasm_glob_objs


def collect_glob_vars(c_src_path: str, clang_opt_level='-O0', emcc_opt_level='-O2', need_compile=True):
    if need_compile:
        out_path, clang_dwarf_txt_path = clang_dwarf(c_src_path, opt_level=clang_opt_level)
        wasm_path, js_path, wasm_dwarf_txt_path = emscripten_dwarf(c_src_path, opt_level=emcc_opt_level)
    else:
        assert c_src_path.endswith('.c')
        out_path = c_src_path[:-2] + '.out'
        clang_dwarf_txt_path = out_path + '.dwarf'

        wasm_path = c_src_path[:-2] + '.wasm'
        js_path = c_src_path[:-2] + '.js'
        wasm_dwarf_txt_path = wasm_path + '.dwarf'

    wasm_glob_objs, wasm_name_list = traverse_dwarf(wasm_dwarf_txt_path)
    clang_glob_objs, clang_name_list = traverse_dwarf(clang_dwarf_txt_path)

    new_wasm_globs = []
    new_clang_globs = []
    for obj in clang_glob_objs:
        if "g_" in obj[1]["DW_AT_name"] or obj[1]["DW_AT_name"] in wasm_name_list:
            if obj not in new_clang_globs:
                new_clang_globs.append(obj)
            for wasm_obj in wasm_glob_objs:
                mat = re.search(r'"g_\d+"', wasm_obj[1]["DW_AT_name"])
                if mat or wasm_obj[1]["DW_AT_name"] == obj[1]["DW_AT_name"]:
                    # additional check
                    # if wasm glob has 'DW_OP_deref_size 0x1' in 'DW_AT_location' attribute, we can ignore this glob
                    # this remove FPss caused by `select` wasm instruction or constant propagation
                    if 'DW_OP_deref_size 0x1' not in wasm_obj[1]["DW_AT_location"] and wasm_obj not in new_wasm_globs:
                        new_wasm_globs.append(wasm_obj)

                    # break
            continue

    # debug
    # print(new_wasm_globs)
    # print(new_clang_globs)

    # status, output = utils.cmd("rm {}".format(out_path))
    # status, output = utils.cmd("rm {}".format(wasm_path))
    # status, output = utils.cmd("rm {}".format(js_path))

    # Fix: keep all clang globs, only filter wasm globs
    return new_wasm_globs, clang_glob_objs


def collect_funcs(c_src_path: str, clang_opt_level='-O0', emcc_opt_level='-O2', need_compile=True):
    if need_compile:
        out_path, clang_dwarf_txt_path = clang_dwarf(c_src_path, opt_level=clang_opt_level)
        wasm_path, js_path, wasm_dwarf_txt_path = emscripten_dwarf(c_src_path, opt_level=emcc_opt_level)
    else:
        assert c_src_path.endswith('.c')
        out_path = c_src_path[:-2] + '.out'
        clang_dwarf_txt_path = out_path + '.dwarf'

        wasm_path = c_src_path[:-2] + '.wasm'
        js_path = c_src_path[:-2] + '.js'
        wasm_dwarf_txt_path = wasm_path + '.dwarf'

    wasm_func_objs, wasm_param_dict, wasm_func_names_list = traverse_dwarf_subprogs(wasm_dwarf_txt_path)
    clang_func_objs, clang_param_dict, clang_func_names_list = traverse_dwarf_subprogs(clang_dwarf_txt_path)

    new_wasm_funcs = []
    new_clang_funcs = []
    for obj in clang_func_objs:
        if "func_" in obj[1]["DW_AT_name"] or obj[1]["DW_AT_name"] in wasm_func_names_list:
            if obj not in new_clang_funcs:
                new_clang_funcs.append(obj)
            for wasm_obj in wasm_func_objs:
                if "func_" in wasm_obj[1]["DW_AT_name"] or wasm_obj[1]["DW_AT_name"] == obj[1]["DW_AT_name"]:
                    if wasm_obj not in new_wasm_funcs:
                        new_wasm_funcs.append(wasm_obj)
                    # debug
                    # print(obj)
                    # if obj[1]["DW_AT_name"] in clang_param_dict.keys():
                    #     print(clang_param_dict[obj[1]["DW_AT_name"]])
                    # else:
                    #     print("No parameter")
                    # print(wasm_obj)
                    # if wasm_obj[1]["DW_AT_name"] in wasm_param_dict.keys():
                    #     print(wasm_param_dict[wasm_obj[1]["DW_AT_name"]])
                    #     assert len(wasm_param_dict[wasm_obj[1]["DW_AT_name"]]) == len(clang_param_dict[obj[1]["DW_AT_name"]])
                    # else:
                    #     print("No parameter")

                    # break
            continue

    # status, output = utils.cmd("rm {}".format(out_path))
    # status, output = utils.cmd("rm {}".format(wasm_path))
    # status, output = utils.cmd("rm {}".format(js_path))

    # Fix: keep all clang func objs
    return (new_wasm_funcs, wasm_param_dict, wasm_func_names_list), (clang_func_objs, clang_param_dict, clang_func_names_list)


if __name__ == '__main__':
    # get_global_vars("/home/tester/Documents/WebAssembly/examples/test1090_re.c")

    collect_glob_vars("/home/tester/Documents/WebAssembly/examples/test1090_re.c")
    collect_funcs("/home/tester/Documents/WebAssembly/examples/test1090_re.c")

