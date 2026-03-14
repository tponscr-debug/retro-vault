/**
 * ui.js — Module de rendu UI principal.
 * Gère la grille de jeux, les filtres console/genre/année, l'infinite scroll.
 * Dépend de : CatalogAPI (catalog.js), SearchAPI (search.js), Fuse.js
 * Expose window.UI
 */

(function () {
  'use strict';

  // ─── Mapping slug → label court pour les badges ──────────────────────────
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

  // ─── Couleurs associées à chaque console (pour le bouton ALL actif neutre) ─
  const CONSOLE_BAR_ALL = 'ALL';

  window.UI = {
    // ── Config ──────────────────────────────────────────────────────────────
    PAGE_SIZE: 40,
    _page: 0,
    _currentGames: [],
    _observer: null,

    // ── Références DOM ──────────────────────────────────────────────────────
    _grid: null,
    _sentinel: null,
    _gamesCount: null,
    _emptyState: null,
    _searchInput: null,
    _consoleBar: null,
    _filterConsoleList: null,
    _filterGenreList: null,
    _yearMin: null,
    _yearMax: null,
    _searchResultsCount: null,

    // ── État des filtres ─────────────────────────────────────────────────────
    _activeConsoleSlug: null, // null = ALL
    _checkedConsoles: new Set(),
    _checkedGenres: new Set(),

    // ────────────────────────────────────────────────────────────────────────
    init() {
      // Récupérer les éléments DOM
      this._grid               = document.getElementById('game-grid');
      this._sentinel           = document.getElementById('loading-sentinel');
      this._gamesCount         = document.getElementById('games-count');
      this._emptyState         = document.getElementById('empty-state');
      this._searchInput        = document.getElementById('search-input');
      this._consoleBar         = document.getElementById('console-bar');
      this._filterConsoleList  = document.getElementById('filter-console-list');
      this._filterGenreList    = document.getElementById('filter-genre-list');
      this._yearMin            = document.getElementById('year-input-min');
      this._yearMax            = document.getElementById('year-input-max');
      this._searchResultsCount = document.getElementById('search-results-count');

      // ── Search avec debounce ─────────────────────────────────────────────
      if (this._searchInput) {
        this._searchInput.addEventListener(
          'input',
          this._debounce(() => this._applyFilters(), 300)
        );
      }

      // ── Filtres année ────────────────────────────────────────────────────
      const yearHandler = this._debounce(() => this._applyFilters(), 400);
      if (this._yearMin) this._yearMin.addEventListener('input', yearHandler);
      if (this._yearMax) this._yearMax.addEventListener('input', yearHandler);

      // ── IntersectionObserver pour l'infinite scroll ──────────────────────
      if (this._sentinel) {
        this._observer = new IntersectionObserver(
          (entries) => {
            entries.forEach(entry => {
              if (entry.isIntersecting) {
                this._loadNextPage();
              }
            });
          },
          { rootMargin: '200px' }
        );
        this._observer.observe(this._sentinel);
      }
    },

    // ────────────────────────────────────────────────────────────────────────
    renderConsoleBar(consoles) {
      if (!this._consoleBar) return;
      this._consoleBar.innerHTML = '';

      // Bouton ALL
      const btnAll = document.createElement('button');
      btnAll.className = 'console-btn active';
      btnAll.textContent = CONSOLE_BAR_ALL;
      btnAll.dataset.slug = '';
      btnAll.addEventListener('click', () => {
        this._activeConsoleSlug = null;
        this._syncConsoleBarActive('');
        this._applyFilters();
      });
      this._consoleBar.appendChild(btnAll);

      // Un bouton par console
      consoles.forEach(({ slug, label, count }) => {
        const btn = document.createElement('button');
        btn.className = 'console-btn';
        btn.dataset.slug = slug;
        btn.textContent = `${label} (${count})`;
        btn.addEventListener('click', () => {
          // Toggle : si déjà actif → revenir à ALL
          if (this._activeConsoleSlug === slug) {
            this._activeConsoleSlug = null;
            this._syncConsoleBarActive('');
          } else {
            this._activeConsoleSlug = slug;
            this._syncConsoleBarActive(slug);
          }
          this._applyFilters();
        });
        this._consoleBar.appendChild(btn);
      });
    },

    _syncConsoleBarActive(activeSlug) {
      if (!this._consoleBar) return;
      this._consoleBar.querySelectorAll('.console-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.slug === activeSlug);
      });
    },

    // ────────────────────────────────────────────────────────────────────────
    renderFilters(consoles, genres) {
      // ── Consoles ──
      if (this._filterConsoleList) {
        this._filterConsoleList.innerHTML = '';
        consoles.forEach(({ slug, label }) => {
          const wrapper = document.createElement('div');
          wrapper.className = 'filter-checkbox';

          const id = `fc-${slug}`;
          const checkbox = document.createElement('input');
          checkbox.type    = 'checkbox';
          checkbox.id      = id;
          checkbox.value   = slug;
          checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
              this._checkedConsoles.add(slug);
            } else {
              this._checkedConsoles.delete(slug);
            }
            this._applyFilters();
          });

          const lbl = document.createElement('label');
          lbl.htmlFor = id;
          lbl.appendChild(checkbox);
          lbl.append(label);

          wrapper.appendChild(lbl);
          this._filterConsoleList.appendChild(wrapper);
        });
      }

      // ── Genres ──
      if (this._filterGenreList) {
        this._filterGenreList.innerHTML = '';
        genres.forEach(genre => {
          const wrapper = document.createElement('div');
          wrapper.className = 'filter-checkbox';

          const id = `fg-${genre.replace(/\s+/g, '-').toLowerCase()}`;
          const checkbox = document.createElement('input');
          checkbox.type    = 'checkbox';
          checkbox.id      = id;
          checkbox.value   = genre;
          checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
              this._checkedGenres.add(genre);
            } else {
              this._checkedGenres.delete(genre);
            }
            this._applyFilters();
          });

          const lbl = document.createElement('label');
          lbl.htmlFor = id;
          lbl.appendChild(checkbox);
          lbl.append(genre);

          wrapper.appendChild(lbl);
          this._filterGenreList.appendChild(wrapper);
        });
      }
    },

    // ────────────────────────────────────────────────────────────────────────
    renderGames(games) {
      this._currentGames = games;
      this._page = 0;

      if (this._grid) {
        this._grid.innerHTML = '';
      }

      if (games.length === 0) {
        this.showEmpty(true);
      } else {
        this.showEmpty(false);
        this._loadNextPage();
      }

      // Compteur
      if (this._gamesCount) {
        this._gamesCount.textContent = `${games.length} JEU${games.length !== 1 ? 'X' : ''}`;
      }
      if (this._searchResultsCount) {
        const term = this._searchInput ? this._searchInput.value.trim() : '';
        this._searchResultsCount.textContent = term ? `${games.length} résultat${games.length !== 1 ? 's' : ''}` : '';
      }
    },

    // ────────────────────────────────────────────────────────────────────────
    _loadNextPage() {
      if (!this._grid) return;

      const start = this._page * this.PAGE_SIZE;
      const end   = start + this.PAGE_SIZE;
      const slice = this._currentGames.slice(start, end);

      if (slice.length === 0) return;

      const fragment = document.createDocumentFragment();
      slice.forEach(game => {
        fragment.appendChild(this._createCard(game));
      });
      this._grid.appendChild(fragment);

      this._page++;
    },

    // ────────────────────────────────────────────────────────────────────────
    _createCard(game) {
      const card = document.createElement('div');
      card.className   = 'game-card';
      card.dataset.id  = game.id;

      // Animation delay décalé pour l'effet cascade
      const indexInGrid = this._grid ? this._grid.children.length : 0;
      card.style.animationDelay = `${Math.min(indexInGrid * 18, 500)}ms`;

      // ── Cover image ──
      if (game.cover_url) {
        const img = document.createElement('img');
        img.className = 'game-card__cover';
        img.alt       = game.title || '';
        img.loading   = 'lazy';
        img.src       = game.cover_url;
        img.onerror   = () => {
          img.style.display = 'none';
          card.appendChild(this._createPlaceholder(game.title));
        };
        card.appendChild(img);
      } else {
        card.appendChild(this._createPlaceholder(game.title));
      }

      // ── Overlay ──
      const overlay = document.createElement('div');
      overlay.className = 'game-card__overlay';

      // Badge console
      const slug  = game.console_slug || '';
      const badge = document.createElement('span');
      badge.className = `game-card__console-badge console-badge-${slug}`;
      badge.textContent = this._getConsoleBadgeLabel(slug);
      overlay.appendChild(badge);

      // Titre
      const title = document.createElement('div');
      title.className   = 'game-card__title';
      title.textContent = game.title || 'Unknown';
      overlay.appendChild(title);

      // Meta (année + genre)
      const meta = document.createElement('div');
      meta.className = 'game-card__meta';
      if (game.year) {
        const yr = document.createElement('span');
        yr.textContent = game.year;
        meta.appendChild(yr);
      }
      if (Array.isArray(game.genre) && game.genre.length > 0) {
        const gr = document.createElement('span');
        gr.textContent = game.genre[0];
        meta.appendChild(gr);
      }
      overlay.appendChild(meta);
      card.appendChild(overlay);

      // ── Navigation vers player ──
      card.addEventListener('click', () => {
        window.location.href = `player.html?id=${encodeURIComponent(game.id)}`;
      });

      return card;
    },

    _createPlaceholder(title) {
      const ph = document.createElement('div');
      ph.className = 'game-card__placeholder';
      if (title) {
        const t = document.createElement('span');
        t.textContent = title;
        ph.appendChild(t);
      }
      return ph;
    },

    // ────────────────────────────────────────────────────────────────────────
    _getConsoleBadgeLabel(slug) {
      return BADGE_LABELS[slug] || (slug ? slug.toUpperCase().slice(0, 5) : '???');
    },

    // ────────────────────────────────────────────────────────────────────────
    _debounce(fn, delay) {
      let timer = null;
      return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
      };
    },

    // ────────────────────────────────────────────────────────────────────────
    _applyFilters() {
      if (typeof SearchAPI === 'undefined') return;

      const term = this._searchInput ? this._searchInput.value : '';

      // Consoles : la console-bar a priorité sur les checkboxes sidebar
      let consoles = [];
      if (this._activeConsoleSlug) {
        consoles = [this._activeConsoleSlug];
      } else if (this._checkedConsoles.size > 0) {
        consoles = Array.from(this._checkedConsoles);
      }

      const genres  = this._checkedGenres.size > 0 ? Array.from(this._checkedGenres) : [];
      const yearMin = this._yearMin && this._yearMin.value ? parseInt(this._yearMin.value, 10) : undefined;
      const yearMax = this._yearMax && this._yearMax.value ? parseInt(this._yearMax.value, 10) : undefined;

      const filters = {};
      if (consoles.length > 0) filters.consoles = consoles;
      if (genres.length > 0)   filters.genres   = genres;
      if (yearMin)              filters.yearMin  = yearMin;
      if (yearMax)              filters.yearMax  = yearMax;

      const results = SearchAPI.query(term, filters);
      this.renderGames(results);
    },

    // ────────────────────────────────────────────────────────────────────────
    showLoading(bool) {
      if (this._sentinel) {
        this._sentinel.style.visibility = bool ? 'visible' : 'hidden';
      }
    },

    showEmpty(bool) {
      if (this._emptyState) {
        this._emptyState.classList.toggle('hidden', !bool);
      }
    },
  };

})();
