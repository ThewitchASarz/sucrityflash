"""
Hashing utilities for content integrity and evidence chaining.
"""
import hashlib
import json
from typing import Any


def sha256_hash(data: str) -> str:
    """
    Generate SHA-256 hash of string data.

    Args:
        data: String data to hash

    Returns:
        str: Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_hash_dict(data: dict) -> str:
    """
    Generate SHA-256 hash of dictionary (deterministic JSON serialization).

    Args:
        data: Dictionary to hash

    Returns:
        str: Hex-encoded SHA-256 hash
    """
    # Deterministic JSON serialization (sorted keys, no whitespace)
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return sha256_hash(json_str)


def verify_hash(data: str, expected_hash: str) -> bool:
    """
    Verify data matches expected hash.

    Args:
        data: Data to verify
        expected_hash: Expected SHA-256 hash

    Returns:
        bool: True if hash matches
    """
    actual_hash = sha256_hash(data)
    return actual_hash == expected_hash


def verify_dict_hash(data: dict, expected_hash: str) -> bool:
    """
    Verify dictionary matches expected hash.

    Args:
        data: Dictionary to verify
        expected_hash: Expected SHA-256 hash

    Returns:
        bool: True if hash matches
    """
    actual_hash = sha256_hash_dict(data)
    return actual_hash == expected_hash
