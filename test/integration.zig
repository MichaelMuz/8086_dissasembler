const std = @import("std");
const _8086_dissasembler = @import("_8086_dissasembler");

const tmp = std.testing.tmpDir(.{});
var test_counter: std.atomic.Value(u32) = .init(0);

fn getBinFromNasm(asm_instructions: []const [:0]const u8, buffer: []u8) !void {
    const test_num = test_counter.fetchAdd(1, .monotonic);

    const nasm_in_file = std.fmt("{s}/{d}.asm", .{ tmp, test_num });
    const nasm_out_file = std.fmt("{s}/{d}_bin", .{ tmp, test_num });

    try tmp.dir.writeFile(std.testing.io, .{ .sub_path = nasm_in_file, .data = asm_instructions });

    std.process.run(std.testing.allocator, std.testing.io, .{ .argv = [_][]u8{ "nasm", nasm_in_file, "-o", nasm_out_file } });

    try tmp.dir.readFile(tmp, std.testing.io, nasm_out_file, buffer);
}

fn helpTestRoundTrip(asm_instructions: []const [:0]const u8) !void {
    const original_bin = [_]u8{undefined} ** 1024;
    getBinFromNasm(asm_instructions, &original_bin) catch |err| {
        std.testing.print("Nasm choked on test input.\nTest instructions: {s}\nError: {s}", .{ asm_instructions, err });
        return err;
    };

    var reader = std.Io.Reader.fixed(&asm_instructions);
    var our_disassembly = [_]u8{undefined} ** 1024;
    var writer = std.Io.Writer.fixed(&our_disassembly);
    _8086_dissasembler.disassembleStream(&reader, &writer) catch |err| {
        std.testing.print("Our disassembler choked on nasm output.\nTest instructions: {s}\nNasm's assembly: {s}\nError:{s}", .{ asm_instructions, original_bin, err });
        return err;
    };

    var bin_of_our_disassembly = [_]u8{undefined} ** 1024;
    getBinFromNasm(asm_instructions, &bin_of_our_disassembly) catch |err| {
        std.testing.print("Nasm choked on our disassembler's output.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nError:{s}", .{ asm_instructions, original_bin, our_disassembly, err });
        return err;
    };
    std.testing.expectEqualSlices(u8, original_bin, bin_of_our_disassembly) catch |err| {
        std.testing.print("Binary our our disassembly not same as binary of test instructions.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nBinary of our disassembly: {s}\nError:{s}", .{ asm_instructions, original_bin, our_disassembly, bin_of_our_disassembly, err });
    };
}
