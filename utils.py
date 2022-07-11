import os
import sys
import subprocess
from threading import Timer
# from subprocess import Popen, PIPE, getstatusoutput

import config


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
        if file_size >= 1024 * 8:  # TODO: size limit 8KB
            continue

        status, output = cmd(config.csmith_compile_cmd.format(c_path, elf_path))
        if status != 0:
            continue  # if cannot be compiled, re-generate a new source code

        output, status = run_single_prog('timeout 3 ' + elf_path)
        if status != 0:
            continue

        break
    status, output = cmd("rm {}".format(elf_path))
