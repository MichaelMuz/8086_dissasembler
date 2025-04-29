#!/usr/bin/env sh

python instruction_decoder.py

for file in ./asm/disassembled/*.asm; do
    filename=$(basename "$file")
    py_version=asm/my_disassembler_output/"$filename"
    echo comparing "$filename" to "$py_version"
    diff --ignore-matching-lines="^\s*;|^\s*$" "$file" "$py_version" >&2
done
