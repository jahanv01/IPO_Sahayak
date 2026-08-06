from chunker import SectionedPage, build_chunks, detect_sections


def test_detect_sections_skips_front_matter_buffer():
    pages = (
        ["cover page text"] * 15
        + ["RISK FACTORS\n\nSome real risk content."]
        + ["More risk content."] * 2
    )

    sectioned = detect_sections(pages)

    assert all(page.section == "risk_factors" for page in sectioned)
    assert sectioned[0].page_number == 16  # 1-indexed: pages[15]


def test_detect_sections_ignores_toc_entry_with_trailing_page_number():
    toc_page = "RISK FACTORS 45"  # looks like a table-of-contents line, not a heading
    real_heading_page = "RISK FACTORS\n\nActual risk factor content here."
    pages = [toc_page] * 20 + [real_heading_page] + ["more content"]

    sectioned = detect_sections(pages)

    assert sectioned
    assert sectioned[0].page_number == 21  # the real heading, not any ToC page


def test_detect_sections_switches_section_on_new_heading():
    pages = (
        ["front matter"] * 15
        + ["RISK FACTORS\n\nRisk content."]
        + ["OUR BUSINESS\n\nBusiness content."]
    )

    sectioned = detect_sections(pages)

    assert [page.section for page in sectioned] == ["risk_factors", "business"]


def test_build_chunks_splits_long_section_with_overlap():
    long_text = " ".join(f"word{i}" for i in range(500))
    sectioned = [SectionedPage(page_number=1, section="business", text=long_text)]

    chunks = build_chunks(sectioned, words_per_chunk=100, overlap_words=20)

    assert len(chunks) > 1
    assert all(chunk.section == "business" for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    # Overlap: the tail of chunk 0 should reappear at the head of chunk 1.
    assert chunks[0].content.split()[-20:] == chunks[1].content.split()[:20]


def test_build_chunks_tracks_starting_page_across_pages():
    page_10_text = " ".join(f"w{i}" for i in range(140))
    page_11_text = " ".join(f"w{i}" for i in range(140, 280))
    sectioned = [
        SectionedPage(page_number=10, section="financials", text=page_10_text),
        SectionedPage(page_number=11, section="financials", text=page_11_text),
    ]

    chunks = build_chunks(sectioned, words_per_chunk=150, overlap_words=30)

    assert chunks[0].page_number == 10
    # Second chunk starts partway through, still on page 10 or 11 depending on overlap.
    assert chunks[1].page_number in (10, 11)


def test_build_chunks_empty_input():
    assert build_chunks([]) == []
