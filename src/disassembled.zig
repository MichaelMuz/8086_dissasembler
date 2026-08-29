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

const DisasmInstr = union(enum) {
    nullary_instruction: NullaryInstruction,
    unary_instruction: UnaryInstruction,
    binary_instruction: BinaryInstruction,
    jump_instruction: JumpInstruction,

    pub fn fmt(self: *@This(), arr: *std.ArrayList(u8)) void {
        return switch (self) {
            inline else => self.fmt(arr),
        };
    }
};

// --- naturally above here is instruction types ---

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

fn getMode(mod: ?u2, rm: ?u3) ?Mode {
    if ((mod == null) ^ (rm == null)) {
        // either have both or missing both
        unreachable;
    }

    const m = mod orelse return null;
    const r = rm orelse return null;

    return switch (m) {
        0b00 => if ((r) == 0b110) .{ .mode = .word_displacement_mode, .direct_memory_index = true } else .{ .mode = .no_displacement_mode, .direct_memory_index = false },
        0b01 => .{ .mode = .byte_displacement_mode, .direct_memory_index = false },
        0b10 => .{ .mode = .word_displacement_mode, .direct_memory_index = false },
        0b11 => .{ .mode = .register_mode, .direct_memory_index = false },
    };
}

fn getDataOperand(hasData: bool, data: u16, word: bool) ?operands.ImmediateOperand {
    if (hasData) {
        return operands.ImmediateOperand{ .value = data, .word = word };
    } else {
        return null;
    }
}

fn getRegOperand(reg: ?u3, sr: ?u2, word: bool) ?operands.RegisterOperand {
    if (reg) |r| {
        return operands.RegOperand{ .reg_ind = r, .word = word };
    } else if (sr) |s| {
        return operands.SegmentRegOperand{ .reg_ind = s };
    } else {
        return null;
    }
}

fn getRmOperand(rm: ?u3, mode: ?Mode, word: bool, disp: u16) ?operands.RegisterOperand {
    const m = mode orelse return null; // can't have rm operand without mode

    if (rm) |reg_or_mem_base| {
        if (m.mode == .register_mode) {
            return operands.RegOperand{ .reg_ind = reg_or_mem_base, .word = word };
        } else {
            return operands.MemoryOperand{
                .memory_base = if (m.direct_memory_index) null else reg_or_mem_base,
                .displacement = disp,
                .word = word,
            };
        }
    } else {
        return null;
    }
}

pub fn disassemble(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) @This() {
    if (extracted.get(.ip_inc8)) |inc_8| {
        return JumpInstruction{ .mnemonic = schema.name, .disp = @intCast(inc_8), .label = null };
    }

    const hasData: bool = extracted.get(.data) != null;
    const data: u16 = std.mem.readInt(u16, [_]u8{ extracted.get(.data_if_w_eq_1) orelse 0, extracted.get(.data) orelse 0 }, .big);
    const word: bool = if (extracted.get(.w)) |w| w == 1 else unreachable; // no idea what to do with instructions that don't have a w. Prob unary but idk yet

    const data_operand = getDataOperand(hasData, data, word);

    const reg: ?u3 = @truncate(extracted.get(.reg));
    const sr: ?u2 = @truncate(extracted.get(.sr));

    const reg_operand = getRegOperand(reg, sr, word);

    const rm: ?u3 = @truncate(extracted.get(.rm));
    const mode: ?Mode = getMode(extracted.get(.mod), rm);
    const disp: u16 = std.mem.readInt(u16, [_]u8{ extracted.get(.disp_lo) orelse 0, extracted.get(.disp_hi) orelse 0 }, .big);

    const rm_operand = getRmOperand(rm, mode, word, disp);

    const operand_buffer = [_]@This(){undefined} ** 3;
    const op_arr = std.ArrayList(operands.Operand).initBuffer(operand_buffer);
    for ([_]operands.Operands{ data_operand, reg_operand, rm_operand }) |op| {
        if (op) |o| {
            op_arr.appendBounded(o);
        }
    }

    const d: u1 = @truncate(extracted.get(.d) orelse 0);

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
