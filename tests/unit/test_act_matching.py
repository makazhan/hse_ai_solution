"""Тесты скоринг-алгоритма авто-матчинга актов с инцидентами."""
import datetime
from uuid import uuid4

import pytest

from src.application.services.act_matching import (
    MATCH_THRESHOLD,
    SUBSTRING_SCORE,
    _compute_score,
    _normalize,
    _score_company,
    _score_date,
    _score_injury_type,
    _score_name,
    _score_region,
)
from src.domain.entities.incidents import EnquiryAct, Incident
from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    InjuryType,
    Region,
)


# --- _normalize ---

class TestNormalize:
    def test_none(self):
        assert _normalize(None) == ""

    def test_empty(self):
        assert _normalize("") == ""

    def test_lowercase_and_collapse_spaces(self):
        assert _normalize("  ФИО  Пострадавшего  ") == "фио пострадавшего"

    def test_remove_quotes(self):
        assert _normalize('АО «Тест»') == "ао тест"
        assert _normalize('АО "Тест"') == "ао тест"


# --- _score_date ---

class TestScoreDate:
    def test_exact_match(self):
        d = datetime.date(2026, 1, 15)
        assert _score_date(d, d) == 1.0

    def test_one_day_diff(self):
        d1 = datetime.date(2026, 1, 15)
        d2 = datetime.date(2026, 1, 16)
        assert _score_date(d1, d2) == pytest.approx(0.75)

    def test_three_days_diff(self):
        d1 = datetime.date(2026, 1, 15)
        d2 = datetime.date(2026, 1, 18)
        assert _score_date(d1, d2) == pytest.approx(0.25)

    def test_four_days_diff(self):
        d1 = datetime.date(2026, 1, 15)
        d2 = datetime.date(2026, 1, 19)
        assert _score_date(d1, d2) == 0.0

    def test_none_act_date(self):
        assert _score_date(None, datetime.date(2026, 1, 15)) == 0.0

    def test_none_incident_date(self):
        assert _score_date(datetime.date(2026, 1, 15), None) == 0.0


# --- _score_name ---

class TestScoreName:
    def test_exact_match(self):
        assert _score_name("Иванов Иван Иванович", "Иванов Иван Иванович") == 1.0

    def test_partial_match(self):
        score = _score_name("Иванов И.И.", "Иванов Иван Иванович")
        assert 0.4 < score < 0.9

    def test_no_match(self):
        score = _score_name("Петров Пётр", "Сидоров Алексей")
        assert score < 0.5

    def test_none_values(self):
        assert _score_name(None, "Иванов") == 0.0
        assert _score_name("Иванов", None) == 0.0

    def test_empty_strings(self):
        assert _score_name("", "Иванов") == 0.0


# --- _score_company ---

class TestScoreCompany:
    def test_exact_substring(self):
        score = _score_company(
            "АО Казахтелеком",
            "АО «Казахтелеком»",
            None,
        )
        assert score == SUBSTRING_SCORE

    def test_dzo_match(self):
        score = _score_company(
            "Нурсат+",
            None,
            "Нурсат+",
        )
        assert score == SUBSTRING_SCORE

    def test_best_of_company_and_dzo(self):
        score = _score_company(
            "Казахтелеком",
            "Unrelated Corp",
            "АО Казахтелеком — головной офис",
        )
        assert score == SUBSTRING_SCORE

    def test_none_act_company(self):
        assert _score_company(None, "Тест", None) == 0.0

    def test_no_match(self):
        score = _score_company("ТОО Восток Электроника", "АО Западный Транспорт", "ООО Северный Металл")
        assert score < 0.5


# --- _score_region ---

class TestScoreRegion:
    def test_exact_substring(self):
        assert _score_region("Алматы", "г. Алматы") == SUBSTRING_SCORE

    def test_none_values(self):
        assert _score_region(None, "Алматы") == 0.0
        assert _score_region("Алматы", None) == 0.0

    def test_no_match(self):
        score = _score_region("Астана", "Актобе")
        assert score < 0.7


# --- _score_injury_type ---

class TestScoreInjuryType:
    def test_both_fatal(self):
        assert _score_injury_type("Смертельный исход", "Смертельный исход") == 1.0

    def test_letal_and_smertelny(self):
        assert _score_injury_type("летальный", "смертельный") == 1.0

    def test_severe_match(self):
        assert _score_injury_type("тяжёлая травма", "Тяжёлая") == 1.0

    def test_light_both_forms(self):
        assert _score_injury_type("лёгкая", "легкая") == 1.0

    def test_mismatch(self):
        assert _score_injury_type("лёгкая", "тяжёлая") == 0.3

    def test_group_case(self):
        assert _score_injury_type("групповой", "групповой случай") == 1.0

    def test_none_values(self):
        assert _score_injury_type(None, "тяжёлая") == 0.0

    def test_no_keywords(self):
        assert _score_injury_type("перелом", "ушиб") == 0.0


# --- _compute_score (integration) ---

class TestComputeScore:
    def _make_act(self, **kwargs) -> EnquiryAct:
        defaults = dict(
            id=uuid4(),
            incident_date_from_act=datetime.date(2026, 1, 15),
            victim_name_from_act="Иванов Иван Иванович",
            company_name_from_act="АО Казахтелеком",
            region_from_act="Алматы",
            injury_severity="тяжёлая",
        )
        defaults.update(kwargs)
        return EnquiryAct(**defaults)

    def _make_incident(self, **kwargs) -> Incident:
        defaults = dict(
            id=uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            victim_name="Иванов Иван Иванович",
            company=Company.KAZAKHTELECOM,
            region=Region.ALMATY_CITY,
            injury_type=InjuryType.SEVERE,
            classification=IncidentClassification.WORK_ACCIDENT,
            location="Офис",
        )
        defaults.update(kwargs)
        return Incident(**defaults)

    def test_perfect_match_above_threshold(self):
        act = self._make_act()
        inc = self._make_incident()
        score = _compute_score(act, inc)
        assert score >= MATCH_THRESHOLD

    def test_different_date_lowers_score(self):
        act = self._make_act(incident_date_from_act=datetime.date(2026, 1, 18))
        inc = self._make_incident()
        score_shifted = _compute_score(act, inc)
        act_exact = self._make_act()
        score_exact = _compute_score(act_exact, inc)
        assert score_shifted < score_exact

    def test_completely_different_below_threshold(self):
        act = self._make_act(
            victim_name_from_act="Петров Пётр",
            company_name_from_act="ТОО Альфа",
            region_from_act="Астана",
            injury_severity="лёгкая",
        )
        inc = self._make_incident(
            incident_date=datetime.date(2026, 2, 1),
        )
        score = _compute_score(act, inc)
        assert score < MATCH_THRESHOLD

    def test_no_extracted_fields(self):
        act = self._make_act(
            incident_date_from_act=None,
            victim_name_from_act=None,
            company_name_from_act=None,
            region_from_act=None,
            injury_severity=None,
        )
        inc = self._make_incident()
        score = _compute_score(act, inc)
        assert score == 0.0
