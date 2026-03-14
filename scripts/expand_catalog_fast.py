#!/usr/bin/env python3
"""
Fast catalog expansion script.
Strategy: search Archive.org for items, fetch file lists in parallel using threads,
then build catalog entries quickly.
"""

import json
import urllib.request
import urllib.parse
import time
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

CATALOG_PATH = '/Users/thomaspons/Projects/retro-vault/data/catalog.json'

CONSOLES = {
    'nes': {
        'name': 'NES',
        'slug': 'nes',
        'core': 'fceumm',
        'extensions': ['.nes'],
        'queries': ['subject:"Nintendo Entertainment System" mediatype:software'],
        'target': 60,
    },
    'snes': {
        'name': 'SNES',
        'slug': 'snes',
        'core': 'snes9x',
        'extensions': ['.sfc', '.smc'],
        'queries': ['subject:"Super Nintendo" mediatype:software'],
        'target': 50,
    },
    'n64': {
        'name': 'N64',
        'slug': 'n64',
        'core': 'mupen64plus_next',
        'extensions': ['.z64', '.n64', '.v64'],
        'preferred_ext': '.z64',
        'queries': ['subject:"Nintendo 64" mediatype:software'],
        'target': 40,
    },
    'gb': {
        'name': 'GB',
        'slug': 'gb',
        'core': 'gambatte',
        'extensions': ['.gb'],
        'queries': ['subject:"Game Boy" mediatype:software'],
        'target': 30,
    },
    'gbc': {
        'name': 'GBC',
        'slug': 'gbc',
        'core': 'gambatte',
        'extensions': ['.gbc'],
        'queries': ['subject:"Game Boy Color" mediatype:software'],
        'target': 30,
    },
    'gba': {
        'name': 'GBA',
        'slug': 'gba',
        'core': 'mgba',
        'extensions': ['.gba'],
        'queries': ['subject:"Game Boy Advance" mediatype:software'],
        'target': 40,
    },
}

_lock = threading.Lock()


def fetch_json(url, timeout=15, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={'User-Agent': 'RetroVault-CatalogBuilder/2.0'}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5)
    return None


def search_archive(query, rows=400):
    encoded_q = urllib.parse.quote(query)
    url = (
        f'https://archive.org/advancedsearch.php'
        f'?q={encoded_q}'
        f'&fl[]=identifier&fl[]=title'
        f'&rows={rows}'
        f'&sort[]=downloads+desc'
        f'&output=json'
    )
    data = fetch_json(url, timeout=20)
    if data and 'response' in data:
        return data['response'].get('docs', [])
    return []


def get_rom_file(identifier, extensions, preferred_ext=None):
    """Fetch metadata and return (filename, ext) or (None, None)."""
    url = f'https://archive.org/metadata/{identifier}/files'
    data = fetch_json(url, timeout=12)
    if not data or 'result' not in data:
        return None, None

    files = data['result']
    candidates = []
    for f in files:
        name = f.get('name', '')
        nl = name.lower()
        # Skip BIOS files
        if any(x in nl for x in ['[bios]', '(bios)', 'bios.']):
            continue
        for ext in extensions:
            if nl.endswith(ext):
                size = int(f.get('size', 0))
                candidates.append((name, ext, size))
                break

    if not candidates or len(candidates) > 5:
        return None, None

    if preferred_ext:
        pref = [(n, e, s) for n, e, s in candidates if e == preferred_ext]
        if pref:
            candidates = pref

    def score(item):
        name, ext, size = item
        nl = name.lower()
        r = 0
        if '(usa)' in nl or '(world)' in nl:
            r = 20_000_000
        elif '(europe)' in nl or '(e)' in nl:
            r = 10_000_000
        elif '(japan)' in nl or '(j)' in nl:
            r = 5_000_000
        return r + size

    candidates.sort(key=score, reverse=True)
    return candidates[0][0], candidates[0][1]


def sanitize_id(console_slug, title, max_len=40):
    text = title.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return f"{console_slug}-{text[:max_len].rstrip('-')}"


def encode_filename(filename):
    return urllib.parse.quote(filename, safe='')


def process_item(args):
    """Worker function: fetch metadata for one identifier and return entry or None."""
    identifier, title, console_key, config = args
    rom_filename, file_ext = get_rom_file(identifier, config['extensions'], config.get('preferred_ext'))
    if not rom_filename:
        return None
    return {
        'identifier': identifier,
        'title': title,
        'console_key': console_key,
        'config': config,
        'rom_filename': rom_filename,
        'file_ext': file_ext,
    }


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
        target = config['target']
        print(f"\n{'='*55}")
        print(f"  {config['name']} — target: +{target}")

        # Collect search candidates
        candidates = []
        for query in config['queries']:
            print(f"  Searching Archive.org...")
            results = search_archive(query, rows=500)
            print(f"  -> {len(results)} results")
            for r in results:
                rid = r.get('identifier', '')
                rtitle = r.get('title', '')
                if not rid or not rtitle:
                    continue
                if rid in existing_identifiers:
                    continue
                title_key = (rtitle.lower().strip(), console_key)
                if title_key in existing_titles:
                    continue
                candidates.append((rid, rtitle))
            time.sleep(0.5)

        # Deduplicate
        seen = set()
        unique_candidates = []
        for rid, rtitle in candidates:
            if rid not in seen:
                seen.add(rid)
                unique_candidates.append((rid, rtitle))

        print(f"  New candidates to check: {len(unique_candidates)}")

        # Parallel metadata fetching — 8 workers, stop when we have enough
        work_items = [
            (rid, rtitle, console_key, config)
            for rid, rtitle in unique_candidates
        ]

        new_games_console = []
        processed = 0

        # Process in batches of 50 to avoid overwhelming Archive.org
        batch_size = 50
        for batch_start in range(0, len(work_items), batch_size):
            if len(new_games_console) >= target:
                break
            batch = work_items[batch_start:batch_start + batch_size]

            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = {executor.submit(process_item, item): item for item in batch}
                for future in as_completed(futures, timeout=120):
                    try:
                        result = future.result(timeout=15)
                    except Exception:
                        continue

                    processed += 1
                    if result is None:
                        continue

                    identifier = result['identifier']
                    title = result['title']
                    rom_filename = result['rom_filename']
                    file_ext = result['file_ext']

                    # Build entry (thread-safe via lock for ID generation)
                    with _lock:
                        if identifier in existing_identifiers:
                            continue
                        title_key = (title.lower().strip(), console_key)
                        if title_key in existing_titles:
                            continue

                        base_id = sanitize_id(console_key, title)
                        game_id = base_id
                        counter = 2
                        while game_id in existing_ids:
                            game_id = f"{base_id}-{counter}"
                            counter += 1

                        existing_ids.add(game_id)
                        existing_identifiers.add(identifier)
                        existing_titles.add(title_key)

                    entry = {
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
                    new_games_console.append(entry)

                    if len(new_games_console) <= 3 or len(new_games_console) % 10 == 0:
                        print(f"  [{len(new_games_console)}] {title[:45]} -> {rom_filename[:35]}")

                    if len(new_games_console) >= target:
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        break

            print(f"  Batch done: {len(new_games_console)} added so far (processed {processed})")

        stats[console_key] = len(new_games_console)
        all_new.extend(new_games_console)
        print(f"  FINAL for {config['name']}: +{len(new_games_console)}")
        time.sleep(1)

    # Merge into catalog
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

    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print("Catalog saved!")


if __name__ == '__main__':
    main()
