"""Перечисления для НПА."""
from enum import Enum


class NPATier(str, Enum):
    """Тип НПА по иерархии."""
    KOD = "КОД"
    ZAK = "ЗАК"
    PRIK = "ПРИК"
    POST = "ПОСТ"


TIER_ORDER = [NPATier.KOD, NPATier.ZAK, NPATier.POST, NPATier.PRIK]
