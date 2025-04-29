#!/usr/bin/env sh

for file in ./asm/disassembled/*.asm; do
    filename=$(basename "${file%.*}")
    out_file=./asm/assembled/"$filename"
    nasm "$file" -o "$out_file"
done
