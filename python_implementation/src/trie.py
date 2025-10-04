from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import Self
from venv import logger

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
            logger.debug(
                f"{self._curr_inst.literal_value = }, {self.bit_ind = }, {next_ret = }"
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
    left: "Node | None" = None
    right: "Node | None" = None


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None" = None


@dataclass
class LeafNode:
    token_iter: BitModeSchemaIterator


type Node = BitNode | FieldNode | LeafNode


def make_correct_node(val: NamedField | bool):
    if isinstance(val, bool):
        head = BitNode()
    else:
        head = FieldNode(val)
    return head


def insert_into_internal_node(head: BitNode | FieldNode, val: NamedField | bool):
    if isinstance(head, BitNode):
        assert isinstance(val, bool), f"Expected bit but got {type(val)}"
        if val:
            head.right = BitNode()
        else:
            head.left = BitNode()

    elif isinstance(head, FieldNode):
        assert isinstance(val, NamedField), f"Expected NamedField but got {type(val)}"
        assert (
            head.named_field == val
        ), f"Incompatible named fields: {head.named_field} vs {val}"
        logger.debug(f"Inserting {head = }")
        head.next = insert_into_trie(head.next, token_iter)


def create_node_from_token(token, remaining_iter):
    """Create appropriate node type from token and attach remaining iterator"""
    if isinstance(token, bool):
        node = BitNode()
        if token:
            node.right = insert_into_trie(None, remaining_iter)
        else:
            node.left = insert_into_trie(None, remaining_iter)
        return node
    else:
        node = FieldNode(token)
        node.next = insert_into_trie(None, remaining_iter)
        return node


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
            logger.debug(
                "Completely finished instruction, leaf node with empty iterator"
            )
            return LeafNode(token_iter)
        if token_iter.is_next_named():
            # If we are not being compared and on the boundary of a named field, we can coil up here
            logger.debug("curling here")
            return LeafNode(token_iter)
        else:
            logger.debug("this token must be a bit")
            head = BitNode()

    elif isinstance(head, LeafNode):
        logger.debug("Unrolling leaf node")
        next_leaf_token = next(head.token_iter, None)
        assert next_leaf_token is not None, "Duplicate instruction detected"
        assert isinstance(
            next_leaf_token, NamedField
        ), "First field in coiled leaf should be named"
        next_leaf_node = FieldNode(next_leaf_token)
        next_leaf_node.next = insert_into_trie(None, head.token_iter)
        head = next_leaf_node

    current_token = next(token_iter, None)
    logger.debug(f"{head = }, {current_token = }, {token_iter.whole_ind = }")

    if isinstance(head, BitNode):
        assert isinstance(
            current_token, bool
        ), f"Expected bit but got {type(current_token)}"
        logger.debug("Handling a BitNode")
        if current_token:
            logger.debug("Going right")
            head.right = insert_into_trie(head.right, token_iter)
        else:
            logger.debug("Going left")
            head.left = insert_into_trie(head.left, token_iter)

    elif isinstance(head, FieldNode):
        assert isinstance(
            current_token, NamedField
        ), f"Expected NamedField but got {type(current_token)}"
        assert (
            head.named_field == current_token
        ), f"Incompatible named fields: {head.named_field} vs {current_token}"
        logger.debug(f"Inserting {head = }")
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
