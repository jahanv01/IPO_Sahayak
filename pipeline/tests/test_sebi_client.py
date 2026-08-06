"""Tests use HTML fragments captured verbatim from SEBI's real listing/detail pages."""

from sebi_client import extract_pdf_url, parse_listing

# Trimmed excerpt of https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10
SAMPLE_LISTING_HTML = """
<table class='table table-striped table-bordered table-hover bordered fix_table dataTable no-footer' id='sample_1' role='grid'>
<thead><tr role='row'><th>Date</th><th>Title</th></tr></thead>
<tbody>
<tr role='row' class='odd'>
    <td>Aug 06, 2026</td>
    <td><a href="https://www.sebi.gov.in/filings/public-issues/aug-2026/encube-ethicals-limited-drhp_103383.html"  target="_blank" title="Encube Ethicals Limited - DRHP<br><a href= 'https://www.sebi.gov.in/sebi_data/commondocs/aug-2026/Encube%20Ethicals%20Limited%20-%20AP_p.pdf' style=color:#000000>Encube Ethicals Limited- Abridged Prospectus</a>" class="points"> Encube Ethicals Limited - DRHP</a>
</tr>
<tr role='row' class='odd'>
    <td>Aug 03, 2026</td>
    <td><a href="https://www.sebi.gov.in/filings/public-issues/aug-2026/hero-motors-limited-corrigendum-to-drhp_103180.html"  target="_blank" title="Hero Motors Limited - Corrigendum to DRHP" class="points"> Hero Motors Limited - Corrigendum to DRHP</a>
</tr>
<tr role='row' class='odd'>
    <td>Aug 03, 2026</td>
    <td><a href="https://www.sebi.gov.in/filings/public-issues/aug-2026/veritas-finance-limited-rhp_103304.html"  target="_blank" title="Veritas Finance Limited - RHP" class="points"> Veritas Finance Limited - RHP</a>
</tr>
<tr role='row' class='odd'>
    <td>Jul 22, 2026</td>
    <td><a href="https://www.sebi.gov.in/filings/public-issues/jul-2026/fusion-cx-limited-addendum-to-drhp_102992.html"  target="_blank" title="Fusion CX Limited - Addendum to DRHP" class="points"> Fusion CX Limited - Addendum to DRHP</a>
</tr>
<tr role='row' class='odd'>
    <td>Jul 29, 2026</td>
    <td><a href="https://www.sebi.gov.in/filings/public-issues/jul-2026/indian-gas-exchange-limited-drhp_102988.html"  target="_blank" title="Indian Gas Exchange Limited - DRHP" class="points"> Indian Gas Exchange Limited - DRHP</a>
</tr>
</tbody>
</table>
"""

# Trimmed excerpt of a real SEBI filing detail page.
SAMPLE_DETAIL_HTML = """
<iframe src='../../../web/?file=https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1785994501228.pdf' width='100%' style='max-height:90%; height:600px;'></iframe>
"""


def test_parse_listing_keeps_only_fresh_drhp_filings():
    filings = parse_listing(SAMPLE_LISTING_HTML)

    # Corrigendum, addendum, and RHP-only rows are all excluded.
    assert [f.company for f in filings] == ["Encube Ethicals Limited", "Indian Gas Exchange Limited"]


def test_parse_listing_extracts_date_and_filing_id():
    filings = parse_listing(SAMPLE_LISTING_HTML)

    first = filings[0]
    assert first.filed_date == "Aug 06, 2026"
    assert first.filing_id == "103383"
    assert first.detail_url.endswith("encube-ethicals-limited-drhp_103383.html")


def test_extract_pdf_url_from_iframe():
    assert (
        extract_pdf_url(SAMPLE_DETAIL_HTML)
        == "https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1785994501228.pdf"
    )


def test_extract_pdf_url_returns_none_when_no_iframe():
    assert extract_pdf_url("<p>no iframe here</p>") is None
