from dataclasses import dataclass
import enum
from functools import cached_property
import json
import logging
import os
import re
from typing import TypeAlias


class Mode(enum.Enum):
    NO_DISPLACEMENT_MODE = enum.auto()
    BYTE_DISPLACEMENT_MODE = enum.auto()
    WORD_DISPLACEMENT_MODE = enum.auto()
    REGISTER_MODE = enum.auto()


def get_mode(mod_val: int, rm_val: int | None):
    logging.debug(f"getting mode {mod_val = }, {rm_val = }")
    all_modes = [
        Mode.NO_DISPLACEMENT_MODE,
        Mode.BYTE_DISPLACEMENT_MODE,
        Mode.WORD_DISPLACEMENT_MODE,
        Mode.REGISTER_MODE,
    ]

    mode = all_modes[mod_val]
    if mode is Mode.NO_DISPLACEMENT_MODE and rm_val == 0b110:
        mode = Mode.WORD_DISPLACEMENT_MODE

    return mode


@dataclass(frozen=True)
class ImmediateOperand:
    value: int


@dataclass(frozen=True)
class RegisterOperand:
    register_index: int


@dataclass(frozen=True)
class MemoryOperand:
    memory_base: int
    displacement: int


Operand: TypeAlias = ImmediateOperand | RegisterOperand | MemoryOperand


@dataclass(frozen=True)
class DisassembledInstruction:
    mnemonic: str
    dest: str
    source: str

    def __str__(self) -> str:
        return f"{self.mnemonic} {self.dest}, {self.source}"


class DisassembledInstructionBuilder:
    REG_NAME_LOWER_AND_WORD = [
        # [lower_register_name, word_full_register_name]
        ["al", "ax"],
        ["cl", "cx"],
        ["dl", "dx"],
        ["bl", "bx"],
        ["ah", "sp"],
        ["ch", "bp"],
        ["dh", "si"],
        ["bh", "di"],
    ]
    RM_TO_EFFECTIVE_ADDR_CALC = [
        # if there are two things in the list, the equation these bits code for are those added
        ["bx", "si"],
        ["bx", "di"],
        ["bp", "si"],
        ["bp", "di"],
        ["si"],
        ["di"],
        ["bp"],
        ["bx"],
    ]
    ALWAYS_NEEDED_FIELDS = {
        # if we see this in an instruction schema, we must always parse it
        NamedField.D,
        NamedField.W,
        NamedField.MOD,
        NamedField.REG,
        NamedField.RM,
        NamedField.DATA,
    }

    def __init__(self, instruction_schema: InstructionSchema, identifier_literal):
        self.instruction_schema = instruction_schema
        self.parsed_fields = {
            named_field: implied_value
            for named_field, implied_value in instruction_schema.implied_values.items()
        }

        self.implied_values = set(self.parsed_fields.keys())
        self.identifier_literal = identifier_literal

    def with_field(self, schema_field: SchemaField, field_value: int):
        if isinstance(schema_field, LiteralField):
            assert schema_field.literal_value == field_value
        elif isinstance(schema_field, NamedField):
            self.parsed_fields[schema_field] = field_value
        return self

    def is_needed(self, schema_field: SchemaField) -> bool:
        if isinstance(schema_field, LiteralField):
            return True
        else:
            assert isinstance(schema_field, NamedField)
        assert (
            schema_field not in self.implied_values
        ), f"Asking if {schema_field} is required but its value is already implied"

        if schema_field in self.ALWAYS_NEEDED_FIELDS:
            return True
        elif schema_field == NamedField.DATA_IF_W1:
            return bool(self.parsed_fields[NamedField.W])
        elif schema_field in (NamedField.DISP_LO, NamedField.DISP_HI):
            return (self.mode == Mode.WORD_DISPLACEMENT_MODE) or (
                self.mode == Mode.BYTE_DISPLACEMENT_MODE
                and (schema_field == NamedField.DISP_LO)
            )
        else:
            raise ValueError(f"don't know how to check if {schema_field} is needed")

    @cached_property
    def mode(self) -> Mode:
        """This one is special because it is used in checking if a field is needed"""
        mod_value = self.parsed_fields[NamedField.MOD]
        rm_value = self.parsed_fields.get(NamedField.RM)
        mode = get_mode(mod_value, rm_value)
        logging.debug(f"locked in mode as {mode = }")
        return mode

    @cached_property
    def word(self):
        return self.parsed_fields[NamedField.W]

    @cached_property
    def direction(self):
        return self.parsed_fields[NamedField.D]

    @cached_property
    def displacement(self):
        disp = None
        if NamedField.DISP_LO in self.parsed_fields:
            disp = combine_bytes(
                self.parsed_fields[NamedField.DISP_LO],
                self.parsed_fields.get(NamedField.DISP_HI),
            )
            return disp

    @cached_property
    def data_operand(self):
        data_operand = None
        if NamedField.DATA in self.parsed_fields:
            data_operand = ImmediateOperand(
                value=combine_bytes(
                    self.parsed_fields[NamedField.DATA],
                    self.parsed_fields.get(NamedField.DATA_IF_W1),
                )
            )
        return data_operand

    @cached_property
    def register_operand(self):
        reg_operand = None
        if NamedField.REG in self.parsed_fields:
            reg_operand = RegisterOperand(
                register_index=self.parsed_fields[NamedField.REG]
            )
        return reg_operand

    @cached_property
    def rm_operand(self):
        rm_operand = None
        if NamedField.RM in self.parsed_fields:
            reg_or_mem_base = self.parsed_fields[NamedField.RM]
            if self.mode == Mode.REGISTER_MODE:
                rm_operand = RegisterOperand(register_index=reg_or_mem_base)
            else:
                rm_operand = MemoryOperand(
                    memory_base=reg_or_mem_base,
                    displacement=self.displacement or 0,
                )
        return rm_operand

    def _format_operand(self, operand: Operand) -> str:
        match operand:
            case RegisterOperand():
                return self.REG_NAME_LOWER_AND_WORD[operand.register_index][self.word]
            case MemoryOperand():
                equation = list(self.RM_TO_EFFECTIVE_ADDR_CALC[operand.memory_base])
                if operand.displacement and operand.displacement > 0:
                    equation.append(str(operand.displacement))
                return f"[{' + '.join(equation)}]"
            case ImmediateOperand():
                return str(operand.value)

    def build(self) -> DisassembledInstruction:
        assert not (
            self.data_operand and self.register_operand and self.rm_operand
        ), "Too many operands"

        if self.data_operand is not None:
            operands = [self.data_operand, self.register_operand or self.rm_operand]
        else:
            operands = [self.register_operand, self.rm_operand]

        if bool(self.direction):
            operands.reverse()

        assert None not in operands, "Cannot have null source or dest"
        source, dest = (self._format_operand(op) for op in operands)

        return DisassembledInstruction(
            mnemonic=self.instruction_schema.mnemonic, source=source, dest=dest
        )
