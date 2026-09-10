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
    const bin_of_our_disassembly = getBinFromNasm(our_disassembly, &reassembly_buf) catch |err| {
        std.debug.print("Nasm choked on our disassembler's output.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nError:{}", .{ asm_instructions, original_bin, our_disassembly, err });
        return err;
    };
    std.testing.expectEqualSlices(u8, original_bin, bin_of_our_disassembly) catch |err| {
        std.debug.print("Our disassembly not same as binary of test instructions.\nTest instructions: {s}\nNasm's assembly: {s}\nOur disassembly: {s}\nBinary of our disassembly: {s}\nError:{}", .{ asm_instructions, original_bin, our_disassembly, bin_of_our_disassembly, err });
        return err;
    };
}

test "mov completionist" {
    try testRoundTripHelper(&.{
        "mov si, bx",
        "mov dh, al",
        "mov cl, 12",
        "mov ch, -12",
        "mov cx, 12",
        "mov cx, -12",
        "mov dx, 3948",
        "mov dx, -3948",
        "mov al, [bx + si]",
        "mov bx, [bp + di]",
        "mov dx, [bp]",
        "mov ah, [bx + si + 4]",
        "mov al, [bx + si + 4999]",
        "mov [bx + di], cx",
        "mov [bp + si], cl",
        "mov [bp], ch",
        "mov ax, [bx + di - 37]",
        "mov [si - 300], cx",
        "mov dx, [bx - 32]",
        "mov [bp + di], byte 7",
        "mov [di + 901], word 347",
        "mov bp, [5]",
        "mov bx, [3458]",
        "mov ax, [2555]",
        "mov ax, [16]",
        "mov [2554], ax",
        "mov [15], ax",
    });
}

test "push completionist" {
    try testRoundTripHelper(&.{
        "push word [bp + si]",
        "push word [3000]",
        "push word [bx + di - 30]",
        "push cx",
        "push ax",
        "push dx",
        "push cs",
    });
}

test "pop completionist" {
    try testRoundTripHelper(&.{
        "pop word [bp + si]",
        "pop word [3]",
        "pop word [bx + di - 3000]",
        "pop sp",
        "pop di",
        "pop si",
        "pop ds",
    });
}

test "xchg memory" {
    try testRoundTripHelper(&.{
        "xchg ax, [bp - 1000]",
        "xchg [bx + 50], bp",
    });
}

test "xchg accumulator registers" {
    try testRoundTripHelper(&.{
        "xchg ax, ax",
        "xchg ax, dx",
        "xchg ax, sp",
        "xchg ax, si",
        "xchg ax, di",
    });
}
test "xchg general registers" {
    try testRoundTripHelper(&.{
        "xchg cx, dx",
        "xchg si, cx",
        "xchg cl, ah",
    });
}

test "in" {
    try testRoundTripHelper(&.{
        "in al, 200",
        "in al, dx",
        "in ax, dx",
    });
}

test "out" {
    try testRoundTripHelper(&.{
        "out 44, ax",
        "out dx, al",
    });
}

test "xlat and lea" {
    try testRoundTripHelper(&.{
        "xlat",
        "lea ax, [bx + di + 1420]",
        "lea bx, [bp - 50]",
        "lea sp, [bp - 1003]",
        "lea di, [bx + si - 7]",
    });
}

test "lds" {
    try testRoundTripHelper(&.{
        "lds ax, [bx + di + 1420]",
        "lds bx, [bp - 50]",
        "lds sp, [bp - 1003]",
        "lds di, [bx + si - 7]",
    });
}

test "les" {
    try testRoundTripHelper(&.{
        "les ax, [bx + di + 1420]",
        "les bx, [bp - 50]",
        "les sp, [bp - 1003]",
        "les di, [bx + si - 7]",
    });
}

test "lahf sahf pushf popf" {
    try testRoundTripHelper(&.{
        "lahf",
        "sahf",
        "pushf",
        "popf",
    });
}

test "add completionist" {
    try testRoundTripHelper(&.{
        "add cx, [bp]",
        "add dx, [bx + si]",
        "add al, [bx + si]",
        "add bh, [bp + si + 4]",
        "add [bp + di + 5000], ah",
        "add [bx], al",
        "add [bx + si], bx",
        "add sp, 392",
        "add si, 5",
        "add ax, 1000",
        "add ah, 30",
        "add al, 9",
        "add word [bp + si + 1000], 29",
        "add cx, bx",
        "add ch, al",
    });
}

test "adc" {
    try testRoundTripHelper(&.{
        "adc cx, [bp]",
        "adc dx, [bx + si]",
        "adc [bp + di + 5000], ah",
        "adc [bx], al",
        "adc sp, 392",
        "adc si, 5",
        "adc ax, 1000",
        "adc ah, 30",
        "adc al, 9",
        "adc cx, bx",
        "adc ch, al",
    });
}

test "inc" {
    try testRoundTripHelper(&.{
        "inc ax",
        "inc cx",
        "inc dh",
        "inc al",
        "inc ah",
        "inc sp",
        "inc di",
        "inc byte [bp + 1002]",
        "inc word [bx + 39]",
        "inc byte [bx + si + 5]",
        "inc word [bp + di - 10044]",
        "inc word [9349]",
        "inc byte [bp]",
    });
}

test "aaa daa" {
    try testRoundTripHelper(&.{
        "aaa",
        "daa",
    });
}

test "sub completionist" {
    try testRoundTripHelper(&.{
        "sub cx, [bp]",
        "sub dx, [bx + si]",
        "sub [bp + di + 5000], ah",
        "sub [bx], al",
        "sub sp, 392",
        "sub si, 5",
        "sub ax, 1000",
        "sub ah, 30",
        "sub al, 9",
        "sub word [bx + di], 29",
        "sub cx, bx",
        "sub ch, al",
    });
}

test "sbb" {
    try testRoundTripHelper(&.{
        "sbb cx, [bp]",
        "sbb dx, [bx + si]",
        "sbb [bp + di + 5000], ah",
        "sbb [bx], al",
        "sbb sp, 392",
        "sbb si, 5",
        "sbb ax, 1000",
        "sbb ah, 30",
        "sbb al, 9",
        "sbb cx, bx",
        "sbb ch, al",
    });
}

test "dec" {
    try testRoundTripHelper(&.{
        "dec ax",
        "dec cx",
        "dec dh",
        "dec al",
        "dec ah",
        "dec sp",
        "dec di",
        "dec byte [bp + 1002]",
        "dec word [bx + 39]",
        "dec byte [bx + si + 5]",
        "dec word [bp + di - 10044]",
        "dec word [9349]",
        "dec byte [bp]",
    });
}

test "neg" {
    try testRoundTripHelper(&.{
        "neg ax",
        "neg cx",
        "neg dh",
        "neg al",
        "neg ah",
        "neg sp",
        "neg di",
        "neg byte [bp + 1002]",
        "neg word [bx + 39]",
        "neg byte [bx + si + 5]",
        "neg word [bp + di - 10044]",
        "neg word [9349]",
        "neg byte [bp]",
    });
}

test "cmp completionist" {
    try testRoundTripHelper(&.{
        "cmp bx, cx",
        "cmp dh, [bp + 390]",
        "cmp [bp + 2], si",
        "cmp bl, 20",
        "cmp byte [bx], 34",
        "cmp si, 2",
        "cmp al, -30",
        "cmp word [4834], 29",
        "cmp ax, 23909",
    });
}

test "aas das" {
    try testRoundTripHelper(&.{
        "aas",
        "das",
    });
}

test "mul" {
    try testRoundTripHelper(&.{
        "mul al",
        "mul cx",
        "mul word [bp]",
        "mul byte [bx + di + 500]",
    });
}

test "imul" {
    try testRoundTripHelper(&.{
        "imul ch",
        "imul dx",
        "imul byte [bx]",
        "imul word [9483]",
    });
}

test "aam" {
    try testRoundTripHelper(&.{"aam"});
}

test "div" {
    try testRoundTripHelper(&.{
        "div bl",
        "div sp",
        "div byte [bx + si + 2990]",
        "div word [bp + di + 1000]",
    });
}

test "idiv" {
    try testRoundTripHelper(&.{
        "idiv ax",
        "idiv si",
        "idiv byte [bp + si]",
        "idiv word [bx + 493]",
    });
}

test "aad cbw cwd" {
    try testRoundTripHelper(&.{
        "aad",
        "cbw",
        "cwd",
    });
}

test "not" {
    try testRoundTripHelper(&.{
        "not ah",
        "not bl",
        "not sp",
        "not si",
        "not word [bp]",
        "not byte [bp + 9905]",
    });
}

test "shift rotate by one registers" {
    try testRoundTripHelper(&.{
        "shl ah, 1",
        "shr ax, 1",
        "sar bx, 1",
        "rol cx, 1",
        "ror dh, 1",
        "rcl sp, 1",
        "rcr bp, 1",
    });
}

test "shift rotate by one memory" {
    try testRoundTripHelper(&.{
        "shl word [bp + 5], 1",
        "shr byte [bx + si - 199], 1",
        "sar byte [bx + di - 300], 1",
        "rol word [bp], 1",
        "ror word [4938], 1",
        "rcl byte [3], 1",
        "rcr word [bx], 1",
    });
}

test "shift rotate by cl registers" {
    try testRoundTripHelper(&.{
        "shl ah, cl",
        "shr ax, cl",
        "sar bx, cl",
        "rol cx, cl",
        "ror dh, cl",
        "rcl sp, cl",
        "rcr bp, cl",
    });
}

test "shift rotate by cl memory" {
    try testRoundTripHelper(&.{
        "shl word [bp + 5], cl",
        "shr word [bx + si - 199], cl",
        "sar byte [bx + di - 300], cl",
        "rol byte [bp], cl",
        "ror byte [4938], cl",
        "rcl byte [3], cl",
        "rcr word [bx], cl",
    });
}

test "and" {
    try testRoundTripHelper(&.{
        "and al, ah",
        "and ch, cl",
        "and bp, si",
        "and di, sp",
        "and al, 93",
        "and ax, 20392",
        "and [bp + si + 10], ch",
        "and [bx + di + 1000], dx",
        "and bx, [bp]",
        "and cx, [4384]",
        "and byte [bp - 39], 239",
        "and word [bx + si - 4332], 10328",
    });
}

test "test" {
    try testRoundTripHelper(&.{
        "test bx, cx",
        "test dh, [bp + 390]",
        "test [bp + 2], si",
        "test bl, 20",
        "test byte [bx], 34",
        "test ax, 23909",
    });
}

test "or" {
    try testRoundTripHelper(&.{
        "or al, ah",
        "or ch, cl",
        "or bp, si",
        "or di, sp",
        "or al, 93",
        "or ax, 20392",
        "or [bp + si + 10], ch",
        "or [bx + di + 1000], dx",
        "or bx, [bp]",
        "or cx, [4384]",
        "or byte [bp - 39], 239",
        "or word [bx + si - 4332], 10328",
    });
}

test "xor" {
    try testRoundTripHelper(&.{
        "xor al, ah",
        "xor ch, cl",
        "xor bp, si",
        "xor di, sp",
        "xor al, 93",
        "xor ax, 20392",
        "xor [bp + si + 10], ch",
        "xor [bx + di + 1000], dx",
        "xor bx, [bp]",
        "xor cx, [4384]",
        "xor byte [bp - 39], 239",
        "xor word [bx + si - 4332], 10328",
    });
}

test "rep string operations" {
    try testRoundTripHelper(&.{
        "rep movsb",
        "rep cmpsb",
        "rep scasb",
        "rep lodsb",
        "rep movsw",
        "rep cmpsw",
        "rep scasw",
        "rep lodsw",
    });
}

test "rep stos" {
    try testRoundTripHelper(&.{
        "rep stosb",
        "rep stosw",
    });
}

test "indirect call" {
    try testRoundTripHelper(&.{
        "call [39201]",
        "call [bp - 100]",
        "call sp",
        "call ax",
    });
}

test "indirect jmp" {
    try testRoundTripHelper(&.{
        "jmp ax",
        "jmp di",
        "jmp [12]",
        "jmp [4395]",
    });
}

test "ret immediate and plain" {
    try testRoundTripHelper(&.{
        "ret -7",
        "ret 500",
        "ret",
    });
}

test "conditional jumps and loops completionist" {
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
        "jne label",
        "jnl label",
        "jg label",
        "jnb label",
        "ja label",
        "jnp label",
        "jno label",
        "jns label",
        "loop label",
        "loopz label",
        "loopnz label",
        "jcxz label",
    });
}

test "int" {
    try testRoundTripHelper(&.{
        "int 13",
        "int3",
    });
}

test "into iret" {
    try testRoundTripHelper(&.{
        "into",
        "iret",
    });
}

test "flag control halt wait" {
    try testRoundTripHelper(&.{
        "clc",
        "cmc",
        "stc",
        "cld",
        "std",
        "cli",
        "sti",
        "hlt",
        "wait",
    });
}

test "lock" {
    try testRoundTripHelper(&.{
        "lock not byte [bp + 9905]",
        "lock xchg [100], al",
    });
}

test "mov segment overrides" {
    try testRoundTripHelper(&.{
        "mov al, cs:[bx + si]",
        "mov bx, ds:[bp + di]",
        "mov dx, es:[bp]",
        "mov ah, ss:[bx + si + 4]",
    });
}

test "alu segment overrides" {
    try testRoundTripHelper(&.{
        "and ss:[bp + si + 10], ch",
        "or ds:[bx + di + 1000], dx",
        "xor bx, es:[bp]",
        "cmp cx, es:[4384]",
        "test byte cs:[bp - 39], 239",
        "sbb word cs:[bx + si - 4332], 10328",
    });
}

test "lock segment override" {
    try testRoundTripHelper(&.{"lock not byte CS:[bp + 9905]"});
}

test "far direct call and jmp" {
    try testRoundTripHelper(&.{
        "call 123:456",
        "jmp 789:34",
    });
}

test "mov segment register to memory" {
    try testRoundTripHelper(&.{"mov [bx+si+59],es"});
}

test "near direct jmp and call" {
    try testRoundTripHelper(&.{
        "jmp 2620",
        "call 11804",
    });
}

test "retf and ret" {
    try testRoundTripHelper(&.{
        "retf 17556",
        "ret 17560",
        "retf",
        "ret",
    });
}

test "near and far indirect call and jmp" {
    try testRoundTripHelper(&.{
        "call [bp+si-0x3a]",
        "call far [bp+si-0x3a]",
        "jmp [di]",
        "jmp far [di]",
    });
}

test "far direct jmp" {
    try testRoundTripHelper(&.{"jmp 21862:30600"});
}

test "additional mov cases" {
    try testRoundTripHelper(&.{
        "mov ax, 100",
        "mov bh, 12",
        "mov bh, [bp]",
        "mov ax, ds",
        "mov ds, ax",
        "mov es, bx",
        "mov cx, ss",
    });
}

test "relative jumps without labels" {
    try testRoundTripHelper(&.{
        "jne $ + 3",
        "jne $ - 3",
    });
}
