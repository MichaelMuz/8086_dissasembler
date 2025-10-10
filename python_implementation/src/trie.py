from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import Self

from python_implementation.src.base.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import get_sub_most_sig_bits


class BitModeSchemaIterator:
    def __init__(self, instruction: InstructionSchema) -> None:
        self.instruction = instruction
        self.whole_ind = 0
        self.bit_ind = 0

    @cached_property
    def _fields(self):
        return [self.instruction.identifier_literal] + self.instruction.fields

    @property
    def _curr_inst(self):
        return self._fields[self.whole_ind]

    def __iter__(self):
        return self

    def is_next_named(self):
        return self.has_more() and isinstance(self._curr_inst, NamedField)

    def has_more(self):
        return self.whole_ind < len(self._fields)

    def __next__(self) -> bool | NamedField:
        next_ret = None
        if self.whole_ind == len(self._fields):
            raise StopIteration
        elif isinstance(self._curr_inst, NamedField):
            next_ret = self._curr_inst
            self.whole_ind += 1
        else:
            next_ret = bool(
                get_sub_most_sig_bits(
                    self._curr_inst.literal_value,
                    self.bit_ind,
                    1,
                    total_bits=self._curr_inst.bit_width,
                )
            )
            self.bit_ind += 1
            if self.bit_ind == self._curr_inst.bit_width:
                self.bit_ind = 0
                self.whole_ind += 1
        return next_ret

    def to_whole_field_iter(self) -> Iterator[SchemaField]:
        match self._curr_inst:
            case LiteralField(bit_width=bw):
                assert self.bit_ind == bw, "Cannot Transition on unfinished literal"
            case NamedField():
                assert self.bit_ind == 0, "Inconsistent bit index state"

        return (self._fields[i] for i in range(self.whole_ind, len(self._fields)))


@dataclass
class BitNode:
    left: "BitNode | LeafNode | None" = None
    right: "BitNode | LeafNode | None" = None
    next: "FieldNode | LeafNode | None" = None


@dataclass
class FieldNode:
    named_field: NamedField
    left: "BitNode | LeafNode | None" = None
    right: "BitNode | LeafNode | None" = None
    next: "FieldNode | LeafNode | None" = None


@dataclass
class LeafNode:
    token_iter: BitModeSchemaIterator


type Node = BitNode | FieldNode | LeafNode

def create_node(curr: NamedField | bool):
    if isinstance(curr, NamedField):
        return FieldNode(curr)
    else:
        return BitNode()

def attach_correctly(head: Node, curr: Node):
    assert not isinstance(head, LeafNode), "Cannot attach to leaf node"
    match curr:
        case BitNode(True):
            head.right = BitNode()
        case False:
            head.left = BitNode()
        case NamedField() as x:
            head.next = FieldNode(x)


def insert_into_trie(
    head: Node | None,
    token_iter: BitModeSchemaIterator,
) -> Node:
    """
    Need to:
    1. if head is a bitnode we make sure the next token is a bool and go left/right
    2. if head is a field node we need to make sure the next token is a named field and go next
    3. if head is None we need to make a subtree from here, we will curl into a leaf node
    4. if head is a leaf node we need to unroll it one token, make the correct node, then attach
       the rest of it, coiled, to the right next/left/right pointer
    """
    if head is None:
        if not token_iter.has_more():
            return LeafNode(token_iter)
        if token_iter.is_next_named():
            # If we are not being compared and on the boundary of a named field, we can coil up here
            return LeafNode(token_iter)
        else:
            head = BitNode()

    elif isinstance(head, LeafNode):
        next_leaf_token = next(head.token_iter, None)
        assert next_leaf_token is not None, "Duplicate instruction detected"
        next_leaf_node = (
            FieldNode(next_leaf_token)
            if isinstance(next_leaf_token, NamedField)
            else BitNode()
        )
        attach_correctly(next_leaf_node, insert_into_trie(None, head.token_iter))
        next_leaf_node.next =
        head = next_leaf_node

    current_token = next(token_iter, None)

    if isinstance(current_token, bool):
        head = head or BitNode()
        # notice current token is just used to decide the direction we take
        if current_token:
            head.right = insert_into_trie(head.right, token_iter)
        else:
            head.left = insert_into_trie(head.left, token_iter)

    elif isinstance(current_token, NamedField):
        if isinstance(head, FieldNode) and head.named_field != current_token:
            raise ValueError("Two FieldNodes at same place means ISA is ambiguous")
        # notice we don't insert named fields into each other, we just assert they are the same
        head = head or FieldNode(current_token)
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
                BitModeSchemaIterator(instruction),
            )
        assert isinstance(head, BitNode), f"Expected BitNode, got `{type(head)}`"
        return cls(head)
