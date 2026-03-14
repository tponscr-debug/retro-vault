/**
 * player.js — Module de la page émulateur.
 * Charge le jeu depuis CatalogAPI, injecte les variables EmulatorJS,
 * puis charge dynamiquement le loader EmulatorJS.
 * Dépend de : CatalogAPI (catalog.js)
 * Expose initPlayer() en global.
 */

// Mapping slug → label complet pour le panneau info
const CONSOLE_FULL_LABELS = {
  nes:       'NES',
  snes:      'Super NES',
  n64:       'Nintendo 64',
  gba:       'Game Boy Advance',
  gb:        'Game Boy',
  gbc:       'Game Boy Color',
  ps1:       'PlayStation',
  genesis:   'Mega Drive / Genesis',
  sms:       'Master System',
  gg:        'Game Gear',
  arcade:    'Arcade',
  atari2600: 'Atari 2600',
};

// Mapping slug → touches clavier (EmulatorJS defaults)
const CONTROLS_MAP = {
  _default: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'Z',        action: 'A' },
    { key: 'X',        action: 'B' },
    { key: 'Enter',    action: 'Start' },
    { key: 'R.Shift',  action: 'Select' },
    { key: 'Esc',      action: 'Menu' },
  ],
  snes: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'Z',        action: 'A' },
    { key: 'X',        action: 'B' },
    { key: 'A',        action: 'Y' },
    { key: 'S',        action: 'X' },
    { key: 'Q',        action: 'L' },
    { key: 'W',        action: 'R' },
    { key: 'Enter',    action: 'Start' },
    { key: 'R.Shift',  action: 'Select' },
    { key: 'Esc',      action: 'Menu' },
  ],
  gba: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'Z',        action: 'A' },
    { key: 'X',        action: 'B' },
    { key: 'Q',        action: 'L' },
    { key: 'W',        action: 'R' },
    { key: 'Enter',    action: 'Start' },
    { key: 'R.Shift',  action: 'Select' },
    { key: 'Esc',      action: 'Menu' },
  ],
  n64: [
    { key: '← ↑ ↓ →', action: 'Stick' },
    { key: 'Z',        action: 'A' },
    { key: 'X',        action: 'B' },
    { key: 'C',        action: 'C-Up' },
    { key: 'V',        action: 'C-Down' },
    { key: 'F',        action: 'C-Left' },
    { key: 'G',        action: 'C-Right' },
    { key: 'Q',        action: 'L' },
    { key: 'W',        action: 'R' },
    { key: 'S',        action: 'Z-Trig' },
    { key: 'Enter',    action: 'Start' },
    { key: 'Esc',      action: 'Menu' },
  ],
  genesis: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'X',        action: 'B  (saut)' },
    { key: 'Z',        action: 'C  (tir)' },
    { key: 'S',        action: 'A  (spécial)' },
    { key: 'A',        action: 'X' },
    { key: 'Q',        action: 'Y' },
    { key: 'E',        action: 'Z' },
    { key: 'V',        action: 'Mode' },
    { key: 'Enter',    action: 'Start' },
    { key: 'Esc',      action: 'Menu' },
  ],
  sms: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'Z',        action: 'Btn 1' },
    { key: 'X',        action: 'Btn 2' },
    { key: 'Enter',    action: 'Start' },
    { key: 'Esc',      action: 'Menu' },
  ],
  gg: [
    { key: '← ↑ ↓ →', action: 'D-Pad' },
    { key: 'Z',        action: 'Btn 1' },
    { key: 'X',        action: 'Btn 2' },
    { key: 'Enter',    action: 'Start' },
    { key: 'Esc',      action: 'Menu' },
  ],
  atari2600: [
    { key: '← ↑ ↓ →', action: 'Joystick' },
    { key: 'Z',        action: 'Fire' },
    { key: 'Enter',    action: 'Reset' },
    { key: 'Esc',      action: 'Menu' },
  ],
  arcade: [
    { key: '← ↑ ↓ →', action: 'Joystick' },
    { key: 'Z',        action: 'Btn 1' },
    { key: 'X',        action: 'Btn 2' },
    { key: 'A',        action: 'Btn 3' },
    { key: 'S',        action: 'Btn 4' },
    { key: '1',        action: '1P Start' },
    { key: '2',        action: '2P Start' },
    { key: '5',        action: 'Coin' },
    { key: 'Esc',      action: 'Menu' },
  ],
};

// Mapping slug → label court pour les badges
const BADGE_LABELS = {
  nes:       'NES',
  snes:      'SNES',
  n64:       'N64',
  gba:       'GBA',
  gb:        'GB',
  gbc:       'GBC',
  ps1:       'PS1',
  genesis:   'GEN',
  sms:       'SMS',
  gg:        'GG',
  arcade:    'ARC',
  atari2600: 'ATR',
};

// ─── Helpers DOM ─────────────────────────────────────────────────────────────
function setEl(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value || '—';
}

function setAttr(id, attr, value) {
  const el = document.getElementById(id);
  if (el && value) el.setAttribute(attr, value);
}

function toggleClass(id, cls, force) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle(cls, force);
}

// ─── Overlay de chargement ───────────────────────────────────────────────────
function hideLoadingOverlay() {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  overlay.style.transition = 'opacity 0.6s ease';
  overlay.style.opacity    = '0';
  setTimeout(() => overlay.remove(), 650);
}

// Barre de progression simulée (EmulatorJS ne fournit pas toujours d'events)
function startProgressBar() {
  const bar = document.getElementById('loading-bar');
  if (!bar) return;

  let progress = 0;
  const tick = () => {
    // Progression rapide jusqu'à 85%, puis lente jusqu'à 95%
    const step = progress < 85 ? Math.random() * 4 + 1 : Math.random() * 0.5;
    progress = Math.min(progress + step, 95);
    bar.style.width = `${progress}%`;

    if (progress < 95) {
      setTimeout(tick, 120 + Math.random() * 80);
    }
  };
  tick();
}

function completeProgressBar() {
  const bar = document.getElementById('loading-bar');
  if (bar) bar.style.width = '100%';
  setTimeout(hideLoadingOverlay, 400);
}

// ─── Remplissage du panneau info ─────────────────────────────────────────────
function fillInfoPanel(game) {
  const slug = game.console_slug || '';

  // Cover
  const cover = document.getElementById('player-cover-large');
  if (cover) {
    if (game.cover_url) {
      cover.src = game.cover_url;
      cover.alt = game.title || '';
      cover.onerror = () => { cover.style.display = 'none'; };
    } else {
      cover.style.display = 'none';
    }
  }

  // Header : titre + badge
  setEl('player-game-title', game.title);

  const badge = document.getElementById('player-console-badge');
  if (badge) {
    badge.textContent = BADGE_LABELS[slug] || slug.toUpperCase();
    badge.className   = `console-badge-${slug}`;
  }

  // Lignes info
  setEl('info-console',    CONSOLE_FULL_LABELS[slug] || slug.toUpperCase());
  setEl('info-year',       game.year ? String(game.year) : null);
  setEl('info-genre',      Array.isArray(game.genre) ? game.genre.join(', ') : game.genre);
  setEl('info-developer',  game.developer);
  setEl('info-players',    game.players ? `${game.players}P` : null);

  // Description
  const desc = document.getElementById('player-description');
  if (desc) desc.textContent = game.description || '';

  // Avertissement BIOS
  const biosWarn = document.getElementById('bios-warning');
  if (biosWarn) {
    toggleClass('bios-warning', 'hidden', !game.bios_required);
  }

  // Contrôles clavier
  fillControlsPanel(slug);
}

// ─── Panneau de contrôles ────────────────────────────────────────────────────
function fillControlsPanel(slug) {
  const panel = document.getElementById('controls-panel');
  if (!panel) return;

  const bindings = CONTROLS_MAP[slug] || CONTROLS_MAP._default;
  panel.innerHTML = bindings.map(b =>
    `<div class="control-row">
       <span class="control-key">${b.key}</span>
       <span class="control-action">${b.action}</span>
     </div>`
  ).join('');
}

// ─── Proxy CORS local ────────────────────────────────────────────────────────
function buildProxyUrl(romUrl, romFilename) {
  if (!romUrl) return null;
  // Inclure le nom de fichier dans le PATH du proxy (ex: /proxy/tron.zip)
  // pour qu'EmulatorJS puisse détecter l'extension du ROM (.nes, .zip, .gba, etc.)
  const filename = romFilename
    ? encodeURIComponent(romFilename)
    : encodeURIComponent(romUrl.split('/').pop().split('?')[0]) || 'rom';
  return `http://localhost:8236/proxy/${filename}?url=${encodeURIComponent(romUrl)}`;
}

// ─── Correctif clavier AZERTY ────────────────────────────────────────────────
// Sur AZERTY, les touches Z/A/Q/W envoient des keyCodes différents de QWERTY :
//   AZERTY Z → keyCode 87 (W QWERTY)   AZERTY W → keyCode 90 (Z QWERTY)
//   AZERTY A → keyCode 81 (Q QWERTY)   AZERTY Q → keyCode 65 (A QWERTY)
// EmulatorJS utilise les keyCodes → il faut remapper pour que les labels affichés
// correspondent aux touches physiques sur un clavier français.
function buildDefaultControls() {
  const lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
  const isAZERTY = lang.startsWith('fr') || lang.startsWith('be');
  if (!isAZERTY) return undefined;

  // Remapping AZERTY : on garde les labels (Z, A, Q) mais on associe le bon keyCode physique
  // Button 0 (B/jump)  → X=88  (identique sur AZERTY ✓)
  // Button 1 (Y/spéc)  → S=83  (identique ✓)
  // Button 2 (Select)  → V=86  (identique ✓)
  // Button 3 (Start)   → Enter=13 (identique ✓)
  // Button 8 (A/tir)   → AZERTY Z → keyCode 87 au lieu de 90
  // Button 9 (X)       → AZERTY A → keyCode 81 au lieu de 65
  // Button 10 (L)      → AZERTY Q → keyCode 65 au lieu de 81
  // Button 11 (R)      → E=69   (identique ✓)
  return {
    0: {
      0:  { value: '88' },  // B   → X
      1:  { value: '83' },  // Y   → S
      2:  { value: '86' },  // Sel → V
      3:  { value: '13' },  // Sta → Enter
      4:  { value: '38' },  // Up
      5:  { value: '40' },  // Down
      6:  { value: '37' },  // Left
      7:  { value: '39' },  // Right
      8:  { value: '87' },  // A   → AZERTY Z (keyCode 87)
      9:  { value: '81' },  // X   → AZERTY A (keyCode 81)
      10: { value: '65' },  // L   → AZERTY Q (keyCode 65)
      11: { value: '69' },  // R   → E
    },
  };
}

// ─── Injection EmulatorJS ────────────────────────────────────────────────────
function injectEmulator(game) {
  const romUrl = buildProxyUrl(game.rom_url, game.rom_filename);

  // Variables globales requises par EmulatorJS (doivent être définies avant loader.js)
  window.EJS_player        = '#emulator-container';
  window.EJS_gameUrl       = romUrl;
  window.EJS_core          = game.emulator_core;
  window.EJS_pathtodata    = 'https://cdn.emulatorjs.org/stable/data/';
  window.EJS_startOnLoaded = true;
  window.EJS_gameName      = game.title || '';

  // Correctif AZERTY : ajuste les keyCodes par défaut
  const controls = buildDefaultControls();
  if (controls) window.EJS_defaultControls = controls;

  // BIOS pour PS1 ou jeux qui l'exigent
  if (game.bios_required && game.bios_url) {
    window.EJS_biosUrl = game.bios_url;
  }

  // Callback EmulatorJS : déclenché quand l'émulateur est prêt
  window.EJS_onGameStart = () => {
    completeProgressBar();
    // S'assurer que le conteneur a le focus clavier
    const container = document.getElementById('emulator-container');
    if (container) {
      container.focus();
      // Redonner le focus si l'utilisateur clique ailleurs puis revient
      document.addEventListener('keydown', () => {
        if (document.activeElement !== container) container.focus();
      }, { capture: true, passive: true });
    }
  };

  // Charger dynamiquement le loader
  const script = document.createElement('script');
  script.src   = 'https://cdn.emulatorjs.org/stable/data/loader.js';
  script.onerror = () => {
    console.error('[player.js] Échec du chargement du loader EmulatorJS.');
    // Masquer l'overlay quand même pour éviter un écran bloqué
    completeProgressBar();
  };
  document.body.appendChild(script);

  // Fallback : si EJS_onGameStart n'est jamais appelé au bout de 30s
  setTimeout(() => {
    const overlay = document.getElementById('loading-overlay');
    if (overlay && overlay.parentNode) {
      completeProgressBar();
    }
  }, 30000);
}

// ─── Bouton retour ───────────────────────────────────────────────────────────
function bindBackButton() {
  const btn = document.getElementById('back-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = 'index.html';
    }
  });
}

// ─── Point d'entrée ──────────────────────────────────────────────────────────
async function initPlayer() {
  // 1. Lire ?id= depuis l'URL
  const params = new URLSearchParams(window.location.search);
  const gameId = params.get('id');

  if (!gameId) {
    window.location.replace('index.html');
    return;
  }

  // 2. Charger le catalogue si besoin
  let game = null;
  try {
    await CatalogAPI.load();
    game = CatalogAPI.getById(gameId);
  } catch (err) {
    console.error('[player.js] Erreur chargement catalogue :', err);
    window.location.replace('index.html');
    return;
  }

  // 3. Jeu introuvable
  if (!game) {
    console.warn(`[player.js] Jeu introuvable : ${gameId}`);
    window.location.replace('index.html');
    return;
  }

  // 4. Remplir le panneau info
  fillInfoPanel(game);

  // 5. Bouton retour
  bindBackButton();

  // 6. Démarrer la barre de progression
  startProgressBar();

  // 7. Injecter et lancer l'émulateur
  injectEmulator(game);
}
