#!/usr/bin/env python3
"""
scripts/setup_env.py - Helper para configurar .env

Ejecutar:
    python scripts/setup_env.py
"""

import os
from pathlib import Path


def main():
    """Configura .env interactivamente."""
    root = Path(__file__).parent.parent
    env_file = root / ".env"
    env_example = root / ".env.example"

    print("=" * 60)
    print("  Setup de configuración - Causal Narrative Engine")
    print("=" * 60)
    print()

    # Verificar si .env ya existe
    if env_file.exists():
        print(f"⚠️  El archivo .env ya existe en: {env_file}")
        respuesta = input("¿Sobrescribir? (s/N): ").strip().lower()
        if respuesta != "s":
            print("Cancelado.")
            return

    # Verificar que .env.example exista
    if not env_example.exists():
        print(f"❌ Error: No se encuentra {env_example}")
        print("Asegúrate de estar en la raíz del proyecto.")
        return

    print()
    print("Configuración de Anthropic API (Claude)")
    print("-" * 60)
    print()
    print("Para obtener tu API key:")
    print("  1. Ve a: https://console.anthropic.com/settings/keys")
    print("  2. Crea una nueva key")
    print("  3. Cópiala (solo se muestra una vez)")
    print()

    # Solicitar API key
    api_key = input("Ingresa tu API key (o Enter para dejar vacío): ").strip()

    if not api_key:
        print()
        print("⚠️  No ingresaste API key.")
        print("El archivo .env se creará con valores de ejemplo.")
        print("Deberás editarlo manualmente después.")
        print()

    # Solicitar modelo (opcional)
    print()
    print("Modelos disponibles:")
    print("  1. claude-3-5-sonnet-20241022  (recomendado: balance calidad/precio)")
    print("  2. claude-opus-4               (máxima calidad, más caro)")
    print("  3. claude-haiku-3              (rápido y económico)")
    print()

    modelo_opcion = input("Selecciona modelo (1-3, o Enter para usar el recomendado): ").strip()

    modelos = {
        "1": "claude-3-5-sonnet-20241022",
        "2": "claude-opus-4",
        "3": "claude-haiku-3",
    }
    modelo = modelos.get(modelo_opcion, "claude-3-5-sonnet-20241022")

    # Crear .env
    with open(env_example, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Reemplazar valores
    if api_key:
        contenido = contenido.replace(
            "ANTHROPIC_API_KEY=sk-ant-api03-tu-api-key-aquí",
            f"ANTHROPIC_API_KEY={api_key}"
        )

    contenido = contenido.replace(
        "ANTHROPIC_MODEL=claude-3-5-sonnet-20241022",
        f"ANTHROPIC_MODEL={modelo}"
    )

    # Escribir .env
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(contenido)

    print()
    print("=" * 60)
    print("✅ Archivo .env creado exitosamente")
    print("=" * 60)
    print()
    print(f"📁 Ubicación: {env_file}")
    print()

    if api_key:
        print("✅ API key configurada")
        print(f"✅ Modelo: {modelo}")
        print()
        print("Ahora puedes ejecutar:")
        print("  pytest -m anthropic_api -v")
    else:
        print("⚠️  API key NO configurada")
        print()
        print("Para agregar tu API key manualmente:")
        print(f"  1. Edita: {env_file}")
        print("  2. Reemplaza 'tu-api-key-aquí' con tu key real")
        print()

    print("Para tests sin API (gratis):")
    print("  pytest tests/test_fase1.py tests/test_mock_adapter.py -v")
    print()


if __name__ == "__main__":
    main()
