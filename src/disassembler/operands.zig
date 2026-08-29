const std = @import("std");
const decoder = @import("../decoder.zig");

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
const rm_to_effective_addr_calc = [_][2]?*const [2:0]u8{
    // if there are two things in the list, the equation these bits code for are those added
    .{ "bx", "si" },
    .{ "bx", "di" },
    .{ "bp", "si" },
    .{ "bp", "di" },
    .{ "si", null },
    .{ "di", null },
    .{ "bp", null },
    .{ "bx", null },
};
const segment_names = [_]*const [2:0]u8{ "es", "cs", "ss", "ds" };

const ImmediateOperand = struct {
    value: u16,
    word: bool,

    pub fn fmt(self: *const @This(), arr: *std.ArrayList(u8)) void {
        arr.printAssumeCapacity("{d}", .{self.value});
    }
};

const RegOperand = struct {
    reg_ind: u3,
    word: bool,

    pub fn fmt(self: *const @This(), arr: *std.ArrayList(u8)) void {
        arr.printAssumeCapacity("{s}", .{reg_and_word_to_reg_name[self.reg_ind]});
    }
};

const SegmentRegOperand = struct {
    reg_ind: u3,
    word: bool = true, // true by default

    pub fn fmt(self: *const @This(), arr: *std.ArrayList(u8)) void {
        arr.printAssumeCapacity("{s}", .{segment_names[self.reg_ind]});
    }
};

const RegisterOperand = union(enum) {
    reg_operand: RegOperand,
    seg_operand: SegmentRegOperand,

    pub fn word(self: *const @This()) bool {
        return switch (self) {
            inline else => self.word,
        };
    }
};

const MemoryOperand = struct {
    memory_base: ?u8,
    displacement: u16,
    word: bool,

    // pub fn getSizeSpec( self: *const @This()) [4]u8 {
    //     return switch (self.word) {
    //         true => "word",
    //         false => "byte",
    //     };
    // }

    pub fn fmt(self: *const @This(), arr: *std.ArrayList(u8)) void {
        arr.printAssumeCapacity("[", .{});

        const first, const second = if (self.memory_base) |m|
            rm_to_effective_addr_calc[m]
        else
            .{ null, null };

        var need_plus = false;
        if (first) |f| {
            arr.printAssumeCapacity("{s}", .{f});
            need_plus = true;
        }
        if (second) |s| {
            if (need_plus) {
                arr.printAssumeCapacity(" + ", .{});
            }
            arr.printAssumeCapacity("{s}", .{s});
            need_plus = true;
        }
        if (self.displacement != 0) {
            if (need_plus) {
                arr.printAssumeCapacity(" + ", .{});
            }
            arr.printAssumeCapacity("{d}", .{self.displacement});
        }

        arr.printAssumeCapacity("]", .{});
    }
};

const Operand = union(enum) {
    immediate_operand: ImmediateOperand,
    register_operand: RegisterOperand,
    memory_operand: MemoryOperand,

    pub fn fmt(self: *const @This(), arr: *std.ArrayList(u8)) void {
        return switch (self) {
            inline else => |op| op.fmt(arr),
        };
    }
};

fn test_fmt_helper(expected: []const u8, actual: anytype) !void {
    var buf = [_]u8{0} ** 64;
    var arr = std.ArrayList(u8).initBuffer(&buf);
    actual.fmt(&arr);
    try std.testing.expectEqualStrings(expected, arr.items);
}

test "immediate operand" {
    try test_fmt_helper("12", &ImmediateOperand{ .value = 12, .word = false });
}

test "reg operand byte" {
    try test_fmt_helper("ch", &RegOperand{ .reg_ind = 5, .word = false });
}
test "reg operand word" {
    try test_fmt_helper("bp", &RegOperand{ .reg_ind = 5, .word = true });
}

test "segment reg operand" {
    try test_fmt_helper("cs", &SegmentRegOperand{ .reg_ind = 1, .word = false });
}

test "register operand is reg operand" {
    try test_fmt_helper("bp", &RegisterOperand{ .reg_operand = .{ .reg_ind = 5, .word = false } });
}
test "register operand is seg operand" {
    try test_fmt_helper("cs", &RegisterOperand{ .seg_operand = .{ .reg_ind = 1, .word = false } });
}

test "memory operand partial null base only" {
    try test_fmt_helper("[di]", &MemoryOperand{ .memory_base = 5, .displacement = 0, .word = false });
}
test "memory operand no null base only" {
    try test_fmt_helper("[bx + si]", &MemoryOperand{ .memory_base = 5, .displacement = 0, .word = false });
}
test "memory operand displacement only" {
    try test_fmt_helper("[4]", &MemoryOperand{ .memory_base = null, .displacement = 4, .word = false });
}
test "memory operand partial null base and displacement" {
    try test_fmt_helper("[di + 4]", &MemoryOperand{ .memory_base = 5, .displacement = 4, .word = false });
}
test "memory operand no null base and displacement" {
    try test_fmt_helper("[bx + si + 4]", &MemoryOperand{ .memory_base = 5, .displacement = 4, .word = false });
}

test "operand immediate" {
    try test_fmt_helper("12", &Operand{ .immediate_operand = .{ .value = 12, .word = false } });
}
test "operand register" {
    try test_fmt_helper("bp", &Operand{ .register_operand = .{ .reg_operand = .{ .reg_ind = 5, .word = false } } });
}
test "operand memory" {
    try test_fmt_helper("[bx + si + 4]", &Operand{ .memory_operand = .{ .memory_base = 5, .displacement = 4, .word = false } });
}
