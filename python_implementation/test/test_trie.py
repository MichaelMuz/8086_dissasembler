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

        assert head.children[0] is None and head.named is None
        head = head.right

        # 1
        assert head is not None and head.value is True
        # its coiled up
        assert head.coil is not None and not any(head.children)

    def test_short_overlapping_path_insert(self):
        trie = Trie.from_parsable_instructions(
            [
                InstructionSchema("move", LiteralField(0b101, 3), [NamedField.D], {}),
                InstructionSchema("move", LiteralField(0b100, 3), [NamedField.D], {}),
            ]
        )
        head = trie.dummy_head

        assert head is not None
        assert head.left is None and head.named is None
        head = head.right

        # 1
        assert head is not None and head.value is True
        assert head.named is None and head.right is None
        head = head.left

        # 0
        assert head is not None and head.value is False
        assert head.named is None

        # 0/1 diverge
        left = head.left
        right = head.right

        # left is 0
        assert left is not None and left.value is False
        # its coiled up
        assert left.coil is not None and not any(left.children)

        # right is 1
        assert right is not None and right.value is True
        # its coiled up
        assert right.coil is not None and not any(right.children)

        lc, rc = left.get_rest_of_coil(), right.get_rest_of_coil()

        assert next(lc) == NamedField.D
        assert next(rc) == NamedField.D

        with self.assertRaises(StopIteration):
            next(lc)

        with self.assertRaises(StopIteration):
            next(rc)

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
        assert head.left is None and head.named is None

        # 1
        head = head.right
        assert head is not None and head.value is True
        assert head.left is None and head.right is None

        # D
        head = head.named
        assert head is not None and head.value is NamedField.D
        assert head.named is None

        # 0/1 diverge
        left = head.left
        right = head.right

        # left is 0
        assert left is not None and left.value is False
        # its coiled up
        assert left.coil is not None and not any(left.children)

        # right is 1
        assert right is not None and right.value is True
        # its coiled up
        assert right.coil is not None and not any(right.children)

        lc, rc = left.get_rest_of_coil(), right.get_rest_of_coil()
        assert next(lc) == NamedField.ADDR_HI
        assert next(rc) == NamedField.ADDR_LO

        with self.assertRaises(StopIteration):
            next(lc)

        with self.assertRaises(StopIteration):
            next(rc)

    def test_full_unroll(self):
        trie = Trie.from_parsable_instructions(
            [
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
                ),
                InstructionSchema(
                    "move",
                    LiteralField(0b1, 1),
                    [
                        NamedField.D,
                        LiteralField(0b1, 1),
                        NamedField.ADDR_LO,
                        LiteralField(0b10, 2),
                    ],
                    {},
                ),
            ]
        )
        head = trie.dummy_head

        # dummy node
        assert head is not None

        # 1
        assert head.left is None and head.named is None
        head = head.right
        assert head is not None and head.value is True

        # D
        assert head.left is None and head.right is None
        head = head.named
        assert head is not None and head.value is NamedField.D

        # 1
        assert head.left is None and head.named is None
        head = head.right
        assert head is not None and head.value is True
        assert head.left is None and head.right is None

        # ADDR_LO
        assert head.left is None and head.right is None
        head = head.named
        assert head is not None and head.value is NamedField.ADDR_LO

        # 1
        assert head.left is None and head.named is None
        head = head.right
        assert head is not None and head.value is True

        # 0/1 diverge
        left = head.left
        right = head.right

        # left is 0
        assert left is not None and left.value is False
        # its coiled up
        assert left.coil is not None and not any(left.children)

        # right is 1
        assert right is not None and right.value is True
        # its coiled up
        assert right.coil is not None and not any(right.children)

        # their iterators are both spent
        with self.assertRaises(StopIteration):
            next(left.get_rest_of_coil())

        with self.assertRaises(StopIteration):
            next(right.get_rest_of_coil())

    def test_single(self):
        Trie.from_parsable_instructions(
            [
                InstructionSchema(
                    "move",
                    LiteralField(0b100011, 6),
                    [
                        NamedField.D,
                        LiteralField(0b1, 1),
                        NamedField.MOD,
                        LiteralField(0b0, 1),
                    ],
                    {},
                ),
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
                ),
                InstructionSchema(
                    "loopnz",
                    LiteralField(0b11100000, 8),
                    [
                        NamedField.IP_INC8,
                    ],
                    {},
                ),
                InstructionSchema(
                    "jcxz",
                    LiteralField(0b11100011, 8),
                    [
                        NamedField.IP_INC8,
                    ],
                    {},
                ),
            ]
        )
