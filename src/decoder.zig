const std = @import("std");
const utils = @import("utils.zig");
const lexer = @import("lexer.zig");

// TODO: maybe this this is the recognizer/matcher and the thing that does the extraction is the decoder?
const DecodeError = error{
    NoSuchInstruction,
};

fn extract(reader: *std.Io.Reader, schema: lexer.schema.InstructionSchema) !void {
    var extracted = std.EnumArray(u8, lexer.schema.NamedField);
    const curr_byte = try reader.takeByte(); // TODO: end of stream is unexpected for us. Can turn into our own 'expected more bytes error' in theory
    const next_msb: u4 = 0; // TODO can change this to u3 if I guard the additions closely
    for (schema.fields()) |f| {
        const sub_bits = utils.getSubMostSigBits(u8, curr_byte, next_msb, f.width());
        switch (f) {
            f.literal_field => if (f.literal_field.value != sub_bits) @panic("Extract called on schema with incompatible fixed fields"),
            f.named_field => extracted.set(f.named_field, sub_bits),
        }

        // TODO: something should decide if we continue or this instruction is done
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
