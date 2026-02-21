"""Test API - API layer tests."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.main import app


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    return MagicMock()


@pytest.fixture
def client(mock_repository):
    """Create a test client with mocked dependencies."""
    app.dependency_overrides[get_repository] = lambda: mock_repository
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_healthy_status(self, client, mock_repository):
        """Test that health endpoint returns healthy status when system is OK."""
        # Setup mock repository
        mock_repository.health_check.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["storage_accessible"] is True

    def test_health_returns_unhealthy_when_storage_fails(self, client, mock_repository):
        """Test that health endpoint returns unhealthy when storage check fails."""
        mock_repository.health_check.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["storage_accessible"] is False


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_returns_aggregated_data(self, client, mock_repository):
        """Test that metrics endpoint returns aggregated metrics."""
        # Setup mock repository with gold data
        gold_df = pd.DataFrame({
            "entity_id": ["entity_1", "entity_2", "entity_3"],
            "date": pd.to_datetime(["2026-02-20", "2026-02-20", "2026-02-21"]),
            "total_value": [100.0, 200.0, 300.0],
        })
        mock_repository.read_gold.return_value = gold_df
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 3
        assert data["entity_count"] == 3

    def test_metrics_handles_empty_gold_layer(self, client, mock_repository):
        """Test that metrics endpoint handles empty gold layer."""
        gold_df = pd.DataFrame()
        mock_repository.read_gold.return_value = gold_df
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 0
        assert data["entity_count"] == 0


class TestGoldDataEndpoint:
    """Test gold data query endpoint."""

    def test_gold_endpoint_returns_data(self, client, mock_repository):
        """Test that gold endpoint returns data."""
        gold_df = pd.DataFrame({
            "entity_id": ["entity_1", "entity_2"],
            "total_value": [100.0, 200.0],
        })
        mock_repository.read_gold.return_value = gold_df
        
        response = client.get("/gold?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["total_available"] == 2
        assert len(data["data"]) == 2

    def test_gold_endpoint_respects_limit(self, client, mock_repository):
        """Test that gold endpoint respects limit parameter."""
        gold_df = pd.DataFrame({
            "entity_id": [f"entity_{i}" for i in range(100)],
            "total_value": [float(i) for i in range(100)],
        })
        mock_repository.read_gold.return_value = gold_df
        
        response = client.get("/gold?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 10
        assert data["total_available"] == 100


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_returns_service_info(self, client):
        """Test that root endpoint returns service information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Energy Data Platform"
        assert "version" in data
        assert data["status"] == "running"
