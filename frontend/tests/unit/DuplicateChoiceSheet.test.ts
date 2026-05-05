// F50 (T020) — Tests DuplicateChoiceSheet (bottom sheet F39 — FR-006b).
// Vérifie : rendu conditionnel, affichage du document existant, émissions
// reuse / force-new / cancel, fermeture par clic sur le backdrop.

import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"

import DuplicateChoiceSheet from "../../app/components/documents/DuplicateChoiceSheet.vue"
import type { DocumentDetail } from "../../app/types/documents"

function makeDoc(p: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "doc-existing",
    entreprise_id: "e1",
    name: "Statuts SARL.pdf",
    original_filename: "statuts.pdf",
    mime_type: "application/pdf",
    size_bytes: 12345,
    type: "statuts",
    ocr_status: "done",
    ocr_error: null,
    created_at: "2026-04-30T15:00:00Z",
    extraction_payload: { fields: [] },
    extraction_validated_at: null,
    extraction_validated_by: null,
    linked_projets: [],
    tags: [],
    deleted_at: null,
    purge_scheduled_at: null,
    ...p,
  }
}

describe("<DuplicateChoiceSheet> (F50)", () => {
  it("ne rend rien tant que open=false", () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: false,
        filename: "x.pdf",
        existing: makeDoc(),
      },
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it("rend la dialog ARIA et affiche le document existant", () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "Statuts SARL.pdf",
        existing: makeDoc({ name: "Statuts SARL.pdf" }),
      },
    })
    const dlg = wrapper.find('[role="dialog"]')
    expect(dlg.exists()).toBe(true)
    expect(dlg.attributes("aria-modal")).toBe("true")
    expect(wrapper.text()).toContain("Statuts SARL.pdf")
    expect(wrapper.text()).toContain("statut OCR")
  })

  it("émet `reuse` avec l'existingId au clic sur Réutiliser", async () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "x.pdf",
        existing: makeDoc({ id: "doc-42" }),
      },
    })
    await wrapper.find("button.bg-emerald-600").trigger("click")
    expect(wrapper.emitted("reuse")).toEqual([["doc-42"]])
  })

  it("émet `force-new` au clic sur Forcer un nouvel envoi", async () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "x.pdf",
        existing: makeDoc(),
      },
    })
    const buttons = wrapper.findAll("button")
    const forceBtn = buttons.find((b) => b.text() === "Forcer un nouvel envoi")
    expect(forceBtn).toBeDefined()
    await forceBtn!.trigger("click")
    expect(wrapper.emitted("force-new")).toBeTruthy()
    expect(wrapper.emitted("force-new")?.[0]).toEqual([])
  })

  it("émet `cancel` au clic sur Annuler", async () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "x.pdf",
        existing: makeDoc(),
      },
    })
    const buttons = wrapper.findAll("button")
    const cancelBtn = buttons.find((b) => b.text() === "Annuler")
    await cancelBtn!.trigger("click")
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("émet `cancel` au clic sur le backdrop", async () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "x.pdf",
        existing: makeDoc(),
      },
    })
    await wrapper.find('[role="dialog"]').trigger("click")
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("n'émet pas reuse si existing=null", async () => {
    const wrapper = mount(DuplicateChoiceSheet, {
      props: {
        open: true,
        filename: "x.pdf",
        existing: null,
      },
    })
    await wrapper.find("button.bg-emerald-600").trigger("click")
    expect(wrapper.emitted("reuse")).toBeFalsy()
  })
})
