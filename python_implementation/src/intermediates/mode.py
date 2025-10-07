import logging
from enum import Enum, auto


class Mode:
    class Type(Enum):
        NO_DISPLACEMENT_MODE = auto()
        BYTE_DISPLACEMENT_MODE = auto()
        WORD_DISPLACEMENT_MODE = auto()
        REGISTER_MODE = auto()

    def __init__(self, mod_val: int, rm_val: int | None) -> None:
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
