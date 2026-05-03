/**
 * Pinia store éphémère du bottom sheet chat (F39).
 * Aucune persistance : la DB (chat_messages) reste source de vérité (P8, Q1).
 */
import { defineStore } from 'pinia'
import type { ToolInstruction } from '~/types/tools/contracts'

export type CloseReason = 'submit' | 'freetext' | 'cancel'

export interface SheetState {
  current: ToolInstruction | null
  isClosing: boolean
  inFlight: boolean
  error: string | null
  freeTextRequested: boolean
}

export const useChatBottomSheetStore = defineStore('chatBottomSheet', {
  state: (): SheetState => ({
    current: null,
    isClosing: false,
    inFlight: false,
    error: null,
    freeTextRequested: false,
  }),
  getters: {
    isOpen: (state): boolean => state.current !== null,
  },
  actions: {
    setCurrent(instruction: ToolInstruction | null): void {
      this.current = instruction
      this.error = null
      this.freeTextRequested = false
      this.isClosing = false
    },
    markClosing(value: boolean): void {
      this.isClosing = value
    },
    markInFlight(value: boolean): void {
      this.inFlight = value
    },
    setError(message: string | null): void {
      this.error = message
    },
    requestFreeText(): void {
      this.freeTextRequested = true
    },
    reset(): void {
      this.current = null
      this.isClosing = false
      this.inFlight = false
      this.error = null
      this.freeTextRequested = false
    },
  },
})
