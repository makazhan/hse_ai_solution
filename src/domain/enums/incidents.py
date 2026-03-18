from enum import Enum

class Company(str, Enum):
    """Портфельная компания"""
    KAZAKHTELECOM = "АО «Казахтелеком»"
    KAZMUNAYGAS = "АО «НК «КазМунайГаз»"
    KAZPOST = "АО «Казпочта»"
    SAMRUK_ENERGO = "АО «Самрук-Энерго»"
    KAZATOMPROM = "АО «НАК «Казатомпром»"
    KTZ = "АО «НК «Казахстан темир жолы»"
    KEGOC = "АО «KEGOC»"
    QAZAQGAZ = "АО «НК «QazaqGaz»"
    TAU_KEN_SAMRUK = "АО «НГРК «Тау-Кен Самрук»"
    SAMRUK_KAZYNA_ONDEU = "ТОО 'Samruk-Kazyna Ondeu'"

class IncidentClassification(str, Enum):
    """Вид/классификация происшествия"""
    WORK_ACCIDENT = "Несчастный случай (согласно Трудовому кодексу РК)"
    NO_INJURY_DTP = "ДТП без пострадавших по вине работника организации"
    FATAL_HEALTH_ISSUE_AT_WORK = "Несчастный случай по причине внезапного ухудшения здоровья с летальным исходом (в рабочее время и на рабочем месте)"
    FIRE_NO_INJURIES = "Пожар без пострадавших"
    ACCIDENT_NO_INJURIES = "Авария без пострадавших (согласно Закону РК «О Гражданской защите)"
    DANGEROUS_OBJECT_INCIDENT = "Инцидент на опасном производственном объекте (согласно Закону РК «О Гражданской защите)"
    HEALTH_ISSUE_ACCIDENT = "Несчастный случай по причине внезапного ухудшения здоровья"
    FATAL_HEALTH_ISSUE_OFF_WORK = "Несчастный случай по причине внезапного ухудшения здоровья с летальным исходом (в не рабочее время и не на рабочем месте)"
    EMERGENCY_NO_INJURIES = "Чрезвычайная ситуация без пострадавших"

class Region(str, Enum):
    """Регион происшествия"""
    EKO = "Восточно-Казахстанская область"
    ATYRAU = "Атырауская область"
    KOSTANAY = "Костанайская область"
    PAVLODAR = "Павлодарская область"
    TURKESTAN = "Туркестанская область"
    MANGISTAU = "Мангистауская область"
    KYZYLORDA = "Кызылординская область"
    AKTOBE = "Актюбинская область"
    ALMATY_REGION = "Алматинская область"
    ABAY = "Абайская область"
    NEAR_ABROAD = "Ближнее зарубежье"
    ALMATY_CITY = "Алматы"
    SKO = "Северо-Казахстанская область"
    AKMOLA = "Акмолинская область"
    ASTANA_CITY = "Астана"
    KARAGANDA = "Карагандинская область"
    ZHAMBYL = "Жамбылская область"
    ZKO = "Западно-Казахстанская область"
    ULYTAU = "Улытауская область"
    SHYMKENT_CITY = "Шымкент"
    ZHETYSU = "Жетысуйская область"

class WorkExperience(str, Enum):
    """Стаж работы пострадавшего"""
    FROM_6_TO_10_YEARS = "С 6 до 10 лет"
    FROM_1_TO_5_YEARS = "С 1 до 5 лет"
    LESS_THAN_1_YEAR = "До 1 года"
    FROM_11_TO_20_YEARS = "С 11 до 20 лет"
    MORE_THAN_20_YEARS = "Более 20 лет"

class InjuryType(str, Enum):
    """Тип травмы"""
    SEVERE = "Травма относится к тяжелым"
    NON_SEVERE = "Травма не относится к тяжелым"
    FATAL = "Смертельный исход"

class InvestigationResult(str, Enum):
    """Результаты расследования"""
    WORK_RELATED = "Связан с трудовой деятельностью"
    NOT_WORK_RELATED = "Не связан с трудовой деятельностью"

class InvestigationStatus(str, Enum):
    """Завершено / не завершено расследование"""
    COMPLETED = "Завершено"
    NOT_COMPLETED = "Не завершено"

class DeletionStatus(str, Enum):
    """Статаус удаления заявки"""
    MARKED_FOR_DELETION = "УДАЛИТЬ"

class RecommendationPriority(str, Enum):
    """Приоритет рекомендации по ТБ"""
    HIGH = "Высокий"
    MEDIUM = "Средний"
    LOW = "Низкий"

class RecommendationStatus(str, Enum):
    """Статус выполнения рекомендации"""
    PENDING = "Ожидает выполнения"
    IN_PROGRESS = "В работе"
    COMPLETED = "Выполнено"
    REJECTED = "Отклонено"


class EnquiryActType(str, Enum):
    """Тип акта расследования"""
    INTERNAL = "Внутреннее расследование"
    SPECIAL = "Специальное расследование"


class EnquiryActLinkStatus(str, Enum):
    """Статус привязки акта к инциденту"""
    UNLINKED = "Не привязан"
    AUTO_MATCHED = "Автоматически привязан"
    MANUALLY_LINKED = "Привязан вручную"