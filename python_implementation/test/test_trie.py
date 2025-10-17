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
        assert head is not None and head.value is True
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
        assert head is not None and head.value is True
        assert head.children[1] is None and head.children[2] is None
        head = head.children[0]

        # 0
        assert head is not None and head.value is False
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
        assert head is not None and head.value is True
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
    #     trie = Trie.from_parsable_instructions(
    #         [
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
    #             ),
    #             InstructionSchema(
    #                 "move",
    #                 LiteralField(0b1, 1),
    #                 [
    #                     NamedField.D,
    #                     LiteralField(0b1, 1),
    #                     NamedField.ADDR_LO,
    #                     LiteralField(0b1, 1),
    #                 ],
    #                 {},
    #             ),
    #         ]
    #     )
    #     head = trie.dummy_head

    #     # dummy node
    #     assert head is not None

    #     # 1
    #     assert head.children[0] is None and head.children[1] is None
    #     head = head.children[2]
    #     assert head is not None and head.value is True

    #     # D
    #     assert head.children[0] is None and head.children[2] is None
    #     head = head.children[1]
    #     assert head is not None and head.value is NamedField.D

    #     # 1
    #     assert head.children[0] is None and head.children[1] is None
    #     head = head.children[2]
    #     assert head is not None and head.value is True
    #     assert head.children[0] is None and head.children[2] is None

    #     # ADDR_LO
    #     assert head.children[0] is None and head.children[2] is None
    #     head = head.children[1]
    #     assert head is not None and head.value is NamedField.ADDR_LO

    #     # 1
    #     assert head.children[0] is None and head.children[1] is None
    #     head = head.children[2]
    #     assert head is not None and head.value is True

    #     # shorter inst ends here, what behavior do I want?
    #     # short_inst_last_head = head

    #     # 1
    #     assert head.children[0] is None and head.children[1] is None
    #     head = head.children[2]
    #     assert head is not None and head.value is True
    #     assert not any(head.children)

    #     assert next(head.coil) is True
    #     with self.assertRaises(StopIteration):
    #         next(head.coil)

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
