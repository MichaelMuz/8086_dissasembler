const std = @import("std");
const utils = @import("utils.zig");

const NamedField = enum {
    d,
    w,
    s,
    v,
    z,
    mod,
    reg,
    rm,
    sr,
    esc_opcode_hi,
    esc_opcode_lo,
    disp_lo,
    disp_hi,
    data,
    data_if_w_eq_1,
    data_if_sw_eq_01,
    data_8,
    data_lo,
    data_hi,
    addr_lo,
    addr_hi,
    ip_lo,
    ip_hi,
    ip_inc_lo,
    ip_inc_hi,
    ip_inc8,
    cs_lo,
    cs_hi,

    pub fn of(s: []const u8) NamedField {
        const variant = std.meta.stringToEnum(NamedField, s) orelse unreachable;
        return variant;
    }

    pub fn width(self: NamedField) u4 {
        return switch (self) {
            .d => 1,
            .w => 1,
            .s => 1,
            .v => 1,
            .z => 1,
            .mod => 2,
            .reg => 3,
            .rm => 3,
            .sr => 2,
            .esc_opcode_hi => 3,
            .esc_opcode_lo => 3,
            .disp_lo => 8,
            .disp_hi => 8,
            .data => 8,
            .data_if_w_eq_1 => 8,
            .data_if_sw_eq_01 => 8,
            .data_8 => 8,
            .data_lo => 8,
            .data_hi => 8,
            .addr_lo => 8,
            .addr_hi => 8,
            .ip_lo => 8,
            .ip_hi => 8,
            .ip_inc_lo => 8,
            .ip_inc_hi => 8,
            .ip_inc8 => 8,
            .cs_lo => 8,
            .cs_hi => 8,
        };
    }
};

const LiteralField = struct {
    width: u4,
};

const SchemaField = union(enum) {
    literal_field: LiteralField,
    named_field: NamedField,

    pub fn width(self: SchemaField) u4 {
        return switch (self) {
            .literal_field => |lit| lit.width,
            .named_field => |named| named.width(),
        };
    }
};

const MaxFieldsPerInstruction = 8 * 6; // At most 8 one bit things, at most 6 bytes

const InstructionSchema = struct {
    name: []const u8,
    fixed_list: struct {
        fields: [MaxFieldsPerInstruction]SchemaField,
        len: usize,
    },
    /// the literal bits preserved and 0s for the variable bits
    skeleton: u16,
    /// the literal bits have 1s and the variable bits get 0s
    mask: u16,

    pub fn fields(self: *const InstructionSchema) []SchemaField {
        return self.fixed_list.fields[0..self.fixed_list.len];
    }

    fn isLiteral(str: []const u8) bool {
        for (str) |c| {
            if (c != '1' and c != '0') return false;
        }
        return true;
    }

    fn parseSegment(segment: []const u8) struct { SchemaField, u8, u8 } {
        var curr_field: SchemaField = undefined;
        var add_to_skeleton: u8 = 0;
        var add_to_mask: u8 = 0;

        if (InstructionSchema.isLiteral(segment)) {
            curr_field = .{
                .literal_field = .{
                    .width = @intCast(segment.len),
                },
            };
            // want to copy these bits to the skeleton and make mask have 1s here
            // mask gets 1s here
            add_to_skeleton = std.fmt.parseInt(u8, segment, 2) catch unreachable;
            add_to_mask = (@as(u8, 1) << @truncate(curr_field.width())) - 1;
        } else {
            curr_field = .{
                .named_field = NamedField.of(segment),
            };
            // skeleton and mask keep 0s here
        }

        return .{
            curr_field,
            add_to_skeleton,
            add_to_mask,
        };
    }

    fn parseByte(byte: []const u8, field_list: *std.ArrayList(SchemaField)) struct { u8, u8 } {
        var skeleton: u8 = 0;
        var mask: u8 = 0;
        var next_msb: u4 = 0;

        var segment_iter = std.mem.tokenizeSequence(u8, byte, " ");
        while (segment_iter.next()) |seg| {
            std.debug.print("byte: {s}, next_msb: {d}\n", .{ byte, next_msb });
            const curr_field, const add_to_skeleton, const add_to_mask = InstructionSchema.parseSegment(seg);
            field_list.appendAssumeCapacity(curr_field);
            skeleton = utils.insertMostSigBits(u8, skeleton, @truncate(next_msb), add_to_skeleton, curr_field.width());
            mask = utils.insertMostSigBits(u8, mask, @truncate(next_msb), add_to_mask, curr_field.width());
            next_msb += curr_field.width();
        }

        std.debug.print("byte: {s}, next_msb: {d}\n", .{ byte, next_msb });
        std.debug.assert(next_msb == 8);

        return .{ skeleton, mask };
    }

    pub fn parseInstructionSchema(name: []const u8, pattern: []const u8) !InstructionSchema {
        var buffer: [MaxFieldsPerInstruction]SchemaField = undefined;
        var field_list = std.ArrayList(SchemaField).initBuffer(&buffer);

        var skeleton_halfs: [2]u8 = [_]u8{0} ** 2;
        var mask_halfs: [2]u8 = [_]u8{0} ** 2;
        var i: u8 = 0;

        var byte_iter = std.mem.tokenizeSequence(u8, pattern, ", ");
        while (byte_iter.next()) |byte| : (i += 1) {
            const byte_skeleton, const byte_mask = InstructionSchema.parseByte(byte, &field_list);
            if (i < 2) {
                skeleton_halfs[i] = byte_skeleton;
                mask_halfs[i] = byte_mask;
            } else {
                std.debug.assert(byte_skeleton == 0);
                std.debug.assert(byte_mask == 0);
            }
        }

        // std.debug.print("skeleton: {s}\n", .{skeleton});
        // std.debug.print("mask: {s}\n", .{mask});

        return InstructionSchema{
            .name = name,
            .fixed_list = .{
                .fields = buffer,
                .len = field_list.items.len,
            },
            .skeleton = std.mem.readInt(u16, &skeleton_halfs, .big),
            .mask = std.mem.readInt(u16, &mask_halfs, .big),
        };
    }

    pub fn matches(self: *const InstructionSchema, other_pattern: u16) bool {
        const zero_where_agree = other_pattern ^ self.skeleton;
        const zero_where_agree_and_variable = zero_where_agree & self.mask;
        std.debug.print("skeleton: {b:0>16}\nmask: {b:0>16}\nzero_where_agree: {b}\nzero_where_agree_and_variable: {b}\n", .{ self.skeleton, self.mask, zero_where_agree, zero_where_agree_and_variable });
        return 0 == zero_where_agree_and_variable;
    }
};

const RawInstructionEncoding = struct {
    name: []const u8,
    pattern: []const u8,
};

// Intel 8086 Family User's Manual, October 1979, table 4-12, pages 4-22--4-27.
const instruction_encodings = [_]RawInstructionEncoding{
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
        _ = try InstructionSchema.parseInstructionSchema(encoding.name, encoding.pattern);
    }
}

test "check that things match" {
    const mov0 = InstructionSchema.parseInstructionSchema("mov0", "100010 d w") catch unreachable;
    // const mov1 = Instruction.init("mov1", "1100011w") catch unreachable;
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
