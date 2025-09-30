from functools import cached_property
import logging

from python_implementation.src.disassembly.instruction import DisassembledInstruction
from python_implementation.src.parse.operands import (
    ImmediateOperand,
    RegisterOperand,
    MemoryOperand,
)
from python_implementation.src.parse.mode import Mode
from python_implementation.src.templates.instruction_schema import InstructionSchema
from python_implementation.src.templates.schema_field import NamedField
from python_implementation.src.utils import as_signed_int, combine_bytes


class DecodeAccumulator:
    def __init__(self, instruction_schema: InstructionSchema):
        self.parsed_fields: dict[NamedField, int] = {}
        # We won't have this yet, we will add these when the instruction schema is discovered
        # self.parsed_fields: dict[NamedField, int] = dict(
        #     instruction_schema.implied_values
        # )

    def with_field(self, schema_field: NamedField, field_value: int):
        self.parsed_fields[schema_field] = field_value

    @cached_property
    def mode(self) -> Mode:
        """This one is special because it is used in checking if a field is needed"""
        mod_value = self.parsed_fields[NamedField.MOD]
        rm_value = self.parsed_fields.get(NamedField.RM)
        mode = Mode(mod_value, rm_value)
        logging.debug(f"locked in mode as {mode = }")
        return mode

    @cached_property
    def word(self):
        return bool(self.parsed_fields[NamedField.W])

    @cached_property
    def direction(self):
        return bool(self.parsed_fields[NamedField.D])

    @cached_property
    def sign_extension(self):
        return bool(self.parsed_fields[NamedField.S])

    @cached_property
    def displacement(self):
        disp = None
        if NamedField.DISP_LO in self.parsed_fields:
            disp = combine_bytes(
                self.parsed_fields[NamedField.DISP_LO],
                self.parsed_fields.get(NamedField.DISP_HI),
            )
            return as_signed_int(disp)

    @cached_property
    def data_operand(self):
        data_operand = None
        if NamedField.DATA in self.parsed_fields:
            data_operand = ImmediateOperand(
                value=combine_bytes(
                    self.parsed_fields[NamedField.DATA],
                    self.parsed_fields.get(NamedField.DATA_IF_W1),
                ),
                word=self.word,
            )
        return data_operand

    @cached_property
    def register_operand(self):
        reg_operand = None
        if NamedField.REG in self.parsed_fields:
            reg_operand = RegisterOperand(
                register_index=self.parsed_fields[NamedField.REG], word=self.word
            )
        return reg_operand

    @cached_property
    def rm_operand(self):
        rm_operand = None
        if NamedField.RM in self.parsed_fields:
            reg_or_mem_base = self.parsed_fields[NamedField.RM]
            if self.mode.type is Mode.Type.REGISTER_MODE:
                rm_operand = RegisterOperand(
                    register_index=reg_or_mem_base, word=self.word
                )
            else:
                rm_operand = MemoryOperand(
                    memory_base=(
                        None if self.mode.direct_memory_index else reg_or_mem_base
                    ),
                    displacement=self.displacement or 0,
                )
        return rm_operand

    def build(self, instruction_schema: InstructionSchema) -> DisassembledInstruction:
        assert not (
            self.data_operand and self.register_operand and self.rm_operand
        ), "Too many operands"

        if self.data_operand is not None:
            operands = [self.data_operand, self.register_operand or self.rm_operand]
        else:
            operands = [self.register_operand, self.rm_operand]

        if self.direction:
            operands.reverse()

        assert None not in operands, "Cannot have null source or dest"
        source, dest = operands

        return DisassembledInstruction(
            mnemonic=instruction_schema.mnemonic, source=source, dest=dest
        )
