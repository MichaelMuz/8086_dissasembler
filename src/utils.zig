const std = @import("std");

fn IndexT(T: type) type {
    return std.math.Log2Int(T);
}

fn NumBitsT(T: type) type {
    return std.math.Log2IntCeil(T);
}

fn WideT(T: type) type {
    return std.meta.Int(.unsigned, @typeInfo(T).int.bits + 1);
}

pub fn getSubBits(T: type, to_index: T, start_ind: IndexT(T), num_bits: NumBitsT(T)) T {
    const r_shifted = to_index >> start_ind;
    const mask: T = @truncate((@as(WideT(T), 1) << num_bits) - 1);
    return r_shifted & mask;
}

pub fn getSubMostSigBits(T: type, to_index: T, msb_start_ind: IndexT(T), num_bits: NumBitsT(T)) T {
    const max_ind: IndexT(T) = @typeInfo(T).int.bits - 1;

    const end_ind: IndexT(T) = max_ind - msb_start_ind;
    const num_bits_past_start: IndexT(T) = @truncate(num_bits - 1);
    const start_ind: IndexT(T) = end_ind - num_bits_past_start;
    return getSubBits(T, to_index, start_ind, num_bits);
}

test "get sub bits basic" {
    try std.testing.expect(getSubBits(u8, 0b11010110, 2, 3) == 0b101);
}
test "get sub bits from start" {
    try std.testing.expect(getSubBits(u8, 0b11010110, 0, 4) == 0b0110);
}
test "get sub bits single bit" {
    try std.testing.expect(getSubBits(u8, 0b11010110, 5, 1) == 0);
    try std.testing.expect(getSubBits(u8, 0b11010110, 4, 1) == 1);
}
test "get sub bits all bits" {
    try std.testing.expect(getSubBits(u8, 0b11010110, 0, 8) == 0b11010110);
}
test "get sub bits high bits" {
    try std.testing.expect(getSubBits(u8, 0b11010110, 5, 3) == 0b110);
}

test "get sub sig bits high bits" {
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 0, 3) == 0b110);
}
test "get sub sig bits middle" {
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 2, 3) == 0b010);
}
test "get sub sig bits single bit" {
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 2, 3) == 0b010);
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 0, 1) == 1);
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 1, 1) == 1);
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 2, 1) == 0);
    try std.testing.expect(getSubMostSigBits(u2, 0b10, 0, 1) == 1);
}
test "get sub sig bits last bits" {
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 6, 2) == 0b10);
}
test "get sub sig bits all bits" {
    try std.testing.expect(getSubMostSigBits(u8, 0b11010110, 0, 8) == 0b11010110);
}
