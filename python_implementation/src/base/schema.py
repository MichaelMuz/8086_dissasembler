import logging
from dataclasses import dataclass
from enum import Enum

from python_implementation.src.utils import BITS_PER_BYTE


class LiteralField:
    def __init__(self, literal_value: int, bit_width: int):
        self.literal_value = literal_value
        assert bit_width > 0 and bit_width < BITS_PER_BYTE
        self.bit_width = bit_width

    def is_match(self, other_int: int):
        assert int.bit_length(other_int) <= 8
        other_int_shifted = other_int >> (BITS_PER_BYTE - self.bit_width)
        logging.debug(
            f"comparing me: {self.literal_value:08b}, to: {other_int_shifted:08b}. Before downshift: {other_int:08b}"
        )
        return other_int_shifted == self.literal_value

    def __repr__(self) -> str:
        return f"LiteralField(literal_value=0b{self.literal_value:08b}, bit_width={self.bit_width})"


class NamedField(Enum):
    bit_width: int  # for type checker, this exists
    always_needed: bool  # for type checker, this exists

    D = ("d", 1, True)
    W = ("w", 1, True)
    S = ("s", 1, True)
    REG = ("reg", 3, True)
    MOD = ("mod", 2, True)
    RM = ("rm", 3, True)
    DATA = ("data", 8, True)
    DISP_LO = ("disp-lo", 8)
    DISP_HI = ("disp-hi", 8)
    ADDR_LO = ("addr-lo", 8)
    ADDR_HI = ("addr-hi", 8)
    DATA_IF_W1 = ("data-if-w=1", 8)
    DATA_IF_SW_01 = ("data-if-s:w=01", 8)

    def __new__(cls, field_name: str, bit_width: int, always_needed: bool = False):
        obj = object.__new__(cls)
        obj._value_ = field_name
        obj.bit_width = bit_width
        obj.always_needed = always_needed
        return obj


type SchemaField = LiteralField | NamedField
type ParsedNamedField = dict[NamedField, int]


@dataclass
class InstructionSchema:
    mnemonic: str
    identifier_literal: LiteralField
    fields: list[SchemaField]
    implied_values: ParsedNamedField
