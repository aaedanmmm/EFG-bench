"""Interpreter unit tests. StubRobot is a mock capability; no SDK runs here."""
from pathlib import Path
import pytest
from src.runtime import ProtocolError, Runtime


class StubRobot:
    scenario = {"api_level": "2.19"}


def run(code):
    return Runtime(StubRobot()).run(code)


@pytest.mark.parametrize("code,error", [
    ('import os\nmetadata={"apiLevel":"2.19"}\ndef run(p): pass', "Unsupported Python syntax"),
    ('from os import system\nmetadata={"apiLevel":"2.19"}\ndef run(p): pass', "Only 'from opentrons"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    p.__class__()', "Private attributes"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    open("/tmp/ot2-escape-marker", "w")', "Builtin unavailable"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    for x in range(1000000): pass', "Sequence exceeds"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    while True: pass', "Unsupported Python syntax"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    p.comment = 1', "Only variable assignment"),
    ('metadata={"apiLevel":"2.19"}\n@print\ndef run(p): pass', "Expected undecorated"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    x = [a for a in range(10)]', "Unsupported Python syntax"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    x = 1000000 * 1000000', "Expected a finite number"),
    ('metadata={"apiLevel":"2.19"}\ndef run(p):\n    x = "a" * 1000000', "Expected a finite number"),
])
def test_rejects_unsupported_code(code, error):
    with pytest.raises(ProtocolError, match=error):
        run(code)


def test_no_filesystem_side_effect():
    marker = Path("/tmp/ot2-escape-marker")
    existed = marker.exists()
    with pytest.raises(ProtocolError):
        run('metadata={"apiLevel":"2.19"}\ndef run(p):\n    open("/tmp/ot2-escape-marker", "w")')
    assert marker.exists() == existed


def test_step_budget():
    with pytest.raises(ProtocolError, match="step budget"):
        run('metadata={"apiLevel":"2.19"}\ndef run(p):\n    for a in range(384):\n        for b in range(384):\n            x = 1')
