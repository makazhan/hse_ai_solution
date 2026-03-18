"""Тесты фильтров актов расследования"""
import datetime

from src.application.filters.enquiry_acts import EnquiryActFilters


def test_filters_default_all_none():
    """По умолчанию все фильтры = None."""
    f = EnquiryActFilters()
    assert f.act_type is None
    assert f.link_status is None
    assert f.date_from is None
    assert f.victim_name is None
    assert f.cause_category is None


def test_filters_use_primitive_types():
    """Фильтры используют примитивы (str), а не enum-типы."""
    f = EnquiryActFilters(
        act_type="Специальное расследование",
        link_status="Не привязан",
        language="ru",
        incident_id="12345678-1234-1234-1234-123456789abc",
        cause_category="Нарушение ТБ",
        violation_type="Без ограждения",
        industry_tag="Строительство",
    )

    # Все строки — не enum
    assert isinstance(f.act_type, str)
    assert isinstance(f.link_status, str)
    assert isinstance(f.incident_id, str)


def test_filters_date_range():
    """Фильтрация по диапазону дат."""
    f = EnquiryActFilters(
        date_from=datetime.date(2025, 1, 1),
        date_to=datetime.date(2025, 12, 31),
    )
    assert f.date_from == datetime.date(2025, 1, 1)
    assert f.date_to == datetime.date(2025, 12, 31)
