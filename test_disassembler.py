import itertools
import os
import subprocess
from typing import override
import unittest
import disassembler as disasm

TEMP_NASM_INPUT_FILE_LOCATION = "tmp/inst.asm"
TEMP_NASM_OUTPUT_FILE_LOCATION = "tmp/bin.asm"

if not os.path.exists(
    nasm_temp_file_dir := TEMP_NASM_INPUT_FILE_LOCATION.split("/")[0]
):
    os.makedirs(nasm_temp_file_dir)


def get_bin_from_nasm(asm_instructions: str):
    with open(TEMP_NASM_INPUT_FILE_LOCATION, "w") as file:
        file.write(asm_instructions)
    subprocess.run(
        ["nasm", TEMP_NASM_INPUT_FILE_LOCATION, "-o", TEMP_NASM_OUTPUT_FILE_LOCATION]
    )
    with open(TEMP_NASM_OUTPUT_FILE_LOCATION, "rb") as file:
        binary: bytes = file.read()
    return binary


def get_bin_seen_error_str(bin: bytes) -> str:
    as_byte_strings = [f"{by:08b}" for by in bin]
    return "disassembler saw:\n" + " ".join(as_byte_strings)


class TestDisassembler(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.parsable_instructions = disasm.get_parsable_instructions_from_file()
        return super().setUp()

    def help_test_given_asm(self, asm_instructions: list[str] | str):
        """
        Compare binary created by nasm on given asm code and the
        binary created on new disassembly because negative numbers
        and positive numbers only differ by interpretation but can't really
        be distinguished from binary.
        """
        if isinstance(asm_instructions, str):
            asm_instructions = [asm_instructions]
        original_bin = get_bin_from_nasm(
            "\n".join(itertools.chain(["bits 16"], asm_instructions))
        )
        print(get_bin_seen_error_str(original_bin))
        try:
            disassembled = disasm.disassemble_binary_to_string(
                self.parsable_instructions, original_bin
            )
        except Exception as e:
            print(get_bin_seen_error_str(original_bin))
            raise e

        try:
            bin_of_our_disassembly = get_bin_from_nasm(disassembled)
        except Exception as e:
            print(get_bin_seen_error_str(original_bin))
            print(f"our disassembly:\n{disassembled}")
            raise e

        self.assertEqual(
            original_bin, bin_of_our_disassembly, get_bin_seen_error_str(original_bin)
        )


class TestMov(TestDisassembler):
    def test_reg_to_reg(self):
        self.help_test_given_asm("mov cx, bx")

    def test_many_reg_to_reg(self):
        self.help_test_given_asm(
            [
                "mov cx, bx",
                "mov ch, ah",
                "mov dx, bx",
                "mov bx, di",
                "mov al, cl",
                "mov ch, ch",
                "mov bx, ax",
                "mov bx, si",
                "mov sp, di",
                "mov bp, ax",
                "mov si, bx",
                "mov dh, al",
            ]
        )

    def test_8bit_immediate_to_register(self):
        self.help_test_given_asm("mov bh, 12")

    def test_many_8bit_immediate_to_register(self):
        self.help_test_given_asm(["mov cl, 12", "mov ch, -12"])

    def test_16bit_immediate_to_register(self):
        self.help_test_given_asm("mov ax, 100")

    def test_many_16bit_immediate_to_register(self):
        self.help_test_given_asm(
            ["mov cx, 12", "mov cx, -12", "mov dx, 3948", "mov dx, -3948"]
        )

    def test_source_address_calculation_single_var(self):
        self.help_test_given_asm("mov bh, [bp]")

    def test_source_address_calculation_double_var(self):
        self.help_test_given_asm("mov bh, [bp]")

    def test_many_source_address_calculation(self):
        self.help_test_given_asm(
            [
                "mov al, [bx + si]",
                "mov bx, [bp + di]",
                "mov dx, [bp]",
            ]
        )

    def test_source_address_with_8bit_displacement(self):
        self.help_test_given_asm("mov ah, [bx + si + 4]")

    def test_source_address_with_16bit_displacement(self):
        self.help_test_given_asm("mov al, [bx + si + 4999]")

    def test_dest_address_calculation(self):
        self.help_test_given_asm(
            ["mov [bx + di], cx", "mov [bp + si], cl", "mov [bp], ch"]
        )
