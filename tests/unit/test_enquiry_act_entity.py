"""Тесты доменной сущности EnquiryAct"""
import datetime
from uuid import uuid4

from src.domain.entities.incidents import EnquiryAct, EnquiryActChunk
from src.domain.enums.incidents import (
    EnquiryActType,
    EnquiryActLinkStatus,
)


def test_enquiry_act_defaults():
    """Создание акта с минимальным набором полей — проверяем дефолты."""
    act = EnquiryAct()

    assert act.id is not None
    assert act.incident_id is None
    assert act.link_status == EnquiryActLinkStatus.UNLINKED
    assert act.act_type is None
    assert act.language == "ru"
    assert act.commission_members == []
    assert act.cause_categories == []
    assert act.violation_types == []
    assert act.industry_tags == []


def test_enquiry_act_with_all_fields():
    """Создание акта с заполненными полями."""
    act_id = uuid4()
    incident_id = uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    act = EnquiryAct(
        id=act_id,
        incident_id=incident_id,
        link_status=EnquiryActLinkStatus.AUTO_MATCHED,
        act_type=EnquiryActType.SPECIAL,
        act_date=datetime.date(2026, 1, 15),
        act_number="АКТ-001",
        file_path="uploads/2026/01/15/test.pdf",
        original_filename="test.pdf",
        extracted_text="Текст акта",
        victim_name="Иванов И.И.",
        company_name="АО Тест",
        cause_categories=["Нарушение ТБ"],
        violation_types=["Нет ограждения"],
        industry_tags=["Строительство"],
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )

    assert act.id == act_id
    assert act.incident_id == incident_id
    assert act.link_status == EnquiryActLinkStatus.AUTO_MATCHED
    assert act.act_type == EnquiryActType.SPECIAL
    assert act.cause_categories == ["Нарушение ТБ"]


def test_enquiry_act_manually_linked_status():
    """Проверка нового статуса MANUALLY_LINKED."""
    act = EnquiryAct(link_status=EnquiryActLinkStatus.MANUALLY_LINKED)
    assert act.link_status == EnquiryActLinkStatus.MANUALLY_LINKED
    assert act.link_status.value == "Привязан вручную"


def test_enquiry_act_timestamps_are_utc():
    """Дефолтные timestamps должны быть timezone-aware (UTC)."""
    act = EnquiryAct()
    assert act.created_at.tzinfo is not None
    assert act.uploaded_at.tzinfo is not None
    assert act.updated_at.tzinfo is not None


def test_enquiry_act_chunk_creation():
    """Создание чанка акта."""
    act_id = uuid4()
    chunk = EnquiryActChunk(
        act_id=act_id,
        chunk_index=0,
        section_type="circumstances",
        content="Текст чанка",
        embedding=[0.1] * 1024,
    )

    assert chunk.act_id == act_id
    assert chunk.chunk_index == 0
    assert len(chunk.embedding) == 1024
