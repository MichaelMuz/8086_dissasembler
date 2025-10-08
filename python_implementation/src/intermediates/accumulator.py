from functools import cached_property
from python_implementation.src.base.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.disassembled import (
    DisassembledBinaryInstruction,
    DisassembledInstruction,
    DisassembledJumpInstruction,
    DisassembledUnaryInstruction,
)
from python_implementation.src.intermediates.mode import Mode
from python_implementation.src.intermediates.operands import (
    ImmediateOperand,
    MemoryOperand,
    RegisterOperand,
)
from python_implementation.src.utils import BITS_PER_BYTE, as_signed_int, combine_bytes


class DecodeAccumulator:
    def __init__(self):
        self.parsed_fields: dict[NamedField, int] = {}
        self.bit_size = 0

    def with_field(self, schema_field: SchemaField, field_value: int):
        self.bit_size += schema_field.bit_width
        if isinstance(schema_field, NamedField):
            self.parsed_fields[schema_field] = field_value
        else:
            assert field_value == schema_field.literal_value

    def with_bit(self, _: bool):
        self.bit_size += 1

    def with_implied_fields(self, implied_fields: dict[NamedField, int]) -> None:
        assert self.parsed_fields.keys().isdisjoint(
            implied_fields.keys()
        ), "Given implied fields overlap with already parsed fields"
        self.parsed_fields.update(implied_fields)

    @cached_property
    def mode(self) -> Mode:
        """This one is special because it is used in checking if a field is needed"""
        mod_value = self.parsed_fields[NamedField.MOD]
        rm_value = self.parsed_fields.get(NamedField.RM)
        mode = Mode(mod_value, rm_value)
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
    def ip_inc8(self):
        return self.parsed_fields.get(NamedField.IP_INC8)

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

    def get_size(self):
        size, rem = divmod(self.bit_size, BITS_PER_BYTE)
        assert rem == 0, "Asking for size on incomplete instruction"
        return size

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

    def is_needed(self, field: SchemaField):
        if isinstance(field, LiteralField) or field.always_needed:
            return True

        match field:
            case field.DISP_LO:
                return self.mode.type in (
                    Mode.Type.WORD_DISPLACEMENT_MODE,
                    Mode.Type.BYTE_DISPLACEMENT_MODE,
                )
            case field.DISP_HI:
                return self.mode.type == Mode.Type.WORD_DISPLACEMENT_MODE
            case field.ADDR_HI:
                raise NotImplementedError("Don't use ADDR_HI yet")
            case field.DATA_IF_W1:
                return self.word
            case field.DATA_IF_SW_01:
                return not (self.sign_extension) and self.word
            case _:
                raise ValueError("I don't know how to check if this is needed")

    def build(self, instruction_schema: InstructionSchema) -> DisassembledInstruction:
        if self.ip_inc8:
            return DisassembledJumpInstruction(
                instruction_schema.mnemonic, self.ip_inc8, self.get_size()
            )
        operands = list(
            filter(None, [self.data_operand, self.register_operand, self.rm_operand])
        )

        match operands:
            case []:
                raise NotImplementedError("Can't do nullary yet")
            case [op]:
                return DisassembledUnaryInstruction(
                    mnemonic=instruction_schema.mnemonic,
                    op=op,
                    inst_size=self.get_size(),
                )
            case [source, dest]:
                if self.direction:
                    source, dest = dest, source
                return DisassembledBinaryInstruction(
                    mnemonic=instruction_schema.mnemonic,
                    source=source,
                    dest=dest,
                    inst_size=self.get_size(),
                )
            case _:
                raise ValueError(f"Unexpected operand count: {len(operands)}")
