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

fn getSrc(extracted: *const decoder.ParsedInstruction) !struct { [16]u8, u5 } {
    // can prob replace manual bookkeeping with arraylist given this buf
    var buf = [_]u8{0} ** 16;
    var bytes: usize = 0;

    if (extracted.get(.data)) |data| {
        if (extracted.get(.data_if_w_eq_1)) |diw1| {
            const both_data = std.mem.readInt(u16, &[_]u8{ diw1, data }, .big);
            bytes = (try std.fmt.bufPrint(&buf, "{b}", .{both_data})).len;
        } else {
            bytes = (try std.fmt.bufPrint(&buf, "{b}", .{data})).len;
        }
    } else if (extracted.get(.reg)) |reg| {
        const w = extracted.get(.w) orelse 0;
        const register = reg_and_word_to_reg_name[@truncate(reg)][w];
        bytes = (try std.fmt.bufPrint(&buf, "{s}", .{register})).len;
    } else {
        unreachable;
    }
    return .{ buf, @truncate(bytes) };
}

fn getDst(extracted: *const decoder.ParsedInstruction) !struct { [16]u8, u5 } {
    var buf = [_]u8{0} ** 16;
    var bytes: usize = 0;
    if (extracted.get(.rm)) |rm| {
        const w = extracted.get(.w) orelse 0;
        const reg = reg_and_word_to_reg_name[@truncate(rm)][w];
        bytes = (try std.fmt.bufPrint(&buf, "{s}", .{reg})).len;
    } else {
        unreachable;
    }
    return .{ buf, @truncate(bytes) };
}

pub fn formatInst(schema: *const lexer.schema.InstructionSchema, extracted: *const decoder.ParsedInstruction) ![]u8 {
    var src_struct = try getSrc(extracted);
    var dst_struct = try getDst(extracted);

    // std.debug.print("src: {s}, dst: {s}\n", .{ src, dst, d });
    if (extracted.get(.d) != 0) {
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

// this is our first 'implicit' instruction. The direction is implied to be 0. We can orelse this for now
// test "8 bit immediate to register" {
//     // "mov", "1100011 w, mod 000 rm, disp_lo, disp_hi, data, data_if_w_eq_1"
//     const encoding = lexer.encodings.instruction_encodings[1];
//     var parsed_inst = decoder.ParsedInstruction.initFill(null);
//     parsed_inst.set(.w, 0b0);
//     parsed_inst.set(.mod, 0b11);
//     parsed_inst.set(.rm, 1);
//     const ac = try formatInst(&encoding, &parsed_inst);
//     try std.testing.expectEqualStrings("mov cl, 12", ac);
// }
