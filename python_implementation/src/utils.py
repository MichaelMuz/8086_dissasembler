import math


BITS_PER_BYTE = 8


def get_sub_bits(to_ind: int, start_ind: int, num_bits: int):
    r_shifted = to_ind >> start_ind
    mask = (1 << num_bits) - 1
    return r_shifted & mask


def get_sub_most_sig_bits(
    to_ind: int, msb_start_ind: int, num_bits: int, total_bits=BITS_PER_BYTE
):
    max_ind = total_bits - 1
    end_ind = max_ind - msb_start_ind
    start_ind = end_ind - num_bits + 1  # includes start
    return get_sub_bits(to_ind, start_ind, num_bits)


def combine_bytes(low: int, high: int | None) -> int:
    if high is not None:
        return (high << 8) + low
    return low


def as_signed_int(unsigned: int) -> int:
    if unsigned == 0:
        return unsigned
    byte_width = math.ceil(unsigned.bit_length() / BITS_PER_BYTE)
    bytes_needed = 1 << (byte_width - 1).bit_length()  # Next power of 2
    highest_bit_mask = 1 << (bytes_needed * BITS_PER_BYTE)
    max_signed = highest_bit_mask >> 1
    if unsigned >= max_signed:
        return unsigned - highest_bit_mask

    return unsigned
