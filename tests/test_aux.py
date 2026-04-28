from __future__ import annotations

from pathlib import Path

from latexmk_py.parsers.dotaux import AuxResult, parse_aux

FIXTURES = Path(__file__).parent / "fixtures" / "logs"


def test_parse_aux_bib_files() -> None:
    result = parse_aux(FIXTURES / "simple.aux")
    assert "refs.bib" in result.bib_files
    assert "extra.bib" in result.bib_files


def test_parse_aux_bib_extension_appended() -> None:
    result = parse_aux(FIXTURES / "simple.aux")
    for name in result.bib_files:
        assert name.endswith(".bib")


def test_parse_aux_bst_file() -> None:
    result = parse_aux(FIXTURES / "simple.aux")
    assert "plain" in result.bst_files


def test_parse_aux_recurses_into_input() -> None:
    result = parse_aux(FIXTURES / "simple.aux")
    assert "ch1refs.bib" in result.bib_files


def test_parse_aux_aux_inputs_recorded() -> None:
    result = parse_aux(FIXTURES / "simple.aux")
    assert any("ch1.aux" in p for p in result.aux_inputs)


def test_parse_aux_missing_file_returns_empty() -> None:
    result = parse_aux(Path("nonexistent.aux"))
    assert result == AuxResult(
        bib_files=frozenset(),
        bst_files=frozenset(),
        aux_inputs=frozenset(),
    )


def test_parse_aux_missing_included_aux_skipped(tmp_path: Path) -> None:
    aux = tmp_path / "main.aux"
    aux.write_text("\\bibdata{refs}\n\\@input{missing_child.aux}\n")
    result = parse_aux(aux)
    assert "refs.bib" in result.bib_files
    # missing child silently ignored — no exception raised


def test_parse_aux_no_extension_on_bibdata(tmp_path: Path) -> None:
    aux = tmp_path / "main.aux"
    aux.write_text("\\bibdata{mybib}\n")
    result = parse_aux(aux)
    assert "mybib.bib" in result.bib_files


def test_parse_aux_already_has_bib_extension(tmp_path: Path) -> None:
    aux = tmp_path / "main.aux"
    aux.write_text("\\bibdata{mybib.bib}\n")
    result = parse_aux(aux)
    assert "mybib.bib" in result.bib_files
    assert "mybib.bib.bib" not in result.bib_files


def test_parse_aux_comma_separated_bibdata(tmp_path: Path) -> None:
    aux = tmp_path / "main.aux"
    aux.write_text("\\bibdata{a,b,c}\n")
    result = parse_aux(aux)
    assert result.bib_files == frozenset({"a.bib", "b.bib", "c.bib"})
