import re
import os
import sys
import copy

import lcs
import profile
import pointed_objs
import wasm_instrument
import pin_instrument


glob_array_dict = dict()


def clear_glob_array_dict():
    global glob_array_dict
    glob_array_dict.clear()


def get_name_and_addr(glob_obj: dict):
    """ This function could be complex to handle different array/structure/union type """
    global glob_array_dict

    obj = glob_obj
    obj_name = obj['DW_AT_name'].strip('()').strip('"')
    obj_addr = obj["DW_AT_location"]
    obj_addr = int(re.search(r"DW_OP_addr (\w+)", obj_addr).group(1), 16)
    # obj_addr = int(obj_addr.strip('()').split(' ')[1], 16)
    obj_type = obj["DW_AT_type"]

    obj_key = obj["DW_AT_name"] + obj["DW_AT_location"]
    if obj_key in glob_array_dict:
        return glob_array_dict[obj_key]

    if '[' in obj_type:  # array, return address list
        obj_list = []
        obj_type = obj["DW_AT_type"]
        obj_type = obj_type.replace('const ', '')
        obj_type = obj_type.replace('volatile ', '')
        if mat := re.search(r'\(0x[\da-fA-F]+\s"(\w+)((\[\d+])+)"\)', obj_type):
            obj_type = mat.group(1)
            array_dim = mat.group(2)
            array_dim = array_dim.replace('[', '')
            array_dim = array_dim.split(']')
            array_dim.remove('')
            obj_num = 1
            for dim in array_dim:
                dim = dim.strip()
                if len(dim) > 0:
                    obj_num *= int(dim)
            if "int64" in obj_type:
                step_size = 8
            elif "int32" in obj_type:
                step_size = 4
            elif "int16" in obj_type:
                step_size = 2
            elif "int8" in obj_type:
                step_size = 1
            elif 'char' not in obj_type and 'short' not in obj_type and 'int' not in obj_type and 'long' not in obj_type:
                return [], (0, 0, 0)  # ignore complex structure/union
            else:
                assert False, "glob obj type: {} not implemented".format(obj_type)

            # TODO: handle DW_OP_piece
            if 'DW_OP_piece' in obj["DW_AT_location"]:
                if obj["DW_AT_type"].count("[") > 1:
                    return [], (0, 0, 0)  # ignore complex multiple dimension array with optimized memory layout

                assert obj["DW_AT_type"].count("[") == 1

                # get #optimized elements
                opt_num = 0
                it = re.finditer(r"DW_OP_piece (0x\d+)", obj["DW_AT_location"].strip('()'))
                for mat in it:
                    opt_num += int(int(mat.group(1), 16) / step_size)

                tmp_list = []
                tmp_idx = 0
                addr_info = obj["DW_AT_location"].strip('()')
                assert addr_info.count("DW_OP_addr") == 1
                addr_info = addr_info.split(', ')
                for dwarf_item in addr_info:
                    if mat := re.match(r"DW_OP_piece 0x(\w+)", dwarf_item):
                        tmp_n = int(int(mat.group(1), 16) / step_size)
                        for i in range(tmp_n):
                            tmp_list += [(obj_name+'[{}]'.format(tmp_idx), 0)]
                            tmp_idx += 1
                    elif mat := re.match(r"DW_OP_addr 0x(\w+)", dwarf_item):
                        tmp_addr = int(mat.group(1), 16)
                        for i in range(obj_num - opt_num):
                            tmp_list.append((obj_name+'[{}]'.format(tmp_idx), tmp_addr))
                            tmp_idx += 1
                            tmp_addr += step_size
                    else:
                        pass
                assert tmp_idx == obj_num
                obj_list = copy.deepcopy(tmp_list)
                min_addr = obj_addr + obj_num * step_size
                max_addr = obj_addr
                for tmp in tmp_list:
                    if tmp[1] == 0:
                        obj_list.remove(tmp)
                    else:
                        max_addr = max(tmp[1], max_addr)
                        min_addr = min(tmp[1], min_addr)
                glob_array_dict[obj_key] = (obj_list, (min_addr, max_addr, step_size))
                return obj_list, (min_addr, max_addr, step_size)

            dim_len = len(array_dim)
            for count in range(obj_num):
                tmp_count = count
                idx_nums = [0 for i in range(dim_len)]
                dim_nums = [1 for i in range(dim_len)]
                for i in range(dim_len):
                    for j in range(i+1, dim_len):
                        dim_nums[i] *= int(array_dim[j])
                for j in range(dim_len):
                    idx_nums[j] = int(tmp_count / dim_nums[j])
                    tmp_count = tmp_count % dim_nums[j]
                name = obj_name
                for k in range(dim_len):
                    name += '[{}]'.format(idx_nums[k])
                obj_list.append((name, obj_addr+count*step_size))
            glob_array_dict[obj_key] = (obj_list, (obj_addr, obj_addr+(obj_num-1)*step_size, step_size))
            return obj_list, (obj_addr, obj_addr+(obj_num-1)*step_size, step_size)
        elif '*' in obj_type and '[' in obj_type:
            return [], (0, 0, 0)  # pointer array, ignore
        else:
            assert False

    else:  # single addr
        # step_size of single var may never be used, but just in case
        if "int64" in obj_type or '*' in obj_type:
            step_size = 8
        elif "int32" in obj_type or '"int"' in obj_type:
            step_size = 4
        elif "int16" in obj_type:
            step_size = 2
        elif "int8" in obj_type:
            step_size = 1
        elif 'char' not in obj_type and 'short' not in obj_type and 'int' not in obj_type and 'long' not in obj_type:
            step_size = None  # ignore complex structure/union
        else:
            assert False, "glob obj type: {} not implemented".format(obj_type)
        glob_array_dict[obj_key] = ([(obj_name, obj_addr)], (obj_addr, obj_addr, step_size))
        return [(obj_name, obj_addr)], (obj_addr, obj_addr, step_size)


def generalize_wasm_trace(trace_path: str, wasm_globs: list, wasm_func_objs: list, wasm_param_dict: dict):
    func_trace_dict = dict()
    glob_trace_dict = dict()
    clear_glob_array_dict()

    def func_trace_add(key, value):
        if key in func_trace_dict.keys():
            func_trace_dict[key].append(value)
        else:
            func_trace_dict[key] = [value]

    def glob_trace_add(key, value):
        if key in glob_trace_dict.keys():
            glob_trace_dict[key].append(value)
        else:
            glob_trace_dict[key] = [value]

    aux_info = ""
    with open(trace_path, 'r') as f:
        lines = f.readlines()
        idx = 0
        while idx < len(lines):
            l = lines[idx]
            if l.startswith('ID:'):
                aux_info = l
            elif l.startswith('$') and 'R:' not in l:  # func call
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

                func_trace_add(func_name, ('P', arg_list, aux_info))
                aux_info = ""

            elif l.startswith('$') and 'R:' in l:  # func return
                func_name = l[:l.find('R:')].strip('$ ')
                ret_value = int(l[l.find(':')+1:].strip(), 16)

                func_trace_add(func_name, ('R', [ret_value], aux_info))
                aux_info = ""

            elif l.startswith('W: '):  # globals write
                write_addr = int(l[l.find(':')+1:].strip(), 16)
                write_size = int(l.split(':')[2].strip())  # TODO: update wasm instrumentation
                idx += 1
                l = lines[idx]
                assert l.startswith('V: ')
                write_value = int(l[l.find(':') + 1:].strip(), 16)

                glob_name = ''  # find corresponding global name
                for obj in wasm_globs:
                    obj = obj[1]
                    obj_list, (min_addr, max_addr, step_size) = get_name_and_addr(obj)
                    if min_addr <= write_addr <= max_addr:
                        for name, addr in obj_list:
                            if write_addr == addr:
                                glob_name = name
                                break
                    if len(glob_name) > 0:
                        break

                if len(glob_name) != 0 and step_size != write_size:
                    # handle optimized writes in wasm binary
                    mask = 1
                    for i in range(step_size*8 - 1):
                        mask = (mask << 1) | 1
                    tmp_list = []
                    while write_size > 0:
                        for name, addr in obj_list:
                            if write_addr == addr:
                                glob_name = name
                                break
                        tmp_list.append((glob_name, write_value & mask))
                        glob_name = ''
                        write_addr += step_size
                        write_value = write_value >> step_size * 8

                    for it in tmp_list:
                        glob_trace_add(it[0], (it[1], aux_info))
                    aux_info = ""

                elif len(glob_name) != 0:
                    glob_trace_add(glob_name, (write_value, aux_info))
                    aux_info = ""

            elif l.startswith('P: ') or l.startswith('V: '):
                assert False, 'error during parsing raw wasm trace.'
            else:
                pass
            idx += 1
    return glob_trace_dict, func_trace_dict


def get_func_obj(func_addr: int, func_objs: list):
    for obj in func_objs:
        obj = obj[1]
        if "DW_AT_low_pc" not in obj:
            continue
        current_addr = int(obj["DW_AT_low_pc"].strip('()'), 16)
        if current_addr == func_addr:
            return obj


def generalize_pin_trace(trace_path: str, clang_globs: list, clang_func_objs: list, clang_param_dict: dict):
    func_trace_dict = dict()
    glob_trace_dict = dict()
    clear_glob_array_dict()

    def func_trace_add(key, value):
        if key in func_trace_dict.keys():
            func_trace_dict[key].append(value)
        else:
            func_trace_dict[key] = [value]

    def glob_trace_add(key, value):
        if key in glob_trace_dict.keys():
            glob_trace_dict[key].append(value)
        else:
            glob_trace_dict[key] = [value]

    aux_info = ""
    with open(trace_path, 'r') as f:
        lines = f.readlines()
        idx = 0
        while idx < len(lines):
            l = lines[idx]
            if l.startswith('0x'):
                aux_info = l
            elif l.startswith('>') and 'R:' not in l:  # func call
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

                func_trace_add(func_name, ('P', arg_list, aux_info))
                aux_info = ""

            elif l.startswith('>') and 'R:' in l:  # func return
                func_addr = int(l.split(' ')[0].strip().strip('>'), 16)
                func_obj = get_func_obj(func_addr, clang_func_objs)
                func_name = func_obj["DW_AT_name"].strip('()').strip('"')

                ret_value = int(l[l.find(':') + 1:].strip(), 16)

                func_trace_add(func_name, ('R', [ret_value], aux_info))
                aux_info = ""

            elif l.startswith('W: '):  # globals write
                write_addr = int(l.split(':')[1].strip(), 16)
                write_size = int(l.split(':')[2].strip())
                idx += 1
                l = lines[idx]
                assert l.startswith('V: ')
                write_value = int(l[l.find(':') + 1:].strip(), 16)

                if write_size == 16:
                    idx += 3
                    l = lines[idx]
                    assert l.startswith('V: ')
                    write_value_con = int(l[l.find(':') + 1:].strip(), 16)

                    # TODO: 16 bytes values, exist in clang O3 binaries
                    # writes to consecutive elements in an array
                    glob_name = ''  # find corresponding global name
                    for obj in clang_globs:
                        obj = obj[1]
                        obj_list, (min_addr, max_addr, step_size) = get_name_and_addr(obj)
                        if min_addr <= write_addr <= max_addr:
                            for name, addr in obj_list:
                                if write_addr == addr:
                                    glob_name = name
                                    break
                        if len(glob_name) != 0:
                            break
                    assert len(glob_name) != 0, "error: global {} not founded".format(hex(write_addr))

                    # founded the corresponding global variable and the step_size,
                    # now split the 16 bytes into consecutive writes
                    if step_size == 8:
                        tmp_list = [(write_addr, write_value), (write_addr+8, write_value_con)]
                    elif step_size == 4:
                        tmp_list = [(write_addr, write_value & 0xffffffff), (write_addr+4, (write_value >> 32)),
                                    (write_addr+8, write_value_con & 0xffffffff), (write_addr+12, (write_value_con >> 32))]
                    else:
                        pass  # complex var

                    if step_size:
                        for w_addr, w_val in tmp_list:
                            for name, addr in obj_list:
                                if w_addr == addr:
                                    glob_trace_add(name, (w_val, aux_info))
                                    break
                        aux_info = ""
                else:
                    glob_name = ''  # find corresponding global name
                    for obj in clang_globs:
                        obj = obj[1]
                        obj_list, (min_addr, max_addr, step_size) = get_name_and_addr(obj)
                        if min_addr <= write_addr <= max_addr:
                            for name, addr in obj_list:
                                if write_addr == addr:
                                    glob_name = name
                                    break

                    if len(glob_name) != 0:
                        # it's possible len(glob_name)==0, some complex cases are not handled
                        if step_size != write_size:
                            # due to compiler optimization
                            # currently, we cannot get the while value of this obj
                            # add an extra auxiliary info
                            aux_info = "OPT\n"+aux_info

                        glob_trace_add(glob_name, (write_value, aux_info))
                        aux_info = ""

            elif l.startswith('P: ') or l.startswith('V: '):
                assert False, 'error during parsing raw wasm trace.'
            elif l.startswith('#eof'):
                break
            else:
                pass
            idx += 1
    return glob_trace_dict, func_trace_dict


def trace_check_glob_correct(wasm_glob_trace_dict: dict, clang_glob_trace_dict: dict, wasm_globs: list, case2_check=False):
    print('\nChecking correctness (global writes) ...')
    inconsistent_list = []

    # Case 1: inconsistent last write
    for glob_name, glob_trace in wasm_glob_trace_dict.items():
        glob_trace = [v[0] for v in glob_trace]
        # find corresponding glob_obj
        glob_key = glob_name
        if '[' in glob_key:
            glob_key = glob_key[:glob_key.find('[')]  # an array element -> array name
        for obj in wasm_globs:
            obj = obj[1]
            if obj["DW_AT_name"] == '("{}")'.format(glob_key):
                break
        assert obj["DW_AT_name"] == '("{}")'.format(glob_key)

        if glob_name not in clang_glob_trace_dict:
            # this function only check correctness inconsistent, so just skip
            continue

        clang_trace = clang_glob_trace_dict[glob_name]
        clang_trace = [v[0] for v in clang_trace]  # remove auxiliary information
        if '*' in obj["DW_AT_type"]:
            # for pointers: using PtrItem
            glob_trace_backup = glob_trace
            glob_trace = []
            for v in glob_trace_backup:
                glob_trace.append(lcs.PtrItem(ptr_name=glob_name, ptr_value=v))

            clang_trace_backup = clang_trace
            clang_trace = []
            for v in clang_trace_backup:
                clang_trace.append(lcs.PtrItem(ptr_name=glob_name, ptr_value=v))

        if glob_trace[-1] != clang_trace[-1] and not clang_glob_trace_dict[glob_name][-1][1].startswith("OPT\n"):  # compiler optimization may only update part of the var
            inconsistent_list.append(glob_name)
            print('>Glob trace inconsistency founded.')
            print('\tglob_name: {}, wasm_last_write: {}, clang_last_write: {}'.format(glob_name, glob_trace[-1], clang_trace[-1]))

    # Case 2: missing global writes
    if case2_check:
        for glob_name, glob_trace in clang_glob_trace_dict.items():
            if glob_name not in wasm_glob_trace_dict:
                glob_key = glob_name
                if '[' in glob_key:
                    glob_key = glob_key[:glob_key.find('[')]  # an array element -> array name
                # exists in wasm globs?
                for obj in wasm_globs:
                    obj = obj[1]
                    if obj["DW_AT_name"] == '("{}")'.format(glob_key):
                        break
                if obj["DW_AT_name"] == '("{}")'.format(glob_key):  # exist
                    inconsistent_list.append(glob_name)
                    print('>Missing glob trace founded.')
                    print('\tglob_name: {}'.format(glob_name))
                else:
                    # TODO: what if the glob does not exist in wasm globs
                    # Ignore
                    pass
                    # inconsistent_list.append(glob_name)
                    # print('>Missing glob definition founded.')
                    # print('\tglob_name: {}'.format(glob_name))
    return inconsistent_list


def trace_check_glob_perf(wasm_glob_trace_dict: dict, clang_glob_trace_dict: dict, wasm_globs: list):
    print('\nChecking performance (global writes) ...')
    inconsistent_list = []
    for glob_name, glob_trace in wasm_glob_trace_dict.items():
        glob_trace = [v[0] for v in glob_trace]
        glob_key = glob_name
        if '[' in glob_key:
            glob_key = glob_key[:glob_key.find('[')]
        for obj in wasm_globs:
            obj = obj[1]
            if obj["DW_AT_name"] == '("{}")'.format(glob_key):
                break
        assert obj["DW_AT_name"] == '("{}")'.format(glob_key)

        if glob_name not in clang_glob_trace_dict:
            inconsistent_list.append(glob_name)
            print('>Redundant glob trace founded.')
            print('\tglob_name: {}'.format(glob_name))
            continue

        clang_trace = clang_glob_trace_dict[glob_name]
        # if clang_trace contains optimized writes (only write part of the whole glob, e.g. 1 byte of int32)
        # simply ignore this glob
        opt_write_flag = False
        for it in clang_trace:
            if 'OPT\n' in it[1]:
                opt_write_flag = True
                break
        if opt_write_flag:
            continue

        clang_trace = [v[0] for v in clang_trace]  # remove auxiliary information
        if '*' in obj["DW_AT_type"]:
            # for pointers: using PtrItem
            glob_trace_backup = glob_trace
            glob_trace = []
            for v in glob_trace_backup:
                glob_trace.append(lcs.PtrItem(ptr_name=glob_name, ptr_value=v))

            clang_trace_backup = clang_trace
            clang_trace = []
            for v in clang_trace_backup:
                clang_trace.append(lcs.PtrItem(ptr_name=glob_name, ptr_value=v))

        lcs_trace, lcs_trace2 = lcs.lcs(clang_trace, glob_trace)
        if len(glob_trace) != len(lcs_trace):
            inconsistent_list.append(glob_name)
            if glob_trace[-1] == clang_trace[-1]:
                print('>Glob trace performance inconsistency founded.')
            else:
                print('>Glob trace correctness inconsistency founded.')
            print('\tglob_name: {},'.format(glob_name), end=' ')
            for i in range(len(glob_trace)):
                if i not in lcs_trace:
                    print('write_index: {}, write_value: {},'.format(i, glob_trace[i]), end=' ')
            print()

    return inconsistent_list


def trace_check_func_correct(wasm_func_trace_dict: dict, clang_func_trace_dict: dict, wasm_func_objs: list, wasm_param_dict: dict):
    # TODO: Clang O0, Wasm O3, mainly focus on the correctness
    print('\nChecking correctness (function calls) ...')
    inconsistent_list = []
    for func_name, func_trace in wasm_func_trace_dict.items():
        if func_name == 'main':
            continue  # ignore main function, as the return value is not captured by pin tool (tracer)

        func_key = '("{}")'.format(func_name)
        pointer_flags = []
        params = wasm_param_dict[func_key]
        for param in params:
            if '*' in param["DW_AT_type"] or '[' in param["DW_AT_type"]:
                # TODO: What array argument looks like?
                if '[' in param["DW_AT_type"]:
                    print("debug: array argument")
                pointer_flags.append(True)
            else:
                pointer_flags.append(False)

        if func_name not in clang_func_trace_dict:
            continue  # the function is inlined in optimized clang binary
        clang_trace = clang_func_trace_dict[func_name]

        # Emscripten has (advanced) optimization strategies that only inline some out of all function calls
        # Thus, we cannot assume/assert len(clang_trace) == len(func_trace)
        # Here, the assumption would be: function calls exist in wasm trace should also exist in clang trace
        func_item_trace = []
        for item in func_trace:
            # item[2] -> auxiliary information
            func_item_trace.append(lcs.FuncItem(func_name=func_name, item_type=item[0], item_values=item[1], pointer_flags=pointer_flags))

        clang_item_trace = []
        for item in clang_trace:
            # item[2] -> auxiliary information
            clang_item_trace.append(lcs.FuncItem(func_name=func_name, item_type=item[0], item_values=item[1], pointer_flags=pointer_flags))

        clang_idx = 0
        for i in range(len(func_item_trace)):
            match_flag = False
            for j in range(clang_idx, len(clang_item_trace)):
                if func_item_trace[i] == clang_item_trace[j]:
                    match_flag = True
                    clang_idx = j + 1
                    break
            if not match_flag:
                inconsistent_list.append(func_name)
                print('>Func trace inconsistency founded.')
                print('\tfunc_name: {}, wasm_item_index: {}, item_type: {}, item_values: {}'.format(
                       func_name, i, func_item_trace[i].type, func_item_trace[i].values))
    return inconsistent_list


def trace_check_func_perf(wasm_func_trace_dict: dict, clang_func_trace_dict: dict, wasm_func_objs: list, wasm_param_dict: dict):
    # TODO: for the performance check, we compare Clang O3 with Wasm O3? i.e. does Wasm compiler have comparable optimization quality?
    print('\nChecking performance (function calls) ...')
    inconsistent_list = []
    for func_name, func_trace in wasm_func_trace_dict.items():
        if func_name == 'main':
            continue  # ignore main function, as the return value is not captured by pin tool (tracer)

        func_key = '("{}")'.format(func_name)
        pointer_flags = []
        params = wasm_param_dict[func_key]
        for param in params:
            if '*' in param["DW_AT_type"] or '[' in param["DW_AT_type"]:
                # TODO: What array argument looks like?
                if '[' in param["DW_AT_type"]:
                    print("debug: array argument")
                pointer_flags.append(True)
            else:
                pointer_flags.append(False)

        if func_name not in clang_func_trace_dict:
            # TODO: is missing inline opportunity a problem?
            # Seems not
            # https://dl.acm.org/doi/10.1145/3503222.3507744

            # print('>Func trace inconsistency founded.')
            #  print('{} could be optimized or inlined.'.format(func_name))
            # inconsistent_list.append(func_name)
            continue

        clang_trace = clang_func_trace_dict[func_name]

        # TODO: if we want to check missed opt opportunity we need to assume it is possible that len(clang_trace) != len(func_trace), i.e. Clang may have some advanced optimizations
        # assert len(clang_trace) == len(func_trace), "error: inconsistent length of function call.\nIs this possible?"
        func_item_trace = []
        for item in func_trace:
            # item[2] -> auxiliary information
            func_item_trace.append(lcs.FuncItem(func_name=func_name, item_type=item[0], item_values=item[1], pointer_flags=pointer_flags))

        clang_item_trace = []
        for item in clang_trace:
            # item[2] -> auxiliary information
            clang_item_trace.append(lcs.FuncItem(func_name=func_name, item_type=item[0], item_values=item[1], pointer_flags=pointer_flags))

        lcs_item_trace, lcs_item_trace2 = lcs.lcs(clang_item_trace, func_item_trace)
        if len(lcs_item_trace) != len(func_item_trace):
            inconsistent_list.append(func_name)
            print('>Func trace inconsistency founded.')
            print('\tfunc_name: {},'.format(func_name), end=' ')
            for i in range(len(func_item_trace)):
                if i not in lcs_item_trace:
                    print('item_index: {}, item_type: {}'.format(i, func_trace[i][0]), end=' ')
            print()
    return inconsistent_list


def trace_check(c_src_path: str):
    print("\nTrace Consistency Checking for {}...".format(c_src_path))
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

    # Before checking
    wat_path = wasm_path[:-5] + '.wat'
    mapping_dict, wasm_objs_dict, clang_objs_dict = pointed_objs.get_pointed_objs_mapping(c_src_path, elf_path, wat_path)
    lcs.FuncItem.set_dict(mapping_dict, wasm_objs_dict, clang_objs_dict)
    lcs.PtrItem.set_dict(mapping_dict, wasm_objs_dict, clang_objs_dict)
    # TODO: update instrumentation, and provided more information to locate bugs

    # trace consistency check
    if len(wasm_globs) > 0:
        glob_correct_inconsistent_list = \
            trace_check_glob_correct(wasm_glob_trace_dict, clang_glob_trace_dict, wasm_globs)
    else:
        glob_correct_inconsistent_list = []
    func_correct_inconsistent_list = \
        trace_check_func_correct(wasm_func_trace_dict, clang_func_trace_dict, wasm_func_objs, wasm_param_dict)

    # if len(glob_correct_inconsistent_list) > 0 or len(func_correct_inconsistent_list) > 0:
    print('glob (incorrect):', glob_correct_inconsistent_list)
    print('func (incorrect):', func_correct_inconsistent_list)
    # else:
    if len(wasm_globs) > 0:
        glob_perf_inconsistent_list = \
            trace_check_glob_perf(wasm_glob_trace_dict, clang_glob_trace_dict, wasm_globs)
    else:
        glob_perf_inconsistent_list = []
    func_perf_inconsistent_list = \
        trace_check_func_perf(wasm_func_trace_dict, clang_func_trace_dict, wasm_func_objs, wasm_param_dict)

    print('glob (performance):', glob_perf_inconsistent_list)
    print('glob (performance):', func_perf_inconsistent_list)

    return glob_correct_inconsistent_list, func_correct_inconsistent_list, glob_perf_inconsistent_list, func_perf_inconsistent_list


def main():
    # test
    c_src_path = "./tmp.c"
    trace_check(c_src_path)


def test(debug_dir="./debug_cases"):
    skip_list = ["1001.c", "1008.c"]
    debug_dir = os.path.abspath(debug_dir)
    files = os.listdir(debug_dir)
    files.sort()
    for f in files:
        if f.endswith('.c'):
            if [True if v in f else False for v in skip_list].count(True) > 0:
                continue
            f = os.path.join(debug_dir, f)
            trace_check(f)


if __name__ == '__main__':
    main()
    test()
