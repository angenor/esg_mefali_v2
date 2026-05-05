import { ref, onMounted, onBeforeUnmount, type Ref } from "vue";

const QUERY = "(prefers-reduced-motion: reduce)";

export function useReducedMotion(): Ref<boolean> {
  const reduced = ref(false);

  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return reduced;
  }

  const mql = window.matchMedia(QUERY);
  reduced.value = mql.matches;

  const handler = (event: MediaQueryListEvent): void => {
    reduced.value = event.matches;
  };

  onMounted(() => {
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handler);
    } else {
      (mql as MediaQueryList & { addListener: (h: typeof handler) => void }).addListener(handler);
    }
  });

  onBeforeUnmount(() => {
    if (typeof mql.removeEventListener === "function") {
      mql.removeEventListener("change", handler);
    } else {
      (mql as MediaQueryList & { removeListener: (h: typeof handler) => void }).removeListener(handler);
    }
  });

  return reduced;
}

export function gsapDuration(d: number, reduced: boolean): number {
  return reduced ? 0 : d;
}
