---
name: sdmm
description: Sistema Dramatico Multi-Medidor — los 7 medidores, interacciones, y umbrales
trigger: Cuando se trabaje con DramaticEngine, vectores dramaticos, eventos forzados, o umbrales
---

# Sistema Dramatico Multi-Medidor (SDMM)

Innovacion central del proyecto. Reemplaza "vida del arbol" con un vector formal de 7 dimensiones.

## Los 7 Medidores

| Medidor | Rango | Inicio | Que mide |
|---------|-------|--------|----------|
| `tension` | [0-100] | 30 | Nivel de conflicto activo |
| `hope` | [0-100] | 60 | Percepcion de que las cosas pueden mejorar |
| `chaos` | [0-100] | 20 | Entropia del mundo, eventos impredecibles |
| `rhythm` | [0-100] | 50 | Velocidad narrativa |
| `saturation` | [0-100] | 0 | Agotamiento del arco actual |
| `connection` | [0-100] | 40 | Profundidad emocional con personajes |
| `mystery` | [0-100] | 50 | Preguntas sin resolver |

## Interacciones automaticas (se aplican despues de cada delta)

```
tension > 50     ->  hope -= ((tension - 50) // 10) * 2
chaos > 60       ->  rhythm += (chaos - 60) // 10
saturation > 70  ->  connection -= (saturation - 70) // 5
hope < 20        ->  mystery += 3
```

Todos los valores se clampean a [0, 100] despues de aplicar interacciones.

## Umbrales -> Eventos Forzados (Phi)

### Prioridad 1: Combinaciones
```
mystery > 65 AND tension > 65    ->  CLIMAX_REVELATION
connection > 70 AND tension > 60 ->  EMOTIONAL_MOMENT
```

### Prioridad 2: Individuales
```
saturation > 95                  ->  ARC_CLOSURE
tension > 85                     ->  CLIMAX
hope < 10                        ->  TRAGEDY
chaos > 80                       ->  CHAOS_STORM
saturation > 85                  ->  PLOT_TWIST
tension < 15                     ->  DISRUPTIVE
hope > 90                        ->  UNEXPECTED_THREAT
rhythm > 90 (x3 turnos seguidos) ->  NARRATIVE_REST
```

## Como funciona un evento forzado

1. `DramaticEngine.evaluate_thresholds()` retorna `ForcedEventConstraint | None`
2. Si hay constraint, se incluye en el `NarrativeContext` para la IA
3. La IA recibe un **constraint obligatorio** en el system prompt
4. El evento forzado se integra causalmente al DAG — no es una interrupcion externa, sino consecuencia formal de los eventos que elevaron el medidor

## Archivos clave

- `cne_core/engine/dramatic_engine.py` — `DramaticEngine`, `DramaticVector`, `ForcedEventConstraint`, `ForcedEventType`
- `cne_core/models/event.py` — `DramaticDelta` (los deltas que cada evento aplica)
- `cne_core/ai/context_builder.py` — Como se presenta el estado dramatico a la IA

## DramaticDelta

```python
@dataclass
class DramaticDelta:
    tension: int = 0
    hope: int = 0
    chaos: int = 0
    rhythm: int = 0
    saturation: int = 0
    connection: int = 0
    mystery: int = 0
```

Cada evento narrativo puede incluir un `DramaticDelta` que modifica el vector. El motor aplica las interacciones automaticas despues.
