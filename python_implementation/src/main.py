import os

from python_implementation.src.base.config_loader import (
    get_parsable_instructions_from_config,
)
from python_implementation.src.parser import BitIterator, parse_binary
from python_implementation.src.trie import Trie


def main():
    parsable_instructions = get_parsable_instructions_from_config()
    trie = Trie.from_parsable_instructions(parsable_instructions)
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    files_to_do = ["single_register_mov", "many_register_mov", "listing_0039_more_movs"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        with open(full_input_file_path, "rb") as file:
            file_contents: bytes = file.read()
        disasm = parse_binary(trie, BitIterator(file_contents))
        full_output_file_path = os.path.join(output_directory, file_name + ".asm")
        with open(full_output_file_path, "w") as f:
            f.write(str(disasm))


if __name__ == "__main__":
    main()
