"""Fetches the SEBI public issues listing and resolves real DRHP PDF URLs.

SEBI's "Draft Offer Documents filed with SEBI" listing page is server-rendered on page 1
(no JS needed for the most recent ~25 filings). Each row links to a detail page whose real
DRHP PDF is embedded in an <iframe src="...?file=<pdf-url>">, separate from the "Abridged
Prospectus" link that appears in the row's own title text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

LISTING_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10"
USER_AGENT = "IPOSahayakBot/1.0 (+educational project; contact: bhavin.prajapati.ic@gmail.com)"
REQUEST_TIMEOUT = 30
PDF_DOWNLOAD_TIMEOUT = 120

# Matches the trailing "<company-slug>-drhp_<id>.html" of a fresh DRHP filing's URL.
# Filtered separately for "corrigendum"/"addendum" first, since those also end in
# "-drhp_<id>.html" and would otherwise match too.
_DRHP_HREF_RE = re.compile(r"/([a-z0-9-]+)-drhp_(\d+)\.html$", re.IGNORECASE)
_SKIP_KEYWORDS = ("corrigendum", "addendum")
_IFRAME_FILE_RE = re.compile(r"file=(https?://[^'\"]+?\.pdf)", re.IGNORECASE)


@dataclass
class DrhpFiling:
    company: str
    filed_date: str
    detail_url: str
    filing_id: str


def parse_listing(html: str) -> list[DrhpFiling]:
    """Parse the SEBI listing page HTML into fresh DRHP filings.

    Skips corrigenda/addenda and non-DRHP filings (e.g. RHP-only rows).
    """
    soup = BeautifulSoup(html, "html.parser")
    filings = []
    for row in soup.select("table#sample_1 tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        link = cells[1].find("a")
        if link is None or not link.get("href"):
            continue
        href = link["href"]
        if any(keyword in href.lower() for keyword in _SKIP_KEYWORDS):
            continue
        match = _DRHP_HREF_RE.search(href)
        if not match:
            continue
        slug, filing_id = match.groups()
        company = slug.replace("-", " ").title()
        filings.append(
            DrhpFiling(
                company=company,
                filed_date=cells[0].get_text(strip=True),
                detail_url=href,
                filing_id=filing_id,
            )
        )
    return filings


def fetch_listing(session: requests.Session) -> list[DrhpFiling]:
    resp = session.get(LISTING_URL, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return parse_listing(resp.text)


def extract_pdf_url(detail_html: str) -> str | None:
    """Pull the real DRHP PDF URL out of the detail page's embedded iframe."""
    match = _IFRAME_FILE_RE.search(detail_html)
    return match.group(1) if match else None


def fetch_pdf_url(session: requests.Session, detail_url: str) -> str | None:
    resp = session.get(detail_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return extract_pdf_url(resp.text)


def download_pdf(session: requests.Session, pdf_url: str) -> bytes:
    resp = session.get(pdf_url, headers={"User-Agent": USER_AGENT}, timeout=PDF_DOWNLOAD_TIMEOUT)
    resp.raise_for_status()
    return resp.content
