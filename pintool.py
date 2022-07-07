import os
import sys

import utils
import config
import profile

tools_list = ["tracer", ]


def compile_pin_tool():
    for tool_name in tools_list:
        path1 = os.path.join('./Pintool', tool_name + '.cpp')
        path2 = os.path.join(config.pintool_dir, tool_name + '.cpp')
        status, output = utils.cmd("cp {} {}".format(path1, path2))

    # utils.project_dir
    project_dir_backup = utils.project_dir
    utils.project_dir = config.pintool_dir
    for tool_name in tools_list:
        status, output = utils.cmd(config.compile_pintool_cmd.format(tool_name))
        if status != 0:
            print(output)
    utils.project_dir = project_dir_backup


# ===============


def get_raw_trace(elf_path: str, glob_addr_file: str, func_addr_file: str, ret_func_addr_file: str, param_file: str, trace_path: str):
    project_dir_backup = utils.project_dir
    utils.project_dir = config.pintool_dir
    # ------- set project_dir before instrumentation

    status, output = utils.cmd(config.pin_trace_cmd.format(trace_path, glob_addr_file, func_addr_file,
                                                           ret_func_addr_file, param_file, elf_path))

    # status, output = utils.cmd("rm {}".format(glob_addr_file))
    # status, output = utils.cmd("rm {}".format(func_addr_file))
    # status, output = utils.cmd("rm {}".format(param_file))

    # ------- end reset project_dir
    utils.project_dir = project_dir_backup


if __name__ == '__main__':
    compile_pin_tool()

