from dataclasses import InitVar, dataclass
from functools import cached_property
from typing import override
from venv import logger

from python_implementation.src.base.schema import NamedField
from python_implementation.src.intermediates.operands import (
    ImmediateOperand,
    MemoryOperand,
    Operand,
)
from python_implementation.src.utils import as_signed_int


@dataclass(frozen=True)
class DisassembledNullaryInstruction:
    mnemonic: str
    inst_size: int


@dataclass(frozen=True)
class DisassembledUnaryInstruction:
    mnemonic: str
    op: Operand
    inst_size: int

    @override
    def __str__(self) -> str:
        size_spec = ""
        if self.mnemonic == "push":
            # should change this later, just have word be an attr on all operands?
            size_spec = "word "
        return f"{self.mnemonic} {size_spec}{self.op}"


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
    disp: InitVar[int]
    inst_size: int
    label: str | None = None

    def __post_init__(self, disp):
        self.displ = as_signed_int(disp)

    @override
    def __str__(self) -> str:
        destination = self.label or f"${as_signed_int(self.displ):+}"
        return f"{self.mnemonic} {destination}"

    def get_abs_label_offset(self, curr_byte_ind: int):
        return curr_byte_ind + self.inst_size + self.displ


type DisassembledInstruction = DisassembledNullaryInstruction | DisassembledUnaryInstruction | DisassembledBinaryInstruction | DisassembledJumpInstruction


@dataclass(frozen=True)
class Disassembly:
    instructions: list[DisassembledInstruction]

    @cached_property
    def instructions_with_labels(self) -> list[DisassembledInstruction | str]:
        curr_byte = 0
        jump_loc_to_insts: dict[int, list[DisassembledJumpInstruction]] = {}
        for inst in self.instructions:
            if isinstance(inst, DisassembledJumpInstruction):
                target_byte = inst.get_abs_label_offset(curr_byte)
                jump_loc_to_insts.setdefault(target_byte, [])
                jump_loc_to_insts[target_byte].append(inst)

            curr_byte += inst.inst_size

        curr_byte = 0
        label_counter = 0
        result: list[DisassembledInstruction | str] = []
        for inst in self.instructions:
            if curr_byte in jump_loc_to_insts:
                label = f"label_{label_counter}"
                label_counter += 1
                for j_inst in jump_loc_to_insts.pop(curr_byte):
                    j_inst.label = label
                result.append(label + ":")

            result.append(inst)
            curr_byte += inst.inst_size

        if len(jump_loc_to_insts) > 0:
            logger.warning(
                f"Disassembly contains {len(jump_loc_to_insts)} jumps pointing to middle of other instructions or out of instruction bounds"
            )

        return result

    @override
    def __str__(self) -> str:
        return "\n".join(["bits 16", *map(str, self.instructions_with_labels)])
