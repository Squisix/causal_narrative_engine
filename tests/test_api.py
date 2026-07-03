"""
tests/test_api.py - REST API Tests

Uses httpx.AsyncClient to test endpoints with correct async.
Requires PostgreSQL running (docker-compose up -d).

Run:
    pytest tests/test_api.py -v
"""

import pytest
import httpx
from httpx import ASGITransport

from api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _create_world(client, **overrides):
    """Helper: creates a world and returns (world_id, response_data)."""
    data = {
        "name": "Test World",
        "context": "A medieval kingdom for testing",
        "protagonist": "The hero",
        "era": "Medieval",
        "tone": "dark",
        "antagonist": "Villain",
        "rules": "Basic rules",
        "constraints": ["No magic"],
        "max_depth": 20,
    }
    data.update(overrides)
    r = await client.post("/worlds", json=data)
    assert r.status_code == 201, f"create_world failed: {r.text}"
    body = r.json()
    return body["world_id"], body


async def _start_narrative(client, world_id, adapter_type="mock"):
    """Helper: starts narrative and returns response."""
    r = await client.post(
        f"/worlds/{world_id}/start",
        json={"adapter_type": adapter_type, "adapter_config": {"deterministic": True, "seed": 42}},
    )
    assert r.status_code == 201, f"start_narrative failed: {r.text}"
    return r.json()


async def _cleanup_world(client, world_id):
    """Helper: deletes a world."""
    await client.delete(f"/worlds/{world_id}")


# -- Health & root --

@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    r = await client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "Causal Narrative Engine API"


# -- World CRUD --

@pytest.mark.asyncio
async def test_create_world(client):
    world_id, data = await _create_world(client, name="API Test World")
    assert world_id is not None
    assert data["name"] == "API Test World"
    assert data["tone"] == "dark"
    assert data["total_commits"] == 0
    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_create_world_with_entities(client):
    world_id, data = await _create_world(
        client,
        name="World with entities",
        initial_entities=[
            {"name": "Kael", "entity_type": "character", "attributes": {"health": 100}},
            {"name": "Fortaleza", "entity_type": "location", "attributes": {"danger": 50}},
        ],
    )
    assert data["name"] == "World with entities"
    r = await client.get(f"/worlds/{world_id}")
    assert r.status_code == 200
    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_get_world(client):
    world_id, _ = await _create_world(client)
    r = await client.get(f"/worlds/{world_id}")
    assert r.status_code == 200
    assert r.json()["world_id"] == world_id
    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_get_nonexistent_world(client):
    r = await client.get("/worlds/nonexistent-id")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_world(client):
    world_id, _ = await _create_world(client)
    r = await client.delete(f"/worlds/{world_id}")
    assert r.status_code == 204
    r = await client.get(f"/worlds/{world_id}")
    assert r.status_code == 404


# -- Narrative flow --

@pytest.mark.asyncio
async def test_start_narrative(client):
    world_id, _ = await _create_world(client)
    data = await _start_narrative(client, world_id)

    assert data["depth"] == 0
    assert len(data["narrative_text"]) > 50
    assert len(data["choices"]) >= 2
    assert "dramatic_state" in data
    assert data["dramatic_state"]["tension"] > 0

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_advance_narrative(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    commit_id = start["commit_id"]
    choice_text = start["choices"][0]["text"]

    r = await client.post(
        f"/commits/{commit_id}/advance",
        json={"choice": choice_text, "adapter_type": "mock"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["depth"] == 1
    assert data["commit_id"] != commit_id
    assert data["parent_id"] == commit_id

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_advance_with_custom_choice(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    commit_id = start["commit_id"]

    r = await client.post(
        f"/commits/{commit_id}/advance",
        json={"choice": "I do something totally unexpected", "custom": True, "adapter_type": "mock"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["depth"] == 1

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_get_commit(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    commit_id = start["commit_id"]

    r = await client.get(f"/commits/{commit_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["commit_id"] == commit_id
    assert "narrative_text" in data
    assert "choices" in data

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_get_dramatic_state(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)

    r = await client.get(f"/commits/{start['commit_id']}/dramatic")
    assert r.status_code == 200
    data = r.json()
    assert "tension" in data
    assert "hope" in data
    assert 0 <= data["tension"] <= 100
    assert 0 <= data["hope"] <= 100

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_causal_reason_in_response(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)

    assert "causal_reason" in start
    assert start["causal_reason"] is not None

    # Advance and check causal_reason on the second commit too
    choice_text = start["choices"][0]["text"]
    r = await client.post(
        f"/commits/{start['commit_id']}/advance",
        json={"choice": choice_text, "adapter_type": "mock"},
    )
    data = r.json()
    assert data["causal_reason"] is not None
    assert len(data["causal_reason"]) > 10

    await _cleanup_world(client, world_id)


# -- Navigation --

@pytest.mark.asyncio
async def test_list_commits(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    choice_text = start["choices"][0]["text"]
    await client.post(
        f"/commits/{start['commit_id']}/advance",
        json={"choice": choice_text, "adapter_type": "mock"},
    )

    r = await client.get(f"/worlds/{world_id}/commits")
    assert r.status_code == 200
    commits = r.json()
    assert len(commits) == 2
    assert commits[0]["depth"] == 0
    assert commits[1]["depth"] == 1

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_goto_commit(client):
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    commit0_id = start["commit_id"]
    choice_text = start["choices"][0]["text"]

    r = await client.post(
        f"/commits/{commit0_id}/advance",
        json={"choice": choice_text, "adapter_type": "mock"},
    )
    commit1_id = r.json()["commit_id"]

    # Go back to commit 0
    r = await client.post(f"/commits/{commit0_id}/goto")
    assert r.status_code == 200
    data = r.json()
    assert data["commit_id"] == commit0_id
    assert data["depth"] == 0

    await _cleanup_world(client, world_id)


@pytest.mark.asyncio
async def test_existing_paths(client):
    """Advance twice from same commit -> existing_paths should show both children."""
    world_id, _ = await _create_world(client)
    start = await _start_narrative(client, world_id)
    commit0_id = start["commit_id"]

    # Advance with first choice
    choice1 = start["choices"][0]["text"]
    await client.post(
        f"/commits/{commit0_id}/advance",
        json={"choice": choice1, "adapter_type": "mock"},
    )

    # Go back and get commit0 - should show existing path
    r = await client.get(f"/commits/{commit0_id}")
    data = r.json()
    assert len(data["existing_paths"]) >= 1
    assert data["existing_paths"][0]["choice_text"] == choice1

    await _cleanup_world(client, world_id)


# -- Full flow --

@pytest.mark.asyncio
async def test_full_narrative_flow_3_chapters(client):
    world_id, _ = await _create_world(
        client,
        name="Full Flow Test",
        initial_entities=[
            {"name": "Hero", "entity_type": "character", "attributes": {"health": 100}},
        ],
    )
    start = await _start_narrative(client, world_id)

    commit_id = start["commit_id"]
    for depth in range(1, 4):
        r = await client.get(f"/commits/{commit_id}")
        choices = r.json()["choices"]
        assert len(choices) >= 2, f"No choices at depth {depth - 1}"

        r = await client.post(
            f"/commits/{commit_id}/advance",
            json={"choice": choices[0]["text"], "adapter_type": "mock"},
        )
        assert r.status_code == 201, f"Advance failed at depth {depth}: {r.json()}"
        data = r.json()
        assert data["depth"] == depth
        commit_id = data["commit_id"]

    # Verify final state
    r = await client.get(f"/worlds/{world_id}/commits")
    commits = r.json()
    assert len(commits) == 4

    await _cleanup_world(client, world_id)
