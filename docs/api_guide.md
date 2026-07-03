# CNE REST API Guide

This guide details all HTTP endpoints available in the CNE REST API to manage worlds, advance branching stories, and inspect the dramatic and causal states.

## Base URL
Default: `http://localhost:8000`

---

## Endpoints

### 1. Create World Seed
Registers an immutable world definition (genre, rules, tone, constraints, and protagonist).
- **HTTP Method**: `POST`
- **Path**: `/worlds`
- **Request Body (JSON)**:
```json
{
  "name": "Reino de Valdris",
  "context": "Un reino medieval al borde de la guerra. El rey ha muerto misteriosamente.",
  "protagonist": "Lyra, the princess",
  "era": "Medieval, year 843",
  "tone": "dark",
  "antagonist": "Malachar",
  "rules": "Magic requires a blood price",
  "constraints": ["No time travel"],
  "output_language": "es",
  "dramatic_config": {
    "tension": 30,
    "hope": 60,
    "chaos": 20,
    "rhythm": 50,
    "saturation": 0,
    "connection": 40,
    "mystery": 50
  }
}
```
- **Response**: `201 Created` with full world metadata (including generated `world_id`).

### 2. Retrieve World Metadata
- **HTTP Method**: `GET`
- **Path**: `/worlds/{world_id}`
- **Response**: `200 OK` with world properties and statistics (total commits, active branches).

### 3. Start Narrative Session
Initializes the root commit of a narrative on a world seed.
- **HTTP Method**: `POST`
- **Path**: `/worlds/{world_id}/start`
- **Request Body (JSON)**:
```json
{
  "adapter_type": "mock",
  "adapter_config": {
    "deterministic": true,
    "seed": 42
  }
}
```
- **Response**: `200 OK` returning the root commit response.

### 4. Advance Story (Decision Point)
Advances the story forward by submitting a choice.
- **HTTP Method**: `POST`
- **Path**: `/commits/{commit_id}/advance`
- **Request Body (JSON)**:
```json
{
  "choice": "Confront Malachar directly",
  "custom": false,
  "adapter_type": "mock"
}
```
- **Response**: `200 OK` with the child commit state, including generated narrative, summary, new choices, and the updated dramatic snapshot.

### 5. Jump to Commit (Rewind)
Rewinds the narrative tree to an existing branch or parent commit.
- **HTTP Method**: `POST`
- **Path**: `/commits/{commit_id}/goto`
- **Response**: `200 OK` returning the state snapshot of the jumped commit.

### 6. Delete World
Clears a world and permanently deletes all narrative branches.
- **HTTP Method**: `DELETE`
- **Path**: `/worlds/{world_id}`
- **Response**: `204 No Content`

### 7. Health Check
- **HTTP Method**: `GET`
- **Path**: `/health`
- **Response**: `200 OK` with version and service statuses (database, cache, AI adapter).
