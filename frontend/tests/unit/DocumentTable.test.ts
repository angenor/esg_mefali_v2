// F50 (T028) — Tests DocumentTable.

import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { defineComponent, h } from "vue"

import type { DocumentDetail } from "../../app/types/documents"

// Stub vue-virtual-scroller : RecycleScroller rend simplement les items via slot.
vi.mock("vue-virtual-scroller", () => {
  const RecycleScroller = defineComponent({
    name: "RecycleScroller",
    props: {
      items: { type: Array, default: () => [] },
      itemSize: { type: Number, default: 0 },
      keyField: { type: String, default: "id" },
    },
    setup(props, { slots }) {
      return () =>
        h(
          "div",
          { class: "stub-recycle-scroller" },
          (props.items as DocumentDetail[]).map((item, index) =>
            slots.default ? slots.default({ item, index }) : null,
          ),
        )
    },
  })
  return { RecycleScroller }
})

vi.mock("vue-virtual-scroller/dist/vue-virtual-scroller.css", () => ({}), {
  virtual: true,
})

import DocumentTable from "../../app/components/documents/DocumentTable.vue"

function makeDoc(p: Partial<DocumentDetail> & Pick<DocumentDetail, "id" | "name">): DocumentDetail {
  return {
    entreprise_id: "e",
    original_filename: p.name,
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
  } as DocumentDetail
}

describe("<DocumentTable> (F50)", () => {
  it("rend la grille ARIA et les en-têtes", () => {
    const wrapper = mount(DocumentTable, { props: { items: [] } })
    const grid = wrapper.find('[role="grid"]')
    expect(grid.exists()).toBe(true)
    expect(grid.attributes("aria-label")).toBe("Liste de documents")
    const headers = wrapper.findAll('[role="columnheader"]').map((h) => h.text())
    expect(headers).toContain("Nom")
    expect(headers).toContain("Type")
    expect(headers).toContain("Date")
    expect(headers).toContain("Statut")
    expect(headers).toContain("Taille")
  })

  it("affiche « Chargement… » quand loading=true", () => {
    const wrapper = mount(DocumentTable, {
      props: { items: [], loading: true },
    })
    expect(wrapper.text()).toContain("Chargement")
  })

  it("formate la taille en o/Ko/Mo", () => {
    const wrapper = mount(DocumentTable, {
      props: {
        items: [
          makeDoc({ id: "s", name: "S", size_bytes: 800 }),
          makeDoc({ id: "k", name: "K", size_bytes: 5_000 }),
          makeDoc({ id: "m", name: "M", size_bytes: 5_000_000 }),
        ],
      },
    })
    expect(wrapper.text()).toContain("800 o")
    expect(wrapper.text()).toContain("Ko")
    expect(wrapper.text()).toContain("Mo")
  })

  it("affiche le statut UI mappé", () => {
    const wrapper = mount(DocumentTable, {
      props: {
        items: [
          makeDoc({
            id: "1",
            name: "Validé",
            ocr_status: "done",
            extraction_validated_at: "2026-05-05T10:00:00Z",
          }),
          makeDoc({ id: "2", name: "Vérifier", ocr_status: "done" }),
        ],
      },
    })
    expect(wrapper.text()).toContain("Validé")
    expect(wrapper.text()).toContain("Vérifier")
  })

  it("émet `select` au clic sur une ligne et au Enter", async () => {
    const items = [makeDoc({ id: "row-1", name: "Doc 1" })]
    const wrapper = mount(DocumentTable, { props: { items } })
    const row = wrapper.findAll('[role="row"]').find((r) => r.text().includes("Doc 1"))
    await row!.trigger("click")
    expect(wrapper.emitted("select")?.[0]).toEqual(["row-1"])
    await row!.trigger("keydown.enter")
    expect(wrapper.emitted("select")?.length).toBe(2)
  })

  it("émet `preview` au clic sur le bouton Prévisualiser sans propager au row", async () => {
    const items = [makeDoc({ id: "p-1", name: "Preview" })]
    const wrapper = mount(DocumentTable, { props: { items } })
    const btn = wrapper.findAll("button").find(
      (b) => b.attributes("aria-label") === "Prévisualiser",
    )
    await btn!.trigger("click")
    expect(wrapper.emitted("preview")?.[0]).toEqual(["p-1"])
    expect(wrapper.emitted("select")).toBeFalsy()
  })

  it("émet `delete` au clic sur le bouton Supprimer", async () => {
    const items = [makeDoc({ id: "d-1", name: "Del" })]
    const wrapper = mount(DocumentTable, { props: { items } })
    const btn = wrapper.findAll("button").find(
      (b) => b.attributes("aria-label") === "Supprimer",
    )
    await btn!.trigger("click")
    expect(wrapper.emitted("delete")?.[0]).toEqual(["d-1"])
  })

  it("émet `verify` quand le doc est en statut verify (ocr=done sans validated_at)", async () => {
    const items = [makeDoc({ id: "v-1", name: "Vrf", ocr_status: "done" })]
    const wrapper = mount(DocumentTable, { props: { items } })
    const btn = wrapper.findAll("button").find((b) => b.text() === "Vérifier")
    expect(btn).toBeDefined()
    await btn!.trigger("click")
    expect(wrapper.emitted("verify")?.[0]).toEqual(["v-1"])
  })

  it("met en surbrillance la ligne sélectionnée via selectedId", () => {
    const items = [
      makeDoc({ id: "s-1", name: "A" }),
      makeDoc({ id: "s-2", name: "B" }),
    ]
    const wrapper = mount(DocumentTable, {
      props: { items, selectedId: "s-2" },
    })
    const rowB = wrapper.findAll('[role="row"]').find((r) => r.text().includes("B"))
    expect(rowB?.classes().some((c) => c.includes("emerald-50"))).toBe(true)
  })
})
