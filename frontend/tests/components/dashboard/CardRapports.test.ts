// F44 T023 — Tests CardRapports.
import { describe, expect, it } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardRapports from "~/components/dashboard/CardRapports.vue"

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to" :data-href="to"><slot/></a>' },
  ClientOnly: { template: "<div><slot/></div>" },
  QRCodeVue3: { props: ["value"], template: '<canvas data-testid="qr"/>' },
}

setActivePinia(createPinia())

describe("CardRapports", () => {
  it("filled → 3 rapports + 2 attestations actives avec QR cliquable vers /verify/{publicId}", async () => {
    const wrapper = mount(CardRapports, {
      props: {
        vm: {
          kind: "filled",
          data: {
            recentRapports: [
              {
                id: "r1",
                title: "Rapport 1",
                referentielsLabel: "GCF · IFC",
                generatedAt: new Date("2026-04-25"),
                downloadHref: "/rapports/r1.pdf",
              },
            ],
            activeAttestations: [
              {
                id: "att1",
                publicId: "pub-att1",
                generatedAt: new Date("2026-04-20"),
                validUntil: new Date("2027-04-20"),
                verifyHref: "/verify/pub-att1",
              },
            ],
            href: "/rapports",
          },
        },
      },
      global: { stubs: STUBS },
    })
    await flushPromises()
    expect(wrapper.find('[data-testid="rapport-link"]').attributes("data-href")).toBe(
      "/rapports/r1.pdf",
    )
    const att = wrapper.find('[data-testid="attestation-qr"]')
    expect(att.exists()).toBe(true)
    expect(att.attributes("data-href")).toBe("/verify/pub-att1")
  })

  it("empty → CTA", () => {
    const wrapper = mount(CardRapports, {
      props: { vm: { kind: "empty", cta: { label: "G", href: "/rapports" }, message: "M" } },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('a[href="/rapports"]').exists()).toBe(true)
  })

  // F44 T048 [US5] — ≥ 2 attestations actives : QR rendus + lien /verify/{publicId}.
  it("≥ 2 attestations actives → 2 QR rendus avec liens /verify/{publicId}", async () => {
    const wrapper = mount(CardRapports, {
      props: {
        vm: {
          kind: "filled",
          data: {
            recentRapports: [],
            activeAttestations: [
              {
                id: "att1",
                publicId: "pub-1",
                generatedAt: new Date("2026-04-20"),
                validUntil: new Date("2027-04-20"),
                verifyHref: "/verify/pub-1",
              },
              {
                id: "att2",
                publicId: "pub-2",
                generatedAt: new Date("2026-04-21"),
                validUntil: new Date("2027-04-21"),
                verifyHref: "/verify/pub-2",
              },
            ],
            href: "/rapports",
          },
        },
      },
      global: { stubs: STUBS },
    })
    await flushPromises()
    const qrLinks = wrapper.findAll('[data-testid="attestation-qr"]')
    expect(qrLinks.length).toBe(2)
    expect(qrLinks[0]?.attributes("data-href")).toBe("/verify/pub-1")
    expect(qrLinks[1]?.attributes("data-href")).toBe("/verify/pub-2")
  })
})
