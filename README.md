# 8086 Disassembler

## What is this?

This project is based on [Casey Muratori's Performance Aware Programming completionist disassembler challenge](https://github.com/cmuratori/computer_enhance/tree/main).

### Primary goal

Create a tool that will turn a binary targeting the [8086](https://en.wikipedia.org/wiki/Intel_8086) into 16 bit x86 assembly and cover as many of the [documented instructions](https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf#page=164) as possible.

### Secondary goals

Learn:
- Zig
- More about CPU architecture
- How to measure and improve performance

Generally want to combine these and make sure that the tool not only works, but also runs fast.

## Usage

The disassembler has no dependencies to run aside from Zig, but because the input is binary it is hard to create yourself.
Recommended to use [`nasm`](https://www.nasm.us/) and `xxd` to create inputs.

### Running

Let's try it on this small example assembly program
```asm
bits 16
mov ax, 20
push ax
xor ax, ax
```

NASM assembles it to `b81400 50 31c0`
```sh
nasm -o /dev/stdout /dev/stdin <<'EOF' | xxd -p
bits 16
mov ax, 20
push ax
xor ax, ax
EOF
```

Now we can use the disassembler to recover the original program.
```sh
$ echo 'b81400 50 31c0' | xxd -r -p | zig build run -- - -
bits 16
mov ax, 20
push ax
xor ax, ax
```

### Testing

Run unit tests. No dependencies.
``` sh
zig build unit
```

Run integration tests. These require NASM because we test round trips, see [Round trip testing](#round-trip-testing)
``` sh
zig build integration
```

Run all tests
``` sh
zig build test
```

Add `-Dtest-filter="<match string>"` to the end of any of these to filter down to only tests whose name matches the supplied `match string`

## How it works

Quick list of interesting design decisions made while programming this

### Instruction table

The instruction table in [`encodings.zig`](src/lexer/encodings.zig) is written to mirror the instruction manual's [documented instructions](https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf#page=164) and parsed at compile time using Zig's comptime.

- **Generic**: shorthand instructions get their implied values filled in where it makes sense semantically to keep code generic and avoid special casing.
- **Extensible**: code handles instructions generically and new encodings can be added as configuration leaving an extensible core.
- **Fast**: compile time configuration means the program doesn't need to waste time parsing the configuration on startup.

### Round trip testing

Because our tool turns binary into human readable text there are many formatting quirks. For example, with 8 bit immediate data the tool has no way of knowing if you wrote a positive or negative number. 
It is up to the program at runtime to use the bits as two's complement or not. Ex: `10101010` is either `170` or `-86` depending on how the bits are interpreted. We output the positive version.
For this reason comparing the input string to `nasm` and the output string of the disassembler is too flimsy. We instead put our output back into nasm and assert the binary resulting from our assembly is correct.

`text -(assemble)> binary -(disassemble)> text -(assemble)> binary` and compare the two `binary` to be sure our human readable code compiles the same.

### Zero heap allocation

The main executable should purely use fixed-size stack allocations at runtime to avoid paying for extra allocations and syscalls.
We can do this because most instructions can be processed and output immediately so we can incrementally read and stream output as each line is processed.
One time this gets a bit muddy is when you want to output labels for jumps because we may be on instruction 100 so we have processed 1-99 already but we find out the label needs to be before instruction 50.
This is still possible because direct (relative) jumps have a limited range they can jump to, at most the 64KB of a segment, so we just need to allocate a window that large and stream output once it falls out of the window. 

## Current/future state

- Most instructions but not all are done, progress can be seen in how many [integration tests](test/integration.zig) are commented out.
- Currently jump instructions don't have labels, they just use the relative jump syntax in our output `jmp $ - 7` rather than placing a `my_label:` 7 bytes above and having `jmp my_label` instead.

