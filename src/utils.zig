const std = @import("std");

// TODO: I bet I can make this work on any size int. Just dk how to ask zig to make second param
// size of log base 2 of the first

pub fn getSubBits(to_index: u16, start_ind: u8, num_bits: u8) u16 {
    const r_shifted = to_index >> start_ind;
    const mask = (1 << num_bits) - 1;
    return r_shifted & mask;
}

pub fn getSubMostSigBits(to_index: u16, msb_start_ind: u8, num_bits: u8) u16 {
    const max_ind: u8 = @typeInfo(@TypeOf((to_index))).int.bits - 1;
    const end_ind = max_ind - msb_start_ind;
    const start_ind = end_ind - num_bits + 1; // includes start
    return getSubBits(to_index, start_ind, num_bits);
}

test "get sub bits basic" {
    try std.testing.expect(getSubBits(0b11010110, 2, 3) == 0b101);
}
// test "get sub bits from start" {
//     std.testing.expect(getSubBits(0b11010110, 0, 4) == 0b0110);
// }
// test "get sub bits single bit" {
//     std.testing.expect(getSubBits(0b11010110, 5, 1) == 0);
//     std.testing.expect(getSubBits(0b11010110, 4, 1) == 1);
// }
// test "get sub bits all bits" {
//     std.testing.expect(getSubBits(0b11010110, 0, 8) == 0b11010110);
// }
// test "get sub bits high bits" {
//     std.testing.expect(getSubBits(0b11010110, 0, 8) == 0b110);
// }

// test "get sub sig bits high bits" {
//     std.testing.expect(getSubMostSigBits(0b11010110, 0, 3) == 0b110);
// }
// test "get sub sig bits middle" {
//     std.testing.expect(getSubMostSigBits(0b11010110, 2, 3) == 0b010);
// }
// test "get sub sig bits single bit" {
//     std.testing.expect(getSubMostSigBits(0b11010110, 2, 3) == 0b010);
//     std.testing.expect(getSubMostSigBits(0b11010110, 0, 1) == 1);
//     std.testing.expect(getSubMostSigBits(0b11010110, 1, 1) == 1);
//     std.testing.expect(getSubMostSigBits(0b11010110, 2, 1) == 0);
//     std.testing.expect(getSubMostSigBits(0b10, 0, 1) == 1);
// }
// test "get sub sig bits last bits" {
//     std.testing.expect(getSubMostSigBits(0b11010110, 6, 2) == 0b10);
// }
// test "get sub sig bits all bits" {
//     std.testing.expect(getSubMostSigBits(0b11010110, 0, 8) == 0b11010110);
// }
