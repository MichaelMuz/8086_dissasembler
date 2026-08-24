const std = @import("std");
const utils = @import("utils.zig");
const lexer = @import("lexer.zig");

// TODO: maybe this this is the recognizer/matcher and the thing that does the extraction is the decoder?
const DecodeError = error{
    NoSuchInstruction,
};

// fn should_take(field: lexer.schema.SchemaField){

// }

fn extract(reader: *std.Io.Reader, schema: lexer.schema.InstructionSchema) !void {
    var extracted = std.EnumArray(u8, lexer.schema.NamedField);
    const curr_byte = try reader.takeByte(); // TODO: end of stream is unexpected for us. Can turn into our own 'expected more bytes error' in theory
    const next_msb: u4 = 0; // TODO can change this to u3 if I guard the additions closely
    for (schema.fields()) |f| {
        const sub_bits = utils.getSubMostSigBits(u8, curr_byte, next_msb, f.width());
        const named_field = switch (f) {
            f.literal_field => if (f.literal_field.value == sub_bits) continue else unreachable,
            f.named_field => f.named_field,
        };

        const should_take = switch (named_field) |nf| {
            .d => true,
            .w => true,
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

        return extract(reader, matched_schema);
    }
}
