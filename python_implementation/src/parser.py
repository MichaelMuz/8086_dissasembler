import logging

from python_implementation.src.base.schema import LiteralField
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
            if bit_iter.next_bits(1):
                head = head.right
            else:
                head = head.left
        elif isinstance(head, FieldNode):
            acc.with_field(
                head.named_field, bit_iter.next_bits(head.named_field.bit_width)
            )
            head = head.next

    assert head is not None, "Invalid Instruction"
    whole_iter = head.token_iter.to_whole_field_iter()
    while (e := next(whole_iter, None)) is not None:
        val = bit_iter.next_bits(e.bit_width)
        if isinstance(e, LiteralField):
            assert val == e.literal_value
        else:
            acc.with_field(e, val)

    return acc.build(head.token_iter.instruction)
