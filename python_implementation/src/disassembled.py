from dataclasses import dataclass

from python_implementation.src.intermediates.operands import (
    ImmediateOperand,
    MemoryOperand,
    Operand,
)


@dataclass(frozen=True)
class DisassembledInstruction:
    mnemonic: str
    dest: Operand
    source: Operand

    def __str__(self) -> str:
        size_spec = ""
        if isinstance(self.dest, MemoryOperand) and isinstance(
            self.source, ImmediateOperand
        ):
            size_spec = "word " if self.source.word else "byte "
        return f"{self.mnemonic} {self.dest}, {size_spec}{self.source}"
