import os
import sys
import json
import subprocess
from threading import Timer
# from subprocess import Popen, PIPE, getstatusoutput

import config
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


def cmd_emsdk(commandline):
    with cd(project_dir):
        my_env = os.environ.copy()
        my_env["PATH"] = config.emsdk_path + os.pathsep + my_env["PATH"]
        my_env["PATH"] = config.emscripten_path + os.pathsep + my_env["PATH"]
        my_env["PATH"] = config.node_path + os.pathsep + my_env["PATH"]
        my_env["EMSDK"] = config.emsdk_path
        my_env["EM_CONFIG"] = config.emsdk_path + '/.emscripten'
        my_env["EMSDK_NODE"] = config.node_path + '/node'

        proc = subprocess.Popen(commandline, env=my_env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return stdout, stderr


project_dir = './'
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


def csmith_generate(c_path: str):
    c_path = os.path.abspath(c_path)
    elf_path = c_path[:c_path.rfind('.')] + '.out'

    while True:
        status, output = cmd(config.csmith_cmd.format(c_path))
        assert status == 0

        # avoid huge test case, which is hard to locate bug statement
        file_size = os.path.getsize(c_path)
        if file_size >= 1024 * 10:  # TODO: size limit 10KB
            continue

        status, output = cmd(config.csmith_compile_cmd.format(c_path, elf_path))
        if status != 0:
            continue  # if cannot be compiled, re-generate a new source code

        output, status = run_single_prog('timeout 3 ' + elf_path)
        if status != 0:
            continue

        break
    status, output = cmd("rm {}".format(elf_path))


def wasm2wat(wasm_path: str):
    global project_dir

    wasm_path = os.path.abspath(wasm_path)
    dir_path = os.path.dirname(wasm_path)
    assert wasm_path.endswith('.wasm')
    wat_path = wasm_path[:-5] + '.wat'

    tmp_dir = project_dir
    project_dir = dir_path

    status, output = cmd(config.wasm2wat_cmd.format(wasm_path, wat_path))

    project_dir = tmp_dir

    return wat_path


def udf_checking(c_path: str):
    """ Checking for undefined behaviors
        1. Assigned value is garbage or undefined [clang-analyzer-core.uninitialized.Assign]
        2. The right operand of '>>' is a garbage value [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. The result of the left shift is undefined because the right operand is negative [clang-analyzer-core.UndefinedBinaryOperatorResult]
        3. warning: more '%' conversions than data arguments [clang-diagnostic-format-insufficient-args]
    """
    status, output = cmd(config.clang_tidy_cmd.format(c_path))
    if 'Assigned value is garbage or undefined' in output:
        return False
    elif 'garbage value' in output:
        return False
    elif 'is undefined' in output:
        return False
    elif "more '%' conversions than data arguments" in output:
        return False

    # if 'warning' in output:
    #     print('check this')

    return True


def compile_checking(c_path: str, opt_level='-O0'):

    elf_path, dwarf_path, compile_output = profile.clang_dwarf_withoutput(c_path, opt_level=opt_level)

    if "tentative array" in compile_output:
        return False
    elif "past the end of the array" in compile_output:
        return False
    elif "incompatible pointer to integer conversion" in compile_output:
        return False
    return True


def crash_checking(c_path: str, opt_level='-O0'):
    global timeout_sec
    timeout_tmp = timeout_sec
    timeout_sec = 1
    elf_path, dwarf_path = profile.clang_dwarf(c_path, opt_level=opt_level)

    output1, status = run_single_prog('timeout 1 ' + elf_path)
    timeout_sec = timeout_tmp
    if status != 0:
        return False
    elif 'Warning: Not Safe!' in output1:
        return False
    return True


def obj_to_json(dict_obj, output_path: str):
    j = json.dumps(dict_obj, sort_keys=True, indent=4)
    with open(output_path, 'w') as f:
        f.write(j)


def json_to_obj(json_path: str):
    if not os.path.exists(json_path):
        return list()
    with open(json_path, 'r') as f:
        j_txt = f.read()
        list_obj = json.loads(s=j_txt)
        return list_obj
