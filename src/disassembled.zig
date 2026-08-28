const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");
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

// --- naturally above here is instruction types ---
// Note that a lot of stuff below here could be part of the operand type that is creating it
// also if we had a struct with the particular types filled in then we could avoid truncate bc it would know
// w is a u1. Also we could have getMode be a method which would be convenient. The enum array representation
// is fine for when we are simply jamming the numbers we found while decoding the instruction but when
// we start to use that it is a bit cumbersome as the canonical type for a decoded instruction

const ModeType = enum {
    no_displacement_mode,
    byte_displacement_mode,
    word_displacement_mode,
    register_mode,
};

const Mode = struct {
    mode: ModeType,
    direct_memory_index: bool,
};

fn getMode(extracted: *const decoder.ParsedInstruction) Mode {
    const mod_val = if (extracted.get(.mod)) |m| m else unreachable;
    return switch (mod_val) {
        0b100...std.math.maxInt(@TypeOf(mod_val)) => unreachable,
        0b00 => if (extracted.get(.rm) == 0b110) .{ .mode = .word_displacement_mode, .direct_memory_index = true } else .{ .mode = .no_displacement_mode, .direct_memory_index = false },
        0b01 => .{ .mode = .byte_displacement_mode, .direct_memory_index = false },
        0b10 => .{ .mode = .word_displacement_mode, .direct_memory_index = false },
        0b11 => .{ .mode = .register_mode, .direct_memory_index = false },
    };
}

fn getDataOperand(extracted: *const decoder.ParsedInstruction) ?operands.ImmediateOperand {
    if (extracted.get(.data)) |dl| {
        var data = [_]u8{ 0, dl };
        if (extracted.get(.data_if_w_eq_1)) |dh| {
            data = [_]u8{ dh, dl };
        }

        if (extracted.get(.w)) |w| {
            return operands.ImmediateOperand{ .value = std.mem.readInt(u16, data, .big), .word = w };
        } else unreachable;
    } else {
        return null;
    }
}

fn getRegOperand(extracted: *const decoder.ParsedInstruction) ?operands.RegisterOperand {
    if (extracted.get(.reg)) |r| {
        if (extracted.get(.w)) |w| {
            return operands.RegOperand{ .reg_ind = @truncate(r), .word = w == 1 };
        } else unreachable;
    } else if (extracted.get(.sr)) |sr| {
        return operands.SegmentRegOperand{ .reg_ind = @truncate(sr) };
    } else {
        return null;
    }
}

fn getRmOperand(extracted: *const decoder.ParsedInstruction) ?operands.RegisterOperand {
    const word = if (extracted.get(.w)) |w| w == 1 else unreachable;
    if (extracted.get(.rm)) |reg_or_mem_base| {
        const mode = getMode(extracted);
        if (mode.mode == .register_mode) {
            return operands.RegOperand{ .reg_ind = @truncate(reg_or_mem_base), .word = word };
        } else {
            const dl = extracted.get(.disp_lo) orelse 0;
            var disp = [_]u8{ 0, dl };
            if (extracted.get(.disp_hi)) |dh| {
                disp = [_]u8{ dh, dl };
            }
            return operands.MemoryOperand{ .memory_base = if (mode.direct_memory_index) null else reg_or_mem_base, .displacement = disp, .word = word };
        }
    } else {
        return null;
    }
}

const DisasmInstr = union(enum) {
    nullary_instruction: NullaryInstruction,
    unary_instruction: UnaryInstruction,
    binary_instruction: BinaryInstruction,
    jump_instruction: JumpInstruction,

    pub fn construct(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) @This() {
        if (extracted.get(.ip_inc8)) |inc_8| {
            return JumpInstruction{ .mnemonic = schema.name, .disp = @intCast(inc_8), .label = null };
        }

        const data = getDataOperand(extracted);
        const register = getRegOperand(extracted);
        const rm = getRmOperand(extracted);

        const operand_buffer = [_]@This(){undefined} ** 3;
        const op_arr = std.ArrayList(operands.Operand).initBuffer(operand_buffer);
        for ([_]operands.Operands{ data, register, rm }) |op| {
            if (op) |o| {
                op_arr.appendBounded(o);
            }
        }

        const d: u8 = @truncate(extracted.get(.d) orelse 0);

        return switch (op_arr.len) {
            0 => NullaryInstruction{ .mnemonic = schema.name },
            1 => UnaryInstruction{ .mnemonic = schema.name, .op = op_arr[0] },
            2 => BinaryInstruction{
                .mnemonic = schema.name,
                .src = op_arr[0 ^ d],
                .dst = op_arr[1 ^ d],
            },
            else => unreachable,
        };
    }
};
