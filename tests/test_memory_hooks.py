"""The hook lists in Memory: one list per kind of access, called after the
access, in list order. See docs/instrumentation-design.md, section 3."""

import pytest

from papple2.core.memory import Memory

ADDRESS = 0x0300

READ_KINDS = ["opcode", "operand", "pointer", "data", "stack", "vector"]
WRITE_KINDS = ["data", "stack"]


@pytest.mark.parametrize("kind", READ_KINDS)
def test_read_hook_sees_address_and_value(kind: str) -> None:
    memory = Memory()
    memory.load_test_data(ADDRESS, [0x42])
    seen: list[tuple[int, int]] = []
    getattr(memory, f"after_read_{kind}").append(lambda address, value: seen.append((address, value)))

    value = getattr(memory, f"read_{kind}")(ADDRESS)

    assert value == 0x42
    assert seen == [(ADDRESS, 0x42)]


@pytest.mark.parametrize("kind", WRITE_KINDS)
def test_write_hook_sees_the_old_value(kind: str) -> None:
    memory = Memory()
    memory.load_test_data(ADDRESS, [0x05])
    seen: list[tuple[int, int, int]] = []
    getattr(memory, f"after_write_{kind}").append(
        lambda address, value, old_value: seen.append((address, value, old_value))
    )

    getattr(memory, f"write_{kind}")(ADDRESS, 0x07)

    assert memory._mem[ADDRESS] == 0x07
    assert seen == [(ADDRESS, 0x07, 0x05)]


def test_hooks_run_in_list_order() -> None:
    memory = Memory()
    calls: list[str] = []
    memory.after_read_opcode.append(lambda address, value: calls.append("first"))
    memory.after_read_opcode.append(lambda address, value: calls.append("second"))

    memory.read_opcode(ADDRESS)

    assert calls == ["first", "second"]
