import logging

from python_implementation.src.base.schema import InstructionSchema, NamedField
from python_implementation.src.disassembled import Disassembly
from python_implementation.src.intermediates.accumulator import DecodeAccumulator
from python_implementation.src.trie import Trie
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
        return self.curr_byte is None

    def next_bits(self, num_bits: int):
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
    head = trie.dummy_head
    acc = DecodeAccumulator()
    while head is not None and head.coil is None:
        if isinstance(head.value, bool):
            print("asking for 1 more")
            b = bool(bit_iter.next_bits(1))
            acc.with_bit(b)
            if b:
                head = head.children[2]
            else:
                head = head.children[0]
        elif isinstance(head.value, NamedField):
            print(f"asking for {head.value.bit_width} more")
            acc.with_field(head.value, bit_iter.next_bits(head.value.bit_width))
            head = head.children[1]
        else:
            raise ValueError(f"Unexpected {head.value}")

    assert head is not None
    rest_of_coil = head.get_rest_of_coil()

    while rest_of_coil.has_more() and not rest_of_coil.can_transition():
        coil_bit = next(rest_of_coil)
        assert isinstance(
            coil_bit, bool
        ), "We know instruction but failing to match literal bits"
        read_bit = bool(bit_iter.next_bits(1))
        assert read_bit == coil_bit
        acc.with_bit(read_bit)
        print(f"in the wrap up, asking for one more, {read_bit = }")

    print(
        f"done with trie now using the iter, {bit_iter.curr_byte = }, {bit_iter.msb_bit_ind = }"
    )

    print(f"done with trie now using the iter, {rest_of_coil.instruction = }")

    acc.with_implied_fields(rest_of_coil.instruction.implied_values)
    whole_iter = rest_of_coil.to_whole_field_iter()
    for e in whole_iter:
        print(f"checking if {e} needed")
        if acc.is_needed(e):
            val = bit_iter.next_bits(e.bit_width)
            acc.with_field(e, val)
        print(f"after {e = }, {bit_iter.curr_byte = }, {bit_iter.msb_bit_ind = }")

    print(f"\n building {rest_of_coil.instruction} \n")
    return acc.build(rest_of_coil.instruction)


def parse_binary(
    parsable_instructions: list[InstructionSchema], file_contents: bytes
) -> Disassembly:
    trie = Trie.from_parsable_instructions(parsable_instructions)
    bit_iter = BitIterator(file_contents)
    disassembled_instructions = []
    while bit_iter.peek_whole_byte() is not None:

        disassembled_instruction = parse(trie, bit_iter)
        disassembled_instructions.append(disassembled_instruction)

    return Disassembly(disassembled_instructions)
