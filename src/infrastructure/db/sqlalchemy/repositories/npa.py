from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from src.application.interfaces.repositories.npa import (
    BaseNpaTypeRepository,
    BaseNpaRepository,
    BaseNormTypeRepository,
    BaseNormRepository,
    BaseNormVersionRepository,
    BaseNormEmbeddingRepository,
    BaseAmendmentRepository,
    BaseCrossReferenceRepository,
)
from src.domain.entities.npa import (
    NpaTypeEntity,
    NpaEntity,
    NormTypeEntity,
    NormEntity,
    NormVersionEntity,
    NormEmbeddingEntity,
    AmendmentEntity,
    CrossReferenceEntity,
)
from src.domain.enums.npa import LanguageCode, NormStatus
from src.infrastructure.db.sqlalchemy.models.npa import (
    NpaTypeModel,
    NpaModel,
    NormTypeModel,
    NormModel,
    NormVersionModel,
    NormEmbeddingModel,
    AmendmentModel,
    CrossReferenceModel,
)
from src.infrastructure.db.sqlalchemy.repositories.base import BaseSqlAlchemyRepository


@dataclass
class SqlAlchemyNpaTypeRepository(BaseNpaTypeRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, npa_type_id: UUID) -> NpaTypeEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaTypeModel).where(NpaTypeModel.id == npa_type_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_code(self, code: str) -> NpaTypeEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaTypeModel).where(NpaTypeModel.code == code)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_all(self) -> list[NpaTypeEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaTypeModel).order_by(NpaTypeModel.hierarchy_level)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, npa_type: NpaTypeEntity) -> NpaTypeEntity:
        async with self._async_sessionmaker() as session:
            model = NpaTypeModel.from_entity(npa_type)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()


@dataclass
class SqlAlchemyNpaRepository(BaseNpaRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, npa_id: UUID) -> NpaEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaModel)
                .options(selectinload(NpaModel.npa_type))
                .where(NpaModel.id == npa_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_type(self, npa_type_id: UUID) -> list[NpaEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaModel)
                .options(selectinload(NpaModel.npa_type))
                .where(NpaModel.npa_type_id == npa_type_id)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_effective_on_date(self, query_date: date) -> list[NpaEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NpaModel)
                .options(selectinload(NpaModel.npa_type))
                .where(
                    and_(
                        NpaModel.effective_from <= query_date,
                        or_(
                            NpaModel.effective_to.is_(None),
                            NpaModel.effective_to > query_date
                        ),
                        NpaModel.status == NormStatus.ACTIVE.value
                    )
                )
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, npa: NpaEntity) -> NpaEntity:
        async with self._async_sessionmaker() as session:
            model = NpaModel.from_entity(npa)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def update(self, npa: NpaEntity) -> NpaEntity:
        async with self._async_sessionmaker() as session:
            model = NpaModel.from_entity(npa)
            merged = await session.merge(model)
            await session.commit()
            await session.refresh(merged)
            return merged.to_entity()


@dataclass
class SqlAlchemyNormTypeRepository(BaseNormTypeRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, norm_type_id: UUID) -> NormTypeEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormTypeModel).where(NormTypeModel.id == norm_type_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_code(self, code: str) -> NormTypeEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormTypeModel).where(NormTypeModel.code == code)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_retrievable(self) -> list[NormTypeEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormTypeModel).where(NormTypeModel.is_retrievable == True)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, norm_type: NormTypeEntity) -> NormTypeEntity:
        async with self._async_sessionmaker() as session:
            model = NormTypeModel.from_entity(norm_type)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()


@dataclass
class SqlAlchemyNormRepository(BaseNormRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, norm_id: UUID) -> NormEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormModel)
                .options(
                    selectinload(NormModel.npa).selectinload(NpaModel.npa_type),
                    selectinload(NormModel.norm_type)
                )
                .where(NormModel.id == norm_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_npa_id(self, npa_id: UUID) -> list[NormEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormModel)
                .options(selectinload(NormModel.norm_type))
                .where(NormModel.npa_id == npa_id)
                .order_by(NormModel.path)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_children(self, parent_id: UUID) -> list[NormEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormModel)
                .options(selectinload(NormModel.norm_type))
                .where(NormModel.parent_id == parent_id)
                .order_by(NormModel.order_index)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_ancestors(self, norm_id: UUID) -> list[NormEntity]:
        async with self._async_sessionmaker() as session:
            norm_result = await session.execute(
                select(NormModel).where(NormModel.id == norm_id)
            )
            norm = norm_result.scalar_one_or_none()
            if not norm or not norm.path:
                return []

            path_parts = norm.path.split('.')
            ancestor_ids = [UUID(p) for p in path_parts[:-1]]

            if not ancestor_ids:
                return []

            result = await session.execute(
                select(NormModel)
                .options(selectinload(NormModel.norm_type))
                .where(NormModel.id.in_(ancestor_ids))
                .order_by(NormModel.depth)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, norm: NormEntity) -> NormEntity:
        async with self._async_sessionmaker() as session:
            model = NormModel.from_entity(norm)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def update(self, norm: NormEntity) -> NormEntity:
        async with self._async_sessionmaker() as session:
            model = NormModel.from_entity(norm)
            merged = await session.merge(model)
            await session.commit()
            await session.refresh(merged)
            return merged.to_entity()


@dataclass
class SqlAlchemyNormVersionRepository(BaseNormVersionRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, version_id: UUID) -> NormVersionEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormVersionModel)
                .options(
                    selectinload(NormVersionModel.norm)
                    .selectinload(NormModel.npa)
                    .selectinload(NpaModel.npa_type),
                    selectinload(NormVersionModel.norm)
                    .selectinload(NormModel.norm_type),
                )
                .where(NormVersionModel.id == version_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_current_version(
        self, norm_id: UUID, language: LanguageCode
    ) -> NormVersionEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormVersionModel)
                .options(selectinload(NormVersionModel.norm))
                .where(
                    and_(
                        NormVersionModel.norm_id == norm_id,
                        NormVersionModel.language == language.value,
                        NormVersionModel.effective_to.is_(None),
                        NormVersionModel.status == NormStatus.ACTIVE.value
                    )
                )
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_version_at_date(
        self, norm_id: UUID, language: LanguageCode, query_date: date
    ) -> NormVersionEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormVersionModel)
                .options(selectinload(NormVersionModel.norm))
                .where(
                    and_(
                        NormVersionModel.norm_id == norm_id,
                        NormVersionModel.language == language.value,
                        NormVersionModel.effective_from <= query_date,
                        or_(
                            NormVersionModel.effective_to.is_(None),
                            NormVersionModel.effective_to > query_date
                        ),
                        NormVersionModel.status == NormStatus.ACTIVE.value
                    )
                )
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_all_versions(self, norm_id: UUID) -> list[NormVersionEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormVersionModel)
                .where(NormVersionModel.norm_id == norm_id)
                .order_by(NormVersionModel.effective_from.desc())
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, version: NormVersionEntity) -> NormVersionEntity:
        async with self._async_sessionmaker() as session:
            model = NormVersionModel.from_entity(version)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def update(self, version: NormVersionEntity) -> NormVersionEntity:
        async with self._async_sessionmaker() as session:
            model = NormVersionModel.from_entity(version)
            merged = await session.merge(model)
            await session.commit()
            await session.refresh(merged)
            return merged.to_entity()

    async def close_version(self, version_id: UUID, effective_to: date) -> None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormVersionModel).where(NormVersionModel.id == version_id)
            )
            model = result.scalar_one()
            model.effective_to = effective_to
            await session.commit()


@dataclass
class SqlAlchemyNormEmbeddingRepository(BaseNormEmbeddingRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, embedding_id: UUID) -> NormEmbeddingEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormEmbeddingModel).where(NormEmbeddingModel.id == embedding_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_version_id(self, version_id: UUID) -> list[NormEmbeddingEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormEmbeddingModel)
                .where(NormEmbeddingModel.norm_version_id == version_id)
                .order_by(NormEmbeddingModel.chunk_index)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def search_similar(
        self,
        query_embedding: list[float],
        language: LanguageCode,
        limit: int = 10,
        effective_date: Optional[date] = None,
    ) -> list[tuple[NormEmbeddingEntity, float]]:
        async with self._async_sessionmaker() as session:
            query = (
                select(
                    NormEmbeddingModel,
                    (1 - NormEmbeddingModel.embedding.cosine_distance(query_embedding)).label('similarity')
                )
                .join(NormVersionModel)
                .join(NormModel)
                .join(NormTypeModel)
                .options(
                    selectinload(NormEmbeddingModel.norm_version)
                    .selectinload(NormVersionModel.norm)
                    .selectinload(NormModel.npa)
                    .selectinload(NpaModel.npa_type),
                    selectinload(NormEmbeddingModel.norm_version)
                    .selectinload(NormVersionModel.norm)
                    .selectinload(NormModel.norm_type),
                )
                .where(
                    and_(
                        NormVersionModel.language == language.value,
                        NormVersionModel.status == NormStatus.ACTIVE.value,
                        NormTypeModel.is_retrievable == True
                    )
                )
            )

            if effective_date:
                query = query.where(
                    and_(
                        NormVersionModel.effective_from <= effective_date,
                        or_(
                            NormVersionModel.effective_to.is_(None),
                            NormVersionModel.effective_to > effective_date
                        )
                    )
                )
            else:
                query = query.where(NormVersionModel.effective_to.is_(None))

            query = query.order_by(
                NormEmbeddingModel.embedding.cosine_distance(query_embedding)
            ).limit(limit)

            result = await session.execute(query)
            rows = result.all()

            return [(row[0].to_entity(), float(row[1])) for row in rows]

    async def create(self, embedding: NormEmbeddingEntity) -> NormEmbeddingEntity:
        async with self._async_sessionmaker() as session:
            model = NormEmbeddingModel.from_entity(embedding)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def delete_by_version_id(self, version_id: UUID) -> None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(NormEmbeddingModel).where(
                    NormEmbeddingModel.norm_version_id == version_id
                )
            )
            models = result.scalars().all()
            for model in models:
                await session.delete(model)
            await session.commit()


@dataclass
class SqlAlchemyAmendmentRepository(BaseAmendmentRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, amendment_id: UUID) -> AmendmentEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(AmendmentModel)
                .options(
                    selectinload(AmendmentModel.amending_npa),
                    selectinload(AmendmentModel.amended_npa)
                )
                .where(AmendmentModel.id == amendment_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_amending_npa(self, npa_id: UUID) -> list[AmendmentEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(AmendmentModel)
                .options(
                    selectinload(AmendmentModel.amending_npa),
                    selectinload(AmendmentModel.amended_npa)
                )
                .where(AmendmentModel.amending_npa_id == npa_id)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_by_amended_npa(self, npa_id: UUID) -> list[AmendmentEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(AmendmentModel)
                .options(
                    selectinload(AmendmentModel.amending_npa),
                    selectinload(AmendmentModel.amended_npa)
                )
                .where(AmendmentModel.amended_npa_id == npa_id)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, amendment: AmendmentEntity) -> AmendmentEntity:
        async with self._async_sessionmaker() as session:
            model = AmendmentModel.from_entity(amendment)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()


@dataclass
class SqlAlchemyCrossReferenceRepository(BaseCrossReferenceRepository, BaseSqlAlchemyRepository):
    async def get_by_id(self, ref_id: UUID) -> CrossReferenceEntity | None:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(CrossReferenceModel).where(CrossReferenceModel.id == ref_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_outgoing(self, norm_id: UUID) -> list[CrossReferenceEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(CrossReferenceModel)
                .options(
                    selectinload(CrossReferenceModel.source_norm),
                    selectinload(CrossReferenceModel.target_norm)
                )
                .where(CrossReferenceModel.source_norm_id == norm_id)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_incoming(self, norm_id: UUID) -> list[CrossReferenceEntity]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(CrossReferenceModel)
                .options(
                    selectinload(CrossReferenceModel.source_norm),
                    selectinload(CrossReferenceModel.target_norm)
                )
                .where(CrossReferenceModel.target_norm_id == norm_id)
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def create(self, ref: CrossReferenceEntity) -> CrossReferenceEntity:
        async with self._async_sessionmaker() as session:
            model = CrossReferenceModel.from_entity(ref)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()
