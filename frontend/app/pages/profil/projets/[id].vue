<script setup lang="ts">
// F43 T048 — page détail projet : 5 sections (Identité, Description, Localisation, Budget, Documents).
import { computed, ref } from "vue"
import { useT } from "~/composables/useT"
import { useProjet } from "~/composables/useProjet"
import { useDecimal } from "~/composables/useDecimal"
import SectionCard, {
  type FieldDescriptor,
} from "~/components/profil/SectionCard.vue"
import SectionEditor from "~/components/profil/SectionEditor.vue"
import ConflictDialog from "~/components/profil/ConflictDialog.vue"
import MoneyField from "~/components/profil/MoneyField.vue"
import CountryMultiSelect from "~/components/profil/CountryMultiSelect.vue"
import ProjetDocuments from "~/components/profil/ProjetDocuments.vue"
import ProjetDocumentsGrid from "~/components/documents/ProjetDocumentsGrid.vue"
import HistoryDrawer from "~/components/profil/HistoryDrawer.vue"
import type { MoneyOut } from "~/stores/entreprise"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  title: "Détail projet",
})

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const { t } = useT()
const projet = useProjet(id)
const { format: formatAmount } = useDecimal()

await useAsyncData(`projet-${id}`, () => projet.load())

const data = projet.data
const errors = projet.errors
const saving = projet.saving
const conflict = projet.conflict

const dataView = computed<Record<string, unknown>>(() => {
  return (data.value ?? {}) as Record<string, unknown>
})

const SECTION_IDENTITE: FieldDescriptor[] = [
  { key: "nom", label: "Nom", kind: "input", required: true },
  { key: "secteur", label: "Secteur", kind: "input" },
  { key: "type_impact", label: "Type d'impact", kind: "input" },
]
const SECTION_DESCRIPTION: FieldDescriptor[] = [
  { key: "description", label: "Description", kind: "textarea" },
]
const SECTION_LOCALISATION: FieldDescriptor[] = [
  { key: "localisation_pays_iso2", label: "Pays", kind: "country" },
  { key: "localisation_region", label: "Région", kind: "input" },
]
const SECTION_BUDGET: FieldDescriptor[] = [
  { key: "budget", label: "Budget", kind: "money" },
  { key: "horizon_mois", label: "Horizon (mois)", kind: "number" },
]

const allFields = computed(() => [
  ...SECTION_IDENTITE,
  ...SECTION_DESCRIPTION,
  ...SECTION_LOCALISATION,
  ...SECTION_BUDGET,
])

function fieldLabel(key: string): string {
  return allFields.value.find((f) => f.key === key)?.label ?? key
}

function onUpdate(payload: { field: string; value: unknown }): void {
  projet.patchField(payload.field, payload.value)
}

function onConflict(choice: "mine" | "theirs" | "cancel"): void {
  void projet.resolveConflict(choice)
}

const showDeleteConfirm = ref(false)
const historyOpen = ref(false)

async function confirmDelete(): Promise<void> {
  const ok = await projet.softDelete()
  if (ok) {
    showDeleteConfirm.value = false
    void router.push("/profil/projets")
  }
}

function formatMoney(m: MoneyOut | null | undefined): string {
  if (!m?.amount) return "—"
  try {
    return formatAmount(m.amount, m.currency)
  } catch {
    return `${m.amount} ${m.currency}`
  }
}
</script>

<template>
  <section v-if="data" class="projet-detail" aria-labelledby="projet-detail-title">
    <header class="projet-detail__header">
      <h1 id="projet-detail-title">{{ data.nom }}</h1>
      <div class="projet-detail__actions">
        <button
          type="button"
          class="projet-detail__history"
          @click="historyOpen = true"
        >
          {{ t("profil.entreprise.action.history") }}
        </button>
        <button
          type="button"
          class="projet-detail__delete"
          @click="showDeleteConfirm = true"
        >
          {{ t("profil.projets.delete.confirm_cta") }}
        </button>
      </div>
    </header>

    <div class="projet-detail__grid">
      <SectionCard
        title="Identité"
        :fields="SECTION_IDENTITE"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
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
          <dl v-else class="projet-detail__readonly">
            <div v-for="f in SECTION_IDENTITE" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.projets.detail.section.description')"
        :fields="SECTION_DESCRIPTION"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_DESCRIPTION"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          />
          <p v-else class="projet-detail__description">
            {{ dataView.description || "—" }}
          </p>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.projets.detail.section.localisation')"
        :fields="SECTION_LOCALISATION"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
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
            <template #localisation_pays_iso2="{ value }">
              <CountryMultiSelect
                :model-value="value ? [value as string] : []"
                :mono="true"
                @update:model-value="(v) => slotUpdate('localisation_pays_iso2', v[0] ?? null)"
              />
            </template>
          </SectionEditor>
          <dl v-else class="projet-detail__readonly">
            <div v-for="f in SECTION_LOCALISATION" :key="f.key">
              <dt>{{ f.label }}</dt>
              <dd>{{ dataView[f.key] ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.projets.detail.section.budget')"
        :fields="SECTION_BUDGET"
        :data="dataView"
        :saving="saving"
        :errors="errors"
        @update:field="onUpdate"
      >
        <template #default="{ editing, onUpdate: slotUpdate }">
          <SectionEditor
            v-if="editing"
            :fields="SECTION_BUDGET"
            :data="dataView"
            :errors="errors"
            :saving="saving"
            @update:field="(p) => slotUpdate(p.field, p.value)"
          >
            <template #budget="{ value }">
              <MoneyField
                :model-value="(value as MoneyOut | null) ?? null"
                @update:model-value="(v) => slotUpdate('budget', v)"
              />
            </template>
          </SectionEditor>
          <dl v-else class="projet-detail__readonly">
            <div>
              <dt>Budget</dt>
              <dd>{{ formatMoney(dataView.budget as MoneyOut | null) }}</dd>
            </div>
            <div>
              <dt>Horizon (mois)</dt>
              <dd>{{ dataView.horizon_mois ?? "—" }}</dd>
            </div>
          </dl>
        </template>
      </SectionCard>

      <SectionCard
        :title="t('profil.projets.detail.section.documents')"
        :fields="[]"
        :data="dataView"
      >
        <template #default>
          <ProjetDocuments :projet-id="id" />
          <ProjetDocumentsGrid :projet-id="id" class="mt-4" />
        </template>
      </SectionCard>
    </div>

    <HistoryDrawer
      :open="historyOpen"
      entity="projet"
      :entity-id="id"
      @close="historyOpen = false"
    />

    <ConflictDialog
      v-if="conflict"
      :open="!!conflict"
      :field="conflict.field"
      :field-label="fieldLabel(conflict.field)"
      :your-value="conflict.your"
      :current-value="conflict.current"
      @resolve="onConflict"
    />

    <Teleport v-if="showDeleteConfirm" to="body">
      <div class="projet-detail__modal" role="dialog" aria-modal="true">
        <div class="projet-detail__modal-overlay" @click="showDeleteConfirm = false" />
        <div class="projet-detail__modal-panel">
          <h2>{{ t("profil.projets.delete.confirm_title") }}</h2>
          <p>{{ t("profil.projets.delete.confirm_body") }}</p>
          <div class="projet-detail__modal-actions">
            <button type="button" @click="showDeleteConfirm = false">Annuler</button>
            <button type="button" class="projet-detail__danger" @click="confirmDelete">
              {{ t("profil.projets.delete.confirm_cta") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
  <p v-else aria-live="polite">Chargement…</p>
</template>

<style scoped>
.projet-detail {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}
.projet-detail__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}
.projet-detail__header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #0f172a;
}
.projet-detail__actions {
  display: flex;
  gap: 0.5rem;
}
.projet-detail__delete,
.projet-detail__history {
  background: transparent;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.45rem 0.875rem;
  cursor: pointer;
  font-weight: 500;
  color: #0f172a;
}
.projet-detail__delete {
  border-color: #fecaca;
  color: #b91c1c;
}
.projet-detail__grid {
  display: grid;
  gap: 1rem;
}
.projet-detail__readonly {
  display: grid;
  gap: 0.5rem;
}
.projet-detail__readonly div {
  display: grid;
  grid-template-columns: 12rem 1fr;
  gap: 0.5rem;
}
.projet-detail__readonly dt {
  color: #475569;
  font-weight: 500;
  font-size: 0.875rem;
}
.projet-detail__description {
  color: #0f172a;
  white-space: pre-wrap;
}
.projet-detail__modal {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 1rem;
}
.projet-detail__modal-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
}
.projet-detail__modal-panel {
  position: relative;
  background: #fff;
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
  max-width: 28rem;
  display: grid;
  gap: 0.75rem;
}
.projet-detail__modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
.projet-detail__modal-actions button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 0.5rem;
  padding: 0.5rem 0.875rem;
  cursor: pointer;
  font-weight: 500;
}
.projet-detail__danger {
  background: #b91c1c !important;
  color: #fff;
  border-color: #b91c1c !important;
}
@media (min-width: 1024px) {
  .projet-detail__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
