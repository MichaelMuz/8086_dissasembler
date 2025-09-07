import unittest

from python_implementation.src.utils import as_signed_int


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
