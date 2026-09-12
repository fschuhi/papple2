import pytest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


@pytest.fixture
def memory():
    return Memory()


@pytest.fixture
def cpu(memory):
    return CPU(memory, None)
