import re
import os
import sys

import profile
import wasm_instrument
import pin_instrument


def get_name_and_addr(glob_obj: dict):
    """ This function could be complex to handle different array/structure/union type """
    obj = glob_obj
    obj_name = obj['DW_AT_name'].strip('()').strip('"')
    obj_addr = obj["DW_AT_location"]
    obj_addr = int(obj_addr.strip('()').split(' ')[1], 16)

    obj_type = obj["DW_AT_type"]
    if '[' in obj_type:  # array, return address list
        obj_list = []
        obj_type = obj["DW_AT_type"]
        if mat := re.search(r'\(0x[\da-fA-F]+\s"(\w+)\[(\d+)]"\)', obj_type):
            obj_type = mat.group(1)
            obj_num = int(mat.group(2))
            if "int64" in obj_type:
                step_size = 8
            elif "int32" in obj_type:
                step_size = 4
            elif "int16" in obj_type:
                step_size = 2
            elif "int8" in obj_type:
                step_size = 1
            else:
                assert False, "glob obj type: {} not implemented".format(obj_type)

            for i in range(obj_num):
                obj_list.append((obj_name+'[{}]'.format(i), obj_addr+i*step_size))
            return obj_list, (obj_addr, obj_addr+(obj_num-1)*step_size)
        else:
            assert False

    else:  # single addr
        return [(obj_name, obj_addr)], (obj_addr, obj_addr)


def generalize_wasm_trace(trace_path: str, wasm_globs: list, wasm_func_objs: list, wasm_param_dict: dict):
    func_trace_dict = dict()
    glob_trace_dict = dict()

    with open(trace_path, 'r') as f:
        lines = f.readlines()
        idx = 0
        while idx < len(lines):
            l = lines[idx]
            if l.startswith('$') and 'R:' not in l:  # func call
                func_name = l.strip().strip('$')
                func_key = '("{}")'.format(func_name)
                param_list = wasm_param_dict[func_key] if func_key in wasm_param_dict.keys() else []
                arg_list = []
                for param in param_list:
                    idx += 1
                    l = lines[idx]
                    assert l.startswith('P:')
                    arg_value = int(l[l.find(':')+1:].strip(), 16)
                    arg_list.append(arg_value)
                if func_name in func_trace_dict.keys():
                    func_trace_dict[func_name].append(('P', arg_list))
                else:
                    func_trace_dict[func_name] = [('P', arg_list)]
            elif l.startswith('$') and 'R:' in l:  # func return
                func_name = l[:l.find('R:')].strip('$ ')
                ret_value = int(l[l.find(':')+1:].strip(), 16)
                if func_name in func_trace_dict.keys():
                    func_trace_dict[func_name].append(('R', [ret_value]))
                else:
                    func_trace_dict[func_name] = [('R', [ret_value])]
            elif l.startswith('W: '):  # globals write
                write_addr = int(l[l.find(':')+1:].strip(), 16)
                idx += 1
                l = lines[idx]
                assert l.startswith('V: ')
                write_value = int(l[l.find(':') + 1:].strip(), 16)

                glob_name = ''  # find corresponding global name
                for obj in wasm_globs:
                    if len(glob_name) > 0:
                        break
                    obj = obj[1]
                    obj_list, (min_addr, max_addr) = get_name_and_addr(obj)
                    if min_addr <= write_addr <= max_addr:
                        for name, addr in obj_list:
                            if write_addr == addr:
                                glob_name = name
                                break
                if len(glob_name) != 0:
                    if glob_name in glob_trace_dict:
                        glob_trace_dict[glob_name].append(write_value)
                    else:
                        glob_trace_dict[glob_name] = [write_value]

            elif l.startswith('P: ') or l.startswith('V: '):
                assert False, 'error during parsing raw wasm trace.'
            else:
                pass
            idx += 1
    return glob_trace_dict, func_trace_dict


def get_func_obj(func_addr: int, func_objs: list):
    for obj in func_objs:
        obj = obj[1]
        current_addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
        if current_addr == func_addr:
            return obj


def generalize_pin_trace(trace_path: str, clang_globs: list, clang_func_objs: list, clang_param_dict: dict):
    func_trace_dict = dict()
    glob_trace_dict = dict()

    with open(trace_path, 'r') as f:
        lines = f.readlines()
        idx = 0
        while idx < len(lines):
            l = lines[idx]
            if l.startswith('>') and 'R:' not in l:  # func call
                func_addr = int(l.strip().strip('>'), 16)
                func_obj = get_func_obj(func_addr, clang_func_objs)
                func_name = func_obj["DW_AT_name"].strip('()').strip('"')
                func_key = func_obj["DW_AT_name"]

                param_list = clang_param_dict[func_key] if func_key in clang_param_dict.keys() else []
                arg_list = []
                for param in param_list:
                    idx += 1
                    l = lines[idx]
                    assert l.startswith('P:')
                    arg_value = int(l[l.find(':') + 1:].strip(), 16)
                    arg_list.append(arg_value)
                if func_name in func_trace_dict.keys():
                    func_trace_dict[func_name].append(('P', arg_list))
                else:
                    func_trace_dict[func_name] = [('P', arg_list)]
            elif l.startswith('>') and 'R:' in l:  # func return
                func_addr = int(l.split(' ')[0].strip().strip('>'), 16)
                func_obj = get_func_obj(func_addr, clang_func_objs)
                func_name = func_obj["DW_AT_name"].strip('()').strip('"')

                ret_value = int(l[l.find(':') + 1:].strip(), 16)
                if func_name in func_trace_dict.keys():
                    func_trace_dict[func_name].append(('R', [ret_value]))
                else:
                    func_trace_dict[func_name] = [('R', [ret_value])]
            elif l.startswith('W: '):  # globals write
                write_addr = int(l.split(':')[1].strip(), 16)
                idx += 1
                l = lines[idx]
                assert l.startswith('V: ')
                write_value = int(l[l.find(':') + 1:].strip(), 16)

                glob_name = ''  # find corresponding global name
                for obj in clang_globs:
                    obj = obj[1]
                    obj_list, (min_addr, max_addr) = get_name_and_addr(obj)
                    if min_addr <= write_addr <= max_addr:
                        for name, addr in obj_list:
                            if write_addr == addr:
                                glob_name = name
                                break
                assert len(glob_name) != 0, "error: global {} not founded".format(hex(write_addr))

                if glob_name in glob_trace_dict:
                    glob_trace_dict[glob_name].append(write_value)
                else:
                    glob_trace_dict[glob_name] = [write_value]

            elif l.startswith('P: ') or l.startswith('V: '):
                assert False, 'error during parsing raw wasm trace.'
            else:
                pass
            idx += 1
    return glob_trace_dict, func_trace_dict


def trace_check_glob_correct(wasm_glob_trace_dict: dict, clang_glob_trace_dict: dict, wasm_globs: list):
    inconsistent_list = []
    for glob_name, glob_trace in wasm_glob_trace_dict.items():
        glob_key = glob_name
        if '[' in glob_key:
            glob_key = glob_key[:glob_key.find('[')]
        for obj in wasm_globs:
            obj = obj[1]
            if obj["DW_AT_name"] == '("{}")'.format(glob_key):
                break
        assert obj["DW_AT_name"] == '("{}")'.format(glob_key)
        if '*' in obj["DW_AT_type"]:  # TODO: currently we ignore all pointers
            continue

        clang_trace = clang_glob_trace_dict[glob_name]
        if glob_trace[-1] != clang_trace[-1]:
            inconsistent_list.append(glob_name)
            print('glob trace inconsistency founded.')
            print('glob_name: {}, wasm_last_write: {}, clang_last_write: {}'.format(glob_name, glob_trace[-1], clang_trace[-1]))
    return inconsistent_list


def trace_check_glob_perf(wasm_glob_trace_dict: dict, clang_glob_trace_dict: dict):
    pass


def trace_check_func_correct(wasm_func_trace_dict: dict, clang_func_trace_dict: dict, wasm_func_objs: list, wasm_param_dict: dict):
    inconsistent_list = []

    for func_name, func_trace in wasm_func_trace_dict.items():
        if func_name == 'main':
            continue  # ignore main function, as the return value is not captured by pin tool (tracer)

        func_key = '("{}")'.format(func_name)
        check_flags = []
        params = wasm_param_dict[func_key]
        for param in params:
            if '*' in param["DW_AT_type"] or '[' in param["DW_AT_type"]:
                # TODO: currently ignore all pointer/array arguemnts
                check_flags.append(False)
            else:
                check_flags.append(True)

        clang_trace = clang_func_trace_dict[func_name]
        assert len(clang_trace) == len(func_trace), "error: inconsistent length of function call.\nIs this possible?"
        for i in range(len(func_trace)):
            trace_item = func_trace[i]
            clang_trace_item = clang_trace[i]
            item_type = trace_item[0]
            item_values = trace_item[1]
            clang_item_type = clang_trace_item[0]
            clang_item_values = clang_trace_item[1]
            assert item_type == clang_item_type, 'error: inconsistent item type in func trace of {]'.format(func_name)
            for j in range(len(check_flags)):
                chk = check_flags[j]
                if chk and item_values[j] != clang_item_values[j]:
                    inconsistent_list.append(func_name)
                    print('func trace inconsistency founded.')
                    print('func_name: {}, item_index: {}, item_type: {}, arg_index: {}, arg_type: {}, wasm_arg_value: {}, clang_arg_value: {}'.format(
                           func_name, i, item_type, j, params[j]["DW_AT_type"], item_values[j], clang_item_values[j]))
    return inconsistent_list


def trace_check_func_perf(wasm_func_trace_dict: dict, clang_func_trace_dict: dict):
    pass


def trace_check(c_src_path: str):

    # profile, get dwarf information of global variables and function arguments
    wasm_globs, clang_globs = profile.collect_glob_vars(c_src_path)
    (wasm_func_objs, wasm_param_dict, wasm_func_names_list), \
        (clang_func_objs, clang_param_dict, clang_func_names_list) = profile.collect_funcs(c_src_path)

    # compile
    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_src_path)
    elf_path, dwarf_path = profile.clang_dwarf(c_src_path)

    # get trace
    wasm_instrument.instrument(wasm_path, wasm_globs, wasm_func_objs, wasm_param_dict, wasm_path)
    clang_raw_trace_path = pin_instrument.instrument(c_src_path, clang_globs, clang_func_objs, clang_param_dict, elf_path)
    wasm_raw_trace_path = wasm_instrument.run_wasm(js_path)

    # trace generalization
    wasm_glob_trace_dict, wasm_func_trace_dict = generalize_wasm_trace(wasm_raw_trace_path,
                                                                       wasm_globs, wasm_func_objs, wasm_param_dict)
    clang_glob_trace_dict, clang_func_trace_dict = generalize_pin_trace(clang_raw_trace_path,
                                                                        clang_globs, clang_func_objs, clang_param_dict)

    # TODO: consistency check
    glob_correct_inconsistent_list = trace_check_glob_correct(wasm_glob_trace_dict, clang_glob_trace_dict, wasm_globs)
    # trace_check_glob_perf(wasm_glob_trace_dict, clang_glob_trace_dict)
    func_correct_inconsistent_list = trace_check_func_correct(wasm_func_trace_dict, clang_func_trace_dict, wasm_func_objs, wasm_param_dict)
    # trace_check_func_perf(wasm_func_trace_dict, clang_func_trace_dict)

    print(glob_correct_inconsistent_list)
    print(func_correct_inconsistent_list)


def main():
    # test
    c_src_path = "/home/tester/Documents/WebAssembly/examples/test1090_re.c"
    trace_check(c_src_path)


if __name__ == '__main__':
    main()
