import itertools
import logging
import os
import shutil
import subprocess
import unittest
from typing import override

from ..src import disassembler as disasm

logging.basicConfig(level=logging.DEBUG)
test_logger = logging.getLogger("tests")

TEMP_NASM_INPUT_FILE_LOCATION = "tmp/inst.asm"
TEMP_NASM_OUTPUT_FILE_LOCATION = "tmp/bin.asm"


def get_bin_from_nasm(asm_instructions: str):
    with open(TEMP_NASM_INPUT_FILE_LOCATION, "w") as file:
        file.write(asm_instructions)
    subprocess.run(
        ["nasm", TEMP_NASM_INPUT_FILE_LOCATION, "-o", TEMP_NASM_OUTPUT_FILE_LOCATION],
        capture_output=True,
    )
    with open(TEMP_NASM_OUTPUT_FILE_LOCATION, "rb") as file:
        binary: bytes = file.read()
    return binary


def get_bin_seen_error_str(bin: bytes) -> str:
    as_byte_strings = [f"{by:08b}" for by in bin]
    return "disassembler saw:\n" + " ".join(as_byte_strings)


class TestDisassembler(unittest.TestCase):
    @override
    def tearDown(self) -> None:
        nasm_temp_file_dir = TEMP_NASM_INPUT_FILE_LOCATION.split("/")[0]
        if os.path.exists(nasm_temp_file_dir):
            shutil.rmtree(nasm_temp_file_dir)

        return super().tearDown()

    @override
    def setUp(self) -> None:
        nasm_temp_file_dir = TEMP_NASM_INPUT_FILE_LOCATION.split("/")[0]
        if not os.path.exists(nasm_temp_file_dir):
            os.makedirs(nasm_temp_file_dir)

        self.parsable_instructions = disasm.get_parsable_instructions_from_config()

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
        test_logger.debug(get_bin_seen_error_str(original_bin))
        try:
            disassembled = disasm.disassemble_binary_to_string(
                self.parsable_instructions, original_bin
            )
            logging.debug(f"disassembler output: \n{disassembled}")
        except Exception as e:
            test_logger.debug(get_bin_seen_error_str(original_bin))
            raise e

        try:
            bin_of_our_disassembly = get_bin_from_nasm(disassembled)
        except Exception as e:
            test_logger.debug(get_bin_seen_error_str(original_bin))
            test_logger.debug(f"our disassembly:\n{disassembled}")
            raise e

        self.assertEqual(
            original_bin, bin_of_our_disassembly, get_bin_seen_error_str(original_bin)
        )


# class TestMov(TestDisassembler):
#     def test_reg_to_reg(self):
#         self.help_test_given_asm("mov cx, bx")

#     def test_many_reg_to_reg(self):
#         self.help_test_given_asm(
#             [
#                 "mov cx, bx",
#                 "mov ch, ah",
#                 "mov dx, bx",
#                 "mov bx, di",
#                 "mov al, cl",
#                 "mov ch, ch",
#                 "mov bx, ax",
#                 "mov bx, si",
#                 "mov sp, di",
#                 "mov bp, ax",
#                 "mov si, bx",
#                 "mov dh, al",
#             ]
#         )

#     def test_8bit_immediate_to_register(self):
#         self.help_test_given_asm("mov bh, 12")

#     def test_many_8bit_immediate_to_register(self):
#         self.help_test_given_asm(["mov cl, 12", "mov ch, -12"])

#     def test_16bit_immediate_to_register(self):
#         self.help_test_given_asm("mov ax, 100")

#     def test_many_16bit_immediate_to_register(self):
#         self.help_test_given_asm(
#             ["mov cx, 12", "mov cx, -12", "mov dx, 3948", "mov dx, -3948"]
#         )

#     def test_source_address_calculation_single_var(self):
#         self.help_test_given_asm("mov bh, [bp]")

#     def test_source_address_calculation_double_var(self):
#         self.help_test_given_asm("mov bh, [bp]")

#     def test_many_source_address_calculation(self):
#         self.help_test_given_asm(
#             [
#                 "mov al, [bx + si]",
#                 "mov bx, [bp + di]",
#                 "mov dx, [bp]",
#             ]
#         )

#     def test_source_address_with_8bit_displacement(self):
#         self.help_test_given_asm("mov ah, [bx + si + 4]")

#     def test_source_address_with_16bit_displacement(self):
#         self.help_test_given_asm("mov al, [bx + si + 4999]")

#     def test_dest_address_calculation(self):
#         self.help_test_given_asm(
#             ["mov [bx + di], cx", "mov [bp + si], cl", "mov [bp], ch"]
#         )

#     def test_signed_displacement(self):
#         self.help_test_given_asm("mov ax, [bx + di - 37]")

#     def test_signed_displacements(self):
#         self.help_test_given_asm(
#             ["mov ax, [bx + di - 37]", "mov [si - 300], cx", "mov dx, [bx - 32]"]
#         )

#     def test_explicit_size(self):
#         self.help_test_given_asm("mov [di + 901], word 347")

#     def test_explicit_sizes(self):
#         self.help_test_given_asm(["mov [bp + di], byte 7", "mov [di + 901], word 347"])

#     def test_direct_address(self):
#         self.help_test_given_asm("mov bp, [5]")

#     def test_direct_addresses(self):
#         self.help_test_given_asm(["mov bp, [5]", "mov bx, [3458]"])

#     def test_memory_to_accumulator(self):
#         self.help_test_given_asm("mov ax, [2555]")

#     def test_memory_to_accumulators(self):
#         self.help_test_given_asm(["mov ax, [2555]", "mov ax, [16]"])

#     def test_accumulator_to_memory(self):
#         self.help_test_given_asm("mov [2554], ax")

#     def test_accumulator_to_memories(self):
#         self.help_test_given_asm(["mov [2554], ax", "mov [15], ax"])


class TestSub(TestDisassembler):
    def test_sub_reg_from_memory(self):
        self.help_test_given_asm("sub bx, [bp]")

    def test_subs_reg_from_memory(self):
        self.help_test_given_asm(["sub bx, [bx+si]", "sub bx, [bp]"])

    # def test_sub_immediate_from_reg(self):
    #     self.help_test_given_asm(["sub si, 2", "sub bp, 2", "sub cx, 8"])

    # def test_sub_reg_from_memory_with_displacement(self):
    #     self.help_test_given_asm(
    #         [
    #             "sub bx, [bp + 0]",
    #             "sub cx, [bx + 2]",
    #             "sub bh, [bp + si + 4]",
    #             "sub di, [bp + di + 6]",
    #         ]
    #     )

    # def test_sub_reg_from_memory_dest(self):
    #     self.help_test_given_asm(
    #         [
    #             "sub [bx+si], bx",
    #             "sub [bp], bx",
    #             "sub [bp + 0], bx",
    #             "sub [bx + 2], cx",
    #             "sub [bp + si + 4], bh",
    #             "sub [bp + di + 6], di",
    #         ]
    #     )

    # def test_sub_immediate_from_memory(self):
    #     self.help_test_given_asm(["sub byte [bx], 34", "sub word [bx + di], 29"])

    # def test_sub_mixed_operations(self):
    #     self.help_test_given_asm(
    #         ["sub ax, [bp]", "sub al, [bx + si]", "sub ax, bx", "sub al, ah"]
    #     )

    # def test_sub_immediate_values(self):
    #     self.help_test_given_asm(["sub ax, 1000", "sub al, -30", "sub al, 9"])


# class TestAdd(TestDisassembler):
#     def test_add_reg_from_memory(self):
#         self.help_test_given_asm(["add bx, [bx+si]", "add bx, [bp]"])

#     def test_add_immediate_to_reg(self):
#         self.help_test_given_asm(["add si, 2", "add bp, 2", "add cx, 8"])

#     def test_add_reg_from_memory_with_displacement(self):
#         self.help_test_given_asm(
#             [
#                 "add bx, [bp + 0]",
#                 "add cx, [bx + 2]",
#                 "add bh, [bp + si + 4]",
#                 "add di, [bp + di + 6]",
#             ]
#         )

#     def test_add_reg_to_memory(self):
#         self.help_test_given_asm(
#             [
#                 "add [bx+si], bx",
#                 "add [bp], bx",
#                 "add [bp + 0], bx",
#                 "add [bx + 2], cx",
#                 "add [bp + si + 4], bh",
#                 "add [bp + di + 6], di",
#             ]
#         )

#     def test_add_immediate_to_memory(self):
#         self.help_test_given_asm(["add byte [bx], 34", "add word [bp + si + 1000], 29"])

#     def test_add_mixed_operations(self):
#         self.help_test_given_asm(
#             ["add ax, [bp]", "add al, [bx + si]", "add ax, bx", "add al, ah"]
#         )

#     def test_add_immediate_values(self):
#         self.help_test_given_asm(["add ax, 1000", "add al, -30", "add al, 9"])


# class TestCmp(TestDisassembler):
#     def test_cmp_reg_with_memory(self):
#         self.help_test_given_asm(["cmp bx, [bx+si]", "cmp bx, [bp]"])

#     def test_cmp_reg_with_immediate(self):
#         self.help_test_given_asm(["cmp si, 2", "cmp bp, 2", "cmp cx, 8"])

#     def test_cmp_reg_with_memory_displacement(self):
#         self.help_test_given_asm(
#             [
#                 "cmp bx, [bp + 0]",
#                 "cmp cx, [bx + 2]",
#                 "cmp bh, [bp + si + 4]",
#                 "cmp di, [bp + di + 6]",
#             ]
#         )

#     def test_cmp_memory_with_reg(self):
#         self.help_test_given_asm(
#             [
#                 "cmp [bx+si], bx",
#                 "cmp [bp], bx",
#                 "cmp [bp + 0], bx",
#                 "cmp [bx + 2], cx",
#                 "cmp [bp + si + 4], bh",
#                 "cmp [bp + di + 6], di",
#             ]
#         )

#     def test_cmp_memory_with_immediate(self):
#         self.help_test_given_asm(["cmp byte [bx], 34", "cmp word [4834], 29"])

#     def test_cmp_mixed_operations(self):
#         self.help_test_given_asm(
#             ["cmp ax, [bp]", "cmp al, [bx + si]", "cmp ax, bx", "cmp al, ah"]
#         )

#     def test_cmp_immediate_values(self):
#         self.help_test_given_asm(["cmp ax, 1000", "cmp al, -30", "cmp al, 9"])


# class TestJumps(TestDisassembler):
#     def test_jnz_instructions(self):
#         self.help_test_given_asm(
#             [
#                 "test_label0:",
#                 "jnz test_label1",
#                 "jnz test_label0",
#                 "test_label1:",
#                 "jnz test_label0",
#                 "jnz test_label1",
#             ]
#         )

#     def test_conditional_jumps(self):
#         self.help_test_given_asm(
#             [
#                 "label:",
#                 "je label",
#                 "jl label",
#                 "jle label",
#                 "jb label",
#                 "jbe label",
#                 "jp label",
#                 "jo label",
#                 "js label",
#             ]
#         )

#     def test_negative_conditional_jumps(self):
#         self.help_test_given_asm(
#             [
#                 "label:",
#                 "jne label",
#                 "jnl label",
#                 "jg label",
#                 "jnb label",
#                 "ja label",
#                 "jnp label",
#                 "jno label",
#                 "jns label",
#             ]
#         )

#     def test_loop_instructions(self):
#         self.help_test_given_asm(
#             ["label:", "loop label", "loopz label", "loopnz label", "jcxz label"]
#         )
