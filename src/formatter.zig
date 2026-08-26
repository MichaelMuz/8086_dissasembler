const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");

const reg_and_word_to_reg_name = [_][2]*const [2:0]u8{
    // 8 bit reg, 16 bit reg
    .{ "al", "ax" },
    .{ "cl", "cx" },
    .{ "dl", "dx" },
    .{ "bl", "bx" },
    .{ "ah", "sp" },
    .{ "ch", "bp" },
    .{ "dh", "si" },
    .{ "bh", "di" },
};

pub fn formatInst(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) ![]u8 {
    const d = extracted.get(.d).?;
    const w = extracted.get(.w).?;
    const reg: u3 = @truncate(extracted.get(.reg).?);
    const rm: u3 = @truncate(extracted.get(.rm).?);

    var src = reg_and_word_to_reg_name[reg][w];
    var dst = reg_and_word_to_reg_name[rm][w];
    // std.debug.print("src: {s}, dst: {s}\n", .{ src, dst, d });
    if (d != 0) {
        const tmp = src;
        src = dst;
        dst = tmp;
    }
    // std.debug.print("src: {s}, dst: {s}\n", .{ src, dst });

    var buf = [_]u8{0} ** 64; // prob overkill
    // x86 has: inst dest, source
    return (try std.fmt.bufPrint(&buf, "{s} {s}, {s}", .{ schema.name, dst, src }));
}

test "simple reg to reg" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
    const encoding = lexer.encodings.instruction_encodings[0];
    var parsed_inst = decoder.ParsedInstruction.initFill(null);
    parsed_inst.set(.d, 0b0);
    parsed_inst.set(.w, 0b1);
    parsed_inst.set(.mod, 0b11);
    parsed_inst.set(.reg, 3);
    parsed_inst.set(.rm, 1);
    const ac = try formatInst(&encoding, &parsed_inst);
    try std.testing.expectEqualStrings("mov cx, bx", ac);
}

test "simple reg to reg with d set" {
    // "mov", "100010 d w, mod reg rm, disp_lo, disp_hi" reg/mem to/from reg
    const encoding = lexer.encodings.instruction_encodings[0];
    var parsed_inst = decoder.ParsedInstruction.initFill(null);
    parsed_inst.set(.d, 0b1);
    parsed_inst.set(.w, 0b1);
    parsed_inst.set(.mod, 0b11);
    parsed_inst.set(.reg, 3);
    parsed_inst.set(.rm, 1);
    const ac = try formatInst(&encoding, &parsed_inst);
    try std.testing.expectEqualStrings("mov bx, cx", ac);
}
