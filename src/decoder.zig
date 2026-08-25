const std = @import("std");
const utils = @import("utils.zig");
const lexer = @import("lexer.zig");

const DecodeError = error{
    InvalidInstruction,
};

const ParsedInstruction = std.EnumArray(lexer.schema.NamedField, ?u8);

fn calcDisp(extracted: *const ParsedInstruction) enum { none, one_byte, two_bytes } {
    // note could just make this a static lookup table, prob faster at runtime. Will check asm zig generates.
    const max_u8 = std.math.maxInt(u8);
    return switch (extracted.get(.mod) orelse return .none) {
        0b100...max_u8 => unreachable,
        0b00 => switch (extracted.get(.rm) orelse unreachable) {
            0b1000...max_u8 => unreachable,
            0b110 => .two_bytes,
            else => .none,
        },
        0b01 => .one_byte,
        0b10 => .two_bytes,
        0b11 => .none,
    };
}

fn shouldTake(extracted: *const ParsedInstruction, curr_field: *const lexer.schema.SchemaField) bool {
    return switch (curr_field.*) {
        .literal_field => true,
        .named_field => |n| switch (n) {
            .d => true,
            .w => true,
            .s => true,
            .v => true,
            .z => true,
            .mod => true,
            .reg => true,
            .rm => true,
            .sr => true,
            .esc_opcode_hi => true,
            .esc_opcode_lo => true,
            .disp_lo => calcDisp(extracted) != .none,
            .disp_hi => calcDisp(extracted) == .two_bytes,
            .data => true,
            .data_if_w_eq_1 => extracted.get(.w).? != 0,
            .data_if_sw_eq_01 => extracted.get(.s).? == 0 and extracted.get(.w).? != 0,
            .data_8 => true,
            .data_lo => true,
            .data_hi => true,
            .addr_lo => true,
            .addr_hi => true,
            .ip_lo => true,
            .ip_hi => true,
            .ip_inc_lo => true,
            .ip_inc_hi => true,
            .ip_inc8 => true,
            .cs_lo => true,
            .cs_hi => true,
        },
    };
}

fn extract(reader: *std.Io.Reader, schema: *const lexer.schema.InstructionSchema) !ParsedInstruction {
    // std.debug.print("starting\n", .{});
    var parsedInst = ParsedInstruction.initFill(null);
    var next_msb: u3 = 0;
    var curr_byte: u8 = 0;

    for (schema.fields()) |f| {
        if (next_msb == 0) {
            if (!shouldTake(&parsedInst, &f)) {
                if (next_msb != 0 or f.width() != 8) unreachable;
                continue;
            }

            curr_byte = reader.takeByte() catch |err| switch (err) {
                error.EndOfStream => return error.InvalidInstruction,
                error.ReadFailed => return err,
            };
        }

        // std.debug.print("HERE curr_byte: {b}, next_msb: {d}, f.width: {d}\n", .{ curr_byte, next_msb, f.width() });
        const sub_bits = utils.getSubMostSigBits(u8, curr_byte, next_msb, f.width());

        switch (f) {
            .literal_field => |l| if (l.value != sub_bits) unreachable,
            .named_field => |n| parsedInst.set(n, sub_bits),
        }

        const new_next_msb: u4 = next_msb + f.width();
        if (new_next_msb > 8) {
            unreachable;
        } else if (new_next_msb == 8) {
            next_msb = 0;
        } else {
            next_msb = @truncate(new_next_msb);
        }
    }
    return parsedInst; // maybe I take an out param? Could be more performant. Will check asm zig makes
}

fn decode(reader: *std.Io.Reader) !ParsedInstruction {
    const peeked = reader.peek(2) catch |err| switch (err) {
        error.EndOfStream => try reader.peek(1),
        error.ReadFailed => return err,
    };

    const is_last_byte: bool = peeked.len == 1;
    const stamp: u16 = switch (is_last_byte) {
        true => std.mem.readInt(u16, &[_]u8{ peeked[0], 0 }, .big),
        false => std.mem.readInt(u16, &[_]u8{ peeked[0], peeked[1] }, .big),
    };

    const matched_schema: lexer.schema.InstructionSchema = for (lexer.encodings.instruction_encodings) |err| {
        if (is_last_byte and !err.isOneByteIdentified()) {
            continue;
        } else if (err.matches(stamp)) {
            break err;
        }
    } else return error.InvalidInstruction;

    return extract(reader, &matched_schema);
}

// pub fn disassembleStream(reader: *std.Io.Reader, writer: *std.Io.Writer) !void {
//     while (true) {
//         // const d = decode(reader);
//         // const s = format(d);
//         // try writer.write(s);
//     }
// }

test "basic mov" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi"
    var reader = std.Io.Reader.fixed(&[_]u8{ 0b10001011, 0b11001001 });
    const ac = try decode(&reader);
    var exp = ParsedInstruction.initFill(null);
    exp.set(.d, 0b1);
    exp.set(.w, 0b1);
    exp.set(.mod, 0b11);
    exp.set(.reg, 0b001);
    exp.set(.rm, 0b01);
    try std.testing.expectEqualSlices(?u8, &ac.values, &exp.values);
}

test "mov with no disp_hi and w=0 conditional fixins" {
    // 1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1
    var reader = std.Io.Reader.fixed(&[_]u8{ 0b11000110, 0b01000000, 0b11110000, 0b00001111 });
    const ac = try decode(&reader);
    var exp = ParsedInstruction.initFill(null);
    exp.set(.w, 0b0);
    exp.set(.mod, 0b01);
    exp.set(.rm, 0b00);
    exp.set(.disp_lo, 0b11110000);
    exp.set(.data, 0b00001111);
    try std.testing.expectEqualSlices(?u8, &ac.values, &exp.values);
}

test "mov with all conditional fixins" {
    // 1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1
    var reader = std.Io.Reader.fixed(&[_]u8{ 0b11000111, 0b10000000, 0b11110000, 0b00001111, 0b10101010, 0b01010101 });
    const ac = try decode(&reader);
    var exp = ParsedInstruction.initFill(null);
    exp.set(.w, 0b1);
    exp.set(.mod, 0b10);
    exp.set(.rm, 0b00);
    exp.set(.disp_lo, 0b11110000);
    exp.set(.disp_hi, 0b00001111);
    exp.set(.data, 0b10101010);
    exp.set(.data_if_w_eq_1, 0b01010101);
    try std.testing.expectEqualSlices(?u8, &ac.values, &exp.values);
}
