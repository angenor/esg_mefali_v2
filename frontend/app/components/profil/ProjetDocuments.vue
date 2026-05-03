<script setup lang="ts">
// F43 T058 — ProjetDocuments : upload + miniatures + suppression.
//
// Validation cliente (R9) :
//   - MIME ∈ { application/pdf, image/jpeg, image/png,
//              application/vnd.openxmlformats-officedocument.wordprocessingml.document,
//              application/vnd.openxmlformats-officedocument.spreadsheetml.sheet }
//   - Taille ≤ 25 Mo.
import { computed, ref } from "vue"
import { useT } from "~/composables/useT"
import { useProjetsStore, type DocumentProjetRead } from "~/stores/projets"
import { useToast } from "~/composables/useToast"

interface Props {
  projetId: string
}

const props = defineProps<Props>()
const { t } = useT()
const store = useProjetsStore()
const toast = useToast()

const ALLOWED_MIME = new Set<string>([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
])
const MAX_BYTES = 25 * 1024 * 1024

const documents = computed<DocumentProjetRead[]>(
  () => store.documentsById[props.projetId] ?? [],
)
const uploading = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)

function pickFile(): void {
  inputRef.value?.click()
}

async function onChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!ALLOWED_MIME.has(file.type)) {
    toast.push({
      severity: "error",
      message: t("profil.projets.documents.error_mime"),
      duration: 4000,
    })
    input.value = ""
    return
  }
  if (file.size > MAX_BYTES) {
    toast.push({
      severity: "error",
      message: t("profil.projets.documents.error_size"),
      duration: 4000,
    })
    input.value = ""
    return
  }
  await upload(file)
  input.value = ""
}

async function upload(file: File): Promise<void> {
  uploading.value = true
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string
    const formData = new FormData()
    formData.append("file", file)
    formData.append("type_doc", "autre")
    const created = await $fetch<DocumentProjetRead>(
      `${apiBase}/me/projets/${props.projetId}/documents`,
      { method: "POST", credentials: "include", body: formData },
    )
    const existing = store.documentsById[props.projetId] ?? []
    store.documentsById = {
      ...store.documentsById,
      [props.projetId]: [...existing, created],
    }
  } catch {
    toast.push({ severity: "error", message: "Échec du téléversement", duration: 3000 })
  } finally {
    uploading.value = false
  }
}

async function removeDoc(doc: DocumentProjetRead): Promise<void> {
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string
    await $fetch(`${apiBase}/me/projets/${props.projetId}/documents/${doc.id}`, {
      method: "DELETE",
      credentials: "include",
    })
    const existing = store.documentsById[props.projetId] ?? []
    store.documentsById = {
      ...store.documentsById,
      [props.projetId]: existing.filter((d) => d.id !== doc.id),
    }
  } catch {
    toast.push({ severity: "error", message: "Échec de la suppression", duration: 3000 })
  }
}

function isImage(mime: string): boolean {
  return mime === "image/jpeg" || mime === "image/png"
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}
</script>

<template>
  <div class="projet-docs">
    <ul v-if="documents.length > 0" class="projet-docs__list">
      <li v-for="doc in documents" :key="doc.id" class="projet-docs__item">
        <div class="projet-docs__icon" :data-mime="doc.mime" aria-hidden="true">
          <span v-if="isImage(doc.mime)">🖼️</span>
          <span v-else-if="doc.mime.includes('pdf')">📄</span>
          <span v-else-if="doc.mime.includes('word')">📝</span>
          <span v-else-if="doc.mime.includes('sheet')">📊</span>
          <span v-else>📎</span>
        </div>
        <div class="projet-docs__meta">
          <p class="projet-docs__name">{{ doc.nom }}</p>
          <p class="projet-docs__size">{{ formatSize(doc.taille_octets) }}</p>
        </div>
        <button
          type="button"
          class="projet-docs__remove"
          :aria-label="`Supprimer ${doc.nom}`"
          @click="removeDoc(doc)"
        >
          ×
        </button>
      </li>
    </ul>
    <p v-else class="projet-docs__empty">{{ t("profil.projets.documents.empty") }}</p>

    <input
      ref="inputRef"
      type="file"
      accept="application/pdf,image/jpeg,image/png,.docx,.xlsx"
      class="projet-docs__input"
      @change="onChange"
    />
    <button type="button" class="projet-docs__cta" :disabled="uploading" @click="pickFile">
      {{ uploading ? "…" : t("profil.projets.documents.upload") }}
    </button>
  </div>
</template>

<style scoped>
.projet-docs {
  display: grid;
  gap: 0.75rem;
}
.projet-docs__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.5rem;
}
.projet-docs__item {
  display: grid;
  grid-template-columns: 2.5rem 1fr auto;
  gap: 0.625rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border-radius: 0.5rem;
}
.projet-docs__icon {
  font-size: 1.5rem;
  text-align: center;
}
.projet-docs__name {
  font-weight: 500;
  color: #0f172a;
  font-size: 0.875rem;
}
.projet-docs__size {
  color: #64748b;
  font-size: 0.75rem;
}
.projet-docs__remove {
  background: none;
  border: 0;
  color: #b91c1c;
  font-size: 1.25rem;
  cursor: pointer;
  line-height: 1;
}
.projet-docs__empty {
  color: #64748b;
  font-size: 0.875rem;
}
.projet-docs__input {
  display: none;
}
.projet-docs__cta {
  background: #15803d;
  color: #fff;
  border: 0;
  border-radius: 0.5rem;
  padding: 0.5rem 0.875rem;
  font-weight: 500;
  cursor: pointer;
  width: fit-content;
}
.projet-docs__cta:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
</style>
