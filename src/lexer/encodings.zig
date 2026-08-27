const std = @import("std");
const schema = @import("schema.zig");
const parser = @import("parser.zig");

// https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf
// Table 4-12 page 164

pub const instruction_encodings = encodings: {
    @setEvalBranchQuota(1_000_000);

    break :encodings [_]schema.InstructionSchema{
        // Data transfer
        parser.instructionSchema("mov", "100010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("mov", "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("mov", "1011 w reg, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("mov", "1010000 w, addr_lo, addr_hi", .{}),
        parser.instructionSchema("mov", "1010001 w, addr_lo, addr_hi", .{}),
        parser.instructionSchema("mov", "10001110, mod 0 sr rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("mov", "10001100, mod 0 sr rm, disp_lo, disp_hi", .{}),

        parser.instructionSchema("push", "11111111, mod 110 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("push", "01010 reg", .{}),
        parser.instructionSchema("push", "000 sr 110", .{}),

        parser.instructionSchema("pop", "10001111, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("pop", "01011 reg", .{}),
        parser.instructionSchema("pop", "000 sr 111", .{}),

        parser.instructionSchema("xchg", "1000011 w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("xchg", "10010 reg", .{}),

        parser.instructionSchema("in", "1110010 w, data_8", .{}),
        parser.instructionSchema("in", "1110110 w", .{}),
        parser.instructionSchema("out", "1110011 w, data_8", .{}),
        parser.instructionSchema("out", "1110111 w", .{}),

        parser.instructionSchema("xlat", "11010111", .{}),
        parser.instructionSchema("lea", "10001101, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("lds", "11000101, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("les", "11000100, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("lahf", "10011111", .{}),
        parser.instructionSchema("sahf", "10011110", .{}),
        parser.instructionSchema("pushf", "10011100", .{}),
        parser.instructionSchema("popf", "10011101", .{}),

        // Arithmetic
        parser.instructionSchema("add", "000000 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("add", "100000 s w, mod 000 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instructionSchema("add", "0000010 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("adc", "000100 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("adc", "100000 s w, mod 010 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instructionSchema("adc", "0001010 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("inc", "1111111 w, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("inc", "01000 reg", .{}),
        parser.instructionSchema("aaa", "00110111", .{}),
        parser.instructionSchema("daa", "00100111", .{}),

        parser.instructionSchema("sub", "001010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("sub", "100000 s w, mod 101 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instructionSchema("sub", "0010110 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("sbb", "000110 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("sbb", "100000 s w, mod 011 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instructionSchema("sbb", "0001110 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("dec", "1111111 w, mod 001 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("dec", "01001 reg", .{}),
        parser.instructionSchema("neg", "1111011 w, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instructionSchema("cmp", "001110 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("cmp", "100000 s w, mod 111 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instructionSchema("cmp", "0011110 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("aas", "00111111", .{}),
        parser.instructionSchema("das", "00101111", .{}),
        parser.instructionSchema("mul", "1111011 w, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("imul", "1111011 w, mod 101 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("aam", "11010100, 00001010", .{}),
        parser.instructionSchema("div", "1111011 w, mod 110 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("idiv", "1111011 w, mod 111 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("aad", "11010101, 00001010", .{}),
        parser.instructionSchema("cbw", "10011000", .{}),
        parser.instructionSchema("cwd", "10011001", .{}),

        // Logic
        parser.instructionSchema("not", "1111011 w, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("shl", "110100 v w, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("shr", "110100 v w, mod 101 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("sar", "110100 v w, mod 111 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("rol", "110100 v w, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("ror", "110100 v w, mod 001 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("rcl", "110100 v w, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("rcr", "110100 v w, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instructionSchema("and", "001000 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("and", "1000000 w, mod 100 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("and", "0010010 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("test", "1000010 w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("test", "1111011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("test", "1010100 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("or", "000010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("or", "1000000 w, mod 001 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("or", "0000110 w, data, data_if_w_eq_1", .{}),

        parser.instructionSchema("xor", "001100 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("xor", "1000000 w, mod 110 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instructionSchema("xor", "0011010 w, data, data_if_w_eq_1", .{}),

        // String manipulation
        parser.instructionSchema("rep", "1111001 z", .{}),
        parser.instructionSchema("movs", "1010010 w", .{}),
        parser.instructionSchema("cmps", "1010011 w", .{}),
        parser.instructionSchema("scas", "1010111 w", .{}),
        parser.instructionSchema("lods", "1010110 w", .{}),
        parser.instructionSchema("stos", "1010101 w", .{}),

        // Control transfer
        parser.instructionSchema("call", "11101000, ip_inc_lo, ip_inc_hi", .{}),
        parser.instructionSchema("call", "11111111, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("call", "10011010, ip_lo, ip_hi, cs_lo, cs_hi", .{}),
        parser.instructionSchema("call", "11111111, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instructionSchema("jmp", "11101001, ip_inc_lo, ip_inc_hi", .{}),
        parser.instructionSchema("jmp", "11101011, ip_inc8", .{}),
        parser.instructionSchema("jmp", "11111111, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("jmp", "11101010, ip_lo, ip_hi, cs_lo, cs_hi", .{}),
        parser.instructionSchema("jmp", "11111111, mod 101 rm, disp_lo, disp_hi", .{}),

        parser.instructionSchema("ret", "11000011", .{}),
        parser.instructionSchema("ret", "11000010, data_lo, data_hi", .{}),
        parser.instructionSchema("ret", "11001011", .{}),
        parser.instructionSchema("ret", "11001010, data_lo, data_hi", .{}),

        parser.instructionSchema("je", "01110100, ip_inc8", .{}),
        parser.instructionSchema("jl", "01111100, ip_inc8", .{}),
        parser.instructionSchema("jle", "01111110, ip_inc8", .{}),
        parser.instructionSchema("jb", "01110010, ip_inc8", .{}),
        parser.instructionSchema("jbe", "01110110, ip_inc8", .{}),
        parser.instructionSchema("jp", "01111010, ip_inc8", .{}),
        parser.instructionSchema("jo", "01110000, ip_inc8", .{}),
        parser.instructionSchema("js", "01111000, ip_inc8", .{}),
        parser.instructionSchema("jne", "01110101, ip_inc8", .{}),
        parser.instructionSchema("jnl", "01111101, ip_inc8", .{}),
        parser.instructionSchema("jg", "01111111, ip_inc8", .{}),
        parser.instructionSchema("jnb", "01110011, ip_inc8", .{}),
        parser.instructionSchema("ja", "01110111, ip_inc8", .{}),
        parser.instructionSchema("jnp", "01111011, ip_inc8", .{}),
        parser.instructionSchema("jno", "01110001, ip_inc8", .{}),
        parser.instructionSchema("jns", "01111001, ip_inc8", .{}),

        parser.instructionSchema("loop", "11100010, ip_inc8", .{}),
        parser.instructionSchema("loopz", "11100001, ip_inc8", .{}),
        parser.instructionSchema("loopnz", "11100000, ip_inc8", .{}),
        parser.instructionSchema("jcxz", "11100011, ip_inc8", .{}),

        parser.instructionSchema("int", "11001101, data_8", .{}),
        parser.instructionSchema("int", "11001100", .{}),
        parser.instructionSchema("into", "11001110", .{}),
        parser.instructionSchema("iret", "11001111", .{}),

        // Processor control
        parser.instructionSchema("clc", "11111000", .{}),
        parser.instructionSchema("cmc", "11110101", .{}),
        parser.instructionSchema("stc", "11111001", .{}),
        parser.instructionSchema("cld", "11111100", .{}),
        parser.instructionSchema("std", "11111101", .{}),
        parser.instructionSchema("cli", "11111010", .{}),
        parser.instructionSchema("sti", "11111011", .{}),
        parser.instructionSchema("hlt", "11110100", .{}),
        parser.instructionSchema("wait", "10011011", .{}),
        parser.instructionSchema("esc", "11011 esc_opcode_hi, mod esc_opcode_lo rm, disp_lo, disp_hi", .{}),
        parser.instructionSchema("lock", "11110000", .{}),
        parser.instructionSchema("segment", "001 sr 110", .{}),
    };
};

test "build instruction encodings" {
    _ = instruction_encodings;
}
