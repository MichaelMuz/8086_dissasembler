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

    pub fn of(s: []const u8) NamedField {
        const variant = std.meta.stringToEnum(NamedField, s) orelse unreachable;
        return variant;
    }

    // should I make this a u3? That only gets to 7 we should use u4? Maybe comptime to be int size needed for variants?
    // figure cpu wants 8 aligned anyhow
    pub fn width(self: NamedField) u4 {
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
            .skeleton = std.mem.readInt(u16, &skeleton_halfs, .little),
            .mask = std.mem.readInt(u16, &mask_halfs, .little),
        };
    }

    pub fn matches(self: *const InstructionSchema, other_pattern: u16) bool {
        const zero_where_agree = other_pattern ^ self.skeleton;
        const zero_where_agree_and_variable = zero_where_agree & self.mask;
        std.debug.print("zero_where_agree: {d}, zero_where_agree_and_variable: {d}\n", .{ zero_where_agree, zero_where_agree_and_variable });
        return 0 == zero_where_agree_and_variable;
    }
};

test "check that things match" {
    const mov0 = InstructionSchema.parseInstructionSchema("mov0", "100010 d w") catch unreachable;
    // const mov1 = Instruction.init("mov1", "1100011w") catch unreachable;
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
