from typing import Iterator, TypeAlias
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
    left: "Node | None"
    right: "Node | None"

    @staticmethod
    def get_side_att_name(bit: bool):
        return "right" if bit else "left"


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None"


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


def insert_into_trie(head: Node, token_iter: Iterator[NamedField | bool]) -> None:
    current_token = next(token_iter, None)
    if current_token is None:
        return

    next_node_attr_name: str
    if isinstance(head, BitNode):
        assert isinstance(
            current_token, bool
        ), f"Expected bit but got {type(current_token)}"
        next_node_attr_name = "right" if current_token else "left"
    else:
        assert isinstance(
            current_token, NamedField
        ), f"Expected NamedField but got {type(current_token)}"
        assert (
            head.named_field == current_token
        ), f"Incompatible named fields: {head.named_field} vs {current_token}"
        next_node_attr_name = "next"

    next_node = getattr(head, next_node_attr_name)
    if next_node is None:
        setattr(head, next_node_attr_name, build_subtrie_from_remaining(token_iter))
    else:
        insert_into_trie(next_node, token_iter)


def build_subtrie_from_remaining(
    token_iter: Iterator[NamedField | bool],
) -> Node | None:
    current_token = next(token_iter, None)
    if current_token is None:
        return None

    if isinstance(current_token, int):
        root = BitNode(None, None)
        setattr(
            root,
            BitNode.get_side_att_name(current_token),
            build_subtrie_from_remaining(token_iter),
        )
        return root

    elif isinstance(current_token, NamedField):
        root = FieldNode(current_token, None)
        root.next = build_subtrie_from_remaining(token_iter)
        return root
