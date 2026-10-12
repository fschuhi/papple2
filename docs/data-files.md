# papple2 -- Data files

`papple2` needs Apple II binaries, a disk image and Bandits' files from Total Replay, none of which can be distributed in this repo -- all of them are still under copyright. `data_dir` in `papple2.toml` points to `data/`; its folders `data/bin/` (binaries), `data/do/` (disk images) and `data/tr/bandits/` (Total Replay files) ship with a `.gitkeep` and nothing else. Get the files yourself:

- **`A2ROM.BIN`** -- the Apple II ROM. Available from [Reactive Micro's downloads](https://downloads.reactivemicro.com/Users/Grant_Stockley/), Grant Stockley's page -- also a good source of hard-to-find Apple II documentation and software generally, worth knowing about on its own.
- **`ROBOTRON.BIN`** -- a raw memory image of Robotron 2084. Not distributed as a standalone binary anywhere; has to be produced from the original DOS 3.3 disk image:
  1. Download `Robotron 2084 (1983)(Atari).do` from [myabandonware](https://www.myabandonware.com/game/robotron-2084-2t#download).
  2. Open it in [CiderPress II](https://github.com/fadden/CiderPress2), an open-source Apple II disk/file archive tool.
  3. Right-click on the `ROBOTRON` entry (Type `B`, binary) and extract it.
  4. Check the extracted file's size: 25088 bytes, matching the Data Len CiderPress II shows for the entry, and `ROBOTRON.BIN`'s expected size. If it doesn't match, something went wrong in the extraction.
- **`LODE_RUNNER.BIN`** -- the main program of Lode Runner (Broderbund, 1983), for `make boot-lode-runner`. Also produced from a disk image:
  1. Download the disk image from [archive.org](https://archive.org/details/a2_Lode_Runner_1983_Broderbund_cr_Reset_Vector) (the release cracked by Reset Vector).
  2. Open it in CiderPress II.
  3. Right-click on the `LODE RUNNER` entry (Type `B`, binary) and extract it. Its auxiliary type is `$0800`, the address DOS loads it to, which is also where `scripts/boot_lode_runner.py` loads it.
  4. Check the extracted file's size: 33024 bytes, matching the Data Len CiderPress II shows for the entry. Rename it to `LODE_RUNNER.BIN`.
- **`Lode_Runner_1983_Broderbund_cr_Reset_Vector.do`** -- the Lode Runner disk image itself, the same archive.org download as in step 1 above. Keep its name. `make boot-lode-runner` reads the levels and the high-score table from it once a real game starts. Its size must be 143360 bytes (35 tracks, 16 sectors of 256 bytes, DOS 3.3 order); `papple2.core.disk_image` refuses anything else.
- **Bandits' files** -- the main program `BANDITS` and its data files `BANDITS.A` to `BANDITS.Z`, from Total Replay v6.1 (by 4am and qkumba), for `make boot-bandits`:
  1. Get the Total Replay v6.1 disk image.
  2. Open it in CiderPress II.
  3. Extract `BANDITS` (Type `BIN`, loads at `$0800`, 9479 bytes) and the data files `BANDITS.A` to `BANDITS.Z` (Type `NON`), keeping their names.

Place the binaries in `data/bin/`, the disk image in `data/do/`, and Bandits' files in `data/tr/bandits/` (all below wherever `data_dir` in your `papple2.toml` points).
