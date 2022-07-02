#!/usr/bin/env python3

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


csmith_path = '/home/lifter/Documents/csmith/src/csmith'
csmith_cmd = csmith_path + " --max-funcs 1 --max-expr-complexity 5 > {}"
csmith_runtime = '/home/lifter/Documents/csmith/runtime'
csmith_compile_cmd = 'gcc -w {} -I' + csmith_runtime + ' -o {}'

emcc_init = 'source /home/lifter/Documents/WebAssembly/emsdk/emsdk_env.sh'
emcc_cmd = 'emcc -w -I' + csmith_runtime + ' {} -o {} -o {}'
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


def main():
    tmp_out = './tmp.out'
    tmp_c = './tmp.c'
    tmp_wasm = './tmp.wasm'
    tmp_js = './tmp.js'

    status, output = cmd(csmith_compile_cmd.format(tmp_c, tmp_out))
    if status != 0:
        exit(-1)

    output, status = run_single_prog('timeout 3 ' + tmp_out)
    if status != 0:
        exit(-1)

    out2 = emcc_generate(tmp_c, tmp_wasm, tmp_js)

    if output != out2 and 'checksum' in out2:
        exit(0)
    else:
        exit(-1)


if __name__ == '__main__':
    main()
