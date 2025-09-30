import logging
from python_implementation.src.templates import (
    DisassembledInstruction,
    DisassembledInstructionBuilder,
)
from python_implementation.src.templates.instruction_schema import InstructionSchema
from python_implementation.src.utils import BITS_PER_BYTE, get_sub_most_sig_bits


class BitIterator:
    def __init__(self, b: bytes):
        self.inst_bytes = b
        self.iterator = iter(b)
        self.curr_byte = None
        self.byte_ind = -1
        self.msb_bit_ind = BITS_PER_BYTE

    def _grab_byte(self):
        self.curr_byte = next(self.iterator, None)
        self.byte_ind += 1
        self.msb_bit_ind = 0

        logging.debug(f"grabbing byte, it was: {self.curr_byte}")
        return self.curr_byte is None

    def next_bits(self, num_bits: int):
        logging.debug(f"request for: {num_bits = }")
        if num_bits > BITS_PER_BYTE:
            raise ValueError("Our ISA does not have fields larger than a byte")
        assert num_bits > 0

        if self.msb_bit_ind == BITS_PER_BYTE:
            ended = self._grab_byte()
            assert not ended, "Instruction stream ended in the middle of an instruction"

        assert self.curr_byte is not None, "invariant"

        bits_left = BITS_PER_BYTE - self.msb_bit_ind
        if num_bits > bits_left:
            logging.info(f"{self.msb_bit_ind = }, {bits_left = }")
            raise ValueError(
                "Our ISA does not have fields that straddle byte boundaries"
            )

        field_value = get_sub_most_sig_bits(self.curr_byte, self.msb_bit_ind, num_bits)

        self.msb_bit_ind += num_bits
        return field_value

    def peek_whole_byte(self):
        if self.msb_bit_ind == BITS_PER_BYTE:
            self._grab_byte()
        elif self.msb_bit_ind != 0:
            raise ValueError("Tried to peek incomplete byte")
        return self.curr_byte


def disassemble_instruction(
    instruction_schema: InstructionSchema, bit_iter: BitIterator
) -> DisassembledInstruction:

    disassembled_instruction_builder = DisassembledInstructionBuilder(
        instruction_schema,
        bit_iter.next_bits(instruction_schema.identifier_literal.bit_width),
    )

    for schema_field in instruction_schema.fields:
        if not disassembled_instruction_builder.is_needed(schema_field):
            logging.debug(f"{schema_field = } not needed")
            continue

        logging.debug(f"{schema_field = } needed")
        logging.debug(f"curr byte: {bit_iter.curr_byte:08b} {bit_iter.msb_bit_ind = }")
        field_value = bit_iter.next_bits(schema_field.bit_width)
        logging.debug(f"has value {field_value = }")
        logging.debug(f"curr byte: {bit_iter.curr_byte:08b} {bit_iter.msb_bit_ind = }")
        disassembled_instruction_builder.with_field(schema_field, field_value)

    return disassembled_instruction_builder.build()


def disassemble(
    possible_instructions: list[InstructionSchema], bit_iter: BitIterator
) -> list[DisassembledInstruction]:

    disassembled_instructions = []
    while (current_byte := bit_iter.peek_whole_byte()) is not None:
        logging.debug("starting new instruction")

        matching_schema = None
        for possible_instruction in possible_instructions:
            if possible_instruction.identifier_literal.is_match(current_byte):
                matching_schema = possible_instruction
                logging.debug(
                    f"found matching schema: {matching_schema.identifier_literal.literal_value}"
                )
                break
        assert matching_schema is not None

        disassembled_instruction = disassemble_instruction(matching_schema, bit_iter)
        logging.debug(f"{disassembled_instruction= }:\n{disassembled_instruction = }")
        disassembled_instructions.append(disassembled_instruction)

    return disassembled_instructions


def disassemble_binary_to_string(
    possible_instructions: list[InstructionSchema], b: bytes
) -> str:
    logging.debug("disassembler seeing:\n" + " ".join([f"{by:08b}" for by in b]))
    bit_iter = BitIterator(b)
    disassembled = disassemble(possible_instructions, bit_iter)

    disassembly_as_str = "\n".join(["bits 16", *map(str, disassembled)])
    return disassembly_as_str
