#!/usr/bin/env python3

import os
import itertools


def parse_file_and_get_dissasembled_instructions(inp_file_name):
    print(f"input binary file name: {inp_file_name}")
    instructions = []
    with open(inp_file_name, "rb") as file:
        binary = file.read()
        for byte1, byte2 in itertools.batched(binary, 2, strict=True):
            # bit 7 indicated direction of the move, 0 means source is reg field, 1 means destination in reg field
            direction_set = bool(byte1 & 0b00000010)

            # bit 8 tells us if we use the 16 bit register or just lower 8 bits
            word_16_bit_set = bool(byte1 & 0b00000001)
            if (byte1 & 0b10001000) == 0b10001000:
                # in byte 2 first 2 bits are mode bits tell us what kind of move
                # 11 tells us register to register
                mode_bits = byte2 & 0b11000000
                assert (
                    mode_bits == 0b11000000
                ), "Only deal with mov register to register, memory mov not expected"
                # indexed by register number code, then indexed by if we are using the full word
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
                reg_field_operand = reg_name_lower_and_word[reg_field_val][
                    word_16_bit_set
                ]

                # if mode is 11 it is register to register and we have a second register as the second operand
                r_m_field_val = byte2 & 0b00000111
                r_m_field_operand = reg_name_lower_and_word[r_m_field_val][
                    word_16_bit_set
                ]

                source_dest = [reg_field_operand, r_m_field_operand]
                if direction_set:
                    source_dest = list(reversed(source_dest))
                source, dest = source_dest

                instructions.append(f"MOV {dest}, {source}")
            else:

                raise ValueError(
                    f"Didn't expect to get here, given input was: {" ".join([f"{b:08b}" for b in binary])}"
                )
    print(f"{instructions = }")
    return instructions


def main():
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    files_to_do = os.listdir(input_directory)
    # files_to_do = ["single_register_mov"]
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
