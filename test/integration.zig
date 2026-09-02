const std = @import("std");
const _8086_dissasembler = @import("_8086_dissasembler");

const tmp_name: [:0]const u8 = "/tmp/8086";
var test_counter: std.atomic.Value(u32) = .init(0);

fn getBinFromNasm(asm_instructions: []const u8, buffer: []u8) ![]const u8 {
    try std.Io.Dir.cwd().createDirPath(std.testing.io, tmp_name);
    const tmp_dir = try std.Io.Dir.openDirAbsolute(std.testing.io, tmp_name, .{});
    defer tmp_dir.close(std.testing.io);

    const test_num = test_counter.fetchAdd(1, .monotonic);

    var in_file_name_buf = [_]u8{undefined} ** 256;
    const nasm_in_file = try std.fmt.bufPrint(&in_file_name_buf, "{s}/{d}.asm", .{ tmp_name, test_num });
    var out_file_name_buf = [_]u8{undefined} ** 256;
    const nasm_out_file = try std.fmt.bufPrint(&out_file_name_buf, "{s}/{d}_bin", .{ tmp_name, test_num });

    try tmp_dir.writeFile(std.testing.io, .{ .sub_path = nasm_in_file, .data = asm_instructions });

    _ = try std.process.run(std.testing.allocator, std.testing.io, .{ .argv = &.{ "nasm", nasm_in_file, "-o", nasm_out_file } });

    const nasm_out = try tmp_dir.readFile(std.testing.io, nasm_out_file, buffer);
    return nasm_out;
}

fn testRoundTripHelper(asm_instructions_slc: []const [:0]const u8) !void {
    const asm_instructions_no_header = try std.mem.join(std.testing.allocator, "\n", asm_instructions_slc);
    defer std.testing.allocator.free(asm_instructions_no_header);
    const asm_instructions = try std.fmt.allocPrint(std.testing.allocator, "bits 16\n{s}\n", .{asm_instructions_no_header});
    defer std.testing.allocator.free(asm_instructions);

    var orig_bin_buf = [_]u8{undefined} ** 1024;
    const original_bin = getBinFromNasm(asm_instructions, &orig_bin_buf) catch |err| {
        std.debug.print("Nasm choked on test input.\nTest instructions:\n{s}\nError: {}", .{ asm_instructions, err });
        return err;
    };

    // std.debug.print("Nasm gave binary.\nTest instructions:\n{s}\n", .{asm_instructions});

    var disassember_buf = [_]u8{undefined} ** 1024;
    var reader = std.Io.Reader.fixed(original_bin);
    var writer = std.Io.Writer.fixed(&disassember_buf);
    _8086_dissasembler.disassembleStream(&reader, &writer) catch |err| {
        std.debug.print("Our disassembler choked on nasm output.\nTest instructions:\n{s}\nNasm's assembly: {s}\nError:{}", .{ asm_instructions, original_bin, err });
        return err;
    };
    const our_disassembly = writer.buffered();

    var reassembly_buf = [_]u8{undefined} ** 1024;
    const bin_of_our_disassembly = getBinFromNasm(asm_instructions, &reassembly_buf) catch |err| {
        std.debug.print("Nasm choked on our disassembler's output.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nError:{}", .{ asm_instructions, original_bin, our_disassembly, err });
        return err;
    };
    std.testing.expectEqualSlices(u8, original_bin, bin_of_our_disassembly) catch |err| {
        std.debug.print("Binary our our disassembly not same as binary of test instructions.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nBinary of our disassembly: {s}\nError:{}", .{ asm_instructions, original_bin, our_disassembly, bin_of_our_disassembly, err });
    };
}

test "reg to reg" {
    try testRoundTripHelper(&.{"mov cx, bx"});
}
