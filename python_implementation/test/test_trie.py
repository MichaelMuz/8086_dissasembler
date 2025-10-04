import logging
import unittest
from venv import logger

from python_implementation.src.base.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
)
from python_implementation.src.trie import (
    BitModeSchemaIterator,
    BitNode,
    LeafNode,
    insert_into_trie,
)


logging.basicConfig(level=logging.DEBUG)


class TestBitModeSchemaIterator(unittest.TestCase):
    def test_iteration(self):
        it = BitModeSchemaIterator(
            InstructionSchema(
                "mnemonic",
                LiteralField(0b101, 3),
                [LiteralField(0b10, 2), NamedField.D],
                {},
            )
        )
        logger.debug([x for x in it])
        assert next(it) == True
        assert next(it) == False
        assert next(it) == NamedField.D


class TestTrie(unittest.TestCase):
    def test_empty_insert(self):
        head = insert_into_trie(
            None,
            BitModeSchemaIterator(
                InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {})
            ),
        )

        assert isinstance(head, BitNode)
        assert head.left is None

        node = head.right  # bit 1
        assert isinstance(node, BitNode)
        assert node.right is None

        node = node.left  # bit 0
        assert isinstance(node, BitNode)
        assert node.left is None

        node = node.right  # bit 1
        assert isinstance(node, LeafNode)
        assert next(node.token_iter) == NamedField.D

        with self.assertRaises(StopIteration):
            next(node.token_iter)
