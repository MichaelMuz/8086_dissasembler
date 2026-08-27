const std = @import("std");
const utils = @import("../utils.zig");
const schema = @import("schema.zig");

fn isLiteral(str: []const u8) bool {
    for (str) |c| {
        if (c != '1' and c != '0') return false;
    }
    return true;
}

fn parseSegment(segment: []const u8) struct { schema.SchemaField, u8, u8 } {
    var curr_field: schema.SchemaField = undefined;
    var add_to_skeleton: u8 = 0;
    var add_to_mask: u8 = 0;

    if (isLiteral(segment)) {
        curr_field = .{
            .literal_field = .{
                .width = @intCast(segment.len),
                .value = std.fmt.parseInt(u8, segment, 2) catch unreachable,
            },
        };
        // want to copy these bits to the skeleton and make mask have 1s here
        // mask gets 1s here
        add_to_skeleton = std.fmt.parseInt(u8, segment, 2) catch unreachable;
        add_to_mask = (@as(u8, 1) << @truncate(curr_field.width())) - 1;
    } else {
        curr_field = .{
            .named_field = schema.NamedField.of(segment),
        };
        // skeleton and mask keep 0s here
    }

    return .{
        curr_field,
        add_to_skeleton,
        add_to_mask,
    };
}

fn parseByte(byte: []const u8, field_list: *std.ArrayList(schema.SchemaField)) struct { u8, u8 } {
    var skeleton: u8 = 0;
    var mask: u8 = 0;
    var next_msb: u4 = 0;

    var segment_iter = std.mem.tokenizeSequence(u8, byte, " ");
    while (segment_iter.next()) |seg| {
        // std.debug.print("byte: {s}, next_msb: {d}\n", .{ byte, next_msb });
        const curr_field, const add_to_skeleton, const add_to_mask = parseSegment(seg);
        field_list.appendAssumeCapacity(curr_field);
        skeleton = utils.insertMostSigBits(u8, skeleton, @truncate(next_msb), add_to_skeleton, curr_field.width());
        mask = utils.insertMostSigBits(u8, mask, @truncate(next_msb), add_to_mask, curr_field.width());
        next_msb += curr_field.width();
    }

    // std.debug.print("byte: {s}, next_msb: {d}\n", .{ byte, next_msb });
    std.debug.assert(next_msb == 8);

    return .{ skeleton, mask };
}

const NotImplied = @as(?u8, null);
const ImplicitInitKwargs = std.enums.EnumFieldStruct(schema.NamedField, ?u8, NotImplied);

pub fn instSch(name: []const u8, pattern: []const u8, implied_values: ImplicitInitKwargs) schema.InstructionSchema {
    var buffer: [schema.MaxFieldsPerInstruction]schema.SchemaField = undefined;
    var field_list = std.ArrayList(schema.SchemaField).initBuffer(&buffer);

    var skeleton_halfs: [2]u8 = [_]u8{0} ** 2;
    var mask_halfs: [2]u8 = [_]u8{0} ** 2;
    var i: u8 = 0;

    var byte_iter = std.mem.tokenizeSequence(u8, pattern, ", ");
    while (byte_iter.next()) |byte| : (i += 1) {
        const byte_skeleton, const byte_mask = parseByte(byte, &field_list);
        if (i < 2) {
            skeleton_halfs[i] = byte_skeleton;
            mask_halfs[i] = byte_mask;
        } else {
            std.debug.assert(byte_skeleton == 0);
            std.debug.assert(byte_mask == 0);
        }
    }

    return schema.InstructionSchema{
        .name = name,
        .fixed_list = .{
            .fields = buffer,
            .len = field_list.items.len,
        },
        .implied_values = schema.ImpliedValues.initDefault(NotImplied, implied_values),
        .skeleton = std.mem.readInt(u16, &skeleton_halfs, .big),
        .mask = std.mem.readInt(u16, &mask_halfs, .big),
    };
}

test "check that things match" {
    const mov0 = instSch("mov0", "100010 d w", .{});
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
test "is one bit identified if I fill just first byte" {
    const mov = instSch("mov0", "100010 d w", .{});
    try std.testing.expect(mov.isOneByteIdentified());
}
test "is one bit identified if I fill just first byte and second is just vars" {
    const mov = instSch("mov0", "100010 d w, reg mod rm", .{});
    try std.testing.expect(mov.isOneByteIdentified());
}
test "is not one bit identified if I fill just one bit in second byte" {
    const mov = instSch("mov0", "100010 d w, reg rm 0 d", .{});
    try std.testing.expect(!mov.isOneByteIdentified());
}
test "check that the literal field has the right value" {
    const mov = instSch("mov0", "100010 d w, reg rm 0 d", .{});
    try std.testing.expect(mov.fields()[0].literal_field.value == 0b100010);
}
test "check that implied values are populated" {
    const mov = instSch("mov0", "100010 d w", .{ .data = 1, .z = 5 });
    try std.testing.expect(mov.fields()[0].literal_field.value == 0b100010);
    try std.testing.expect(mov.implied_values.get(.data) == 1);
    try std.testing.expect(mov.implied_values.get(.z) == 5);
}
