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

    def __next__(self) -> bool | NamedField:
        for self.whole_ind in range(self.whole_ind, len(self.instruction.fields)):
            if isinstance(self._curr_inst, NamedField):
                return self._curr_inst

            elif self.bit_ind < self._curr_inst.bit_width:
                to_ret = bool(
                    utils.get_sub_most_sig_bits(
                        self._curr_inst.literal_value, self.bit_ind, 1
                    )
                )
                self.bit_ind += 1
                return to_ret

            else:
                self.bit_ind = 0

        raise StopIteration

    def to_whole_field_iter(self) -> Iterator[SchemaField]:
        match self._curr_inst:
            case LiteralField(bit_width=bw):
                assert (
                    self.whole_ind == bw + 1
                ), "Cannot Transition on unfinished literal"
            case NamedField():
                assert self.bit_ind == 0, "Inconsistant bit index state"

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


Node: TypeAlias = BitNode | FieldNode | LeafNode


def insert_into_trie(
    head: Node | None,
    token_iter: BitModeSchemaIterator,
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
                BitModeSchemaIterator(instruction),
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
    whole_iter = head.token_iter.to_whole_field_iter()
    while (e := next(whole_iter, None)) is not None:
        val = bit_iter.next_bits(e.bit_width)
        if isinstance(e, LiteralField):
            assert val == e.literal_value
        else:
            acc.with_field(e, val)

    return acc.build(head.token_iter.instruction)
