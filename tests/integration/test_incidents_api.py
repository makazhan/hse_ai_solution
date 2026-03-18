"""Интеграционные тесты эндпоинтов инцидентов.

Тесты, требующие БД, помечены @pytest.mark.skipif(not HAS_DB) и
пропускаются при отсутствии реального подключения.
"""
import os

import pytest
from httpx import AsyncClient
from fastapi import status

from src.presentation.api.main import create_app

# Считаем, что БД доступна, если задана переменная окружения
HAS_DB = bool(os.environ.get("DATABASE_URL"))


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DB, reason="Нет подключения к БД")
async def test_create_incident_endpoint():
    """POST /api/v1/incidents — создание инцидента (требует БД)"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/incidents",
            json={
                "incident_date": "2024-01-15",
                "company": "АО «Казахтелеком»",
                "classification": "Несчастный случай (согласно Трудовому кодексу РК)",
                "region": "Алматы",
                "location": "Офис",
                "description": "Тестовый инцидент",
            }
        )

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DB, reason="Нет подключения к БД")
async def test_get_incidents_endpoint():
    """GET /api/v1/incidents — получение списка (требует БД)"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/incidents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DB, reason="Нет подключения к БД")
async def test_create_incident_with_invalid_company():
    """POST с невалидным значением компании → 422"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/incidents",
            json={
                "incident_date": "2024-01-15",
                "company": "Invalid Company Name",
                "classification": "Несчастный случай (согласно Трудовому кодексу РК)",
                "region": "Алматы",
                "location": "Офис",
                "description": "Тестовый инцидент",
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
