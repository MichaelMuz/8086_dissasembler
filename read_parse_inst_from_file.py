from dataclasses import dataclass
import json
import os
import re


def safe_next(it):
    try:
        return next(it)
    except StopIteration:
        return StopIteration


# @dataclass
# class Literal:
#     byte: int


# class Field:
#     byte_num: int
#     start_bit: int
#     field_size: int


# class InstructionAnatomy:
#     identifier: Literal
#     parts: list[Field]


field_type_bit_len: dict[str | int, int] = {
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


@dataclass
class ParsableInstruction:
    mnemonic: str
    instructions: list[str | int]
    implied_values: dict[str, str | int]


def get_parsable_instructions() -> list[ParsableInstruction]:
    parsable_instructions = []
    with open("better_json.json", "r") as file:
        data = json.load(file)

    for mnemonic_group in data["instructions"]:
        mnemonic = mnemonic_group["mnemonic"]
        variations = mnemonic_group["variations"]
        for variation in variations:
            form = variation["format"]
            implied_values = variation["implied_values"]
            instruction_parts = []
            # each comma separated group contains instruction parts that total a byte in size
            for this_byte in form.split(", "):
                current_start_bit = 0
                for this_inst_piece in this_byte.split(" "):
                    match this_inst_piece:
                        case x if mat := re.match("[01]+", x):
                            assert mat.end() > 0
                            assert mat.end() < 9
                            current_start_bit += mat.end()
                            instruction_parts.append(int(x, 2))
                        case x:
                            current_start_bit += field_type_bit_len[x]
                            instruction_parts.append(x)

                assert current_start_bit == 8
            assert isinstance(instruction_parts[0], int)
            parsable_instructions.append(
                ParsableInstruction(mnemonic, instruction_parts, implied_values)
            )
    return parsable_instructions


def disassemble(first_byte: int, parsable_instruction: ParsableInstruction):
    current_byte = first_byte
    inst_parts_iter = iter(parsable_instruction.instructions)
    bits_left = 8 - int.bit_length(next(inst_parts_iter))
    instruction_part_to_value: dict = {"mnemonic": parsable_instruction.mnemonic}
    for instruction_part in inst_parts_iter:
        print(f"{instruction_part = }")
        assert bits_left >= 0
        if bits_left == 0:
            bits_left = 8
        inst_part_size = field_type_bit_len[instruction_part]
        start_bit = bits_left - inst_part_size
        mask = (2**inst_part_size - 1) << start_bit
        print(f"comparing with {current_byte:0b}")
        field_value = (current_byte & mask) >> start_bit
        instruction_part_to_value[instruction_part] = field_value
        bits_left -= inst_part_size

    print(f"returning from disasemble")
    return instruction_part_to_value


def parse_instructions():
    parsable_instructions = get_parsable_instructions()

    input_directory = "./asm/assembled/"
    files_to_do = ["single_register_mov"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        with open(full_input_file_path, "rb") as file:
            file_contents: bytes = file.read()
        one_byte_at_a_time = iter(file_contents)

        disasembled_insts = []
        while (byte1 := safe_next(one_byte_at_a_time)) is not StopIteration:
            assert isinstance(byte1, int)
            parsable_instruction_template = None
            for parsable_instruction in parsable_instructions:
                identifier_literal = parsable_instruction.instructions[0]
                assert isinstance(identifier_literal, int)

                properly_shifted_literal = identifier_literal << (
                    8 - int.bit_length(identifier_literal)
                )
                if (byte1 & properly_shifted_literal) == properly_shifted_literal:
                    parsable_instruction_template = parsable_instruction
                    break
            assert parsable_instruction_template is not None
            disasembled_inst = disassemble(byte1, parsable_instruction_template)
            disasembled_insts.append(disasembled_inst)


if __name__ == "__main__":
    parse_instructions()
