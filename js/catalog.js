/**
 * catalog.js — Module de chargement et d'accès au catalogue de jeux rétro.
 * Expose window.CatalogAPI (aucun import, vanilla JS pur).
 */

(function () {
  'use strict';

  const CONSOLE_LABELS = {
    nes:       'NES',
    snes:      'SNES',
    n64:       'N64',
    gba:       'GBA',
    gb:        'Game Boy',
    gbc:       'Game Boy Color',
    ps1:       'PS1',
    genesis:   'Genesis',
    sms:       'Master System',
    gg:        'Game Gear',
    arcade:    'Arcade',
    atari2600: 'Atari 2600',
  };

  window.CatalogAPI = {
    _games: [],
    _loaded: false,

    /**
     * Charge le catalogue depuis data/catalog.json.
     * @returns {Promise<Array>} Liste des jeux
     */
    async load() {
      if (this._loaded) return this._games;

      try {
        const response = await fetch('./data/catalog.json');

        if (!response.ok) {
          throw new Error(`Erreur HTTP ${response.status} lors du chargement du catalogue.`);
        }

        const data = await response.json();

        if (!data || !Array.isArray(data.games)) {
          throw new Error('Format du catalogue invalide : propriété "games" manquante ou non-tableau.');
        }

        this._games = data.games;
        this._loaded = true;

        console.info(`[CatalogAPI] ${this._games.length} jeux chargés (v${data.version}).`);
        return this._games;

      } catch (err) {
        console.error('[CatalogAPI] Impossible de charger le catalogue :', err);
        this._games = [];
        throw err;
      }
    },

    /** Retourne tous les jeux chargés. */
    getAll() {
      return this._games;
    },

    /**
     * Retourne un jeu par son identifiant unique.
     * @param {string} id
     * @returns {Object|null}
     */
    getById(id) {
      return this._games.find(g => g.id === id) || null;
    },

    /**
     * Retourne tous les jeux d'une console donnée.
     * @param {string} slug — ex. "nes", "snes"
     * @returns {Array}
     */
    getByConsole(slug) {
      return this._games.filter(g => g.console_slug === slug);
    },

    /**
     * Retourne la liste unique de tous les genres présents dans le catalogue.
     * @returns {string[]}
     */
    getGenres() {
      const set = new Set();
      this._games.forEach(g => {
        if (Array.isArray(g.genre)) {
          g.genre.forEach(genre => set.add(genre));
        }
      });
      return Array.from(set).sort();
    },

    /**
     * Retourne la liste des consoles avec leur label et le nombre de jeux.
     * @returns {Array<{slug: string, label: string, count: number}>}
     */
    getConsoles() {
      const counts = {};
      this._games.forEach(g => {
        const slug = g.console_slug;
        counts[slug] = (counts[slug] || 0) + 1;
      });

      return Object.entries(counts)
        .map(([slug, count]) => ({
          slug,
          label: CONSOLE_LABELS[slug] || slug.toUpperCase(),
          count,
        }))
        .sort((a, b) => a.label.localeCompare(b.label));
    },

    /**
     * Retourne des statistiques globales sur le catalogue.
     * @returns {{ total: number, byConsole: Object, byGenre: Object }}
     */
    getStats() {
      const byConsole = {};
      const byGenre   = {};

      this._games.forEach(g => {
        // Par console
        const slug = g.console_slug;
        byConsole[slug] = (byConsole[slug] || 0) + 1;

        // Par genre
        if (Array.isArray(g.genre)) {
          g.genre.forEach(genre => {
            byGenre[genre] = (byGenre[genre] || 0) + 1;
          });
        }
      });

      return {
        total: this._games.length,
        byConsole,
        byGenre,
      };
    },
  };

})();
