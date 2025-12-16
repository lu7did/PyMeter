import pytest

from pycontrol.core import PyControl, PyControlError


def test_creation_and_status():
    c = PyControl(name="test", level=2)
    assert c.status() == {"name": "test", "level": 2}


def test_set_level_bounds():
    c = PyControl(name="t", level=0)
    with pytest.raises(PyControlError):
        c.set_level(11)
    with pytest.raises(PyControlError):
        c.set_level(-1)


def test_increment_and_reset():
    c = PyControl(name="t", level=8)
    assert c.increment(1) == 9
    assert c.increment(5) == 10
    c.reset()
    assert c.level == 0
