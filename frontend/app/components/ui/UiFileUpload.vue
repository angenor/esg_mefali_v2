<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import type { UiUploadFile } from '~/types/ui'

interface Props {
  modelValue?: UiUploadFile[]
  accept?: string[]
  maxSize?: number
  multiple?: boolean
  mode?: 'dropzone' | 'button'
  maxFiles?: number
  uploadFn?: (f: File, onProgress: (ratio: number) => void) => Promise<void>
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  accept: () => ['*/*'],
  maxSize: 10 * 1024 * 1024,
  multiple: true,
  mode: 'dropzone',
  maxFiles: undefined,
  uploadFn: undefined,
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: UiUploadFile[]): void
  (e: 'add', files: File[]): void
  (e: 'remove', id: string): void
  (e: 'progress', id: string, ratio: number): void
  (e: 'success', id: string): void
  (e: 'error', id: string, message: string): void
  (e: 'retry', id: string): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const previewUrls = new Map<string, string>()

const acceptAttr = computed(() => props.accept.join(','))

function isMimeAllowed(f: File): boolean {
  if (props.accept.includes('*/*')) return true
  return props.accept.some((m) => {
    if (m === f.type) return true
    if (m.endsWith('/*')) return f.type.startsWith(m.slice(0, -1))
    return false
  })
}

function makeId(): string {
  return `up-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function buildEntry(file: File, error?: string): UiUploadFile {
  return {
    id: makeId(),
    file,
    status: error ? 'error' : 'queued',
    progress: 0,
    error,
  }
}

async function processFiles(files: File[]): Promise<void> {
  if (props.disabled) return
  emit('add', files)
  const next: UiUploadFile[] = [...props.modelValue]

  for (const f of files) {
    let error: string | undefined
    if (!isMimeAllowed(f)) error = `Type ${f.type || 'inconnu'} non autorisé`
    else if (f.size > props.maxSize) error = `Fichier trop volumineux (max ${Math.round(props.maxSize / 1024 / 1024)} Mo)`
    else if (props.maxFiles !== undefined && next.length >= props.maxFiles)
      error = `Nombre maximum de fichiers atteint (${props.maxFiles})`

    const entry = buildEntry(f, error)
    next.push(entry)
    if (f.type.startsWith('image/') && typeof URL !== 'undefined' && URL.createObjectURL) {
      previewUrls.set(entry.id, URL.createObjectURL(f))
    }
  }
  emit('update:modelValue', next)

  if (props.uploadFn) {
    for (const entry of next.filter((e) => e.status === 'queued')) {
      runUpload(entry)
    }
  }
}

async function runUpload(entry: UiUploadFile): Promise<void> {
  if (!props.uploadFn) return
  const update = (patch: Partial<UiUploadFile>): void => {
    const next = props.modelValue.map((e) => (e.id === entry.id ? { ...e, ...patch } : e))
    emit('update:modelValue', next)
  }
  update({ status: 'uploading', progress: 0 })
  try {
    await props.uploadFn(entry.file, (ratio) => {
      update({ progress: ratio })
      emit('progress', entry.id, ratio)
    })
    update({ status: 'success', progress: 1 })
    emit('success', entry.id)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erreur réseau'
    update({ status: 'error', error: msg })
    emit('error', entry.id, msg)
  }
}

function onPickerChange(e: Event): void {
  const target = e.target as HTMLInputElement
  if (!target.files) return
  processFiles(Array.from(target.files))
  target.value = ''
}

function onDrop(e: DragEvent): void {
  e.preventDefault()
  dragOver.value = false
  if (!e.dataTransfer) return
  processFiles(Array.from(e.dataTransfer.files))
}

function openPicker(): void {
  inputRef.value?.click()
}

function onDropzoneKey(e: KeyboardEvent): void {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    openPicker()
  }
}

function remove(id: string): void {
  const url = previewUrls.get(id)
  if (url) {
    URL.revokeObjectURL(url)
    previewUrls.delete(id)
  }
  emit('update:modelValue', props.modelValue.filter((e) => e.id !== id))
  emit('remove', id)
}

function retry(id: string): void {
  const entry = props.modelValue.find((e) => e.id === id)
  if (entry) {
    emit('retry', id)
    runUpload(entry)
  }
}

function previewFor(id: string): string | undefined {
  return previewUrls.get(id)
}

onBeforeUnmount(() => {
  for (const url of previewUrls.values()) URL.revokeObjectURL(url)
  previewUrls.clear()
})

defineExpose({ focus: () => inputRef.value?.focus(), openPicker })
</script>

<template>
  <div class="ui-upload" :data-mode="mode">
    <input
      ref="inputRef"
      type="file"
      :accept="acceptAttr"
      :multiple="multiple"
      class="ui-upload__hidden"
      @change="onPickerChange"
    />
    <div
      v-if="mode === 'dropzone'"
      role="button"
      tabindex="0"
      aria-label="Glisser des fichiers ou cliquer pour sélectionner"
      class="ui-upload__dropzone"
      :data-drag="dragOver || undefined"
      @click="openPicker"
      @keydown="onDropzoneKey"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
    >
      <slot name="dropzone">
        <p>Glisser des fichiers ici ou cliquer pour sélectionner</p>
        <p class="ui-upload__hint">
          Max {{ Math.round(maxSize / 1024 / 1024) }} Mo · {{ accept.join(', ') }}
        </p>
      </slot>
    </div>
    <button
      v-else
      type="button"
      class="ui-upload__button"
      :disabled="disabled"
      @click="openPicker"
    >
      Ajouter un fichier
    </button>

    <ul v-if="modelValue.length" class="ui-upload__list">
      <li
        v-for="entry in modelValue"
        :key="entry.id"
        role="listitem"
        class="ui-upload__item"
        :data-status="entry.status"
      >
        <slot name="item" :entry="entry" :preview="previewFor(entry.id)" :remove="() => remove(entry.id)" :retry="() => retry(entry.id)">
          <img v-if="previewFor(entry.id)" :src="previewFor(entry.id)" alt="" class="ui-upload__preview" />
          <div class="ui-upload__meta">
            <strong>{{ entry.file.name }}</strong>
            <span class="ui-upload__hint">{{ Math.round(entry.file.size / 1024) }} Ko · {{ entry.status }}</span>
            <span v-if="entry.error" aria-live="polite" class="ui-upload__error">{{ entry.error }}</span>
            <progress v-if="entry.status === 'uploading'" :value="entry.progress" max="1" />
          </div>
          <button
            v-if="entry.status === 'error'"
            type="button"
            class="ui-upload__btn"
            @click="retry(entry.id)"
          >
            Réessayer
          </button>
          <button
            type="button"
            :aria-label="`Retirer ${entry.file.name}`"
            class="ui-upload__btn"
            @click="remove(entry.id)"
          >
            ×
          </button>
        </slot>
      </li>
    </ul>
    <slot v-else name="empty" />
  </div>
</template>

<style scoped>
.ui-upload__hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  overflow: hidden;
  white-space: nowrap;
}
.ui-upload__dropzone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
  background: var(--color-surface);
  font-family: var(--font-sans);
  min-height: 96px;
}
.ui-upload__dropzone[data-drag] {
  border-color: var(--color-brand-500);
  background: var(--color-brand-50);
}
.ui-upload__dropzone:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
.ui-upload__hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.ui-upload__list {
  list-style: none;
  padding: 0;
  margin: var(--space-3) 0 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.ui-upload__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.ui-upload__item[data-status='error'] {
  border-color: var(--color-danger-500);
}
.ui-upload__preview {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: var(--radius-sm);
}
.ui-upload__meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.ui-upload__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
.ui-upload__btn {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  min-height: 36px;
}
.ui-upload__button {
  background: var(--color-brand-500);
  color: #fff;
  border: 0;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  min-height: 44px;
}
</style>
