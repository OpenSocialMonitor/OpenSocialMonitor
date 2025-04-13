"""
Database interfaces for OpenSocialMonitor

This module provides functions for storing and retrieving
information about monitored accounts and detected bots.
"""

from .manager import DatabaseManager

# Create a singleton instance for convenient access
db = DatabaseManager()