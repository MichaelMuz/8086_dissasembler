const std = @import("std");

const _8086_dissasembler = @import("_8086_dissasembler");

pub fn main(init: std.process.Init) !void {
    const arena: std.mem.Allocator = init.arena.allocator();

    const args = try init.minimal.args.toSlice(arena);
    const input_arg = args[1];
    const output_arg = args[2];

    var in_buffer: [1024]u8 = undefined;
    var in_reader: std.Io.File.Reader =
        if (std.mem.eql(u8, input_arg, "-")) std.Io.File.stdin().reader(init.io, &in_buffer) else .init(
            try std.Io.Dir.cwd().openFile(init.io, input_arg, .{ .mode = .read_only }),
            init.io,
            &in_buffer,
        );

    var out_buffer: [1024]u8 = undefined;
    var out_writer: std.Io.File.Writer =
        if (std.mem.eql(u8, output_arg, "-")) std.Io.File.stdout().writer(init.io, &out_buffer) else .init(
            try std.Io.Dir.cwd().openFile(init.io, output_arg, .{ .mode = .write_only }),
            init.io,
            &out_buffer,
        );

    try _8086_dissasembler.disassembleStream(&in_reader.interface, &out_writer.interface);
    try out_writer.flush();
}

// hard to mock std.process.init I think unfortunately
// test "main smoke test" {
//     var reader = std.Io.Reader.fixed(&[_]u8{ 0b10001000, 0b11001000 });
//     var buf = [_]u8{undefined} ** 256;
//     var writer = std.Io.Writer.fixed(&buf);
//     try main(&reader, &writer);
//     try std.testing.expectEqualStrings("mov al, cl", writer.buffered());
// }
