# Diagrama de Flujo - Causal Narrative Engine

## Flujo Principal del Motor

```mermaid
flowchart TD
    Start([Usuario inicia historia]) --> CreateWorld[Crear WorldDefinition]
    CreateWorld --> |WorldDefinition| InitMachine[StateMachine.__init__]

    InitMachine --> InitComponents[Inicializar Componentes]
    InitComponents --> |dramatic_config| InitDramatic[DramaticEngine]
    InitComponents --> InitCausal[CausalValidator]
    InitComponents --> InitState[Estado en memoria:<br/>entities, world_variables]

    InitDramatic --> CallStart[StateMachine.start]
    InitCausal --> CallStart
    InitState --> CallStart

    CallStart --> CreateInitEvent[Crear NarrativeEvent inicial]
    CreateInitEvent --> |event.id| RegisterEvent[CausalValidator.add_event]
    RegisterEvent --> CreateInitCommit[Crear NarrativeCommit raíz]
    CreateInitCommit --> ReturnStart[Retornar StoryAdvanceResult]

    ReturnStart --> DisplayChoice{Usuario ve<br/>narrativa + opciones}

    DisplayChoice --> |Elige opción| Advance[StateMachine.advance_story]
    DisplayChoice --> |Volver atrás| GoTo[StateMachine.go_to_commit]

    %% ADVANCE STORY FLOW
    Advance --> ApplyEntity[Aplicar EntityDeltas]
    ApplyEntity --> ApplyWorld[Aplicar WorldVariableDeltas]
    ApplyWorld --> ApplyDrama[DramaticEngine.apply_delta]

    ApplyDrama --> ApplyInteractions[Aplicar interacciones<br/>entre medidores]
    ApplyInteractions --> ClampValues[Clampear valores 0-100]
    ClampValues --> EvalThresholds{DramaticEngine<br/>.evaluate_thresholds}

    EvalThresholds --> |Umbral cruzado| ForcedEvent[ForcedEventConstraint]
    EvalThresholds --> |Sin umbral| NoForced[constraint = None]

    ForcedEvent --> CreateEvent[Crear NarrativeEvent]
    NoForced --> CreateEvent

    CreateEvent --> AddEventCausal[CausalValidator.add_event]
    AddEventCausal --> AddEdge[CausalValidator.add_edge<br/>parent → current]

    AddEdge --> CheckCycle{Detectar ciclo<br/>con BFS}
    CheckCycle --> |Ciclo detectado| ThrowError[Lanzar CausalCycleError]
    CheckCycle --> |DAG válido| CreateCommit[Crear NarrativeCommit]

    CreateCommit --> UpdateParent[Parent.add_child]
    UpdateParent --> UpdatePointer[Actualizar current_commit_id]
    UpdatePointer --> ReturnResult[Retornar StoryAdvanceResult]

    ReturnResult --> DisplayChoice

    %% GO TO COMMIT FLOW
    GoTo --> FindCommit{Commit existe?}
    FindCommit --> |No| ErrorNotFound[ValueError]
    FindCommit --> |Sí| RestoreDramatic[Restaurar DramaticVector<br/>desde snapshot]
    RestoreDramatic --> RestoreWorld[Restaurar world_variables]
    RestoreWorld --> RestoreEntities[Restaurar entity_states]
    RestoreEntities --> UpdateCurrent[Actualizar current_commit_id<br/>y depth]
    UpdateCurrent --> ReturnRestore[Retornar StoryAdvanceResult]
    ReturnRestore --> DisplayChoice

    ThrowError --> End([Error])
    ErrorNotFound --> End

    style CreateWorld fill:#e1f5ff
    style InitMachine fill:#e1f5ff
    style DramaticEngine fill:#ffe1f5
    style CausalValidator fill:#ffe1f5
    style ApplyDrama fill:#fff4e1
    style EvalThresholds fill:#fff4e1
    style CheckCycle fill:#e1ffe1
    style CreateCommit fill:#f0e1ff
    style StoryAdvanceResult fill:#ffe1e1
```

## Modelos Principales y sus Relaciones

```mermaid
classDiagram
    class WorldDefinition {
        +str id
        +str name
        +str context
        +NarrativeTone tone
        +list~Entity~ initial_entities
        +dict dramatic_config
        +int max_depth
        +to_context_string()
    }

    class Entity {
        +str id
        +str name
        +EntityType entity_type
        +dict attributes
        +int created_at_depth
        +int destroyed_at_depth
        +is_alive bool
    }

    class NarrativeEvent {
        +str id
        +str commit_id
        +EventType event_type
        +str narrative_text
        +str summary
        +list~str~ caused_by
        +list~EntityDelta~ entity_deltas
        +list~WorldVariableDelta~ world_deltas
        +DramaticDelta dramatic_delta
        +int depth
        +int topo_order
    }

    class NarrativeCommit {
        +str id
        +str world_id
        +str parent_id
        +str event_id
        +str choice_text
        +int depth
        +dict dramatic_snapshot
        +dict world_state_snapshot
        +dict entity_states
        +list~str~ children_ids
        +bool is_ending
    }

    class DramaticVector {
        +int tension
        +int hope
        +int chaos
        +int rhythm
        +int saturation
        +int connection
        +int mystery
        +apply_delta()
        +to_dict()
    }

    class DramaticDelta {
        +int tension
        +int hope
        +int chaos
        +int rhythm
        +int saturation
        +int connection
        +int mystery
    }

    class StateMachine {
        -WorldDefinition world
        -dict~str,Entity~ _entities
        -dict _world_variables
        -CausalValidator _causal_validator
        -DramaticEngine _dramatic_engine
        -dict~str,NarrativeCommit~ _commits
        -str _current_commit_id
        +start()
        +advance_story()
        +go_to_commit()
    }

    class CausalValidator {
        -dict~str,list~ _adjacency
        -set _events
        -list~CausalEdge~ _edges
        +add_event()
        +add_edge()
        +is_dag()
        +get_topo_order()
    }

    class DramaticEngine {
        -DramaticVector vector
        -list _history
        +apply_delta()
        +evaluate_thresholds()
        +get_dramatic_summary()
    }

    WorldDefinition "1" --> "*" Entity : initial_entities
    WorldDefinition "1" --> "1" StateMachine : inicializa

    StateMachine "1" --> "1" CausalValidator : mantiene
    StateMachine "1" --> "1" DramaticEngine : mantiene
    StateMachine "1" --> "*" NarrativeCommit : gestiona
    StateMachine "1" --> "*" NarrativeEvent : crea

    NarrativeEvent "1" --> "1" DramaticDelta : contiene
    NarrativeEvent "1" --> "1" NarrativeCommit : pertenece

    NarrativeCommit "1" --> "1" DramaticVector : snapshot
    NarrativeCommit "1" --> "0..1" NarrativeCommit : parent
    NarrativeCommit "1" --> "*" NarrativeCommit : children

    DramaticEngine "1" --> "1" DramaticVector : mantiene
    DramaticEngine --> DramaticDelta : procesa

    CausalValidator --> NarrativeEvent : valida
```

## Secuencia de Ejecución Completa

```mermaid
sequenceDiagram
    actor Usuario
    participant WD as WorldDefinition
    participant SM as StateMachine
    participant CV as CausalValidator
    participant DE as DramaticEngine
    participant NE as NarrativeEvent
    participant NC as NarrativeCommit

    %% INICIO
    Usuario->>WD: Crear semilla del mundo
    Usuario->>SM: new StateMachine(world)
    SM->>CV: new CausalValidator()
    SM->>DE: new DramaticEngine(config)

    Usuario->>SM: start(narrative, choices)
    SM->>NE: Crear evento inicial
    SM->>CV: add_event(event.id)
    CV-->>SM: topo_order
    SM->>NC: Crear commit raíz
    SM-->>Usuario: StoryAdvanceResult

    %% DECISIÓN DEL JUGADOR
    Usuario->>SM: advance_story(choice, narrative, deltas)

    Note over SM: 1. Aplicar deltas de entidades
    SM->>SM: _apply_entity_deltas()

    Note over SM: 2. Aplicar deltas de mundo
    SM->>SM: _apply_world_deltas()

    Note over SM: 3. Actualizar vector dramático
    SM->>DE: apply_delta(dramatic_delta)
    DE->>DE: apply_interactions()
    DE->>DE: clamp_values()

    Note over SM: 4. Evaluar umbrales
    SM->>DE: evaluate_thresholds()
    alt Umbral cruzado
        DE-->>SM: ForcedEventConstraint
    else Sin umbral
        DE-->>SM: None
    end

    Note over SM: 5. Crear evento narrativo
    SM->>NE: new NarrativeEvent(deltas)

    Note over SM: 6. Validar causalidad
    SM->>CV: add_event(event.id)
    SM->>CV: add_edge(parent_id, event.id)

    CV->>CV: _find_path(event.id, parent_id)
    alt Existe camino (ciclo)
        CV-->>SM: CausalCycleError
        SM-->>Usuario: Error
    else No hay ciclo (DAG válido)
        CV-->>SM: CausalEdge creada

        Note over SM: 7. Crear nuevo commit
        SM->>NC: new NarrativeCommit()
        NC->>NC: Guardar snapshots
        SM->>SM: Actualizar punteros
        SM-->>Usuario: StoryAdvanceResult
    end

    %% NAVEGACIÓN
    Usuario->>SM: go_to_commit(commit_id)
    SM->>NC: Obtener commit
    SM->>DE: Restaurar vector desde snapshot
    SM->>SM: Restaurar estado del mundo
    SM-->>Usuario: StoryAdvanceResult
```

## Flujo de Validación Causal (Detección de Ciclos)

```mermaid
flowchart TD
    AddEdge[add_edge parent→child] --> CheckExists{Eventos<br/>existen?}
    CheckExists --> |No| EventNotFound[EventNotFoundError]
    CheckExists --> |Sí| CheckDuplicate{Arista ya<br/>existe?}

    CheckDuplicate --> |Sí| ReturnExisting[Retornar arista existente]
    CheckDuplicate --> |No| FindPath[_find_path<br/>child → parent<br/>usando BFS]

    FindPath --> BFSInit[Iniciar BFS desde child]
    BFSInit --> BFSQueue{Queue vacía?}

    BFSQueue --> |No| PopNode[Dequeue nodo actual]
    PopNode --> CheckTarget{Nodo == parent?}

    CheckTarget --> |Sí| CycleFound[Ciclo detectado!<br/>Camino encontrado]
    CheckTarget --> |No| GetNeighbors[Obtener vecinos<br/>de adjacency]

    GetNeighbors --> AddQueue[Añadir no-visitados<br/>a queue]
    AddQueue --> BFSQueue

    BFSQueue --> |Sí| NoCycle[No hay camino<br/>child → parent]

    CycleFound --> ThrowCycle[Lanzar CausalCycleError<br/>con camino del ciclo]
    NoCycle --> SafeAdd[Añadir a adjacency]
    SafeAdd --> CreateEdge[Crear CausalEdge]
    CreateEdge --> UpdateTopo[Actualizar topo_order]
    UpdateTopo --> ReturnEdge[Retornar arista]

    style FindPath fill:#e1ffe1
    style BFSInit fill:#e1ffe1
    style CycleFound fill:#ffe1e1
    style NoCycle fill:#e1f5ff
    style SafeAdd fill:#e1f5ff
```

## Flujo de Evaluación Dramática (Sistema SDMM)

```mermaid
flowchart TD
    ApplyDelta[apply_delta<br/>DramaticDelta] --> AddDirectDeltas[Sumar deltas directos<br/>a cada medidor]

    AddDirectDeltas --> CheckTension{tension > 50?}
    CheckTension --> |Sí| ErodeHope[hope -= tension-50 // 10 × 2]
    CheckTension --> |No| CheckChaos
    ErodeHope --> CheckChaos

    CheckChaos{chaos > 60?} --> |Sí| BoostRhythm[rhythm += chaos-60 // 10]
    CheckChaos --> |No| CheckSat
    BoostRhythm --> CheckSat

    CheckSat{saturation > 70?} --> |Sí| LoseConnection[connection -= saturation-70 // 5]
    CheckSat --> |No| CheckLowHope
    LoseConnection --> CheckLowHope

    CheckLowHope{hope < 20?} --> |Sí| AddMystery[mystery += 3]
    CheckLowHope --> |No| Clamp
    AddMystery --> Clamp

    Clamp[Clampear todos<br/>los valores 0-100] --> UpdateCounter{rhythm > 70?}
    UpdateCounter --> |Sí| IncTurns[_high_rhythm_turns++]
    UpdateCounter --> |No| ResetTurns[_high_rhythm_turns = 0]

    IncTurns --> SaveHistory[Guardar en _history]
    ResetTurns --> SaveHistory
    SaveHistory --> EvalThresholds

    EvalThresholds[evaluate_thresholds] --> Priority1{Combinaciones}

    Priority1 --> CheckMysteryTension{mystery>65<br/>AND<br/>tension>65?}
    CheckMysteryTension --> |Sí| ClimaxRev[CLIMAX_REVELATION]
    CheckMysteryTension --> |No| CheckConnTension

    CheckConnTension{connection>70<br/>AND<br/>tension>60?} --> |Sí| EmotMoment[EMOTIONAL_MOMENT]
    CheckConnTension --> |No| Priority2

    Priority2{Umbrales individuales} --> CheckSat95{saturation>95?}
    CheckSat95 --> |Sí| ArcClose[ARC_CLOSURE]
    CheckSat95 --> |No| CheckTens85

    CheckTens85{tension>85?} --> |Sí| Climax[CLIMAX]
    CheckTens85 --> |No| CheckHope10

    CheckHope10{hope<10?} --> |Sí| Tragedy[TRAGEDY]
    CheckHope10 --> |No| CheckChaos80

    CheckChaos80{chaos>80?} --> |Sí| ChaosStorm[CHAOS_STORM]
    CheckChaos80 --> |No| CheckSat85

    CheckSat85{saturation>85?} --> |Sí| PlotTwist[PLOT_TWIST]
    CheckSat85 --> |No| CheckTens15

    CheckTens15{tension<15?} --> |Sí| Disruptive[DISRUPTIVE]
    CheckTens15 --> |No| CheckHope90

    CheckHope90{hope>90?} --> |Sí| UnexpThreat[UNEXPECTED_THREAT]
    CheckHope90 --> |No| CheckRhythm90

    CheckRhythm90{rhythm>90<br/>AND<br/>turns>=3?} --> |Sí| NarrRest[NARRATIVE_REST]
    CheckRhythm90 --> |No| NoConstraint[return None]

    ClimaxRev --> ReturnConstraint[return ForcedEventConstraint]
    EmotMoment --> ReturnConstraint
    ArcClose --> ReturnConstraint
    Climax --> ReturnConstraint
    Tragedy --> ReturnConstraint
    ChaosStorm --> ReturnConstraint
    PlotTwist --> ReturnConstraint
    Disruptive --> ReturnConstraint
    UnexpThreat --> ReturnConstraint
    NarrRest --> ReturnConstraint

    style ApplyDelta fill:#fff4e1
    style Clamp fill:#e1f5ff
    style EvalThresholds fill:#ffe1f5
    style ReturnConstraint fill:#ffe1e1
    style NoConstraint fill:#e1ffe1
```

## Resumen de Componentes por Fase

| Componente | Responsabilidad | Modelos que usa | Modelos que produce |
|------------|----------------|-----------------|---------------------|
| **WorldDefinition** | Semilla inmutable del universo narrativo | Entity, dramatic_config | - |
| **StateMachine** | Orquestador central | WorldDefinition, Entity, NarrativeEvent, NarrativeCommit | StoryAdvanceResult |
| **CausalValidator** | Garantizar DAG sin ciclos | NarrativeEvent.id, CausalEdge | topo_order, estadísticas DAG |
| **DramaticEngine** | Gestionar vector dramático y umbrales | DramaticDelta, DramaticVector | ForcedEventConstraint (o None) |
| **NarrativeEvent** | Unidad atómica de la historia | EntityDelta, WorldVariableDelta, DramaticDelta | - |
| **NarrativeCommit** | Punto versionado (como Git) | NarrativeEvent, snapshots del estado | - |
| **StoryAdvanceResult** | Respuesta del motor al cliente | NarrativeCommit, DramaticVector, NarrativeChoice | - |

---

**Propiedad Invariante Clave**: El grafo de eventos es SIEMPRE un DAG. Esto garantiza:
- ✅ Reconstrucción determinista del estado
- ✅ Sin paradojas causales (A causa A)
- ✅ Orden topológico válido
- ✅ Navegación hacia atrás coherente
