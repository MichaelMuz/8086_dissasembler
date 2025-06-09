from dataclasses import dataclass
import enum
import functools
import json
import os
import re
from typing import Iterator


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
class InstructionLiteral:
    literal: int
    size: int

    def is_match(self, other_int: int):
        print(f"other int: {other_int:08b}")
        assert int.bit_length(other_int) <= 8
        other_int_down_shifted = other_int >> (8 - self.size)
        print(f"comparing me: {self.literal:08b}, to: {other_int_down_shifted:08b}")
        if other_int_down_shifted == self.literal:
            return True
        return False


@dataclass
class ParsableInstruction:
    mnemonic: str
    identifier_literal: InstructionLiteral
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
                            instruction_parts.append(
                                InstructionLiteral(int(x, 2), mat.end())
                            )
                        case x:
                            current_start_bit += field_type_bit_len[x]
                            instruction_parts.append(x)

                assert current_start_bit == 8
            identifier_literal, rest_of_instruction = (
                instruction_parts[0],
                instruction_parts[1:],
            )
            parsable_instructions.append(
                ParsableInstruction(
                    mnemonic,
                    identifier_literal,
                    rest_of_instruction,
                    implied_values,
                )
            )
    return parsable_instructions


def get_from_so_far_dict_and_implied(
    key: str, so_far_dict: dict[str, int], parsable_instruction: ParsableInstruction
):
    val = parsable_instruction.implied_values.get(key, None) or so_far_dict.get(
        key, None
    )
    return val


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
        and instruction_part in {"d", "w", "mod", "reg", "rm", "data"}
    ):
        return True
    elif instruction_part == "data-if-w=1":
        return bool(this_check_val("w"))
    elif instruction_part.startswith("disp"):
        mod_val = this_check_val("mod")
        rm_val = this_check_val("rm")
        mode = get_mode(mod_val, rm_val)
        print(f"displacement mode: {mode}")
        is_lo = instruction_part.endswith("-lo")
        is_hi = instruction_part.endswith("-hi")
        assert (
            is_lo or is_hi
        ), f"cannot have disp that isn't -hi or -lo: {instruction_part}"

        needed = (mode == Mode.WORD_DISPLACEMENT_MODE) or (
            mode == Mode.BYTE_DISPLACEMENT_MODE and is_lo
        )
        return needed
    else:
        raise ValueError(f"don't know how to check if {instruction_part} is needed")


def disassemble(
    first_byte: int,
    inst_pull_iter: Iterator[int],
    parsable_instruction: ParsableInstruction,
) -> dict[str, int | str]:
    current_byte = first_byte
    inst_parts_iter = iter(parsable_instruction.instructions)

    bits_left = 8 - parsable_instruction.identifier_literal.size

    instruction_part_to_value: dict = {"mnemonic": parsable_instruction.mnemonic}
    for instruction_part in inst_parts_iter:
        print(f"{instruction_part = }")
        print(f"{instruction_part_to_value = }")

        assert isinstance(instruction_part, str)
        if not is_instruction_needed(
            parsable_instruction, instruction_part, instruction_part_to_value
        ):
            print("not needed")
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
    assert (
        len(
            set(instruction_part_to_value).intersection(
                parsable_instruction.implied_values
            )
        )
        == 0
    ), f"{instruction_part_to_value = } {parsable_instruction.implied_values = }"

    return {**instruction_part_to_value, **parsable_instruction.implied_values}


def parse_instructions(
    parsable_instructions: list[ParsableInstruction], one_byte_at_a_time: Iterator[int]
) -> list[dict[str, int | str]]:
    disasembled_insts = []
    while (byte1 := next(one_byte_at_a_time, None)) is not None:
        print(f"byte1: {byte1:08b}")
        assert isinstance(byte1, int)
        parsable_instruction_template = None
        for parsable_instruction in parsable_instructions:
            if parsable_instruction.identifier_literal.is_match(byte1):
                parsable_instruction_template = parsable_instruction
                break
        all_inst = [
            f"{ins.identifier_literal.literal:0b}" for ins in parsable_instructions
        ]
        assert (
            parsable_instruction_template is not None
        ), f"didn't catch what {parsable_instruction.identifier_literal.literal:0b} is {all_inst = }"
        print(
            f"it is {parsable_instruction.identifier_literal.literal:0b} for {byte1:0b}"
        )
        disasembled_inst = disassemble(
            byte1, one_byte_at_a_time, parsable_instruction_template
        )
        disasembled_insts.append(disasembled_inst)
    print(f"{disasembled_insts = }")
    return disasembled_insts


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


def get_reg(reg_val: int, w: bool):
    return REG_NAME_LOWER_AND_WORD[reg_val][w]


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


# def combine_bytes(
#     parsed_instruction: dict[str, int], low: str, high: str
# ) -> int | None:
#     if low not in parsed_instruction:
#         return None

#     total = parsed_instruction[low]
#     high_val = parsed_instruction.get(high, 0)
#     if high != 0:
#         total += high_val << 8
#     return total


def combine_bytes(low: int, high: int) -> int | None:
    if high != 0:
        return (high << 8) + low
    return low


def get_disassembled_string(parsed_instruction: dict) -> str:
    # when we are here we assume we only have keys that correspond to values that are relevent
    # for example we shouldn't have disp-hi if we didn't need it for this instruction

    # everything has these
    mnemonic = parsed_instruction["mnemonic"]
    word_val = parsed_instruction["w"]
    direction = parsed_instruction["d"]
    mod_val = parsed_instruction["mod"]

    mode = get_mode(mod_val, parsed_instruction.get("rm"))

    source = None
    dest_val = None
    if "data" in parsed_instruction:
        # can't have data, reg, and rm in one instruction
        has_reg = "reg" in parsed_instruction
        has_rm = "rm" in parsed_instruction
        assert not (has_reg and has_rm)
        assert has_reg or has_rm

        dest_val = parsed_instruction.get("reg", parsed_instruction.get("rm"))
        assert dest_val is not None
        source = combine_bytes(  # the immediate in the data is source
            parsed_instruction["data"], parsed_instruction.get("data-if-w=1", 0)
        )
    else:
        dest_val = parsed_instruction["rm"]
        source = get_reg(parsed_instruction["reg"], word_val)

    if mode is Mode.REGISTER_MODE:
        dest = get_reg(dest_val, word_val)
    else:
        equation = list(RM_TO_EFFECTIVE_ADDR_CALC[dest_val])

        if "disp-lo" in parsed_instruction:
            disp = combine_bytes(
                parsed_instruction["disp-lo"], parsed_instruction.get("disp-hi", 0)
            )
            if disp != 0:
                equation.append(str(disp))
        str_equation = " + ".join(equation)
        dest = f"[{str_equation}]"

    assert source is not None
    assert dest is not None

    if direction:
        source, dest = dest, source

    return f"{mnemonic} {dest}, {source}"


PARSABLE_INSTRUCTION_FILE = "asm_config.json"


def get_parsable_instructions_from_file():
    with open(PARSABLE_INSTRUCTION_FILE, "r") as file:
        json_data_from_file = json.load(file)
    parsable_instructions = get_parsable_instructions(json_data_from_file)
    return parsable_instructions


def disassemble_binary_to_string(
    parsable_instructions: list[ParsableInstruction], file_contents: bytes
) -> str:
    one_byte_at_a_time = iter(file_contents)

    # get the value for each field as per the possible instructions
    parsed_instructions = parse_instructions(parsable_instructions, one_byte_at_a_time)
    # get the string representation of each instruction
    disassembly = "\n".join(
        ["bits 16", *map(get_disassembled_string, parsed_instructions)]
    )
    return disassembly


def main():
    # get list of possible instructions and how to parse them
    parsable_instructions = get_parsable_instructions_from_file()
    input_directory = "./asm/assembled/"
    output_directory = "./asm/disassembled/"
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
