wasm_type_def = """
  (type (;{};) (func (param i32 i32) ))
  (type (;{};) (func (param i32)))
  (type (;{};) (func (param i64)))
  (type (;{};) (func (param i32) (result i32)))
"""

wasm_myprint_i32w = """
  (func $myprint_i32w (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 16
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer
    
    local.get 1
    local.get 0
    i32.store ;; store address in stack mem
    
    i32.const {}
    local.get 1
    call $iprintf  ;; print the address
    drop
    
    local.get 1
    i32.const 16  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32v = """
  (func $myprint_i32v (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 16
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer
    
    local.get 1
    local.get 0
    i32.store ;; store address in stack mem
    
    i32.const {}
    local.get 1
    call $iprintf  ;; print the address
    drop
    
    local.get 1
    i32.const 16  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32p = """
  (func $myprint_i32p (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 16
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer

    local.get 1
    local.get 0
    i32.store ;; store address in stack mem

    i32.const {}
    local.get 1
    call $iprintf  ;; print the address
    drop

    local.get 1
    i32.const 16  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i64p = """
  (func $myprint_i64p (type {}) (param i64)
    (local i32)
    global.get $__stack_pointer
    i32.const 16
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer
    
    local.get 1
    local.get 0
    i64.store ;; store address in stack mem
    
    i32.const {}
    local.get 1
    call $iprintf  ;; print the address
    drop
    
    local.get 1
    i32.const 16  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32r = """
  (func $myprint_i32r (type {}) (param i32) (result i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 16
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer

    local.get 1
    local.get 0
    i32.store ;; store address in stack mem

    i32.const {}
    local.get 1
    call $iprintf  ;; print the address
    drop

    local.get 1
    i32.const 16  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer
    
    local.get 0)
"""

wasm_myprint_call = """
  (func $myprint_call (type {}) (param i32)
    local.get 0
    i32.const 0
    call $iprintf  ;; print the callee name
    drop
    )
"""

wasm_instrument_i32store = """
  (func $instrument_i32store (type {}) (param i32 i32)
    (local i32 i32)
    
    local.get 0
    call $myprint_i32w  ;; print the address
    
    local.get 1
    call $myprint_i32v  ;; print the value
    
    local.get 0
    local.get 1
    i32.store  ;; original store operation
    )
"""

wasm_data_str = """
  (data $.str.w32 (i32.const {}) "W: 0x%lx\\0a\\00")
  (data $.str.v32 (i32.const {}) "V: 0x%lx\\0a\\00")
  (data $.str.p32 (i32.const {}) "P: 0x%lx\\0a\\00")
  (data $.str.p64 (i32.const {}) "P: 0x%llx\\0a\\00")
  (data $.str.r32 (i32.const {}) "R: 0x%lx\\0a\\00")"""

wasm_func_names_str = """
  (data $.str.{} (i32.const {}) "${}\\0a\\00")"""

wasm_func_return_str = """
  (data $.str.r.{} (i32.const {}) "${} \\00")"""

