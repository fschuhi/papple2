import csv
import argparse
from pathlib import Path
from collections import defaultdict


def compress_xrefs(in_path: Path, out_path: Path) -> None:
    print(f"Reading {in_path}...")

    # Gruppieren nach (instruction, kind, target)
    groups = defaultdict(list)

    with in_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            instr = row["instruction_address"]
            kind = row["kind"]
            target = row["target"]
            eff_addr = int(row["effective_address"], 16)
            count = int(row["count"])

            key = (instr, kind, target)
            groups[key].append((eff_addr, count))

    compressed_rows = []

    # Lückenlose Bereiche (Ranges) finden
    for (instr, kind, target), accesses in groups.items():
        # Sortieren nach effective_address
        accesses.sort(key=lambda x: x[0])

        start_addr = accesses[0][0]
        last_addr = accesses[0][0]
        range_count = accesses[0][1]

        for eff_addr, count in accesses[1:]:
            if eff_addr == last_addr + 1:
                # Lückenlos: Bereich erweitern
                last_addr = eff_addr
                range_count += count
            else:
                # Lücke gefunden: Alten Bereich abspeichern und neuen beginnen
                compressed_rows.append({
                    "instruction_address": instr,
                    "kind": kind,
                    "target": target,
                    "effective_range": f"{start_addr:04x}-{last_addr + 1:04x}",
                    "bytes": (last_addr + 1) - start_addr,
                    "total_count": range_count
                })
                start_addr = eff_addr
                last_addr = eff_addr
                range_count = count

        # Den letzten Bereich der Gruppe abspeichern
        compressed_rows.append({
            "instruction_address": instr,
            "kind": kind,
            "target": target,
            "effective_range": f"{start_addr:04x}-{last_addr + 1:04x}",
            "bytes": (last_addr + 1) - start_addr,
            "total_count": range_count
        })

    print(f"Writing {len(compressed_rows):,} compressed rows to {out_path}...")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "instruction_address", "kind", "target", "effective_range", "bytes", "total_count"
        ])
        writer.writeheader()
        writer.writerows(compressed_rows)


def main():
    parser = argparse.ArgumentParser(description="Compress contiguous xrefs into ranges.")
    parser.add_argument("input_csv", help="Path to raw lr_xrefs.csv")
    parser.add_argument("output_csv", help="Path to save compressed CSV")
    args = parser.parse_args()

    compress_xrefs(Path(args.input_csv), Path(args.output_csv))


if __name__ == "__main__":
    main()
