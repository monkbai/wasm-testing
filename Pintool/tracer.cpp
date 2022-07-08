#include <stdio.h>
#include <unordered_map>
#include <iostream>
#include <fstream>
#include <list>
#include "pin.H"

static std::unordered_map<ADDRINT, std::string> str_of_ins_at;

FILE * trace;

int after_call_flag = 0; // is current instruction after a call
ADDRINT callee_addr = 0; // callee addr of previous call instruction

// just want hash table
static std::unordered_map<uint64_t, uint64_t> global_addr;
static std::unordered_map<uint64_t, uint64_t> func_addr;
static std::unordered_map<uint64_t, uint64_t> ret_func_addr;

static std::unordered_map<uint64_t, std::list<uint32_t>> func2param; // func_addr -> [size_of_arg1, size_of_arg2, ...]
/* ===================================================================== */
// Command line switches
/* ===================================================================== */
KNOB<std::string> KnobOutputFile(KNOB_MODE_WRITEONCE,  "pintool",
    "o", "", "specify file name for MyPinTool output");

KNOB<std::string>   KnobAddrsFile(KNOB_MODE_WRITEONCE,  "pintool",
    "addrs_file", "0x422860", "file path");
// ==========
KNOB<std::string>   KnobGlobalsAddrFile(KNOB_MODE_WRITEONCE,  "pintool",
    "global_addr_file", "", "");
KNOB<std::string>   KnobFuncAddrFile(KNOB_MODE_WRITEONCE,  "pintool",
    "func_addr_file", "", "");
KNOB<std::string>   KnobRetFuncAddrFile(KNOB_MODE_WRITEONCE,  "pintool",
    "ret_func_addr_file", "", "");
KNOB<std::string>   KnobParamFile(KNOB_MODE_WRITEONCE,  "pintool",
    "param_file", "", "");

/* ===================================================================== */
// Utilities
/* ===================================================================== */

VOID RecordInst(VOID * ip)
{
    std::string ins_str = str_of_ins_at[(ADDRINT)ip];
    // fprintf(trace,">%p:\t%s\n", ip, ins_str.c_str());  // for debug
    fprintf(trace,">%p\n", ip);

    //std::string ins_str = str_of_ins_at[(ADDRINT)ip];
    //fprintf(trace,"%p:\t%s\n", ip, ins_str.c_str());
    //fprintf(trace,"N:\t%p:\t%d\n", (void *)0xDEADBEEF, 7); // not real memory op
    //fprintf(trace,"N:\n");
}

// Print a memory read record
VOID RecordMemRead(VOID * ip, VOID * mem_addr, USIZE mem_size)
{
    fprintf(trace,"%p\n", ip);
    //std::string ins_str = str_of_ins_at[(ADDRINT)ip];
    //fprintf(trace,"%p:\t%s\n", ip, ins_str.c_str());
    //fprintf(trace,"R:\t%p:\t%lu\n", mem_addr, mem_size);
    //fprintf(trace,"%p: R %p\n", ip, addr);
}

// Print a memory write record
VOID RecordMemWrite(VOID * ip, VOID * mem_addr, USIZE mem_size)
{
    if (global_addr.find((uint64_t)mem_addr) == global_addr.end()){
        // only instrument target global writes
        return;
    }
    // std::string ins_str = str_of_ins_at[(ADDRINT)ip];
    // fprintf(trace,">%p:\t%s\n", ip, ins_str.c_str());  // for debug

    fprintf(trace,"W: %p: %lu\n", mem_addr, mem_size);
    if (mem_size == 1){
        fprintf(trace,"V: 0x%x\n", (unsigned int)*(uint8_t *)(mem_addr));
    }
    else if (mem_size == 2){
        fprintf(trace,"V: 0x%x\n", (unsigned int)*(uint16_t *)(mem_addr));
    }
    else if (mem_size == 4){
        fprintf(trace,"V: 0x%x\n", (unsigned int)*(uint32_t *)(mem_addr));
    }
    else if (mem_size == 8){
        fprintf(trace,"V: 0x%llx\n", *(long long unsigned int *)(mem_addr));
    }
    else{
        fprintf(trace,"V: unimplemented mem_size: %ld\n", mem_size);
    }
}

VOID AfterCall(VOID * ip, ADDRINT rax){
    // TODO: what if the return value is a pointer
    if (ret_func_addr.find(callee_addr) != ret_func_addr.end()){  // only print return value of the target functions
        fprintf(trace,">%p R: %p\n", (VOID *)callee_addr, (void *)rax);
    }
}

VOID RecordArgs(VOID * ip, ADDRINT rdi, ADDRINT rsi, ADDRINT rdx, ADDRINT rcx, ADDRINT r8, ADDRINT r9){
    if (func2param.find((uint64_t)ip) == func2param.end()){
        return; // no argument
    }
    // TODO: what if the argument is a pointer
    // TODO: what if #argument > 6
    ADDRINT args[6] = {rdi, rsi, rdx, rcx, r8, r9};
    uint32_t idx = 0;
    for (std::list<uint32_t>::iterator it = func2param[(uint64_t)ip].begin(); it != func2param[(uint64_t)ip].end(); ++it) {
        if (*it == 1){
            fprintf(trace, "P: 0x%x\n", (unsigned int)(uint8_t)(args[idx]));
        }
        else if (*it == 2){
            fprintf(trace, "P: 0x%x\n", (unsigned int)(uint16_t)(args[idx]));
        }
        else if (*it == 4){
            fprintf(trace, "P: 0x%x\n", (unsigned int)(uint32_t)(args[idx]));
        }
        else if (*it == 8){
            fprintf(trace, "P: 0x%llx\n", (long long unsigned int)(args[idx]));
        }
        else{
            fprintf(trace, "P: unimplemented arg_size: %d\n", *it);
        }
        idx += 1;
    }
}

// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID *v)
{
    ADDRINT ins_addr = INS_Address(ins);

    str_of_ins_at[INS_Address(ins)] = INS_Disassemble(ins);
    std::string ins_asm = INS_Disassemble(ins);

    UINT32 memOperands = INS_MemoryOperandCount(ins);

    if (func_addr.find(ins_addr) != func_addr.end()){
        // Step 1:
        // instrument function start, print argument values
        INS_InsertPredicatedCall(
            ins, IPOINT_BEFORE, (AFUNPTR)RecordInst,
            IARG_INST_PTR,
            IARG_END);
        // TODO: print the arguemnts according to the param_file
        INS_InsertPredicatedCall(
            ins, IPOINT_BEFORE, (AFUNPTR)RecordArgs,
            IARG_INST_PTR,
            IARG_REG_VALUE, LEVEL_BASE::REG_RDI,
            IARG_REG_VALUE, LEVEL_BASE::REG_RSI,
            IARG_REG_VALUE, LEVEL_BASE::REG_RDX,
            IARG_REG_VALUE, LEVEL_BASE::REG_RCX,
            IARG_REG_VALUE, LEVEL_BASE::REG_R8,
            IARG_REG_VALUE, LEVEL_BASE::REG_R9,
            IARG_END);
    }

    /*
    if (!(ins_asm.find("xmm")!=ins_asm.npos || ins_asm.find("ymm")!=ins_asm.npos)){
        return;
    }
    */

    if (memOperands != 0){
        // Step 2:
        // Iterate over each memory operand of the instruction.
        // instrument global writes
        for (UINT32 memOp = 0; memOp < memOperands; memOp++)
        {
            if (INS_MemoryOperandIsRead(ins, memOp))
            {
            }

            if (INS_MemoryOperandIsWritten(ins, memOp) && INS_IsValidForIpointAfter(ins))
            {
                USIZE mem_size = INS_MemoryOperandSize(ins, memOp);
                INS_InsertPredicatedCall(
                    ins, IPOINT_AFTER, (AFUNPTR)RecordMemWrite,
                    IARG_INST_PTR,
                    IARG_MEMORYOP_EA, memOp,
                    IARG_UINT64, mem_size,
                    IARG_END);
            }
        }
    }

    // Step 3:
    // instrument the succeeded instruction after call
    // retrieve the return value (RAX)
    if (after_call_flag != 0){
        INS_InsertPredicatedCall(
        ins, IPOINT_BEFORE, (AFUNPTR)AfterCall,
        IARG_INST_PTR,
        IARG_REG_VALUE, LEVEL_BASE::REG_RAX,
        IARG_END);
    }

    if (INS_IsCall(ins) && INS_IsDirectControlFlow(ins)){
        callee_addr = INS_DirectControlFlowTargetAddress(ins);
        after_call_flag = 1;
    }
    else{
        after_call_flag = 0;
    }
}

VOID Fini(INT32 code, VOID *v)
{
    fprintf(trace, "#eof\n");
    fclose(trace);
}

/* ===================================================================== */
/* Utilities                                                             */
/* ===================================================================== */
   
INT32 Usage()
{
    PIN_ERROR( "This Pintool prints a trace of memory addresses\n" 
              + KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}

int ReadGlobalAddr(){
    std::string globalAddrFile = KnobGlobalsAddrFile.Value();
    FILE *fp = fopen(globalAddrFile.c_str(),"r");

    while(!feof(fp)){
        uint64_t current_addr;
        fscanf(fp, "%lx\n", &current_addr);
        global_addr[current_addr] = current_addr;
    }
    return 0;
}

int ReadFuncAddr(){
    std::string funcAddrFile = KnobFuncAddrFile.Value();
    FILE *fp = fopen(funcAddrFile.c_str(),"r");

    while(!feof(fp)){
        uint64_t current_addr;
        fscanf(fp, "%lx\n", &current_addr);
        func_addr[current_addr] = current_addr;
    }
    return 0;
}

int ReadRetFuncAddr(){
    std::string funcAddrFile = KnobRetFuncAddrFile.Value();
    FILE *fp = fopen(funcAddrFile.c_str(),"r");

    while(!feof(fp)){
        uint64_t current_addr;
        fscanf(fp, "%lx\n", &current_addr);
        ret_func_addr[current_addr] = current_addr;
    }
    return 0;
}

int ReadFuncParamAddr(){
    std::string funcParamFile = KnobParamFile.Value();
    FILE *fp = fopen(funcParamFile.c_str(),"r");

    while(!feof(fp)){
        uint64_t current_addr;
        uint32_t arg_count = 0;
        uint32_t arg_size = 0;
        std::list<uint32_t> args;
        fscanf(fp, "%lx\n", &current_addr);
        func2param[current_addr] = args;
        fscanf(fp, "%d\n", &arg_count);
        for (unsigned int i = 0; i < arg_count; i++){
            fscanf(fp, "%d\n", &arg_size);
            func2param[current_addr].push_back(arg_size);
        }
        // debug
        /*
        printf("%lx ", current_addr);
        for (std::list<uint32_t>::iterator it = func2param[current_addr].begin(); it != func2param[current_addr].end(); ++it) {
            printf("%d ", *it);
        }
        printf("\n");
        */
    }
    return 0;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char *argv[])
{
    if (PIN_Init(argc, argv)) return Usage();

    std::string fileName = KnobOutputFile.Value();
    trace = fopen(fileName.c_str(), "w");

    ReadGlobalAddr();
    ReadFuncAddr();
    ReadRetFuncAddr();
    ReadFuncParamAddr();

    // debug
    //printf("output: %s, start: %p, end: %p\n", fileName.c_str(), (void *)start_addr, (void *)end_addr);
    
    INS_AddInstrumentFunction(Instruction, 0);
    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();
    
    return 0;
}
