from typing import Iterator, Self, TypeAlias
from dataclasses import dataclass
from python_implementation.src import utils
from python_implementation.src.builder import DecodeAccumulator
from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)

from python_implementation.src.decoder import BitIterator


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
