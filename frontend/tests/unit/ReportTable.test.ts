// F49 T028 — Tests composant ReportTable.

import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import ReportTable from "../../app/components/rapports/ReportTable.vue"
import type { Rapport } from "../../app/types/reports"

;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

const reports: Rapport[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    type: "conformite",
    referentiel_id: "ESG_MEFALI",
    period_from: "2025-01-01",
    period_to: "2025-12-31",
    created_at: "2026-05-04T10:30:00Z",
    size_bytes: 1024 * 800,
    status: "ready",
    download_filename: "rapport-conformite-2025.pdf",
    referentiels: ["ESG_MEFALI"],
    entity_type: "entreprise",
    entity_id: "22222222-2222-2222-2222-222222222222",
  },
]

describe("<ReportTable>", () => {
  it("affiche les colonnes attendues", () => {
    const w = mount(ReportTable, {
      props: { reports },
      global: { stubs: { UiBadge: { template: "<span><slot /></span>" } } },
    })
    const headers = w.findAll("thead th").map((th) => th.text())
    expect(headers).toEqual(
      expect.arrayContaining([
        "Titre",
        "Type",
        "Période",
        "Date",
        "Taille",
        "Statut",
        "Actions",
      ]),
    )
  })

  it("affiche le chip de statut", () => {
    const w = mount(ReportTable, {
      props: { reports },
      global: { stubs: { UiBadge: { template: "<span class=\"badge\"><slot /></span>" } } },
    })
    expect(w.find('[data-testid="status-chip"]').exists()).toBe(true)
    expect(w.find('[data-testid="status-chip"]').text()).toBe("Prêt")
  })

  it("emit `select` au clic sur une ligne", async () => {
    const w = mount(ReportTable, {
      props: { reports },
      global: { stubs: { UiBadge: { template: "<span><slot /></span>" } } },
    })
    await w.find('[data-testid="report-row"]').trigger("click")
    expect(w.emitted().select?.[0]?.[0]).toBe(reports[0].id)
  })

  it("emit `regenerate` au clic sur le bouton régénérer", async () => {
    const w = mount(ReportTable, {
      props: { reports },
      global: { stubs: { UiBadge: { template: "<span><slot /></span>" } } },
    })
    await w.find('[data-testid="regenerate-btn"]').trigger("click")
    expect(w.emitted().regenerate?.[0]?.[0]).toEqual(reports[0])
  })

  it("affiche le slot empty quand aucune ligne", () => {
    const w = mount(ReportTable, {
      props: { reports: [] },
      slots: { empty: "<p>Vide</p>" },
      global: { stubs: { UiBadge: { template: "<span><slot /></span>" } } },
    })
    expect(w.text()).toContain("Vide")
  })
})
