/**
 * search.js — Intégration Fuse.js pour la recherche et le filtrage du catalogue.
 * Expose window.SearchAPI (vanilla JS, Fuse.js chargé via balise <script> dans le HTML).
 *
 * Dépendance :
 *   <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>
 *   (doit être chargé AVANT ce fichier)
 */

(function () {
  'use strict';

  /** @type {Fuse|null} */
  let _fuseInstance = null;

  /** @type {Array} Référence aux jeux fournis lors de l'init */
  let _allGames = [];

  // Options Fuse.js
  const FUSE_OPTIONS = {
    keys: [
      { name: 'title',     weight: 0.5 },
      { name: 'genre',     weight: 0.2 },
      { name: 'console',   weight: 0.1 },
      { name: 'developer', weight: 0.1 },
      { name: 'tags',      weight: 0.1 },
    ],
    threshold: 0.3,
    includeScore: true,
    minMatchCharLength: 2,
    ignoreLocation: true,
  };

  window.SearchAPI = {
    /**
     * Initialise Fuse.js avec la liste de jeux fournie.
     * Doit être appelé après CatalogAPI.load().
     * @param {Array} games
     */
    init(games) {
      if (typeof Fuse === 'undefined') {
        console.error('[SearchAPI] Fuse.js non disponible. Vérifiez que le CDN est chargé avant search.js.');
        return;
      }

      _allGames     = games;
      _fuseInstance = new Fuse(games, FUSE_OPTIONS);
      console.info(`[SearchAPI] Fuse.js initialisé avec ${games.length} jeux.`);
    },

    /**
     * Recherche et filtre les jeux.
     *
     * @param {string} term              — Terme de recherche (vide = tous)
     * @param {Object} [filters={}]      — Filtres additionnels
     * @param {string[]} [filters.consoles]  — Slugs de consoles
     * @param {string[]} [filters.genres]    — Genres (ex. "Platform")
     * @param {number}   [filters.yearMin]   — Année minimale incluse
     * @param {number}   [filters.yearMax]   — Année maximale incluse
     * @returns {Array} Jeux correspondants, triés par pertinence
     */
    query(term = '', filters = {}) {
      if (!_fuseInstance && _allGames.length === 0) {
        console.warn('[SearchAPI] SearchAPI non initialisé. Appelez SearchAPI.init(games) d\'abord.');
        return [];
      }

      // 1. Recherche textuelle Fuse ou retour complet
      let results;

      const trimmed = term.trim();

      if (trimmed.length === 0 || !_fuseInstance) {
        // Pas de terme : on part de l'ensemble complet, on simulera un score uniforme
        results = _allGames;
      } else {
        // Fuse retourne [{ item, score, refIndex }]
        const fuseResults = _fuseInstance.search(trimmed);
        // Extraire les items (déjà triés du plus pertinent au moins pertinent)
        results = fuseResults.map(r => r.item);
      }

      // 2. Application des filtres
      const { consoles, genres, yearMin, yearMax } = filters;

      if (consoles && consoles.length > 0) {
        results = results.filter(g => consoles.includes(g.console_slug));
      }

      if (genres && genres.length > 0) {
        results = results.filter(g =>
          Array.isArray(g.genre) && g.genre.some(genre => genres.includes(genre))
        );
      }

      if (typeof yearMin === 'number' && !isNaN(yearMin)) {
        results = results.filter(g => g.year >= yearMin);
      }

      if (typeof yearMax === 'number' && !isNaN(yearMax)) {
        results = results.filter(g => g.year <= yearMax);
      }

      return results;
    },

    /**
     * Réinitialise l'instance Fuse (utile si le catalogue change).
     */
    clearCache() {
      _fuseInstance = null;
      _allGames     = [];
      console.info('[SearchAPI] Cache réinitialisé.');
    },
  };

})();
