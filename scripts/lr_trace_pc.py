"""Trace Lode Runner's PC before and after each executed instruction.

Boots headless, including the RWTS trap, and collects one tuple per
instruction: start PC, fetched opcode, and end PC. No control-flow
interpretation is performed.

After the run, writes tmp/lr_trace_pc.csv using uppercase hexadecimal
with a dollar prefix. Adjacent records are kept exactly as observed,
including any gap caused by a trap.

Run from the repo root:

    .venv/bin/python scripts/lr_trace_pc.py data/bin/LODE_RUNNER.BIN
    .venv/bin/python scripts/lr_trace_pc.py data/bin/LODE_RUNNER.BIN --instructions 1000000
"""

import argparse
import csv
import time
from pathlib import Path

# Python puts the folder of the started script on its search path,
# so the sibling boot script can be imported directly.
from boot_lode_runner import boot
from papple2.core.cpu import CPU
from papple2.debug.stop_conditions import instruction_count_reaches

OUTPUT = Path("tmp/lr_trace_pc.csv")


class TracePC:
    """Collect the instruction's start PC, opcode, and resulting PC."""

    def __init__(self, cpu: CPU) -> None:
        self.cpu = cpu
        self.records: list[tuple[int, int, int]] = []

    def after_instruction(self) -> None:
        self.records.append(
            (self.cpu.last_PC, self.cpu.last_opcode, self.cpu.PC)
        )


def save_csv(trace: TracePC, filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("start_PC", "opcode", "end_PC"))
        writer.writerows(
            (f"${start_pc:04X}", f"${opcode:02X}", f"${end_pc:04X}")
            for start_pc, opcode, end_pc in trace.records
        )

    print(f"wrote {len(trace.records):,} instruction records to {filename}")
    print("CSV includes one additional header line")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to LODE_RUNNER.BIN")
    parser.add_argument(
        "--instructions",
        type=int,
        default=4_000_000,
        help="stop after N instructions (default: 4000000)",
    )
    args = parser.parse_args()

    emulator, rwts = boot(args.binary, headless=True)
    trace = TracePC(emulator.cpu)
    emulator.attach(trace)

    start = time.perf_counter()
    emulator.run(until=instruction_count_reaches(args.instructions))
    seconds = time.perf_counter() - start
    emulator.detach(trace)

    print(f"{emulator.instructions:,} instructions in {seconds:.2f} s")
    print(f"RWTS reads served: {len(rwts.log)}")
    save_csv(trace, OUTPUT)


if __name__ == "__main__":
    main()
