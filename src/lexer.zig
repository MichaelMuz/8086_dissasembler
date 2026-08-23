const std = @import("std");

// TODO I can comptime this so it knows if it is 8 or 16 bits prob?
const Instruction = struct {
    name: []const u8,
    pattern: []const u8,
    /// the literal bits preserved and 0s for the variable bits
    skeleton: u16,
    /// the literal bits have 1s and the variable bits get 0s
    mask: u16,

    pub fn init(name: []const u8, pattern: []const u8) !Instruction {
        var skeleton: [16]u8 = [_]u8{'0'} ** 16;
        var mask: [16]u8 = [_]u8{'0'} ** 16;

        // TODO ugly and inefficient. Can just do bit manip later
        for (0.., pattern) |i, c| {
            if (c == '1' or c == '0') {
                skeleton[i] = c;
                mask[i] = '1';
            } else {
                skeleton[i] = '0';
                mask[i] = '0';
            }
        }

        std.debug.print("skeleton: {s}\n", .{skeleton});
        std.debug.print("mask: {s}\n", .{mask});

        return Instruction{ .name = name, .pattern = pattern, .skeleton = try (std.fmt.parseInt(u16, &skeleton, 2)), .mask = try (std.fmt.parseInt(u16, &mask, 2)) };
    }

    pub fn matches(self: Instruction, other_pattern: u16) bool {
        const zero_where_agree = other_pattern ^ self.skeleton;
        const zero_where_agree_and_variable = zero_where_agree & self.mask;
        std.debug.print("zero_where_agree: {d}, zero_where_agree_and_variable: {d}\n", .{ zero_where_agree, zero_where_agree_and_variable });
        return 0 == zero_where_agree_and_variable;
    }
};

test "check that things match" {
    const mov0 = Instruction.init("mov0", "100010dw") catch unreachable;
    // const mov1 = Instruction.init("mov1", "1100011w") catch unreachable;
    try std.testing.expect(mov0.matches(0b10001011 << 8));
    try std.testing.expect(mov0.matches(0b10001000 << 8));
    try std.testing.expect(!mov0.matches(0b10011011 << 8));
}
