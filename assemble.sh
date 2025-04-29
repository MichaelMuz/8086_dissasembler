#!/usr/bin/env sh

for file in ./asm/disassembled/*.asm; do
    filename=$(basename "$file")
    nasm "$file" -o ./asm/assembled/"$filename"
done
