/**
 * gamepad.js — Détection et affichage du statut de la manette (Xbox One).
 * Auto-initialisé au chargement, aucun export.
 *
 * Mapping Xbox One (référence) :
 * ─────────────────────────────────────────────────────────────────────
 * Boutons (buttons[index]) :
 *   0 = A         1 = B         2 = X         3 = Y
 *   4 = LB        5 = RB        6 = LT        7 = RT
 *   8 = Select    9 = Start     10 = LS       11 = RS
 *   12 = D-Up     13 = D-Down   14 = D-Left   15 = D-Right
 *   16 = Xbox (Guide)
 *
 * Axes (axes[index]) :
 *   0 = Left Stick X    1 = Left Stick Y
 *   2 = Right Stick X   3 = Right Stick Y
 *   (valeurs : -1.0 → 1.0)
 * ─────────────────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  /**
   * Met à jour le badge #gamepad-badge selon l'état de connexion.
   * @param {boolean} connected
   * @param {string}  [id='']  — Identifiant de la manette (fourni par l'API)
   */
  function showGamepadStatus(connected, id = '') {
    const badge = document.getElementById('gamepad-badge');
    if (!badge) return;

    if (connected) {
      badge.classList.add('active');
      badge.title = `Manette connectée : ${id}`;
    } else {
      badge.classList.remove('active');
      badge.title = 'Aucune manette détectée';
    }
  }

  // ─── Événements Gamepad API ───────────────────────────────────────────────

  window.addEventListener('gamepadconnected', (event) => {
    const { id, index } = event.gamepad;
    console.info(`[Gamepad] Manette connectée (index ${index}) : ${id}`);
    showGamepadStatus(true, id);
  });

  window.addEventListener('gamepaddisconnected', (event) => {
    const { id, index } = event.gamepad;
    console.info(`[Gamepad] Manette déconnectée (index ${index}) : ${id}`);

    // Vérifier si d'autres manettes sont encore connectées
    const remaining = navigator.getGamepads
      ? Array.from(navigator.getGamepads()).filter(Boolean)
      : [];

    if (remaining.length > 0) {
      const other = remaining[0];
      showGamepadStatus(true, other.id);
    } else {
      showGamepadStatus(false, id);
    }
  });

  // ─── Init au chargement (manette déjà branchée avant la page) ────────────
  window.addEventListener('DOMContentLoaded', () => {
    if (!navigator.getGamepads) return;

    const pads = Array.from(navigator.getGamepads()).filter(Boolean);
    if (pads.length > 0) {
      showGamepadStatus(true, pads[0].id);
    } else {
      showGamepadStatus(false);
    }
  });

})();
