from abc import abstractmethod
from typing import Generator, Generic, Iterator, Self, TypeAlias, TypeVar
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


# want to go through with literal fields broken down. Then we have state change function that returns a new thing that goes through the rest by whole chunk, checking to make sure we didn't
# switch in a broken down literal part. The general concept of how each iterator works is pretty simple, they have an iterator and they pull from it until it is over then they grab the next thing in the chain.
# We can have a base class that does this, calling .get_next_subiter and child classes that override it based on if they want to break down literal filed iterators or not


class SubIterator(Iterator):
    @abstractmethod
    def has_more(self) -> bool:
        pass


class LiteralFieldIterator(SubIterator):
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


class WholeFieldIterator(SubIterator):
    def __init__(self, field: SchemaField):
        self.field = field
        self.used = False

    def has_more(self) -> bool:
        return not self.used

    def __next__(self) -> SchemaField:
        if not self.has_more():
            raise StopIteration
        self.used = True
        return self.field


T = TypeVar("T")


class InstructionSchemaIterator(Generic[T]):
    def __init__(self, instruction: InstructionSchema, starting_ind=0) -> None:
        self.instruction = instruction
        self.field_ind = starting_ind
        self.curr_iter = self.create_sub_iter()

    @abstractmethod
    def create_sub_iter(self) -> SubIterator:
        pass

    def __next__(self) -> T:
        if not self.has_more():
            raise StopIteration
        return next(self.curr_iter)

    def has_more(self) -> bool:
        if not self.curr_iter.has_more():
            self.field_ind += 1
            if self.field_ind < len(self.instruction.fields):
                self.curr_iter = self.create_sub_iter()
        return self.curr_iter.has_more()


class BitModeInstructionSchemaIterator(InstructionSchemaIterator[bool | NamedField]):
    def create_sub_iter(self) -> WholeFieldIterator | LiteralFieldIterator:
        field = self.instruction.fields[self.field_ind]
        if isinstance(field, NamedField):
            return WholeFieldIterator(field)
        return LiteralFieldIterator(field)

    def to_field_mode(self):
        assert (
            not self.curr_iter.has_more()
        ), "Cannot transition until full field consumed in bit mode"
        return FieldModeInstructionSchemaIterator(self.instruction, self.field_ind)


class FieldModeInstructionSchemaIterator(InstructionSchemaIterator[SchemaField]):
    def create_sub_iter(self) -> WholeFieldIterator:
        return WholeFieldIterator(self.instruction.fields[self.field_ind])


def bin_iter(field: LiteralField) -> Generator[bool, None, None]:
    for i in range(field.bit_width):
        yield bool(utils.get_sub_most_sig_bits(field.literal_value, i, 1))


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
