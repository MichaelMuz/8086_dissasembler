from typing import Self, TypeAlias
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


class LiteralFieldIterator:
    def __init__(self, literal_field: LiteralField):
        self.literal_field = literal_field
        self.bit_index = 0

    def has_more(self) -> bool:
        return self.bit_index < self.literal_field.bit_width

    def __next__(self) -> bool:
        if not self.has_more():
            raise StopIteration
        ret = bool(
            utils.get_sub_most_sig_bits(
                self.literal_field.literal_value, self.bit_index, 1
            )
        )
        self.bit_index += 1
        return ret


class FieldModeInstructionSchemaIterator:
    def __init__(self, instruction: InstructionSchema, starting_ind: int = 0) -> None:
        self.instruction = instruction
        self.field_ind = starting_ind

    def __next__(self) -> SchemaField:
        if not self.has_more():
            raise StopIteration
        return self.instruction.fields[self.field_ind]

    def has_more(self) -> bool:
        return self.field_ind < len(self.instruction.fields)


class BitModeInstructionSchemaIterator:
    def __init__(self, whole_iter: FieldModeInstructionSchemaIterator) -> None:
        self.whole_iter = whole_iter
        self.sub_iter = None

    def __iter__(self):
        return self

    def __next__(self) -> bool | NamedField:
        if not self.has_more():
            raise StopIteration
        if self.sub_iter is None or not self._sub_has_more():
            next_whole = next(self.whole_iter)
            if isinstance(next_whole, NamedField):
                return next_whole
            self.sub_iter = LiteralFieldIterator(next_whole)

        return next(self.sub_iter)

    def _sub_has_more(self) -> bool:
        return self.sub_iter is not None and self.sub_iter.has_more()

    def has_more(self) -> bool:
        return self.whole_iter.has_more() or self._sub_has_more()

    def to_whole_field_mode(self) -> FieldModeInstructionSchemaIterator:
        assert not self._sub_has_more(), "Cannot transition mid literal"
        return self.whole_iter


@dataclass
class BitNode:
    left: "Node | None" = None
    right: "Node | None" = None


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None" = None


@dataclass
class LeafNode:
    token_iter: BitModeInstructionSchemaIterator


Node: TypeAlias = BitNode | FieldNode | LeafNode


def insert_into_trie(
    head: Node | None,
    token_iter: BitModeInstructionSchemaIterator,
) -> Node:
    current_token = next(token_iter, None)

    if current_token is None:
        # both done, we are a leaf at the very bottom of a finished instruction
        assert head is None, "Instruction ends while another continues, ambiguous"
        head = LeafNode(token_iter)
        return head

    elif isinstance(head, LeafNode):
        # head will be None and the correct thing will be created for head, then we will insert the current token
        head = insert_into_trie(None, head.token_iter)

    if head is None:
        # head is None so we are the root, make the correct node
        if isinstance(current_token, bool):
            head = BitNode()
        else:
            head = FieldNode(current_token)

    if isinstance(head, BitNode):
        assert isinstance(
            current_token, bool
        ), f"Expected bit but got {type(current_token)}"
        if current_token:
            head.right = insert_into_trie(head.right, token_iter)
        else:
            head.left = insert_into_trie(head.left, token_iter)

    elif isinstance(head, FieldNode):
        assert isinstance(
            current_token, NamedField
        ), f"Expected NamedField but got {type(current_token)}"
        assert (
            head.named_field == current_token
        ), f"Incompatible named fields: {head.named_field} vs {current_token}"
        head.next = insert_into_trie(head.next, token_iter)

    return head


# Need to have final instruction type as soon as possible in the tree bc need to have implied values
class Trie:
    def __init__(self, head: BitNode) -> None:
        self.head = head

    @classmethod
    def from_parsable_instructions(cls, instructions: list[InstructionSchema]) -> Self:
        head = None
        for instruction in instructions:
            head = insert_into_trie(
                head,
                BitModeInstructionSchemaIterator(
                    FieldModeInstructionSchemaIterator(instruction)
                ),
            )
        assert isinstance(head, BitNode), f"Expected BitNode, got `{type(head)}`"
        return cls(head)


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
    whole_iter = head.token_iter.to_whole_field_mode()
    while (e := next(whole_iter, None)) is not None:
        val = bit_iter.next_bits(e.bit_width)
        if isinstance(e, LiteralField):
            assert val == e.literal_value
        else:
            acc.with_field(e, val)

    return acc.build(whole_iter.instruction)
