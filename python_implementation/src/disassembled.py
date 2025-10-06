from dataclasses import dataclass
from functools import cached_property
from typing import override

from python_implementation.src.intermediates.operands import (
    ImmediateOperand,
    MemoryOperand,
    Operand,
)


@dataclass(frozen=True)
class DisassembledBinaryInstruction:
    mnemonic: str
    dest: Operand
    source: Operand
    inst_size: int

    @override
    def __str__(self) -> str:
        size_spec = ""
        if isinstance(self.dest, MemoryOperand) and isinstance(
            self.source, ImmediateOperand
        ):
            size_spec = "word " if self.source.word else "byte "
        return f"{self.mnemonic} {self.dest}, {size_spec}{self.source}"


@dataclass
class DisassembledJumpInstruction:
    mnemonic: str
    disp: int
    inst_size: int
    label: str | None = None

    @override
    def __str__(self) -> str:
        destination = self.label or f"{self.disp:08b}"
        return f"{self.mnemonic}, {destination}"

    def get_abs_label_offset(self, curr_byte_ind: int):
        return curr_byte_ind + self.inst_size + self.disp


type DisassembledInstruction = DisassembledBinaryInstruction | DisassembledJumpInstruction


@dataclass(frozen=True)
class Disassembly:
    instructions: list[DisassembledInstruction]

    @cached_property
    def instructions_with_labels(self) -> list[DisassembledInstruction | str]:

        curr_byte = 0
        label_counter = 0
        jump_loc_to_label_name: dict[int, str] = {}
        for inst in self.instructions:
            if isinstance(inst, DisassembledJumpInstruction):
                target_byte = inst.get_abs_label_offset(curr_byte)

                if target_byte not in jump_loc_to_label_name:
                    jump_loc_to_label_name[target_byte] = f"label_{label_counter}"
                    label_counter += 1

                inst.label = jump_loc_to_label_name[target_byte]

            curr_byte += inst.inst_size

        curr_byte = 0
        result: list[DisassembledInstruction | str] = []
        for inst in self.instructions:
            if curr_byte in jump_loc_to_label_name:
                result.append(jump_loc_to_label_name[curr_byte] + ":")

            result.append(inst)
            curr_byte += inst.inst_size

        return result

    @override
    def __str__(self) -> str:
        return "\n".join(["bits 16", *map(str, self.instructions_with_labels)])
