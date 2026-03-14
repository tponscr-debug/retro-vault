"""
Archive.org scraper — récupère les ROMs par console.
API : https://archive.org/advancedsearch.php
"""
import httpx
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CONSOLE_QUERIES = {
    "nes":       'subject:"Nintendo Entertainment System" AND mediatype:software',
    "snes":      'subject:"Super Nintendo" AND mediatype:software',
    "n64":       'subject:"Nintendo 64" AND mediatype:software',
    "gba":       'subject:"Game Boy Advance" AND mediatype:software',
    "gb":        'subject:"Game Boy" NOT "Game Boy Advance" AND mediatype:software',
    "gbc":       'subject:"Game Boy Color" AND mediatype:software',
    "genesis":   'subject:"Sega Genesis" OR subject:"Mega Drive" AND mediatype:software',
    "sms":       'subject:"Master System" AND mediatype:software',
    "ps1":       'subject:"PlayStation" NOT "PlayStation 2" AND mediatype:software',
    "atari2600": 'subject:"Atari 2600" AND mediatype:software',
    "arcade":    'collection:internetarcade AND mediatype:software',
}

CONSOLE_EXTENSIONS = {
    "nes":       [".nes"],
    "snes":      [".sfc", ".smc"],
    "n64":       [".z64", ".n64", ".v64"],
    "gba":       [".gba"],
    "gb":        [".gb"],
    "gbc":       [".gbc"],
    "genesis":   [".md", ".bin"],
    "sms":       [".sms"],
    "ps1":       [".pbp", ".bin"],
    "atari2600": [".a26", ".bin"],
    "arcade":    [".zip"],
}

SEARCH_BASE_URL = "https://archive.org/advancedsearch.php"
METADATA_BASE_URL = "https://archive.org/metadata"
DOWNLOAD_BASE_URL = "https://archive.org/download"


async def search_roms(console_slug: str, max_results: int = 100) -> list[dict]:
    """
    Cherche des items sur Archive.org pour une console donnée.
    Retourne une liste de {identifier, title, subjects}.
    """
    query = CONSOLE_QUERIES.get(console_slug)
    if not query:
        logger.warning(f"Console inconnue : {console_slug}")
        return []

    params = {
        "q":        query,
        "fl[]":     ["identifier", "title", "subject"],
        "output":   "json",
        "rows":     str(max_results),
        "page":     "1",
        "sort[]":   "downloads desc",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(SEARCH_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        docs = data.get("response", {}).get("docs", [])
        results = []
        for doc in docs:
            subjects = doc.get("subject", [])
            if isinstance(subjects, str):
                subjects = [subjects]
            results.append({
                "identifier": doc.get("identifier", ""),
                "title":      doc.get("title", doc.get("identifier", "Unknown")),
                "subjects":   subjects,
            })
        return results

    except httpx.TimeoutException:
        logger.error(f"Timeout lors de la recherche Archive.org pour {console_slug}")
        return []
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} pour {console_slug}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la recherche pour {console_slug}: {e}")
        return []


async def get_rom_file(identifier: str, console_slug: str) -> Optional[dict]:
    """
    Récupère les fichiers d'un item Archive.org et retourne le premier fichier ROM valide.
    Retourne {name, url, size} ou None.
    """
    valid_extensions = CONSOLE_EXTENSIONS.get(console_slug, [])
    if not valid_extensions:
        return None

    url = f"{METADATA_BASE_URL}/{identifier}/files"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        files = data.get("result", [])
        if not files:
            return None

        # Séparer les ROM non-ZIP des ZIP
        non_zip_roms = []
        zip_roms = []

        for f in files:
            fname = f.get("name", "")
            ext = _get_extension(fname).lower()

            if ext in valid_extensions and ext != ".zip":
                non_zip_roms.append(f)
            elif ext == ".zip" and ".zip" in valid_extensions:
                zip_roms.append(f)
            elif ext == ".zip" and ext not in valid_extensions:
                # Pour les consoles non-arcade, ignorer les ZIP sauf si c'est le seul format
                pass

        # Préférer les non-ZIP, sinon prendre le ZIP
        chosen = None
        if non_zip_roms:
            chosen = non_zip_roms[0]
        elif zip_roms:
            chosen = zip_roms[0]
        elif ".zip" not in valid_extensions:
            # Dernier recours : chercher un ZIP même pour les consoles qui n'en veulent pas
            for f in files:
                if _get_extension(f.get("name", "")).lower() == ".zip":
                    chosen = f
                    break

        if not chosen:
            return None

        fname = chosen.get("name", "")
        size = int(chosen.get("size", 0)) if chosen.get("size") else 0
        file_url = f"{DOWNLOAD_BASE_URL}/{identifier}/{fname}"

        return {
            "name": fname,
            "url":  file_url,
            "size": size,
        }

    except httpx.TimeoutException:
        logger.warning(f"Timeout pour les fichiers de {identifier}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} pour les fichiers de {identifier}")
        return None
    except Exception as e:
        logger.warning(f"Erreur pour les fichiers de {identifier}: {e}")
        return None


async def verify_rom_accessible(url: str) -> bool:
    """
    Fait un HEAD request pour vérifier que l'URL est accessible (200/206).
    Timeout 10s. Retourner False si erreur.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(url)
            return response.status_code in (200, 206)
    except Exception:
        return False


def _get_extension(filename: str) -> str:
    """Retourne l'extension d'un fichier (avec le point, en minuscules)."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
