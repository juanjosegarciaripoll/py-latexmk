from __future__ import annotations

from pathlib import Path

from latexmk_py.parsers.bcf import BcfResult, parse_bcf

FIXTURES = Path(__file__).parent / "fixtures" / "logs"


def test_parse_bcf_data_sources() -> None:
    result = parse_bcf(FIXTURES / "simple.bcf")
    assert "refs.bib" in result.data_sources
    assert "extra.bib" in result.data_sources


def test_parse_bcf_remote_urls_excluded() -> None:
    result = parse_bcf(FIXTURES / "simple.bcf")
    for src in result.data_sources:
        assert not src.startswith("https:")


def test_parse_bcf_missing_file_returns_empty() -> None:
    result = parse_bcf(Path("nonexistent.bcf"))
    assert result == BcfResult(data_sources=frozenset())


def test_parse_bcf_malformed_xml_returns_empty(tmp_path: Path) -> None:
    bcf = tmp_path / "bad.bcf"
    bcf.write_text("this is not xml <<<")
    result = parse_bcf(bcf)
    assert result == BcfResult(data_sources=frozenset())


def test_parse_bcf_empty_datasources(tmp_path: Path) -> None:
    bcf = tmp_path / "empty.bcf"
    bcf.write_text(
        '<?xml version="1.0"?>\n'
        '<bcf:controlfile xmlns:bcf="http://biblatex-biber.sourceforge.net/biblatexml">\n'
        "  <bcf:datasources/>\n"
        "</bcf:controlfile>\n"
    )
    result = parse_bcf(bcf)
    assert result.data_sources == frozenset()


def test_parse_bcf_skips_non_bibtex_datasources(tmp_path: Path) -> None:
    bcf = tmp_path / "mixed.bcf"
    bcf.write_text(
        '<?xml version="1.0"?>\n'
        '<bcf:controlfile xmlns:bcf="http://biblatex-biber.sourceforge.net/biblatexml">\n'
        '  <bcf:datasource type="file" datatype="bibtex">good.bib</bcf:datasource>\n'
        '  <bcf:datasource type="file" datatype="ris">other.ris</bcf:datasource>\n'
        "</bcf:controlfile>\n"
    )
    result = parse_bcf(bcf)
    assert result.data_sources == frozenset({"good.bib"})
