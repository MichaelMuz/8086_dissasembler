import logging
import unittest

from python_implementation.src.base.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
)
from python_implementation.src.trie import (
    BitModeSchemaIterator,
    Trie,
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
        trie = Trie.from_parsable_instructions(
            [InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {})]
        )
        head = trie.dummy_head

        assert head.children[0] is None and head.children[1] is None
        head = head.children[2]

        # 1
        assert head is not None and isinstance(head.value, bool) and head.value is True
        # its coiled up
        assert head.coil is not None and not any(head.children)

    def test_overlapping_path_insert(self):
        trie = Trie.from_parsable_instructions(
            [
                InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {}),
                InstructionSchema("move", LiteralField(0b100, 3), [NamedField.D], {}),
            ]
        )
        head = trie.dummy_head

        assert head is not None
        assert head.children[0] is None and head.children[1] is None
        head = head.children[2]

        # 1
        assert head is not None and isinstance(head.value, bool) and head.value is True
        assert head.children[1] is None and head.children[2] is None
        head = head.children[0]

        # 0
        assert head is not None and isinstance(head.value, bool) and head.value is False
        assert head.children[1] is None

        # 0/1 diverge
        left = head.children[0]
        right = head.children[2]

        # left is 0
        assert left is not None and isinstance(left.value, bool) and left.value is False
        # its coiled up
        assert left.coil is not None and not any(left.children)

        # right is 1
        assert (
            right is not None and isinstance(right.value, bool) and right.value is True
        )
        # its coiled up
        assert right.coil is not None and not any(right.children)

        assert next(left.coil) is False
        assert next(right.coil) is True
        assert next(left.coil) == NamedField.D
        assert next(right.coil) == NamedField.D

        with self.assertRaises(StopIteration):
            next(left.coil)

        with self.assertRaises(StopIteration):
            next(right.coil)

    def test_overlapping_path_insert(self):

        trie = Trie.from_parsable_instructions(
            [
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [NamedField.D, LiteralField(0b1, 1), NamedField.ADDR_LO],
                    {},
                ),
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [NamedField.D, LiteralField(0b0, 1), NamedField.ADDR_HI],
                    {},
                ),
            ]
        )
        head = trie.dummy_head

        # dummy node
        assert head is not None
        assert head.children[0] is None and head.children[1] is None

        # 1
        head = head.children[2]
        assert head is not None and isinstance(head.value, bool) and head.value is True
        assert head.children[0] is None and head.children[2] is None

        # D
        head = head.children[1]
        assert head is not None and head.value is NamedField.D
        assert head.children[1] is None

        # 0/1 diverge
        left = head.children[0]
        right = head.children[2]

        # left is 0
        assert left is not None and left.value is False
        # its coiled up
        assert left.coil is not None and not any(left.children)

        # right is 1
        assert right is not None and right.value is True
        # its coiled up
        assert right.coil is not None and not any(right.children)

        assert next(left.coil) is False
        assert next(right.coil) is True
        assert next(left.coil) == NamedField.ADDR_HI
        assert next(right.coil) == NamedField.ADDR_LO

        with self.assertRaises(StopIteration):
            next(left.coil)

        with self.assertRaises(StopIteration):
            next(right.coil)

    # def test_full_unroll(self):
    #     head = insert_into_trie(
    #         None,
    #         BitModeSchemaIterator(
    #             InstructionSchema(
    #                 "move",
    #                 LiteralField(0b1, 1),
    #                 [
    #                     NamedField.D,
    #                     LiteralField(0b1, 1),
    #                     NamedField.ADDR_LO,
    #                     LiteralField(0b011, 3),
    #                 ],
    #                 {},
    #             )
    #         ),
    #     )

    #     # 1
    #     assert isinstance(head, BitNode)
    #     assert head.left is None

    #     node = head.right
    #     assert isinstance(node, LeafNode)
    #     # curled up on named field
    #     assert node.token_iter.is_next_named()

    #     head = insert_into_trie(
    #         head,
    #         BitModeSchemaIterator(
    #             InstructionSchema(
    #                 "move",
    #                 LiteralField(0b1, 1),
    #                 [
    #                     NamedField.D,
    #                     LiteralField(0b1, 1),
    #                     NamedField.ADDR_LO,
    #                     LiteralField(0b11, 2),
    #                 ],
    #                 {},
    #             )
    #         ),
    #     )
    #     assert isinstance(head, BitNode)
    #     assert head.left is None
    #     node = head.right
    #     assert isinstance(node, FieldNode)
    #     assert node.named_field == NamedField.D
    #     node = node.next
    #     assert isinstance(node, BitNode)
    #     assert node.left is None
    #     node = node.right
    #     assert isinstance(node, FieldNode)
    #     assert node.named_field == NamedField.ADDR_LO
    #     node = node.next
    #     assert isinstance(node, BitNode)
    #     assert isinstance(node.left, BitNode) and isinstance(node.right, BitNode)

    #     l = node.left
    #     r = node.right
    #     assert r.left is None and isinstance(r.right, LeafNode)
    #     r_leaf = r.right
    #     with self.assertRaises(StopIteration):
    #         next(r_leaf.token_iter)

    #     assert l.left is None and isinstance(l.right, BitNode)
    #     l = l.right
    #     assert l.left is None and isinstance(l.right, LeafNode)
    #     l_leaf = l.right
    #     with self.assertRaises(StopIteration):
    #         next(l_leaf.token_iter)

    # def test_single(self):
    #     head = insert_into_trie(
    #         None,
    #         BitModeSchemaIterator(
    #             InstructionSchema(
    #                 "move",
    #                 LiteralField(0b100011, 6),
    #                 [
    #                     NamedField.D,
    #                     LiteralField(0b1, 1),
    #                     NamedField.MOD,
    #                     LiteralField(0b0, 1),
    #                 ],
    #                 {},
    #             )
    #         ),
    #     )

    #     head = insert_into_trie(
    #         head,
    #         BitModeSchemaIterator(
    #             InstructionSchema(
    #                 "move",
    #                 LiteralField(0b1, 1),
    #                 [
    #                     NamedField.D,
    #                     LiteralField(0b1, 1),
    #                     NamedField.ADDR_LO,
    #                     LiteralField(0b11, 2),
    #                 ],
    #                 {},
    #             )
    #         ),
    #     )
