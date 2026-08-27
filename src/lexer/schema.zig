const std = @import("std");
const utils = @import("../utils.zig");

pub const NamedField = enum {
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

pub const LiteralField = struct {
    width: u4,
    value: u8,
};

pub const SchemaField = union(enum) {
    literal_field: LiteralField,
    named_field: NamedField,

    pub fn width(self: SchemaField) u4 {
        return switch (self) {
            .literal_field => |lit| lit.width,
            .named_field => |named| named.width(),
        };
    }
};

pub const MaxFieldsPerInstruction = 8 * 6; // At most 8 one bit things, at most 6 bytes

pub const ImpliedValues = std.EnumArray(NamedField, ?u8);

pub const InstructionSchema = struct {
    name: []const u8,
    fixed_list: struct {
        fields: [MaxFieldsPerInstruction]SchemaField,
        len: usize,
    },
    /// things hardcoded by the instruction itself
    implied_values: std.EnumArray(NamedField, ?u8),
    /// the literal bits preserved and 0s for the variable bits
    skeleton: u16,
    /// the literal bits have 1s and the variable bits get 0s
    mask: u16,

    pub fn isOneByteIdentified(self: *const InstructionSchema) bool {
        return utils.getSubBits(u16, self.mask, 0, 8) == 0;
    }

    pub fn fields(self: *const InstructionSchema) []const SchemaField {
        return self.fixed_list.fields[0..self.fixed_list.len];
    }

    pub fn matches(self: *const InstructionSchema, other_pattern: u16) bool {
        const zero_where_agree = other_pattern ^ self.skeleton;
        const zero_where_agree_and_variable = zero_where_agree & self.mask;
        // std.debug.print("skeleton: {b:0>16}\nmask: {b:0>16}\nzero_where_agree: {b}\nzero_where_agree_and_variable: {b}\n", .{ self.skeleton, self.mask, zero_where_agree, zero_where_agree_and_variable });
        return 0 == zero_where_agree_and_variable;
    }
};
