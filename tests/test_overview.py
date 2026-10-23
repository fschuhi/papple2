"""Tests for papple2.workbench.overview: lr_routines.csv and lr_overview.txt
of nested_loops' run.

nested_loops has two routines: the program from 6000, seven blocks, 17
bytes, running to done's NOP at 6013-6014, so its span is 20 bytes; and
sub at 6010, one block of three bytes, called six times by the JSR in
inner.
"""

from pathlib import Path

from papple2.workbench import shell
from papple2.workbench.overview import (
    LISTING_FILE,
    OVERVIEW_FILE,
    ROUTINES_FILE,
    listing_tsv,
    overview_text,
    routines_csv,
    write_overview_reports,
)
from papple2.workbench.shell import label, use_dossier


def test_routines_csv_has_one_row_per_routine_with_labels_and_callees(
    nested_loops_run, tmp_path: Path
) -> None:
    # The dossier is opened after the run: 6000 keeps no label, sub gets one
    # by hand, and 6000's callee shows by it.
    use_dossier(tmp_path / "dossier")
    label(0x6010, "sub")

    assert routines_csv(shell.session).splitlines() == [
        "routine,label,end,span_bytes,blocks,blocks_bytes,called,loops,calls",
        "6000,,6014,20,7,17,1,2,sub",
        "6010,sub,6013,3,1,3,6,0,",
    ]


def test_overview_text_names_the_loops_and_the_routines(
    nested_loops_run, tmp_path: Path
) -> None:
    use_dossier(tmp_path / "dossier")
    label(0x6002, "outer")

    text = overview_text(shell.session)

    assert "  39 instructions" in text
    assert "  2 routines" in text
    # outer is the loop at 6002, run twice; inner, at 6004, lies inside it.
    assert "    loop 6002          2x  outer" in text.splitlines()
    assert "      loop 6004          6x" in text.splitlines()


def test_listing_tsv_lists_every_routine_with_a_separator_row_between(
    nested_loops_run, tmp_path: Path
) -> None:
    # 6000's listing runs to done's NOP and includes sub, which lies
    # inside its span; sub follows with a listing of its own. The separator
    # row carries sub's label and the first address of its listing, so no
    # address cell is empty.
    use_dossier(tmp_path / "dossier")
    label(0x6010, "sub")

    rows = [line.split("\t") for line in listing_tsv(shell.session).splitlines()]

    assert rows[0] == [
        "routine", "address", "bytes", "label",
        "instruction", "target", "target_label", "comment",
    ]
    assert rows[3] == ["6000", "6004", "20 10 60", "", "JSR sub", "6010", "sub", ""]
    assert rows[-3:] == [
        ["sub", "6010", "", "", "", "", "", ""],
        ["sub", "6010", "e6 10", "sub", "INC $10", "0010", "", ""],
        ["sub", "6012", "60", "", "RTS", "", "", ""],
    ]


def test_write_overview_reports_writes_the_three_files_into_the_reports_folder(
    nested_loops_run,
) -> None:
    write_overview_reports(shell.session)

    assert (nested_loops_run.folder / OVERVIEW_FILE).exists()
    assert (nested_loops_run.folder / ROUTINES_FILE).exists()
    assert (nested_loops_run.folder / LISTING_FILE).exists()
