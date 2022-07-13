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

    status, output = utils.cmd(config.clang_ir_cmd2.format(c_src_path, ll_path))

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

    stdout, stderr = utils.cmd_emsdk(config.emcc_dwarf_cmd.format(c_src_path, wasm_path, js_path))
    status, output = utils.cmd(config.dwarfdump_cmd.format(wasm_path, dwarf_txt_path))

    utils.project_dir = tmp_dir

    return wasm_path, js_path, dwarf_txt_path


def clang_dwarf(c_src_path: str):
    c_src_path = os.path.abspath(c_src_path)
    dir_path = os.path.dirname(c_src_path)
    assert c_src_path.endswith('.c')
    out_path = c_src_path[:-2] + '.out'
    dwarf_txt_path = out_path + '.dwarf'

    tmp_dir = utils.project_dir
    utils.project_dir = dir_path

    status, output = utils.cmd(config.clang_dwarf_cmd2.format(c_src_path, out_path))
    status, output = utils.cmd(config.dwarfdump_cmd.format(out_path, dwarf_txt_path))

    utils.project_dir = tmp_dir

    return out_path, dwarf_txt_path


def parse_dwarf_obj(obj_str: str):
    mat = re.match(r"(0x\w+):", obj_str)
    obj_addr = mat.group(1)
    obj_str = obj_str[11:].strip()
    lines = obj_str.split('\n')
    obj_type = lines[0].strip()

    obj_dict = dict()
    obj_dict["addr"] = obj_addr
    obj_dict["type"] = obj_type

    obj_str = obj_str[obj_str.find('\n'):].strip()  # skip the first line
    while mat := re.match(r"(DW_\w+)\t(\([^\[\n\r]*(\s+\[[^)\n\r]+\)[^)\n\r]*)*.*\))", obj_str):
        attr = mat.group(1)
        value = mat.group(2)
        obj_dict[attr] = value

        obj_str = obj_str.replace(mat.group(), '')
        obj_str = obj_str.strip()
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


def traverse_dwarf_subprogs(dwarf_path: str):
    func_objs = []
    param_dict = dict()
    func_names_list = []

    current_func = dict()
    with open(dwarf_path, 'r') as f:
        dwarf_txt = f.read()
        dwarf_objs = dwarf_txt.split('\n\n')
        for obj in dwarf_objs:
            if not obj.startswith('0x') or "DW_AT_name" not in obj:
                continue
            if "DW_TAG_subprogram" not in obj and "DW_TAG_formal_parameter" not in obj:
                continue

            obj_addr, obj_type, obj_dict = parse_dwarf_obj(obj)
            if obj_type == "DW_TAG_subprogram":
                func_objs.append((obj_addr, obj_dict))
                func_names_list.append(obj_dict["DW_AT_name"])
                current_func = obj_dict
            elif obj_type == "DW_TAG_formal_parameter":
                if current_func["DW_AT_name"] in param_dict.keys():
                    param_dict[current_func["DW_AT_name"]].append(obj_dict)
                else:
                    param_dict[current_func["DW_AT_name"]] = [obj_dict]
    return func_objs, param_dict, func_names_list


def collect_glob_vars(c_src_path: str):
    out_path, clang_dwarf_txt_path = clang_dwarf(c_src_path)
    wasm_path, js_path, wasm_dwarf_txt_path = emscripten_dwarf(c_src_path)

    wasm_glob_objs, wasm_name_list = traverse_dwarf(wasm_dwarf_txt_path)
    clang_glob_objs, clang_name_list = traverse_dwarf(clang_dwarf_txt_path)

    new_wasm_globs = []
    new_clang_globs = []
    for obj in clang_glob_objs:
        if obj[1]["DW_AT_name"] in wasm_name_list:
            new_clang_globs.append(obj)
            for wasm_obj in wasm_glob_objs:
                if wasm_obj[1]["DW_AT_name"] == obj[1]["DW_AT_name"]:
                    new_wasm_globs.append(wasm_obj)
                    break
            continue

    # debug
    # print(new_wasm_globs)
    # print(new_clang_globs)

    # status, output = utils.cmd("rm {}".format(out_path))
    # status, output = utils.cmd("rm {}".format(wasm_path))
    # status, output = utils.cmd("rm {}".format(js_path))
    return new_wasm_globs, new_clang_globs


def collect_funcs(c_src_path: str):
    out_path, clang_dwarf_txt_path = clang_dwarf(c_src_path)
    wasm_path, js_path, wasm_dwarf_txt_path = emscripten_dwarf(c_src_path)

    wasm_func_objs, wasm_param_dict, wasm_func_names_list = traverse_dwarf_subprogs(wasm_dwarf_txt_path)
    clang_func_objs, clang_param_dict, clang_func_names_list = traverse_dwarf_subprogs(clang_dwarf_txt_path)

    new_wasm_funcs = []
    new_clang_funcs = []
    for obj in clang_func_objs:
        if obj[1]["DW_AT_name"] in wasm_func_names_list:
            new_clang_funcs.append(obj)
            for wasm_obj in wasm_func_objs:
                if wasm_obj[1]["DW_AT_name"] == obj[1]["DW_AT_name"]:
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
                    break
            continue

    # status, output = utils.cmd("rm {}".format(out_path))
    # status, output = utils.cmd("rm {}".format(wasm_path))
    # status, output = utils.cmd("rm {}".format(js_path))

    return (new_wasm_funcs, wasm_param_dict, wasm_func_names_list), (new_clang_funcs, clang_param_dict, clang_func_names_list)


if __name__ == '__main__':
    # get_global_vars("/home/tester/Documents/WebAssembly/examples/test1090_re.c")

    collect_glob_vars("/home/tester/Documents/WebAssembly/examples/test1090_re.c")
    collect_funcs("/home/tester/Documents/WebAssembly/examples/test1090_re.c")

