<script setup lang="ts">
/**
 * AskFileUpload — upload binaire vers l'endpoint approprié, puis POST message PME.
 *
 * Routing :
 *  - attach_to=entreprise → POST `${apiBase}/v1/entreprise/documents`
 *  - attach_to=projet     → POST `${apiBase}/v1/projets/{projet_id}/documents`
 *
 * Le binaire passe par XHR pour la progression (R10) ; en cas d'erreur taille/MIME,
 * message inline FR + bouton « Annuler » (FR-019) qui émet dismiss-for-freetext.
 */
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_file_upload' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const DEFAULT_MIME = ['application/pdf', 'image/png', 'image/jpeg']
const DEFAULT_MAX = 10 * 1024 * 1024

const question = computed(() => sanitizeText(props.instruction.payload.question))
const acceptedMime = computed(() => props.instruction.payload.accepted_mime ?? DEFAULT_MIME)
const maxSize = computed(() => props.instruction.payload.max_size_bytes ?? DEFAULT_MAX)
const acceptAttr = computed(() => acceptedMime.value.join(','))

const file = ref<File | null>(null)
const progress = ref<number>(0)
const localError = ref<string | null>(null)
const uploading = ref<boolean>(false)
const submit = useBottomSheetSubmit()

const submitDisabled = computed(() => file.value === null || uploading.value)

function uploadEndpoint(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.()
  const base = String(cfg?.public?.apiBase ?? 'http://localhost:8010').replace(/\/$/, '')
  if (props.instruction.payload.attach_to === 'projet') {
    return `${base}/v1/projets/${props.instruction.payload.projet_id}/documents`
  }
  return `${base}/v1/entreprise/documents`
}

function onFileChange(e: Event): void {
  localError.value = null
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] ?? null
  if (!f) {
    file.value = null
    return
  }
  if (!acceptedMime.value.includes(f.type)) {
    localError.value = `Format ${f.type || 'inconnu'} non accepté.`
    file.value = null
    return
  }
  if (f.size > maxSize.value) {
    localError.value = `Fichier trop volumineux (max ${(maxSize.value / 1024 / 1024).toFixed(0)} Mo).`
    file.value = null
    return
  }
  file.value = f
}

function uploadXhr(f: File): Promise<{ doc_id: string; filename: string; mime: string; size: number }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', uploadEndpoint())
    xhr.withCredentials = true
    xhr.responseType = 'json'
    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable) progress.value = Math.round((evt.loaded / evt.total) * 100)
    }
    xhr.onerror = () => reject(new Error('network'))
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const body = xhr.response as { doc_id: string; filename?: string; mime?: string; size?: number }
        resolve({ doc_id: body.doc_id, filename: body.filename ?? f.name, mime: body.mime ?? f.type, size: body.size ?? f.size })
      } else {
        reject(new Error(`http_${xhr.status}`))
      }
    }
    const form = new FormData()
    form.append('file', f, f.name)
    xhr.send(form)
  })
}

async function onSubmit(): Promise<void> {
  if (!file.value || uploading.value) return
  uploading.value = true
  progress.value = 0
  try {
    const value = await uploadXhr(file.value)
    const label = `Document chargé : ${value.filename}`
    const res = await submit.submit({
      threadId: props.instruction.context.thread_id,
      inResponseToMessageId: props.instruction.context.message_id,
      tool: 'ask_file_upload',
      value,
      label,
    })
    if (res.ok || res.errorCode === '409') {
      emit('submit', { tool: 'ask_file_upload', value, label })
      return
    }
    emit('error', {
      code: res.errorCode ?? 'unknown',
      message: res.errorMessage ?? 'Erreur',
      retriable: res.errorCode === '5xx' || res.errorCode === 'network',
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'erreur inconnue'
    localError.value = `Upload échoué (${msg}).`
    emit('error', { code: msg, message: localError.value, retriable: true })
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <BottomSheetShell
    :title="question"
    :submit-disabled="submitDisabled"
    :in-flight="submit.inFlight.value || uploading"
    :error-message="localError"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <input
      type="file"
      :accept="acceptAttr"
      data-testid="ask-file-upload-input"
      @change="onFileChange"
    />
    <p v-if="file" class="ask-file-upload__file">
      {{ file.name }} ({{ (file.size / 1024 / 1024).toFixed(2) }} Mo)
    </p>
    <progress v-if="uploading" :value="progress" max="100" class="ask-file-upload__progress" />
  </BottomSheetShell>
</template>

<style scoped>
.ask-file-upload__file { color: var(--color-text-muted, #64748b); margin: var(--space-2, 8px) 0; }
.ask-file-upload__progress { width: 100%; }
</style>
