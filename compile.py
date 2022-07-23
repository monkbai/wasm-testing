""" Deprecated """

import os
import sys
import subprocess
from threading import Timer
# from subprocess import Popen, PIPE, getstatusoutput


import utils
import profile


class cd:
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def cmd(commandline):
    with cd(project_dir):
        # print(commandline)
        status, output = subprocess.getstatusoutput(commandline)
        # print(output)
        return status, output


emsdk_path = '/home/lifter/Documents/WebAssembly/emsdk'
emscripten_path = '/home/lifter/Documents/WebAssembly/emsdk/upstream/emscripten'
node_path = '/home/lifter/Documents/WebAssembly/emsdk/node/14.18.2_64bit/bin'


def cmd_modified(commandline):
    with cd(project_dir):
        my_env = os.environ.copy()
        my_env["PATH"] = emsdk_path + os.pathsep + my_env["PATH"]
        my_env["PATH"] = emscripten_path + os.pathsep + my_env["PATH"]
        my_env["PATH"] = node_path + os.pathsep + my_env["PATH"]
        my_env["EMSDK"] = emsdk_path
        my_env["EM_CONFIG"] = emsdk_path + '/.emscripten'
        my_env["EMSDK_NODE"] = node_path + '/node'

        proc = subprocess.Popen(commandline, env=my_env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return stdout, stderr


def run(prog_path):
    with cd(project_dir):
        # print(prog_path)
        proc = subprocess.Popen(prog_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()  # stderr: summary, stdout:  each statement
        return stdout, stderr


timeout_sec = 3


def run_single_prog(prog_path):
    global timeout_sec
    proc = subprocess.Popen(prog_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timer = Timer(timeout_sec, proc.kill)
    try:
        timer.start()
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()
    return stdout.decode('utf-8'), proc.returncode


project_dir = './'

csmith_path = '/home/lifter/Documents/csmith/src/csmith'
csmith_cmd = csmith_path + " --max-funcs 1 --no-safe-math --max-expr-complexity 5 > {}"
csmith_runtime = '/home/lifter/Documents/csmith/runtime'
csmith_compile_cmd = 'gcc -w {} -I' + csmith_runtime + ' -o {}'


def csmith_generate(c_path: str, elf_path: str):
    c_path = os.path.abspath(c_path)
    elf_path = os.path.abspath(elf_path)

    status, output = cmd(csmith_cmd.format(c_path))
    assert status == 0

    status, output = cmd(csmith_compile_cmd.format(c_path, elf_path))
    assert status == 0

    output, status = run_single_prog('timeout 3 ' + elf_path)
    if status != 0:
        return ''

    return output.strip()


emcc_init = 'source /home/lifter/Documents/WebAssembly/emsdk/emsdk_env.sh'
emcc_cmd = 'emcc -w -O3 -I' + csmith_runtime + ' {} -o {} -o {}'
nodejs_cmd = 'node {}'


def emcc_generate(c_path: str, wasm_path: str, js_path: str):
    assert wasm_path.endswith('.wasm')
    assert js_path.endswith('.js')

    c_path = os.path.abspath(c_path)
    wasm_path = os.path.abspath(wasm_path)
    js_path = os.path.abspath(js_path)

    stdout, stderr = cmd_modified(emcc_cmd.format(c_path, wasm_path, js_path))
    assert os.path.exists(wasm_path) and os.path.exists(js_path)

    # status, output = cmd(nodejs_cmd.format(js_path))
    # assert status == 0
    output, status = run_single_prog(nodejs_cmd.format(js_path))
    if status != 0:
        return ''

    return output.strip()


def fuzz():
    error_list = []
    # 1-1,000: with safe math, default optimization level
    # 1,000-2,000: no safe math, O3 optimization level
    for i in range(1000, 2000):
        print(i)
        c_file = './testcases/test{}.c'.format(i)
        out_file = './testcases/test{}.out'.format(i)
        wasm_file = './testcases/test{}.wasm'.format(i)
        js_file = './testcases/test{}.js'.format(i)
        out1 = csmith_generate(c_file, out_file)
        while len(out1) == 0:
            out1 = csmith_generate(c_file, out_file)
        print(out1)
        out2 = emcc_generate(c_file, wasm_file, js_file)
        print(out2)
        if out1 != out2:
            print('error')
            cmd('cp {} {}'.format(c_file, './errorcases/'))
            cmd('cp {} {}'.format(out_file, './errorcases/'))
            cmd('cp {} {}'.format(wasm_file, './errorcases/'))
            cmd('cp {} {}'.format(js_file, './errorcases/'))
            error_list.append(i)

    print(error_list)


def post_check(dir_path: str):
    tp_list = []  # True Positives
    file_idx = 0
    while file_idx < 260:
        c_path = os.path.join(dir_path, 'test{}.c'.format(file_idx))
        if not os.path.exists(c_path):
            file_idx += 1
            continue

        wasm_path, js_path, wasm_dwarf_txt_path = profile.emscripten_dwarf(c_path, opt_level='-O2')
        elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level='-O2')
        output1, status = utils.run_single_prog(os.path.join(dir_path, 'test{}.out'.format(file_idx)))
        output2, status = utils.run_single_prog("node {}".format(os.path.join(dir_path, 'test{}.js'.format(file_idx))))
        if output1 != output2:
            tp_list.append(file_idx)
        else:
            # utils.cmd("mv {} {}".format(c_path, os.path.join(dir_path, "UndefinedBehaviors")))
            pass

        file_idx += 1
    print(tp_list)


if __name__ == '__main__':
    post_check("/home/tester/Documents/WebAssembly/wasm-compiler-testing/inconsis_trace/bug_cases")
    # out1 = csmith_generate('./testcases/test.c', './testcases/test.out')
    # print(out1)
    # out2 = emcc_generate('./testcases/test.c', './testcases/test.wasm', './testcases/test.js')
    # print(out2)
    # assert out1 == out2
    fuzz()
