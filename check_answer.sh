#!/usr/bin/env bash

filter_comments_and_blanks() {
    grep -v -e "^\s*;" -e "^\s*$" "$1"
}

python instruction_decoder.py

for file in ./asm/disassembled/*.asm; do
    filename=$(basename "$file")
    py_version=asm/my_disassembler_output/"$filename"
    diff <(filter_comments_and_blanks "$file") <(filter_comments_and_blanks "$py_version")
done
