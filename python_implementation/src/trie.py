from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Self

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

    def to_whole_field_iter(self) -> Iterator[SchemaField]:
        match self._curr_inst:
            case LiteralField(bit_width=bw):
                assert self.bit_ind == bw, "Cannot Transition on unfinished literal"
            case NamedField():
                assert self.bit_ind == 0, "Inconsistent bit index state"

        return (self._fields[i] for i in range(self.whole_ind, len(self._fields)))


# a branch is a bundle of pointers and non-head nodes have values
# branches will all be by default completely coiled until they are inserted into another branch
# at that point the inserted into branch will uncoil one instruction
# @dataclass
# class _HeadNode:
#     left: Any = None
#     right: Any = None
#     next: Any = None

#     def insert(self, node):
#         match node:
#             case Node(True):
#                 self.right = node
#             case Node(False):
#                 self.left = node
#             case Node(NamedField()):
#                 self.next = node
#             case _:
#                 raise ValueError("Unexpected node type")
#         return node


# @dataclass
# class Node(_HeadNode):
#     val: NamedField | bool = field(kw_only=True)


# @dataclass
# class Branch:
#     coil: BitModeSchemaIterator

#     def insert(self, other: Self):
#         # self needs to uncoild once
#         next_self = next(self.coil)
#         next_other = next(other.coil)
#         head = Node(val=next_self)
#         new_node = head.insert(Node(val=next_other))

#         if next_self == next_other:
#             self.insert(other)


# class Node:
#     def __init__(self, coil: BitModeSchemaIterator) -> None:
#         self.coil = coil
#         self.value = next(self.coil)
#         self._left: Any = None
#         self._right: Any = None
#         self._next: Any = None

#     def _unroll_one(self):
#         if self.coil is None:
#             return
#         unrolled_node = Node(self.coil)
#         attr = f"_{self.get_correct_attr(unrolled_node.value)}"
#         setattr(self, attr, unrolled_node)
#         self.coil = None

#     @cached_property
#     def left(self):
#         self._unroll_one()
#         return self._left

#     @cached_property
#     def right(self):
#         self._unroll_one()
#         return self._right

#     @cached_property
#     def next(self):
#         self._unroll_one()
#         return self._next

#     def get_correct_attr(self, val: NamedField | bool):
#         match val:
#             case True:
#                 return "right"
#             case False:
#                 return "left"
#             case NamedField():
#                 return "next"
#             # case _:
#             #     raise ValueError("Unexpected node type")

#     def insert(self, other_node: "BitModeSchemaIterator | Node"):
#         # I assume the parent node did the right thing pairing us together
#         # if we continue on the same path, that is fine it means we were prefixed the same so far
#         # I may have the issue that I insert into my child the value of the current parent
#         if not isinstance(other_node, Node):
#             other_node = Node(other_node)

#         att = self.get_correct_attr(other_node.value)
#         att_val = getattr(self, att)
#         if att_val is not None:
#             att_val.insert(other_node)
#         else:
#             setattr(self, f"_{att}", other_node)


class Node:
    """
    How this works:
    1. when insert is called it is for the next level bc insert starts at the dummy head node so comparing value at dummy and the first thing makes no sense
    2. when being inserted into we know our val from peeking so throw out next in could and make node from rest. Attach it to the correct spot based on new child's value. This is how we lazily unroll, on insert.
    3. get correct direction from the thing we are inserting. If we don't have that direction, coil the rest of what we are inserting and attach it to us there. Otherwise call insert on what we already have in that direction
    """

    def __init__(self, coil: BitModeSchemaIterator) -> None:
        self.value = coil.peek()
        self.coil = coil
        self.children: list[Node | None] = [None, None, None]

    def get_ind(self, val: bool | NamedField) -> int:
        match val:
            case False:
                return 0
            case NamedField():
                return 1
            case True:
                return 2

    def insert(self, inst: BitModeSchemaIterator):
        if self.coil is not None:
            _ = next(self.coil)
            new_child = Node(self.coil)
            ind = self.get_ind(new_child.value)
            self.children[ind] = new_child

        ind = self.get_ind(inst.peek())
        if self.children[ind] is None:
            self.children[ind] = Node(inst)
        else:
            if ind == 1:
                assert self.children[1].value == inst.peek(), "Ambiguous ISA"
            _ = next(inst)
            self.children[ind].insert(inst)


class DummyNode(Node):
    def __init__(self) -> None:
        self.value = -1
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
