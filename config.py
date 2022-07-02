csmith_runtime = '/home/lifter/Documents/csmith/runtime'
clang_dwarf_cmd = "clang -c -w -g -emit-llvm -S {} -o {}"
clang_dwarf_cmd2 = "clang -c -w -g -emit-llvm -S -I/home/lifter/Documents/csmith/runtime {} -o {}"

dwarfdump_cmd = "llvm-dwarfdump {} > {}"

emsdk_path = '/home/lifter/Documents/WebAssembly/emsdk'
emscripten_path = '/home/lifter/Documents/WebAssembly/emsdk/upstream/emscripten'
node_path = '/home/lifter/Documents/WebAssembly/emsdk/node/14.18.2_64bit/bin'

emcc_cmd = 'emcc -w -O3 -I' + csmith_runtime + ' {} -o {} -o {}'
nodejs_cmd = 'node {}'
