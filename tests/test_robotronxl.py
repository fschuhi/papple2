"""
Tests for RobotronXl.py's functions as they get converted from xlwings'
@xw.func to PyXLL's @xl_func.

These are called directly as plain Python functions -- outside of Excel,
PyXLL's @xl_func decorator is a passthrough, so no Excel/PyXLL runtime is
needed to exercise them here (see the pyxll docs: "when called from
outside of Excel [...] accept proper python types when called from other
python code").

Two things are deliberately NOT covered here:
- the @xl_func("...") signature strings themselves (argument/return type
  declarations) -- those only matter once Excel is actually doing the
  type coercion, which needs a real Excel/PyXLL round trip to verify;
- what the functions actually return once Robotron is running for real
  -- the disassembly/annotation/access-log content depends on domain
  knowledge that isn't captured anywhere right now (see chat), so this
  only checks "doesn't raise, returns the right rough shape".
"""

import pytest

import examples.Robotron.RobotronXl as robotron_xl


# Functions that only need a running workbench (no memlog dialog):
# (the function itself, a plausible set of arguments to call it with, the
# type its result should have once a real workbench exists).
FUNCTIONS = [
    (robotron_xl.get_disassembly, (), list),
    (robotron_xl.get_memory_map, (), list),
    (robotron_xl.get_annotations, (), list),
    (robotron_xl.max_cycles, (), int),
    (robotron_xl.count_mem_accesses, (), int),
    (robotron_xl.get_mem_access_counts, (), list),
    (robotron_xl.get_mem_access_log, (0, 999999), list),
    (robotron_xl.get_screen_read_counts, (0, 999999), list),
    (robotron_xl.get_screen_write_counts, (0, 999999, False), list),
    (robotron_xl.get_access_colors, ('reads', 0, 0, True, False), list),
    (robotron_xl.get_bytes, (0, 10), list),
]
FUNCTION_IDS = [func.__name__ for func, _, _ in FUNCTIONS]

# Functions that additionally need workbench.memlog_dialog to already exist
# (create_memlog_dialog itself is tested separately below, since its result
# depends on whether a dialog already exists -- it doesn't fit this shape).
# find_pc_forward/backward reliably return "not found" here: with no
# instructions ever run, memory_states is empty, so the search loop in both
# never finds a match, regardless of the pc searched for.
MEMLOG_FUNCTIONS = [
    (robotron_xl.send_memlog_dialog_event, ('down_key',), str),
    (robotron_xl.get_memlog_lines, (), list),
    (robotron_xl.get_memlog_cursor_pos, (), int),
    (robotron_xl.find_pc_forward, (0x1234,), str),
    (robotron_xl.find_pc_backward, (0x1234,), str),
]
MEMLOG_FUNCTION_IDS = [func.__name__ for func, _, _ in MEMLOG_FUNCTIONS]

# The three ndim=2/transpose functions: each takes a forced 2D list of
# addresses (mirroring PyXLL's var[][] argument type) and returns a flat
# list, one entry per address. get_attribute_from_info's own '?' marker
# (used when memory_map has no OpInfo recorded for an address) is what we
# expect here, since running_workbench never executes any instructions.
ARRAY_FUNCTIONS = [
    robotron_xl.get_touch_count,
    robotron_xl.get_first_cycles,
    robotron_xl.get_last_cycles,
]
ARRAY_FUNCTION_IDS = [func.__name__ for func in ARRAY_FUNCTIONS]

# For the guard-path test only: every function above, plus create_memlog_dialog
# itself (it only calls validate_workbench(), not validate_memlog_dialog(), so
# it belongs in the guard check but not in the memlog smoke-test group), plus
# the three array functions with a single dummy address each.
GUARD_PATH_FUNCTIONS = (
    FUNCTIONS
    + MEMLOG_FUNCTIONS
    + [(robotron_xl.create_memlog_dialog, (3,), str)]
    + [(func, ([['$2dfd']],), list) for func in ARRAY_FUNCTIONS]
)
GUARD_PATH_IDS = [func.__name__ for func, _, _ in GUARD_PATH_FUNCTIONS]


@pytest.fixture(scope="module")
def running_workbench(tmp_path_factory):
    """Boots a real, headless Workbench once for the whole module (not once
    per parametrized case -- that would mean re-loading Robotron repeatedly).
    No event loop, no actual Robotron execution: we're only testing that the
    functions run and return the right shape, not what they report."""
    data_dir = "data"
    trace_dir = str(tmp_path_factory.mktemp("trace"))
    robotron_xl.start_emulator(
        data_dir, trace_dir, show_window=False, time_machine=False, mem_access=True
    )
    robotron_xl.continue_robotron(
        event_loop=False, simulate_execution=False, determine_stretches=False
    )


@pytest.fixture(scope="module")
def memlog_dialog_ready(running_workbench):
    """Builds on running_workbench by also creating workbench.memlog_dialog,
    which send_memlog_dialog_event/get_memlog_lines/get_memlog_cursor_pos/
    find_pc_forward/find_pc_backward all assume already exists."""
    robotron_xl.create_memlog_dialog(3)


@pytest.mark.parametrize(
    "func, args, expected_type", GUARD_PATH_FUNCTIONS, ids=GUARD_PATH_IDS
)
def test_function_reports_missing_workbench_before_start_emulator(
    func, args, expected_type, monkeypatch
):
    """validate_workbench()'s guard path, exercised via ExcelContext: calling
    any of these before start_emulator() has run must not raise, but come
    back as the Excel-style error string ExcelContext produces -- regardless
    of what arguments are passed."""
    monkeypatch.setattr(robotron_xl, "workbench", None)
    assert func(*args) == "#cannot find the workbench"


@pytest.mark.parametrize("func, args, expected_type", FUNCTIONS, ids=FUNCTION_IDS)
def test_function_returns_expected_type_once_workbench_exists(
    func, args, expected_type, running_workbench
):
    """Smoke test: once a real workbench exists, each function should run to
    completion and return the rough shape we expect, whatever the content
    turns out to be."""
    assert isinstance(func(*args), expected_type)


@pytest.mark.parametrize(
    "func, args, expected_type", MEMLOG_FUNCTIONS, ids=MEMLOG_FUNCTION_IDS
)
def test_memlog_function_returns_expected_type_once_dialog_exists(
    func, args, expected_type, memlog_dialog_ready
):
    """Same idea as the smoke test above, for the five functions that also
    need workbench.memlog_dialog to exist first."""
    assert isinstance(func(*args), expected_type)


def test_find_pc_forward_and_backward_report_not_found_with_no_recorded_states(
    memlog_dialog_ready,
):
    """With mem_access enabled but nothing ever executed, memory_states is
    empty, so both search directions must come back "not found" -- not an
    error, and not a false "found" for whatever pc happens to be passed."""
    assert robotron_xl.find_pc_forward(0x1234) == "not found"
    assert robotron_xl.find_pc_backward(0x1234) == "not found"


def test_create_memlog_dialog_creates_then_reuses(running_workbench):
    """create_memlog_dialog's own two-state behavior: the first call (for a
    given window_lines) creates a new dialog, a later call with the same
    window_lines reuses it instead of creating a second one.

    Uses window_lines=5, deliberately different from memlog_dialog_ready's 3:
    workbench is a module-level global shared with every other test in this
    file, so this stays correct regardless of whether memlog_dialog_ready
    has already run (and left a window_lines=3 dialog behind) or not."""
    assert robotron_xl.create_memlog_dialog(5) == "ok (created)"
    assert robotron_xl.create_memlog_dialog(5) == "ok (reused)"


@pytest.mark.parametrize("func", ARRAY_FUNCTIONS, ids=ARRAY_FUNCTION_IDS)
def test_array_function_returns_unknown_marker_for_untouched_address(
    func, running_workbench
):
    """With nothing ever executed, memory_map has no OpInfo recorded for any
    address, so each of these three should come back with the forced 2D
    input flattened to a 1-item list containing get_attribute_from_info's
    own '?' marker for "no info at this address"."""
    assert func([['$2dfd']]) == ['?']
