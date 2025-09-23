from functools import singledispatchmethod
from typing import Never, Self, TypeAlias
from dataclasses import dataclass
from python_implementation.src import utils
from python_implementation.src.builder import DecodeAccumulator
from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)


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

    @singledispatchmethod
    def insert(self, bit: bool) -> "tuple[BitNode, BitNode]":
        new_node = BitNode()
        if bit:
            self.right = new_node
        else:
            self.left = new_node
        return self, new_node

    @insert.register
    def _(self, _: NamedField) -> Never:
        raise ValueError("Cannot insert named field into Bitnode")


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None" = None

    @singledispatchmethod
    def insert(self, named_field: NamedField) -> "tuple[FieldNode, FieldNode]":
        assert (
            self.named_field is named_field
        ), f"Incompatible named fields: {self.named_field} vs {named_field}"
        return self, self

    @insert.register
    def _(self, _: bool) -> Never:
        raise ValueError("Cannot insert bit into Bitnode")


@dataclass
class LeafNode:
    token_iter: BitModeInstructionSchemaIterator

    def insert(self, val: bool | NamedField) -> "tuple[BitNode | FieldNode, Node]":
        first_node = None
        prev_node = None
        # if curr is still a bool then we need to put it in the right place in the previous bitnode chain (if there was one)
        # if curr becomes a named field we need to put it in the right place in the previous bitnode chain (if there was one) and break bc we will now coil the rest
        for curr in self.token_iter:
            if isinstance(curr, NamedField):
                curr_node = FieldNode(curr)
            elif prev_node is not None:
                _, curr_node = prev_node.insert(curr)
            else:
                curr_node = BitNode()

            if first_node is None:
                first_node = curr_node

            if not isinstance(curr_node, BitNode):
                break

            prev_node = curr_node

        assert first_node is not None, "We had an empty iterator"

        return first_node, first_node.insert(val)[1]


Node: TypeAlias = BitNode | FieldNode | LeafNode


# Need to have final instruction type as soon as possible in the tree bc need to have implied values
class Trie:
    def __init__(self, head: BitNode) -> None:
        self.head = head

    @classmethod
    def from_parsable_instructions(cls, instructions: list[InstructionSchema]) -> Self:
        all_inst_iters = map(
            BitModeInstructionSchemaIterator,
            map(FieldModeInstructionSchemaIterator, instructions),
        )
        head = LeafNode(next(all_inst_iters))
        for instruction_iter in all_inst_iters:
            curr_head = head
            prev = None
            for val in instruction_iter:
                a = curr_head.insert(val)
                new_prev, curr_head = curr_head.insert(val)
                if prev is not None:
                    prev.ne
        return Trie(head)


# when knowing the full instruction or using the tree that pattern we always have is
# "ok, how many more bits to read?", the requestors will answer this. One for a Trie and one for normal
# stream of instruction schemas.


class TrieRequester:
    def __init__(self, trie: Trie, accumulator: DecodeAccumulator):
        self.current_node = trie.head
        self.accumulator = accumulator

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
            return True
        return False


class FieldsRequestor:
    def __init__(
        self,
        token_iter: FieldModeInstructionSchemaIterator,
        accumulator: DecodeAccumulator,
    ) -> None:
        self.token_iter = token_iter
        self.accumulator = accumulator
        self.current_field = self._get_next_field()

    def _get_next_field(self) -> SchemaField | None:
        self.current_field = next(self.token_iter, None)

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
