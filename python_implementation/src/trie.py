from typing import Generator, Iterator, Self, TypeAlias
from dataclasses import dataclass
import itertools
from python_implementation.src import utils
from python_implementation.src.builder import DecodeAccumulator
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
    instruction: InstructionSchema
    coil_start: NamedField | None
    token_iter: Iterator[NamedField | bool]


def bin_iter(field: LiteralField) -> Generator[bool, None, None]:
    for i in range(field.bit_width):
        yield bool(utils.get_sub_most_sig_bits(field.literal_value, i, 1))


class InstructionIterator:
    def __init__(self, instruction: InstructionSchema) -> None:
        self.instruction = instruction
        self.ind = 0
        self.sub_iter = None

    def get_bit_or_named_field(self) -> bool | NamedField:
        next_up = None
        if self.sub_iter is not None:
            next_up = next(self.sub_iter, None)
        if next_up is None:
            self.sub_iter = None
            match self.instruction.fields[self.ind]:
                case LiteralField() as x:
                    self.sub_iter = bin_iter(x)
                    next_up = next(self.sub_iter)
                case NamedField() as x:
                    next_up = x
            self.ind += 1

        assert next_up is not None, "Somehow next is None"
        return next_up

    def get_whole_field(self):
        if self.sub_iter is not None:
            unfinished_lit = ((1 << i * int(e)) for i, e in self.sub_iter)
            return unfinished_lit
        else:
            return


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
    head: Node | None,
    token_iter: Iterator[NamedField | bool],
    instruction: InstructionSchema,
) -> Node:
    current_token = next(token_iter, None)
    if current_token is None:
        assert head is None, "Instruction ends while another continues, ambiguous"
        head = LeafNode(instruction, None, token_iter)

    elif head is None:
        # No comparison? We are a coiled branch that will unfold lazily
        if isinstance(current_token, bool):
            # never coil on literal field, we don't want to split fields
            head = BitNode()
        else:
            # can coil on a named field, we are not splitting things
            head = LeafNode(instruction, current_token, token_iter)

    elif isinstance(head, BitNode):
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
        assert (
            head.coil_start is not None
        ), "Asking to unroll fully unrolled instruction"
        uncoiled_node = FieldNode(named_field=head.coil_start)

        new_rewind_iter = itertools.chain([current_token], token_iter)

        # We are comparing the uncoiled thing against itself so we can reatach the rest of the coil
        # only adds iterations for one series of bits or one named field, then goes back to being coiled
        # only one extra iteration on top of what it does otherwise for bits (this iteration) and for fields it is just 2 because we assert it is correct and the next gives a leaf node
        head = insert_into_trie(uncoiled_node, head.token_iter, head.instruction)
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
            head = insert_into_trie(
                head, expand_fields_to_bits(instruction.fields), instruction
            )
        assert isinstance(head, BitNode), f"Expected BitNode, got `{type(head)}`"
        return cls(head)


# class TrieTraverser:
#     def __init__(self, trie: Trie) -> None:
#         self.curr_node = trie.head
#         self.acc = DecodeAccumulator()

#     def get_req_bits(self) -> int | None:
#         if isinstance(self.curr_node, BitNode):
#             return 1
#         elif isinstance(self.curr_node, FieldNode):
#             return self.curr_node.named_field.bit_width
#         else:
#             return None

#     def progress(self, val: int) -> int:
#         if isinstance(self.curr_node, BitNode):
#             return 1
#         elif isinstance(self.curr_node, FieldNode):
#             return self.curr_node.named_field.bit_width


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

    while (e := next(head.token_iter, None)) is not None:
        match e:
            case bool():
                bit_iter.next_bits(1)
            case NamedField():
                acc.with_field(e, bit_iter.next_bits(e.bit_width))

    return acc.build(head.instruction)


# when knowing the full instruction or using the tree that pattern we always have is
# "ok, how many more bits to read?", the requestors will answer this. One for a Trie and one for normal
# stream of instruction schemas.


class TrieRequester:
    def __init__(self, trie: Trie, accumulator: DecodeAccumulator):
        self.current_node = trie.head
        self.accumulator = accumulator
        self.instruction_schema = None

    def bits_needed(self) -> int:
        if isinstance(self.current_node, BitNode):
            return 1
        elif isinstance(self.current_node, FieldNode):
            return self.current_node.named_field.bit_width
        else:
            raise ValueError("Should be complete when at LeafNode")

    def consume(self, bits: int) -> None:
        assert self.current_node is not None, "Current node is None"
        assert not isinstance(
            self.current_node, LeafNode
        ), "Can't consume into Leaf Node"

        if isinstance(self.current_node, BitNode):
            self.current_node = (
                self.current_node.right if bits else self.current_node.left
            )
        elif isinstance(self.current_node, FieldNode):
            self.accumulator.with_field(self.current_node.named_field, bits)
            self.current_node = self.current_node.next

    def is_complete(self) -> bool:
        if isinstance(self.current_node, LeafNode):
            self.instruction_schema = self.current_node.instruction
            return True
        return False


class FieldsRequestor:
    def __init__(
        self, token_iter: Iterator[NamedField | bool], accumulator: DecodeAccumulator
    ) -> None:
        self.token_iter = token_iter
        self.accumulator = accumulator
        self.current_field = self._get_next_field()

    def _get_next_field(self) -> SchemaField | None:
        num_list = []
        while isinstance(next_thing := next(self.token_iter, None), bool):
            num_list.append(str(int(next_thing)))

        bit_count = len(num_list)
        acc_int = int("".join(num_list), 2)

        if bit_count > 0:
            if next_thing is not None:
                self.token_iter = itertools.chain([next_thing], self.token_iter)
            next_thing = LiteralField(acc_int, bit_count)

        if next_thing is not None and not self.accumulator.is_needed(next_thing):
            next_thing = self._get_next_field()
        return next_thing

    def bits_needed(self) -> int:
        assert self.current_field is not None, "Current field is None"
        return self.current_field.bit_width

    def consume(self, bits: int) -> None:
        assert self.current_field is not None, "Current field is None"
        if isinstance(self.current_field, NamedField):
            self.accumulator.with_field(self.current_field, bits)
        else:
            assert self.current_field.literal_value == bits, "Literal does not match"
        self.current_field = self._get_next_field()

    def is_complete(self) -> bool:
        return self.current_field is None
