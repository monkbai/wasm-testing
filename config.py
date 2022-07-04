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
