from dataclasses import dataclass
import functools
import json
import os
import re
from typing import Iterator


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


def get_parsable_instructions(json_data_from_file: dict) -> list[ParsableInstruction]:
    parsable_instructions = []
    for mnemonic_group in json_data_from_file["instructions"]:
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


def get_from_so_far_dict_and_implied(
    key: str, so_far_dict: dict[str, int], parsable_instruction: ParsableInstruction
):
    val = parsable_instruction.implied_values.get(key, None) or so_far_dict.get(
        "mod", None
    )
    return val


def is_instruction_needed(
    parsable_instruction: ParsableInstruction,
    instruction_part: str,
    instruction_dict_so_far: dict[str, int],
) -> bool:
    this_check_val = functools.partial(
        get_from_so_far_dict_and_implied,
        so_far_dict=instruction_dict_so_far,
        parsable_instruction=parsable_instruction,
    )
    if (
        instruction_part not in parsable_instruction.implied_values
        and instruction_part in {"d", "w", "mod", "reg", "rm"}
    ):
        return True
    elif instruction_part == "data-if-w=1":
        return bool(this_check_val("w"))
    elif instruction_part.startswith("disp"):
        mod_val = this_check_val("mod")
        if mod_val == 0:
            return False
        elif mod_val == 1:
            return True
        elif mod_val == 0b10:
            return instruction_part.endswith("-hi")
        elif mod_val == 0b11:
            return (
                get_from_so_far_dict_and_implied(
                    "rm", instruction_dict_so_far, parsable_instruction
                )
                == 0b110
            )
        else:
            raise ValueError(f"mod has an unexpected value of {mod_val}")
    else:
        raise ValueError(f"don't know how to check if {instruction_part} is needed")


def disassemble(
    first_byte: int,
    inst_pull_iter: Iterator[int],
    parsable_instruction: ParsableInstruction,
) -> dict[str, int | str]:
    current_byte = first_byte
    inst_parts_iter = iter(parsable_instruction.instructions)

    instruction_literal = next(inst_parts_iter)
    assert isinstance(instruction_literal, int)
    bits_left = 8 - int.bit_length(instruction_literal)

    instruction_part_to_value: dict = {"mnemonic": parsable_instruction.mnemonic}
    for instruction_part in inst_parts_iter:
        print(f"{instruction_part = }")

        assert isinstance(instruction_part, str)
        if not is_instruction_needed(
            parsable_instruction, instruction_part, instruction_part_to_value
        ):
            continue

        if bits_left == 0:
            current_byte = next(inst_pull_iter)
            bits_left = 8
        assert bits_left > 0

        inst_part_size = field_type_bit_len[instruction_part]
        start_bit = bits_left - inst_part_size

        mask = (2**inst_part_size - 1) << start_bit
        field_value = (current_byte & mask) >> start_bit

        instruction_part_to_value[instruction_part] = field_value
        bits_left -= inst_part_size

    print(f"returning from disasemble")
    return instruction_part_to_value


def parse_instructions(
    parsable_instructions: list[ParsableInstruction], one_byte_at_a_time: Iterator[int]
) -> list[dict[str, int | str]]:
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
        disasembled_inst = disassemble(
            byte1, one_byte_at_a_time, parsable_instruction_template
        )
        disasembled_insts.append(disasembled_inst)
    print(f"{disasembled_insts = }")
    return disasembled_insts


def main():
    # get instructions that we know are possible

    with open("asm_config.json", "r") as file:
        json_data_from_file = json.load(file)
    parsable_instructions = get_parsable_instructions(json_data_from_file)

    input_directory = "./asm/assembled/"
    files_to_do = ["single_register_mov"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        with open(full_input_file_path, "rb") as file:
            file_contents: bytes = file.read()
        one_byte_at_a_time = iter(file_contents)
        file_parsed_results = parse_instructions(
            parsable_instructions, one_byte_at_a_time
        )
        print(f"for file {file_name}: \n{file_parsed_results}")


if __name__ == "__main__":
    main()
