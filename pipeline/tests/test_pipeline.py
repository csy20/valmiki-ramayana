from vr.parse_en import (
    align_monotonic_dp,
    clean_section_body,
    clean_volume_lines,
    extract_proper_tokens,
    fold_for_match,
    fuzzy_parse_roman,
    score_dutt_vs_sarga,
    split_into_paragraphs,
)
from vr.parse_sa import clean_wikitext, extract_poem_body, split_verses


def test_parse_sa_3part_and_1part():
    wiki_3part = """{{header|title=[[../]]}}
<poem>
'''श्रीमद्वाल्मीकियरामायणे बालकाण्डे प्रथमः सर्गः ॥१-१॥'''
तपःस्वाध्यायनिरतं तपस्वी वाग्विदां वरम् ।
नारदं परिपप्रच्छ वाल्मीकिर्मुनिपुङ्गवम् ॥१-१-१॥
<ref>editorial footnote</ref>
को न्वस्मिन्साम्प्रतं लोके गुणवान् कश्च वीर्यवान् ।
धर्मज्ञश्च कृतज्ञश्च सत्यवाक्यो दृढव्रतः ॥१-१-२॥
'''इत्यार्षे श्रीमद्रामायणे वाल्मीकीये आदिकाव्ये बालकाण्डे प्रथमः सर्गः ॥१-१॥'''
</poem>"""
    body, ok = extract_poem_body(wiki_3part)
    assert ok
    verses, anomalies = split_verses(clean_wikitext(body), 1, 1)
    assert not anomalies
    assert len(verses) == 2
    assert verses[0]["n"] == 1
    assert "तपःस्वाध्यायनिरतं" in verses[0]["sa"]
    assert "editorial footnote" not in verses[1]["sa"]
    assert verses[0]["sa"].endswith(" ॥")
    assert "tapaḥsvādhyāyanirataṃ" in verses[0]["iast"]

    wiki_1part = """<div class="verse"><pre>
श्रुत्वा हनूमतो वाक्यम् ।
रामः प्रीतिसमायुक्तः ॥ १॥
इत्यार्षे श्रीमद्रामायणे युद्धकाण्डे प्रथमः सर्गः ॥ १ ॥
</pre></div>"""
    body2, ok2 = extract_poem_body(wiki_1part)
    assert ok2
    verses2, anomalies2 = split_verses(clean_wikitext(body2), 6, 1)
    assert not anomalies2
    assert len(verses2) == 1
    assert verses2[0]["n"] == 1


def test_fuzzy_parse_roman():
    assert fuzzy_parse_roman("I.") == 1
    assert fuzzy_parse_roman("Ml.") == 3
    assert fuzzy_parse_roman("xxxn.") == 32
    assert fuzzy_parse_roman("x l 1 1 .") == 42
    assert fuzzy_parse_roman("XLtll.") == 43
    assert fuzzy_parse_roman("LXVIK") == 67
    assert fuzzy_parse_roman("CXXlV.") == 124
    assert fuzzy_parse_roman("cxx ML") == 123
    assert fuzzy_parse_roman("L.") == 50


def test_clean_and_paragraphs():
    sample = """Google Books boilerplate
Digitized by LjOOQle
SECTION I.
^Hearing those words of Nar-
ada, the sage went away.
* Footnote line — T.
BALAKANDAM.
123
And he beheld a pleasant river.
"""
    lines = clean_volume_lines(sample)
    joined = clean_section_body(lines[1:])
    assert "Google Books" not in joined
    assert "Digitized" not in joined
    assert "Footnote" not in joined
    assert "BALAKANDAM" not in joined
    assert "Narada," in joined

    long_text = " ".join(f"Sentence number {i} talks about Rama and Ayodhya calmly." for i in range(1, 35))
    paras = split_into_paragraphs(long_text, target_min=120, target_max=180)
    assert len(paras) >= 2
    for p in paras[:-1]:
        assert 90 <= len(p.split()) <= 190


def test_dp_alignment():
    # Dutt has 4 sections where section 2 is extra (prakshipta); WS has 3 sargas
    dutt_keys = [1, 2, 3, 4]
    scores = [
        [0.8, 0.0, 0.0],
        [0.0, 0.0, 0.0],  # extra Dutt section
        [0.0, 0.9, 0.0],
        [0.0, 0.0, 0.7],
    ]
    ws_to_dutt, dropped = align_monotonic_dp(dutt_keys, 3, scores)
    assert ws_to_dutt == {1: [1], 2: [3], 3: [4]}
    assert dropped == [2]
    toks = extract_proper_tokens("Rama went with Lakshmana and Sugriva.")
    assert score_dutt_vs_sarga(toks, fold_for_match("rāmaḥ lakṣmaṇaḥ sugrīvaḥ")) == 1.0


def test_hindi_helpers():
    from vr.build import hindi_cache_key
    from vr.hindi import clean_hindi_output, is_suspect_hindi

    k1, n1 = hindi_cache_key("रामः वनं गच्छति ।\nसीता च ॥")
    k2, n2 = hindi_cache_key("रामः वनं गच्छति सीता च")
    assert k1 == k2
    assert n1 == "रामः वनं गच्छति सीता च"

    assert clean_hindi_output("  राम वन गए. ") == "राम वन गए ।".replace("गए ।", "गए ।")
    assert clean_hindi_output("राम वन गए") == "राम वन गए ।"
    assert clean_hindi_output("राम वन गए ।") == "राम वन गए ।"

    assert not is_suspect_hindi("तपस्वी वाल्मीकि ने नारद से पूछा ।", n1)
    assert is_suspect_hindi("", n1)
    assert is_suspect_hindi("एक दो तीन एक दो तीन एक दो तीन एक दो तीन", n1)
