const std = @import("std");
const utils = @import("utils.zig");
const lexer = @import("lexer.zig");

const DecodeError = error{
    NoSuchInstruction,
};

fn calcDisp(extracted: *const std.EnumArray(lexer.schema.NamedField, ?u8)) enum { none, one_byte, two_bytes } {
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

fn shouldTake(extracted: *const std.EnumArray(lexer.schema.NamedField, ?u8), curr_field: *const lexer.schema.InstructionSchema) bool {
    return switch (curr_field) {
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
            .disp_lo => calcDisp(&extracted) != .none,
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

fn extract(reader: *std.Io.Reader, schema: *const lexer.schema.InstructionSchema) !void {
    var extracted = std.EnumArray(lexer.schema.NamedField, ?u8).initFill(null);
    const next_msb: u3 = 0;

    for (schema.fields()) |f| {
        if (!shouldTake(extracted, f)) break;

        const curr_byte = reader.takeByte() catch |err| switch (err) {
            error.EndOfStream => error.InvalidInstruction,
            error.ReadFailed => err,
        };

        const sub_bits = utils.getSubMostSigBits(u8, curr_byte, next_msb, f.width());

        switch (f) {
            f.literal_field => |l| if (l.value == sub_bits) continue else unreachable,
            f.named_field => |n| extracted.set(n, sub_bits),
        }

        if (next_msb + f.width() > 8) unreachable;
        next_msb +% f.width();
    }
}

pub fn decode(reader: *std.Io.Reader) !void {
    while (true) {
        const peeked_bytes = reader.peek(2) catch |err| switch (err) {
            error.EndOfStream => (reader.peek(1) catch |inner_err| switch (inner_err) {
                error.EndOfStream => return,
                error.ReadFailed => return inner_err,
            }),
            error.ReadFailed => return err,
        };

        var stamp: u16 = 0;
        var stamp_is_one_byte: bool = undefined;
        if (peeked_bytes.len == 1) {
            stamp_is_one_byte = true;
            stamp = utils.insertBits(u16, stamp, 0, peeked_bytes[0], 8);
        } else {
            stamp_is_one_byte = false;
            stamp = std.mem.readInt(u16, &peeked_bytes, .big);
        }

        const matched_schema: lexer.schema.InstructionSchema = for (lexer.encodings.instruction_encodings) |e| {
            if (stamp_is_one_byte and !e.isOneByteIdentified()) continue;
            if (e.matches(stamp)) {
                break e;
            }
        } else return error.NoSuchInstruction;

        return extract(reader, &matched_schema);
    }
}
