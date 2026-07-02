---
name: advance-story
description: Como funciona el flujo de avanzar la historia y el sistema de entity creation
trigger: Cuando se trabaje con StateMachine.advance_story, entity creation, o el 5-tuple de to_core_models
---

# Flujo de advance_story y Entity Creation

## Orden de ejecucion en StateMachine.advance_story()

1. **_apply_entity_creations()** — Crea nuevas entidades (personajes, artifacts, locations)
2. **_apply_entity_deltas()** — Modifica atributos de entidades existentes
3. **_apply_world_deltas()** — Modifica variables globales del mundo
4. **DramaticEngine.apply_delta()** — Actualiza el vector dramatico de 7 dimensiones
5. **DramaticEngine.evaluate_thresholds()** — Evalua si se cruzo un umbral (-> evento forzado)
6. **Crear NarrativeEvent** — Con todos los deltas, creations, y causal_reason
7. **CausalValidator.add_edge()** — Validar que el DAG no tenga ciclos
8. **Crear NarrativeCommit** — Con snapshots de estado completo

**IMPORTANTE**: Entity creation va ANTES de entity deltas para que los deltas puedan referenciar entidades recien creadas en el mismo turno.

## EntityCreation dataclass

```python
@dataclass
class EntityCreation:
    entity_name: str
    entity_type: str  # "character", "faction", "artifact", "location"
    attributes: dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

Archivo: `cne_core/models/event.py`

## Atributos especiales para artifacts/items

```python
{
    "possessed_by": null,    # quien lo tiene (null = disponible en el entorno)
    "location": "altar",     # donde esta
    "usable": true,          # si se puede usar
    "effect": "Abre puertas" # que efecto tiene
}
```

## 5-tuple de to_core_models()

`NarrativeResponse.to_core_models()` retorna exactamente 5 valores:

```python
entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
```

Todos los adapters (mock, anthropic, ollama) hacen unpacking de estos 5 valores en `_convert_to_proposal`.

## go_to_commit y entidades dinamicas

Cuando se navega a un commit anterior con `go_to_commit()`:
- Se ejecuta `self._entities.clear()` — limpia TODAS las entidades
- Se reconstruye completamente desde el snapshot del commit target
- Entidades creadas despues de ese commit NO aparecen
- Se usa el campo `created_at_depth` en el snapshot para reconstruir con `Entity()` constructor

## Persistencia de entity creation

En `NarrativeServiceV2._persist_result()`:
1. Se guarda el evento con `repo.save_event()` (incluye EntityCreationORM records)
2. Se crea un `Entity` object y se persiste con `repo.save_entity(entity, world_id)`

Tabla de auditoria: `entity_creations` (migration 004)
