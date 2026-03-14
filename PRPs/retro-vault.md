# PRP — Retro Vault
**Version**: 1.0
**Date**: 2026-03-14
**Statut**: Prêt pour validation

---

## 1. Objectif du projet

Portail de jeux rétro personnel (usage unique, propriétaire), entièrement statique (aucun backend, aucun serveur requis). Le portail permet de :
- Parcourir un catalogue visuel de jeux rétro multi-consoles avec jaquettes
- Lancer directement l'émulateur dans la page via EmulatorJS
- Chercher un jeu par nom, genre ou console (fuzzy search)
- Jouer à la manette Xbox One via Web Gamepad API

Le catalogue est pré-généré (fichier `catalog.json`) via un script Python offline qui scrape Archive.org et TheGamesDB. Aucune dépendance serveur au runtime.

---

## 2. Architecture des fichiers

```
retro-vault/
├── index.html                  # Page d'accueil : grille de jeux
├── player.html                 # Page émulateur (player EmulatorJS)
├── css/
│   ├── base.css                # Reset, variables CSS, typographie
│   ├── grid.css                # Grille de jeux (cards, hover, layout)
│   ├── player.css              # Layout page émulateur
│   └── design-system.css      # Tokens : couleurs, glow, neon effects
├── js/
│   ├── catalog.js              # Chargement et parsing de catalog.json
│   ├── search.js               # Intégration Fuse.js, logique de recherche
│   ├── ui.js                   # Rendu des cards, filtres console/genre
│   ├── player.js               # Instanciation EmulatorJS + config gamepad
│   └── gamepad.js              # Web Gamepad API : mapping Xbox One
├── data/
│   └── catalog.json            # Catalogue généré par le script Python
├── assets/
│   ├── fonts/                  # Polices locales (si auto-hébergées)
│   └── ui/                     # Icônes, logos consoles, assets statiques
├── scripts/
│   ├── build_catalog.py        # Script principal de construction du catalogue
│   ├── sources/
│   │   ├── archive_scraper.py  # Scraping Archive.org API
│   │   └── thegamesdb.py       # Appels TheGamesDB API
│   └── requirements.txt        # httpx, asyncio, tqdm, python-dotenv
├── PRPs/
│   └── retro-vault.md          # Ce document
└── .env                        # THEGAMESDB_API_KEY (non commité)
```

**Règle absolue** : zéro JS inline dans les HTML. Chaque fichier JS a une responsabilité unique et reste sous 400 lignes.

---

## 3. Format `catalog.json`

### Structure globale

```json
{
  "version": "1.0",
  "generated_at": "2026-03-14T12:00:00Z",
  "total": 1250,
  "games": [ ...GameEntry[] ]
}
```

### Structure d'un `GameEntry`

```json
{
  "id": "nes-super-mario-bros",
  "title": "Super Mario Bros.",
  "console": "NES",
  "console_slug": "nes",
  "genre": ["Platform", "Action"],
  "year": 1985,
  "developer": "Nintendo",
  "publisher": "Nintendo",
  "players": 2,
  "rating": 9.2,
  "description": "Le platformer qui a défini une génération...",
  "cover_url": "https://cdn.thegamesdb.net/images/thumb/1.jpg",
  "cover_local": null,
  "rom_url": "https://archive.org/download/myroms-nes/Super_Mario_Bros.nes.zip",
  "archive_identifier": "myroms-nes",
  "rom_filename": "Super_Mario_Bros.nes",
  "emulator_core": "fceumm",
  "bios_required": false,
  "bios_url": null,
  "file_ext": ".nes",
  "tags": ["must-play", "1985", "nintendo"]
}
```

### Champs critiques

| Champ | Type | Rôle |
|---|---|---|
| `id` | string | Identifiant unique kebab-case : `{console_slug}-{title-slug}` |
| `console_slug` | string | Clé de mapping vers le core EmulatorJS |
| `emulator_core` | string | Valeur exacte pour `EJS_core` |
| `rom_url` | string | URL directe Archive.org vers le fichier ZIP/ROM |
| `archive_identifier` | string | Identifiant Archive.org de l'item parent |
| `cover_url` | string | URL CDN TheGamesDB (thumbnail) |
| `bios_required` | bool | Si true, `bios_url` doit pointer vers le BIOS |

---

## 4. Mapping Consoles → EmulatorJS Cores

| Console | `console_slug` | `emulator_core` | Extensions | BIOS requis |
|---|---|---|---|---|
| NES / Famicom | `nes` | `fceumm` | `.nes`, `.zip` | Non |
| Super Nintendo | `snes` | `snes9x` | `.sfc`, `.smc`, `.zip` | Non |
| Nintendo 64 | `n64` | `mupen64plus_next` | `.z64`, `.n64`, `.v64`, `.zip` | Non |
| Game Boy | `gb` | `gambatte` | `.gb`, `.zip` | Non |
| Game Boy Color | `gbc` | `gambatte` | `.gbc`, `.zip` | Non |
| Game Boy Advance | `gba` | `mgba` | `.gba`, `.zip` | Non |
| PlayStation 1 | `ps1` | `pcsx_rearmed` | `.bin`+`.cue`, `.img`, `.pbp` | Oui (SCPH-1001.bin) |
| Sega Genesis / Mega Drive | `genesis` | `genesis_plus_gx` | `.md`, `.bin`, `.zip` | Non |
| Sega Master System | `sms` | `smsplus` | `.sms`, `.zip` | Non |
| Sega Game Gear | `gg` | `genesis_plus_gx` | `.gg`, `.zip` | Non |
| Sega CD | `segacd` | `genesis_plus_gx` | `.bin`+`.cue`, `.iso` | Oui (bios_CD_U.bin) |
| Sega 32X | `32x` | `picodrive` | `.32x`, `.zip` | Non |
| Atari 2600 | `atari2600` | `stella2014` | `.a26`, `.bin`, `.zip` | Non |
| Atari 7800 | `atari7800` | `prosystem` | `.a78`, `.zip` | Non |
| Atari Lynx | `lynx` | `handy` | `.lnx`, `.zip` | Non |
| Arcade / MAME | `arcade` | `mame2003_plus` | `.zip` | Non (souvent) |
| Arcade FBNeo | `fbneo` | `fbneo` | `.zip` | Partiel |
| Nintendo DS | `nds` | `melonds` | `.nds`, `.zip` | Oui (firmware) |
| PSP | `psp` | `ppsspp` | `.iso`, `.cso` | Non |
| 3DO | `3do` | `opera` | `.iso` | Oui (panafz10.bin) |
| Sega Saturn | `saturn` | `yabause` | `.bin`+`.cue`, `.iso` | Oui (sega_101.bin) |

---

## 5. Script Python — Construction du Catalogue (`build_catalog.py`)

### 5.1 Architecture du script

```
scripts/
├── build_catalog.py        # Orchestrateur : merge les sources, écrit catalog.json
├── sources/
│   ├── archive_scraper.py  # Recherche ROMs sur Archive.org
│   └── thegamesdb.py       # Récupère métadonnées + jaquettes sur TheGamesDB
└── requirements.txt
```

**`requirements.txt`** :
```
httpx>=0.27
asyncio
tqdm>=4.66
python-dotenv>=1.0
aiofiles>=23.0
```

### 5.2 Archive.org API

**Endpoint de recherche** :
```
GET https://archive.org/advancedsearch.php
  ?q={QUERY}
  &fl[]=identifier
  &fl[]=title
  &fl[]=subject
  &fl[]=format
  &output=json
  &rows=500
  &page=1
```

**Exemples de queries par console** :
```python
CONSOLE_QUERIES = {
    "nes":     'subject:"Nintendo Entertainment System" AND mediatype:software',
    "snes":    'subject:"Super Nintendo" AND mediatype:software',
    "n64":     'subject:"Nintendo 64" AND mediatype:software',
    "gba":     'subject:"Game Boy Advance" AND mediatype:software',
    "gb":      'subject:"Game Boy" AND mediatype:software',
    "ps1":     'subject:"PlayStation" AND mediatype:software',
    "genesis": 'subject:"Sega Genesis" AND mediatype:software',
    "sms":     'subject:"Master System" AND mediatype:software',
    "arcade":  'collection:internetarcade AND mediatype:software',
}
```

**URL de téléchargement ROM** : Une fois l'`identifier` récupéré, lister les fichiers de l'item pour obtenir l'URL exacte :
```
GET https://archive.org/metadata/{identifier}/files
```
Réponse : liste de fichiers avec `name`, `format`, `size`. Filtrer sur l'extension cible.

URL finale du ROM :
```
https://archive.org/download/{identifier}/{filename}
```

**Collections recommandées** :
- `internetarcade` : Arcade MAME (légal, archive.org héberge et joue lui-même)
- Soft-lib collections pour consoles domestiques
- Recherche par sujet pour trouver des items individuels

### 5.3 TheGamesDB API

**Base URL** : `https://api.thegamesdb.net`
**Auth** : paramètre `apikey={THEGAMESDB_API_KEY}` (clé gratuite sur thegamesdb.net)

**Endpoints utilisés** :

```python
# Recherche par nom + plateforme
GET /v1/Games/ByGameName
  ?apikey={KEY}
  &name={game_title}
  &filter[platform]={platform_id}
  &fields=players,genres,overview,rating,developers,publishers

# Récupérer les images (jaquettes)
GET /v1/Games/Images
  ?apikey={KEY}
  &games_id={game_id}
  &filter[type]=boxart

# Lister les plateformes (pour obtenir les platform_id)
GET /v1/Platforms
  ?apikey={KEY}
```

**Platform IDs TheGamesDB (principaux)** :
```python
PLATFORM_IDS = {
    "nes":     7,
    "snes":    6,
    "n64":     3,
    "gba":     5,
    "gb":      4,
    "gbc":     41,
    "ps1":     10,
    "genesis": 18,
    "sms":     35,
    "gg":      21,
    "arcade":  23,
    "nds":     8,
    "psp":     13,
    "atari2600": 22,
}
```

**URL d'image** :
```
https://cdn.thegamsdb.net/images/thumb/{filename}
```
(Base URL retournée dans `data.base_url` de la réponse `/Games/Images`)

### 5.4 Flux d'orchestration (`build_catalog.py`)

```python
async def build_catalog(consoles: list[str], max_per_console: int = 200):
    games = []
    for console_slug in consoles:
        # 1. Chercher les items sur Archive.org
        archive_items = await archive_scraper.search(console_slug, max_per_console)

        for item in archive_items:
            # 2. Récupérer les fichiers de l'item (pour URL ROM exacte)
            rom_file = await archive_scraper.get_rom_file(item["identifier"], console_slug)
            if not rom_file:
                continue

            # 3. Enrichir avec TheGamesDB
            meta = await thegamesdb.get_metadata(item["title"], console_slug)

            # 4. Merge et construction de l'entrée
            entry = build_game_entry(item, rom_file, meta, console_slug)
            games.append(entry)

    # 5. Écriture catalog.json
    write_catalog(games)
```

**Gestion de la rate limit** : TheGamesDB retourne `remaining_monthly_allowance` dans chaque réponse. Pause si < 50.

---

## 6. UI — Pages et Composants

### 6.1 Page d'accueil (`index.html`)

**Layout** : Sidebar gauche (filtres) + zone principale (grille + search bar)

**Composants** :
- **Header** : Logo "RETRO VAULT" en neon, compteur de jeux
- **SearchBar** : Input avec autocomplete (Fuse.js, debounce 300ms)
- **FilterPanel** (sidebar) : Checkboxes console, select genre, slider année
- **GameGrid** : Grille masonry / CSS Grid auto-fill (cards)
- **GameCard** :
  - Jaquette pleine (cover_url)
  - Overlay hover : titre, console badge, genre, année
  - Clic → `player.html?id={game.id}`
- **ConsoleBar** : Bande horizontale avec icônes consoles (filtrage rapide)

**JS côté accueil** :
- `catalog.js` : `fetch('./data/catalog.json')` → expose `window.CATALOG`
- `search.js` : instancie `new Fuse(games, { keys: ['title','genre','console'], threshold: 0.3 })`
- `ui.js` : rendu cards, gestion filtres, infinite scroll (IntersectionObserver)

### 6.2 Page émulateur (`player.html`)

**Layout** : Pleine page sombre. Emulateur centré, panneau info en dessous.

**Flux** :
1. Lire `?id=` dans l'URL
2. `catalog.js` charge `catalog.json`, trouve le jeu par `id`
3. `player.js` injecte les variables EmulatorJS et charge le loader

**Variables injectées dynamiquement** :
```javascript
window.EJS_player     = "emulator-container";
window.EJS_gameUrl    = game.rom_url;           // URL Archive.org
window.EJS_core       = game.emulator_core;     // ex: "fceumm"
window.EJS_pathToData = "https://cdn.emulatorjs.org/stable/data/";
window.EJS_gameID     = game.id;
window.EJS_gameName   = game.title;
// Options bonus
window.EJS_startOnLoaded = true;
window.EJS_fullscreenOnLoaded = false;
window.EJS_language   = "fr";
window.EJS_gameParentUrl = game.rom_url;        // Pour les multi-disc (PS1, SegaCD)
```

**Script EmulatorJS** :
```html
<script src="https://cdn.emulatorjs.org/stable/loader.js"></script>
```

**Panneau info** : jaquette miniature, titre, console, genre, année, description (scrollable).

**Bouton retour** : flèche animée → retour index avec filtre console restauré.

### 6.3 Responsivité

- Desktop first, grille adaptative (auto-fill minmax 200px, 1fr)
- Mobile : sidebar en drawer bottom-sheet, grille 2 colonnes
- Breakpoints : 480px / 768px / 1280px

---

## 7. Intégration EmulatorJS

### 7.1 CDN et versioning

```
CDN stable : https://cdn.emulatorjs.org/stable/data/
Loader      : https://cdn.emulatorjs.org/stable/loader.js
```

Utiliser `stable` en production. `latest` pour tester les derniers cores.

### 7.2 Code minimal d'instanciation

```html
<!-- player.html -->
<div id="emulator-container"></div>

<script>
  // Variables injectées par player.js AVANT le loader
  window.EJS_player     = "emulator-container";
  window.EJS_gameUrl    = "https://archive.org/download/{id}/{file}.zip";
  window.EJS_core       = "fceumm";   // dynamique selon console
  window.EJS_pathToData = "https://cdn.emulatorjs.org/stable/data/";
  window.EJS_startOnLoaded = true;
</script>
<script src="https://cdn.emulatorjs.org/stable/loader.js"></script>
```

### 7.3 Cas spéciaux

**PlayStation 1 (`.bin`+`.cue`)** :
```javascript
window.EJS_core     = "pcsx_rearmed";
window.EJS_gameUrl  = "game.cue";     // Pointer vers le .cue
window.EJS_biosUrl  = "https://archive.org/download/ps1-bios/SCPH-1001.bin";
```

**Nintendo DS** :
```javascript
window.EJS_core    = "melonds";
window.EJS_biosUrl = "https://example.com/nds-firmware.bin";
```

**MAME Arcade** :
```javascript
window.EJS_core    = "mame2003_plus";
window.EJS_gameUrl = "https://archive.org/download/mame-chds-roms/{game}.zip";
```

**Sauvegardes** : EmulatorJS gère les saves en localStorage automatiquement. Possibilité d'exposer `EJS_saveStateURL` pour sync externe (hors scope v1).

---

## 8. Web Gamepad API — Manette Xbox One

### 8.1 Principe

EmulatorJS gère nativement la Gamepad API. Le module `gamepad.js` se charge uniquement de :
1. Détecter la connexion/déconnexion manette
2. Afficher un indicateur visuel dans l'UI (icône manette active/inactive)
3. Gérer le mapping custom si l'utilisateur le demande (facultatif v1)

### 8.2 Code de détection (`gamepad.js`)

```javascript
// Détection connexion manette
window.addEventListener("gamepadconnected", (e) => {
  const gp = e.gamepad;
  showGamepadStatus(true, gp.id);  // Affiche badge "Manette connectée"
  console.log(`Gamepad connecté : ${gp.id} (${gp.buttons.length} boutons)`);
});

window.addEventListener("gamepaddisconnected", (e) => {
  showGamepadStatus(false);
});

function showGamepadStatus(connected, id = "") {
  const badge = document.getElementById("gamepad-badge");
  badge.classList.toggle("active", connected);
  badge.title = connected ? `Manette : ${id}` : "Aucune manette";
}
```

### 8.3 Mapping Xbox One (référence)

EmulatorJS mappe automatiquement les boutons standards. Référence :

| Index | Bouton Xbox | Action rétro typique |
|---|---|---|
| 0 | A | Confirm / Jump |
| 1 | B | Cancel / Run |
| 2 | X | Action 2 |
| 3 | Y | Action 3 |
| 4 | LB | L (SNES) |
| 5 | RB | R (SNES) |
| 6 | LT | L2 (PS1) |
| 7 | RT | R2 (PS1) |
| 8 | Back/Select | Select |
| 9 | Start | Start |
| 12-15 | D-Pad | Directions |

EmulatorJS expose un écran de remapping intégré (menu EmulatorJS → Controls). Pas besoin de reimplémenter.

---

## 9. Design System

### 9.1 Identité visuelle

**Concept** : "Salle d'arcade premium 2026" — obscurité profonde, néons couleur saturés, typographie rétro-futuriste, grain CRT subtil. Pas un dashboard SaaS générique. Digne d'Awwwards.

**Références** : Hotline Miami color palette, TRON Legacy darkness, Outrun aesthetic, mais avec une finesse 2026.

### 9.2 Palette de couleurs (tokens CSS)

```css
:root {
  /* Fonds */
  --color-void:        #040408;   /* Fond principal — noir absolu avec teinte bleue */
  --color-surface:     #0a0a12;   /* Cards, sidebar */
  --color-surface-alt: #12121e;   /* Hover states */
  --color-border:      #1e1e32;   /* Bordures subtiles */

  /* Néons signature */
  --neon-cyan:         #00f5ff;   /* Accent principal */
  --neon-magenta:      #ff0090;   /* Accent secondaire */
  --neon-yellow:       #ffe600;   /* Highlights arcade */
  --neon-purple:       #9b00ff;   /* Console badges */

  /* Glow effects */
  --glow-cyan:   0 0 10px #00f5ff, 0 0 30px #00f5ff40, 0 0 60px #00f5ff20;
  --glow-magenta: 0 0 10px #ff0090, 0 0 30px #ff009040;

  /* Texte */
  --text-primary:   #e8e8f0;
  --text-secondary: #8888aa;
  --text-muted:     #44445a;

  /* Console colors */
  --console-nes:     #e4000f;   /* Rouge Nintendo */
  --console-snes:    #503080;   /* Violet SNES */
  --console-n64:     #0a5c0a;   /* Vert N64 */
  --console-gba:     #8b008b;   /* Violet GBA */
  --console-ps1:     #00439c;   /* Bleu PlayStation */
  --console-genesis: #1a1aff;   /* Bleu Sega */
  --console-arcade:  #ff6600;   /* Orange Arcade */
}
```

### 9.3 Typographie

```css
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

/* Usage */
--font-display:  'Press Start 2P', monospace;  /* Titres, logo — pixel art */
--font-ui:       'Rajdhani', sans-serif;        /* Navigation, corps, UI */
--font-mono:     'Share Tech Mono', monospace;  /* IDs, metadata, codes */
```

**Hiérarchie** :
- Logo / H1 : `Press Start 2P`, 24-32px, neon-cyan, glow-cyan
- Console badges : `Rajdhani Bold`, 11px uppercase, letter-spacing 0.15em
- Card titles : `Rajdhani SemiBold`, 14-16px
- Metadata : `Share Tech Mono`, 11px, text-secondary

### 9.4 Effets visuels

**CRT Scanlines** (overlay CSS sur le container principal) :
```css
.crt-overlay::after {
  content: "";
  position: fixed; inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,0.08) 2px,
    rgba(0,0,0,0.08) 4px
  );
  pointer-events: none; z-index: 9999;
}
```

**Card hover** :
- Transform : `translateY(-6px) scale(1.02)`
- Border : `1px solid var(--neon-cyan)` + `box-shadow: var(--glow-cyan)`
- Transition : `0.2s cubic-bezier(0.34, 1.56, 0.64, 1)` (spring effect)

**Neon flicker** (logo uniquement) :
```css
@keyframes neon-flicker {
  0%, 95%, 100% { opacity: 1; }
  96%           { opacity: 0.7; }
  97%           { opacity: 1; }
  98%           { opacity: 0.5; }
  99%           { opacity: 0.9; }
}
```

**Loading state** (pendant chargement ROM) : animation "INSERT COIN" pixel art clignotante.

**Console color pills** : chaque card affiche un badge console coloré selon `--console-{slug}`.

### 9.5 Icônes consoles

SVG custom ou Font Awesome (CDN). Chaque console a son icône reconnaissable dans la sidebar et la ConsoleBar horizontale.

---

## 10. Contrats d'API (accès JS runtime)

### 10.1 `catalog.js`

```javascript
// API exposée
window.CatalogAPI = {
  async load(),                          // fetch + parse catalog.json
  getAll(),                              // GameEntry[]
  getById(id: string),                   // GameEntry | null
  getByConsole(slug: string),            // GameEntry[]
  getGenres(),                           // string[]
  getConsoles(),                         // { slug, label, count }[]
}
```

### 10.2 `search.js`

```javascript
// API exposée
window.SearchAPI = {
  init(games: GameEntry[]),              // Instancie Fuse.js
  query(term: string, filters: {         // Retourne GameEntry[] filtrés
    consoles?: string[],
    genres?: string[],
    yearMin?: number,
    yearMax?: number
  }),
  clearCache(),
}
```

### 10.3 `player.js`

```javascript
// Chargé uniquement sur player.html
async function initPlayer(gameId: string) {
  const game = await CatalogAPI.getById(gameId);
  // Injecte les variables EJS_ dans window
  // Ajoute dynamiquement le script loader
  // Lance le gamepad listener
}
```

---

## 11. Contraintes et risques

| Risque | Probabilité | Mitigation |
|---|---|---|
| Archive.org : ROM non disponible en direct (redirect) | Moyen | Utiliser l'API `/metadata/{id}/files` pour obtenir l'URL exacte du fichier. EmulatorJS accepte les ZIP. |
| CORS sur les ROMs Archive.org | Faible | Archive.org envoie `Access-Control-Allow-Origin: *` sur ses téléchargements publics |
| TheGamesDB rate limit (free tier) | Moyen | Le script build tourne une seule fois. Limiter à 1 req/s, persister les résultats en cache local JSON. |
| PS1 / Saturn / SegaCD : BIOS manquant | Haut | Ces consoles nécessitent un BIOS. L'utilisateur doit fournir les BIOS localement (hors catalogue). Documenter dans README. |
| EmulatorJS : performances N64 / PSP | Moyen | Avertissement dans l'UI pour N64/PSP. `mupen64plus_next` est gourmand en WebAssembly. |
| EmulatorJS CDN `stable` en rupture | Faible | Fallback sur un mirror GitHub Releases si nécessaire. |
| Jaquettes manquantes TheGamesDB | Moyen | Fallback sur placeholder SVG stylé "? UNKNOWN GAME" avec couleur console. |
| Catalog trop grand (>5000 jeux) | Faible | Limiter à 200 jeux/console au build. Pagination IntersectionObserver côté UI. |

---

## 12. Plan de test et validation

### Build du catalogue
- [ ] `python scripts/build_catalog.py --consoles nes snes --limit 5` génère un `catalog.json` valide
- [ ] Chaque entrée a bien `rom_url`, `cover_url`, `emulator_core` renseignés
- [ ] Validation JSON schema (jsonschema Python)

### UI — Accueil
- [ ] Ouvrir `index.html` en `file://` → les cards s'affichent avec jaquettes
- [ ] Recherche "mario" → retourne les bons jeux
- [ ] Filtre "NES" → grille filtrée sur NES uniquement
- [ ] Clic sur une card → redirige vers `player.html?id=...`

### UI — Player
- [ ] `player.html?id=nes-super-mario-bros` → EmulatorJS se charge
- [ ] Le ROM se charge depuis Archive.org (pas d'erreur CORS dans la console)
- [ ] L'émulateur démarre et le jeu est jouable
- [ ] Connexion manette Xbox One → badge "Manette connectée" apparaît
- [ ] Inputs manette fonctionnels en jeu

### Cross-console
- [ ] Tester 1 jeu sur chaque console prioritaire (NES, SNES, GBA, PS1, Genesis)
- [ ] Vérifier que le bon `EJS_core` est bien passé

### Performance
- [ ] Lighthouse score > 85 sur index.html (perf, accessibilité)
- [ ] First Contentful Paint < 2s sur connexion locale

---

## 13. Consoles prioritaires (ordre d'implémentation)

| Priorité | Console | Core | Raison |
|---|---|---|---|
| 1 | NES | `fceumm` | Catalogue massif, cores très stables |
| 2 | SNES | `snes9x` | Bibliothèque iconique, émulation parfaite |
| 3 | Game Boy Advance | `mgba` | mGBA = référence mondiale |
| 4 | Sega Genesis | `genesis_plus_gx` | Core excellent, large bibliothèque |
| 5 | Game Boy / GBC | `gambatte` | Même core, double catalogue |
| 6 | PlayStation 1 | `pcsx_rearmed` | Nécessite BIOS utilisateur |
| 7 | Nintendo 64 | `mupen64plus_next` | Performances variables, inclure avec avertissement |
| 8 | Arcade / MAME | `mame2003_plus` | Collection Internet Arcade archive.org |
| 9 | Atari 2600 | `stella2014` | Nostalgie, catalogue simple |
| 10 | Sega Master System | `smsplus` | Complète l'écosystème Sega |

---

## 14. Séquence de build (phases)

### Phase 1 — Fondations (Jour 1)
- Structure de fichiers complète
- Design system CSS (`base.css`, `design-system.css`)
- `catalog.js` : chargement et exposition de `window.CatalogAPI`
- `ui.js` : rendu des cards avec données mock (5 jeux hardcodés)
- Layout `index.html` complet avec sidebar + grille

### Phase 2 — Émulateur (Jour 2)
- `player.html` + `player.js` : instanciation EmulatorJS dynamique
- Test avec 1 ROM NES chargée depuis Archive.org
- `gamepad.js` : détection manette + badge UI

### Phase 3 — Recherche & Filtres (Jour 3)
- `search.js` : intégration Fuse.js
- Filtres console / genre / année
- Infinite scroll (IntersectionObserver)

### Phase 4 — Script Build (Jour 4)
- `archive_scraper.py` : recherche Archive.org + résolution URL fichier
- `thegamesdb.py` : métadonnées + jaquettes
- `build_catalog.py` : orchestration, génération `catalog.json` réel

### Phase 5 — Polish (Jour 5)
- Effets CRT, animations neon, hover effects
- Placeholders jaquettes manquantes
- Avertissements consoles lourdes (N64, PSP)
- Tests cross-console complets

---

## 15. Confidence Score

**Score global : 87 / 100**

| Domaine | Score | Commentaire |
|---|---|---|
| EmulatorJS cores | 95/100 | Cores vérifiés via doc officielle. CDN `stable` confirmé. |
| Archive.org API | 78/100 | Search API confirmée. URL ROM via `/metadata/{id}/files` solide. Certaines collections peuvent avoir des restrictions de téléchargement selon les items. |
| TheGamesDB API | 85/100 | Endpoints et auth confirmés via spec YAML. Platform IDs à vérifier au runtime (peuvent évoluer). |
| Faisabilité technique | 92/100 | Stack vanilla + EmulatorJS = très mature. Aucune dépendance fragile. |
| CORS Archive.org | 80/100 | Généralement open, mais quelques items peuvent être restreints. |
| BIOS PS1/Saturn | 70/100 | Dépend de l'utilisateur. Hors scope du catalogue automatique. |

**Point d'incertitude principal** : La disponibilité en téléchargement direct des ROMs sur Archive.org varie selon les collections et les items. Le script build doit implémenter une vérification préalable (`HEAD` request) et logger les ROMs non accessibles.
