<!--
  F50 T026 — UploadZone (drag & drop + bouton fallback, queue 5, MIME/size).
  Cf. contracts/documents_ui_contracts.md §3.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDocumentsStore } from '~/stores/documents'

interface Props {
  context: 'entreprise' | 'projet'
  projetId?: string | null
  docType?: string
}

const props = withDefaults(defineProps<Props>(), {
  projetId: null,
  docType: 'autre',
})

const emit = defineEmits<{
  (e: 'duplicate-detected', payload: { jobId: string; existingId: string }): void
  (e: 'upload-success', docId: string): void
}>()

const ALLOWED_MIME = new Set([
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/heic',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
])
const MAX_FILE_BYTES = 20 * 1024 * 1024 // 20 Mo (cap UI strict, FR-002).

const store = useDocumentsStore()
const inputRef = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const errors = ref<{ filename: string; message: string }[]>([])

const acceptAttr = computed(() => Array.from(ALLOWED_MIME).join(','))

function validate(file: File): string | null {
  if (file.size > MAX_FILE_BYTES) {
    return `Fichier trop volumineux (> ${Math.round(MAX_FILE_BYTES / 1_000_000)} Mo).`
  }
  if (!ALLOWED_MIME.has(file.type)) {
    return `Type de fichier non autorisé : ${file.type || 'inconnu'}.`
  }
  return null
}

async function handleFiles(files: FileList | File[]): Promise<void> {
  errors.value = []
  for (const file of Array.from(files)) {
    const err = validate(file)
    if (err) {
      errors.value = [...errors.value, { filename: file.name, message: err }]
      continue
    }
    const job = await store.enqueueUpload(file, {
      type: props.docType,
      linkProjetId: props.projetId,
    })
    // Watch job pour signaler les doublons.
    void watchJobForDuplicate(job.id)
  }
}

async function watchJobForDuplicate(jobId: string): Promise<void> {
  // Polling court (max 10 s) côté composant pour détecter un état "duplicate".
  for (let i = 0; i < 100; i++) {
    await new Promise((r) => setTimeout(r, 100))
    const job = store.uploadQueue.find((j) => j.id === jobId)
    if (!job) return
    if (job.status === 'duplicate' && job.sha256) {
      emit('duplicate-detected', { jobId, existingId: job.sha256 })
      return
    }
    if (job.status === 'success' && job.documentId) {
      emit('upload-success', job.documentId)
      return
    }
    if (job.status === 'error' || job.status === 'cancelled') return
  }
}

function onDrop(ev: DragEvent): void {
  ev.preventDefault()
  dragOver.value = false
  if (ev.dataTransfer?.files) void handleFiles(ev.dataTransfer.files)
}

function onDragOver(ev: DragEvent): void {
  ev.preventDefault()
  dragOver.value = true
}

function onDragLeave(): void {
  dragOver.value = false
}

function onPick(): void {
  inputRef.value?.click()
}

function onPickKey(ev: KeyboardEvent): void {
  if (ev.key === 'Enter' || ev.key === ' ') {
    ev.preventDefault()
    onPick()
  }
}

function onChange(ev: Event): void {
  const target = ev.target as HTMLInputElement
  if (target.files) void handleFiles(target.files)
  target.value = ''
}
</script>

<template>
  <div class="space-y-3">
    <div
      role="button"
      tabindex="0"
      :aria-label="`Zone de dépôt — déposez un fichier ou pressez Entrée pour parcourir`"
      class="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors"
      :class="dragOver ? 'border-emerald-500 bg-emerald-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'"
      @click="onPick"
      @keydown="onPickKey"
      @drop="onDrop"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
    >
      <svg
        class="h-10 w-10 text-gray-500"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        aria-hidden="true"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 7.5m0 0L7.5 12M12 7.5v9" />
      </svg>
      <p class="text-sm font-medium text-gray-900">
        Déposez vos fichiers ici ou
        <span class="text-emerald-700 underline">parcourir</span>
      </p>
      <p class="text-xs text-gray-500">PDF, JPG, PNG, DOCX, XLSX — 20 Mo max</p>
      <input
        ref="inputRef"
        type="file"
        multiple
        :accept="acceptAttr"
        class="hidden"
        @change="onChange"
      >
    </div>

    <ul
      v-if="store.activeUploads.length"
      class="space-y-2"
      role="status"
      aria-live="polite"
    >
      <li
        v-for="job in store.activeUploads"
        :key="job.id"
        class="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-3 py-2"
      >
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-gray-900">{{ job.filename }}</p>
          <p class="text-xs text-gray-500">
            {{ Math.round(job.size / 1024) }} Ko · {{ job.status }}
          </p>
        </div>
        <progress
          v-if="job.status === 'uploading'"
          :value="job.percent"
          max="100"
          class="h-1 w-32"
          :aria-valuenow="job.percent"
          aria-valuemin="0"
          aria-valuemax="100"
        />
      </li>
    </ul>

    <ul
      v-if="errors.length"
      class="space-y-1"
      role="alert"
      aria-live="assertive"
    >
      <li
        v-for="(err, i) in errors"
        :key="i"
        class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      >
        <strong>{{ err.filename }}</strong> : {{ err.message }}
      </li>
    </ul>
  </div>
</template>
