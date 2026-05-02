import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { useReducedMotion, gsapDuration } from "../../app/composables/useReducedMotion";

interface MockMQL {
  matches: boolean;
  media: string;
  onchange: null;
  addEventListener: (type: string, listener: (e: MediaQueryListEvent) => void) => void;
  removeEventListener: (type: string, listener: (e: MediaQueryListEvent) => void) => void;
  addListener: (l: (e: MediaQueryListEvent) => void) => void;
  removeListener: (l: (e: MediaQueryListEvent) => void) => void;
  dispatchEvent: (event: Event) => boolean;
  __listeners: Array<(e: MediaQueryListEvent) => void>;
}

function createMockMatchMedia(initial: boolean): MockMQL {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  const mql: MockMQL = {
    matches: initial,
    media: "(prefers-reduced-motion: reduce)",
    onchange: null,
    addEventListener: (_type, listener) => listeners.push(listener),
    removeEventListener: (_type, listener) => {
      const i = listeners.indexOf(listener);
      if (i >= 0) listeners.splice(i, 1);
    },
    addListener: (l) => listeners.push(l),
    removeListener: (l) => {
      const i = listeners.indexOf(l);
      if (i >= 0) listeners.splice(i, 1);
    },
    dispatchEvent: () => true,
    __listeners: listeners,
  };
  return mql;
}

function mountWithComposable() {
  let value: { value: boolean } | null = null;
  const Comp = defineComponent({
    setup() {
      value = useReducedMotion();
      return () => h("div");
    },
  });
  const wrapper = mount(Comp);
  return { wrapper, getRef: () => value! };
}

describe("useReducedMotion", () => {
  let originalMatchMedia: typeof window.matchMedia | undefined;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    if (originalMatchMedia) {
      window.matchMedia = originalMatchMedia;
    }
    vi.restoreAllMocks();
  });

  it("retourne false quand l'utilisateur n'a pas demandé reduced motion", () => {
    const mql = createMockMatchMedia(false);
    window.matchMedia = vi.fn().mockReturnValue(mql);

    const { getRef } = mountWithComposable();
    expect(getRef().value).toBe(false);
  });

  it("retourne true quand l'utilisateur a demandé reduced motion", () => {
    const mql = createMockMatchMedia(true);
    window.matchMedia = vi.fn().mockReturnValue(mql);

    const { getRef } = mountWithComposable();
    expect(getRef().value).toBe(true);
  });

  it("met à jour la valeur quand l'événement change est dispatché", async () => {
    const mql = createMockMatchMedia(false);
    window.matchMedia = vi.fn().mockReturnValue(mql);

    const { getRef } = mountWithComposable();
    expect(getRef().value).toBe(false);

    for (const l of mql.__listeners) {
      l({ matches: true, media: mql.media } as MediaQueryListEvent);
    }
    await nextTick();
    expect(getRef().value).toBe(true);
  });

  it("retombe sur false en SSR (pas de window.matchMedia)", () => {
    const original = window.matchMedia;
    // @ts-expect-error simulation SSR
    delete window.matchMedia;

    const { getRef } = mountWithComposable();
    expect(getRef().value).toBe(false);

    window.matchMedia = original;
  });
});

describe("gsapDuration", () => {
  it("retourne 0 quand reduced=true", () => {
    expect(gsapDuration(0.5, true)).toBe(0);
  });

  it("retourne la durée d'origine quand reduced=false", () => {
    expect(gsapDuration(0.5, false)).toBe(0.5);
  });
});
