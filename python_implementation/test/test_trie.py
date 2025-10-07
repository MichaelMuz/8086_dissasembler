import logging
import unittest

from python_implementation.src.base.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
)
from python_implementation.src.trie import (
    BitModeSchemaIterator,
    BitNode,
    FieldNode,
    LeafNode,
    insert_into_trie,
)


logging.basicConfig(level=logging.DEBUG)


class TestBitModeSchemaIterator(unittest.TestCase):
    def test_iteration(self):
        """Test of iteration and is_next_named through various states"""
        it = BitModeSchemaIterator(
            InstructionSchema(
                "mnemonic",
                LiteralField(0b101, 3),
                [
                    LiteralField(0b11, 2),
                    NamedField.D,
                    NamedField.W,
                    LiteralField(0b1, 1),
                ],
                {},
            )
        )

        # Start: in first literal, should not be at named field
        assert it.is_next_named() == False
        assert next(it) == True  # 1
        assert it.is_next_named() == False
        assert next(it) == False  # 0
        assert it.is_next_named() == False
        assert next(it) == True  # 1

        # Still in second literal
        assert it.is_next_named() == False
        assert next(it) == True  # 1
        assert it.is_next_named() == False
        assert next(it) == True  # 1

        # Now at NamedField.D
        assert it.is_next_named() == True
        assert next(it) == NamedField.D

        # Now at NamedField.W
        assert it.is_next_named() == True
        assert next(it) == NamedField.W

        # Now at final literal
        assert it.is_next_named() == False
        assert next(it) == True  # 1

        # End of iteration
        assert it.is_next_named() == False
        with self.assertRaises(StopIteration):
            next(it)

    def test_iteration_small_first_field(self):
        it = BitModeSchemaIterator(
            InstructionSchema(
                "mnemonic",
                LiteralField(0b1, 1),
                [NamedField.D],
                {},
            )
        )
        assert not it.is_next_named()
        assert next(it) == True
        assert it.is_next_named()
        assert next(it) == NamedField.D
        assert not it.is_next_named()
        with self.assertRaises(StopIteration):
            next(it)


class TestTrie(unittest.TestCase):
    def test_empty_insert(self):
        head = insert_into_trie(
            None,
            BitModeSchemaIterator(
                InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {})
            ),
        )

        # 1
        assert isinstance(head, BitNode)
        assert head.left is None

        # 0
        node = head.right
        assert isinstance(node, BitNode)
        assert node.right is None

        # bit 1
        node = node.left
        assert isinstance(node, BitNode)
        assert node.left is None

        node = node.right
        assert isinstance(node, LeafNode)
        assert next(node.token_iter) == NamedField.D

        with self.assertRaises(StopIteration):
            next(node.token_iter)

    def test_overlapping_path_insert(self):
        head = insert_into_trie(
            None,
            BitModeSchemaIterator(
                InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {})
            ),
        )
        head = insert_into_trie(
            head,
            BitModeSchemaIterator(
                InstructionSchema("move", LiteralField(0b100, 3), [NamedField.D], {})
            ),
        )

        # 1
        assert isinstance(head, BitNode)
        assert head.left is None

        # 0
        node = head.right
        assert isinstance(node, BitNode)
        assert node.right is None

        # bit 0/1 (diverge)
        node = node.left
        assert isinstance(node, BitNode)

        one_split = node.right
        two_split = node.left
        assert isinstance(one_split, LeafNode)
        assert isinstance(two_split, LeafNode)
        assert next(one_split.token_iter) == NamedField.D
        assert next(two_split.token_iter) == NamedField.D

        with self.assertRaises(StopIteration):
            next(one_split.token_iter)

        with self.assertRaises(StopIteration):
            next(two_split.token_iter)

    def test_overlapping_path_insert(self):
        head = insert_into_trie(
            None,
            BitModeSchemaIterator(
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [NamedField.D, LiteralField(0b1, 1), NamedField.ADDR_LO],
                    {},
                )
            ),
        )

        # 1
        assert isinstance(head, BitNode)
        assert head.left is None

        node = head.right
        assert isinstance(node, LeafNode)
        # curled up on named field
        assert node.token_iter.is_next_named()

        head = insert_into_trie(
            head,
            BitModeSchemaIterator(
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [NamedField.D, LiteralField(0b0, 1), NamedField.ADDR_HI],
                    {},
                )
            ),
        )

        # 1
        assert isinstance(head, BitNode)
        assert head.left is None

        # the leaf node uncurled
        node = head.right
        assert isinstance(node, FieldNode)
        assert node.named_field == NamedField.D

        # 0/1 (diverge on second literal)
        node = node.next
        assert isinstance(node, BitNode)
        old_leaf = node.right
        new_leaf = node.left
        assert isinstance(new_leaf, LeafNode)
        assert isinstance(old_leaf, LeafNode)
        assert next(old_leaf.token_iter) == NamedField.ADDR_LO
        assert next(new_leaf.token_iter) == NamedField.ADDR_HI

    def test_full_unroll(self):
        head = insert_into_trie(
            None,
            BitModeSchemaIterator(
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [
                        NamedField.D,
                        LiteralField(0b1, 1),
                        NamedField.ADDR_LO,
                        LiteralField(0b011, 3),
                    ],
                    {},
                )
            ),
        )

        # 1
        assert isinstance(head, BitNode)
        assert head.left is None

        node = head.right
        assert isinstance(node, LeafNode)
        # curled up on named field
        assert node.token_iter.is_next_named()

        head = insert_into_trie(
            head,
            BitModeSchemaIterator(
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [
                        NamedField.D,
                        LiteralField(0b1, 1),
                        NamedField.ADDR_LO,
                        LiteralField(0b11, 2),
                    ],
                    {},
                )
            ),
        )
        assert isinstance(head, BitNode)
        assert head.left is None
        node = head.right
        assert isinstance(node, FieldNode)
        assert node.named_field == NamedField.D
        node = node.next
        assert isinstance(node, BitNode)
        assert node.left is None
        node = node.right
        assert isinstance(node, FieldNode)
        assert node.named_field == NamedField.ADDR_LO
        node = node.next
        assert isinstance(node, BitNode)
        assert isinstance(node.left, BitNode) and isinstance(node.right, BitNode)

        l = node.left
        r = node.right
        assert r.left is None and isinstance(r.right, LeafNode)
        r_leaf = r.right
        with self.assertRaises(StopIteration):
            next(r_leaf.token_iter)

        assert l.left is None and isinstance(l.right, BitNode)
        l = l.right
        assert l.left is None and isinstance(l.right, LeafNode)
        l_leaf = l.right
        with self.assertRaises(StopIteration):
            next(l_leaf.token_iter)
