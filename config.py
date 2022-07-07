import os

csmith_runtime = '/home/lifter/Documents/csmith/runtime'
clang_ir_cmd = "clang -c -w -g -O0 -emit-llvm -S {} -o {}"
clang_ir_cmd2 = "clang -c -w -g -O0 -emit-llvm -S -I/home/lifter/Documents/csmith/runtime {} -o {}"
clang_dwarf_cmd2 = "clang -w -g -O0 -I/home/lifter/Documents/csmith/runtime {} -o {}"

dwarfdump_cmd = "llvm-dwarfdump-12 {} > {}"

emsdk_path = '/home/lifter/Documents/WebAssembly/emsdk'
emscripten_path = '/home/lifter/Documents/WebAssembly/emsdk/upstream/emscripten'
node_path = '/home/lifter/Documents/WebAssembly/emsdk/node/14.18.2_64bit/bin'

emcc_cmd = 'emcc -w -O3 -I' + csmith_runtime + ' {} -o {} -o {}'
emcc_dwarf_cmd = 'emcc -w -g -O3 -I' + csmith_runtime + ' {} -o {} -o {}'
nodejs_cmd = 'node {}'

wasm2wat_cmd = "/home/lifter/Documents/WebAssembly/wabt/build/wasm2wat {} -o {}"
wat2wasm_cmd = "/home/lifter/Documents/WebAssembly/wabt/build/wat2wasm {} -o {}"

pin_home = "/home/lifter/Downloads/pin-3.21-98484-ge7cd811fd-gcc-linux/"
pintool_dir = os.path.join(pin_home, "source/tools/MyPinTool/")
compile_pintool_cmd = "make obj-intel64/{}.so TARGET=intel64"

pin_trace_cmd = pin_home + "pin -t " + \
                pintool_dir + "obj-intel64/tracer.so" \
                              " -o {} -global_addr_file {} -func_addr_file {} -ret_func_addr_file {} -param_file {} -- {}"
