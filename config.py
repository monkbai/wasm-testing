import os

csmith_path = '/home/tester/Documents/csmith/src/csmith'
csmith_cmd = csmith_path + " --max-funcs 5 --no-safe-math --max-expr-complexity 3 > {}"
csmith_runtime = '/home/tester/Documents/csmith/runtime'
csmith_compile_cmd = 'gcc -O -g -w {} -I' + csmith_runtime + ' -o {}'

creduce_path = '/home/tester/Documents/creduce/build/creduce/creduce'

clang_ir_cmd = "clang-12 -c -w -g -O0 -emit-llvm -S {} -o {}"
clang_ir_cmd2 = "clang-12 -c -w -g -O0 -emit-llvm -S -I/home/tester/Documents/csmith/runtime {} -o {}"
clang_dwarf_cmd2 = "clang-12 -w -g -O0 -I/home/tester/Documents/csmith/runtime {} -o {}"
clang_dwarf_opt_cmd = "clang-12 -w -g {} -I/home/tester/Documents/csmith/runtime {} -o {}"
# clang_dwarf_opt_cmd = "gcc -no-pie -w -g {} -I/home/tester/Documents/csmith/runtime {} -o {}"  # -no-pie is important
# clang_dwarf_opt_cmd = "gcc -no-pie -mno-sse -fcf-protection=none -w -g {} -I/home/tester/Documents/csmith/runtime {} -o {}"  # -no-pie is important
# gcc version: 11.2.0

clang_tidy_cmd = "clang-tidy-12 {} -- -I" + csmith_runtime

dwarfdump_cmd = "llvm-dwarfdump-12 {} > {}"

emsdk_path = '/home/tester/Documents/WebAssembly/emsdk'
emscripten_path = '/home/tester/Documents/WebAssembly/emsdk/upstream/emscripten'
node_path = '/home/tester/Documents/WebAssembly/emsdk/node/14.18.2_64bit/bin'

emcc_cmd = 'emcc -w -g -O2 -I' + csmith_runtime + ' {} -o {} -o {}'
emcc_dwarf_cmd = 'emcc -w -g -O2 -I' + csmith_runtime + ' {} -o {} -o {}'
emcc_dwarf_opt_cmd = 'emcc -w -g {} -I' + csmith_runtime + ' {} -o {} -o {}'
nodejs_cmd = 'node {} > {}'

wasm2wat_cmd = "/home/tester/Documents/WebAssembly/wabt/build/wasm2wat {} -o {}"
wat2wasm_cmd = "/home/tester/Documents/WebAssembly/wabt/build/wat2wasm {} -o {}"

pin_home = "/home/tester/Downloads/pin-3.21-98484-ge7cd811fd-gcc-linux/"
pintool_dir = os.path.join(pin_home, "source/tools/MyPinTool/")
compile_pintool_cmd = "make obj-intel64/{}.so TARGET=intel64"

pin_trace_cmd = pin_home + "pin -t " + \
                pintool_dir + "obj-intel64/tracer.so" \
                              " -o {} -global_addr_file {} -func_addr_file {} -ret_func_addr_file {} -param_file {} -- {}"
