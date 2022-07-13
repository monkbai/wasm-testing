#!/usr/bin/python3

import re
import os

import utils


file_name_dict = dict()
debug_line_dict = dict()


def dump_elf(elf_path: str):
    global  file_name_dict, debug_line_dict

    elf_path = os.path.abspath(elf_path)
    status, output = utils.cmd("llvm-dwarfdump-12 -debug-line {}".format(elf_path))
    secs = output.split('\n\n')

    it = re.finditer(r'file_names\[\s+(\d+)]:\s*\n\s*name:\s"(.+)"', secs[1])
    for mat in it:
        file_id = int(mat.group(1))
        file_name = mat.group(2)
        file_name_dict[file_id] = file_name

    it = re.finditer(r'(0x\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*(\w*)\n', secs[2])
    # Address            Line   Column File   ISA Discriminator Flags
    # ------------------ ------ ------ ------ --- ------------- -------------
    # 0x0000000000401150    105      0      5   0             0  is_stmt
    for mat in it:
        asm_addr = int(mat.group(1), 16)
        line_num = int(mat.group(2))
        col_num = int(mat.group(3))
        file_num = int(mat.group(4))
        isa = int(mat.group(5))
        dis = int(mat.group(6))
        flags = mat.group(7)
        debug_line_dict[asm_addr] = [line_num, col_num, file_name_dict[file_num], flags]


def lookup(addr: int):
    return debug_line_dict[addr]


if __name__ == '__main__':
    dump_elf("/home/tester/Documents/WebAssembly/wasm-compiler-testing/debug_cases/test1008.out")
    print(lookup(int('0x4017a3', 16)))
