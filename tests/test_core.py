import unittest
from unittest.mock import patch
from arat.core import discover, adb_ls, adb_pull

class CoreTests(unittest.TestCase):
    def test_public_network_rejected(self):
        with self.assertRaises(ValueError):
            discover("8.8.8.0/24")

    def test_large_range_rejected(self):
        with self.assertRaises(ValueError):
            discover("192.168.0.0/16")

    @patch("arat.core.validated_device", return_value="test")
    def test_adb_scope(self, _):
        with self.assertRaises(ValueError):
            adb_ls(None, "/data/data")

    @patch("arat.core.validated_device", return_value="test")
    def test_traversal_rejected(self, _):
        with self.assertRaises(ValueError):
            adb_pull(None, "/sdcard/../data", ".")

if __name__ == "__main__":
    unittest.main()
