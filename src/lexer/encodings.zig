const std = @import("std");
const schema = @import("schema.zig");
const parser = @import("parser.zig");

// https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf
// Table 4-12 page 164

pub const instruction_encodings = encodings: {
    @setEvalBranchQuota(1_000_000);

    break :encodings [_]schema.InstructionSchema{
        // Data transfer
        parser.instSch("mov", "100010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("mov", "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instSch("mov", "1011 w reg, data, data_if_w_eq_1", .{}),
        parser.instSch("mov", "1010000 w, addr_lo, addr_hi", .{}),
        parser.instSch("mov", "1010001 w, addr_lo, addr_hi", .{}),
        parser.instSch("mov", "10001110, mod 0 sr rm, disp_lo, disp_hi", .{}),
        parser.instSch("mov", "10001100, mod 0 sr rm, disp_lo, disp_hi", .{}),

        parser.instSch("push", "11111111, mod 110 rm, disp_lo, disp_hi", .{}),
        parser.instSch("push", "01010 reg", .{}),
        parser.instSch("push", "000 sr 110", .{}),

        parser.instSch("pop", "10001111, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instSch("pop", "01011 reg", .{}),
        parser.instSch("pop", "000 sr 111", .{}),

        parser.instSch("xchg", "1000011 w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("xchg", "10010 reg", .{}),

        parser.instSch("in", "1110010 w, data_8", .{}),
        parser.instSch("in", "1110110 w", .{}),
        parser.instSch("out", "1110011 w, data_8", .{}),
        parser.instSch("out", "1110111 w", .{}),

        parser.instSch("xlat", "11010111", .{}),
        parser.instSch("lea", "10001101, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("lds", "11000101, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("les", "11000100, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("lahf", "10011111", .{}),
        parser.instSch("sahf", "10011110", .{}),
        parser.instSch("pushf", "10011100", .{}),
        parser.instSch("popf", "10011101", .{}),

        // Arithmetic
        parser.instSch("add", "000000 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("add", "100000 s w, mod 000 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instSch("add", "0000010 w, data, data_if_w_eq_1", .{}),

        parser.instSch("adc", "000100 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("adc", "100000 s w, mod 010 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instSch("adc", "0001010 w, data, data_if_w_eq_1", .{}),

        parser.instSch("inc", "1111111 w, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instSch("inc", "01000 reg", .{}),
        parser.instSch("aaa", "00110111", .{}),
        parser.instSch("daa", "00100111", .{}),

        parser.instSch("sub", "001010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("sub", "100000 s w, mod 101 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instSch("sub", "0010110 w, data, data_if_w_eq_1", .{}),

        parser.instSch("sbb", "000110 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("sbb", "100000 s w, mod 011 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instSch("sbb", "0001110 w, data, data_if_w_eq_1", .{}),

        parser.instSch("dec", "1111111 w, mod 001 rm, disp_lo, disp_hi", .{}),
        parser.instSch("dec", "01001 reg", .{}),
        parser.instSch("neg", "1111011 w, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instSch("cmp", "001110 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("cmp", "100000 s w, mod 111 rm, disp_lo, disp_hi, data, data_if_sw_eq_01", .{}),
        parser.instSch("cmp", "0011110 w, data, data_if_w_eq_1", .{}),

        parser.instSch("aas", "00111111", .{}),
        parser.instSch("das", "00101111", .{}),
        parser.instSch("mul", "1111011 w, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instSch("imul", "1111011 w, mod 101 rm, disp_lo, disp_hi", .{}),
        parser.instSch("aam", "11010100, 00001010", .{}),
        parser.instSch("div", "1111011 w, mod 110 rm, disp_lo, disp_hi", .{}),
        parser.instSch("idiv", "1111011 w, mod 111 rm, disp_lo, disp_hi", .{}),
        parser.instSch("aad", "11010101, 00001010", .{}),
        parser.instSch("cbw", "10011000", .{}),
        parser.instSch("cwd", "10011001", .{}),

        // Logic
        parser.instSch("not", "1111011 w, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instSch("shl", "110100 v w, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instSch("shr", "110100 v w, mod 101 rm, disp_lo, disp_hi", .{}),
        parser.instSch("sar", "110100 v w, mod 111 rm, disp_lo, disp_hi", .{}),
        parser.instSch("rol", "110100 v w, mod 000 rm, disp_lo, disp_hi", .{}),
        parser.instSch("ror", "110100 v w, mod 001 rm, disp_lo, disp_hi", .{}),
        parser.instSch("rcl", "110100 v w, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instSch("rcr", "110100 v w, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instSch("and", "001000 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("and", "1000000 w, mod 100 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instSch("and", "0010010 w, data, data_if_w_eq_1", .{}),

        parser.instSch("test", "1000010 w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("test", "1111011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instSch("test", "1010100 w, data, data_if_w_eq_1", .{}),

        parser.instSch("or", "000010 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("or", "1000000 w, mod 001 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instSch("or", "0000110 w, data, data_if_w_eq_1", .{}),

        parser.instSch("xor", "001100 d w, mod reg rm, disp_lo, disp_hi", .{}),
        parser.instSch("xor", "1000000 w, mod 110 rm, disp_lo, disp_hi, data, data_if_w_eq_1", .{}),
        parser.instSch("xor", "0011010 w, data, data_if_w_eq_1", .{}),

        // String manipulation
        parser.instSch("rep", "1111001 z", .{}),
        parser.instSch("movs", "1010010 w", .{}),
        parser.instSch("cmps", "1010011 w", .{}),
        parser.instSch("scas", "1010111 w", .{}),
        parser.instSch("lods", "1010110 w", .{}),
        parser.instSch("stos", "1010101 w", .{}),

        // Control transfer
        parser.instSch("call", "11101000, ip_inc_lo, ip_inc_hi", .{}),
        parser.instSch("call", "11111111, mod 010 rm, disp_lo, disp_hi", .{}),
        parser.instSch("call", "10011010, ip_lo, ip_hi, cs_lo, cs_hi", .{}),
        parser.instSch("call", "11111111, mod 011 rm, disp_lo, disp_hi", .{}),

        parser.instSch("jmp", "11101001, ip_inc_lo, ip_inc_hi", .{}),
        parser.instSch("jmp", "11101011, ip_inc8", .{}),
        parser.instSch("jmp", "11111111, mod 100 rm, disp_lo, disp_hi", .{}),
        parser.instSch("jmp", "11101010, ip_lo, ip_hi, cs_lo, cs_hi", .{}),
        parser.instSch("jmp", "11111111, mod 101 rm, disp_lo, disp_hi", .{}),

        parser.instSch("ret", "11000011", .{}),
        parser.instSch("ret", "11000010, data_lo, data_hi", .{}),
        parser.instSch("ret", "11001011", .{}),
        parser.instSch("ret", "11001010, data_lo, data_hi", .{}),

        parser.instSch("je", "01110100, ip_inc8", .{}),
        parser.instSch("jl", "01111100, ip_inc8", .{}),
        parser.instSch("jle", "01111110, ip_inc8", .{}),
        parser.instSch("jb", "01110010, ip_inc8", .{}),
        parser.instSch("jbe", "01110110, ip_inc8", .{}),
        parser.instSch("jp", "01111010, ip_inc8", .{}),
        parser.instSch("jo", "01110000, ip_inc8", .{}),
        parser.instSch("js", "01111000, ip_inc8", .{}),
        parser.instSch("jne", "01110101, ip_inc8", .{}),
        parser.instSch("jnl", "01111101, ip_inc8", .{}),
        parser.instSch("jg", "01111111, ip_inc8", .{}),
        parser.instSch("jnb", "01110011, ip_inc8", .{}),
        parser.instSch("ja", "01110111, ip_inc8", .{}),
        parser.instSch("jnp", "01111011, ip_inc8", .{}),
        parser.instSch("jno", "01110001, ip_inc8", .{}),
        parser.instSch("jns", "01111001, ip_inc8", .{}),

        parser.instSch("loop", "11100010, ip_inc8", .{}),
        parser.instSch("loopz", "11100001, ip_inc8", .{}),
        parser.instSch("loopnz", "11100000, ip_inc8", .{}),
        parser.instSch("jcxz", "11100011, ip_inc8", .{}),

        parser.instSch("int", "11001101, data_8", .{}),
        parser.instSch("int", "11001100", .{}),
        parser.instSch("into", "11001110", .{}),
        parser.instSch("iret", "11001111", .{}),

        // Processor control
        parser.instSch("clc", "11111000", .{}),
        parser.instSch("cmc", "11110101", .{}),
        parser.instSch("stc", "11111001", .{}),
        parser.instSch("cld", "11111100", .{}),
        parser.instSch("std", "11111101", .{}),
        parser.instSch("cli", "11111010", .{}),
        parser.instSch("sti", "11111011", .{}),
        parser.instSch("hlt", "11110100", .{}),
        parser.instSch("wait", "10011011", .{}),
        parser.instSch("esc", "11011 esc_opcode_hi, mod esc_opcode_lo rm, disp_lo, disp_hi", .{}),
        parser.instSch("lock", "11110000", .{}),
        parser.instSch("segment", "001 sr 110", .{}),
    };
};

test "build instruction encodings" {
    _ = instruction_encodings;
}
