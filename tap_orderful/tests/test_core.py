"""Tests standard tap features using the built-in SDK tests library."""

import datetime
import json
import os

import pytest
from hotglue_singer_sdk.testing import get_standard_tap_tests

from tap_orderful.tap import TapOrderful

_secrets_config = os.path.join(os.path.dirname(__file__), "../../.secrets/config.json")


@pytest.fixture
def sample_config():
    if not os.path.exists(_secrets_config):
        pytest.skip("Secrets file not found; skipping integration tests.")
    with open(_secrets_config) as f:
        config = json.load(f)
    return {
        **config,
        "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def test_standard_tap_tests(sample_config):
    """Run standard tap tests from the SDK."""
    tests = get_standard_tap_tests(TapOrderful, config=sample_config)
    for test in tests:
        test()
