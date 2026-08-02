"""Tests for Palestine tab HTML content."""
from smd.palestine_content import build_palestine_html


def test_palestine_html_includes_resource_links():
    html = build_palestine_html()
    assert "btselem.org" in html
    assert "decolonizepalestine.com" in html
    assert "matwproject.org/crisis-and-emergencies/palestine" in html
    assert "Learn about the occupation and how to help" in html


def test_palestine_html_includes_solidarity_phrases():
    html = build_palestine_html()
    assert "Hold Israel accountable for violations of international law" in html
    assert "Documented human rights violations in Palestine must stop" in html
    assert "Stop the killing and forced displacement in Gaza and the West Bank" in html


def test_palestine_html_includes_journalists_bds_whistleblowers():
    html = build_palestine_html()
    assert "cpj.org" in html
    assert "bdsmovement.net" in html
    assert "breakingthesilence.org.il" in html
    assert "Journalists &amp; press freedom" in html
    assert "Whistleblowers" in html
    assert "journalists and media workers" in html.lower() or "journalists" in html.lower()
    assert "Boycott, Divestment, Sanctions" in html
