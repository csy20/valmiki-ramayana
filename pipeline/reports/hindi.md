# Hindi Generation Benchmark & Policy Report (IndicTrans2)

- **Model ID:** `ai4bharat/indictrans2-indic-indic-dist-320M` (MIT License)
- **Pinned Revision:** `ffb7582b6d43791f1fb26b2153fc065f2e9ea575`
- **Direction:** `san_Deva` → `hin_Deva`
- **Status:** `hi` kept `null` (`"hi_source": "pending"`, `"hi_verified": false`) across all 23,578 verses pending a classical-Sanskrit-capable generator or community-verified translations.

## CPU Throughput Benchmark (8-core CPU)

| Setting | Sample Size | Throughput | Projected Full Corpus (23,578 vv.) |
| --- | ---: | ---: | ---: |
| `fp32`, `beams=1`, `batch=32` | 50 verses | **2.36 verses/s** | ~2.77 h |
| `fp32`, `beams=1`, `batch=10` | 10 verses | 1.43 verses/s | ~4.57 h |
| `fp32`, `beams=4`, `batch=10` | 10 verses | 0.06 verses/s | ~117 h (repetition loops without penalty) |
| `int8` dynamic quant, `beams=1` | 10 verses | 0.26 verses/s | ~25.0 h |
| `int8` dynamic quant, `beams=4` | 10 verses | 0.07 verses/s | ~93.2 h |

## Sample Output Inspection (`01-bala` 1.1–1.4 & 1.2.1–2)

Testing confirmed canonical `IndicProcessor` formatting (`san_Deva hin_Deva ...`), yet `indictrans2-indic-indic-dist-320M` severely mistranslates sandhi-rich classical Sanskrit poetry because it is trained primarily on modern prose:

- **1.1.1 (`fp32, beams=1`):**
  - SA: `तपः स्वाध्यायनिरतं तपस्वी वाग्विदां वरम् नारदं परिपप्रच्छ वाल्मीकिर्मुनिपुङ्गवम्`
  - HI: `तपस्वी भिक्षु ने नारियला को पोंगवा में डाल दिया, जो तपस्या कर रहे थे।` (hallucinated)
- **1.1.1 (`fp32, beams=4`):**
  - HI: `तपस्वियों में से एक, वाल्मिकी मुर्मनी पुंगुआ ने तपस्या की और भिक्षुओं का आशीर्वाद प्राप्त किया।`
- **1.1.2 (`fp32, beams=1`):**
  - SA: `को न्वस्मिन्साम्प्रतं लोके गुणवान्कश्च वीर्यवान् धर्मज्ञश्च कृतज्ञश्च सत्यवाक्यो दृढव्रतः`
  - HI: `एक सद्गुणी, नारीवादी, धर्मशास्त्री और कृतज्ञ व्यक्ति, जो सत्य वचन पर अटल है।` (`वीर्यवान्` mistranslated as `नारीवादी`)
- **1.1.4 (`fp32, beams=4`, without repetition penalty):**
  - Looped `"या खुद को खुश करने के लिए"` repeatedly until `max_new_tokens=256`.
- **1.2.1 (`beams=2, repetition_penalty=1.2, no_repeat_ngram_size=3`, danda-preserved):**
  - SA: `नारदस्य तु तद्वाक्यं श्रुत्वा वाक्यविशारदः । पूजयामास धर्मात्मा सहशिष्यो महामुनिम् ।`
  - HI: `हालाँकि, नारद के इस कथन को सुनकर, उन्होंने कहा, "भगवान की पूजा करने वाले आत्मा को एक साथ सिखने के लिए धन्यवाद।"`

## Decision

Rather than publishing 23,578 misleading machine hallucinations, the Hindi pipeline module (`pipeline/vr/hindi.py`) and benchmark results are preserved in the repository while `data/` ships with `"hi": null`, `"hi_source": "pending"`, `"hi_verified": false` across all verses. Readers show a transparent notice, and community PRs (`hi_source: "community_verified"`, `hi_verified: true`) or future validated public-domain Hindi pipelines can populate verses incrementally via `pipeline/vr/build.py`.
