import unittest

from python_implementation.src.utils import (
    as_signed_int,
    combine_bytes,
    get_sub_bits,
    get_sub_most_sig_bits,
)


class TestAsSignedInt(unittest.TestCase):
    def test_as_signed_int(self):
        # Test zero
        self.assertEqual(as_signed_int(0), 0)

        # Test 8-bit cases
        self.assertEqual(as_signed_int(127), 127)  # Max positive 8-bit
        self.assertEqual(as_signed_int(128), -128)  # Min negative 8-bit
        self.assertEqual(as_signed_int(255), -1)  # Max unsigned 8-bit

        # Test 16-bit cases
        self.assertEqual(as_signed_int(256), 256)  # Needs 16-bit
        self.assertEqual(as_signed_int(32767), 32767)  # Max positive 16-bit
        self.assertEqual(as_signed_int(32768), -32768)  # Min negative 16-bit
        self.assertEqual(as_signed_int(65535), -1)  # Max unsigned 16-bit

        # Test 32-bit cases
        self.assertEqual(as_signed_int(65536), 65536)  # Needs 32-bit
        self.assertEqual(as_signed_int(2147483647), 2147483647)  # Max positive 32-bit
        self.assertEqual(as_signed_int(2147483648), -2147483648)  # Min negative 32-bit

        self.assertEqual(as_signed_int(300), 300)  # 9-bit value, positive in 16-bit
        self.assertEqual(
            as_signed_int(100000), 100000
        )  # 17-bit value, positive in 32-bit


class TestGetSubBits(unittest.TestCase):
    def test_get_sub_bits_basic(self):
        # Get 3 bits starting at bit 2
        self.assertEqual(get_sub_bits(0b11010110, 2, 3), 0b101)

    def test_get_sub_bits_from_start(self):
        # Get lowest 4 bits
        self.assertEqual(get_sub_bits(0b11010110, 0, 4), 0b0110)

    def test_get_sub_bits_single_bit(self):
        # Get bit at position 5 from the right
        self.assertEqual(get_sub_bits(0b11010110, 5, 1), 0)
        self.assertEqual(get_sub_bits(0b11010110, 4, 1), 1)

    def test_get_sub_bits_all_bits(self):
        # Get all 8 bits
        self.assertEqual(get_sub_bits(0b11010110, 0, 8), 0b11010110)

    def test_get_sub_bits_high_bits(self):
        # Get top 3 bits
        self.assertEqual(get_sub_bits(0b11010110, 5, 3), 0b110)


class TestGetSubMostSigBits(unittest.TestCase):
    def test_get_sub_most_sig_bits_from_top(self):
        # get 3 bits starting from MSB
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 0, 3), 0b110)

    def test_get_sub_most_sig_bits_middle(self):
        # get 3 bits starting from bit index 2 from top
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 2, 3), 0b010)

    def test_get_sub_most_sig_bits_single_bit(self):
        # Get the MSB
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 0, 1), 1)
        # Get second bit from top
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 1, 1), 1)
        # Get third bit from top
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 2, 1), 0)

    def test_get_sub_most_sig_bits_last_bits(self):
        # get last 2 bits
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 6, 2), 0b10)

    def test_get_sub_most_sig_bits_all_bits(self):
        # Get all 8 bits
        self.assertEqual(get_sub_most_sig_bits(0b11010110, 0, 8), 0b11010110)


class TestCombineBytes(unittest.TestCase):
    def test_combine_bytes_with_high(self):
        # Combine 0x34 (low) and 0x12 (high) = 0x1234 = 4660
        self.assertEqual(combine_bytes(0x34, 0x12), 0x1234)

    def test_combine_bytes_no_high(self):
        # Just return the low byte
        self.assertEqual(combine_bytes(0x34, None), 0x34)

    def test_combine_bytes_zero_high(self):
        # High byte is 0
        self.assertEqual(combine_bytes(0xFF, 0x00), 0x00FF)

    def test_combine_bytes_zero_low(self):
        # Low byte is 0
        self.assertEqual(combine_bytes(0x00, 0xFF), 0xFF00)

    def test_combine_bytes_both_zero(self):
        self.assertEqual(combine_bytes(0x00, 0x00), 0x0000)

    def test_combine_bytes_max_values(self):
        # Both bytes at max (0xFF)
        self.assertEqual(combine_bytes(0xFF, 0xFF), 0xFFFF)

    def test_combine_bytes_real_world(self):
        # Simulating displacement: -37 as two's complement in 16-bit
        # -37 = 0xFFDB = high:0xFF, low:0xDB
        self.assertEqual(combine_bytes(0xDB, 0xFF), 0xFFDB)
