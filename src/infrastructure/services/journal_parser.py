import io
import os
import datetime
import pandas as pd
from typing import Any, Optional

from src.application.exceptions.files import UnsupportedFileTypeException, FileParseException
from src.application.interfaces.parsers import JournalParser, ParseResult
from src.domain.enums.incidents import (
    Company,
    IncidentClassification,
    Region,
    InjuryType,
    InvestigationResult,
    InvestigationStatus,
    WorkExperience,
    DeletionStatus,
)

_SUPPORTED_EXTENSIONS = {'.xlsx', '.xls'}


class PandasJournalParser(JournalParser):
    """Парсер журнала инцидентов на основе Pandas.

    Автоматически находит строку заголовка, маппит колонки на поля
    сущности Incident, возвращает ParseResult.
    """

    def parse(self, file_content: bytes, filename: str) -> ParseResult:
        """Парсинг Excel-журнала в словари инцидентов.

        Args:
            file_content: байты .xlsx/.xls файла.
            filename: имя файла для валидации расширения.

        Returns:
            ParseResult со строками и ошибками.

        Raises:
            ValueError: неподдерживаемое расширение, нечитаемый файл, нет обязательных колонок.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeException(
                extension=ext, supported=tuple(sorted(_SUPPORTED_EXTENSIONS)),
            )

        errors: list[str] = []

        try:
            preview = pd.read_excel(io.BytesIO(file_content), header=None, nrows=15)
        except Exception as e:
            raise FileParseException(detail=f"Не удалось прочитать Excel-файл: {e}")

        header_row = self._detect_header_row(preview)
        if header_row is None:
            raise FileParseException(detail="Не удалось определить строку заголовка")

        df = pd.read_excel(io.BytesIO(file_content), header=header_row)

        # Убираем безымянные колонки
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        # Очистка имен колонок
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        df = self._apply_column_aliases(df)

        missing_required = [c for c in self._required_columns() if c not in df.columns]
        if missing_required:
            raise FileParseException(detail=f"Отсутствуют обязательные колонки: {missing_required}")

        results = []

        for idx, row in df.iterrows():
            excel_row = header_row + 2 + idx
            # Пропуск пустых строк
            if pd.isna(row.get('Дата возникновения происшествия')) or pd.isna(row.get('Портфельная компания')):
                continue

            try:
                incident_data = self._map_row(row, excel_row=excel_row)
                if self._missing_required_fields(incident_data):
                    errors.append(
                        f"Row {excel_row}: missing required fields after parsing"
                    )
                    continue
                results.append(incident_data)
            except Exception as e:
                errors.append(f"Row {excel_row}: {e}")
                continue

        return ParseResult(rows=results, errors=errors)

    def _detect_header_row(self, preview: pd.DataFrame) -> Optional[int]:
        """Поиск строки заголовка среди первых строк (порог: 4 из 6 обязательных колонок)."""
        required = [self._normalize_col(c) for c in self._required_columns()]
        best_row = None
        best_score = 0
        for i in range(len(preview)):
            row_vals = [self._normalize_col(v) for v in preview.iloc[i].tolist()]
            score = sum(1 for r in required if r in row_vals)
            if score > best_score:
                best_score = score
                best_row = i
        if best_score < 4:
            return None
        return best_row

    def _normalize_col(self, val: Any) -> str:
        """Нормализация имени колонки: пробелы, регистр, переносы строк."""
        if val is None:
            return ""
        return " ".join(str(val).replace("\n", " ").split()).strip().casefold()

    def _required_columns(self) -> list[str]:
        """Обязательные колонки журнала."""
        return [
            'Дата возникновения происшествия',
            'Портфельная компания',
            'Вид/классификация происшествия',
            'Регион происшествия',
            'Место происшествия',
            'Завершено \\ не завершено расследование',
        ]

    def _apply_column_aliases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Приведение колонок к каноническим именам (пробелы, регистр, переносы)."""
        aliases = {
            self._normalize_col('Дата возникновения происшествия'): 'Дата возникновения происшествия',
            self._normalize_col('Портфельная компания'): 'Портфельная компания',
            self._normalize_col('Вид/классификация происшествия'): 'Вид/классификация происшествия',
            self._normalize_col('Регион происшествия'): 'Регион происшествия',
            self._normalize_col('Место происшествия'): 'Место происшествия',
            self._normalize_col('Завершено \\ не завершено расследование'): 'Завершено \\ не завершено расследование',
        }
        col_map = {}
        for col in df.columns:
            normalized = self._normalize_col(col)
            if normalized in aliases:
                col_map[col] = aliases[normalized]
        return df.rename(columns=col_map)

    def _missing_required_fields(self, data: dict[str, Any]) -> bool:
        """Проверка наличия обязательных полей инцидента."""
        required_fields = [
            'incident_date',
            'company',
            'classification',
            'region',
            'location',
            'investigation_status',
        ]
        return any(data.get(field) in (None, "") for field in required_fields)

    def _map_row(self, row: pd.Series, excel_row: int) -> dict[str, Any]:
        """Маппинг строки Excel в словарь полей Incident.

        Args:
            row: строка pandas Series.
            excel_row: номер строки в Excel (для сообщений об ошибках).

        Returns:
            Словарь с полями сущности Incident.

        Raises:
            ValueError: не удалось сопоставить значение перечисления.
        """
        def get_val(col_name: str, default: Any = None) -> Any:
            val = row.get(col_name)
            if pd.isna(val) or val == '' or val == '-':
                return default
            return val

        def get_enum(enum_cls, val: Any, field_name: str) -> Any:
            """Значение ячейки → enum (точное совпадение, затем нормализованное)."""
            if not val:
                return None
            val_str = str(val).strip()
            try:
                return enum_cls(val_str)
            except ValueError:
                normalized = self._normalize_col(val_str)
                normalized_map = {self._normalize_col(e.value): e for e in enum_cls}
                if normalized in normalized_map:
                    return normalized_map[normalized]
                raise FileParseException(
                    detail=f"Некорректное значение для {field_name}: '{val_str}'",
                )

        # Парсинг даты
        def get_date(val: Any) -> Optional[datetime.date]:
            if pd.isna(val) or val == '-':
                return None
            if isinstance(val, datetime.datetime):
                return val.date()
            if isinstance(val, datetime.date):
                return val
            try:
                return pd.to_datetime(val).date()
            except (ValueError, TypeError, OverflowError):
                return None

        # Парсинг времени
        def get_time(val: Any) -> Optional[datetime.time]:
            if pd.isna(val) or val == '-':
                return None
            if isinstance(val, datetime.time):
                return val
            if isinstance(val, datetime.datetime):
                return val.time()
            try:
                return pd.to_datetime(str(val)).time()
            except (ValueError, TypeError, OverflowError):
                return None

        def clean_str(val: Any) -> Optional[str]:
            if pd.isna(val) or val == '-':
                return None
            return str(val).strip()

        # Маппинг полей
        data = {}

        data['incident_date'] = get_date(row.get('Дата возникновения происшествия'))
        data['incident_time'] = get_time(row.get('Время возникновения происшествия'))

        data['company'] = get_enum(Company, get_val('Портфельная компания'), 'company')
        data['dzo'] = clean_str(get_val('ДЗО'))

        data['classification'] = get_enum(
            IncidentClassification,
            get_val('Вид/классификация происшествия'),
            'classification',
        )
        data['region'] = get_enum(Region, get_val('Регион происшествия'), 'region')
        data['location'] = clean_str(get_val('Место происшествия'))

        data['victim_name'] = clean_str(get_val('ФИО пострадавшего'))
        data['victim_birth_date'] = get_date(get_val('Дата рождения прострадавшего'))
        data['victim_position'] = clean_str(get_val('Должность прострадавшего'))
        data['victim_work_experience'] = get_enum(
            WorkExperience,
            get_val('Стаж работы прострадавшего'),
            'victim_work_experience',
        )

        data['injury_type'] = get_enum(InjuryType, get_val('Тип травмы'), 'injury_type')
        data['diagnosis'] = clean_str(get_val('Диагноз'))

        data['description'] = clean_str(get_val('Краткое описание происшествия')) or "Нет описания"

        data['initial_actions'] = clean_str(get_val('Принятые первоочередные меры по защите персонала, локализации'))

        data['consequences_elimination_date'] = get_date(get_val('Дата ликвидации последствий происшествия'))
        data['consequences_elimination_time'] = get_time(get_val('Время ликвидации последствий происшествия'))

        # Влияние на производство (длинное имя колонки)
        impact_col = [c for c in row.index if str(c).startswith('Влияние на производственный процесс')]
        data['impact_on_production'] = clean_str(get_val(impact_col[0])) if impact_col else None

        data['notified_authorities'] = clean_str(get_val('Какие государтвенные органы и другие организации оповещены'))
        data['preliminary_causes'] = clean_str(get_val('Предварительные причины'))
        data['consequences_description'] = clean_str(get_val('Описание проследствий'))

        # Сумма ущерба
        damage_col = [c for c in row.index if str(c).startswith('Сумма ущерба')]
        damage_val = get_val(damage_col[0]) if damage_col else None
        try:
            data['damage_amount_kzt'] = float(damage_val) if damage_val is not None else None
        except (ValueError, TypeError):
            data['damage_amount_kzt'] = None

        data['investigation_results'] = get_enum(
            InvestigationResult,
            get_val('Результаты расследования'),
            'investigation_results',
        )

        data['main_causes_from_report'] = clean_str(get_val('Информация об основных причинах согласно акту расследования'))
        data['corrective_actions'] = clean_str(get_val('Мероприятия по устранению причин несчастного случая, согласно Акту специального расследования'))
        data['corrective_actions_execution_report'] = clean_str(get_val('Отчет об исполнении мероприятий по устранению причин несчастного случая'))
        data['root_causes'] = clean_str(get_val('Информация о коренных причинах'))
        data['notes'] = clean_str(get_val('Примечание'))

        data['investigation_status'] = get_enum(
            InvestigationStatus,
            get_val('Завершено \\ не завершено расследование'),
            'investigation_status',
        )
        data['deletion_status'] = get_enum(
            DeletionStatus,
            get_val('Статаус удаления заявки'),
            'deletion_status',
        )

        # Автозаполнение счётчиков (каждая строка SAP = 1 пострадавший)
        data['victim_count'] = 1
        data['fatality_count'] = 1 if data.get('injury_type') == InjuryType.FATAL else 0

        return data
