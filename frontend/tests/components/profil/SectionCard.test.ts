// F43 T015 — tests SectionCard.vue (toggle lecture/édition, émission update:field).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import SectionCard, {
  type FieldDescriptor,
} from "~/components/profil/SectionCard.vue"

const FIELDS: FieldDescriptor[] = [
  { key: "raison_sociale", label: "Raison sociale", kind: "input", required: true },
  { key: "annee_creation", label: "Année", kind: "year" },
]

describe("SectionCard", () => {
  it("rend le titre et les champs en lecture", () => {
    const wrapper = mount(SectionCard, {
      props: {
        title: "Identité",
        fields: FIELDS,
        data: { raison_sociale: "ACME SARL", annee_creation: 2018 },
      },
    })
    expect(wrapper.text()).toContain("Identité")
    expect(wrapper.text()).toContain("ACME SARL")
    expect(wrapper.text()).toContain("2018")
  })

  it("clique 'Modifier' bascule en édition et émet toggle-edit(true)", async () => {
    const wrapper = mount(SectionCard, {
      props: {
        title: "Identité",
        fields: FIELDS,
        data: { raison_sociale: "ACME" },
      },
    })
    await wrapper.findAll("button").at(-1)?.trigger("click")
    expect(wrapper.emitted("toggle-edit")?.[0]).toEqual([true])
  })

  it("expose les slots éditing/onUpdate qui émet update:field", async () => {
    const wrapper = mount(SectionCard, {
      props: {
        title: "Identité",
        fields: FIELDS,
        data: { raison_sociale: "ACME" },
      },
      slots: {
        default: `
          <template #default="{ onUpdate }">
            <button data-testid="trigger" @click="onUpdate('raison_sociale', 'NEW')">go</button>
          </template>
        `,
      },
    })
    await wrapper.find('[data-testid="trigger"]').trigger("click")
    expect(wrapper.emitted("update:field")?.[0]).toEqual([
      { field: "raison_sociale", value: "NEW" },
    ])
  })

  it("émet open-history au clic sur le bouton historique", async () => {
    const wrapper = mount(SectionCard, {
      props: { title: "Identité", fields: FIELDS, data: {} },
    })
    await wrapper.find('[data-testid="section-history-btn"]').trigger("click")
    expect(wrapper.emitted("open-history")).toBeTruthy()
  })

  it("affiche l'indicateur 'Enregistrement…' quand saving=true sur un champ", () => {
    const wrapper = mount(SectionCard, {
      props: {
        title: "Identité",
        fields: FIELDS,
        data: {},
        saving: { raison_sociale: true },
      },
    })
    expect(wrapper.text()).toContain("Enregistrement")
  })
})
