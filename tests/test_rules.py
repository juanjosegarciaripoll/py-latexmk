from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from latexmk_py.config import BuildConfig, CommandsConfig, Config, DirectoriesConfig
from latexmk_py.fdb import FdbFileEntry, FdbRule
from latexmk_py.rules import Rule, compute_md5, init_rules, out_of_date, topo_sort

_TEX = Path("doc.tex")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule(name: str, kind: Literal["primary", "secondary", "postprocess", "cusdep"]) -> Rule:
    return Rule(
        name=name, kind=kind, command="cmd", source=Path("a"), dest=Path("b"), base=Path("a")
    )


def _live_rule(tmp_path: Path) -> Rule:
    """Rule with real files and up-to-date MD5 caches."""
    tex = tmp_path / "doc.tex"
    tex.write_text("hello", encoding="utf-8")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    return Rule(
        name="pdflatex",
        kind="primary",
        command="pdflatex %S",
        source=tex,
        dest=pdf,
        base=Path("doc"),
        run_time=1.0,
        source_md5={tex: compute_md5(tex)},
        dest_md5={pdf: compute_md5(pdf)},
    )


# ---------------------------------------------------------------------------
# init_rules — pdf_mode=1 (pdflatex)
# ---------------------------------------------------------------------------


def test_init_rules_mode1_count() -> None:
    assert len(init_rules(_TEX, Config())) == 1


def test_init_rules_mode1_name() -> None:
    assert init_rules(_TEX, Config())[0].name == "pdflatex"


def test_init_rules_mode1_kind() -> None:
    assert init_rules(_TEX, Config())[0].kind == "primary"


def test_init_rules_mode1_source() -> None:
    assert init_rules(_TEX, Config())[0].source == _TEX


def test_init_rules_mode1_dest() -> None:
    assert init_rules(_TEX, Config())[0].dest == Path("doc.pdf")


def test_init_rules_mode1_never_run() -> None:
    assert init_rules(_TEX, Config())[0].run_time == 0.0


def test_init_rules_mode1_out_dir() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=1), directories=DirectoriesConfig(out_dir="build"))
    assert init_rules(_TEX, cfg)[0].dest == Path("build/doc.pdf")


# ---------------------------------------------------------------------------
# init_rules — pdf_mode=2 (latex → dvips → ps2pdf)
# ---------------------------------------------------------------------------


def test_init_rules_mode2_count() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    assert len(init_rules(_TEX, cfg)) == 3


def test_init_rules_mode2_names() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    names = {r.name for r in init_rules(_TEX, cfg)}
    assert names == {"latex", "dvips", "ps2pdf"}


def test_init_rules_mode2_kinds() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["latex"].kind == "primary"
    assert by_name["dvips"].kind == "postprocess"
    assert by_name["ps2pdf"].kind == "postprocess"


def test_init_rules_mode2_chain_dvi() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["latex"].dest == Path("doc.dvi")
    assert by_name["dvips"].source == Path("doc.dvi")


def test_init_rules_mode2_chain_ps() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["dvips"].dest == Path("doc.ps")
    assert by_name["ps2pdf"].source == Path("doc.ps")


def test_init_rules_mode2_chain_pdf() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    assert {r.name: r for r in init_rules(_TEX, cfg)}["ps2pdf"].dest == Path("doc.pdf")


def test_init_rules_mode2_with_out_dir() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2), directories=DirectoriesConfig(out_dir="out"))
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["latex"].dest == Path("out/doc.dvi")
    assert by_name["dvips"].source == Path("out/doc.dvi")
    assert by_name["ps2pdf"].dest == Path("out/doc.pdf")


# ---------------------------------------------------------------------------
# init_rules — other pdf_modes
# ---------------------------------------------------------------------------


def test_init_rules_mode3_names() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=3))
    names = {r.name for r in init_rules(_TEX, cfg)}
    assert "latex" in names
    assert "dvipdf" in names


def test_init_rules_mode3_dvilua_uses_dvilualatex() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=3, dvi_mode=2))
    names = {r.name for r in init_rules(_TEX, cfg)}
    assert "dvilualatex" in names


def test_init_rules_mode4_lualatex() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=4))
    rules = init_rules(_TEX, cfg)
    assert len(rules) == 1
    assert rules[0].name == "lualatex"


def test_init_rules_mode5_xelatex() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=5))
    names = {r.name for r in init_rules(_TEX, cfg)}
    assert "xelatex" in names
    assert "xdvipdfmx" in names


def test_init_rules_dvi_mode1() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=0, dvi_mode=1))
    rules = init_rules(_TEX, cfg)
    assert len(rules) == 1
    assert rules[0].name == "latex"
    assert rules[0].dest == Path("doc.dvi")


def test_init_rules_dvi_mode2() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=0, dvi_mode=2))
    rules = init_rules(_TEX, cfg)
    assert rules[0].name == "dvilualatex"


def test_init_rules_no_mode_empty() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=0, dvi_mode=0))
    assert init_rules(_TEX, cfg) == []


# ---------------------------------------------------------------------------
# init_rules — FDB restoration
# ---------------------------------------------------------------------------


def test_init_rules_fdb_restores_run_time() -> None:
    fr = FdbRule(
        name="pdflatex",
        run_time=1714243200.5,
        source=Path("doc.tex"),
        dest=Path("doc.pdf"),
        base=Path("doc"),
        check_time=0.0,
        last_result=0,
    )
    rules = init_rules(_TEX, Config(), fdb={"pdflatex": fr})
    assert rules[0].run_time == 1714243200.5


def test_init_rules_fdb_restores_last_result() -> None:
    fr = FdbRule(
        name="pdflatex",
        run_time=1.0,
        source=Path("doc.tex"),
        dest=Path("doc.pdf"),
        base=Path("doc"),
        check_time=0.0,
        last_result=1,
    )
    rules = init_rules(_TEX, Config(), fdb={"pdflatex": fr})
    assert rules[0].last_result == 1


def test_init_rules_fdb_restores_source_md5() -> None:
    fr = FdbRule(
        name="pdflatex",
        run_time=1.0,
        source=Path("doc.tex"),
        dest=Path("doc.pdf"),
        base=Path("doc"),
        check_time=0.0,
        last_result=0,
        files=[FdbFileEntry(Path("doc.tex"), 1.0, 100, "abc123", "")],
    )
    rules = init_rules(_TEX, Config(), fdb={"pdflatex": fr})
    assert rules[0].source_md5.get(Path("doc.tex")) == "abc123"


def test_init_rules_fdb_no_match_keeps_zero_run_time() -> None:
    fr = FdbRule(
        name="other_rule",
        run_time=999.0,
        source=Path("x.tex"),
        dest=Path("x.pdf"),
        base=Path("x"),
        check_time=0.0,
        last_result=0,
    )
    rules = init_rules(_TEX, Config(), fdb={"other_rule": fr})
    assert rules[0].run_time == 0.0


# ---------------------------------------------------------------------------
# compute_md5
# ---------------------------------------------------------------------------


def test_compute_md5_correct(tmp_path: Path) -> None:
    content = b"hello world\n"
    p = tmp_path / "f.txt"
    p.write_bytes(content)
    assert compute_md5(p) == hashlib.md5(content).hexdigest()  # noqa: S324


def test_compute_md5_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_bytes(b"")
    assert compute_md5(p) == hashlib.md5(b"").hexdigest()  # noqa: S324


def test_compute_md5_different_files(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"foo")
    b.write_bytes(b"bar")
    assert compute_md5(a) != compute_md5(b)


def test_compute_md5_same_content(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    assert compute_md5(a) == compute_md5(b)


# ---------------------------------------------------------------------------
# out_of_date
# ---------------------------------------------------------------------------


def test_out_of_date_never_run() -> None:
    rule = Rule(
        name="pdflatex",
        kind="primary",
        command="pdflatex %S",
        source=Path("doc.tex"),
        dest=Path("doc.pdf"),
        base=Path("doc"),
        run_time=0.0,
    )
    assert out_of_date(rule) is True


def test_out_of_date_force() -> None:
    rule = Rule(
        name="pdflatex",
        kind="primary",
        command="pdflatex %S",
        source=Path("doc.tex"),
        dest=Path("doc.pdf"),
        base=Path("doc"),
        run_time=1.0,
    )
    assert out_of_date(rule, force=True) is True


def test_out_of_date_false_when_up_to_date(tmp_path: Path) -> None:
    assert out_of_date(_live_rule(tmp_path)) is False


def test_out_of_date_source_md5_changed(tmp_path: Path) -> None:
    rule = _live_rule(tmp_path)
    rule.source.write_text("changed content", encoding="utf-8")
    assert out_of_date(rule) is True


def test_out_of_date_source_missing(tmp_path: Path) -> None:
    rule = _live_rule(tmp_path)
    rule.source.unlink()
    assert out_of_date(rule) is True


def test_out_of_date_dest_missing(tmp_path: Path) -> None:
    rule = _live_rule(tmp_path)
    rule.dest.unlink()
    assert out_of_date(rule) is True


def test_out_of_date_dest_md5_changed(tmp_path: Path) -> None:
    rule = _live_rule(tmp_path)
    # dest still exists but content differs from what's in dest_md5
    rule.dest.write_bytes(b"%PDF-1.5 different")
    assert out_of_date(rule) is True


def test_out_of_date_no_sources_tracked(tmp_path: Path) -> None:
    # Rule with run_time set, no sources tracked, dest exists — should be up-to-date
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    rule = Rule(
        name="pdflatex",
        kind="primary",
        command="pdflatex %S",
        source=tmp_path / "doc.tex",
        dest=pdf,
        base=Path("doc"),
        run_time=1.0,
        dest_md5={pdf: compute_md5(pdf)},
    )
    assert out_of_date(rule) is False


# ---------------------------------------------------------------------------
# topo_sort
# ---------------------------------------------------------------------------


def test_topo_sort_primary_before_postprocess() -> None:
    rules = [_rule("ps2pdf", "postprocess"), _rule("pdflatex", "primary")]
    kinds = [r.kind for r in topo_sort(rules)]
    assert kinds.index("primary") < kinds.index("postprocess")


def test_topo_sort_primary_before_secondary() -> None:
    rules = [_rule("bibtex", "secondary"), _rule("pdflatex", "primary")]
    kinds = [r.kind for r in topo_sort(rules)]
    assert kinds.index("primary") < kinds.index("secondary")


def test_topo_sort_secondary_before_cusdep() -> None:
    rules = [_rule("my_dep", "cusdep"), _rule("bibtex", "secondary")]
    kinds = [r.kind for r in topo_sort(rules)]
    assert kinds.index("secondary") < kinds.index("cusdep")


def test_topo_sort_secondary_before_postprocess() -> None:
    rules = [_rule("dvips", "postprocess"), _rule("bibtex", "secondary")]
    kinds = [r.kind for r in topo_sort(rules)]
    assert kinds.index("secondary") < kinds.index("postprocess")


def test_topo_sort_same_kind_sorted_by_name() -> None:
    rules = [_rule("zz", "secondary"), _rule("aa", "secondary")]
    assert [r.name for r in topo_sort(rules)] == ["aa", "zz"]


# ---------------------------------------------------------------------------
# xdv_mode rules (T22)
# ---------------------------------------------------------------------------


def test_xdv_mode_produces_xelatex_only(tmp_path: Path) -> None:
    """xdv_mode=1, pdf_mode=0: xelatex primary with .xdv dest; no xdvipdfmx."""
    tex = tmp_path / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}\\end{document}", encoding="utf-8")
    cfg = Config(build=BuildConfig(xdv_mode=1, pdf_mode=0))
    rules = init_rules(tex, cfg)
    names = [r.name for r in rules]
    assert names == ["xelatex"]
    assert rules[0].dest.suffix == ".xdv"
    assert not any(r.name == "xdvipdfmx" for r in rules)


def test_topo_sort_preserves_all_rules() -> None:
    rules = [
        _rule("ps2pdf", "postprocess"),
        _rule("dvips", "postprocess"),
        _rule("bibtex", "secondary"),
        _rule("latex", "primary"),
    ]
    assert len(topo_sort(rules)) == len(rules)


def test_topo_sort_mode2_chain_order() -> None:
    cfg = Config(build=BuildConfig(pdf_mode=2))
    rules = init_rules(_TEX, cfg)
    sorted_rules = topo_sort(rules)
    names = [r.name for r in sorted_rules]
    assert names.index("latex") < names.index("dvips")
    assert names.index("latex") < names.index("ps2pdf")


# ---------------------------------------------------------------------------
# T20: landscape mode — dvips command selection
# ---------------------------------------------------------------------------


def test_landscape_mode2_dvips_uses_landscape_cmd() -> None:
    cfg = Config(
        build=BuildConfig(pdf_mode=2, landscape=True),
        commands=CommandsConfig(dvips_landscape="dvips -tlandscape %O -o %D %S"),
    )
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["dvips"].command == "dvips -tlandscape %O -o %D %S"


def test_portrait_mode2_dvips_uses_default_cmd() -> None:
    cfg = Config(
        build=BuildConfig(pdf_mode=2, landscape=False),
        commands=CommandsConfig(dvips="dvips %O -o %D %S"),
    )
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["dvips"].command == "dvips %O -o %D %S"


def test_landscape_ps_mode_dvips_uses_landscape_cmd() -> None:
    cfg = Config(
        build=BuildConfig(pdf_mode=0, dvi_mode=0, postscript_mode=1, landscape=True),
        commands=CommandsConfig(dvips_landscape="dvips -tlandscape %O -o %D %S"),
    )
    by_name = {r.name: r for r in init_rules(_TEX, cfg)}
    assert by_name["dvips"].command == "dvips -tlandscape %O -o %D %S"
