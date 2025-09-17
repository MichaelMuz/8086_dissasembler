from functools import cached_property
from typing import Iterator, Self, TypeAlias
from dataclasses import dataclass
import itertools
from python_implementation.src.builder import DisassembledInstruction
from python_implementation.src.schema import (
    InstructionSchema,
    LiteralField,
    NamedField,
    SchemaField,
)
from python_implementation.src.utils import get_sub_most_sig_bits
from python_implementation.src.decoder import BitIterator


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
    token_iter: Iterator[NamedField | bool]


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
        head = LeafNode(instruction, token_iter)

    elif head is None:
        # No comparison? We are a coiled branch that will unfold lazily
        head = LeafNode(instruction, itertools.chain([current_token], token_iter))

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
        once_uncoiled_head = next(head.token_iter, None)
        assert (
            once_uncoiled_head is not None
        ), "Asking to unroll fully unrolled instruction"
        if isinstance(once_uncoiled_head, NamedField):
            uncoiled_node = FieldNode(named_field=once_uncoiled_head)
        else:
            uncoiled_node = BitNode()

        head_rewind_iter = itertools.chain([once_uncoiled_head], head.token_iter)
        new_rewind_iter = itertools.chain([current_token], token_iter)

        # We are comparing the uncoiled thing against itself so we can reatach the rest of the coil
        # only adds iterations for one series of bits or one named field, then goes back to being coiled
        # only one extra iteration on top of what it does otherwise for bits (this iteration) and for fields it is just 2 because we assert it is correct and the next gives a leaf node
        head = insert_into_trie(uncoiled_node, head_rewind_iter, head.instruction)
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

    def parse(self, bit_iter: BitIterator):
        head = self.head
        vals = {}
        while head is not None and not isinstance(head, LeafNode):
            if isinstance(head, BitNode):
                if bit_iter.next_bits(1):
                    head = head.right
                else:
                    head = head.left
            elif isinstance(head, FieldNode):
                vals[head.named_field] = bit_iter.next_bits(head.named_field.bit_width)
                head = head.next

        assert head is not None, "Invalid Instruction"
        i


class DecodeAccumulator:
    ALWAYS_NEEDED_FIELDS = {
        # if we see this in an instruction schema, we must always parse it
        NamedField.D,
        NamedField.W,
        NamedField.S,
        NamedField.MOD,
        NamedField.REG,
        NamedField.RM,
        NamedField.DATA,
    }

    def __init__(self, instruction_schema: InstructionSchema):
        self.instruction_schema = instruction_schema
        self.parsed_fields = {
            named_field: implied_value
            for named_field, implied_value in instruction_schema.implied_values.items()
        }

        self.implied_values = set(self.parsed_fields.keys())

    def with_field(self, schema_field: SchemaField, field_value: int):
        if isinstance(schema_field, LiteralField):
            logging.debug(f"{schema_field = }, {field_value = }")
            assert schema_field.literal_value == field_value
        elif isinstance(schema_field, NamedField):
            self.parsed_fields[schema_field] = field_value
        return self

    def is_needed(self, schema_field: SchemaField) -> bool:
        if isinstance(schema_field, LiteralField):
            return True
        assert (
            schema_field not in self.implied_values
        ), f"Asking if {schema_field} is required but its value is already implied"

        if schema_field in self.ALWAYS_NEEDED_FIELDS:
            return True
        elif schema_field is NamedField.DATA_IF_W1:
            return bool(self.parsed_fields[NamedField.W])
        elif schema_field is NamedField.DATA_IF_SW_01:
            return self.sign_extension == 0 and self.word
        elif schema_field in (NamedField.DISP_LO, NamedField.DISP_HI):
            return (self.mode.type is Mode.Type.WORD_DISPLACEMENT_MODE) or (
                self.mode.type is Mode.Type.BYTE_DISPLACEMENT_MODE
                and (schema_field is NamedField.DISP_LO)
            )
        else:
            raise ValueError(f"don't know how to check if {schema_field} is needed")

    @cached_property
    def mode(self) -> Mode:
        """This one is special because it is used in checking if a field is needed"""
        mod_value = self.parsed_fields[NamedField.MOD]
        rm_value = self.parsed_fields.get(NamedField.RM)
        mode = Mode(mod_value, rm_value)
        logging.debug(f"locked in mode as {mode = }")
        return mode

    @cached_property
    def word(self):
        return bool(self.parsed_fields[NamedField.W])

    @cached_property
    def direction(self):
        return bool(self.parsed_fields[NamedField.D])

    @cached_property
    def sign_extension(self):
        return bool(self.parsed_fields[NamedField.S])

    @cached_property
    def displacement(self):
        disp = None
        if NamedField.DISP_LO in self.parsed_fields:
            disp = combine_bytes(
                self.parsed_fields[NamedField.DISP_LO],
                self.parsed_fields.get(NamedField.DISP_HI),
            )
            return as_signed_int(disp)

    @cached_property
    def data_operand(self):
        data_operand = None
        if NamedField.DATA in self.parsed_fields:
            data_operand = ImmediateOperand(
                value=combine_bytes(
                    self.parsed_fields[NamedField.DATA],
                    self.parsed_fields.get(NamedField.DATA_IF_W1),
                ),
                word=self.word,
            )
        return data_operand

    @cached_property
    def register_operand(self):
        reg_operand = None
        if NamedField.REG in self.parsed_fields:
            reg_operand = RegisterOperand(
                register_index=self.parsed_fields[NamedField.REG], word=self.word
            )
        return reg_operand

    @cached_property
    def rm_operand(self):
        rm_operand = None
        if NamedField.RM in self.parsed_fields:
            reg_or_mem_base = self.parsed_fields[NamedField.RM]
            if self.mode.type is Mode.Type.REGISTER_MODE:
                rm_operand = RegisterOperand(
                    register_index=reg_or_mem_base, word=self.word
                )
            else:
                rm_operand = MemoryOperand(
                    memory_base=(
                        None if self.mode.direct_memory_index else reg_or_mem_base
                    ),
                    displacement=self.displacement or 0,
                )
        return rm_operand

    def build(self) -> DisassembledInstruction:
        assert not (
            self.data_operand and self.register_operand and self.rm_operand
        ), "Too many operands"

        if self.data_operand is not None:
            operands = [self.data_operand, self.register_operand or self.rm_operand]
        else:
            operands = [self.register_operand, self.rm_operand]

        if self.direction:
            operands.reverse()

        assert None not in operands, "Cannot have null source or dest"
        source, dest = operands

        return DisassembledInstruction(
            mnemonic=self.instruction_schema.mnemonic, source=source, dest=dest
        )
