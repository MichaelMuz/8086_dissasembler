from dataclasses import dataclass
import enum
import json
import logging
from pathlib import Path
import re
from typing import TypeAlias
from python_implementation.src.builder import DecodeAccumulator
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


class NamedField(enum.Enum):
    bit_width: int  # for type checker, this exists
    always_needed: bool  # for type checker, this exists

    D = ("d", 1, True)
    W = ("w", 1, True)
    S = ("s", 1, True)
    REG = ("reg", 3, True)
    MOD = ("mod", 2, True)
    RM = ("rm", 3, True)
    DATA = ("data", 8, True)
    DISP_LO = ("disp-lo", 8, True)
    DISP_HI = ("disp-hi", 8)
    ADDR_LO = ("addr-lo", 8, True)
    ADDR_HI = ("addr-hi", 8)
    DATA_IF_W1 = ("data-if-w=1", 8)
    DATA_IF_SW_01 = ("data-if-s:w=01", 8)

    def __new__(cls, field_name: str, bit_width: int, always_needed: bool = False):
        obj = object.__new__(cls)
        obj._value_ = field_name
        obj.bit_width = bit_width
        obj.always_needed = always_needed
        return obj

    def is_needed(self, acc: DecodeAccumulator):
        if self.always_needed:
            return True

        match self:
            case self.DISP_HI:
                return acc.mode.type == Mode.WORD_DISPLACEMENT_MODE
            case self.ADDR_HI:
                raise NotImplementedError("Don't use ADDR_HI yet")
            case self.DATA_IF_W1:
                return acc.word
            case self.DATA_IF_SW_01:
                return not (acc.sign_extension) and acc.word
            case _:
                raise ValueError("I don't know how to check if this is needed")


SchemaField: TypeAlias = LiteralField | NamedField
ParsedNamedField: TypeAlias = dict[NamedField, int]


@dataclass
class InstructionSchema:
    mnemonic: str
    identifier_literal: LiteralField
    fields: list[SchemaField]
    implied_values: ParsedNamedField


def get_parsable_instructions(json_data_from_file: dict) -> list[InstructionSchema]:
    instruction_schemas = []
    for mnemonic_group in json_data_from_file["instructions"]:
        mnemonic = mnemonic_group["mnemonic"]

        for variation in mnemonic_group["variations"]:

            schema_fields = []
            # each comma separated group contains instruction parts that total a byte in size
            for this_byte in variation["format"].split(", "):
                current_start_bit = 0
                for this_inst_piece in this_byte.split(" "):
                    mat = re.match("[01]+", this_inst_piece)
                    if mat is not None:
                        this_field = LiteralField(int(this_inst_piece, 2), mat.end())
                    else:
                        this_field = NamedField(this_inst_piece)
                    schema_fields.append(this_field)
                    current_start_bit += this_field.bit_width
                assert current_start_bit == 8

            identifier_literal, schema_fields = schema_fields[0], schema_fields[1:]
            assert isinstance(
                identifier_literal, LiteralField
            ), "First parsed field always expected to be literal"

            implied_values = {}
            for field_type, value in variation["implied_values"].items():
                field = NamedField(field_type)
                implied_values[field] = value

            instruction_schema = InstructionSchema(
                mnemonic=mnemonic,
                identifier_literal=identifier_literal,
                fields=schema_fields,
                implied_values=implied_values,
            )
            instruction_schemas.append(instruction_schema)
    return instruction_schemas


PARSABLE_INSTRUCTION_FILE = "asm_config.json"


def get_parsable_instructions_from_config():
    config_path = Path(__file__).parent / ".." / ".." / PARSABLE_INSTRUCTION_FILE
    with open(config_path, "r") as file:
        json_data_from_file = json.load(file)
    return get_parsable_instructions(json_data_from_file)
