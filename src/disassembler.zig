const operands = @import("disassembler/operands.zig");
pub const instructions = @import("disassembler/instructions.zig");
pub const disassemble = @import("disassembler/disassemble.zig");

test {
    _ = disassemble;
    _ = instructions;
    _ = operands;
}
