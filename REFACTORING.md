# REFACTORING: `shell.py` to `Workbench` Migration

## 1. Goal
Eliminate the side-effect-heavy global state in `papple2.workbench.shell` by encapsulating it in an internal `Workbench` object. 

The interactive CLI contract (the top-level commands used at the IPython prompt and in the `lr_*` recipes) remains strictly unchanged. The commands become thin wrappers that delegate to a single `Workbench` instance.

## 2. Target Architecture
*   **`src/papple2/workbench/workbench.py`:** A new module housing the `Workbench` class. This class owns the `reports_folder`, the active `Emulator`, the parsed `Routines`, the `BlockGraph`, and the `Dossier` state. It exposes methods for orchestrating the execution pipeline and fetching formatted views.
*   **`src/papple2/workbench/shell.py`:** The user-facing CLI. It instantiates exactly one `_workbench = Workbench()`. Its functions parse the flexible user inputs (`start: int | str`), call the corresponding `_workbench` method, and wrap the output in `Text` for IPython.

## 3. Implementation Steps
We will tackle this step-by-step to ensure tests stay green:

1.  **Extract the Class:** Create `Workbench` in a new file. Move the global variables from `shell.py` into `Workbench.__init__()`.
2.  **Migrate Pipeline Logic:** Move `run()`, `tiling_reports()`, and `set_current_run()` logic into the `Workbench` class as instance methods. Update `shell.py` to delegate these commands.
3.  **Migrate View Logic:** Move the heavy data-fetching logic (`listing_rows`, `call_sites`, etc.) into `Workbench`. Keep the formatting and `print_*` logic in `shell.py`.
4.  **Test Remediation:** Update `test_shell.py` and related tests to either use the `shell.py` wrappers or instantiate their own isolated `Workbench` objects, guaranteeing no test pollution.
