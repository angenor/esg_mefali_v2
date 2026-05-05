<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { useReducedMotion } from "~/composables/useReducedMotion";
import {
  HomeIcon,
  ChartBarIcon,
  CheckCircleIcon,
  BellIcon,
  DocumentTextIcon,
  ArrowRightIcon,
} from "@heroicons/vue/24/outline";

definePageMeta({ layout: false });

if (import.meta.env.PROD) {
  throw createError({ statusCode: 404, fatal: true, message: "Page introuvable" });
}

const reduced = useReducedMotion();

const neutralShades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const brandShades = [50, 100, 200, 300, 400, 500, 600, 700, 900];
const semanticFamilies = ["success", "warning", "danger", "info"] as const;
const semanticTones = [50, 500, 700];
const fontSizes = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl"];
const spacings = [1, 2, 3, 4, 6, 8, 12, 16, 24];
const radii = ["sm", "md", "lg", "xl", "2xl", "full"];
const shadows = ["xs", "sm", "md", "lg", "xl"];

const computedSwatches = ref<Record<string, string>>({});

function readVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function refreshSwatches(): void {
  const map: Record<string, string> = {};
  for (const n of neutralShades) map[`--color-neutral-${n}`] = readVar(`--color-neutral-${n}`);
  for (const b of brandShades) map[`--color-brand-${b}`] = readVar(`--color-brand-${b}`);
  for (const fam of semanticFamilies) {
    for (const t of semanticTones) map[`--color-${fam}-${t}`] = readVar(`--color-${fam}-${t}`);
  }
  for (const r of ["bg", "surface", "text", "text-muted", "border", "focus-ring"]) {
    map[`--color-${r}`] = readVar(`--color-${r}`);
  }
  computedSwatches.value = map;
}

const darkPreview = ref(false);
function toggleDark(): void {
  darkPreview.value = !darkPreview.value;
  if (darkPreview.value) {
    document.documentElement.setAttribute("data-theme", "dark");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  setTimeout(refreshSwatches, 50);
}

onMounted(() => {
  refreshSwatches();
});

onBeforeUnmount(() => {
  document.documentElement.removeAttribute("data-theme");
});

const motionStateLabel = computed(() =>
  reduced.value ? "prefers-reduced-motion: reduce ✅" : "prefers-reduced-motion: reduce ❌",
);

const animateKey = ref(0);
function pulse(): void {
  animateKey.value += 1;
}
</script>

<template>
  <div class="ds-root">
    <header class="ds-header">
      <h1>Design System — ESG Mefali</h1>
      <p class="muted">
        Page de référence (DEV uniquement). Consomme exclusivement les tokens définis dans
        <code>tokens.css</code>. Voir <code>specs/036-design-system-tokens/</code>.
      </p>

      <nav class="anchors" aria-label="Sections">
        <a href="#palette-neutre">Palette neutre</a>
        <a href="#palette-brand">Palette brand</a>
        <a href="#semantiques">Sémantiques</a>
        <a href="#roles">Rôles surface</a>
        <a href="#typo">Typographie</a>
        <a href="#spacing">Spacing</a>
        <a href="#radius">Radius</a>
        <a href="#shadows">Shadows</a>
        <a href="#focus">Focus</a>
        <a href="#motion">Motion</a>
        <a href="#disabled">États désactivés</a>
        <a href="#icons">Iconographie</a>
        <a href="#logo">Logo</a>
        <a href="#empty-states">Empty states</a>
        <a href="#dark">Mode sombre</a>
      </nav>
    </header>

    <section id="palette-neutre">
      <h2>Palette neutre</h2>
      <div class="row">
        <div
          v-for="n in neutralShades"
          :key="n"
          class="swatch"
          :style="{ background: `var(--color-neutral-${n})` }"
        >
          <span class="swatch-label">
            <code>--color-neutral-{{ n }}</code>
            <em>{{ computedSwatches[`--color-neutral-${n}`] || "" }}</em>
          </span>
        </div>
      </div>
    </section>

    <section id="palette-brand">
      <h2>Palette brand</h2>
      <div class="row">
        <div
          v-for="b in brandShades"
          :key="b"
          class="swatch"
          :style="{ background: `var(--color-brand-${b})` }"
        >
          <span class="swatch-label">
            <code>--color-brand-{{ b }}</code>
            <em>{{ computedSwatches[`--color-brand-${b}`] || "" }}</em>
          </span>
        </div>
      </div>
    </section>

    <section id="semantiques">
      <h2>Sémantiques</h2>
      <div v-for="fam in semanticFamilies" :key="fam" class="row">
        <div
          v-for="t in semanticTones"
          :key="t"
          class="swatch"
          :style="{ background: `var(--color-${fam}-${t})` }"
        >
          <span class="swatch-label">
            <code>--color-{{ fam }}-{{ t }}</code>
            <em>{{ computedSwatches[`--color-${fam}-${t}`] || "" }}</em>
          </span>
        </div>
      </div>
    </section>

    <section id="roles">
      <h2>Surface / texte / bordure / focus-ring</h2>
      <div class="role-grid">
        <div class="role-card role-surface">
          <strong>--color-surface</strong>
          <span>{{ computedSwatches["--color-surface"] || "" }}</span>
          <p>Texte d'exemple sur surface.</p>
        </div>
        <div class="role-card role-bg">
          <strong>--color-bg</strong>
          <span>{{ computedSwatches["--color-bg"] || "" }}</span>
          <p>Texte sur fond page.</p>
        </div>
        <div class="role-card role-text">
          <strong>--color-text</strong>
          <span>{{ computedSwatches["--color-text"] || "" }}</span>
          <p>Couleur texte principal.</p>
        </div>
        <div class="role-card role-text-muted">
          <strong>--color-text-muted</strong>
          <span>{{ computedSwatches["--color-text-muted"] || "" }}</span>
          <p>Couleur texte secondaire.</p>
        </div>
        <div class="role-card role-border">
          <strong>--color-border</strong>
          <span>{{ computedSwatches["--color-border"] || "" }}</span>
          <p>Bordure défaut.</p>
        </div>
        <div class="role-card role-focus">
          <strong>--color-focus-ring</strong>
          <span>{{ computedSwatches["--color-focus-ring"] || "" }}</span>
          <p>Couleur d'anneau de focus.</p>
        </div>
      </div>
    </section>

    <section id="typo">
      <h2>Typographie</h2>
      <div v-for="size in fontSizes" :key="size" class="typo-row">
        <code>--font-size-{{ size }}</code>
        <span :class="`typo-sample typo-${size}`">
          Le développement durable au cœur des PME ouest-africaines
        </span>
      </div>
      <h3 class="typo-heading">Titre — line-height-heading</h3>
      <p class="typo-body">
        Corps — line-height-body. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
        eiusmod tempor incididunt ut labore et dolore magna aliqua.
      </p>
      <table class="kpi-table">
        <thead>
          <tr><th>Indicateur</th><th class="num">Valeur</th><th class="num">Variation</th></tr>
        </thead>
        <tbody>
          <tr><td>CA</td><td class="num">125 430,00</td><td class="num">+12,4 %</td></tr>
          <tr><td>EBE</td><td class="num">9 870,50</td><td class="num">+ 3,1 %</td></tr>
          <tr><td>tCO₂e</td><td class="num">42 015,75</td><td class="num">- 1,8 %</td></tr>
        </tbody>
      </table>
    </section>

    <section id="spacing">
      <h2>Spacing (grille 4 px)</h2>
      <div v-for="s in spacings" :key="s" class="spacing-row">
        <code>--space-{{ s }}</code>
        <span :class="`spacing-bar spacing-bar-${s}`"></span>
      </div>
    </section>

    <section id="radius">
      <h2>Radius</h2>
      <div class="radius-grid">
        <div
          v-for="r in radii"
          :key="r"
          class="radius-square"
          :class="`radius-${r}`"
        >
          <code>--radius-{{ r }}</code>
        </div>
      </div>
    </section>

    <section id="shadows">
      <h2>Shadows</h2>
      <div class="shadow-grid">
        <div
          v-for="sh in shadows"
          :key="sh"
          class="shadow-card"
          :class="`shadow-${sh}`"
        >
          <code>--shadow-{{ sh }}</code>
        </div>
      </div>
    </section>

    <section id="focus">
      <h2>Focus</h2>
      <p class="muted">
        Naviguez avec <kbd>Tab</kbd> pour vérifier l'anneau de focus visible (FR-019).
      </p>
      <div class="focus-row">
        <button class="btn-primary">Bouton</button>
        <a href="#focus" class="link">Lien</a>
        <input type="text" placeholder="Champ texte" />
        <select>
          <option>Option 1</option>
          <option>Option 2</option>
        </select>
        <textarea placeholder="Zone de texte" rows="2"></textarea>
      </div>
    </section>

    <section id="motion">
      <h2>Motion</h2>
      <p class="muted">État système : <strong>{{ motionStateLabel }}</strong></p>
      <div class="motion-row">
        <button :key="`f${animateKey}`" class="btn-primary motion-fast" @click="pulse">
          fast (120 ms)
        </button>
        <button :key="`b${animateKey}`" class="btn-primary motion-base" @click="pulse">
          base (200 ms)
        </button>
        <button :key="`s${animateKey}`" class="btn-primary motion-slow" @click="pulse">
          slow (320 ms)
        </button>
      </div>
    </section>

    <section id="disabled">
      <h2>États désactivés</h2>
      <div class="focus-row">
        <button class="btn-primary" disabled aria-disabled="true">Bouton désactivé</button>
        <input type="text" placeholder="Input désactivé" disabled />
        <a class="link link-disabled" aria-disabled="true" tabindex="-1">Lien désactivé</a>
      </div>
    </section>

    <section id="icons">
      <h2>Iconographie</h2>
      <p class="muted">
        Un seul jeu : Heroicons <code>24/outline</code>. La variante <code>solid</code> est
        réservée aux états sélectionnés (FR-016).
      </p>
      <div class="icon-row">
        <span class="icon-cell"><HomeIcon class="icon" /><code>HomeIcon</code></span>
        <span class="icon-cell"><ChartBarIcon class="icon" /><code>ChartBarIcon</code></span>
        <span class="icon-cell"><CheckCircleIcon class="icon" /><code>CheckCircleIcon</code></span>
        <span class="icon-cell"><BellIcon class="icon" /><code>BellIcon</code></span>
        <span class="icon-cell"><DocumentTextIcon class="icon" /><code>DocumentTextIcon</code></span>
        <span class="icon-cell"><ArrowRightIcon class="icon" /><code>ArrowRightIcon</code></span>
      </div>
    </section>

    <section id="logo">
      <h2>Logo</h2>
      <div class="logo-grid">
        <div class="logo-card logo-light">
          <img src="/brand/logo-horizontal-light.svg" alt="ESG Mefali — logo clair" height="48" />
          <code>logo-horizontal-light.svg</code>
        </div>
        <div class="logo-card logo-dark">
          <img src="/brand/logo-horizontal-dark.svg" alt="ESG Mefali — logo sombre" height="48" />
          <code>logo-horizontal-dark.svg</code>
        </div>
      </div>
      <h3 class="symbol-heading">Symbole — tailles</h3>
      <div class="symbol-row">
        <img src="/brand/symbol.svg" alt="Symbole 16 px" width="16" height="16" />
        <img src="/brand/symbol.svg" alt="Symbole 32 px" width="32" height="32" />
        <img src="/brand/symbol.svg" alt="Symbole 48 px" width="48" height="48" />
        <img src="/brand/symbol.svg" alt="Symbole 64 px" width="64" height="64" />
      </div>
    </section>

    <section id="empty-states">
      <h2>Empty states</h2>
      <p class="muted">
        Trois illustrations spot maximum (FR-017). Chacune accompagne un titre, une aide et
        un CTA.
      </p>
      <div class="empty-grid">
        <article class="empty-card">
          <img src="/illustrations/empty-list.svg" alt="" width="160" height="160" />
          <h3>Aucune candidature pour l'instant</h3>
          <p class="muted">Démarrez votre première candidature ESG en quelques minutes.</p>
          <button class="btn-primary" type="button">
            Démarrer une candidature
            <ArrowRightIcon class="icon-inline" />
          </button>
        </article>
        <article class="empty-card">
          <img src="/illustrations/no-results.svg" alt="" width="160" height="160" />
          <h3>Aucun résultat trouvé</h3>
          <p class="muted">Affinez vos filtres ou élargissez votre recherche.</p>
          <button class="btn-primary" type="button">Réinitialiser les filtres</button>
        </article>
        <article class="empty-card">
          <img src="/illustrations/welcome.svg" alt="" width="160" height="160" />
          <h3>Bienvenue sur ESG Mefali</h3>
          <p class="muted">Configurons ensemble votre profil entreprise.</p>
          <button class="btn-primary" type="button">Compléter mon profil</button>
        </article>
      </div>
    </section>

    <section id="dark">
      <h2>Mode sombre (aperçu DEV)</h2>
      <p class="muted">
        Démo locale uniquement. La bascule est interdite en production (FR-022). Le toggle pose
        <code>data-theme="dark"</code> sur <code>&lt;html&gt;</code>.
      </p>
      <button class="btn-primary" type="button" @click="toggleDark">
        {{ darkPreview ? "Revenir au clair" : "Aperçu sombre" }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.ds-root {
  font-family: var(--font-sans);
  color: var(--color-text);
  background: var(--color-bg);
  min-height: 100vh;
  padding: var(--space-8);
  max-width: 1200px;
  margin: 0 auto;
}
.ds-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-heading);
  margin: 0 0 var(--space-2);
}
.muted {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
.anchors {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-4) 0 var(--space-8);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}
.anchors a {
  font-size: var(--font-size-sm);
  color: var(--color-brand-600);
  text-decoration: none;
}
.anchors a:hover { text-decoration: underline; }

section {
  margin-bottom: var(--space-12);
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-sm);
}
section h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-heading);
  margin: 0 0 var(--space-4);
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.swatch {
  flex: 1 0 96px;
  min-height: 72px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: flex-end;
  padding: var(--space-2);
}
.swatch-label {
  background: var(--color-surface);
  color: var(--color-text);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.swatch-label code { font-family: var(--font-mono); }
.swatch-label em { color: var(--color-text-muted); font-style: normal; }

.role-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3);
}
.role-card {
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}
.role-card strong { font-family: var(--font-mono); }
.role-card.role-bg { background: var(--color-bg); }
.role-card.role-text-muted { color: var(--color-text-muted); }
.role-card.role-border { border-color: var(--color-text); }
.role-card.role-focus { outline: 2px solid var(--color-focus-ring); outline-offset: -4px; }

.typo-row {
  display: grid;
  grid-template-columns: 200px 1fr;
  align-items: baseline;
  gap: var(--space-4);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
}
.typo-row code {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.typo-sample { line-height: var(--line-height-body); }
.typo-xs { font-size: var(--font-size-xs); }
.typo-sm { font-size: var(--font-size-sm); }
.typo-base { font-size: var(--font-size-base); }
.typo-lg { font-size: var(--font-size-lg); }
.typo-xl { font-size: var(--font-size-xl); }
.typo-2xl { font-size: var(--font-size-2xl); }
.typo-3xl { font-size: var(--font-size-3xl); }
.typo-4xl { font-size: var(--font-size-4xl); }
.typo-5xl { font-size: var(--font-size-5xl); }
.typo-heading {
  font-size: var(--font-size-2xl);
  line-height: var(--line-height-heading);
  margin-top: var(--space-4);
}
.typo-body { line-height: var(--line-height-body); }

.kpi-table {
  margin-top: var(--space-4);
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.kpi-table th, .kpi-table td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}
.kpi-table .num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.spacing-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) 0;
}
.spacing-row code { font-family: var(--font-mono); font-size: var(--font-size-xs); }
.spacing-bar {
  display: inline-block;
  height: 16px;
  background: var(--color-brand-500);
  border-radius: var(--radius-sm);
}
.spacing-bar-1 { width: var(--space-1); }
.spacing-bar-2 { width: var(--space-2); }
.spacing-bar-3 { width: var(--space-3); }
.spacing-bar-4 { width: var(--space-4); }
.spacing-bar-6 { width: var(--space-6); }
.spacing-bar-8 { width: var(--space-8); }
.spacing-bar-12 { width: var(--space-12); }
.spacing-bar-16 { width: var(--space-16); }
.spacing-bar-24 { width: var(--space-24); }

.radius-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}
.radius-square {
  width: 96px;
  height: 96px;
  background: var(--color-brand-100);
  border: 1px solid var(--color-brand-500);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}
.radius-sm { border-radius: var(--radius-sm); }
.radius-md { border-radius: var(--radius-md); }
.radius-lg { border-radius: var(--radius-lg); }
.radius-xl { border-radius: var(--radius-xl); }
.radius-2xl { border-radius: var(--radius-2xl); }
.radius-full { border-radius: var(--radius-full); }

.shadow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-6);
}
.shadow-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}
.shadow-xs { box-shadow: var(--shadow-xs); }
.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: var(--shadow-lg); }
.shadow-xl { box-shadow: var(--shadow-xl); }

.focus-row, .motion-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}

.btn-primary {
  background: var(--color-brand-500);
  color: #ffffff;
  border: none;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font: inherit;
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition:
    background var(--duration-base) var(--ease-out),
    transform var(--duration-base) var(--ease-out);
}
.btn-primary:hover:not(:disabled) {
  background: var(--color-brand-600);
}
.btn-primary:disabled {
  background: var(--color-neutral-200);
  color: var(--color-neutral-500);
  cursor: not-allowed;
}

.link { color: var(--color-brand-700); text-decoration: underline; }
.link-disabled {
  color: var(--color-neutral-400);
  pointer-events: none;
  text-decoration: none;
}

input[type="text"], select, textarea {
  font: inherit;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
}
input[type="text"]:disabled {
  background: var(--color-neutral-100);
  color: var(--color-neutral-500);
  cursor: not-allowed;
}

.motion-fast { transition-duration: var(--duration-fast); }
.motion-base { transition-duration: var(--duration-base); }
.motion-slow { transition-duration: var(--duration-slow); }
.motion-row button:active { transform: scale(0.95); }

kbd {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  padding: 2px 6px;
  background: var(--color-neutral-100);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.icon-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--space-3);
}
.icon-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}
.icon {
  width: 24px;
  height: 24px;
  color: var(--color-text);
}
.icon-cell code {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.icon-inline {
  width: 16px;
  height: 16px;
  margin-left: var(--space-1);
  vertical-align: middle;
}

.logo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}
.logo-card {
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  border: 1px solid var(--color-border);
}
.logo-card code {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}
.logo-light {
  background: var(--color-surface);
  color: var(--color-text);
}
.logo-dark {
  background: var(--color-neutral-900);
  color: var(--color-neutral-50);
}
.symbol-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  margin: var(--space-4) 0 var(--space-2);
}
.symbol-row {
  display: flex;
  gap: var(--space-4);
  align-items: flex-end;
}

.empty-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}
.empty-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}
.empty-card h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  margin: var(--space-2) 0 0;
}
.empty-card img {
  align-self: center;
}
</style>
