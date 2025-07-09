from dataclasses import dataclass
import enum
import itertools
import json
import os
import re
from typing import Iterator, Self, TypeAlias


@dataclass
class SchemaField:
    bit_width: int


class LiteralField(SchemaField):
    def __init__(self, literal_value, bit_width):
        self.literal_value = literal_value
        super().__init__(bit_width=bit_width)

    def is_match(self, other_int: int):
        print(f"other int: {other_int:08b}")
        assert int.bit_length(other_int) <= 8
        other_int_down_shifted = other_int >> (8 - self.bit_width)
        print(
            f"comparing me: {self.literal_value:08b}, to: {other_int_down_shifted:08b}"
        )
        return other_int_down_shifted == self.literal_value


class NamedField(SchemaField, enum.Enum):
    D = ("d", 1)
    W = ("w", 1)
    REG = ("reg", 3)
    MOD = ("mod", 2)
    RM = ("rm", 3)
    DISP_LO = ("disp-lo", 8)
    DISP_HI = ("disp-hi", 8)
    ADDR_LO = ("addr-lo", 8)
    ADDR_HI = ("addr-hi", 8)
    DATA = ("data", 8)
    DATA_IF_W1 = ("data-if-w=1", 8)

    def __new__(cls, field_name, bit_length):
        obj = object.__new__(cls)
        obj._value_ = field_name
        return obj

    def __init__(self, field_name, bit_length):
        super().__init__(bit_length)


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
                        assert mat.end() > 0
                        assert mat.end() < 9
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


@dataclass
class DisassembledInstruction:
    instruction_schema: InstructionSchema
    parsed_fields: ParsedNamedField
    string_rep: str


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


def combine_bytes(low: int, high: int | None) -> int | None:
    if high is not None:
        return (high << 8) + low
    return low


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
    ALWAYS_NEEDED_FIELDS = {"d", "w", "mod", "reg", "rm", "data"}

    def __init__(self, instruction_schema: InstructionSchema):
        self.instruction_schema = instruction_schema
        self.parsed_fields = {
            named_field: implied_value
            for named_field, implied_value in instruction_schema.implied_values.items()
        }
        self.implied_values = set(self.parsed_fields.keys())
        self.identifier_literal_added = False
        self.mode = None

    def with_field(self, schema_field: SchemaField, field_value):
        if isinstance(schema_field, LiteralField):
            assert schema_field.literal_value == field_value
            self.identifier_literal_added = True
        elif isinstance(schema_field, NamedField):
            assert self.identifier_literal_added, "Must add identifier literal first"
            self.parsed_fields[schema_field] = field_value
        else:
            raise TypeError("Unexpected subclass")
        return self

    def build(self) -> DisassembledInstruction:
        self.ensure_mode()
        word_val = self.parsed_fields[NamedField.W]
        direction = self.parsed_fields[NamedField.D]

        source = None
        dest_val = None
        if "data" in self.parsed_fields:
            # can't have data, reg, and rm in one instruction
            has_reg = "reg" in self.parsed_fields
            has_rm = "rm" in self.parsed_fields
            assert not (has_reg and has_rm)
            assert has_reg or has_rm

            dest_val = self.parsed_fields.get(
                NamedField.REG, self.parsed_fields.get(NamedField.RM)
            )
            assert dest_val is not None
            source = combine_bytes(  # the immediate in the data is source
                self.parsed_fields[NamedField.DATA],
                self.parsed_fields.get(NamedField.DATA_IF_W1),
            )
        else:
            dest_val = self.parsed_fields[NamedField.RM]
            source = self.REG_NAME_LOWER_AND_WORD[self.parsed_fields[NamedField.REG]][
                word_val
            ]

        if self.mode is Mode.REGISTER_MODE:
            dest = self.REG_NAME_LOWER_AND_WORD[dest_val][word_val]
        else:
            equation = list(self.RM_TO_EFFECTIVE_ADDR_CALC[dest_val])

            if "disp-lo" in self.parsed_fields:
                disp = combine_bytes(
                    self.parsed_fields[NamedField.DISP_LO],
                    self.parsed_fields.get(NamedField.DISP_HI),
                )
                if disp != 0:
                    equation.append(str(disp))
            str_equation = " + ".join(equation)
            dest = f"[{str_equation}]"

        assert source is not None
        assert dest is not None

        if bool(direction):
            source, dest = dest, source

        return DisassembledInstruction(
            instruction_schema=self.instruction_schema,
            parsed_fields=self.parsed_fields,
            string_rep=f"{self.instruction_schema.mnemonic} {dest}, {source}",
        )

    def ensure_mode(self):
        mod_value = self.parsed_fields[NamedField.W]
        rm_value = None
        if "rm" in self.parsed_fields:
            rm_value = self.parsed_fields[NamedField.RM]
        self.mode = get_mode(mod_value, rm_value)

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
            return bool(self.parsed_fields[NamedField.W])
        elif schema_field.name.startswith("disp"):
            self.ensure_mode()

            is_lo = schema_field.name.endswith("-lo")
            is_hi = schema_field.name.endswith("-hi")
            assert (
                is_lo or is_hi
            ), f"cannot have disp that isn't -hi or -lo: {schema_field.name}"

            return (self.mode == Mode.WORD_DISPLACEMENT_MODE) or (
                self.mode == Mode.BYTE_DISPLACEMENT_MODE and is_lo
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
    for schema_field in itertools.chain(
        [instruction_schema.identifier_literal], instruction_schema.fields
    ):
        # if isinstance(schema_field, LiteralField):
        #     disassembled_instruction_builder.with_literal_field(schema_field, current_byte)
        # elif isinstance(schema_field, NamedField):
        #     if not disassembled_instruction_builder.is_needed(schema_field):
        #         continue

        print(f"{schema_field = }, {current_byte = }")
        if not disassembled_instruction_builder.is_needed(schema_field):
            continue

        if bits_left == 0:
            current_byte = next(byte_iter)
            bits_left = 8
        assert bits_left > 0

        start_bit = bits_left - schema_field.bit_width
        mask = (2**schema_field.bit_width - 1) << start_bit
        field_value = (current_byte & mask) >> start_bit
        disassembled_instruction_builder.with_field(schema_field, field_value)
        bits_left -= schema_field.bit_width

    return disassembled_instruction_builder.build()


def disassemble(
    possible_instructions: list[InstructionSchema], byte_iter: Iterator[int]
) -> list[DisassembledInstruction]:

    # print("disassembler seeing:\n" + " ".join([f"{by:08b}" for by in byte_iter]))
    # print(f"will see: {next(byte_iter) = }")
    disassembled_instructions = []
    while (current_byte := next(byte_iter, None)) is not None:

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
) -> str:
    # print("disassembler seeing:\n" + " ".join([f"{by:08b}" for by in bytes_iter]))
    if isinstance(bytes_iter, bytes):
        bytes_iter = iter(bytes_iter)

    disassembled = disassemble(possible_instructions, bytes_iter)

    disassembly_as_str = "\n".join(
        ["bits 16", *[dis.string_rep for dis in disassembled]]
    )
    print(f"returning {disassembly_as_str = }")

    return disassembly_as_str


def get_parsable_instructions_from_file():
    parsable_instruction_file = "asm_config.json"
    with open(parsable_instruction_file, "r") as file:
        json_data_from_file = json.load(file)
    return get_parsable_instructions(json_data_from_file)


def main():
    # get list of possible instructions and how to parse them
    parsable_instructions = get_parsable_instructions_from_file()
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    files_to_do = ["single_register_mov", "many_register_mov", "listing_0039_more_movs"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        with open(full_input_file_path, "rb") as file:
            file_contents: bytes = file.read()
        disassembled = disassemble_binary_to_string(
            parsable_instructions, file_contents
        )
        full_output_file_path = os.path.join(output_directory, file_name + ".asm")
        with open(full_output_file_path, "w") as f:
            f.write(disassembled)


if __name__ == "__main__":
    main()
