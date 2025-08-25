import os

from python_implementation.src.decoder import disassemble_binary_to_string
from python_implementation.src.schema import get_parsable_instructions_from_config


def main():
    parsable_instructions = get_parsable_instructions_from_config()
    input_directory = "./asm/assembled/"
    output_directory = "./asm/my_disassembler_output/"
    files_to_do = ["single_register_mov", "many_register_mov", "listing_0039_more_movs"]
    for file_name in files_to_do:
        full_input_file_path = os.path.join(input_directory, file_name)
        with open(full_input_file_path, "rb") as file:
            file_contents: bytes = file.read()
        disassembled = disassemble_binary_to_string(
            parsable_instructions, file_contents
        )
        full_output_file_path = os.path.join(output_directory, file_name + ".asm")
        with open(full_output_file_path, "w") as f:
            f.write(disassembled)


if __name__ == "__main__":
    main()
