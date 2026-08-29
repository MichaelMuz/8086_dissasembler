const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");
const disassembler = @import("disassembler.zig");

pub fn disassembleStream(reader: *std.Io.Reader, writer: *std.Io.Writer) !void {
    while (true) {
        const decoded = try decoder.decode(reader);
        const disasm: disassembler.instructions.DisasmInstr = try disassembler.disassemble.disassemble(decoded.schema, decoded.parsed);
        disasm.fmt(writer.buffer);
    }
}

test {
    _ = lexer;
    _ = decoder;
    _ = disassembler;
}
