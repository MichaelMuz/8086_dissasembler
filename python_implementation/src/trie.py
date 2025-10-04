from collections.abc import Iterator
from dataclasses import dataclass
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

    @property
    def _fields(self):
        return self.instruction.fields

    @property
    def _curr_inst(self):
        return self._fields[self.whole_ind]

    def __iter__(self):
        return self

    def __next__(self) -> bool | NamedField:
        next_ret = None
        if self.whole_ind == len(self.instruction.fields):
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
            logger.info(
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


def insert_into_trie(
    head: Node | None,
    token_iter: BitModeSchemaIterator,
) -> Node:
    current_token = next(token_iter, None)
    logger.debug(f"{head = }, {current_token = }")

    if current_token is None:
        # both done, we are a leaf at the very bottom of a finished instruction
        assert head is None, "Instruction ends while another continues, ambiguous"
        logger.debug("Completely finished instruction, leaf node with empty iterator")
        head = LeafNode(token_iter)
        return head

    elif isinstance(head, LeafNode):
        # head will be None and the correct thing will be created for head, then we will insert the current token
        logger.debug("Inserting a leaf node, making a new trie with rest of fields")
        head = insert_into_trie(None, head.token_iter)

    if head is None:
        # head is None so we are the root, make the correct node
        if isinstance(current_token, bool):
            head = BitNode()
        else:
            head = FieldNode(current_token)
        logger.debug(f"Head is None so we made a {type(head)}")

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
