"""Cross referencing: which instruction touched which byte, and how.

An instrumentation package, like Tiling and StackTracking: run() builds it
from the CPU, and its hook methods go into Memory's lists of the same
names.

A cross reference (xref) links an instruction to a byte it touched. Four
kinds are counted, named after Memory's hook lists:

    read_immediate  the operand of an immediate instruction: $42 in LDA #$42
    read_pointer    a byte of a pointer: $06 and $07 in LDA ($06),Y
    read_data       a byte read as data
    write_data      a byte written as data

Opcode and operand fetches are not counted: Tiling knows what ran. Neither
are stack and vector reads: StackTracking keeps the stack.

The report, lr_xrefs.csv, has one row per instruction, kind, target and
effective address:

- The target is the address the operand names, as it stood when the
  instruction ran: the table in LDA tbl,X, the pointer in LDA ($06),Y. It
  is read from the instruction's own bytes at the moment of the access, so
  an operand the program wrote itself shows as it ran, on every pass. An
  immediate has no target: it names no address, it is the value.
- The effective address is the byte touched.

Each row then has how often it happened, and three sets:

- indexes: the values of X or Y that the addressing mode added to reach
  this row's byte. X for abs,X and zp,X, and for the pointer of (zp,X); Y
  for abs,Y and zp,Y, and for the data of (zp),Y. Empty for the rest.
- values: the values read or written.
- old values: for writes, the values that were overwritten.

Observed, not proven: what this records is what this run did.

Known limit: an instruction that writes into its own operand, e.g.
INC *+1, has its write counted under the new target, since the write hook
runs after the write.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from papple2.core.cpu import CPU
from papple2.debug.disassembler import Disassembler
from papple2.workbench.tiling import address

# The kinds, as they will appear in the report: the names of Memory's
# hook lists, without "after_".
READ_IMMEDIATE = "read_immediate"
READ_POINTER = "read_pointer"
READ_DATA = "read_data"
WRITE_DATA = "write_data"

# The order of the kinds within one instruction in the report: the order
# in which an instruction makes its accesses.
KIND_ORDER = (READ_IMMEDIATE, READ_POINTER, READ_DATA, WRITE_DATA)

# The report, and its columns. The folder it goes into is the caller's
# choice.
XREFS_FILE = "lr_xrefs.csv"
XREFS_FIELDS = (
    "instruction",
    "kind",
    "target",
    "effective_address",
    "count",
    "indexes",
    "values",
    "old_values",
)

# The register an addressing mode adds to reach a data byte, and to reach
# a pointer byte, by the names of the disassembler's mode methods.
DATA_INDEX = {
    "absolute_x_mode": "X",
    "zero_page_x_mode": "X",
    "absolute_y_mode": "Y",
    "zero_page_y_mode": "Y",
    "indirect_y_mode": "Y",
}
POINTER_INDEX = {
    "indirect_x_mode": "X",
}


class Xref(NamedTuple):
    """What makes one row of the report: the instruction, the kind of
    access, the target (None for an immediate) and the byte touched."""

    instruction: int
    kind: str
    target: int | None
    effective_address: int


@dataclass(slots=True)
class Tally:
    """What one row of the report adds up over the run."""

    count: int = 0
    indexes: set[int] = field(default_factory=set)
    values: set[int] = field(default_factory=set)
    old_values: set[int] = field(default_factory=set)


def index_registers(cpu: CPU, modes: dict[str, str]) -> list[str | None]:
    """For each opcode, the register its addressing mode adds, by modes,
    or None. The modes come from the disassembler's table, the one place
    that knows each opcode's mode by name."""
    registers: list[str | None] = []
    for entry in Disassembler(cpu).ops:
        mode = entry[2] if len(entry) > 2 else None
        registers.append(modes.get(mode.__name__) if mode is not None else None)
    return registers


class CrossReferencing:
    """Count every immediate, pointer and data access by the instruction
    that made it, through four hooks of Memory."""

    def __init__(self, cpu: CPU) -> None:
        self.cpu = cpu
        # The memory list itself, to read the instruction's operand bytes
        # without calling any hook and without touching a soft switch.
        self.mem = cpu.memory._mem
        self.data_index = index_registers(cpu, DATA_INDEX)
        self.pointer_index = index_registers(cpu, POINTER_INDEX)
        self.tallies: dict[Xref, Tally] = {}

    def after_read_immediate(self, address: int, value: int) -> None:
        self._count(READ_IMMEDIATE, None, address, value, None)

    def after_read_pointer(self, address: int, value: int) -> None:
        register = self.pointer_index[self.cpu.last_opcode]
        self._count(READ_POINTER, self._target(), address, value, register)

    def after_read_data(self, address: int, value: int) -> None:
        register = self.data_index[self.cpu.last_opcode]
        self._count(READ_DATA, self._target(), address, value, register)

    def after_write_data(self, address: int, value: int, old_value: int) -> None:
        register = self.data_index[self.cpu.last_opcode]
        tally = self._count(WRITE_DATA, self._target(), address, value, register)
        tally.old_values.add(old_value)

    def _target(self) -> int | None:
        """The address the running instruction's operand names, read from
        its bytes now."""
        cpu, mem = self.cpu, self.mem
        operand = cpu.last_PC + 1
        if cpu.operand_length == 1:
            return mem[operand & 0xFFFF]
        if cpu.operand_length == 2:
            return mem[operand & 0xFFFF] | mem[(operand + 1) & 0xFFFF] << 8
        return None

    def _count(
        self,
        kind: str,
        target: int | None,
        effective_address: int,
        value: int,
        register: str | None,
    ) -> Tally:
        key = Xref(self.cpu.last_PC, kind, target, effective_address)
        tally = self.tallies.get(key)
        if tally is None:
            tally = self.tallies[key] = Tally()
        tally.count += 1
        tally.values.add(value)
        if register == "X":
            tally.indexes.add(self.cpu.X)
        elif register == "Y":
            tally.indexes.add(self.cpu.Y)
        return tally

    def rows(self) -> list[tuple[Xref, Tally]]:
        """Every row of the report, in the report's order: by instruction,
        then by kind in the order an instruction makes its accesses, then
        by target and effective address."""

        def order(item: tuple[Xref, Tally]) -> tuple:
            xref = item[0]
            return (
                xref.instruction,
                KIND_ORDER.index(xref.kind),
                -1 if xref.target is None else xref.target,
                xref.effective_address,
            )

        return sorted(self.tallies.items(), key=order)

    def write_reports(self, folder: Path) -> None:
        """Write lr_xrefs.csv into folder, creating it if needed."""
        path = folder / XREFS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.rows()
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(XREFS_FIELDS)
            for xref, tally in rows:
                writer.writerow(
                    [
                        address(xref.instruction),
                        xref.kind,
                        "" if xref.target is None else address(xref.target),
                        address(xref.effective_address),
                        tally.count,
                        hex_bytes(tally.indexes),
                        hex_bytes(tally.values),
                        hex_bytes(tally.old_values),
                    ]
                )
        print(f"wrote {len(rows):,} records to {path}")


def hex_bytes(values: set[int]) -> str:
    """A set of bytes as the report shows it: sorted, two hex digits each,
    separated by spaces; empty for an empty set."""
    return " ".join(f"{value:02x}" for value in sorted(values))
