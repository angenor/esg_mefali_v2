// Types transverses de la lib UI Primitives (F37).
// Voir specs/037-ui-primitives/data-model.md §1.

export type UiSize = 'sm' | 'md' | 'lg'
export type UiVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'
export type UiSeverity = 'info' | 'success' | 'warning' | 'error'

export interface UiOption<V = string | number> {
  value: V
  label: string
  disabled?: boolean
  description?: string
  group?: string
}

export type UiOptionsLoader<V = string | number> = (q: {
  search: string
  page: number
  pageSize: number
}) => Promise<{ items: UiOption<V>[]; total: number }>

export interface UiToast {
  id: string
  severity: UiSeverity
  title?: string
  message: string
  duration?: number
  actionLabel?: string
  onAction?: () => void
}

export interface UiUploadFile {
  id: string
  file: File
  status: 'queued' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
}

export interface UiFieldStatus {
  invalid: boolean
  errorMessage?: string
  describedById?: string
}
