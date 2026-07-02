"""
cli/play.py - CLI interactivo para jugar historias con el CNE

Ejecutar:
    python cli/play.py
    python cli/play.py --api http://localhost:8000 --adapter ollama
"""

import argparse
import sys

import httpx

# -- Colores ANSI --------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

METER_COLORS = {
    "tension": RED,
    "hope": GREEN,
    "chaos": YELLOW,
    "rhythm": BLUE,
    "saturation": MAGENTA,
    "connection": "\033[95m",
    "mystery": CYAN,
}

METER_LABELS = {
    "tension": "Tension   ",
    "hope": "Esperanza ",
    "chaos": "Caos      ",
    "rhythm": "Ritmo     ",
    "saturation": "Saturacion",
    "connection": "Conexion  ",
    "mystery": "Misterio  ",
}


def clear_screen():
    print("\033[2J\033[H", end="")


def print_header():
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  Causal Narrative Engine - Interactive Story Player{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")


def print_meters(dramatic_state):
    if not dramatic_state:
        return
    print(f"\n{DIM}{'-' * 50}{RESET}")
    print(f"{BOLD}  Estado Dramatico{RESET}\n")
    meters = ["tension", "hope", "chaos", "rhythm", "saturation", "connection", "mystery"]
    for m in meters:
        val = dramatic_state.get(m, 0)
        color = METER_COLORS.get(m, WHITE)
        label = METER_LABELS.get(m, m)
        bar_len = val // 5
        bar = "#" * bar_len + "." * (20 - bar_len)
        print(f"  {label} {color}{bar}{RESET} {val}/100")
    print(f"{DIM}{'-' * 50}{RESET}")


def print_narrative(commit):
    depth = commit.get("depth", 0)
    forced = commit.get("forced_event_type")

    print(f"\n{BOLD}{YELLOW}  -- Capitulo {depth} --{RESET}", end="")
    if forced:
        print(f"  {BOLD}{RED}[{forced}]{RESET}", end="")
    print("\n")

    narrative = commit.get("narrative_text", "")
    for line in narrative.split("\n"):
        print(f"  {WHITE}{line}{RESET}")

    summary = commit.get("summary", "")
    if summary:
        print(f"\n  {DIM}{ITALIC}{summary}{RESET}")

    causal = commit.get("causal_reason")
    if causal:
        print(f"\n  {CYAN}Causa:{RESET} {DIM}{causal}{RESET}")


def print_choices(choices):
    print(f"\n{BOLD}  Elige tu camino:{RESET}\n")
    for i, choice in enumerate(choices, 1):
        text = choice.get("text", "")
        print(f"  {BOLD}{YELLOW}[{i}]{RESET} {text}")
        preview = choice.get("dramatic_preview")
        if preview:
            parts = []
            for key, val in preview.items():
                if val and val != 0:
                    color = GREEN if val > 0 else RED
                    sign = "+" if val > 0 else ""
                    parts.append(f"{color}{key} {sign}{val}{RESET}")
            if parts:
                print(f"      {DIM}{', '.join(parts)}{RESET}")
    print()


def create_world(client, api_url):
    print(f"{BOLD}Crear un nuevo mundo{RESET}\n")

    name = input(f"  Nombre del mundo [{CYAN}Las Tierras Rotas{RESET}]: ").strip()
    if not name:
        name = "Las Tierras Rotas"

    context = input(f"  Contexto [{CYAN}Un mundo postapocaliptico donde la magia resurge{RESET}]: ").strip()
    if not context:
        context = "Un mundo postapocaliptico donde la magia resurge entre las ruinas."

    protagonist = input(f"  Protagonista [{CYAN}Kael, un recolector con poderes magicos{RESET}]: ").strip()
    if not protagonist:
        protagonist = "Kael, un recolector que descubre poderes magicos"

    era = input(f"  Epoca [{CYAN}Post-colapso{RESET}]: ").strip()
    if not era:
        era = "Post-colapso, 300 anos despues"

    print(f"\n  Tonos: {DIM}epic, dark, mysterious, adventurous, philosophical, black_humor{RESET}")
    tone = input(f"  Tono [{CYAN}mysterious{RESET}]: ").strip()
    if not tone:
        tone = "mysterious"

    world_data = {
        "name": name,
        "context": context,
        "protagonist": protagonist,
        "era": era,
        "tone": tone,
    }

    print(f"\n{DIM}Creando mundo...{RESET}")
    resp = client.post(f"{api_url}/worlds", json=world_data)
    resp.raise_for_status()
    world = resp.json()
    print(f"{GREEN}Mundo creado: {world['world_id'][:8]}...{RESET}")
    return world["world_id"]


def start_narrative(client, api_url, world_id, adapter_type):
    print(f"\n{DIM}Generando inicio de la historia...{RESET}")
    resp = client.post(
        f"{api_url}/worlds/{world_id}/start",
        json={"adapter_type": adapter_type},
    )
    resp.raise_for_status()
    return resp.json()


def advance_narrative(client, api_url, commit_id, choice_text, adapter_type):
    print(f"\n{DIM}Generando siguiente capitulo...{RESET}")
    resp = client.post(
        f"{api_url}/commits/{commit_id}/advance",
        json={"choice": choice_text, "adapter_type": adapter_type},
    )
    resp.raise_for_status()
    return resp.json()


def game_loop(client, api_url, adapter_type):
    clear_screen()
    print_header()

    world_id = create_world(client, api_url)
    commit = start_narrative(client, api_url, world_id, adapter_type)

    while True:
        clear_screen()
        print_header()
        print_narrative(commit)
        print_meters(commit.get("dramatic_state"))

        if commit.get("is_ending"):
            print(f"\n{BOLD}{YELLOW}{'=' * 50}{RESET}")
            print(f"{BOLD}{YELLOW}  FIN DE LA HISTORIA{RESET}")
            print(f"{BOLD}{YELLOW}{'=' * 50}{RESET}\n")
            break

        choices = commit.get("choices", [])
        if not choices:
            print(f"\n{RED}No hay opciones disponibles. Fin.{RESET}")
            break

        print_choices(choices)

        while True:
            try:
                raw = input(f"  {BOLD}Tu eleccion (1-{len(choices)}){RESET} [q=salir]: ").strip()
                if raw.lower() == "q":
                    print(f"\n{DIM}Hasta la proxima.{RESET}\n")
                    return
                choice_idx = int(raw) - 1
                if 0 <= choice_idx < len(choices):
                    break
                print(f"  {RED}Elige un numero entre 1 y {len(choices)}{RESET}")
            except ValueError:
                print(f"  {RED}Ingresa un numero valido{RESET}")

        chosen = choices[choice_idx]["text"]
        print(f"\n  {DIM}Elegiste: {chosen}{RESET}")

        commit = advance_narrative(client, api_url, commit["commit_id"], chosen, adapter_type)

    input(f"\n{DIM}Presiona Enter para salir...{RESET}")


def main():
    parser = argparse.ArgumentParser(description="CNE Interactive Story Player")
    parser.add_argument("--api", default="http://localhost:8000", help="URL base de la API")
    parser.add_argument("--adapter", default="ollama", choices=["mock", "ollama", "anthropic"],
                        help="Tipo de AI adapter (default: ollama)")
    args = parser.parse_args()

    print_header()
    print(f"  API: {CYAN}{args.api}{RESET}")
    print(f"  Adapter: {CYAN}{args.adapter}{RESET}\n")

    with httpx.Client(timeout=180.0) as client:
        try:
            health = client.get(f"{args.api}/health")
            health.raise_for_status()
            print(f"  {GREEN}Servidor conectado{RESET}\n")
        except Exception:
            print(f"  {RED}No se pudo conectar al servidor en {args.api}{RESET}")
            print(f"  {DIM}Asegurate de que el servidor esta corriendo:{RESET}")
            print(f"  {DIM}  uvicorn api.main:app --reload{RESET}\n")
            sys.exit(1)

        game_loop(client, args.api, args.adapter)


if __name__ == "__main__":
    main()
