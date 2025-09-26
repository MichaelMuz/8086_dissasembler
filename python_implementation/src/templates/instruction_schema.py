from dataclasses import dataclass
import enum
import json
import logging
from pathlib import Path
import re
from typing import TypeAlias
from python_implementation.src.builder import DecodeAccumulator
from python_implementation.src.utils import BITS_PER_BYTE


@dataclass
class InstructionSchema:
    mnemonic: str
    identifier_literal: LiteralField
    fields: list[SchemaField]
    implied_values: ParsedNamedField
