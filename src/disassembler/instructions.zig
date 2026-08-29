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
                m.getSizeSpec(arr);
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
