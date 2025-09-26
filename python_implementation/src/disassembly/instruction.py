from dataclasses import dataclass
import enum
from functools import cached_property
import logging
from typing import TypeAlias

from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import as_signed_int, combine_bytes


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
