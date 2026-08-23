const std = @import("std");
const parser = @import("parser.zig");

const RawInstructionEncoding = struct {
    name: []const u8,
    pattern: []const u8,
};

// Intel 8086 Family User's Manual, October 1979, table 4-12, pages 4-22--4-27.
pub const instruction_encodings = [_]RawInstructionEncoding{
    // Data transfer
    .{ .name = "mov", .pattern = "100010 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "mov", .pattern = "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1" },
    .{ .name = "mov", .pattern = "1011 w reg, data, data_if_w_eq_1" },
    .{ .name = "mov", .pattern = "1010000 w, addr_lo, addr_hi" },
    .{ .name = "mov", .pattern = "1010001 w, addr_lo, addr_hi" },
    .{ .name = "mov", .pattern = "10001110, mod 0 sr rm, disp_lo, disp_hi" },
    .{ .name = "mov", .pattern = "10001100, mod 0 sr rm, disp_lo, disp_hi" },

    .{ .name = "push", .pattern = "11111111, mod 110 rm, disp_lo, disp_hi" },
    .{ .name = "push", .pattern = "01010 reg" },
    .{ .name = "push", .pattern = "000 sr 110" },

    .{ .name = "pop", .pattern = "10001111, mod 000 rm, disp_lo, disp_hi" },
    .{ .name = "pop", .pattern = "01011 reg" },
    .{ .name = "pop", .pattern = "000 sr 111" },

    .{ .name = "xchg", .pattern = "1000011 w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "xchg", .pattern = "10010 reg" },

    .{ .name = "in", .pattern = "1110010 w, data_8" },
    .{ .name = "in", .pattern = "1110110 w" },
    .{ .name = "out", .pattern = "1110011 w, data_8" },
    .{ .name = "out", .pattern = "1110111 w" },

    .{ .name = "xlat", .pattern = "11010111" },
    .{ .name = "lea", .pattern = "10001101, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "lds", .pattern = "11000101, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "les", .pattern = "11000100, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "lahf", .pattern = "10011111" },
    .{ .name = "sahf", .pattern = "10011110" },
    .{ .name = "pushf", .pattern = "10011100" },
    .{ .name = "popf", .pattern = "10011101" },

    // Arithmetic
    .{ .name = "add", .pattern = "000000 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "add", .pattern = "100000 s w, mod 000 rm, disp_lo, disp_hi, data, data_if_sw_eq_01" },
    .{ .name = "add", .pattern = "0000010 w, data, data_if_w_eq_1" },

    .{ .name = "adc", .pattern = "000100 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "adc", .pattern = "100000 s w, mod 010 rm, disp_lo, disp_hi, data, data_if_sw_eq_01" },
    .{ .name = "adc", .pattern = "0001010 w, data, data_if_w_eq_1" },

    .{ .name = "inc", .pattern = "1111111 w, mod 000 rm, disp_lo, disp_hi" },
    .{ .name = "inc", .pattern = "01000 reg" },
    .{ .name = "aaa", .pattern = "00110111" },
    .{ .name = "daa", .pattern = "00100111" },

    .{ .name = "sub", .pattern = "001010 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "sub", .pattern = "100000 s w, mod 101 rm, disp_lo, disp_hi, data, data_if_sw_eq_01" },
    .{ .name = "sub", .pattern = "0010110 w, data, data_if_w_eq_1" },

    .{ .name = "sbb", .pattern = "000110 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "sbb", .pattern = "100000 s w, mod 011 rm, disp_lo, disp_hi, data, data_if_sw_eq_01" },
    .{ .name = "sbb", .pattern = "0001110 w, data, data_if_w_eq_1" },

    .{ .name = "dec", .pattern = "1111111 w, mod 001 rm, disp_lo, disp_hi" },
    .{ .name = "dec", .pattern = "01001 reg" },
    .{ .name = "neg", .pattern = "1111011 w, mod 011 rm, disp_lo, disp_hi" },

    .{ .name = "cmp", .pattern = "001110 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "cmp", .pattern = "100000 s w, mod 111 rm, disp_lo, disp_hi, data, data_if_sw_eq_01" },
    .{ .name = "cmp", .pattern = "0011110 w, data, data_if_w_eq_1" },

    .{ .name = "aas", .pattern = "00111111" },
    .{ .name = "das", .pattern = "00101111" },
    .{ .name = "mul", .pattern = "1111011 w, mod 100 rm, disp_lo, disp_hi" },
    .{ .name = "imul", .pattern = "1111011 w, mod 101 rm, disp_lo, disp_hi" },
    .{ .name = "aam", .pattern = "11010100, 00001010" },
    .{ .name = "div", .pattern = "1111011 w, mod 110 rm, disp_lo, disp_hi" },
    .{ .name = "idiv", .pattern = "1111011 w, mod 111 rm, disp_lo, disp_hi" },
    .{ .name = "aad", .pattern = "11010101, 00001010" },
    .{ .name = "cbw", .pattern = "10011000" },
    .{ .name = "cwd", .pattern = "10011001" },

    // Logic
    .{ .name = "not", .pattern = "1111011 w, mod 010 rm, disp_lo, disp_hi" },
    .{ .name = "shl", .pattern = "110100 v w, mod 100 rm, disp_lo, disp_hi" },
    .{ .name = "shr", .pattern = "110100 v w, mod 101 rm, disp_lo, disp_hi" },
    .{ .name = "sar", .pattern = "110100 v w, mod 111 rm, disp_lo, disp_hi" },
    .{ .name = "rol", .pattern = "110100 v w, mod 000 rm, disp_lo, disp_hi" },
    .{ .name = "ror", .pattern = "110100 v w, mod 001 rm, disp_lo, disp_hi" },
    .{ .name = "rcl", .pattern = "110100 v w, mod 010 rm, disp_lo, disp_hi" },
    .{ .name = "rcr", .pattern = "110100 v w, mod 011 rm, disp_lo, disp_hi" },

    .{ .name = "and", .pattern = "001000 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "and", .pattern = "1000000 w, mod 100 rm, disp_lo, disp_hi, data, data_if_w_eq_1" },
    .{ .name = "and", .pattern = "0010010 w, data, data_if_w_eq_1" },

    .{ .name = "test", .pattern = "1000010 w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "test", .pattern = "1111011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1" },
    .{ .name = "test", .pattern = "1010100 w, data, data_if_w_eq_1" },

    .{ .name = "or", .pattern = "000010 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "or", .pattern = "1000000 w, mod 001 rm, disp_lo, disp_hi, data, data_if_w_eq_1" },
    .{ .name = "or", .pattern = "0000110 w, data, data_if_w_eq_1" },

    .{ .name = "xor", .pattern = "001100 d w, mod reg rm, disp_lo, disp_hi" },
    .{ .name = "xor", .pattern = "1000000 w, mod 110 rm, disp_lo, disp_hi, data, data_if_w_eq_1" },
    .{ .name = "xor", .pattern = "0011010 w, data, data_if_w_eq_1" },

    // String manipulation
    .{ .name = "rep", .pattern = "1111001 z" },
    .{ .name = "movs", .pattern = "1010010 w" },
    .{ .name = "cmps", .pattern = "1010011 w" },
    .{ .name = "scas", .pattern = "1010111 w" },
    .{ .name = "lods", .pattern = "1010110 w" },
    .{ .name = "stos", .pattern = "1010101 w" },

    // Control transfer
    .{ .name = "call", .pattern = "11101000, ip_inc_lo, ip_inc_hi" },
    .{ .name = "call", .pattern = "11111111, mod 010 rm, disp_lo, disp_hi" },
    .{ .name = "call", .pattern = "10011010, ip_lo, ip_hi, cs_lo, cs_hi" },
    .{ .name = "call", .pattern = "11111111, mod 011 rm, disp_lo, disp_hi" },

    .{ .name = "jmp", .pattern = "11101001, ip_inc_lo, ip_inc_hi" },
    .{ .name = "jmp", .pattern = "11101011, ip_inc8" },
    .{ .name = "jmp", .pattern = "11111111, mod 100 rm, disp_lo, disp_hi" },
    .{ .name = "jmp", .pattern = "11101010, ip_lo, ip_hi, cs_lo, cs_hi" },
    .{ .name = "jmp", .pattern = "11111111, mod 101 rm, disp_lo, disp_hi" },

    .{ .name = "ret", .pattern = "11000011" },
    .{ .name = "ret", .pattern = "11000010, data_lo, data_hi" },
    .{ .name = "ret", .pattern = "11001011" },
    .{ .name = "ret", .pattern = "11001010, data_lo, data_hi" },

    .{ .name = "je", .pattern = "01110100, ip_inc8" },
    .{ .name = "jl", .pattern = "01111100, ip_inc8" },
    .{ .name = "jle", .pattern = "01111110, ip_inc8" },
    .{ .name = "jb", .pattern = "01110010, ip_inc8" },
    .{ .name = "jbe", .pattern = "01110110, ip_inc8" },
    .{ .name = "jp", .pattern = "01111010, ip_inc8" },
    .{ .name = "jo", .pattern = "01110000, ip_inc8" },
    .{ .name = "js", .pattern = "01111000, ip_inc8" },
    .{ .name = "jne", .pattern = "01110101, ip_inc8" },
    .{ .name = "jnl", .pattern = "01111101, ip_inc8" },
    .{ .name = "jg", .pattern = "01111111, ip_inc8" },
    .{ .name = "jnb", .pattern = "01110011, ip_inc8" },
    .{ .name = "ja", .pattern = "01110111, ip_inc8" },
    .{ .name = "jnp", .pattern = "01111011, ip_inc8" },
    .{ .name = "jno", .pattern = "01110001, ip_inc8" },
    .{ .name = "jns", .pattern = "01111001, ip_inc8" },

    .{ .name = "loop", .pattern = "11100010, ip_inc8" },
    .{ .name = "loopz", .pattern = "11100001, ip_inc8" },
    .{ .name = "loopnz", .pattern = "11100000, ip_inc8" },
    .{ .name = "jcxz", .pattern = "11100011, ip_inc8" },

    .{ .name = "int", .pattern = "11001101, data_8" },
    .{ .name = "int", .pattern = "11001100" },
    .{ .name = "into", .pattern = "11001110" },
    .{ .name = "iret", .pattern = "11001111" },

    // Processor control
    .{ .name = "clc", .pattern = "11111000" },
    .{ .name = "cmc", .pattern = "11110101" },
    .{ .name = "stc", .pattern = "11111001" },
    .{ .name = "cld", .pattern = "11111100" },
    .{ .name = "std", .pattern = "11111101" },
    .{ .name = "cli", .pattern = "11111010" },
    .{ .name = "sti", .pattern = "11111011" },
    .{ .name = "hlt", .pattern = "11110100" },
    .{ .name = "wait", .pattern = "10011011" },
    .{ .name = "esc", .pattern = "11011 esc_opcode_hi, mod esc_opcode_lo rm, disp_lo, disp_hi" },
    .{ .name = "lock", .pattern = "11110000" },
    .{ .name = "segment", .pattern = "001 sr 110" },
};

test "all instruction encodings parse" {
    for (instruction_encodings) |encoding| {
        _ = try parser.parseInstructionSchema(encoding.name, encoding.pattern);
    }
}

test "check that things match" {
    const mov0 = parser.parseInstructionSchema("mov0", "100010 d w") catch unreachable;
    // const mov1 = Instruction.init("mov1", "1100011w") catch unreachable;
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
