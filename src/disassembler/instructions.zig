const std = @import("std");
const lexer = @import("../lexer.zig");
const decoder = @import("../decoder.zig");
const operands = @import("operands.zig");

const NullaryInstruction = struct {
    mnemonic: []const u8,
    // inst_size: u8, this is for when jumps need to calculate their offsets

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        arr.printBounded("{s}", .{self.mnemonic});
    }
};

const UnaryInstruction = struct {
    mnemonic: []const u8,
    op: operands.Operand,
    // inst_size: u8, this is for when jumps need to calculate their offsets

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        // "{self.mnemonic} {size_spec}{self.op}"

        arr.printBounded("{s} ", .{self.mnemonic});
        if (self.op == .memory_operand) |m| {
            arr.printBounded("{s} ", .{m.getSizeSpec()});
        }
        arr.printBounded("{d}", self.op.fmt());
    }
};

const BinaryInstruction = struct {
    mnemonic: []const u8,
    dst: operands.Operand,
    src: operands.Operand,
    // inst_size: u8, this is for when jumps need to calculate their offsets

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        // "{self.mnemonic} {self.dest}, {size_spec}{self.source}"

        arr.printBounded("{s} ", .{self.mnemonic});
        self.dst.fmt(arr);
        arr.printBounded(", ", .{});
        if (self.src == .immediate_operand) {
            if (self.dst == .memory_operand) |m| {
                arr.printBounded("{s}", .{m.getSizeSpec(arr)});
            }
        }
        arr.printBounded("{s}", .{self.src.fmt()});
    }
};

const JumpInstruction = struct {
    mnemonic: []const u8,
    disp: i16,
    // inst_size: u8, this is for when jumps need to calculate their offsets
    label: ?[]const u8,

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        // "{self.mnemonic} {destination}"

        if (self.label) |l| {
            arr.printBounded("{s}", .{l});
        } else {
            arr.printBounded("{s}", .{self.disp});
        }
    }

    // pub fn getAbsLabelOffset(self: *@This(), curr_byte_ind: anytype) @TypeOf(curr_byte_ind) {
    //     return curr_byte_ind + self.inst_size + self.dip;
    // }
};

const DisasmInstr = union(enum) {
    nullary_instruction: NullaryInstruction,
    unary_instruction: UnaryInstruction,
    binary_instruction: BinaryInstruction,
    jump_instruction: JumpInstruction,

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        return switch (self) {
            inline else => |inst| inst.fmt(arr),
        };
    }
};

fn test_fmt_helper(expected: []const u8, actual: anytype) !void {
    var buf = [_]u8{0} ** 64;
    var arr = std.ArrayList(u8).initBuffer(&buf);
    actual.fmt(&arr);
    try std.testing.expectEqualStrings(expected, arr.items);
}

test "nullary instruction" {
    try test_fmt_helper("nul", &NullaryInstruction{ .mnemonic = "nul" });
}

test "unary instruction register operand" {
    try test_fmt_helper("unar ax", &UnaryInstruction{ .mnemonic = "unar", .op = operands.Operand{ .register_operand = .{ .reg_operand = .{ .reg_ind = 1, .word = true } } } });
}
test "unary instruction memory operand byte" {
    try test_fmt_helper("unar byte [bx + si + 200]", &UnaryInstruction{ .mnemonic = "unar", .op = operands.Operand{ .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = false } } });
}
test "unary instruction memory operand word" {
    try test_fmt_helper("unar word [bx + si + 200]", &UnaryInstruction{ .mnemonic = "unar", .op = operands.Operand{ .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = true } } });
}

test "binary instruction mem to reg" {
    try test_fmt_helper("binar cx, [bx + si + 200]", &BinaryInstruction{
        .mnemonic = "binar",
        .src = operands.Operand{
            .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = true },
        },
        .dst = .{
            .register_operand = .{ .reg_operand = .{ .reg_ind = 3, .word = true } },
        },
    });
}
test "binary instruction immediate to reg" {
    try test_fmt_helper("binar cl, 5", &BinaryInstruction{
        .mnemonic = "binar",
        .src = operands.Operand{
            .immediate_operand = .{ .value = 5, .word = false },
        },
        .dst = .{
            .register_operand = .{ .reg_operand = .{ .reg_ind = 3, .word = false } },
        },
    });
}
test "binary instruction immediate to mem byte" {
    try test_fmt_helper("binar [bx + si + 200], byte 5", &BinaryInstruction{
        .mnemonic = "binar",
        .src = operands.Operand{
            .immediate_operand = .{ .value = 5, .word = false },
        },
        .dst = operands.Operand{
            .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = false },
        },
    });
}
test "binary instruction immediate to mem word" {
    try test_fmt_helper("binar [bx + si + 200], word 5", &BinaryInstruction{
        .mnemonic = "binar",
        .src = operands.Operand{
            .immediate_operand = .{ .value = 5, .word = true },
        },
        .dst = operands.Operand{
            .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = true },
        },
    });
}

test "jump instruction no label" {
    const jmp = &JumpInstruction{ .mnemonic = "jmp", .disp = "5", .label = null };
    try test_fmt_helper("jmp 5", &jmp);
}
test "jump instruction with label" {
    const jmp = &JumpInstruction{ .mnemonic = "jmp", .disp = "5", .label = null };
    try test_fmt_helper("jmp lab", &jmp);
}

test "disasm nullary" {
    try test_fmt_helper("nul", &DisasmInstr{ .nullary_instruction = .{ .mnemonic = "nul" } });
}
test "disasm unary" {
    try test_fmt_helper("unar ax", &DisasmInstr{ .unary_instruction = .{ .mnemonic = "unar", .op = operands.Operand{ .register_operand = .{ .reg_operand = .{ .reg_ind = 1, .word = true } } } } });
}
test "disasm binary" {
    try test_fmt_helper("binar cx, [bx + si + 200]", &DisasmInstr{ .binary_instruction = .{
        .mnemonic = "binar",
        .src = operands.Operand{
            .memory_operand = .{ .memory_base = 0, .displacement = 200, .word = true },
        },
        .dst = .{
            .register_operand = .{ .reg_operand = .{ .reg_ind = 3, .word = true } },
        },
    } });
}
test "disasm jump" {
    try test_fmt_helper("jmp lab", &DisasmInstr{ .jump_instruction = .{ .mnemonic = "jmp", .disp = "5", .label = null } });
}
