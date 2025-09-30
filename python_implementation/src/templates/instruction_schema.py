from dataclasses import dataclass

from python_implementation.src.templates.schema_field import (
    LiteralField,
    ParsedNamedField,
    SchemaField,
)


@dataclass
class InstructionSchema:
    mnemonic: str
    identifier_literal: LiteralField
    fields: list[SchemaField]
    implied_values: ParsedNamedField
