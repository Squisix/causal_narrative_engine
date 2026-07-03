#!/usr/bin/env python3
"""
scripts/setup_env.py - Helper for configuring .env

Run:
    python scripts/setup_env.py
"""

import os
from pathlib import Path


def main():
    """Configure .env interactively."""
    root = Path(__file__).parent.parent
    env_file = root / ".env"
    env_example = root / ".env.example"

    print("=" * 60)
    print("  Configuration Setup - Causal Narrative Engine")
    print("=" * 60)
    print()

    # Check if .env already exists
    if env_file.exists():
        print(f"WARNING: The .env file already exists at: {env_file}")
        response = input("Overwrite? (y/N): ").strip().lower()
        if response != "y":
            print("Cancelled.")
            return

    # Check that .env.example exists
    if not env_example.exists():
        print(f"ERROR: Cannot find {env_example}")
        print("Make sure you are in the project root.")
        return

    print()
    print("Anthropic API Configuration (Claude)")
    print("-" * 60)
    print()
    print("To obtain your API key:")
    print("  1. Go to: https://console.anthropic.com/settings/keys")
    print("  2. Create a new key")
    print("  3. Copy it (it is only shown once)")
    print()

    # Request API key
    api_key = input("Enter your API key (or press Enter to leave empty): ").strip()

    if not api_key:
        print()
        print("WARNING: No API key entered.")
        print("The .env file will be created with example values.")
        print("You will need to edit it manually afterwards.")
        print()

    # Request model (optional)
    print()
    print("Available models:")
    print("  1. claude-3-5-sonnet-20241022  (recommended: quality/price balance)")
    print("  2. claude-opus-4               (highest quality, more expensive)")
    print("  3. claude-haiku-3              (fast and economical)")
    print()

    modelo_opcion = input("Select model (1-3, or Enter to use the recommended one): ").strip()

    modelos = {
        "1": "claude-3-5-sonnet-20241022",
        "2": "claude-opus-4",
        "3": "claude-haiku-3",
    }
    modelo = modelos.get(modelo_opcion, "claude-3-5-sonnet-20241022")

    # Create .env
    with open(env_example, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Replace values
    if api_key:
        contenido = contenido.replace(
            "ANTHROPIC_API_KEY=sk-ant-api03-your-api-key-here",
            f"ANTHROPIC_API_KEY={api_key}"
        )

    contenido = contenido.replace(
        "ANTHROPIC_MODEL=claude-3-5-sonnet-20241022",
        f"ANTHROPIC_MODEL={modelo}"
    )

    # Write .env
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(contenido)

    print()
    print("=" * 60)
    print("SUCCESS: .env file created successfully")
    print("=" * 60)
    print()
    print(f"Location: {env_file}")
    print()

    if api_key:
        print("API key configured")
        print(f"Model: {modelo}")
        print()
        print("You can now run:")
        print("  pytest -m anthropic_api -v")
    else:
        print("WARNING: API key NOT configured")
        print()
        print("To add your API key manually:")
        print(f"  1. Edit: {env_file}")
        print("  2. Replace 'your-api-key-here' with your real key")
        print()

    print("For tests without API (free):")
    print("  pytest tests/test_fase1.py tests/test_mock_adapter.py -v")
    print()


if __name__ == "__main__":
    main()
