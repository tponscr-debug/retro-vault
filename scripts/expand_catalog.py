#!/usr/bin/env python3
"""
Script to expand the retro-vault catalog by finding new ROMs on Archive.org.
Target: add ~200 new games, focusing on NES, SNES, N64, GB, GBC, GBA.
"""

import json
import urllib.request
import urllib.parse
import time
import re
import sys

CATALOG_PATH = '/Users/thomaspons/Projects/retro-vault/data/catalog.json'

# Console configuration
CONSOLES = {
    'nes': {
        'name': 'NES',
        'slug': 'nes',
        'core': 'fceumm',
        'extensions': ['.nes'],
        'queries': [
            'subject:"Nintendo Entertainment System" mediatype:software',
        ],
        'target': 60,
    },
    'snes': {
        'name': 'SNES',
        'slug': 'snes',
        'core': 'snes9x',
        'extensions': ['.sfc', '.smc'],
        'queries': [
            'subject:"Super Nintendo" mediatype:software',
        ],
        'target': 50,
    },
    'n64': {
        'name': 'N64',
        'slug': 'n64',
        'core': 'mupen64plus_next',
        'extensions': ['.z64', '.n64', '.v64'],
        'preferred_ext': '.z64',
        'queries': [
            'subject:"Nintendo 64" mediatype:software',
        ],
        'target': 40,
    },
    'gb': {
        'name': 'GB',
        'slug': 'gb',
        'core': 'gambatte',
        'extensions': ['.gb'],
        'queries': [
            'subject:"Game Boy" mediatype:software',
        ],
        'target': 30,
    },
    'gbc': {
        'name': 'GBC',
        'slug': 'gbc',
        'core': 'gambatte',
        'extensions': ['.gbc'],
        'queries': [
            'subject:"Game Boy Color" mediatype:software',
        ],
        'target': 30,
    },
    'gba': {
        'name': 'GBA',
        'slug': 'gba',
        'core': 'mgba',
        'extensions': ['.gba'],
        'queries': [
            'subject:"Game Boy Advance" mediatype:software',
        ],
        'target': 40,
    },
}


def fetch_json(url, retries=3):
    """Fetch JSON from URL with error handling and retries."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'RetroVault-Catalog-Builder/1.0'}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"    WARN: Failed to fetch {url[:80]}: {e}")
                return None


def search_archive(query, rows=400):
    """Search Archive.org for items matching query."""
    encoded_q = urllib.parse.quote(query)
    url = (
        f'https://archive.org/advancedsearch.php'
        f'?q={encoded_q}'
        f'&fl[]=identifier&fl[]=title'
        f'&rows={rows}'
        f'&sort[]=downloads+desc'
        f'&output=json'
    )
    data = fetch_json(url)
    if data and 'response' in data and 'docs' in data['response']:
        return data['response']['docs']
    return []


def get_files(identifier):
    """Get file list from Archive.org metadata API."""
    url = f'https://archive.org/metadata/{identifier}/files'
    data = fetch_json(url)
    if data and 'result' in data:
        return data['result']
    return []


def find_rom_file(files, extensions, preferred_ext=None):
    """
    Find the best ROM file from a list of archive files.
    Returns (filename, ext) or (None, None).
    Skips compilations (more than 5 ROM files).
    """
    candidates = []
    for f in files:
        name = f.get('name', '')
        name_lower = name.lower()
        # Skip BIOS files
        if any(skip in name_lower for skip in ['[bios]', '(bios)', 'bios.', '_bios']):
            continue
        for ext in extensions:
            if name_lower.endswith(ext):
                size = int(f.get('size', 0))
                candidates.append((name, ext, size))
                break

    if not candidates:
        return None, None

    # Skip compilations
    if len(candidates) > 5:
        return None, None

    # Prefer preferred extension
    if preferred_ext:
        preferred = [(n, e, s) for n, e, s in candidates if e == preferred_ext]
        if preferred:
            candidates = preferred

    # Sort: prefer USA/World region, then by file size (larger = main ROM)
    def score(item):
        name, ext, size = item
        nl = name.lower()
        region_score = 0
        if '(usa)' in nl or '(world)' in nl:
            region_score = 20_000_000
        elif '(europe)' in nl or '(e)' in nl:
            region_score = 10_000_000
        elif '(japan)' in nl or '(j)' in nl:
            region_score = 5_000_000
        return region_score + size

    candidates.sort(key=score, reverse=True)
    best_name, best_ext, _ = candidates[0]
    return best_name, best_ext


def sanitize_id(console_slug, title, max_len=40):
    """Create a URL-safe ID from console_slug + title."""
    text = title.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    text = text[:max_len].rstrip("-")
    return f"{console_slug}-{text}"


def encode_filename(filename):
    """URL-encode a filename for Archive.org download URLs."""
    return urllib.parse.quote(filename, safe='')


def make_entry(console_key, config, identifier, title, rom_filename, file_ext, existing_ids):
    """Build a catalog game entry."""
    base_id = sanitize_id(console_key, title)
    game_id = base_id
    counter = 2
    while game_id in existing_ids:
        game_id = f"{base_id}-{counter}"
        counter += 1
    existing_ids.add(game_id)

    return {
        "id": game_id,
        "title": title,
        "console": config['name'],
        "console_slug": console_key,
        "genre": [],
        "year": None,
        "developer": None,
        "publisher": None,
        "players": 1,
        "rating": None,
        "description": "",
        "cover_url": f"https://archive.org/services/img/{identifier}",
        "rom_url": f"https://archive.org/download/{identifier}/{encode_filename(rom_filename)}",
        "archive_identifier": identifier,
        "rom_filename": rom_filename,
        "emulator_core": config['core'],
        "bios_required": False,
        "bios_url": None,
        "file_ext": file_ext,
        "tags": [],
    }


def process_console(console_key, config, existing_identifiers, existing_titles, existing_ids):
    """Find and return new game entries for one console."""
    target = config['target']
    print(f"\n{'='*55}")
    print(f"  {config['name']} — target: +{target} games")
    print(f"{'='*55}")

    # Collect search results
    all_results = []
    for query in config['queries']:
        print(f"  Searching: {query[:70]}...")
        results = search_archive(query, rows=400)
        print(f"  -> {len(results)} results")
        all_results.extend(results)
        time.sleep(0.5)

    # Deduplicate by identifier
    seen = set()
    unique_results = []
    for r in all_results:
        rid = r.get('identifier', '')
        if rid and rid not in seen:
            seen.add(rid)
            unique_results.append(r)
    print(f"  Unique candidates: {len(unique_results)}")

    new_games = []
    checked = 0
    skipped_existing = 0
    skipped_no_rom = 0
    skipped_compilation = 0

    for item in unique_results:
        if len(new_games) >= target:
            break

        identifier = item.get('identifier', '')
        title = item.get('title', '')

        if not identifier or not title:
            continue

        # Skip already in catalog
        if identifier in existing_identifiers:
            skipped_existing += 1
            continue

        # Check title+console duplicate
        title_key = (title.lower().strip(), console_key)
        if title_key in existing_titles:
            skipped_existing += 1
            continue

        checked += 1

        # Fetch file metadata
        files = get_files(identifier)
        time.sleep(0.25)

        if not files:
            skipped_no_rom += 1
            continue

        preferred = config.get('preferred_ext')
        rom_filename, file_ext = find_rom_file(files, config['extensions'], preferred)

        if not rom_filename:
            # Check if it was a compilation
            all_rom_count = sum(
                1 for f in files
                for ext in config['extensions']
                if f.get('name', '').lower().endswith(ext)
            )
            if all_rom_count > 5:
                skipped_compilation += 1
            else:
                skipped_no_rom += 1
            continue

        # Build entry
        entry = make_entry(
            console_key, config, identifier, title,
            rom_filename, file_ext, existing_ids
        )

        new_games.append(entry)
        existing_identifiers.add(identifier)
        existing_titles.add(title_key)

        if len(new_games) <= 5 or len(new_games) % 10 == 0:
            print(f"  [{len(new_games)}] {title[:50]} -> {rom_filename[:40]}")

    print(f"\n  Result: {len(new_games)} added | checked {checked} | "
          f"skipped: {skipped_existing} existing, {skipped_no_rom} no ROM, "
          f"{skipped_compilation} compilations")

    return new_games


def main():
    print("Loading catalog...")
    with open(CATALOG_PATH) as f:
        catalog = json.load(f)

    print(f"Current total: {len(catalog['games'])} games")

    # Build lookup sets
    existing_identifiers = set()
    existing_titles = set()
    existing_ids = set()
    for g in catalog['games']:
        if g.get('archive_identifier'):
            existing_identifiers.add(g['archive_identifier'])
        existing_titles.add((g.get('title', '').lower().strip(), g.get('console_slug', '')))
        existing_ids.add(g.get('id', ''))

    all_new = []
    stats = {}

    for console_key, config in CONSOLES.items():
        new = process_console(
            console_key, config,
            existing_identifiers, existing_titles, existing_ids
        )
        all_new.extend(new)
        stats[console_key] = len(new)
        time.sleep(1)

    # Merge
    catalog['games'].extend(all_new)
    catalog['version'] = '4.0'
    catalog['total'] = len(catalog['games'])
    catalog['generated_at'] = '2026-03-14T16:00:00Z'

    print(f"\n{'='*55}")
    print(f"TOTAL ADDED: {len(all_new)} games")
    print(f"NEW TOTAL:   {catalog['total']} games")
    print(f"{'='*55}")
    for key, count in stats.items():
        print(f"  {CONSOLES[key]['name']}: +{count}")

    print(f"\nSaving to {CATALOG_PATH}...")
    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print("Saved!")


if __name__ == '__main__':
    main()
