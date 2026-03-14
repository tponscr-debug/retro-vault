"""
TheGamesDB API client — métadonnées et jaquettes.
API key : variable d'environnement THEGAMESDB_API_KEY
"""
import httpx
import os
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.thegamesdb.net"

PLATFORM_IDS = {
    "nes":       7,
    "snes":      6,
    "n64":       3,
    "gba":       5,
    "gb":        4,
    "gbc":       41,
    "ps1":       10,
    "genesis":   18,
    "sms":       35,
    "gg":        21,
    "arcade":    23,
    "nds":       8,
    "psp":       13,
    "atari2600": 22,
    "atari7800": 56,
}

IMAGE_BASE_URL = "https://cdn.thegamesdb.net/images/original/"


class RateLimitWarning(Warning):
    """Levée quand le quota mensuel TheGamesDB est presque épuisé."""
    pass


def _get_api_key() -> Optional[str]:
    """Retourne la clé API ou None si non définie."""
    key = os.getenv("THEGAMESDB_API_KEY", "").strip()
    return key if key else None


async def get_game_metadata(title: str, console_slug: str) -> Optional[dict]:
    """
    Cherche un jeu par nom sur TheGamesDB.
    Retourne {title, genre, year, developer, publisher, players, rating, description, cover_url, game_id} ou None.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.debug("THEGAMESDB_API_KEY non définie — enrichissement désactivé.")
        return None

    platform_id = PLATFORM_IDS.get(console_slug)
    params = {
        "apikey": api_key,
        "name":   title,
        "fields": "players,genres,overview,rating,developers,publishers,release_date",
    }
    if platform_id:
        params["filter[platform]"] = platform_id

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(f"{BASE_URL}/v1/Games/ByGameName", params=params)
            response.raise_for_status()
            data = response.json()

        # Vérifier le quota restant
        remaining = data.get("remaining_monthly_allowance", 9999)
        if isinstance(remaining, (int, float)) and remaining < 50:
            import warnings
            warnings.warn(
                f"Quota TheGamesDB presque épuisé : {remaining} requêtes restantes.",
                RateLimitWarning,
            )

        games = data.get("data", {}).get("games", [])
        if not games:
            return None

        # Trouver le meilleur match : exact d'abord, sinon le premier résultat
        best_match = None
        title_lower = title.lower().strip()
        for game in games:
            game_title = game.get("game_title", "").lower().strip()
            if game_title == title_lower:
                best_match = game
                break
        if best_match is None:
            best_match = games[0]

        # Extraire les genres (inclus dans la réponse include si présents)
        include = data.get("include", {})
        genres_map = include.get("genres", {}).get("data", {})
        developers_map = include.get("developers", {}).get("data", {})
        publishers_map = include.get("publishers", {}).get("data", {})

        genre_ids = best_match.get("genres", []) or []
        genre_names = [
            genres_map.get(str(gid), {}).get("name", "")
            for gid in genre_ids
            if genres_map.get(str(gid))
        ]

        developer_ids = best_match.get("developers", []) or []
        developer_names = [
            developers_map.get(str(did), {}).get("name", "")
            for did in developer_ids
            if developers_map.get(str(did))
        ]

        publisher_ids = best_match.get("publishers", []) or []
        publisher_names = [
            publishers_map.get(str(pid), {}).get("name", "")
            for pid in publisher_ids
            if publishers_map.get(str(pid))
        ]

        # Extraire l'année depuis release_date (format YYYY-MM-DD ou YYYY)
        release_date = best_match.get("release_date", "") or ""
        year = None
        if release_date:
            year_str = release_date[:4]
            if year_str.isdigit():
                year = int(year_str)

        return {
            "game_id":     best_match.get("id"),
            "title":       best_match.get("game_title", title),
            "genre":       genre_names[0] if genre_names else None,
            "year":        year,
            "developer":   developer_names[0] if developer_names else None,
            "publisher":   publisher_names[0] if publisher_names else None,
            "players":     best_match.get("players"),
            "rating":      best_match.get("rating"),
            "description": best_match.get("overview"),
            "cover_url":   None,  # Rempli par get_game_images
        }

    except httpx.TimeoutException:
        logger.warning(f"Timeout TheGamesDB pour : {title}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} TheGamesDB pour {title}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Erreur TheGamesDB pour {title}: {e}")
        return None


async def get_game_images(game_id: int) -> Optional[str]:
    """
    Récupère l'URL de la jaquette (boxart front) pour un jeu.
    Retourne l'URL de la thumbnail ou None.
    """
    api_key = _get_api_key()
    if not api_key or not game_id:
        return None

    params = {
        "apikey":        api_key,
        "games_id":      game_id,
        "filter[type]":  "boxart",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(f"{BASE_URL}/v1/Games/Images", params=params)
            response.raise_for_status()
            data = response.json()

        images_by_game = data.get("data", {}).get("images", {})
        images = images_by_game.get(str(game_id), [])
        if not images:
            return None

        # Filtrer sur les boxart front
        front_images = [img for img in images if img.get("side") == "front"]
        chosen = front_images[0] if front_images else images[0]

        # Préférer la thumbnail, sinon l'original
        filename = chosen.get("filename") or chosen.get("original", {}).get("url")
        if not filename:
            return None

        base_path = data.get("data", {}).get("base_url", {})
        thumb_base = base_path.get("thumb", IMAGE_BASE_URL)
        original_base = base_path.get("original", IMAGE_BASE_URL)

        thumb_url = chosen.get("thumb")
        if thumb_url:
            if thumb_url.startswith("http"):
                return thumb_url
            return f"{thumb_base.rstrip('/')}/{thumb_url.lstrip('/')}"

        if filename.startswith("http"):
            return filename
        return f"{original_base.rstrip('/')}/{filename.lstrip('/')}"

    except httpx.TimeoutException:
        logger.warning(f"Timeout images TheGamesDB pour game_id={game_id}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} images TheGamesDB game_id={game_id}")
        return None
    except Exception as e:
        logger.warning(f"Erreur images TheGamesDB game_id={game_id}: {e}")
        return None


async def enrich_game(title: str, console_slug: str) -> dict:
    """
    Combine get_game_metadata + get_game_images.
    Retourne toujours un dict (même si enrichissement partiel/raté).
    Gestion rate limit : si remaining_monthly_allowance < 50, lever RateLimitWarning.
    """
    empty_meta = {
        "title":       title,
        "genre":       None,
        "year":        None,
        "developer":   None,
        "publisher":   None,
        "players":     None,
        "rating":      None,
        "description": None,
        "cover_url":   None,
    }

    if not _get_api_key():
        return empty_meta

    meta = await get_game_metadata(title, console_slug)
    if not meta:
        return empty_meta

    game_id = meta.get("game_id")
    if game_id:
        cover_url = await get_game_images(game_id)
        meta["cover_url"] = cover_url

    # Nettoyer le game_id interne avant de retourner
    meta.pop("game_id", None)

    # Fusionner avec empty_meta pour garantir toutes les clés
    result = {**empty_meta, **{k: v for k, v in meta.items() if v is not None}}
    return result
