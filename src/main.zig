const std = @import("std");

const _8086_dissasembler = @import("_8086_dissasembler");

pub fn main(init: std.process.Init) !void {
    const arena: std.mem.Allocator = init.arena.allocator();

    const args = try init.minimal.args.toSlice(arena);
    const input_arg = args[0];
    const output_arg = args[1];

    const in_file =
        if (std.mem.eql(u8, &input_arg, "-")) std.fs.File.stdin() else try std.Io.Dir.cwd().openFile(std.Io, &input_arg, .{ .mode = .read_only });

    const out_file =
        if (std.mem.eql(u8, &output_arg, "-")) std.fs.File.stdout() else try std.Io.Dir.cwd().openFile(std.Io, &output_arg, .{ .mode = .write_only });

    var in_buffer: [1024]u8 = undefined;
    var in_file_reader: std.Io.File.Reader = .init(in_file, std.io, &in_buffer);
    const in_reader = &in_file_reader.interface;

    var out_buffer: [1024]u8 = undefined;
    var out_file_writer: std.Io.File.Writer = .init(out_file, std.io, &out_buffer);
    const out_writer = &out_file_writer.interface;

    try _8086_dissasembler.disassembleStream(&in_reader, &out_writer);
}

// hard to mock std.process.init I think unfortunately
// test "main smoke test" {
//     var reader = std.Io.Reader.fixed(&[_]u8{ 0b10001000, 0b11001000 });
//     var buf = [_]u8{undefined} ** 256;
//     var writer = std.Io.Writer.fixed(&buf);
//     try main(&reader, &writer);
//     try std.testing.expectEqualStrings("mov al, cl", writer.buffered());
// }
