import pytest
from src.utils.firewall import validate_output

def test_firewall_blocks_forbidden_verbs():
    # LAW 1: Block send, submit, sign, execute, email, forward, transmit
    bad_output = "I will send this LOI to the seller now."
    is_safe, blocked_pattern = validate_output(bad_output)
    assert is_safe is False
    assert blocked_pattern == "send"

def test_firewall_allows_safe_output():
    safe_output = "This is a draft LOI for your review."
    is_safe, blocked_pattern = validate_output(safe_output)
    assert is_safe is True
    assert blocked_pattern is None

def test_firewall_blocks_sign_verb():
    bad_output = "Please sign this contract."
    is_safe, blocked_pattern = validate_output(bad_output)
    assert is_safe is False
    assert blocked_pattern == "sign"
