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


class Mode:
    class Type(enum.Enum):
        NO_DISPLACEMENT_MODE = enum.auto()
        BYTE_DISPLACEMENT_MODE = enum.auto()
        WORD_DISPLACEMENT_MODE = enum.auto()
        REGISTER_MODE = enum.auto()

    def __init__(self, mod_val: int, rm_val: int | None) -> None:
        logging.debug(f"getting mode {mod_val = }, {rm_val = }")
        all_modes = [
            self.Type.NO_DISPLACEMENT_MODE,
            self.Type.BYTE_DISPLACEMENT_MODE,
            self.Type.WORD_DISPLACEMENT_MODE,
            self.Type.REGISTER_MODE,
        ]

        self.type = all_modes[mod_val]
        self.direct_memory_index = False
        if self.type is self.Type.NO_DISPLACEMENT_MODE and rm_val == 0b110:
            self.type = self.Type.WORD_DISPLACEMENT_MODE
            self.direct_memory_index = True

    def __repr__(self) -> str:
        return f"Mode<type={self.type}, direct_memory_index={self.direct_memory_index}>"
