from typing import Iterator, Self, TypeAlias
from dataclasses import dataclass
import itertools
from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import get_sub_most_sig_bits


@dataclass
class BitNode:
    left: "Node | None" = None
    right: "Node | None" = None


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None" = None


Node: TypeAlias = BitNode | FieldNode


def expand_fields_to_bits(fields: list[SchemaField]) -> Iterator[NamedField | bool]:
    generators = []
    for field in fields:
        if isinstance(field, LiteralField):
            generators.append(
                get_sub_most_sig_bits(field.literal_value, i, 1)
                for i in range(field.bit_width)
            )
        else:
            generators.append([field])  # Single item "generator"

    return itertools.chain(*generators)


def insert_into_trie(
    head: Node | None, token_iter: Iterator[NamedField | bool]
) -> Node | None:
    current_token = next(token_iter, None)
    if current_token is None:
        return None

    if head is None:
        if isinstance(current_token, NamedField):
            head = FieldNode(named_field=current_token)
        else:
            head = BitNode()

    if isinstance(head, BitNode):
        assert isinstance(
            current_token, bool
        ), f"Expected bit but got {type(current_token)}"
        if current_token:
            head.right = insert_into_trie(head.right, token_iter)
        else:
            head.left = insert_into_trie(head.left, token_iter)

    else:
        assert isinstance(
            current_token, NamedField
        ), f"Expected NamedField but got {type(current_token)}"
        assert (
            head.named_field == current_token
        ), f"Incompatible named fields: {head.named_field} vs {current_token}"
        head.next = insert_into_trie(head.next, token_iter)

    return head


class Trie:
    def __init__(self, head: BitNode) -> None:
        self.head = head

    @classmethod
    def from_parsable_instructions(cls, instructions: list[InstructionSchema]) -> Self:
        head = None
        for instruction in instructions:
            head = insert_into_trie(head, expand_fields_to_bits(instruction.fields))
        assert isinstance(head, BitNode), f"Expected BitNode, got `{type(head)}`"
        return cls(head)
