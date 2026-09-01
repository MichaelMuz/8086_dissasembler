const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");
const disassembler = @import("disassembler.zig");

pub fn disassembleStream(reader: *std.Io.Reader, writer: *std.Io.Writer) !void {
    // I realize that I made everything write to an arraylist but really shoulda just been to some interface so now coupled to arraylist
    var buf = [_]u8{undefined} ** 128;
    var arr = std.ArrayList(u8).initBuffer(&buf);
    while (true) {
        arr.clearRetainingCapacity();
        const decoded = decoder.decode(reader) catch |err| switch (err) {
            error.EndOfStream => break,
            error.ReadFailed => return err,
            error.InvalidInstruction => return err,
        };
        const disasm: disassembler.instructions.DisasmInstr = disassembler.disassemble.disassemble(decoded.schema, &decoded.parsed);
        disasm.fmt(&arr);
        try writer.writeAll(arr.items);
    }
}

test "wired up smoke test" {
    var reader = std.Io.Reader.fixed(&[_]u8{ 0b10001000, 0b11001000 });
    var buf = [_]u8{undefined} ** 256;
    var writer = std.Io.Writer.fixed(&buf);
    try disassembleStream(&reader, &writer);
    try std.testing.expectEqualStrings("mov al, cl", writer.buffered());
}

test {
    _ = lexer;
    _ = decoder;
    _ = disassembler;
}
