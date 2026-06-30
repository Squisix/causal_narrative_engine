"""
tests/test_api.py - Tests de la API REST

Usa FastAPI TestClient para probar los endpoints sin levantar servidor.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Cliente de prueba de FastAPI."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test: GET /health retorna status ok."""
    print("\n[TEST] GET /health")

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.3.0"
    assert "timestamp" in data
    assert data["ai_adapter"] == "mock"

    print(f"  [OK] Health check: {data['status']}")
    print(f"  [OK] Version: {data['version']}")


def test_root_endpoint(client):
    """Test: GET / retorna info básica."""
    print("\n[TEST] GET /")

    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Causal Narrative Engine API"
    assert data["version"] == "0.3.0"
    assert data["docs"] == "/docs"

    print(f"  [OK] Root endpoint works")


def test_create_world(client):
    """Test: POST /worlds crea un mundo."""
    print("\n[TEST] POST /worlds")

    world_data = {
        "name": "Reino de Prueba",
        "context": "Un reino medieval para testing de API",
        "protagonist": "Héroe de prueba",
        "era": "Medieval",
        "tone": "dark",
        "antagonist": "Villano genérico",
        "rules": "Reglas básicas",
        "constraints": ["No magia"],
        "max_depth": 10
    }

    response = client.post("/worlds", json=world_data)

    assert response.status_code == 201

    data = response.json()
    assert "world_id" in data
    assert data["name"] == "Reino de Prueba"
    assert data["tone"] == "oscuro"  # El enum devuelve el valor en español
    assert data["total_commits"] == 0

    print(f"  [OK] World created: {data['world_id'][:8]}")
    print(f"  [OK] Name: {data['name']}")

    return data["world_id"]


def test_get_world(client):
    """Test: GET /worlds/{world_id} obtiene un mundo."""
    print("\n[TEST] GET /worlds/{world_id}")

    # Crear mundo primero
    world_id = test_create_world(client)

    # Obtener mundo
    response = client.get(f"/worlds/{world_id}")

    assert response.status_code == 200

    data = response.json()
    assert data["world_id"] == world_id
    assert data["name"] == "Reino de Prueba"

    print(f"  [OK] World retrieved: {data['world_id'][:8]}")


def test_get_nonexistent_world(client):
    """Test: GET /worlds/{id} retorna 404 si no existe."""
    print("\n[TEST] GET /worlds/{invalid_id} -> 404")

    response = client.get("/worlds/nonexistent-id-123")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data

    print(f"  [OK] 404 returned for nonexistent world")


def test_start_narrative_with_mock(client):
    """Test: POST /worlds/{id}/start inicia narrativa con MockAdapter."""
    print("\n[TEST] POST /worlds/{id}/start (MockAdapter)")

    # Crear mundo
    world_id = test_create_world(client)

    # Iniciar narrativa
    request_data = {
        "adapter_type": "mock",
        "adapter_config": {
            "deterministic": True,
            "seed": 42
        }
    }

    response = client.post(f"/worlds/{world_id}/start", json=request_data)

    assert response.status_code == 201

    data = response.json()
    assert "commit_id" in data
    assert data["depth"] == 0
    assert len(data["narrative_text"]) > 50
    assert len(data["choices"]) >= 2
    assert "dramatic_state" in data

    print(f"  [OK] Narrative started: {data['commit_id'][:8]}")
    print(f"  [OK] Narrative length: {len(data['narrative_text'])} chars")
    print(f"  [OK] Choices: {len(data['choices'])}")

    return data["commit_id"]


def test_advance_narrative(client):
    """Test: POST /commits/{id}/advance avanza la narrativa."""
    print("\n[TEST] POST /commits/{id}/advance")

    # Iniciar narrativa
    commit_id = test_start_narrative_with_mock(client)

    # Obtener commit para ver las choices
    response = client.get(f"/commits/{commit_id}")
    choices = response.json()["choices"]
    chosen_text = choices[0]["text"]

    # Avanzar narrativa
    advance_data = {
        "choice": chosen_text
    }

    response = client.post(f"/commits/{commit_id}/advance", json=advance_data)

    assert response.status_code == 201

    data = response.json()
    assert "commit_id" in data
    assert data["commit_id"] != commit_id  # Nuevo commit
    assert data["depth"] == 1  # Profundidad incrementada
    assert len(data["narrative_text"]) > 50

    print(f"  [OK] Narrative advanced: {data['commit_id'][:8]}")
    print(f"  [OK] New depth: {data['depth']}")


def test_get_commit(client):
    """Test: GET /commits/{id} obtiene un commit."""
    print("\n[TEST] GET /commits/{id}")

    # Crear narrativa
    commit_id = test_start_narrative_with_mock(client)

    # Obtener commit
    response = client.get(f"/commits/{commit_id}")

    assert response.status_code == 200

    data = response.json()
    assert data["commit_id"] == commit_id
    assert "narrative_text" in data
    assert "choices" in data

    print(f"  [OK] Commit retrieved: {data['commit_id'][:8]}")


def test_get_dramatic_state(client):
    """Test: GET /commits/{id}/dramatic obtiene estado dramático."""
    print("\n[TEST] GET /commits/{id}/dramatic")

    # Crear narrativa
    commit_id = test_start_narrative_with_mock(client)

    # Obtener estado dramático
    response = client.get(f"/commits/{commit_id}/dramatic")

    assert response.status_code == 200

    data = response.json()
    assert "tension" in data
    assert "hope" in data
    assert "chaos" in data
    assert 0 <= data["tension"] <= 100
    assert 0 <= data["hope"] <= 100

    print(f"  [OK] Dramatic state: T={data['tension']}, H={data['hope']}, C={data['chaos']}")


def test_delete_world(client):
    """Test: DELETE /worlds/{id} elimina un mundo."""
    print("\n[TEST] DELETE /worlds/{id}")

    # Crear mundo
    world_id = test_create_world(client)

    # Eliminar mundo
    response = client.delete(f"/worlds/{world_id}")

    assert response.status_code == 204

    # Verificar que ya no existe
    response = client.get(f"/worlds/{world_id}")
    assert response.status_code == 404

    print(f"  [OK] World deleted successfully")


def test_full_narrative_flow(client):
    """Test: Flujo completo de narrativa (crear mundo -> iniciar -> avanzar x3)."""
    print("\n[TEST] Flujo completo de narrativa")

    # 1. Crear mundo
    world_data = {
        "name": "Historia de Prueba Completa",
        "context": "Un mundo para probar el flujo completo",
        "protagonist": "El protagonista",
        "era": "Fantástico",
        "tone": "adventurous",
    }

    response = client.post("/worlds", json=world_data)
    assert response.status_code == 201
    world_id = response.json()["world_id"]

    print(f"  [1] World created: {world_id[:8]}")

    # 2. Iniciar narrativa
    response = client.post(
        f"/worlds/{world_id}/start",
        json={"adapter_type": "mock"}
    )
    assert response.status_code == 201
    commit_id = response.json()["commit_id"]

    print(f"  [2] Narrative started: {commit_id[:8]}")

    # 3. Avanzar 3 veces
    for i in range(3):
        # Obtener choices
        response = client.get(f"/commits/{commit_id}")
        choices = response.json()["choices"]
        chosen_text = choices[0]["text"]

        # Avanzar
        response = client.post(
            f"/commits/{commit_id}/advance",
            json={"choice": chosen_text}
        )
        assert response.status_code == 201
        commit_id = response.json()["commit_id"]

        print(f"  [{i+3}] Advanced to depth {i+1}: {commit_id[:8]}")

    print(f"  [OK] Full flow completed successfully")


if __name__ == "__main__":
    print("=== Tests de API REST ===\n")

    # Crear cliente
    client = TestClient(app)

    # Ejecutar tests
    test_health_endpoint(client)
    test_root_endpoint(client)
    test_create_world(client)
    test_get_world(client)
    test_get_nonexistent_world(client)
    test_start_narrative_with_mock(client)
    test_advance_narrative(client)
    test_get_commit(client)
    test_get_dramatic_state(client)
    test_delete_world(client)
    test_full_narrative_flow(client)

    print("\n[SUCCESS] Todos los tests de API pasaron")
