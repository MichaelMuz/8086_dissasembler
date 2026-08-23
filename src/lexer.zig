const std = @import("std");
const utils = @import("utils.zig");

const NamedField = enum {
    d,
    w,
    mod,
    reg,
    rm,
    disp_lo,
    disp_hi,
    data,
    data_if_w_eq_1,

    pub fn of(s: []u8) NamedField {
        const variant = std.meta.stringToEnum(NamedField, s);
        if (variant == null) unreachable;
        return variant;
    }

    // should I make this a u3? That only gets to 7 we should use u4? Maybe comptime to be int size needed for variants?
    // figure cpu wants 8 aligned anyhow
    pub fn width(self: NamedField) u8 {
        return switch (self) {
            .d => 1,
            .w => 1,
            .mod => 3,
            .reg => 3,
            .rm => 2,
            .disp_lo => 8,
            .disp_hi => 8,
            .data => 8,
            .data_if_w_eq_1 => 8,
        };
    }
};

const LiteralField = struct {
    width: u8,
};

const SchemaField = union(enum) {
    literal_field: LiteralField,
    named_field: NamedField,

    pub fn width(self: SchemaField) u8 {
        return switch (self) {
            .literal_field => |lit| lit.width,
            .named_field => |named| named.width(),
        };
    }
};

const MaxFieldsPerInstruction = 8 * 6; // At most 8 one bit things, at most 6 bytes

// TODO I can comptime this so it knows if it is 8 or 16 bits prob?
const Instruction = struct {
    name: []const u8,
    fields: []SchemaField,
    /// the literal bits preserved and 0s for the variable bits
    skeleton: u16,
    /// the literal bits have 1s and the variable bits get 0s
    mask: u16,

    pub fn init(name: []const u8, pattern: []const u8) !Instruction {
        var skeleton: u16 = 0;
        var mask: u16 = 0;
        var next_bit: u8 = @typeInfo(@Int(.unsigned, u16)).int.bits - 1;

        var buffer: [MaxFieldsPerInstruction]SchemaField = undefined;
        var fields = std.ArrayList(SchemaField).initBuffer(buffer);

        for (std.mem.tokenizeAny(u8, pattern, ", ")) |by| {
            for (std.mem.tokenizeAny(u8, by, " ")) |seg| {
                const curr_field = undefined;
                const add_to_skeleton: u8 = 0;
                const add_to_mask: u8 = 0;
                if (std.ascii.isDigit(seg)) {
                    curr_field = LiteralField(add_to_skeleton);
                    // want to copy these bits to the skeleton and make mask have 1s here
                    // mask gets 1s here
                    add_to_skeleton = std.fmt.parseInt(u8, seg, 2);
                    add_to_mask = (1 << curr_field.width) - 1;
                } else {
                    curr_field = NamedField.of(seg);
                    // skeleton and mask get 0s here
                }
                fields.append(curr_field);
                utils.insertMostSigBits(u16, skeleton, next_bit, add_to_skeleton);

                next_bit -= curr_field.width();

                next_field += 1;
            }
        }

        // std.debug.print("skeleton: {s}\n", .{skeleton});
        // std.debug.print("mask: {s}\n", .{mask});

        return Instruction{ .name = name, .fields = pattern[0..next_field], .skeleton = skeleton, .mask = mask };
    }

    pub fn matches(self: Instruction, other_pattern: u16) bool {
        const zero_where_agree = other_pattern ^ self.skeleton;
        const zero_where_agree_and_variable = zero_where_agree & self.mask;
        std.debug.print("zero_where_agree: {d}, zero_where_agree_and_variable: {d}\n", .{ zero_where_agree, zero_where_agree_and_variable });
        return 0 == zero_where_agree_and_variable;
    }
};

test "check that things match" {
    const mov0 = Instruction.init("mov0", "100010dw") catch unreachable;
    // const mov1 = Instruction.init("mov1", "1100011w") catch unreachable;
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
