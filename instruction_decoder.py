#!/usr/bin/env python3

import os


def safe_next(it):
    try:
        return next(it)
    except StopIteration:
        return StopIteration


def convert_to_signed(x, num_bytes):
    twos_compliment_bit_value = 1 << (num_bytes * 8 - 1)
    if x & twos_compliment_bit_value == 0:
        return x
    unsigned_bit_pattern = x & (twos_compliment_bit_value - 1)
    return int(unsigned_bit_pattern) - int(twos_compliment_bit_value)


def parse_file_and_get_dissasembled_instructions(inp_file_name):
    with open(inp_file_name, "rb") as file:
        file_contents: bytes = file.read()

    print(f"fc: {[f"{fc:x}" for fc in file_contents] = }")
    binary = iter(file_contents)
    instructions = []
    while (byte1 := safe_next(binary)) is not StopIteration:
        assert isinstance(byte1, int)
        # print(f"current byte: {byte1:08b}")
        print(f"current byte: {byte1:x}")

        is_immediate_move = (byte1 & 0b11000110) == 0b11000110
        is_immediate_to_reg = (byte1 & 0b10110000) == 0b10110000

        # register/memory to/from register
        if (
            (byte1 & 0b10001000) == 0b10001000
            or is_immediate_move
            or is_immediate_to_reg
        ):

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

            # register is these bits
            reg_field_val = (byte2 & 0b00111000) >> 3
            if is_immediate_to_reg:
                word_bit_set = (byte1 & 0b00001000) >> 3
                reg_field_val = byte1 & 0b00000111

            reg_field_operand = reg_name_lower_and_word[reg_field_val][word_bit_set]
            print(f"operating of {reg_field_operand = }")

            if is_immediate_move:
                assert (
                    reg_field_val == 0
                ), "immediate mov expected to have 0 in reg field"

            # if mode is 11 it is register to register and we have a second register as the second operand
            if mode_bits == 0b11 or is_immediate_to_reg:
                # if mode is 11 it is register to register and we have a second register as the second operand
                r_m_field_operand = reg_name_lower_and_word[r_m_bits][word_bit_set]

                source_dest = [reg_field_operand, r_m_field_operand]
                if direction_bit:
                    source_dest = list(reversed(source_dest))
                source, dest = source_dest

                if is_immediate_move or is_immediate_to_reg:
                    dest = reg_field_operand
                    data_byte_for_bottom_of_reg = (
                        byte2 if is_immediate_to_reg else next(binary)
                    )
                    source = data_byte_for_bottom_of_reg
                    if word_bit_set:
                        data_byte_for_top_of_reg = next(binary)
                        source = (
                            data_byte_for_top_of_reg << 8
                        ) + data_byte_for_bottom_of_reg
                    source = convert_to_signed(source, 1 + int(word_bit_set))

                instructions.append(f"mov {dest}, {source}")
            elif is_immediate_to_reg:
                raise ValueError("immediate to reg not caught in reg to reg!")

            else:
                equation = r_m_to_effective_addr_calc[r_m_bits]

                displacement = 0
                # 8 bit displacement
                print(f"{mode_bits = }")
                print(f"{r_m_bits = }")
                print(f"{direction_bit = }")
                if (mode_bits & 0b11) or (mode_bits == 0 and r_m_bits == 0b110):
                    print(f"8 bit displacement")
                    low_disp_byte = next(binary)
                    displacement += low_disp_byte

                # when mode is 0 no displacement unless r/m field is 110
                # when mode is 10 then 16 bit displacement
                is_2_bytes = False
                if (mode_bits & 0b10) == 0b10 or (mode_bits == 0 and r_m_bits == 0b110):
                    is_2_bytes = True
                    print(f"16 bit displacement")
                    high_disp_byte = next(binary)
                    print(
                        f"low byte: {displacement:08b}, high byte: {high_disp_byte:08b}"
                    )
                    displacement += high_disp_byte << 8

                if displacement > 0:
                    print(f"{displacement = }")

                signed_displacement = convert_to_signed(
                    displacement, 1 + int(is_2_bytes)
                )
                full_memory_equation = " + ".join(equation)
                if displacement > 0:
                    sign = "+" if signed_displacement >= 0 else "-"
                    full_memory_equation += f" {sign} {abs(signed_displacement)}"
                full_memory_equation = f"[{full_memory_equation}]"

                if mode_bits == 0 and r_m_bits == 0b110:
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
                        print(f"byte3 = {byte3:08b}, byte4 = {byte4:08b}")
                        source = (byte4 << 8) + byte3
                    verbage = "word" if word_bit_set else "byte"
                    source = (
                        f"{verbage} {convert_to_signed(source, 1 + int(word_bit_set))}"
                    )

                instructions.append(f"mov {dest}, {source}")

        else:
            left = [f"{b:x}" for b in binary]
            print(f"left: {left}")
            print(f"{instructions = }")

            error_msg = f"Didn't expect to get here, current input was: {byte1:08b}"
            raise ValueError(error_msg)
    return instructions


def main():
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    # files_to_do = os.listdir(input_directory)
    # files_to_do = ["single_register_mov", "many_register_mov", "listing_0039_more_movs"]
    files_to_do = ["listing_0040_challenge_movs"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        instructions = parse_file_and_get_dissasembled_instructions(
            full_input_file_path
        )
        print(instructions)

        ouput_full_file_path = os.path.join(output_directory, f"{file_name}.asm")
        with open(ouput_full_file_path, "w") as file_name:
            file_name.write("bits 16\n\n")
            file_name.write("\n".join(instructions))


if __name__ == "__main__":
    main()
