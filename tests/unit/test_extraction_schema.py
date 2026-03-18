"""Тесты Pydantic-схемы валидации ответа LLM."""
import datetime

import pytest

from src.infrastructure.llm.extraction_schema import (
    CorrectiveMeasureSchema,
    EnquiryActExtractionResult,
    ResponsiblePersonSchema,
)


class TestEnquiryActExtractionResult:

    def test_full_json(self):
        """Полный валидный JSON — все поля заполнены."""
        data = {
            "act_type": "Специальное расследование",
            "act_date": "2026-01-15",
            "act_number": "АКТ-001",
            "language": "ru",
            "commission_chairman": "Иванов И.И.",
            "commission_members": ["Петров П.П.", "Сидоров С.С."],
            "investigation_period": "15.01.2026 - 25.01.2026",
            "incident_date_from_act": "2026-01-10",
            "victim_name_from_act": "Козлов К.К.",
            "company_name_from_act": "АО Казахтелеком",
            "region_from_act": "Алматы",
            "victim_name": "Козлов Кирилл Кириллович",
            "victim_birth_date": "1985-06-20",
            "victim_position": "электромонтёр",
            "victim_experience": "5 лет 3 месяца",
            "victim_training_dates": "10.01.2026",
            "injury_severity": "тяжёлая",
            "victim_dependents": "2 иждивенца",
            "company_name": "АО «Казахтелеком»",
            "company_bin": "123456789012",
            "workplace_description": "подстанция",
            "circumstances": "Электротравма",
            "root_causes": "Нарушение ТБ",
            "immediate_causes": "Отсутствие ограждения",
            "state_classifier_codes": ["01", "02"],
            "investigation_method": "Комиссионный",
            "legal_violations": ["ТК РК ст. 182", "Правила ОТ п. 15"],
            "responsible_persons": [
                {"name": "Иванов И.И.", "position": "начальник", "violation": "не обеспечил"},
            ],
            "corrective_measures": [
                {"measure": "Установить ограждение", "deadline": "01.02.2026", "responsible": "Петров П.П."},
            ],
            "work_related": True,
            "employer_fault_pct": 80,
            "worker_fault_pct": 20,
            "conclusions": "НС связан с производством",
            "ai_summary": "Электротравма на подстанции",
            "ai_risk_factors": ["Высокое напряжение", "Отсутствие СИЗ"],
            "cause_categories": ["Технические", "Нарушение ТБ"],
            "violation_types": ["Нарушение электробезопасности"],
            "industry_tags": ["Энергетика"],
        }

        result = EnquiryActExtractionResult.model_validate(data)

        assert result.act_type == "Специальное расследование"
        assert result.act_date == datetime.date(2026, 1, 15)
        assert result.incident_date_from_act == datetime.date(2026, 1, 10)
        assert result.victim_birth_date == datetime.date(1985, 6, 20)
        assert result.employer_fault_pct == 80
        assert result.work_related is True
        assert len(result.responsible_persons) == 1
        assert result.responsible_persons[0].name == "Иванов И.И."
        assert len(result.corrective_measures) == 1
        assert result.corrective_measures[0].measure == "Установить ограждение"

    def test_empty_json(self):
        """Пустой JSON — все поля None/default."""
        result = EnquiryActExtractionResult.model_validate({})

        assert result.act_type is None
        assert result.act_date is None
        assert result.incident_date_from_act is None
        assert result.victim_name is None
        assert result.responsible_persons is None
        assert result.corrective_measures is None
        assert result.cause_categories is None

    def test_partial_json(self):
        """Частично заполненный JSON — только матчинг-поля."""
        data = {
            "incident_date_from_act": "2026-01-10",
            "victim_name_from_act": "Козлов К.К.",
            "company_name_from_act": "АО Казахтелеком",
        }

        result = EnquiryActExtractionResult.model_validate(data)

        assert result.incident_date_from_act == datetime.date(2026, 1, 10)
        assert result.victim_name_from_act == "Козлов К.К."
        assert result.act_type is None
        assert result.conclusions is None

    def test_invalid_date_string(self):
        """Невалидная дата — Pydantic выбрасывает ValidationError."""
        data = {"act_date": "не-дата"}

        with pytest.raises(Exception):
            EnquiryActExtractionResult.model_validate(data)

    def test_model_dump_excludes_none(self):
        """model_dump() с exclude_none возвращает только заполненные поля."""
        data = {
            "act_type": "Внутреннее расследование",
            "victim_name": "Иванов",
        }
        result = EnquiryActExtractionResult.model_validate(data)
        dumped = {k: v for k, v in result.model_dump().items() if v is not None}

        assert "act_type" in dumped
        assert "victim_name" in dumped
        assert "act_date" not in dumped
        assert "conclusions" not in dumped

    def test_model_validate_json_string(self):
        """Валидация из JSON-строки (как приходит от LLM)."""
        json_str = '{"act_type": "Внутреннее расследование", "act_date": "2026-03-01"}'
        result = EnquiryActExtractionResult.model_validate_json(json_str)

        assert result.act_type == "Внутреннее расследование"
        assert result.act_date == datetime.date(2026, 3, 1)


class TestResponsiblePersonSchema:
    def test_full(self):
        p = ResponsiblePersonSchema(name="Иванов", position="начальник", violation="не обеспечил")
        assert p.name == "Иванов"

    def test_partial(self):
        p = ResponsiblePersonSchema(name="Иванов")
        assert p.position is None
        assert p.violation is None


class TestCorrectiveMeasureSchema:
    def test_full(self):
        m = CorrectiveMeasureSchema(measure="Установить", deadline="01.02.2026", responsible="Петров")
        assert m.measure == "Установить"

    def test_empty(self):
        m = CorrectiveMeasureSchema()
        assert m.measure is None
        assert m.deadline is None
