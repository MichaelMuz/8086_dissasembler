#!/usr/bin/env python3

from dataclasses import dataclass
import enum
import os


def safe_next(it):
    try:
        return next(it)
    except StopIteration:
        return StopIteration


def is_bit_set(num, bit_num):
    return bool((num >> bit_num) & 0b1)


class Mode(enum.Enum):
    NO_DISPLACEMENT_MODE = enum.auto()
    BYTE_DISPLACEMENT_MODE = enum.auto()
    WORD_DISPLACEMENT_MODE = enum.auto()
    REGISTER_MODE = enum.auto()


def get_mode(num, first_mode_bit_num, rm):
    all_modes = [
        Mode.NO_DISPLACEMENT_MODE,
        Mode.BYTE_DISPLACEMENT_MODE,
        Mode.WORD_DISPLACEMENT_MODE,
        Mode.REGISTER_MODE,
    ]

    mode = all_modes[(num >> first_mode_bit_num) & 0b11]
    if mode is Mode.NO_DISPLACEMENT_MODE and rm.value == 0b110:
        mode = Mode.WORD_DISPLACEMENT_MODE

    return mode


class Register:
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

    def __init__(self, num, first_reg_bit_num, word_bit_set) -> None:
        self.value = (num >> first_reg_bit_num) & 0b111
        self.register = self.REG_NAME_LOWER_AND_WORD[self.reg_value][word_bit_set]


class RM:
    r_m_to_effective_addr_calc = [
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

    def __init__(self, num, first_rm_bit_num) -> None:
        self.value = (num >> first_rm_bit_num) & 0b111
        self.effective_addr_regs = self.r_m_to_effective_addr_calc[self.value]


def do_bits_match(num, expected):
    return (num & expected) == expected


def convert_to_signed(x, num_bytes):
    """
    We don't really need to do this because the way we display the number in decimal doesn't matter
    the bytes are the same if we display 0b1001 as -7 or 9.
    This is only here because it is just nice to see it match, as a human
    """
    twos_compliment_bit_value = 1 << (num_bytes * 8 - 1)
    if x & twos_compliment_bit_value == 0:
        return x
    unsigned_bit_pattern = x & (twos_compliment_bit_value - 1)
    return int(unsigned_bit_pattern) - int(twos_compliment_bit_value)


class Instruction:
    def __init__(self, source, dest, direction_bit_set) -> None:
        src_dst = [source, dest]
        if direction_bit_set:
            src_dst = reversed(src_dst)
        self.source, self.dest = src_dst


def parse_file_and_get_dissasembled_instructions(inp_file_name):
    with open(inp_file_name, "rb") as file:
        file_contents: bytes = file.read()

    binary = iter(file_contents)
    instructions = []
    while (byte1 := safe_next(binary)) is not StopIteration:
        assert isinstance(byte1, int)

        is_regmem_tofrom_regmem = do_bits_match(byte1, 0b10001000)
        is_immediate_move = do_bits_match(byte1, 0b11000110)
        is_immediate_to_reg = do_bits_match(byte1, 0b10110000)

        # register/memory to/from register
        if is_regmem_tofrom_regmem or is_immediate_move or is_immediate_to_reg:

            # bit 7 indicated direction of the move, 0 means source is reg field, 1 means destination in reg field
            direction_bit = is_bit_set(byte1, 1)

            byte2 = next(binary)
            rm = RM(byte2, 0)
            mode = get_mode(byte2, 6, rm)

            byte_with_reg_info = byte2
            reg_field_start = 3
            word_bit = 0
            if is_immediate_to_reg:
                byte_with_reg_info = byte1
                word_bit = 3
                reg_field_start = 0

            word_bit_set = is_bit_set(byte1, word_bit)
            reg = Register(byte_with_reg_info, reg_field_start, word_bit_set)

            if is_immediate_move:
                assert reg.value == 0, "immediate mov expected to have 0 in reg field"

            if mode == Mode.REGISTER_MODE or is_immediate_to_reg:
                second_operand = Register(rm.value, 0, word_bit_set)

                if is_immediate_move or is_immediate_to_reg:

                    data_byte_for_bottom_of_reg = (
                        byte2 if is_immediate_to_reg else next(binary)
                    )
                    num = data_byte_for_bottom_of_reg
                    if word_bit_set:
                        num += next(binary) << 8
                    second_operand = num
                inst = Instruction(reg, second_operand, direction_bit)

                instructions.append(inst)
            elif is_immediate_to_reg:
                raise ValueError("immediate to reg not caught in reg to reg!")

            else:
                equation = r_m_to_effective_addr_calc[rm]

                displacement = 0
                # 8 bit displacement
                if (mode & 0b11) or (mode == 0 and rm == 0b110):
                    low_disp_byte = next(binary)
                    displacement += low_disp_byte

                # when mode is 0 no displacement unless r/m field is 110
                # when mode is 10 then 16 bit displacement
                is_2_bytes = False
                if (mode & 0b10) == 0b10 or (mode == 0 and rm == 0b110):
                    is_2_bytes = True
                    high_disp_byte = next(binary)
                    displacement += high_disp_byte << 8

                signed_displacement = convert_to_signed(
                    displacement, 1 + int(is_2_bytes)
                )
                full_memory_equation = " + ".join(equation)
                if displacement > 0:
                    sign = "+" if signed_displacement >= 0 else "-"
                    full_memory_equation += f" {sign} {abs(signed_displacement)}"
                full_memory_equation = f"[{full_memory_equation}]"

                if mode == 0 and rm == 0b110:
                    full_memory_equation = f"[{signed_displacement}]"

                source_dest = [reg_field_operand, full_memory_equation]
                if direction_bit:
                    source_dest = list(reversed(source_dest))
                source, dest = source_dest

                if is_immediate_move:
                    dest = full_memory_equation
                    byte3 = next(binary)
                    source = byte3
                    if word_bit_set:
                        byte4 = next(binary)
                        source = (byte4 << 8) + byte3
                    verbage = "word" if word_bit_set else "byte"
                    source = (
                        f"{verbage} {convert_to_signed(source, 1 + int(word_bit_set))}"
                    )

                instructions.append(f"mov {dest}, {source}")

        # memory to/from accumulator
        elif (byte1 & 0b10100000) == 0b10100000:
            mem = next(binary)
            word_bit_set = word_bit_set = bool(byte1 & 0b00000001)
            from_accum = (byte1 & 0b00000010) >> 1
            if word_bit_set:
                mem += next(binary) << 8
            source_dest = [f"[{mem}]", "ax"]
            if from_accum:
                source_dest = reversed(source_dest)
            source, dest = source_dest
            instructions.append(f"mov {dest}, {source}")
        else:
            left = [f"{b:x}" for b in binary]

            error_msg = f"Didn't expect to get here, current input was: {byte1:08b}"
            raise ValueError(error_msg)
    return instructions


def main():
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    files_to_do = os.listdir(input_directory)
    # files_to_do = ["single_register_mov", "many_register_mov", "listing_0039_more_movs", "listing_0040_challenge_movs"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        instructions = parse_file_and_get_dissasembled_instructions(
            full_input_file_path
        )

        ouput_full_file_path = os.path.join(output_directory, f"{file_name}.asm")
        with open(ouput_full_file_path, "w") as file_name:
            file_name.write("bits 16\n\n")
            file_name.write("\n".join(instructions))


if __name__ == "__main__":
    main()
