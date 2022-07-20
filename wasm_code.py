wasm_type_def = """
  (type (;{};) (func (param i32 i32) ))
  (type (;{};) (func (param i32)))
  (type (;{};) (func (param i64)))
  (type (;{};) (func (param i32) (result i32)))
  (type (;{};) (func (param i32 i64) ))
  (type (;{};) (func (param i32 i32 i32)))
  (type (;{};) (func (param i32 i32) (result i32)))
  (type (;{};) (func (param i32 i32 i32) (result i32)))
"""


wasm_vfiprintf = """  (func $vfiprintf (type {}) (param i32 i32 i32) (result i32)
    local.get 0
    local.get 1
    local.get 2
    i32.const 0
    i32.const 0
    call $__vfprintf_internal)
"""


wasm_iprintf = """(func $iprintf (type {}) (param i32 i32) (result i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
    i32.sub
    local.tee 2
    global.set $__stack_pointer
    local.get 2
    local.get 1
    i32.store offset=12
    i32.const {}
    local.get 0
    local.get 1
    call $vfiprintf
    local.set 1
    local.get 2
    i32.const 64
    i32.add
    global.set $__stack_pointer
    local.get 1)
"""

wasm_myprint_i32w = """
  (func $myprint_i32w (type {}) (param i32 i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
    i32.sub
    local.tee 2
    global.set $__stack_pointer  ;; lift stack pointer
    
    local.get 2
    local.get 0
    i32.store ;; store address in stack mem
    
    i32.const {}
    local.get 2
    call $iprintf  ;; print the address
    drop
    
    local.get 2
    local.get 1
    i32.store ;; store size in stack mem
    
    i32.const {}
    local.get 2
    call $iprintf  ;; print the write size
    drop
    
    local.get 2
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32v = """
  (func $myprint_i32v (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
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
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32p = """
  (func $myprint_i32p (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
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
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32id = """
  (func $myprint_i32id (type {}) (param i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer

    local.get 1
    local.get 0
    i32.store ;; store address in stack mem

    i32.const {}
    local.get 1
    call $iprintf  ;; print the argument
    drop

    local.get 1
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i64p = """
  (func $myprint_i64p (type {}) (param i64)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
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
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i64v = """
  (func $myprint_i64v (type {}) (param i64)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
    i32.sub
    local.tee 1
    global.set $__stack_pointer  ;; lift stack pointer

    local.get 1
    local.get 0
    i64.store ;; store address in stack mem

    i32.const {}
    local.get 1
    call $iprintf  ;; print the value
    drop

    local.get 1
    i32.const 64  ;; restore stack pointer
    i32.add
    global.set $__stack_pointer)
"""

wasm_myprint_i32r = """
  (func $myprint_i32r (type {}) (param i32) (result i32)
    (local i32)
    global.get $__stack_pointer
    i32.const 64
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
    i32.const 64  ;; restore stack pointer
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
    i32.const 4
    call $myprint_i32w  ;; print the address
    
    local.get 1
    call $myprint_i32v  ;; print the value
    
    local.get 0
    local.get 1
    i32.store  ;; original store operation
    )
"""

wasm_instrument_i32store_off = """
  (func $instrument_i32store_off (type {}) (param i32 i32 i32)
    (local i32 i32)
    
    local.get 0
    local.get 2
    i32.add
    local.tee 3
    i32.const 4
    call $myprint_i32w  ;; print the address
    
    local.get 1
    call $myprint_i32v  ;; print the value
    
    local.get 3
    local.get 1
    i32.store  ;; original store operation
    )
"""

wasm_instrument_i64store = """
(func $instrument_i64store (type {}) (param i32 i64)
    local.get 0
    i32.const 8
    call $myprint_i32w  ;; print the address
    
    local.get 1
    call $myprint_i64v  ;; print the value
    
    local.get 0
    local.get 1
    i64.store  ;; original store operation
    )
"""

wasm_data_str = """
  (data $.str.w32 (i32.const {}) "W: 0x%lx: \\00")
  (data $.str.w32s (i32.const {}) "%d\\0a\\00")
  (data $.str.v32 (i32.const {}) "V: 0x%lx\\0a\\00")
  (data $.str.p32 (i32.const {}) "P: 0x%lx\\0a\\00")
  (data $.str.p64 (i32.const {}) "P: 0x%llx\\0a\\00")
  (data $.str.v64 (i32.const {}) "V: 0x%llx\\0a\\00")
  (data $.str.r32 (i32.const {}) "R: 0x%lx\\0a\\00")
  (data $.str.id32 (i32.const {}) "ID: %d\\0a\\00")"""

wasm_func_names_str = """
  (data $.str.{} (i32.const {}) "${}\\0a\\00")"""

wasm_func_return_str = """
  (data $.str.r.{} (i32.const {}) "${} \\00")"""

