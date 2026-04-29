// F04 — VersionBadge unit test (T103, US7).
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import VersionBadge from '../../app/components/VersionBadge.vue';
import { formatVersionBadge } from '../../app/composables/useVersionBadge';

describe('formatVersionBadge', () => {
  it('renders the French formatted label', () => {
    const txt = formatVersionBadge('GCF', 2, '2026-03-15T00:00:00Z');
    expect(txt).toBe('Évalué selon Référentiel GCF v2 du 15/03/2026');
  });

  it('handles single-digit days/months with zero-pad', () => {
    const txt = formatVersionBadge('SDG', 1, '2026-01-05T00:00:00Z');
    expect(txt).toBe('Évalué selon Référentiel SDG v1 du 05/01/2026');
  });
});

describe('VersionBadge component', () => {
  it('renders the formatted label as text', () => {
    const wrapper = mount(VersionBadge, {
      props: {
        referentielName: 'GCF',
        version: 2,
        validFrom: '2026-03-15T00:00:00Z',
      },
    });
    expect(wrapper.text()).toBe('Évalué selon Référentiel GCF v2 du 15/03/2026');
  });
});
