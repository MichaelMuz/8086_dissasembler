const std = @import("std");
const lexer = @import("../lexer.zig");
const decoder = @import("../decoder.zig");
const operands = @import("operands.zig");
const instructions = @import("instructions.zig");

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

fn getDataOperand(hasData: bool, data: u16, word: bool) ?operands.Operand {
    if (hasData) {
        return operands.Operand{ .immediate_operand = .{ .value = data, .word = word } };
    } else {
        return null;
    }
}

fn getRegOperand(reg: ?u3, sr: ?u2, word: bool) ?operands.Operand {
    if (reg) |r| {
        return operands.Operand{ .register_operand = .{ .reg_operand = .{ .reg_ind = r, .word = word } } };
    } else if (sr) |s| {
        return operands.Operand{ .register_operand = .{ .seg_operand = .{ .reg_ind = s } } };
    } else {
        return null;
    }
}

fn getRmOperand(rm: ?u3, mode: ?Mode, word: bool, disp: u16) ?operands.Operand {
    const m = mode orelse return null; // can't have rm operand without mode

    if (rm) |reg_or_mem_base| {
        if (m.mode == .register_mode) {
            return operands.Operand{ .register_operand = .{ .reg_operand = .{ .reg_ind = reg_or_mem_base, .word = word } } };
        } else {
            return operands.Operand{ .memory_operand = .{
                .memory_base = if (m.direct_memory_index) null else reg_or_mem_base,
                .displacement = disp,
                .word = word,
            } };
        }
    } else {
        return null;
    }
}

pub fn disassemble(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) instructions.DisasmInstr {
    if (extracted.get(.ip_inc8)) |inc_8| {
        return instructions.DisasmInstr{ .jump_instruction = .{ .mnemonic = schema.name, .disp = @intCast(inc_8), .label = null } };
    }

    const hasData: bool = extracted.get(.data) != null;
    const data: u16 = std.mem.readInt(u16, &[_]u8{ extracted.get(.data_if_w_eq_1) orelse 0, extracted.get(.data) orelse 0 }, .big);
    const word: bool = if (extracted.get(.w)) |w| w == 1 else unreachable; // no idea what to do with instructions that don't have a w. Prob unary but idk yet

    const data_operand = getDataOperand(hasData, data, word);

    const reg: ?u3 = if (extracted.get(.reg)) |r| @intCast(r) else null;
    const sr: ?u2 = if (extracted.get(.sr)) |sr| @intCast(sr) else null;
    const reg_operand = getRegOperand(reg, sr, word);

    const rm: ?u3 = if (extracted.get(.rm)) |rm| @intCast(rm) else null;
    const mode: ?Mode = getMode(if (extracted.get(.mod)) |m| @intCast(m) else null, rm);
    const disp: u16 = std.mem.readInt(u16, &[_]u8{ extracted.get(.disp_lo) orelse 0, extracted.get(.disp_hi) orelse 0 }, .big);

    const rm_operand = getRmOperand(rm, mode, word, disp);

    var operand_buffer = [_]operands.Operand{undefined} ** 3;
    var op_arr = std.ArrayList(operands.Operand).initBuffer(&operand_buffer);
    for ([_]?operands.Operand{ data_operand, reg_operand, rm_operand }) |op| {
        if (op) |o| {
            op_arr.appendAssumeCapacity(o);
        }
    }

    const d: u1 = @intCast(extracted.get(.d) orelse 0);

    return switch (op_arr.items.len) {
        0 => instructions.DisasmInstr{ .nullary_instruction = .{ .mnemonic = schema.name } },
        1 => instructions.DisasmInstr{ .unary_instruction = .{ .mnemonic = schema.name, .op = op_arr.items[0] } },
        2 => instructions.DisasmInstr{ .binary_instruction = .{
            .mnemonic = schema.name,
            .src = op_arr.items[0 ^ d],
            .dst = op_arr.items[1 ^ d],
        } },
        else => unreachable,
    };
}

fn test_disassemble_helper(expected: []const u8, schema: *const lexer.schema.InstructionSchema, fields: std.enums.EnumFieldStruct(lexer.schema.NamedField, ?u8, @as(?u8, null))) !void {
    var buf = [_]u8{0} ** 64;
    var arr = std.ArrayList(u8).initBuffer(&buf);

    const parsed_inst = decoder.ParsedInstruction.initDefault(@as(?u8, null), fields);
    const disasm_instr = disassemble(schema, &parsed_inst);

    disasm_instr.fmt(&arr);
    try std.testing.expectEqualStrings(expected, arr.items);
}

test "simple reg to reg" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
    try test_disassemble_helper(
        "mov cx, bx",
        &lexer.encodings.instruction_encodings[0],
        .{
            .d = 0b0,
            .w = 0b1,
            .mod = 0b11,
            .reg = 3,
            .rm = 1,
        },
    );
}
test "simple reg to reg with d set" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
    try test_disassemble_helper(
        "mov bx, cx",
        &lexer.encodings.instruction_encodings[0],
        .{
            .d = 0b1,
            .w = 0b1,
            .mod = 0b11,
            .reg = 3,
            .rm = 1,
        },
    );
}
test "8 bit immediate to register uses implicit direction" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
    try test_disassemble_helper(
        "mov cl, 12",
        &lexer.encodings.instruction_encodings[0],
        .{
            .w = 0b0,
            .mod = 0b11,
            .rm = 1,
            .data = 12,
            .d = 0, // would be decoded with implied
        },
    );
}
