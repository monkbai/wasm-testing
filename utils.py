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

