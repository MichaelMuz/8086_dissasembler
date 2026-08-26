const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");

pub fn formatInst(schema: lexer.schema.NamedField, extracted: *const decoder.ParsedInstruction) []u8 {
    _ = schema;
    _ = extracted;
}
