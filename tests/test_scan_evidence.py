"""Independent OCR must locate scan evidence before a fact is verified."""

from src.policy import FactRecord, verify_scan_record
from src.scan_evidence import read_tesseract_words


def record(box=None):
    return FactRecord.model_validate({
        "fact_id": "scan-1", "kind": "field", "subject": None,
        "relation": "invoice_number", "value": "A-17", "origin": "extracted",
        "evidence": {"page": 1, "quote": "Invoice A-17", "bbox": box},
        "state": "uncertain", "reason": "Unchecked", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    })


WORDS = [
    {"page": 1, "text": "Invoice", "bbox": [72, 50, 110, 62], "source": "tesseract"},
    {"page": 1, "text": "A-17", "bbox": [114, 50, 140, 62], "source": "tesseract"},
]


def test_independent_word_boxes_verify_same_quote():
    checked = verify_scan_record(record(), "Invoice A-17", WORDS)
    assert checked.state == "verified"
    assert checked.evidence.bbox == [72.0, 50.0, 140.0, 62.0]


def test_scan_disagreement_and_missing_provenance_stay_uncertain():
    assert verify_scan_record(record(), "Invoice B-17", WORDS).state == "uncertain"
    altered = [dict(word) for word in WORDS]
    altered[1]["text"] = "A-18"
    assert verify_scan_record(record(), "Invoice A-17", altered).state == "uncertain"
    altered[1]["text"] = "A-17"
    altered[1]["source"] = "vision"
    assert verify_scan_record(record(), "Invoice A-17", altered).state == "uncertain"


def test_scan_claimed_box_and_wrong_page_cannot_pass():
    assert verify_scan_record(record([300, 300, 350, 320]), "Invoice A-17", WORDS).state == "uncertain"
    wrong_page = [dict(word, page=2) for word in WORDS]
    assert verify_scan_record(record(), "Invoice A-17", wrong_page).state == "uncertain"


def test_inferred_scan_fact_cannot_be_verified():
    inferred = record().model_copy(update={"origin": "inferred"})
    assert verify_scan_record(inferred, "Invoice A-17", WORDS).state == "uncertain"


def test_tesseract_reader_attaches_page_boxes_and_provenance():
    class Page:
        number = 0

        def get_textpage_ocr(self, **kwargs):
            assert kwargs["full"] is True
            return "ocr-page"

        def get_text(self, kind, *, textpage):
            assert kind == "words" and textpage == "ocr-page"
            return [(72, 50, 110, 62, "Invoice", 0, 0, 0),
                    (114, 50, 140, 62, "A-17", 0, 0, 1)]

    assert read_tesseract_words(Page()) == WORDS
