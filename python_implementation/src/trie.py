from collections.abc import Iterator
from functools import cached_property
from typing import Self

from python_implementation.src.base.schema import (
    InstructionSchema,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import get_sub_most_sig_bits


class BitModeSchemaIterator:
    def __init__(
        self,
        instruction: InstructionSchema,
        whole_ind: int | None = None,
        bit_ind: int | None = None,
    ) -> None:
        self.instruction = instruction
        self.whole_ind = whole_ind or 0
        self.bit_ind = bit_ind or 0

    def clone(self):
        return BitModeSchemaIterator(self.instruction, self.whole_ind, self.bit_ind)

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

    def peek(self) -> NamedField | bool:
        return self._next(False)

    def has_more(self):
        return self.whole_ind < len(self._fields)

    def _next(self, inc: bool) -> bool | NamedField:
        next_ret = None
        if self.whole_ind == len(self._fields):
            raise StopIteration
        elif isinstance(self._curr_inst, NamedField):
            next_ret = self._curr_inst
            self.whole_ind += inc
        else:
            next_ret = bool(
                get_sub_most_sig_bits(
                    self._curr_inst.literal_value,
                    self.bit_ind,
                    1,
                    total_bits=self._curr_inst.bit_width,
                )
            )
            self.bit_ind += inc
            if self.bit_ind == self._curr_inst.bit_width:
                self.bit_ind = 0
                self.whole_ind += 1
        return next_ret

    def __next__(self) -> bool | NamedField:
        return self._next(True)

    def can_transition(self):
        return self.bit_ind == 0 or self.bit_ind == self._curr_inst.bit_width

    def to_whole_field_iter(self) -> Iterator[SchemaField]:
        assert self.can_transition()
        if isinstance(self._curr_inst, NamedField):
            assert self.bit_ind == 0, "Inconsistent bit index state"

        return (self._fields[i] for i in range(self.whole_ind, len(self._fields)))


class Node:
    """
    How this works:
    1. when insert is called it is for the next level bc insert starts at the dummy head node so comparing value at dummy and the first thing makes no sense
    2. when being inserted into we know our val from peeking so throw out next in could and make node from rest. Attach it to the correct spot based on new child's value. This is how we lazily unroll, on insert.
    3. get correct direction from the thing we are inserting. If we don't have that direction, coil the rest of what we are inserting and attach it to us there. Otherwise call insert on what we already have in that direction

    We can't have a situation where one shorter instruction is the exact prefix for a longer one
    We can't have a situation where on one node there are multiple children of different NamedFields
    """

    def __init__(
        self, coil: BitModeSchemaIterator, value: bool | NamedField | None = None
    ) -> None:
        if value is None:
            value = next(coil)

        self.value = value
        self.coil = coil
        self.children: list[Node | None] = [None, None, None]

    def get_rest_of_coil(self):
        assert self.coil is not None
        new_coil = self.coil.clone()
        return new_coil

    LEFT, NAMED, RIGHT = 0, 1, 2

    @classmethod
    def get_ind(cls, val: bool | NamedField) -> int:
        match val:
            case False:
                return cls.LEFT
            case NamedField():
                return cls.NAMED
            case True:
                return cls.RIGHT

    def insert(self, inst: BitModeSchemaIterator):
        if self.coil is not None:
            new_child = Node(self.coil)
            ind = self.get_ind(new_child.value)
            self.children[ind] = new_child
            self.coil = None

        nxt = next(inst)
        ind = self.get_ind(nxt)
        if self.children[ind] is None:
            self.children[ind] = Node(inst, value=nxt)
        else:
            if ind == self.NAMED:
                assert self.children[self.NAMED].value == nxt, "Ambiguous ISA"
            self.children[ind].insert(inst)


class DummyNode(Node):
    def __init__(self) -> None:
        self.value = True
        self.coil = None
        self.children: list[Node | None] = [None, None, None]


class Trie:
    def __init__(self, dummy_head: DummyNode) -> None:
        self.dummy_head = dummy_head

    @classmethod
    def from_parsable_instructions(cls, instructions: list[InstructionSchema]) -> Self:
        head = DummyNode()
        for instruction in instructions:
            head.insert(BitModeSchemaIterator(instruction))

        return cls(head)
