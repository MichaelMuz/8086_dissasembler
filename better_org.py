from dataclasses import dataclass
import enum
import itertools
import re
from typing import Iterator, Self


@dataclass
class SchemaField:
    bit_width: int


class LiteralField(SchemaField):
    def __init__(self, literal_value, bit_width):
        self.literal_value = literal_value
        super().__init__(bit_width=bit_width)

    def is_match(self, other_int: int):
        assert int.bit_length(other_int) <= 8
        other_int_down_shifted = other_int >> (8 - self.bit_width)
        return other_int_down_shifted == self.literal_value


class NamedField(SchemaField):
    NAMED_FIELD_TYPE_TO_BIT_LEN: dict[str, int] = {
        "d": 1,
        "w": 1,
        "reg": 3,
        "mod": 2,
        "rm": 3,
        "disp-lo": 8,
        "disp-hi": 8,
        "addr-lo": 8,
        "addr-hi": 8,
        "data": 8,
        "data-if-w=1": 8,
    }

    def __init__(self, name: str):
        self.name = name
        super().__init__(bit_width=self.NAMED_FIELD_TYPE_TO_BIT_LEN[name])


@dataclass
class ParsedNamedField:
    named_field: NamedField
    parsed_value: int


@dataclass
class InstructionSchema:
    mnemonic: str
    identifier_literal: LiteralField
    fields: list[SchemaField]
    implied_values: list[ParsedNamedField]


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
                        assert mat.end() > 0
                        assert mat.end() < 9
                        this_field = LiteralField(int(this_inst_piece, 2), mat.end())
                    else:
                        this_field = NamedField(this_inst_piece)
                    schema_fields.append(this_field)
                assert current_start_bit == 8

            identifier_literal, schema_fields = schema_fields[0], schema_fields[1:]
            assert isinstance(
                identifier_literal, LiteralField
            ), "First parsed field always expected to be literal"

            implied_values = []
            for field_type, value in variation["implied_values"]:
                field = NamedField(field_type)
                implied_values.append(ParsedNamedField(field, value))

            instruction_schema = InstructionSchema(
                mnemonic=mnemonic,
                identifier_literal=identifier_literal,
                fields=schema_fields,
                implied_values=implied_values,
            )
            instruction_schemas.append(instruction_schema)
    return instruction_schemas


@dataclass
class DisassembledInstruction:
    instruction_schema: InstructionSchema
    parsed_fields: list[ParsedNamedField]


class Mode(enum.Enum):
    NO_DISPLACEMENT_MODE = enum.auto()
    BYTE_DISPLACEMENT_MODE = enum.auto()
    WORD_DISPLACEMENT_MODE = enum.auto()
    REGISTER_MODE = enum.auto()


def get_mode(mod_val: int, rm_val: int | None):
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


class DisassembledInstructionBuilder:
    ALWAYS_NEEDED_FIELDS = {"d", "w", "mod", "reg", "rm", "data"}

    def __init__(self, instruction_schema: InstructionSchema):
        self.instruction_schema = instruction_schema
        self.parsed_fields = {
            implied_value.named_field.name: implied_value
            for implied_value in instruction_schema.implied_values
        }
        self.implied_values = set(self.parsed_fields.keys())
        self.identifier_literal_added = False

    # def with_literal_field(self, literal_field: LiteralField, current_byte: int) -> Self:
    #     assert literal_field.is_match(current_byte)
    #     self.identifier_literal_added = True
    #     return self

    def with_literal_field(
        self, literal_field: LiteralField, parsed_value: int
    ) -> Self:
        assert literal_field.literal_value == parsed_value
        self.identifier_literal_added = True
        return self

    def with_named_field(self, parsed_named_field: ParsedNamedField) -> Self:
        assert self.identifier_literal_added, "Must add identifier literal first"
        self.parsed_fields[parsed_named_field.named_field.name] = parsed_named_field
        return self

    def build(self) -> DisassembledInstruction:
        return DisassembledInstruction(
            instruction_schema=self.instruction_schema,
            parsed_fields=list(self.parsed_fields.values()),
        )

    def is_needed(self, schema_field: SchemaField) -> bool:
        if isinstance(schema_field, LiteralField):
            return True

        assert isinstance(schema_field, NamedField)
        assert (
            schema_field.name not in self.implied_values
        ), f"Asking if {schema_field} is required but its value is already implied"

        if schema_field.name in self.ALWAYS_NEEDED_FIELDS:
            return True
        elif schema_field.name == "data-if-w=1":
            return bool(self.parsed_fields["w"].parsed_value)
        elif schema_field.name.startswith("disp"):
            mod_value = self.parsed_fields["mod"].parsed_value
            rm_value = None
            if "rm" in self.parsed_fields:
                rm_value = self.parsed_fields["rm"].parsed_value
            mode = get_mode(mod_value, rm_value)

            is_lo = schema_field.name.endswith("-lo")
            is_hi = schema_field.name.endswith("-hi")
            assert (
                is_lo or is_hi
            ), f"cannot have disp that isn't -hi or -lo: {schema_field.name}"

            return (mode == Mode.WORD_DISPLACEMENT_MODE) or (
                mode == Mode.BYTE_DISPLACEMENT_MODE and is_lo
            )
        else:
            raise ValueError(f"don't know how to check if {schema_field} is needed")


def disassemble_instruction(
    instruction_schema: InstructionSchema, byte_iter: Iterator[int]
) -> DisassembledInstruction:
    current_byte = next(byte_iter)
    bits_left = 8
    disassembled_instruction_builder = DisassembledInstructionBuilder(
        instruction_schema
    )
    for schema_field in instruction_schema.fields:
        # if isinstance(schema_field, LiteralField):
        #     disassembled_instruction_builder.with_literal_field(schema_field, current_byte)
        # elif isinstance(schema_field, NamedField):
        #     if not disassembled_instruction_builder.is_needed(schema_field):
        #         continue

        if not disassembled_instruction_builder.is_needed(schema_field):
            continue

        if bits_left == 0:
            current_byte = next(byte_iter)
            bits_left = 8
        assert bits_left > 0

        start_bit = bits_left - schema_field.bit_width
        mask = (2**schema_field.bit_width - 1) << start_bit
        field_value = (current_byte & mask) >> start_bit

        if isinstance(schema_field, LiteralField):
            disassembled_instruction_builder.with_literal_field(
                schema_field, field_value
            )
        elif isinstance(schema_field, NamedField):
            parsed_named_field = ParsedNamedField(schema_field, field_value)
            disassembled_instruction_builder.with_named_field(parsed_named_field)

        bits_left -= schema_field.bit_width

    return disassembled_instruction_builder.build()


def disassemble(
    possible_instructions: list[InstructionSchema], byte_iter: Iterator[int]
) -> list[DisassembledInstruction]:

    disassembled_instructions = []
    while current_byte := next(byte_iter, None) is not None:

        matching_schema = None
        for possible_instruction in possible_instructions:
            if possible_instruction.identifier_literal.is_match(current_byte):
                matching_schema = possible_instruction
                break
        assert matching_schema is not None

        disassembled_instruction = disassemble_instruction(
            matching_schema, itertools.chain([current_byte], byte_iter)
        )
        disassembled_instructions.append(disassembled_instruction)

    return disassembled_instructions


def disassemble_binary_to_string(
    possible_instructions: list[InstructionSchema], bytes_iter: bytes | Iterator[int]
):
    if isinstance(bytes_iter, bytes):
        bytes_iter = iter(bytes_iter)

    disassembled = disassemble(possible_instructions, bytes_iter)

    disassembly_as_str = "\n".join(["bits 16", *map(str, disassembled)])

    return disassembly_as_str
