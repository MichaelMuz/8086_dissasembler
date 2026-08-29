const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");
const operands = @import("operands.zig");

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

// test "simple reg to reg" {
//     // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
//     const encoding = lexer.encodings.instruction_encodings[0];
//     var parsed_inst = decoder.ParsedInstruction.initFill(null);
//     parsed_inst.set(.d, 0b0);
//     parsed_inst.set(.w, 0b1);
//     parsed_inst.set(.mod, 0b11);
//     parsed_inst.set(.reg, 3);
//     parsed_inst.set(.rm, 1);
//     const ac = try formatInst(&encoding, &parsed_inst);
//     try std.testing.expectEqualStrings("mov cx, bx", ac);
// }

// test "simple reg to reg with d set" {
//     // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
//     const encoding = lexer.encodings.instruction_encodings[0];
//     var parsed_inst = decoder.ParsedInstruction.initFill(null);
//     parsed_inst.set(.d, 0b1);
//     parsed_inst.set(.w, 0b1);
//     parsed_inst.set(.mod, 0b11);
//     parsed_inst.set(.reg, 3);
//     parsed_inst.set(.rm, 1);
//     const ac = try formatInst(&encoding, &parsed_inst);
//     try std.testing.expectEqualStrings("mov bx, cx", ac);
// }

// test "8 bit immediate to register uses implicit direction" {
//     // "mov", "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1" implied: { .d = 0 }
//     const encoding = lexer.encodings.instruction_encodings[1];
//     var parsed_inst = decoder.ParsedInstruction.initFill(null);
//     parsed_inst.set(.w, 0b0);
//     parsed_inst.set(.mod, 0b11);
//     parsed_inst.set(.rm, 1);
//     parsed_inst.set(.data, 12);
//     parsed_inst.set(.d, 0); // implied
//     const ac = try formatInst(&encoding, &parsed_inst);
//     try std.testing.expectEqualStrings("mov cl, 12", ac);
// }
