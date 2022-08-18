import os
import re
import sys
import time
from multiprocessing import Pool

import utils
import profile
import trace_consistency


def simple_test(process_idx: int):
    """ Clang O3 vs. Emcc O0 + wasm-opt O3
        Mainly focus on the functionality errors
    """
    file_idx = 0
    while file_idx < 2000:
        tmp_file_idx = file_idx
        file_idx += 1
        # print(tmp_file_idx)
        c_path = os.path.join('./find_wasm_opt_bug', 'test{}-{}.c'.format(process_idx, tmp_file_idx))
        
        while True:
            utils.get_one_csmith(c_path)

            wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
            elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O0')

            output1, stderr1 = utils.run_single_prog_err(elf_path)
            output2, stderr2 = utils.run_single_prog_err("node {}".format(js_path))
            if (len(stderr1) > 0 or len(stderr2) > 0) and "by zero" not in stderr2:
                break  # one of the program did not return normally

            if output1 == output2:
                break  # exclude FPs caused by Undefined Behaviors

        wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-all')

        # lightweight checking
        output1, status1 = utils.run_single_prog(elf_path)
        output2, status2 = utils.run_single_prog("node {}".format(js_path))

        # debug 
        # input("continue?")

        # heavyweight checking
        # glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3', need_compile=False)
        if status1 and not status2:
            # x86 program did not return normally
            print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))
            continue
        elif not status1 and status2:
            # wasm program did not return normally
            print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))
            continue
        elif output1 != output2:
            print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))      
            continue
        else:
            status, output = utils.cmd("rm ./find_wasm_opt_bug/test{}-{}.*".format(process_idx, tmp_file_idx))

    # print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))


def trace_test(process_idx: int):
    """ Clang O3 vs. Emcc O0 + wasm-opt O3
        Mainly focus on the under-optimization issues
    """
    print("Start testing...process id {}".format(process_idx))
    file_idx = 0
    while file_idx < 10000:
        tmp_file_idx = file_idx
        file_idx += 1
        # print(tmp_file_idx)
        c_path = os.path.join('./find_wasm_opt', 'test{}-{}.c'.format(process_idx, tmp_file_idx))
        
        while True:
            utils.get_one_csmith(c_path)

            wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
            elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O3')

            output1, status1 = utils.run_single_prog(elf_path)
            output2, status2 = utils.run_single_prog("node {}".format(js_path))
            if output1 == output2:
                break  # exclude FPs caused by Undefined Behaviors
        # print('test{}-{}.c generated'.format(process_idx, tmp_file_idx))

        wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O3')

        # lightweight checking
        output1, status1 = utils.run_single_prog(elf_path)
        output2, status2 = utils.run_single_prog("node {}".format(js_path))

        # heavyweight checking
        glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3', need_compile=False)

        if len(glob_correct) == 0 and len(func_correct) == 0:
            if len(glob_perf) != 0 or len(func_perf) != 0:
                print("Possible under-opt case: test{}-{}".format(process_idx, tmp_file_idx))
                status, output = utils.cmd("mv ./find_wasm_opt/test{}-{}.* ./find_wasm_opt/under_opt".format(process_idx, tmp_file_idx))
        elif (len(glob_correct) != 0 or len(func_correct) != 0) and output1 != output2:
            print("Possible func-bug case: test{}-{}".format(process_idx, tmp_file_idx))
            status, output = utils.cmd("mv ./find_wasm_opt/test{}-{}.* ./find_wasm_opt/func_bug".format(process_idx, tmp_file_idx))
        else:
            print("Possible func-FP case: test{}-{}".format(process_idx, tmp_file_idx))
            status, output = utils.cmd("mv ./find_wasm_opt/test{}-{}.* ./find_wasm_opt/func_FPs".format(process_idx, tmp_file_idx))

        status, output = utils.cmd("rm ./find_wasm_opt/test{}-{}.*".format(process_idx, tmp_file_idx))

    # print("Possible case: test{}-{}".format(process_idx, tmp_file_idx))


def single_test(c_path: str):
    elf_path = c_path[:-2] + '.out'
    js_path = c_path[:-2] + '.js'
    wasm_path = c_path[:-2] + '.wasm'

    wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
    elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O3')

    output1, status1 = utils.run_single_prog(elf_path)
    output2, status2 = utils.run_single_prog("node {}".format(js_path))

    wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O4')

    output1, status1 = utils.run_single_prog(elf_path)
    output2, status2 = utils.run_single_prog("node {}".format(js_path))

    glob_correct, func_correct, glob_perf, func_perf = trace_consistency.trace_check(c_path, clang_opt_level='-O3', emcc_opt_level='-O3', need_compile=False)


def worker1(sleep_time: int):
    time.sleep(sleep_time * 1)
    try:
        simple_test(sleep_time)
    except Exception as e:
        pass


def worker2(sleep_time: int):
    time.sleep(sleep_time * 1)
    try:
        trace_test(sleep_time)
    except Exception as e:
        pass


def test_emi(dir_path="/home/tester/Documents/EMI/DecFuzzer/testcases_emi"):
    for i in range(200):
        for j in range(10):
            c_path = os.path.join(dir_path, 'test{}-{}.c'.format(i, j))

            tmp_out = c_path[:-2] + '.out'
            tmp_js = c_path[:-2] + '.js'
            tmp_wasm = c_path[:-2] + '.wasm'
            utils.cmd("rm {}".format(tmp_out))
            utils.cmd("rm {}".format(tmp_wasm))
            utils.cmd("rm {}".format(tmp_js))

            wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level="-O0")
            elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level="-O0")

            # check compilation results
            if not os.path.exists(tmp_out) or not os.path.exists(tmp_js) or not os.path.exists(tmp_wasm):
                print(c_path)
                continue

            output1, stderr1 = utils.run_single_prog_err(elf_path)
            output2, stderr2 = utils.run_single_prog_err("node {}".format(js_path))

            if len(stderr1) > 0 or len(stderr2) > 0 or output1.strip() != output2.strip():
                f1 = os.path.join(dir_path + '/func_bug_wasm_opt', 'test{}-{}.c'.format(i, j))
                status, output = utils.cmd("cp {} {}".format(c_path, f1))
                continue

            # try with wasm-opt and check again
            wasm_path, wasm_dwarf_txt_path = utils.wasm_opt(wasm_path, wasm_opt_level='-O4')
            # output1, status1 = utils.run_single_prog(elf_path)
            output2, stderr2 = utils.run_single_prog_err("node {}".format(js_path))

            if len(stderr2) > 0 or output1.strip() != output2.strip():
                f1 = os.path.join(dir_path + '/func_bug_wasm_opt', 'test{}-{}.c'.format(i, j))
                status, output = utils.cmd("cp {} {}".format(c_path, f1))
                continue


def by_zero_test(dir_path="./find_wasm_opt_bug"):
    for process_idx in range(16):
        file_idx = 0
        while file_idx < 10000:
            tmp_file_idx = file_idx
            file_idx += 1
            # print(tmp_file_idx)
            c_path = os.path.join('./find_wasm_opt_bug', 'test{}-{}.c'.format(process_idx, tmp_file_idx))
            
            if not os.path.exists(c_path):
                continue

            wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O0')
            elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O0')

            output1, stderr1 = utils.run_single_prog_err(elf_path)
            output2, stderr2 = utils.run_single_prog_err("node {}".format(js_path))
            
            if stderr1 or stderr2:
                if "by zero" in stderr2:
                    err_info = stderr2[stderr2.find("RuntimeError"):]
                    err_info = err_info[:err_info.find('\n')]
                    print(err_info + " " + c_path)
                    status, output = utils.cmd("rm ./find_wasm_opt_bug/test{}-{}.*".format(process_idx, tmp_file_idx))
            elif output1 == output2:
                status, output = utils.cmd("rm ./find_wasm_opt_bug/test{}-{}.*".format(process_idx, tmp_file_idx))
            


if __name__ == '__main__':
    # test_emi()
    # by_zero_test()
    
    # simple_test(7)
    # trace_test(0)
    # single_test("./test15-4498.c")
    # single_test("./test6-1611.c")
    # single_test("./test11-238.c")
    # exit(0)

    if len(sys.argv) == 2 and sys.argv[1] == '1':
        with Pool(16) as p:
            p.starmap(worker1, [(i,) for i in range(16)])
    elif len(sys.argv) == 2 and sys.argv[1] == '2':
        with Pool(16) as p:
            p.starmap(worker2, [(i,) for i in range(16)])
