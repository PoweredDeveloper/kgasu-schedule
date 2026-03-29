"""Tests for Bitrix HTML helpers."""

from __future__ import annotations

from scraper.parser import (
    extract_doc_links,
    extract_max_listing_page,
    group_names_from_schedule_link_label,
)


def test_group_names_from_schedule_link_label_strips_docx_and_splits() -> None:
    assert group_names_from_schedule_link_label("25СЖ01,25СЖ02 .docx") == [
        "25СЖ01",
        "25СЖ02",
    ]


def test_group_names_from_schedule_link_label_semicolon() -> None:
    assert group_names_from_schedule_link_label("Г1; Г2.DOC") == ["Г1", "Г2"]


def test_extract_doc_links_doc_and_docx_query_string() -> None:
    html = """
    <div class="news-list">
      <a href="/x/a.doc">A</a>
      <a href="/y/b.docx?v=1">B</a>
      <a href="/z/c.pdf">skip</a>
    </div>
    """
    base = "https://www.kgasu.ru/student/raspisanie-zanyatiy/"
    got = extract_doc_links(html, base)
    assert got == [
        ("https://www.kgasu.ru/x/a.doc", "A"),
        ("https://www.kgasu.ru/y/b.docx?v=1", "B"),
    ]


def test_extract_doc_links_skips_empty_text() -> None:
    html = '<div class="news-list"><a href="/f.doc"></a></div>'
    assert extract_doc_links(html, "https://ex/") == []


def test_extract_max_listing_page_single() -> None:
    assert extract_max_listing_page("<html></html>") == 1


def test_extract_max_listing_page_from_pager() -> None:
    html = """
    <a class="pagination" href="?PAGEN_1=2">2</a>
    <a class="pagination" href="?PAGEN_1=7">7</a>
    """
    assert extract_max_listing_page(html) == 7
