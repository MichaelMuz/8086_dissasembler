const std = @import("std");
const lexer = @import("lexer.zig");
const decoder = @import("decoder.zig");

pub fn formatInst(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) ![]u8 {
    var src_struct = try getSrc(extracted);
    var dst_struct = try getDst(extracted);

    if (extracted.get(.d) != 0) {
        // std.debug.print("flipping!d: {b}\n", .{extracted.get(.d).?});
        const tmp = src_struct;
        src_struct = dst_struct;
        dst_struct = tmp;
    }
    const src_arr, const src_sz = src_struct;
    const dst_arr, const dst_sz = dst_struct;

    const src = src_arr[0..src_sz];
    const dst = dst_arr[0..dst_sz];

    // std.debug.print("src: {s} #:{d}, dst: {s} #:{d} \n", .{ src, src.len, dst, dst.len });

    // x86 has: inst dest, source
    var buf = [_]u8{0} ** 64; // prob overkill
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

test "8 bit immediate to register uses implicit direction" {
    // "mov", "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1" implied: { .d = 0 }
    const encoding = lexer.encodings.instruction_encodings[1];
    var parsed_inst = decoder.ParsedInstruction.initFill(null);
    parsed_inst.set(.w, 0b0);
    parsed_inst.set(.mod, 0b11);
    parsed_inst.set(.rm, 1);
    parsed_inst.set(.data, 12);
    parsed_inst.set(.d, 0); // implied
    const ac = try formatInst(&encoding, &parsed_inst);
    try std.testing.expectEqualStrings("mov cl, 12", ac);
}
