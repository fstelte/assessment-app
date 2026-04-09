"""Tests for field-level encryption helpers."""

import pytest

from scaffold.core.encryption import EncryptedBinary, EncryptedJSON, EncryptedString


def test_encrypted_string_roundtrip():
    enc = EncryptedString()
    ciphertext = enc.process_bind_param("geheim", None)
    assert ciphertext != "geheim"
    assert ciphertext.startswith("gAAAAA")
    plaintext = enc.process_result_value(ciphertext, None)
    assert plaintext == "geheim"


def test_encrypted_string_produces_unique_ciphertext():
    enc = EncryptedString()
    ct1 = enc.process_bind_param("same", None)
    ct2 = enc.process_bind_param("same", None)
    # Fernet uses a random IV, so two encryptions of the same value differ
    assert ct1 != ct2
    assert enc.process_result_value(ct1, None) == "same"
    assert enc.process_result_value(ct2, None) == "same"


def test_encrypted_json_roundtrip():
    enc = EncryptedJSON()
    data = ["code1", "code2"]
    ciphertext = enc.process_bind_param(data, None)
    assert isinstance(ciphertext, str)
    assert ciphertext.startswith("gAAAAA")
    result = enc.process_result_value(ciphertext, None)
    assert result == data


def test_encrypted_binary_roundtrip():
    enc = EncryptedBinary()
    raw = b"\x00\x01\x02\x03binary data"
    ciphertext = enc.process_bind_param(raw, None)
    assert isinstance(ciphertext, str)
    assert ciphertext.startswith("gAAAAA")
    result = enc.process_result_value(ciphertext, None)
    assert result == raw


def test_none_values_remain_none():
    for enc_cls in (EncryptedString, EncryptedJSON, EncryptedBinary):
        enc = enc_cls()
        assert enc.process_bind_param(None, None) is None
        assert enc.process_result_value(None, None) is None
