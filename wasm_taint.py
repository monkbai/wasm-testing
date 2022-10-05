import re
import os
import sys


def func2blk(func_body: str):
    """ split function body into wasm code blocks """
    blks = []
    lines = func_body.split('\n')
    cur_indent = 0
    cur_blk = []
    for i in range(len(lines)):
        # using the indent to split blocks
        l = lines[i]
        indent = l.find(l.strip())

        if indent == cur_indent:
            cur_blk.append(lines[i])
        elif cur_indent != 0 and indent != cur_indent:
            if len(cur_blk) > 3:
                blks.append(cur_blk)
            cur_indent = indent
            cur_blk = [lines[i]]
        elif cur_indent == 0:
            cur_indent = indent
            cur_blk = [lines[i]]

    return blks


def reverse_taint(blk: list):
    """ return store_inst_count and related_inst_count """
    store_inst_count = 0
    related_inst_count = 0

    related_inst_list = []  # for debug

    # data structure used in taint analysis
    stack = []  # push -> append, pop -> pop, the last value is the stack top value
    variable_dict = dict()

    blk_size = len(blk)
    idx = blk_size - 1
    while idx > -1:
        l = blk[idx]
        l = l.strip()
        idx -= 1
        if l == ')':
            continue
        if mat := re.match(r"[i|f](\d+)\.store", l):
            # a store instruction, two values on the stack top are tainted (addr, store val)
            stack.append("addr")
            stack.append("val")
            store_inst_count += 1
            related_inst_count += 1
            related_inst_list.insert(0, l)
        elif mat := re.match(r"[i|f](\d+)\.load", l):
            # a load instruction, if the stack top value is tainted, then this inst is tainted
            # (currently, we do not taint linear memory)
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            stack.append("")  # the load address
            if top_value:
                related_inst_count += 1
                related_inst_list.insert(0, l)
        elif mat := re.match(r"[i|f](\d+)\.const", l):
            # val on the stack top is pushed by this const inst
            if len(stack) > 0 and stack.pop():
                related_inst_count += 1
                related_inst_list.insert(0, l)
        elif mat := re.match(r"(global|local)\.set ([\w_$]+)", l):
            # means before this inst, a (possibly) unrelated value is on the stack
            var_name = mat.group(2)
            var_value = variable_dict[var_name] if var_name in variable_dict else ""
            variable_dict.pop(var_name) if var_name in variable_dict else None # the value before set is unknown
            stack.append(var_value)
            if var_value:
                related_inst_count += 1
                related_inst_list.insert(0, l)
        elif mat := re.match(r"(global|local)\.get ([\w_$]+)", l):
            var_name = mat.group(2)
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            variable_dict[var_name] = top_value
            if top_value:
                related_inst_count += 1
                related_inst_list.insert(0, l)
        elif mat := re.match(r"(local)\.tee ([\w_$]+)", l):
            var_name = mat.group(2)
            var_value = variable_dict[var_name] if var_name in variable_dict else ""
            variable_dict.pop(var_name) if var_name in variable_dict else None # the value before set is unknown
            # stack.append(var_value)
            if var_value:
                related_inst_count += 1
                related_inst_list.insert(0, l)
        elif mat := re.match(r"[i|f](\d+)\.(add|sub|mul|div|rem|and|or|xor|shl|shr|rotl|rotr)", l):
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            if top_value:
                stack.append("val")
                stack.append("val")
                related_inst_count += 1
                related_inst_list.insert(0, l)
            else:
                stack.append("")
                stack.append("")
        elif mat := re.match(r"[i|f](\d+)\.(eq|ne|lt|gt|le|ge)", l):
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            if top_value:
                stack.append("val")
                stack.append("val")
                related_inst_count += 1
                related_inst_list.insert(0, l)
            else:
                stack.append("")
                stack.append("")
        elif mat := re.match(r"[i|f](\d+)\.(eqz)", l):
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            if top_value:
                stack.append("val")
                related_inst_count += 1
                related_inst_list.insert(0, l)
            else:
                stack.append("")
        elif mat := re.match(r"f(\d+)\.(abs|neg|ceil|floor|trunc|nearest|sqrt)", l):
            pass
        elif mat := re.match(r"[i|f](\d+)\.(extend|trunc|convert|wrap|reinterpret)", l):
            pass
        elif mat := re.match(r"select", l):
            if len(stack) > 0:
                top_value = stack.pop()
            else:
                top_value = ""
            if top_value:
                stack.append("val")
                stack.append("val")
                stack.append("val")
                related_inst_count += 1
                related_inst_list.insert(0, l)
            else:
                stack.append("")
                stack.append("")
                stack.append("")
        elif mat := re.match(r"call", l):  # TODO
            # do not track function call
            stack.clear()
        elif mat := re.match(r"drop", l):
            stack.append("")
        elif mat := re.match(r"(if|else|loop|br|return|block|nop|end|unreachable)", l):
            pass
        elif mat := re.match(r"\(local", l):
            pass
        else:
            assert False, "inst <{}> is not implemented.".format(l)

    return store_inst_count, related_inst_count


def func_call_cost(func_txt: str):
    param_count = 0
    result_count = 0
    func_name = ''

    stack_update_count = 0
    param_store_count = 0

    stack_var = 0
    lines = func_txt.split('\n')
    idx = 0
    while idx < len(lines):
        l = lines[idx]
        l = l.strip()
        if l.startswith("(func $"):
            func_name = re.search(r"\(func (\$\w+)", l).group(1)
            if mat := re.search(r"\(param( \w+)+\)", l):
                param_count = mat.group().count(' ')
            if mat := re.search(r"\(result( \w+)+\)", l):
                result_count = mat.group().count(' ')
        elif l.startswith("global.get $__stack_pointer") and \
                'i32.const' in lines[idx+1] and \
                'i32.sub' in lines[idx+2] and \
                'local.tee' in lines[idx+3] and \
                'global.set $__stack_pointer' in lines[idx+4]:
            stack_var = re.search(r"local.tee (\d+)", lines[idx+3]).group(1)
            stack_update_count += 5
            idx += 4
        elif l.startswith("global.get $__stack_pointer") and \
                'i32.const' in lines[idx+1] and \
                'i32.sub' in lines[idx+2] and \
                'local.tee' in lines[idx+3]:
            stack_var = re.search(r"local.tee (\d+)", lines[idx+3]).group(1)
            stack_update_count += 4
            idx += 2
        elif l.startswith("local.get ") and \
                'i32.const' in lines[idx+1] and \
                'i32.add' in lines[idx+2] and \
                'global.set $__stack_pointer' in lines[idx+3]:
            stack_update_count += 4
            idx += 3
        elif ('local.tee' in l or 'local.get' in l) and \
                ('i32.const' in lines[idx+1] or 'local.get' in lines[idx+1]) and \
                'i32.store' in lines[idx+2]:
            param_store_count += 3
            idx += 2
        idx += 1
    return stack_update_count + param_store_count + param_count + result_count + 1


overall_s_count = 0
overall_r_count = 0

overall_func_count = 0
overall_func_cost = 0


def analysis(wat_path: str):
    global overall_s_count, overall_r_count, overall_func_count, overall_func_cost
    func_list = []
    with open(wat_path, 'r') as f:
        wat_txt = f.read()
        wat_txt = wat_txt[wat_txt.find("  (func $"):]
        wat_txt = wat_txt[:wat_txt.find("  (table")]
        while wat_txt.startswith("  (func ") and wat_txt.count("  (func ") > 1:
            func_txt = wat_txt[:wat_txt.find("  (func ", 1)]
            wat_txt = wat_txt[wat_txt.find("  (func ", 1):]
            func_list.append(func_txt)
        func_list.append(wat_txt)

    for f in func_list:
        func_cost = func_call_cost(f)
        overall_func_count += 1
        overall_func_cost += func_cost

    store_count = 0
    related_count = 0
    for f in func_list:
        blks = func2blk(f)
        for b in blks:
            s_count, r_count = reverse_taint(b)
            store_count += s_count
            related_count += r_count
    # print("store_inst_count:", store_count)
    # print("related_inst_count:", related_count)
    overall_s_count += store_count
    overall_r_count += related_count


if __name__ == '__main__':
    # analysis("/home/tester/Downloads/adpcm/adpcm.wat")
    analysis("/home/tester/Downloads/mips/mips.wat")
    analysis("/home/tester/Downloads/gsm/gsm.wat")
    analysis("/home/tester/Downloads/jpeg/main.wat")
    analysis("/home/tester/Downloads/motion/mpeg2.wat")
    print("overall_s_count:", overall_s_count)
    print("overall_r_count:", overall_r_count)
    print(overall_r_count / overall_s_count)
    print("overall_func_count:", overall_func_count)
    print("overall_func_cost:", overall_func_cost)
    print(overall_func_cost / overall_func_count)

    analysis("/home/tester/Documents/BenchmarkingWebAssembly/modified_benchmarks/CHStone_v1.11_150204/mips/mips.wat")
    analysis("/home/tester/Documents/BenchmarkingWebAssembly/modified_benchmarks/CHStone_v1.11_150204/adpcm/adpcm.wat")
    analysis("/home/tester/Documents/BenchmarkingWebAssembly/modified_benchmarks/CHStone_v1.11_150204/gsm/gsm.wat")
    analysis("/home/tester/Documents/BenchmarkingWebAssembly/modified_benchmarks/CHStone_v1.11_150204/jpeg/main.wat")
    analysis("/home/tester/Documents/BenchmarkingWebAssembly/modified_benchmarks/CHStone_v1.11_150204/motion/mpeg2.wat")

    print("overall_s_count:", overall_s_count)
    print("overall_r_count:", overall_r_count)
    print(overall_r_count / overall_s_count)
    print("overall_func_count:", overall_func_count)
    print("overall_func_cost:", overall_func_cost)
    print(overall_func_cost / overall_func_count)
