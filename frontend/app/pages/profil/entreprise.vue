<script setup lang="ts">
// F43 T023 — Page /profil/entreprise (5 SectionCard + autosave + ConflictDialog).
//
// SSR via useAsyncData → store entreprise.loadAll().
// L'autosave est délégué à useEntrepriseProfile (debounce 800 ms + 409/422/5xx).
// ConflictDialog monté en téléport via le store.conflict (US4).
// HistoryDrawer : bouton « Historique » par section ; le drawer est livré en US6.
import { computed } from "vue"
import { storeToRefs } from "pinia"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useEntrepriseProfile } from "~/composables/useEntrepriseProfile"
import { useT } from "~/composables/useT"
import EntrepriseHeader from "~/components/profil/EntrepriseHeader.vue"
import SectionCard, {
  type FieldDescriptor,
} from "~/components/profil/SectionCard.vue"
import SectionEditor from "~/components/profil/SectionEditor.vue"
import ConflictDialog from "~/components/profil/ConflictDialog.vue"
import MoneyField from "~/components/profil/MoneyField.vue"
import CountryMultiSelect from "~/components/profil/CountryMultiSelect.vue"
import HistoryDrawer from "~/components/profil/HistoryDrawer.vue"
import type { MoneyOut } from "~/stores/entreprise"
import { useDecimal } from "~/composables/useDecimal"
import { ref } from "vue"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Profil entreprise" }],
  title: "Profil entreprise",
})

const { t } = useT()
const store = useEntrepriseStore()
const profile = useEntrepriseProfile()
const { format: formatAmount } = useDecimal()

function formatMoney(m: MoneyOut): string {
  if (!m?.amount) return "—"
  try {
    return formatAmount(m.amount, m.currency)
  } catch {
    return `${m.amount} ${m.currency}`
  }
}

const { data, completion, conflict, errors, saving } = storeToRefs(store)

await useAsyncData("entreprise-profile", () => store.loadAll())

const dataView = computed<Record<string, unknown>>(() => {
  const d = data.value ?? ({} as Record<string, unknown>)
  return d as Record<string, unknown>
})

const percentage = computed(() => completion.value?.percentage ?? 0)
const missing = computed(() => completion.value?.missing ?? [])

const SECTION_IDENTITE: FieldDescriptor[] = [
  {
    key: "raison_sociale",
    label: t("profil.entreprise.field.raison_sociale"),
    kind: "input",
    required: true,
  },
  {
    key: "forme_juridique",
    label: t("profil.entreprise.field.forme_juridique"),
    kind: "input",
  },
  {
    key: "secteur_principal",
    label: t("profil.entreprise.field.secteur_principal"),
    kind: "input",
  },
  {
    key: "annee_creation",
    label: t("profil.entreprise.field.annee_creation"),
    kind: "year",
  },
]
const SECTION_TAILLE: FieldDescriptor[] = [
  { key: "taille_ca", label: t("profil.entreprise.field.taille_ca"), kind: "money" },
  { key: "taille_effectif", label: t("profil.entreprise.field.taille_effectif"), kind: "number" },
]
const SECTION_LOCALISATION: FieldDescriptor[] = [
  {
    key: "localisation_siege_pays_iso2",
    label: t("profil.entreprise.field.localisation_siege_pays_iso2"),
    kind: "country",
  },
  {
    key: "zones_operation_pays_iso2",
    label: t("profil.entreprise.field.zones_operation_pays_iso2"),
    kind: "country-multi",
  },
]
const SECTION_GOUVERNANCE: FieldDescriptor[] = [
  { key: "gouvernance_type", label: t("profil.entreprise.field.gouvernance_type"), kind: "input" },
]
const SECTION_PRATIQUES: FieldDescriptor[] = [
  {
    key: "pratiques_environnement",
    label: t("profil.entreprise.field.pratiques_environnement"),
    kind: "textarea",
  },
]

function onUpdate({ field, value }: { field: string; value: unknown }): void {
  profile.patchField(field, value)
}

function onConflict(choice: "mine" | "theirs" | "cancel"): void {
  void profile.resolveConflict(choice)
}

const historyOpen = ref(false)
function openHistory(): void {
  historyOpen.value = true
}
function closeHistory(): void {
  historyOpen.value = false
}

function getFieldLabel(field: string): string {
  const allFields = [
    ...SECTION_IDENTITE,
    ...SECTION_TAILLE,
    ...SECTION_LOCALISATION,
    ...SECTION_GOUVERNANCE,
    ...SECTION_PRATIQUES,
  ]
  return allFields.find((f) => f.key === field)?.label ?? field
}
</script>

<template>
  <section class="profil-entreprise" aria-labelledby="profil-entreprise-title">
    <EntrepriseHeader
      :percentage="percentage"
      :missing="missing"
      @open-history="openHistory"
    />

    <div class="profil-entreprise__grid">
      <SectionCard
        :title="t('profil.entreprise.section.identite')"
        :fields="SECTION_IDENTITE"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
        @open-history="openHistory"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_IDENTITE"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          />
          <dl v-else class="profil-entreprise__readonly">
            <div v-for="f in SECTION_IDENTITE" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.entreprise.section.taille')"
        :fields="SECTION_TAILLE"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
        @open-history="openHistory"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_TAILLE"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          >
            <template #taille_ca="{ value }">
              <MoneyField
                :model-value="(value as MoneyOut | null) ?? null"
                :label="t('profil.entreprise.field.taille_ca')"
                :error="errors.taille_ca ?? undefined"
                @update:model-value="(v) => slotUpdate('taille_ca', v)"
              />
            </template>
          </SectionEditor>
          <dl v-else class="profil-entreprise__readonly">
            <div v-for="f in SECTION_TAILLE" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd v-if="f.key === 'taille_ca'">
                <span v-if="dataView.taille_ca">
                  {{ formatMoney(dataView.taille_ca as MoneyOut) }}
                </span>
                <span v-else>—</span>
              </dd>
              <dd v-else>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.entreprise.section.localisation')"
        :fields="SECTION_LOCALISATION"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
        @open-history="openHistory"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_LOCALISATION"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          >
            <template #localisation_siege_pays_iso2="{ value }">
              <CountryMultiSelect
                :model-value="value ? [value as string] : []"
                :mono="true"
                :label="t('profil.entreprise.field.localisation_siege_pays_iso2')"
                :error="errors.localisation_siege_pays_iso2 ?? undefined"
                @update:model-value="(v) => slotUpdate('localisation_siege_pays_iso2', v[0] ?? null)"
              />
            </template>
            <template #zones_operation_pays_iso2="{ value }">
              <CountryMultiSelect
                :model-value="(value as string[] | null) ?? []"
                :label="t('profil.entreprise.field.zones_operation_pays_iso2')"
                :error="errors.zones_operation_pays_iso2 ?? undefined"
                @update:model-value="(v) => slotUpdate('zones_operation_pays_iso2', v)"
              />
            </template>
          </SectionEditor>
          <dl v-else class="profil-entreprise__readonly">
            <div v-for="f in SECTION_LOCALISATION" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>
                {{
                  Array.isArray(dataView[f.key])
                    ? (dataView[f.key] as string[]).join(", ") || "—"
                    : (dataView[f.key] ?? "—")
                }}
              </dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.entreprise.section.gouvernance')"
        :fields="SECTION_GOUVERNANCE"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
        @open-history="openHistory"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_GOUVERNANCE"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          />
          <dl v-else class="profil-entreprise__readonly">
            <div v-for="f in SECTION_GOUVERNANCE" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.entreprise.section.pratiques')"
        :fields="SECTION_PRATIQUES"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
        @open-history="openHistory"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_PRATIQUES"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          />
          <dl v-else class="profil-entreprise__readonly">
            <div v-for="f in SECTION_PRATIQUES" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>
    </div>

    <HistoryDrawer
      :open="historyOpen"
      entity="entreprise"
      @close="closeHistory"
    />

    <ConflictDialog
      v-if="conflict"
      :open="!!conflict"
      :field="conflict.field"
      :field-label="getFieldLabel(conflict.field)"
      :your-value="conflict.your"
      :current-value="conflict.current"
      @resolve="onConflict"
    />
  </section>
</template>

<style scoped>
.profil-entreprise {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}
.profil-entreprise__grid {
  display: grid;
  gap: 1rem;
}
.profil-entreprise__readonly {
  display: grid;
  gap: 0.5rem;
}
.profil-entreprise__readonly div {
  display: grid;
  grid-template-columns: 12rem 1fr;
  gap: 0.5rem;
}
.profil-entreprise__readonly dt {
  color: #475569;
  font-weight: 500;
  font-size: 0.875rem;
}
.profil-entreprise__readonly dd {
  color: #0f172a;
  font-size: 0.875rem;
}
@media (min-width: 1024px) {
  .profil-entreprise__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .profil-entreprise__readonly div {
    grid-template-columns: 1fr;
  }
}
</style>
