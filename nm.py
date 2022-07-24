import os
import re
import sys

import utils
import config


def get_nm_list(elf_path: str, globs_list: list) -> list:
    status, output = utils.cmd("nm -n {}".format(elf_path))
    lines = output.split('\n')
    nm_list = []
    for l in lines:
        if l.startswith('00'):
            if mat := re.match(r"00(\w+)\s\w\s(.*)", l):
                addr = int(mat.group(1), 16)
                sym_name = mat.group(2)
                nm_list.append((addr, sym_name))

    # filter with clang globs (dwarf debug info)
    filted_nm_list = []
    for obj in globs_list:
        obj = obj[1]
        obj_name = obj["DW_AT_name"].strip('()').strip('"')
        if '[' not in obj["DW_AT_type"]:
            # single var
            for addr, sym_name in nm_list:
                if sym_name == obj_name:
                    filted_nm_list.append((addr, sym_name))
                    break
        else:
            for addr, sym_name in nm_list:
                if mat := re.match(obj_name+r"(\.\d+)+", sym_name):
                    idx_list = sym_name.split('.')[1:]
                    sym_name = obj_name
                    for idx in idx_list:
                        sym_name += '[{}]'.format(idx)
                    filted_nm_list.append((addr, sym_name))

    return filted_nm_list


if __name__ == '__main__':
    pass
