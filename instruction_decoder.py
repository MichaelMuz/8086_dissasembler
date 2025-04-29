#!/usr/bin/env python3


def main():
    inp_file = "asm/single_register_mov.asm"
    with open(inp_file, "rb") as file:
        binary = file.read()
        byte1 = binary[0]
        byte2 = binary[1]

        # bit 7 indicated direction of the move, 0 means source is reg field, 1 means destination in reg field
        direction_set = bool(byte1 & 0b00000010)

        # bit 8 tells us if we use the 16 bit register or just lower 8 bits
        word_16_bit_set = bool(byte1 & 0b00000001)
        if byte1 == 0b11111100:
            # in byte 2 first 2 bits are mode bits tell us what kind of move
            # 11 tells us register to register
            mode_bits = byte2 & 0b11000000
            assert (
                mode_bits == 0b11000000
            ), "Only deal with mov register to register, memory mov not expected"
            # indexed by register number code, then indexed by if we are using the full word
            reg_name_lower_and_word = [
                # [lower_register_name, word_full_register_name]
                ["AL", "AX"],
                ["CL", "CX"],
                ["DL", "DX"],
                ["BL", "BX"],
                ["AH", "SP"],
                ["CH", "BP"],
                ["DH", "SI"],
                ["BH", "DI"],
            ]
            # first register is these bits
            reg_field_val = (byte2 & 0b00111000) >> 2
            reg_field_operand = reg_name_lower_and_word[reg_field_val][word_16_bit_set]

            # if mode is 11 it is register to register and we have a second register as the second operand
            r_m_field_val = byte2 & 0b00000111
            r_m_field_operand = reg_name_lower_and_word[r_m_field_val][word_16_bit_set]

            source_dest = [reg_field_operand, r_m_field_operand]
            if direction_set:
                source_dest = list(reversed(source_dest))
            source, dest = source_dest

            print(f"MOV {dest}, {source}")


if __name__ == "__main__":
    main()
