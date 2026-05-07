"""
tests/test_normalisation.py
Unit tests for name normaliser, identifier validator, and address parser.
Run: pytest tests/test_normalisation.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.normalisation.name_normaliser import canonicalise_name
from src.normalisation.identifier_validator import validate_and_normalise_pan, validate_and_normalise_gstin
from src.normalisation.address_parser import parse_address


# ═══════════════════════ name_normaliser ════════════════════════════════════

class TestLegalSuffixRemoval:
    def test_pvt_ltd(self):
        result = canonicalise_name("Peenya Garments Pvt Ltd")
        assert "PVT" not in result["canonical"]
        assert "LTD" not in result["canonical"]
        assert "PEENYA" in result["canonical"]
        assert "GARMENTS" in result["canonical"]

    def test_private_limited(self):
        result = canonicalise_name("Sharma Textiles Private Limited")
        assert "PRIVATE" not in result["canonical"]
        assert "LIMITED" not in result["canonical"]

    def test_llp(self):
        result = canonicalise_name("KSR Industries LLP")
        assert "LLP" not in result["canonical"]

    def test_and_co(self):
        result = canonicalise_name("Ravi Trading & Co.")
        assert "CO" not in result["canonical"] or "RAVI" in result["canonical"]

    def test_empty_name(self):
        result = canonicalise_name("")
        assert result["canonical"] == ""
        assert result["soundex"] == ""

    def test_none_name(self):
        result = canonicalise_name(None)
        assert result["canonical"] == ""


class TestAbbreviationExpansion:
    def test_inds_expansion(self):
        result = canonicalise_name("Peenya Inds")
        assert "INDUSTRIES" in result["canonical"]

    def test_mfg_expansion(self):
        result = canonicalise_name("BLR Mfg Co")
        assert "MANUFACTURING" in result["canonical"]

    def test_engg_expansion(self):
        result = canonicalise_name("ABC Engg Works")
        assert "ENGINEERING" in result["canonical"]


class TestCityNormalisation:
    def test_bangalore_to_bengaluru(self):
        result = canonicalise_name("Bangalore Steel Works")
        assert "BENGALURU" in result["canonical"]
        assert "BANGALORE" not in result["canonical"]

    def test_blr_to_bengaluru(self):
        result = canonicalise_name("BLR Auto Parts")
        assert "BENGALURU" in result["canonical"]


class TestPhoneticKeys:
    def test_soundex_present(self):
        result = canonicalise_name("Peenya Garments")
        assert result["soundex"] != ""
        assert len(result["soundex"]) == 4  # Soundex is always 4 chars

    def test_metaphone_tuple(self):
        result = canonicalise_name("Peenya Garments")
        assert isinstance(result["metaphone"], tuple)
        assert len(result["metaphone"]) == 2


# ═══════════════════════ identifier_validator ════════════════════════════════

class TestPANValidation:
    def test_valid_pan(self):
        result = validate_and_normalise_pan("AABCP1234Q")
        assert result["valid"] is True
        assert result["normalised"] == "AABCP1234Q"
        assert result["has_value"] is True

    def test_lowercase_pan_normalised(self):
        result = validate_and_normalise_pan("aabcp1234q")
        assert result["valid"] is True
        assert result["normalised"] == "AABCP1234Q"

    def test_invalid_pan_format(self):
        result = validate_and_normalise_pan("123456789A")
        assert result["valid"] is False
        assert result["normalised"] is None
        assert result["has_value"] is True

    def test_pan_absent_na(self):
        result = validate_and_normalise_pan("NA")
        assert result["has_value"] is False
        assert result["valid"] is False

    def test_pan_absent_nil(self):
        result = validate_and_normalise_pan("NIL")
        assert result["has_value"] is False

    def test_pan_absent_none(self):
        result = validate_and_normalise_pan(None)
        assert result["has_value"] is False

    def test_pan_absent_empty(self):
        result = validate_and_normalise_pan("")
        assert result["has_value"] is False


class TestGSTINValidation:
    def test_valid_karnataka_gstin(self):
        result = validate_and_normalise_gstin("29AABCP1234Q1Z5")
        assert result["valid"] is True
        assert result["is_karnataka"] is True
        assert result["state_code"] == "29"
        assert result["pan_embedded"] == "AABCP1234Q"

    def test_invalid_gstin(self):
        result = validate_and_normalise_gstin("INVALIDGSTIN")
        assert result["valid"] is False

    def test_gstin_absent(self):
        result = validate_and_normalise_gstin("N/A")
        assert result["has_value"] is False


# ═══════════════════════ address_parser ══════════════════════════════════════

class TestAddressParser:
    def test_bbmp_style(self):
        addr = "#14, 3rd Cross, Peenya Industrial Area, Bengaluru - 560058"
        parsed = parse_address(addr)
        assert parsed.pin_code == "560058"
        assert parsed.address_type == "bbmp"

    def test_industrial_style(self):
        addr = "Plot No. 14-A, KIADB Industrial Area, Peenya, Bengaluru 560058"
        parsed = parse_address(addr)
        assert parsed.pin_code == "560058"
        assert parsed.address_type == "industrial"
        assert parsed.industrial_area is not None

    def test_survey_style(self):
        addr = "Sy. No. 247/3, Peenya Industrial Area, 560058"
        parsed = parse_address(addr)
        assert parsed.address_type == "survey"
        assert parsed.survey_plot_no == "247/3"

    def test_landmark_style(self):
        addr = "Near SBI Bank, 3rd Main, Rajajinagar, Bengaluru 560073"
        parsed = parse_address(addr)
        assert parsed.address_type == "landmark"
        assert parsed.landmark is not None

    def test_pin_code_extraction(self):
        addr = "Some Address, Bengaluru 560058"
        parsed = parse_address(addr)
        assert parsed.pin_code == "560058"

    def test_pin_metadata_fill(self):
        addr = "Industrial Area, 560058"
        parsed = parse_address(addr)
        assert parsed.district == "Bengaluru Urban"
        assert parsed.taluk is not None

    def test_address_tokens_generated(self):
        addr = "Plot 14, KIADB Industrial Area, Peenya, 560058"
        parsed = parse_address(addr)
        assert len(parsed.address_tokens) > 0

    def test_empty_address(self):
        parsed = parse_address("")
        assert parsed.pin_code is None
        assert parsed.address_type == "unknown"
