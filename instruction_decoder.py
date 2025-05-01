#!/usr/bin/env python3

import os


def safe_next(it):
    try:
        return next(it)
    except StopIteration:
        return StopIteration


def parse_file_and_get_dissasembled_instructions(inp_file_name):
    with open(inp_file_name, "rb") as file:
        file_contents: bytes = file.read()

    # print(f"fc: {[f"{fc:x}" for fc in file_contents] = }")
    binary = iter(file_contents)
    instructions = []
    while (byte1 := safe_next(binary)) is not StopIteration:
        # print(f"byte1 = {byte1:x}")
        assert isinstance(byte1, int)

        # register/memory to/from register
        if (byte1 & 0b10001000) == 0b10001000:
            # bit 7 indicated direction of the move, 0 means source is reg field, 1 means destination in reg field
            direction_bit = bool(byte1 & 0b00000010)
            # bit 8 tells us if we use the 16 bit register or just lower 8 bits
            word_bit_set = bool(byte1 & 0b00000001)

            byte2 = next(binary)
            mode_bits = (byte2 & 0b11000000) >> 6

            r_m_bits = byte2 & 0b00000111

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

            # if mode is 11 it is register to register and we have a second register as the second operand
            if mode_bits == 0b11:
                reg_name_lower_and_word = [
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
                # first register is these bits
                reg_field_val = (byte2 & 0b00111000) >> 3
                reg_field_operand = reg_name_lower_and_word[reg_field_val][word_bit_set]

                # if mode is 11 it is register to register and we have a second register as the second operand
                r_m_field_operand = reg_name_lower_and_word[r_m_bits][word_bit_set]

                source_dest = [reg_field_operand, r_m_field_operand]
                if direction_bit:
                    source_dest = list(reversed(source_dest))
                source, dest = source_dest

                instructions.append(f"mov {dest}, {source}")

            else:
                equation = r_m_to_effective_addr_calc[r_m_bits]

                displacement = 0
                # 8 bit displacement
                if mode_bits & 0b01:
                    low_disp_byte = next(binary)
                    displacement += low_disp_byte

                # when mode is 0 no displacement unless r/m field is 11
                # when mode is 10 then 16 bit displacement
                if mode_bits & 0b10 or (mode_bits == 0 and r_m_bits == 0b00):
                    high_disp_byte = next(binary)
                    displacement += high_disp_byte << 8

                instructions.append(
                    " + ".join(equation)
                    + (f" + {displacement}" if displacement > 0 else "")
                )

        # immediate to register/memory
        # elif byte1 == 0b1011:
        #     mode_bits =

        else:
            left = [f"{b:x}" for b in binary]
            print(f"left: {left}")
            print(f"{instructions = }")

            raise ValueError(
                f"Didn't expect to get here, given input was: {" ".join([f"{b:08b}" for b in binary])}"
            )
    return instructions


def main():
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    # files_to_do = os.listdir(input_directory)
    # files_to_do = ["single_register_mov", "many_register_mov"]
    files_to_do = ["listing_0039_more_movs"]
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
