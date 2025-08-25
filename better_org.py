from dataclasses import dataclass
import enum
from functools import cached_property
import json
import logging
import os
import re
from typing import Literal, TypeAlias


BITS_PER_BYTE = 8


def get_sub_bits(to_ind: int, start_ind: int, num_bits: int):
    r_shifted = to_ind >> start_ind
    mask = (1 << num_bits) - 1
    return r_shifted & mask


def get_sub_most_sig_bits(to_ind: int, msb_start_ind: int, num_bits: int):
    max_ind = BITS_PER_BYTE - 1
    end_ind = max_ind - msb_start_ind
    start_ind = end_ind - num_bits + 1  # includes start
    return get_sub_bits(to_ind, start_ind, num_bits)


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


class NamedField(enum.Enum):
    bit_width: int  # for type checker, this exists

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

    def __new__(cls, field_name: str, bit_width: int):
        obj = object.__new__(cls)
        obj._value_ = field_name
        obj.bit_width = bit_width
        return obj


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


def combine_bytes(low: int, high: int | None) -> int:
    if high is not None:
        return (high << 8) + low
    return low


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

    @cached_property
    def mode(self) -> Mode:
        mod_value = self.parsed_fields[NamedField.MOD]
        rm_value = self.parsed_fields.get(NamedField.RM)
        mode = get_mode(mod_value, rm_value)
        logging.debug(f"locked in mode as {mode = }")
        return mode

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

    def _format_operand(self, operand: Operand, word_val) -> str:
        match operand:
            case RegisterOperand():
                return self.REG_NAME_LOWER_AND_WORD[operand.register_index][word_val]
            case MemoryOperand():
                equation = list(self.RM_TO_EFFECTIVE_ADDR_CALC[operand.memory_base])
                if operand.displacement and operand.displacement > 0:
                    equation.append(str(operand.displacement))
                return f"[{' + '.join(equation)}]"
            case ImmediateOperand():
                return str(operand.value)

    def build(self) -> DisassembledInstruction:
        word_val = self.parsed_fields[NamedField.W]
        direction = self.parsed_fields[NamedField.D]

        disp = None
        if NamedField.DISP_LO in self.parsed_fields:
            disp = combine_bytes(
                self.parsed_fields[NamedField.DISP_LO],
                self.parsed_fields.get(NamedField.DISP_HI),
            )

        data_operand = None
        if NamedField.DATA in self.parsed_fields:
            data_operand = ImmediateOperand(
                value=combine_bytes(
                    self.parsed_fields[NamedField.DATA],
                    self.parsed_fields.get(NamedField.DATA_IF_W1),
                )
            )

        reg_operand = None
        if NamedField.REG in self.parsed_fields:
            reg_operand = RegisterOperand(
                register_index=self.parsed_fields[NamedField.REG]
            )

        rm_operand = None
        if NamedField.RM in self.parsed_fields:
            reg_or_mem_base = self.parsed_fields[NamedField.RM]
            if self.mode == Mode.REGISTER_MODE:
                rm_operand = RegisterOperand(register_index=reg_or_mem_base)
            else:
                rm_operand = MemoryOperand(
                    memory_base=reg_or_mem_base,
                    displacement=disp or 0,
                )

        assert not (data_operand and reg_operand and rm_operand), "Too many operands"

        if data_operand:
            # Immediate instruction: register/memory + immediate
            operands = [reg_operand or rm_operand, data_operand]
        else:
            # Register/memory instruction: rm + reg
            operands = [rm_operand, reg_operand]

        if bool(direction):
            operands.reverse()

        assert None not in operands, "Cannot have null source or dest"
        source, dest = (self._format_operand(op, word_val) for op in operands)

        return DisassembledInstruction(
            instruction_schema=self.instruction_schema,
            parsed_fields=self.parsed_fields,
            string_rep=f"{self.instruction_schema.mnemonic} {dest}, {source}",
        )

        # source = None
        # dest_val = None
        # if NamedField.DATA in self.parsed_fields:
        #     assert (NamedField.REG in self.parsed_fields) ^ (
        #         NamedField.RM in self.parsed_fields
        #     ), "Must have exactly one of reg or rm, not both or neither"

        #     dest_val = self.parsed_fields.get(
        #         NamedField.REG, self.parsed_fields.get(NamedField.RM)
        #     )
        #     assert dest_val is not None
        #     source = combine_bytes(  # the immediate in the data is source
        #         self.parsed_fields[NamedField.DATA],
        #         self.parsed_fields.get(NamedField.DATA_IF_W1),
        #     )
        # else:
        #     dest_val = self.parsed_fields[NamedField.RM]
        #     source = self.REG_NAME_LOWER_AND_WORD[self.parsed_fields[NamedField.REG]][
        #         word_val
        #     ]

        # if self.mode is Mode.REGISTER_MODE:
        #     dest = self.REG_NAME_LOWER_AND_WORD[dest_val][word_val]
        # else:
        #     equation = list(self.RM_TO_EFFECTIVE_ADDR_CALC[dest_val])

        #     if NamedField.DISP_LO in self.parsed_fields:
        #         disp = combine_bytes(
        #             self.parsed_fields[NamedField.DISP_LO],
        #             self.parsed_fields.get(NamedField.DISP_HI),
        #         )
        #         if disp != 0:
        #             equation.append(str(disp))
        #     str_equation = " + ".join(equation)
        #     dest = f"[{str_equation}]"

        # if bool(direction):
        #     source, dest = dest, source

        # assert source is not None and dest is not None
        # logging.debug(f"{self.mode = }")


class BitIterator:
    def __init__(self, b: bytes):
        self.inst_bytes = b
        self.iterator = iter(b)
        self.curr_byte = None
        self.byte_ind = -1
        self.msb_bit_ind = BITS_PER_BYTE

    def _grab_byte(self):
        self.curr_byte = next(self.iterator, None)
        self.byte_ind += 1
        self.msb_bit_ind = 0

        logging.debug(f"grabbing byte, it was: {self.curr_byte}")
        return self.curr_byte is None

    def next_bits(self, num_bits: int):
        logging.debug(f"request for: {num_bits = }")
        if num_bits > BITS_PER_BYTE:
            raise ValueError("Our ISA does not have fields larger than a byte")
        assert num_bits > 0

        if self.msb_bit_ind == BITS_PER_BYTE:
            ended = self._grab_byte()
            assert not ended, "Instruction stream ended in the middle of an instruction"

        assert self.curr_byte is not None, "invariant"

        bits_left = BITS_PER_BYTE - self.msb_bit_ind
        if num_bits > bits_left:
            logging.info(f"{self.msb_bit_ind = }, {bits_left = }")
            raise ValueError(
                "Our ISA does not have fields that straddle byte boundaries"
            )

        field_value = get_sub_most_sig_bits(self.curr_byte, self.msb_bit_ind, num_bits)

        self.msb_bit_ind += num_bits
        return field_value

    def peek_whole_byte(self):
        if self.msb_bit_ind == BITS_PER_BYTE:
            self._grab_byte()
        elif self.msb_bit_ind != 0:
            raise ValueError("Tried to peek incomplete byte")
        return self.curr_byte


def disassemble_instruction(
    instruction_schema: InstructionSchema, bit_iter: BitIterator
) -> DisassembledInstruction:

    disassembled_instruction_builder = DisassembledInstructionBuilder(
        instruction_schema,
        bit_iter.next_bits(instruction_schema.identifier_literal.bit_width),
    )

    for schema_field in instruction_schema.fields:
        if not disassembled_instruction_builder.is_needed(schema_field):
            logging.debug(f"{schema_field = } not needed")
            continue

        logging.debug(f"{schema_field = } needed")
        logging.debug(f"curr byte: {bit_iter.curr_byte:08b} {bit_iter.msb_bit_ind = }")
        field_value = bit_iter.next_bits(schema_field.bit_width)
        logging.debug(f"has value {field_value = }")
        logging.debug(f"curr byte: {bit_iter.curr_byte:08b} {bit_iter.msb_bit_ind = }")
        disassembled_instruction_builder.with_field(schema_field, field_value)

    return disassembled_instruction_builder.build()


def disassemble(
    possible_instructions: list[InstructionSchema], bit_iter: BitIterator
) -> list[DisassembledInstruction]:

    disassembled_instructions = []
    while (current_byte := bit_iter.peek_whole_byte()) is not None:
        logging.debug("starting new instruction")

        matching_schema = None
        for possible_instruction in possible_instructions:
            if possible_instruction.identifier_literal.is_match(current_byte):
                matching_schema = possible_instruction
                logging.debug(
                    f"found matching schema: {matching_schema.identifier_literal.literal_value}"
                )
                break
        assert matching_schema is not None

        disassembled_instruction = disassemble_instruction(matching_schema, bit_iter)
        logging.debug(
            f"{disassembled_instruction.string_rep = }:\n{disassembled_instruction.parsed_fields = }"
        )
        disassembled_instructions.append(disassembled_instruction)

    return disassembled_instructions


def disassemble_binary_to_string(
    possible_instructions: list[InstructionSchema], b: bytes
) -> str:
    logging.debug("disassembler seeing:\n" + " ".join([f"{by:08b}" for by in b]))
    bit_iter = BitIterator(b)
    disassembled = disassemble(possible_instructions, bit_iter)

    disassembly_as_str = "\n".join(
        ["bits 16", *[dis.string_rep for dis in disassembled]]
    )
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
