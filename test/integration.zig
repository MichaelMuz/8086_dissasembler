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

test "mov reg to reg" {
    try testRoundTripHelper(&.{"mov cx, bx"});
}
test "mov many reg to reg" {
    try testRoundTripHelper(&.{
        "mov cx, bx",
        "mov ch, ah",
        "mov dx, bx",
        "mov bx, di",
        "mov al, cl",
        "mov ch, ch",
        "mov bx, ax",
        "mov bx, si",
        "mov sp, di",
        "mov bp, ax",
        "mov si, bx",
        "mov dh, al",
    });
}
test "mov 8bit immediate to register" {
    try testRoundTripHelper(&.{"mov bh, 12"});
}
test "mov many 8bit immediate to register" {
    try testRoundTripHelper(&.{ "mov cl, 12", "mov ch, -12" });
}
test "mov 16bit immediate to register" {
    try testRoundTripHelper(&.{"mov ax, 100"});
}
test "mov many 16bit immediate to register" {
    try testRoundTripHelper(&.{ "mov cx, 12", "mov cx, -12", "mov dx, 3948", "mov dx, -3948" });
}
test "mov source address calculation single var" {
    try testRoundTripHelper(&.{"mov bh, [bp]"});
}
test "mov source address calculation double var" {
    try testRoundTripHelper(&.{"mov bh, [bp]"});
}
test "mov many source address calculation" {
    try testRoundTripHelper(&.{
        "mov al, [bx + si]",
        "mov bx, [bp + di]",
        "mov dx, [bp]",
    });
}
test "mov source address with 8bit displacement" {
    try testRoundTripHelper(&.{"mov ah, [bx + si + 4]"});
}
test "mov source address with 16bit displacement" {
    try testRoundTripHelper(&.{"mov al, [bx + si + 4999]"});
}
test "mov dest address calculation" {
    try testRoundTripHelper(&.{ "mov [bx + di], cx", "mov [bp + si], cl", "mov [bp], ch" });
}
test "mov signed displacement" {
    try testRoundTripHelper(&.{"mov ax, [bx + di - 37]"});
}
test "mov signed displacements" {
    try testRoundTripHelper(&.{ "mov ax, [bx + di - 37]", "mov [si - 300], cx", "mov dx, [bx - 32]" });
}
test "mov explicit size" {
    try testRoundTripHelper(&.{"mov [di + 901], word 347"});
}
test "mov explicit sizes" {
    try testRoundTripHelper(&.{ "mov [bp + di], byte 7", "mov [di + 901], word 347" });
}
test "mov direct address" {
    try testRoundTripHelper(&.{"mov bp, [5]"});
}
test "mov direct addresses" {
    try testRoundTripHelper(&.{ "mov bp, [5]", "mov bx, [3458]" });
}
test "mov memory to accumulator" {
    try testRoundTripHelper(&.{"mov ax, [2555]"});
}
test "mov memory to accumulators" {
    try testRoundTripHelper(&.{ "mov ax, [2555]", "mov ax, [16]" });
}
test "mov accumulator to memory" {
    try testRoundTripHelper(&.{"mov [2554], ax"});
}
test "mov accumulator to memories" {
    try testRoundTripHelper(&.{ "mov [2554], ax", "mov [15], ax" });
}
test "mov segment register" {
    try testRoundTripHelper(&.{"mov ax, ds"});
}
test "mov segment register2" {
    try testRoundTripHelper(&.{"mov ds, ax"});
}
test "mov segment registers" {
    try testRoundTripHelper(&.{
        "mov ax, ds",
        "mov ds, ax",
        "mov es, bx",
        "mov cx, ss",
    });
}

test "sub reg from memory" {
    try testRoundTripHelper(&.{"sub bx, [bp]"});
}
test "sub regs from memory" {
    try testRoundTripHelper(&.{ "sub bx, [bx+si]", "sub bx, [bp]" });
}
test "sub immediate from reg" {
    try testRoundTripHelper(&.{ "sub si, 2", "sub bp, 2", "sub cx, 8" });
}
test "sub reg from memory with displacement" {
    try testRoundTripHelper(&.{
        "sub bx, [bp + 0]",
        "sub cx, [bx + 2]",
        "sub bh, [bp + si + 4]",
        "sub di, [bp + di + 6]",
    });
}
test "sub reg from memory dest" {
    try testRoundTripHelper(&.{
        "sub [bx+si], bx",
        "sub [bp], bx",
        "sub [bp + 0], bx",
        "sub [bx + 2], cx",
        "sub [bp + si + 4], bh",
        "sub [bp + di + 6], di",
    });
}
test "sub immediate from memory" {
    try testRoundTripHelper(&.{ "sub byte [bx], 34", "sub word [bx + di], 29" });
}
test "sub mixed operations" {
    try testRoundTripHelper(&.{ "sub ax, [bp]", "sub al, [bx + si]", "sub ax, bx", "sub al, ah" });
}
test "sub immediate values" {
    try testRoundTripHelper(&.{ "sub ax, 1000", "sub al, -30", "sub al, 9" });
}

test "add reg from memory" {
    try testRoundTripHelper(&.{ "add bx, [bx+si]", "add bx, [bp]" });
}
test "add immediate to reg" {
    try testRoundTripHelper(&.{ "add si, 2", "add bp, 2", "add cx, 8" });
}
test "add reg from memory with displacement" {
    try testRoundTripHelper(&.{
        "add bx, [bp + 0]",
        "add cx, [bx + 2]",
        "add bh, [bp + si + 4]",
        "add di, [bp + di + 6]",
    });
}
test "add reg to memory" {
    try testRoundTripHelper(&.{
        "add [bx+si], bx",
        "add [bp], bx",
        "add [bp + 0], bx",
        "add [bx + 2], cx",
        "add [bp + si + 4], bh",
        "add [bp + di + 6], di",
    });
}
test "add immediate to memory" {
    try testRoundTripHelper(&.{ "add byte [bx], 34", "add word [bp + si + 1000], 29" });
}
test "add mixed operations" {
    try testRoundTripHelper(&.{ "add ax, [bp]", "add al, [bx + si]", "add ax, bx", "add al, ah" });
}
test "add immediate values" {
    try testRoundTripHelper(&.{ "add ax, 1000", "add al, -30", "add al, 9" });
}

test "cmp reg with memory" {
    try testRoundTripHelper(&.{ "cmp bx, [bx+si]", "cmp bx, [bp]" });
}
test "cmp reg with immediate" {
    try testRoundTripHelper(&.{ "cmp si, 2", "cmp bp, 2", "cmp cx, 8" });
}
test "cmp reg with memory displacement" {
    try testRoundTripHelper(&.{
        "cmp bx, [bp + 0]",
        "cmp cx, [bx + 2]",
        "cmp bh, [bp + si + 4]",
        "cmp di, [bp + di + 6]",
    });
}
test "cmp memory with reg" {
    try testRoundTripHelper(&.{
        "cmp [bx+si], bx",
        "cmp [bp], bx",
        "cmp [bp + 0], bx",
        "cmp [bx + 2], cx",
        "cmp [bp + si + 4], bh",
        "cmp [bp + di + 6], di",
    });
}
test "cmp memory with immediate" {
    try testRoundTripHelper(&.{ "cmp byte [bx], 34", "cmp word [4834], 29" });
}
test "cmp mixed operations" {
    try testRoundTripHelper(&.{ "cmp ax, [bp]", "cmp al, [bx + si]", "cmp ax, bx", "cmp al, ah" });
}
test "cmp immediate values" {
    try testRoundTripHelper(&.{ "cmp ax, 1000", "cmp al, -30", "cmp al, 9" });
}

test "jumps jnz instructions" {
    try testRoundTripHelper(&.{
        "test_label0:",
        "jnz test_label1",
        "jnz test_label0",
        "test_label1:",
        "jnz test_label0",
        "jnz test_label1",
    });
}
test "jumps conditional jumps" {
    try testRoundTripHelper(&.{
        "label:",
        "je label",
        "jl label",
        "jle label",
        "jb label",
        "jbe label",
        "jp label",
        "jo label",
        "js label",
    });
}
test "jumps negative conditional jumps" {
    try testRoundTripHelper(&.{
        "label:",
        "jne label",
        "jnl label",
        "jg label",
        "jnb label",
        "ja label",
        "jnp label",
        "jno label",
        "jns label",
    });
}
test "jumps loop instructions" {
    try testRoundTripHelper(&.{ "label:", "loop label", "loopz label", "loopnz label", "jcxz label" });
}

test "push" {
    try testRoundTripHelper(&.{"push word [3000]"});
}
test "pushes" {
    try testRoundTripHelper(&.{
        "push word [bp + si]",
        "push word [3000]",
        "push word [bx + di - 30]",
        "push cx",
        "push ax",
        "push dx",
    });
}

test "pop" {
    try testRoundTripHelper(&.{"pop sp"});
}
test "pops" {
    try testRoundTripHelper(&.{
        "pop word [bp + si]",
        "pop word [3]",
        "pop word [bx + di - 3000]",
        "pop sp",
        "pop di",
        "pop si",
    });
}
