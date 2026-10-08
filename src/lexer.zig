pub const schema = @import("lexer/schema.zig");
pub const parser = @import("lexer/parser.zig");
pub const encodings = @import("lexer/encodings.zig");

test {
    _ = schema;
    _ = parser;
    _ = encodings;
}
