"""The hook lists in Memory: one list per kind of access, called after the
access, in list order. See docs/instrumentation-design.md, section 3.

One test per method, written out on purpose: the nine methods are near
copies of each other, and each test checks that its method calls its own
list with the right values."""

from papple2.core.memory import Memory


# reads: a read hook gets (address, value)


def test_read_opcode_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_opcode.append(lambda address, value: seen.append((address, value)))

    assert memory.read_opcode(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_operand_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_operand.append(lambda address, value: seen.append((address, value)))

    assert memory.read_operand(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_pointer_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_pointer.append(lambda address, value: seen.append((address, value)))

    assert memory.read_pointer(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_data_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_data.append(lambda address, value: seen.append((address, value)))

    assert memory.read_data(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_immediate_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_immediate.append(lambda address, value: seen.append((address, value)))

    assert memory.read_immediate(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_stack_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_stack.append(lambda address, value: seen.append((address, value)))

    assert memory.read_stack(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


def test_read_vector_calls_its_hooks() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x42])
    seen = []
    memory.after_read_vector.append(lambda address, value: seen.append((address, value)))

    assert memory.read_vector(0x0300) == 0x42
    assert seen == [(0x0300, 0x42)]


# writes: a write hook gets (address, value, old_value)


def test_write_data_calls_its_hooks_with_the_old_value() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x05])
    seen = []
    memory.after_write_data.append(lambda address, value, old_value: seen.append((address, value, old_value)))

    memory.write_data(0x0300, 0x07)

    assert memory._mem[0x0300] == 0x07
    assert seen == [(0x0300, 0x07, 0x05)]


def test_write_stack_calls_its_hooks_with_the_old_value() -> None:
    memory = Memory()
    memory.load_test_data(0x0300, [0x05])
    seen = []
    memory.after_write_stack.append(lambda address, value, old_value: seen.append((address, value, old_value)))

    memory.write_stack(0x0300, 0x07)

    assert memory._mem[0x0300] == 0x07
    assert seen == [(0x0300, 0x07, 0x05)]


# order: hooks in one list run in the order they were added


def test_hooks_run_in_list_order() -> None:
    memory = Memory()
    calls = []
    memory.after_read_opcode.append(lambda address, value: calls.append("first"))
    memory.after_read_opcode.append(lambda address, value: calls.append("second"))

    memory.read_opcode(0x0300)

    assert calls == ["first", "second"]
