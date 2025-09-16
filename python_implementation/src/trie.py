from typing import Iterator, Self, TypeAlias
from dataclasses import dataclass
import itertools
from python_implementation.src.builder import DisassembledInstruction
from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import get_sub_most_sig_bits
from python_implementation.src.decoder import BitIterator


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
    instruction: SchemaField
    token_iter: Iterator[NamedField | bool]


Node: TypeAlias = BitNode | FieldNode | LeafNode


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
    head: Node | None, token_iter: Iterator[NamedField | bool], instruction: SchemaField
) -> Node:
    current_token = next(token_iter, None)
    if current_token is None:
        assert head is None, "Instruction ends while another continues, ambiguous"
        return LeafNode(instruction, token_iter)

    if head is None:
        # No comparison? We are a coiled branch that will unfold lazily
        return LeafNode(instruction, itertools.chain([current_token], token_iter))

    if isinstance(head, BitNode):
        assert isinstance(
            current_token, bool
        ), f"Expected bit but got {type(current_token)}"
        if current_token:
            head.right = insert_into_trie(head.right, token_iter, instruction)
        else:
            head.left = insert_into_trie(head.left, token_iter, instruction)

    elif isinstance(head, FieldNode):
        assert isinstance(
            current_token, NamedField
        ), f"Expected NamedField but got {type(current_token)}"
        assert (
            head.named_field == current_token
        ), f"Incompatible named fields: {head.named_field} vs {current_token}"
        head.next = insert_into_trie(head.next, token_iter, instruction)
    else:
        # unspring coiled branch that head is
        once_uncoiled_head = next(head.token_iter, None)
        assert (
            once_uncoiled_head is not None
        ), "Asking to unroll fully unrolled instruction"
        if isinstance(current_token, NamedField):
            uncoiled_node = FieldNode(named_field=current_token)
        else:
            uncoiled_node = BitNode()

        head_rewind_iter = itertools.chain([once_uncoiled_head], head.token_iter)
        new_rewind_iter = itertools.chain([current_token], token_iter)

        # We are comparing the uncoiled thing against itself so we can reatach the rest of the coil
        # only adds iterations for one series of bits or one named field, then goes back to being coiled
        # only one extra iteration on top of what it does otherwise for bits (this iteration) and for fields it is just 2 because we assert it is correct and the next gives a leaf node
        head = insert_into_trie(uncoiled_node, head_rewind_iter, head.instruction)
        # now next instruction will actually add a node to the trie
        head = insert_into_trie(head, new_rewind_iter, instruction)

    return head


# Need to have final instruction type as soon as possible in the tree bc need to have implied values
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

    # def _is_needed(self, schema_field: SchemaField, parsed_fields) -> bool:
    #     if isinstance(schema_field, LiteralField):
    #         return True

    #     if schema_field in self.ALWAYS_NEEDED_FIELDS:
    #         return True
    #     elif schema_field is NamedField.DATA_IF_W1:
    #         return bool(self.parsed_fields[NamedField.W])
    #     elif schema_field is NamedField.DATA_IF_SW_01:
    #         return self.sign_extension == 0 and self.word
    #     elif schema_field in (NamedField.DISP_LO, NamedField.DISP_HI):
    #         return (self.mode.type is Mode.Type.WORD_DISPLACEMENT_MODE) or (
    #             self.mode.type is Mode.Type.BYTE_DISPLACEMENT_MODE
    #             and (schema_field is NamedField.DISP_LO)
    #         )
    #     else:
    #         raise ValueError(f"don't know how to check if {schema_field} is needed")

    # def _parse_rec(
    #     self, head: Node | None, bit_iter: BitIterator
    # ) -> DisassembledInstruction:
    #     if head is None:
    #         return
    #     elif isinstance(head, BitNode):
    #         if bit_iter.next_bits(1):
    #             return self._parse_rec(head.right, bit_iter)
    #         else:
    #             return self._parse_rec(head.left, bit_iter)
    #     else:

    #         field_value = bit_iter.next_bits(head.named_field.bit_width)

    # def parse(self, bit_iter: BitIterator) -> DisassembledInstruction:
    #     self._parse_rec(self, self.head, bit_iter)
