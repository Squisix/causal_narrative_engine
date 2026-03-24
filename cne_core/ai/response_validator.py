"""
cne_core/ai/response_validator.py - Validacion de respuestas de IA

El ResponseValidator verifica que las respuestas generadas por la IA
cumplan las propiedades P1-P4 del motor antes de aplicarlas:

P1 - CAUSALIDAD: No crear ciclos, eventos bien conectados
P2 - DETERMINISMO: Estados reconstruibles
P3 - VERSIONADO: Metadata correcta
P4 - CONSISTENCIA: Entidades muertas no actuan, valores en rango

Si una respuesta falla validacion, se rechaza y se puede:
- Pedir a la IA que la regenere
- Aplicar fallbacks seguros
- Loguear el error para mejorar el prompt
"""

from typing import Any, Optional
from dataclasses import dataclass

from cne_core.ai.response_schema import NarrativeResponse
from cne_core.models.world import WorldDefinition


@dataclass
class ValidationResult:
    """
    Resultado de validar una respuesta de IA.

    Si is_valid=False, errors contiene la lista de problemas encontrados.
    """
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def __str__(self) -> str:
        if self.is_valid:
            warnings_str = f" ({len(self.warnings)} warnings)" if self.warnings else ""
            return f"[VALID]{warnings_str}"
        else:
            return f"[INVALID] {len(self.errors)} errors: {'; '.join(self.errors[:3])}"


class ResponseValidator:
    """
    Valida que las respuestas de la IA sean coherentes y seguras.

    Realiza validaciones en dos niveles:
    1. Validacion de schema (Pydantic lo hace automaticamente)
    2. Validacion de coherencia narrativa (este validator)
    """

    def __init__(
        self,
        world: WorldDefinition,
        current_entities: dict[str, Any],
        current_world_vars: dict[str, Any],
    ):
        """
        Args:
            world: La semilla del mundo (define las reglas).
            current_entities: Estado actual de las entidades.
            current_world_vars: Estado actual de las variables del mundo.
        """
        self.world = world
        self.current_entities = current_entities
        self.current_world_vars = current_world_vars

    def validate(self, response: NarrativeResponse) -> ValidationResult:
        """
        Valida una respuesta completa de la IA.

        Args:
            response: La respuesta parseada (ya paso validacion de Pydantic).

        Returns:
            ValidationResult indicando si es valida y que errores hay.
        """
        errors = []
        warnings = []

        # V1: Validar entity deltas
        entity_errors = self._validate_entity_deltas(response.entity_deltas)
        errors.extend(entity_errors)

        # V2: Validar dramatic deltas
        dramatic_errors = self._validate_dramatic_deltas(response.dramatic_deltas)
        errors.extend(dramatic_errors)

        # V3: Validar coherencia narrativa
        narrative_warnings = self._validate_narrative_coherence(response)
        warnings.extend(narrative_warnings)

        # V4: Validar choices
        choice_errors = self._validate_choices(response)
        errors.extend(choice_errors)

        # V5: Validar que respete constraints del mundo
        constraint_errors = self._validate_world_constraints(response)
        errors.extend(constraint_errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_entity_deltas(self, entity_deltas: list) -> list[str]:
        """
        Valida que los deltas de entidades sean coherentes.

        P4: Las entidades muertas no pueden actuar.
        """
        errors = []

        for delta in entity_deltas:
            entity_id = delta.entity_id
            entity_name = delta.entity_name

            # Verificar que la entidad exista
            if entity_id not in self.current_entities:
                # Podria ser una entidad nueva que se crea en este evento
                # Por ahora, solo advertencia
                continue

            entity_state = self.current_entities[entity_id]

            # CRITICO: Entidades muertas no pueden actuar
            if not entity_state.get("alive", True):
                # A menos que el delta sea resucitarla (cambio de alive)
                if delta.attribute != "alive":
                    errors.append(
                        f"P4 VIOLATION: Entidad muerta '{entity_name}' no puede "
                        f"cambiar atributo '{delta.attribute}'. "
                        f"Las entidades muertas no actuan."
                    )

            # Validar que el old_value coincida con el estado actual
            current_value = entity_state.get(delta.attribute)
            if current_value is not None and current_value != delta.old_value:
                errors.append(
                    f"CONSISTENCY ERROR: Entidad '{entity_name}' tiene "
                    f"{delta.attribute}={current_value} pero la IA asume "
                    f"{delta.old_value}. Estado inconsistente."
                )

        return errors

    def _validate_dramatic_deltas(self, dramatic_deltas) -> list[str]:
        """
        Valida que los deltas dramaticos esten en rango.

        Los deltas deben estar en [-100, +100].
        """
        errors = []

        # Pydantic ya valida el rango, pero verificamos por si acaso
        deltas_dict = dramatic_deltas.dict() if hasattr(dramatic_deltas, 'dict') else dramatic_deltas

        for meter, value in deltas_dict.items():
            if not isinstance(value, int):
                errors.append(
                    f"DRAMATIC DELTA ERROR: {meter} debe ser int, es {type(value)}"
                )
                continue

            if not (-100 <= value <= 100):
                errors.append(
                    f"DRAMATIC DELTA ERROR: {meter}={value} fuera de rango [-100, +100]"
                )

        return errors

    def _validate_narrative_coherence(self, response: NarrativeResponse) -> list[str]:
        """
        Validaciones de coherencia narrativa (no-criticas, warnings).

        Cosas que no rompen el motor pero indican que la IA podria mejorar.
        """
        warnings = []

        # W1: Narrative demasiado corta
        word_count = len(response.narrative.split())
        if word_count < 50:
            warnings.append(
                f"Narrativa corta ({word_count} palabras). Recomendado: 150-250."
            )

        # W2: Narrative demasiado larga
        if word_count > 350:
            warnings.append(
                f"Narrativa larga ({word_count} palabras). Puede cansar al jugador."
            )

        # W3: Summary demasiado largo
        if len(response.summary) > 150:
            warnings.append(
                "Summary demasiado largo. Debe ser 1 oracion concisa."
            )

        # W4: Ningun cambio dramatico (historia plana)
        if response.dramatic_deltas:
            deltas_dict = response.dramatic_deltas.dict() if hasattr(response.dramatic_deltas, 'dict') else response.dramatic_deltas
            total_change = sum(abs(v) for v in deltas_dict.values())
            if total_change == 0 and not response.is_ending:
                warnings.append(
                    "Sin cambios dramaticos. La historia puede sentirse plana."
                )

        # W5: Demasiados deltas (complejidad excesiva)
        if len(response.entity_deltas) > 5:
            warnings.append(
                f"{len(response.entity_deltas)} entity deltas. Podria ser demasiado "
                f"complejo para un solo evento."
            )

        return warnings

    def _validate_choices(self, response: NarrativeResponse) -> list[str]:
        """
        Valida que las opciones sean apropiadas.
        """
        errors = []

        # Si es ending, no debe haber choices
        if response.is_ending and len(response.choices) > 0:
            errors.append(
                "ENDING ERROR: is_ending=true pero hay choices. "
                "Los finales no tienen opciones."
            )

        # Si no es ending, debe haber al menos 2 choices
        if not response.is_ending and len(response.choices) < 2:
            errors.append(
                "CHOICES ERROR: Debe haber al menos 2 opciones (excepto en endings)."
            )

        # Verificar que las opciones no sean identicas
        if len(response.choices) > 1:
            unique_choices = set(c.lower().strip() for c in response.choices)
            if len(unique_choices) < len(response.choices):
                errors.append(
                    "CHOICES ERROR: Hay opciones duplicadas o muy similares."
                )

        return errors

    def _validate_world_constraints(self, response: NarrativeResponse) -> list[str]:
        """
        Valida que la respuesta respete las restricciones del mundo.

        Esto es CRITICO: las constraints de la WorldDefinition son inviolables.
        """
        errors = []

        # Verificar cada constraint
        for constraint in self.world.constraints:
            # Buscar keywords en el constraint
            constraint_lower = constraint.lower()

            # Ejemplo: "Los muertos no pueden regresar"
            if "muertos" in constraint_lower and "no" in constraint_lower:
                # Verificar que ningun entity_delta reviva a alguien
                for delta in response.entity_deltas:
                    if delta.attribute == "alive":
                        if delta.old_value == False and delta.new_value == True:
                            errors.append(
                                f"WORLD CONSTRAINT VIOLATION: '{constraint}'. "
                                f"La IA intento revivir a '{delta.entity_name}'."
                            )

            # Ejemplo: "No hay viajes en el tiempo"
            if "tiempo" in constraint_lower and "no" in constraint_lower:
                # Buscar keywords en narrative y summary
                narrative_lower = response.narrative.lower()
                summary_lower = response.summary.lower()

                time_keywords = ["pasado", "futuro", "viaje en el tiempo", "retroceder"]
                for keyword in time_keywords:
                    if keyword in narrative_lower or keyword in summary_lower:
                        errors.append(
                            f"WORLD CONSTRAINT VIOLATION: '{constraint}'. "
                            f"La narrativa menciona conceptos temporales prohibidos."
                        )

            # Pued agregar mas validaciones especificas por tipo de constraint

        return errors

    def validate_with_fallback(
        self,
        response: NarrativeResponse,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> tuple[bool, ValidationResult, Optional[str]]:
        """
        Valida la respuesta y sugiere como corregirla si falla.

        Args:
            response: La respuesta a validar.
            attempt: Numero de intento actual.
            max_attempts: Maximo de intentos permitidos.

        Returns:
            tuple: (continuar_intentando, resultado, mensaje_para_ia)
        """
        result = self.validate(response)

        if result.is_valid:
            return (False, result, None)  # No reintentar, todo ok

        if attempt >= max_attempts:
            return (False, result, None)  # No reintentar, maximo alcanzado

        # Construir mensaje para la IA
        error_summary = "; ".join(result.errors[:3])  # Top 3 errores
        feedback = (
            f"La respuesta tiene errores de validacion (intento {attempt}/{max_attempts}):\n"
            f"{error_summary}\n\n"
            f"Por favor, genera una nueva respuesta que corrija estos problemas."
        )

        return (True, result, feedback)


class ValidationLogger:
    """
    Logger especializado para registrar validaciones.

    Util para analizar que tipo de errores comete la IA con mas frecuencia
    y mejorar el prompt en consecuencia.
    """

    def __init__(self):
        self.validation_history: list[dict] = []

    def log_validation(
        self,
        response: NarrativeResponse,
        result: ValidationResult,
        metadata: Optional[dict] = None,
    ):
        """Registra el resultado de una validacion."""
        entry = {
            "timestamp": str(__import__("datetime").datetime.now()),
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "narrative_length": len(response.narrative.split()),
            "num_choices": len(response.choices),
            "num_entity_deltas": len(response.entity_deltas),
        }

        if metadata:
            entry.update(metadata)

        self.validation_history.append(entry)

    def get_error_stats(self) -> dict:
        """Retorna estadisticas de errores."""
        if not self.validation_history:
            return {"total_validations": 0}

        total = len(self.validation_history)
        valid = sum(1 for e in self.validation_history if e["is_valid"])

        all_errors = []
        for entry in self.validation_history:
            all_errors.extend(entry["errors"])

        # Contar tipos de errores
        error_types = {}
        for error in all_errors:
            # Extraer el tipo del error (primera palabra antes de ':')
            error_type = error.split(":")[0] if ":" in error else "UNKNOWN"
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "success_rate": valid / total if total > 0 else 0,
            "error_types": error_types,
        }

    def export_to_file(self, filepath: str):
        """Exporta el historial a un archivo JSON."""
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.validation_history, f, indent=2, ensure_ascii=False)
