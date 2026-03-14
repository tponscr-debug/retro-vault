#!/usr/bin/env python3
"""
build_catalog.py — Génère data/catalog.json depuis Archive.org + TheGamesDB.

Usage:
  python build_catalog.py                          # Toutes les consoles, 100 jeux/console
  python build_catalog.py --consoles nes snes      # Consoles spécifiques
  python build_catalog.py --limit 10               # Limiter par console
  python build_catalog.py --output catalog_test.json
  python build_catalog.py --no-verify              # Skip vérification accessibilité des ROMs
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from sources.archive_scraper import search_roms, get_rom_file, verify_rom_accessible
from sources.thegamesdb import enrich_game

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_catalog")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMULATOR_CORES = {
    "nes":       "fceumm",
    "snes":      "snes9x",
    "n64":       "mupen64plus_next",
    "gba":       "mgba",
    "gb":        "gambatte",
    "gbc":       "gambatte",
    "ps1":       "pcsx_rearmed",
    "genesis":   "genesis_plus_gx",
    "sms":       "smsplus",
    "gg":        "genesis_plus_gx",
    "atari2600": "stella2014",
    "atari7800": "prosystem",
    "arcade":    "mame2003_plus",
}

BIOS_REQUIRED = {"ps1", "segacd", "saturn", "nds"}

CONSOLE_LABELS = {
    "nes":       "NES",
    "snes":      "SNES",
    "n64":       "Nintendo 64",
    "gba":       "Game Boy Advance",
    "gb":        "Game Boy",
    "gbc":       "Game Boy Color",
    "ps1":       "PlayStation 1",
    "genesis":   "Sega Genesis",
    "sms":       "Master System",
    "gg":        "Game Gear",
    "atari2600": "Atari 2600",
    "atari7800": "Atari 7800",
    "arcade":    "Arcade",
}

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convertit un titre en kebab-case."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)        # Supprimer les chars spéciaux
    text = re.sub(r"[\s_]+", "-", text)          # Espaces → tirets
    text = re.sub(r"-+", "-", text)              # Tirets multiples → un seul
    text = text.strip("-")
    return text


def format_file_size(size_bytes: int) -> str:
    """Formate une taille en octets en string lisible."""
    if size_bytes == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def build_game_entry(
    archive_item: dict,
    rom_file: dict,
    meta: dict,
    console_slug: str,
) -> dict:
    """Construit une entrée GameEntry complète."""
    raw_title = meta.get("title") or archive_item.get("title", "Unknown")
    slug = slugify(raw_title)

    return {
        "id":           f"{console_slug}-{slug}",
        "slug":         slug,
        "title":        raw_title,
        "console":      console_slug,
        "console_label": CONSOLE_LABELS.get(console_slug, console_slug.upper()),
        "emulator_core": EMULATOR_CORES.get(console_slug, ""),
        "bios_required": console_slug in BIOS_REQUIRED,
        "rom": {
            "filename": rom_file.get("name", ""),
            "url":      rom_file.get("url", ""),
            "size":     rom_file.get("size", 0),
            "size_label": format_file_size(rom_file.get("size", 0)),
        },
        "metadata": {
            "genre":       meta.get("genre"),
            "year":        meta.get("year"),
            "developer":   meta.get("developer"),
            "publisher":   meta.get("publisher"),
            "players":     meta.get("players"),
            "rating":      meta.get("rating"),
            "description": meta.get("description"),
            "cover_url":   meta.get("cover_url"),
        },
        "archive_identifier": archive_item.get("identifier", ""),
        "subjects":           archive_item.get("subjects", []),
    }


# ---------------------------------------------------------------------------
# Console processing
# ---------------------------------------------------------------------------

async def process_console(
    console_slug: str,
    limit: int,
    verify_urls: bool = False,
) -> list[dict]:
    """Traite une console : scrape Archive.org + enrichit via TheGamesDB."""
    items = await search_roms(console_slug, limit)
    if not items:
        logger.warning(f"Aucun item trouvé pour {console_slug}")
        return []

    entries = []
    pbar = tqdm(items, desc=f"  {console_slug.upper():<12}", leave=False, unit="jeu")

    for item in pbar:
        pbar.set_postfix_str(item.get("title", "")[:30])

        # 1. Récupérer le fichier ROM
        rom_file = await get_rom_file(item["identifier"], console_slug)
        if not rom_file:
            logger.debug(f"Pas de ROM pour {item['identifier']}")
            continue

        # 2. (Optionnel) Vérifier l'accessibilité
        if verify_urls:
            accessible = await verify_rom_accessible(rom_file["url"])
            if not accessible:
                logger.debug(f"ROM inaccessible : {rom_file['url']}")
                continue

        # 3. Enrichir les métadonnées
        meta = await enrich_game(item["title"], console_slug)

        # 4. Construire l'entrée
        entry = build_game_entry(item, rom_file, meta, console_slug)
        entries.append(entry)

        # Rate limiting poli
        await asyncio.sleep(0.5)

    return entries


# ---------------------------------------------------------------------------
# Déduplication & tri
# ---------------------------------------------------------------------------

def deduplicate(games: list[dict]) -> list[dict]:
    """Déduplique par (console, slug). Garde la première occurrence."""
    seen: set[str] = set()
    unique = []
    for game in games:
        key = f"{game['console']}::{game['slug']}"
        if key not in seen:
            seen.add(key)
            unique.append(game)
    return unique


def sort_games(games: list[dict]) -> list[dict]:
    """Trie par console puis par titre."""
    return sorted(games, key=lambda g: (g["console"], g["title"].lower()))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(consoles: list[str], limit: int, output_path: str, verify_urls: bool) -> None:
    # Filtrer les consoles invalides
    invalid = [c for c in consoles if c not in EMULATOR_CORES]
    if invalid:
        print(f"[WARN] Consoles inconnues ignorées : {', '.join(invalid)}")
        consoles = [c for c in consoles if c in EMULATOR_CORES]

    if not consoles:
        print("[ERROR] Aucune console valide. Abandon.")
        sys.exit(1)

    all_games: list[dict] = []

    for console in consoles:
        print(f"\n→ Console : {CONSOLE_LABELS.get(console, console.upper())} ({console})")
        games = await process_console(console, limit, verify_urls=verify_urls)
        all_games.extend(games)
        print(f"  {len(games)} jeu(x) ajouté(s)")

    # Post-traitement
    all_games = deduplicate(all_games)
    all_games = sort_games(all_games)

    # Construire le catalogue
    catalog = {
        "version":      "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total":        len(all_games),
        "consoles":     list(dict.fromkeys(g["console"] for g in all_games)),
        "games":        all_games,
    }

    # S'assurer que le dossier data/ existe
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / output_path
    output_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ Catalogue généré : {output_file}")
    print(f"  {len(all_games)} jeux | {len(catalog['consoles'])} console(s)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build Retro Vault catalog from Archive.org + TheGamesDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--consoles",
        nargs="+",
        default=list(EMULATOR_CORES.keys()),
        metavar="CONSOLE",
        help=f"Consoles à traiter. Disponibles : {', '.join(EMULATOR_CORES.keys())}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        metavar="N",
        help="Nombre maximum de jeux par console (défaut : 100)",
    )
    parser.add_argument(
        "--output",
        default="catalog.json",
        metavar="FILENAME",
        help="Nom du fichier de sortie dans data/ (défaut : catalog.json)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Vérifier l'accessibilité de chaque ROM (plus lent)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Activer les logs DEBUG",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    asyncio.run(main(args.consoles, args.limit, args.output, args.verify))
