import logging
from venv import logger

from python_implementation.src.base.schema import InstructionSchema
from python_implementation.src.disassembled import Disassembly
from python_implementation.src.intermediates.accumulator import DecodeAccumulator
from python_implementation.src.trie import BitNode, FieldNode, LeafNode, Trie
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


def parse(trie: Trie, bit_iter: BitIterator):
    head = trie.head
    acc = DecodeAccumulator()
    while head is not None and not isinstance(head, LeafNode):
        if isinstance(head, BitNode):
            logger.debug("requesting 1 bit")
            b = bool(bit_iter.next_bits(1))
            acc.with_bit(b)
            if b:
                head = head.right
            else:
                head = head.left
        elif isinstance(head, FieldNode):
            logger.debug(f"requesting {head.named_field.bit_width} bits")
            acc.with_field(
                head.named_field, bit_iter.next_bits(head.named_field.bit_width)
            )
            head = head.next

    logger.debug("Got to leaf node")
    assert head is not None, "Invalid Instruction"
    acc.with_implied_fields(head.token_iter.instruction.implied_values)
    whole_iter = head.token_iter.to_whole_field_iter()
    for e in whole_iter:
        if acc.is_needed(e):
            logger.debug(f"need {e}")
            val = bit_iter.next_bits(e.bit_width)
            acc.with_field(e, val)

    return acc.build(head.token_iter.instruction)


def parse_binary(
    parsable_instructions: list[InstructionSchema], file_contents: bytes
) -> Disassembly:
    trie = Trie.from_parsable_instructions(parsable_instructions)
    bit_iter = BitIterator(file_contents)
    disassembled_instructions = []
    while bit_iter.peek_whole_byte() is not None:
        logging.debug("starting new instruction")

        disassembled_instruction = parse(trie, bit_iter)
        disassembled_instructions.append(disassembled_instruction)

    return Disassembly(disassembled_instructions)
