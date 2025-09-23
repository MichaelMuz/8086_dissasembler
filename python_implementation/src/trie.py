from typing import Self, TypeAlias
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


@dataclass
class FieldNode:
    named_field: NamedField
    next: "Node | None" = None


@dataclass
class LeafNode:
    token_iter: BitModeInstructionSchemaIterator


Node: TypeAlias = BitNode | FieldNode | LeafNode


def insert_into_trie(
    head: Node | None,
    token_iter: BitModeInstructionSchemaIterator,
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
                BitModeInstructionSchemaIterator(
                    FieldModeInstructionSchemaIterator(instruction)
                ),
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

    def get_product(self) -> LeafNode:
        assert self.is_complete()
        assert isinstance(
            self.current_node, LeafNode
        ), "Non-leaf node at bottom of tree"
        return self.current_node


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


class Requestor:
    def __init__(self, trie: Trie, accumulator: DecodeAccumulator):
        self.state = TrieRequester(trie, accumulator)

    def bits_needed(self) -> int:
        return self.bits_needed()

    def consume(self, bits: int) -> None:
        self.state.consume(bits)
        if self.state.is_complete() and isinstance(self.state, TrieRequester):
            self.state = FieldsRequestor(
                self.state.get_product().token_iter.to_whole_field_mode(),
                self.state.accumulator,
            )

    def is_complete(self):
        return self.state.is_complete()
