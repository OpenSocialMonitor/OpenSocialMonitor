"""
Test the Instagram platform connector
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.platforms.instagram import InstagramPlatform

class TestInstagramPlatform(unittest.TestCase):
    """Test cases for the Instagram platform connector"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.platform = InstagramPlatform()
    
    def test_initialization(self):
        """Test that the Instagram platform initializes correctly"""
        self.assertEqual(self.platform.name, "Instagram")
        self.assertFalse(self.platform.is_logged_in)
    
    def test_get_platform_name(self):
        """Test that the platform name is correct"""
        self.assertEqual(self.platform.name, "Instagram")
    
    # Skip login test by default to avoid API calls during automated testing
    @unittest.skip("Skipping login test to avoid API calls")
    def test_login(self):
        """Test login functionality (skipped by default)"""
        success = self.platform.login()
        self.assertTrue(success)
        self.assertTrue(self.platform.is_logged_in)

if __name__ == '__main__':
    unittest.main()