from __future__ import annotations

from pathlib import Path

from latexmk_py.fdb import FdbFileEntry, FdbRule, read_fdb, write_fdb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURE = Path(__file__).parent / "fixtures" / "logs" / "simple.fdb_latexmk"


def _make_rule(name: str = "pdflatex") -> FdbRule:
    return FdbRule(
        name=name,
        run_time=1714243200.5,
        source=Path("simple.tex"),
        dest=Path("simple.pdf"),
        base=Path("simple"),
        check_time=1714243201.0,
        last_result=0,
        files=[
            FdbFileEntry(
                path=Path("simple.tex"),
                mtime=1714243100.0,
                size=1234,
                md5="abc123def456abc10123456789abcdef",
                from_rule="",
            ),
            FdbFileEntry(
                path=Path("article.cls"),
                mtime=1700000000.0,
                size=56789,
                md5="feedbeef0000feed0123456789abcdef",
                from_rule="",
            ),
        ],
        generated=[Path("simple.pdf"), Path("simple.log")],
        rewritten_before_read=[],
    )


# ---------------------------------------------------------------------------
# read_fdb — error paths
# ---------------------------------------------------------------------------


def test_read_missing_file(tmp_path: Path) -> None:
    assert read_fdb(tmp_path / "no_such.fdb_latexmk") == {}


def test_read_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.fdb_latexmk"
    p.write_text("", encoding="utf-8")
    assert read_fdb(p) == {}


def test_read_wrong_header(tmp_path: Path) -> None:
    p = tmp_path / "bad.fdb_latexmk"
    p.write_text("not a fdb file\n", encoding="utf-8")
    assert read_fdb(p) == {}


def test_read_wrong_version(tmp_path: Path) -> None:
    p = tmp_path / "bad.fdb_latexmk"
    p.write_text("# Fdb version 99\n", encoding="utf-8")
    assert read_fdb(p) == {}


def test_read_malformed_rule_header(tmp_path: Path) -> None:
    p = tmp_path / "bad.fdb_latexmk"
    p.write_text('# Fdb version 4\n["pdflatex"] broken\n', encoding="utf-8")
    assert read_fdb(p) == {}


def test_read_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    p = tmp_path / "comments.fdb_latexmk"
    p.write_text(
        "# Fdb version 4\n"
        "\n"
        "# a comment\n"
        '["pdflatex"] 0.0 "" "" "" 0.0 0\n'
        "  (generated)\n"
        "  (rewritten before read)\n",
        encoding="utf-8",
    )
    rules = read_fdb(p)
    assert "pdflatex" in rules


# ---------------------------------------------------------------------------
# read_fdb — fixture (real-format file)
# ---------------------------------------------------------------------------


def test_read_fixture_rule_present() -> None:
    assert "pdflatex" in read_fdb(_FIXTURE)


def test_read_fixture_rule_times() -> None:
    rule = read_fdb(_FIXTURE)["pdflatex"]
    assert rule.run_time == 1714243200.5
    assert rule.check_time == 1714243201.0


def test_read_fixture_last_result() -> None:
    assert read_fdb(_FIXTURE)["pdflatex"].last_result == 0


def test_read_fixture_file_count() -> None:
    assert len(read_fdb(_FIXTURE)["pdflatex"].files) == 2


def test_read_fixture_first_file_path() -> None:
    assert read_fdb(_FIXTURE)["pdflatex"].files[0].path == Path("simple.tex")


def test_read_fixture_first_file_md5() -> None:
    assert read_fdb(_FIXTURE)["pdflatex"].files[0].md5 == "abc123def456abc10123456789abcdef"


def test_read_fixture_first_file_size() -> None:
    assert read_fdb(_FIXTURE)["pdflatex"].files[0].size == 1234


def test_read_fixture_generated() -> None:
    generated = read_fdb(_FIXTURE)["pdflatex"].generated
    assert len(generated) == 2
    assert Path("simple.pdf") in generated
    assert Path("simple.log") in generated


def test_read_fixture_rewritten_empty() -> None:
    assert read_fdb(_FIXTURE)["pdflatex"].rewritten_before_read == []


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


def test_round_trip_rule_names(tmp_path: Path) -> None:
    fdb_path = tmp_path / "rt.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": _make_rule()})
    assert set(read_fdb(fdb_path)) == {"pdflatex"}


def test_round_trip_scalars(tmp_path: Path) -> None:
    orig = _make_rule()
    fdb_path = tmp_path / "rt.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": orig})
    got = read_fdb(fdb_path)["pdflatex"]
    assert got.name == orig.name
    assert got.run_time == orig.run_time
    assert got.source == orig.source
    assert got.dest == orig.dest
    assert got.base == orig.base
    assert got.check_time == orig.check_time
    assert got.last_result == orig.last_result


def test_round_trip_file_entries(tmp_path: Path) -> None:
    orig = _make_rule()
    fdb_path = tmp_path / "rt.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": orig})
    got = read_fdb(fdb_path)["pdflatex"]
    assert len(got.files) == len(orig.files)
    for g, o in zip(got.files, orig.files, strict=True):
        assert g.path == o.path
        assert g.mtime == o.mtime
        assert g.size == o.size
        assert g.md5 == o.md5
        assert g.from_rule == o.from_rule


def test_round_trip_generated(tmp_path: Path) -> None:
    orig = _make_rule()
    fdb_path = tmp_path / "rt.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": orig})
    assert read_fdb(fdb_path)["pdflatex"].generated == orig.generated


def test_round_trip_rewritten(tmp_path: Path) -> None:
    orig = FdbRule(
        name="pdflatex",
        run_time=1.0,
        source=Path("a.tex"),
        dest=Path("a.pdf"),
        base=Path("a"),
        check_time=2.0,
        last_result=0,
        rewritten_before_read=[Path("a.aux")],
    )
    fdb_path = tmp_path / "rt.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": orig})
    assert read_fdb(fdb_path)["pdflatex"].rewritten_before_read == [Path("a.aux")]


def test_round_trip_multiple_rules(tmp_path: Path) -> None:
    r2 = FdbRule(
        name="bibtex simple",
        run_time=1714243300.0,
        source=Path("simple.aux"),
        dest=Path("simple.bbl"),
        base=Path("simple"),
        check_time=1714243301.0,
        last_result=0,
    )
    fdb_path = tmp_path / "multi.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": _make_rule(), "bibtex simple": r2})
    assert set(read_fdb(fdb_path)) == {"pdflatex", "bibtex simple"}


# ---------------------------------------------------------------------------
# write_fdb — exact format checks
# ---------------------------------------------------------------------------


def test_write_header(tmp_path: Path) -> None:
    fdb_path = tmp_path / "out.fdb_latexmk"
    write_fdb(fdb_path, {})
    assert fdb_path.read_text(encoding="utf-8").splitlines()[0] == "# Fdb version 4"


def test_write_rule_header_format(tmp_path: Path) -> None:
    rule = FdbRule(
        name="pdflatex",
        run_time=1714243200.0,
        source=Path("a.tex"),
        dest=Path("a.pdf"),
        base=Path("a"),
        check_time=1714243201.0,
        last_result=0,
    )
    fdb_path = tmp_path / "out.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": rule})
    lines = fdb_path.read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith('["pdflatex"]')
    assert '"a.tex"' in lines[1]
    assert '"a.pdf"' in lines[1]


def test_write_file_entry_format(tmp_path: Path) -> None:
    rule = FdbRule(
        name="pdflatex",
        run_time=0.0,
        source=Path("a.tex"),
        dest=Path("a.pdf"),
        base=Path("a"),
        check_time=0.0,
        last_result=0,
        files=[FdbFileEntry(Path("a.tex"), 1.5, 100, "abcd1234abcd1234abcd1234abcd1234", "")],
    )
    fdb_path = tmp_path / "out.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": rule})
    text = fdb_path.read_text(encoding="utf-8")
    assert '  "a.tex"' in text
    assert "abcd1234abcd1234abcd1234abcd1234" in text


def test_write_always_has_generated_and_rewritten_sections(tmp_path: Path) -> None:
    rule = FdbRule(
        name="pdflatex",
        run_time=0.0,
        source=Path("a.tex"),
        dest=Path("a.pdf"),
        base=Path("a"),
        check_time=0.0,
        last_result=0,
    )
    fdb_path = tmp_path / "out.fdb_latexmk"
    write_fdb(fdb_path, {"pdflatex": rule})
    text = fdb_path.read_text(encoding="utf-8")
    assert "  (generated)" in text
    assert "  (rewritten before read)" in text
