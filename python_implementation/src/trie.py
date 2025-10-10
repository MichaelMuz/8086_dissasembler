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


@dataclass
class BitNode:
    left: Any = None
    right: Any = None
    next: Any = None
    parent: Any = None

    def insert(self, tok_iter):
        curr_val = next(tok_iter, None)
        if curr_val is None:
            return self

        curr_node = BitNode() if isinstance(curr_val, bool) else FieldNode(curr_val)

        match curr_val:
            case True:
                self.right = curr_node
            case False:
                self.left = curr_node
            case NamedField():
                self.next = curr_node
        return curr_node


@dataclass
class FieldNode:
    named_field: NamedField
    left: Any = None
    right: Any = None
    next: Any = None
    parent: Any = None

    def insert(self, tok_iter):
        curr_val = next(tok_iter, None)
        if curr_val is None:
            return self

        curr_node = BitNode() if isinstance(curr_val, bool) else FieldNode(curr_val)

        match curr_val:
            case True:
                self.right = curr_node
            case False:
                self.left = curr_node
            case NamedField():
                self.next = curr_node
        return curr_node


@dataclass
class LeafNode:
    token_iter: BitModeSchemaIterator
    left: Any = None
    right: Any = None
    next: Any = None
    parent: Any = None

    def unroll(self):
        # oull out one more
        curr_val = next(self.token_iter)
        # create right node type
        curr_node = BitNode() if isinstance(curr_val, bool) else FieldNode(curr_val)
        # figure out where to put the rest of the coil
        if self.token_iter.has_more():
            match self.token_iter.peek():
                case True:
                    curr_node.right = self
                case False:
                    curr_node.left = self
                case NamedField():
                    curr_node.next = self

        # update parent with uncoiled head
        match curr_val:
            case True:
                assert self.parent.right == self
                self.parent.right = curr_node
            case False:
                assert self.parent.left == self
                self.parent.left = curr_node
            case NamedField():
                assert self.parent.next == self
                self.parent.next = curr_node
        return curr_node

    def insert(self, tok_iter):
        return self.unroll().insert(tok_iter)
