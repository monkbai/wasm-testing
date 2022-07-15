#!/usr/bin/env python3
""" Deprecated """

import os
import sys
import subprocess
from threading import Timer


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


project_dir = './'
emsdk_path = '/home/tester/Documents/WebAssembly/emsdk'
emscripten_path = '/home/tester/Documents/WebAssembly/emsdk/upstream/emscripten'
node_path = '/home/tester/Documents/WebAssembly/emsdk/node/14.18.2_64bit/bin'


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
        return stdout, proc.returncode


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


csmith_path = '/home/tester/Documents/csmith/src/csmith'
csmith_runtime = '/home/tester/Documents/csmith/runtime'
csmith_compile_cmd = 'gcc -w {} -I' + csmith_runtime + ' -o {}'

emcc_init = 'source /home/tester/Documents/WebAssembly/emsdk/emsdk_env.sh'
emcc_cmd = 'emcc -w -g -O2 -I' + csmith_runtime + ' {} -o {} -o {}'
nodejs_cmd = 'node {}'


def emcc_generate(c_path: str, wasm_path: str, js_path: str):
    assert wasm_path.endswith('.wasm')
    assert js_path.endswith('.js')

    c_path = os.path.abspath(c_path)
    wasm_path = os.path.abspath(wasm_path)
    js_path = os.path.abspath(js_path)

    subprocess.getstatusoutput('rm {}'.format(wasm_path))
    subprocess.getstatusoutput('rm {}'.format(js_path))
    stdout, status = cmd_modified(emcc_cmd.format(c_path, wasm_path, js_path))
    if status != 0:
        exit(-1)

    # status, output = cmd(nodejs_cmd.format(js_path))
    # assert status == 0
    output, status = run_single_prog(nodejs_cmd.format(js_path))
    if status != 0:
        exit(-1)

    return output.strip()


def udf_checking(c_path: str):
    """ Checking for undefined behaviors
        1. Assigned value is garbage or undefined [clang-analyzer-core.uninitialized.Assign]
        2. The right operand of '>>' is a garbage value [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. The result of the left shift is undefined because the right operand is negative [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. warning: more '%' conversions than data arguments [clang-diagnostic-format-insufficient-args]
    """
    status, output = cmd("clang-tidy-12 {} -- -I/home/tester/Documents/csmith/runtime".format(c_path))
    if 'Assigned value is garbage or undefined' in output:
        exit(-1)
    elif 'garbage value' in output:
        exit(-1)
    # elif 'is undefined' in output:
    #     exit(-1)
    elif "more '%' conversions than data arguments" in output:
        exit(-1)


def main(tmp_c: str):
    tmp_c = os.path.abspath(tmp_c)
    # TODO: what if do not keep <func_1>
    # with open(tmp_c, 'r') as f:
    #     if 'func_1' not in f.read():
    #         exit(-1)  # keep func_1
    udf_checking(c_path=tmp_c)

    tmp_out = tmp_c[:tmp_c.rfind('.')] + '.out'
    tmp_wasm = tmp_c[:tmp_c.rfind('.')] + '.wasm'
    tmp_js = tmp_c[:tmp_c.rfind('.')] + '.js'

    status, output = cmd(csmith_compile_cmd.format(tmp_c, tmp_out))
    if status != 0:
        exit(-1)

    output, status = run_single_prog('timeout 3 ' + tmp_out)
    if status != 0:
        exit(-1)

    out2 = emcc_generate(tmp_c, tmp_wasm, tmp_js)

    if output.strip() != out2.strip():
        exit(0)
    else:
        exit(-1)


if __name__ == '__main__':
    # main('tmp.c')
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        exit(-1)
