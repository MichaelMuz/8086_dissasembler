#!/usr/bin/env sh

for file in ./asm/disassembled/*.asm; do
    filename=$(basename "${file%.*}")
    echo file: $file
    echo filename: $filename
    out_file=./asm/assembled/"$filename"
    echo $out_file
    nasm "$file" -o ./asm/assembled/"$filename"
done
