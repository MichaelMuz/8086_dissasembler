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

pub fn insertBits(T: type, insert_into: T, start_ind: IndexT(T), to_insert: anytype, num_bits: ?NumBitsT(@TypeOf(to_insert))) T {
    const I = @TypeOf(to_insert);

    const width: NumBitsT(I) = num_bits orelse @typeInfo(I).int.bits;
    std.debug.assert(width <= @typeInfo(T).int.bits);

    const mask_of_width: T = @truncate((@as(WideT(T), 1) << width) - 1);
    const mask: T = mask_of_width << start_ind;
    const insert_into_target_cleared = insert_into & ~mask;

    const clean_to_insert: T = to_insert & mask_of_width; // may not want to use entire to_insert, just first bits
    const to_insert_shifted: T = clean_to_insert << start_ind;
    const post_insert: T = insert_into_target_cleared | to_insert_shifted;
    return post_insert;
}

pub fn insertMostSigBits(T: type, insert_into: T, start_ind: IndexT(T), to_insert: anytype, num_bits: ?NumBitsT(@TypeOf(to_insert))) T {
    const I = @TypeOf(to_insert);

    const container_width: NumBitsT(T) = @typeInfo(T).int.bits;
    const to_insert_width: NumBitsT(I) = num_bits orelse @typeInfo(I).int.bits;

    const highest_least_sig_start_ind: IndexT(T) = container_width - 1;
    const insert_width_index_offset: IndexT(I) = to_insert_width - 1;

    const least_sig_start_ind: IndexT(T) = highest_least_sig_start_ind - start_ind - insert_width_index_offset;

    return insertBits(T, insert_into, least_sig_start_ind, to_insert, num_bits);
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

test "insert bits start" {
    try std.testing.expect(insertBits(u5, 0b10101, 0, @as(u3, 0b010), null) == 0b10010);
}
test "insert bits end" {
    try std.testing.expect(insertBits(u5, 0b10101, 2, @as(u3, 0b010), null) == 0b01001);
}
test "insert bits middle" {
    try std.testing.expect(insertBits(u8, 0b10101010, 2, @as(u3, 0b110), null) == 0b10111010);
}
test "insert bits start num bits whole" {
    try std.testing.expect(insertBits(u5, 0b10101, 0, @as(u3, 0b010), 3) == 0b10010);
}
test "insert bits start num bits part" {
    try std.testing.expect(insertBits(u5, 0b10101, 0, @as(u3, 0b010), 2) == 0b10110);
}
test "insert bits end num bits whole" {
    try std.testing.expect(insertBits(u5, 0b10101, 2, @as(u3, 0b010), 3) == 0b01001);
}
test "insert bits middle num bits part" {
    try std.testing.expect(insertBits(u8, 0b10101010, 2, @as(u3, 0b101), 2) == 0b10100110);
}

test "insert sig bits start" {
    try std.testing.expect(insertMostSigBits(u5, 0b10101, 0, @as(u3, 0b010), null) == 0b01001);
}
test "insert sig bits end" {
    try std.testing.expect(insertMostSigBits(u5, 0b10101, 2, @as(u3, 0b010), null) == 0b10010);
}
test "insert sig bits middle" {
    try std.testing.expect(insertMostSigBits(u8, 0b10101010, 2, @as(u3, 0b110), null) == 0b10110010);
}
test "insert sig bits start num bits whole" {
    try std.testing.expect(insertMostSigBits(u5, 0b10101, 0, @as(u3, 0b010), 3) == 0b01001);
}
test "insert sig bits start num bits part" {
    try std.testing.expect(insertMostSigBits(u5, 0b00101, 0, @as(u3, 0b010), 2) == 0b10101);
}
test "insert sig bits end num bits whole" {
    try std.testing.expect(insertMostSigBits(u5, 0b10101, 2, @as(u3, 0b010), 3) == 0b10010);
}
test "insert sig bits end num bits part" {
    try std.testing.expect(insertMostSigBits(u5, 0b10001, 2, @as(u3, 0b010), 2) == 0b10101);
}
test "insert sig bits middle num bits whole" {
    try std.testing.expect(insertMostSigBits(u8, 0b10101010, 2, @as(u3, 0b110), 3) == 0b10110010);
}
test "insert sig bits middle num bits part" {
    try std.testing.expect(insertMostSigBits(u8, 0b10101010, 2, @as(u3, 0b001), 2) == 0b10011010);
}
