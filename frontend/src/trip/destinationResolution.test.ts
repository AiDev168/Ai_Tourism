import { describe, expect, it } from 'vitest';
import { destinationResolutionMessages } from '../i18n/destinationResolutionMessages';
import { confirmDestinationCandidate, normalizeDestinationName, resolveDestinationNames, type ProductionDestinationCandidate } from './destinationResolution';

type CandidateOverrides = Omit<Partial<ProductionDestinationCandidate>, 'aliases'> & { aliases?: string[] };
const candidate = (overrides: CandidateOverrides = {}): ProductionDestinationCandidate => {
  const { aliases = ['Shiraz', 'شيراز'], ...fields } = overrides;
  return {
    destinationId: '1', destinationKey: 'shiraz-city', canonicalName: 'شیراز',
    localizedNames: { 'fa-IR': 'شیراز' },
    aliases: aliases.map(value => ({ locale: value === 'Shiraz' ? 'en-US' : 'ar', value, aliasType: 'alternate_script_name' })),
    destinationType: 'city', provinceName: 'فارس', cityName: 'شیراز',
    ...fields,
  };
};
const catalogue = (...destinations: ProductionDestinationCandidate[]) => ({
  kind: 'available' as const, boundary: 'knowledge.production_destinations', destinations,
});

describe('production destination resolution contract', () => {
  it('matches a unique canonical name and approved alias', () => {
    const result = resolveDestinationNames(['شیراز', 'Shiraz'], 'en-US', catalogue(candidate()));
    expect(result.kind).toBe('resolved');
    expect(result.items).toEqual([
      { kind: 'resolved', originalPhrase: 'شیراز', destination: expect.objectContaining({ destinationKey: 'shiraz-city' }) },
      { kind: 'resolved', originalPhrase: 'Shiraz', destination: expect.objectContaining({ destinationKey: 'shiraz-city' }) },
    ]);
  });

  it('normalizes Persian and Arabic character variants and safe spacing/punctuation', () => {
    expect(normalizeDestinationName('كاشان')).toBe(normalizeDestinationName('کاشان'));
    expect(normalizeDestinationName('ش‌یراز،')).toBe(normalizeDestinationName('شیراز'));
    expect(normalizeDestinationName('شِيراز')).not.toBe(normalizeDestinationName('شيراز'));
    const result = resolveDestinationNames(['كاشان'], 'ar', catalogue(candidate({ canonicalName: 'کاشان', aliases: [] })));
    expect(result.items[0]).toMatchObject({ kind: 'resolved', destination: { canonicalName: 'کاشان' } });
  });

  it('accepts different-script aliases without runtime translation', () => {
    expect(resolveDestinationNames(['شيراز'], 'ar', catalogue(candidate())).items[0].kind).toBe('resolved');
    expect(resolveDestinationNames(['Shiraz'], 'fa-IR', catalogue(candidate())).items[0].kind).toBe('resolved');
  });

  it('returns every eligible candidate for a collision and never picks the first', () => {
    const result = resolveDestinationNames(['Maragheh'], 'en-US', catalogue(
      candidate({ destinationId: '2', destinationKey: 'observatory', canonicalName: 'رصدخانه مراغه', aliases: ['Maragheh'] }),
      candidate({ destinationId: '3', destinationKey: 'city', canonicalName: 'مراغه', aliases: ['Maragheh'] }),
    ));
    expect(result.kind).toBe('needs-clarification');
    expect(result.items[0]).toMatchObject({ kind: 'ambiguous', originalPhrase: 'Maragheh', candidates: [{ destinationId: '2' }, { destinationId: '3' }] });
  });

  it('resolves a collision only after an explicit traveler choice', () => {
    const pending = resolveDestinationNames(['Maragheh'], 'fa-IR', catalogue(
      candidate({ destinationId: '2', destinationKey: 'observatory', canonicalName: 'رصدخانه مراغه', aliases: ['Maragheh'] }),
      candidate({ destinationId: '3', destinationKey: 'city', canonicalName: 'مراغه', aliases: ['Maragheh'] }),
    ));
    const confirmed = confirmDestinationCandidate(pending, 0, '3');
    expect(confirmed.kind).toBe('resolved');
    expect(confirmed.items[0]).toMatchObject({ kind: 'confirmed', originalPhrase: 'Maragheh', destination: { destinationId: '3' } });
    expect(confirmDestinationCandidate(pending, 0, 'missing')).toBe(pending);
  });

  it('does not fuzzy-resolve an unknown or unsupported expression', () => {
    const result = resolveDestinationNames(['near Shiraz', 'شهر زیبا'], 'fa-IR', catalogue(candidate()));
    expect(result.kind).toBe('needs-clarification');
    expect(result.items.map(item => item.kind)).toEqual(['not-found', 'not-found']);
  });

  it('distinguishes an empty approved catalogue from an unavailable one and rejects another boundary', () => {
    expect(resolveDestinationNames(['Shiraz'], 'en-US', catalogue()).items[0].kind).toBe('catalogue-empty');
    expect(resolveDestinationNames(['Shiraz'], 'en-US', { kind: 'unavailable' }).items[0].kind).toBe('catalogue-unavailable');
    expect(resolveDestinationNames(['Shiraz'], 'en-US', { kind: 'available', boundary: 'knowledge.destinations', destinations: [candidate()] }).items[0].kind)
      .toBe('catalogue-unavailable');
  });

  it('preserves requested route order and repeated phrases', () => {
    const kashan = candidate({ destinationId: '2', destinationKey: 'kashan', canonicalName: 'کاشان', aliases: ['Kashan'] });
    const result = resolveDestinationNames(['Kashan', 'Shiraz', 'Kashan'], 'en-US', catalogue(candidate(), kashan));
    expect(result.originalPhrases).toEqual(['Kashan', 'Shiraz', 'Kashan']);
    expect(result.items.map(item => item.originalPhrase)).toEqual(['Kashan', 'Shiraz', 'Kashan']);
    expect(result.items.map(item => item.kind === 'resolved' ? item.destination.destinationKey : null)).toEqual(['kashan', 'shiraz-city', 'kashan']);
  });

  it('preserves the exact phrase when the approved catalogue is empty', () => {
    const phrase = ' شيراز‌ ';
    const result = resolveDestinationNames([phrase], 'ar', catalogue());
    expect(result.originalPhrases).toEqual([phrase]);
    expect(result.items[0]).toMatchObject({ kind: 'catalogue-empty', originalPhrase: phrase });
  });

  it('provides localized clarification, unavailable, and correction copy in every locale', () => {
    const locales = ['fa-IR', 'en-US', 'ar'] as const;
    const keys = Object.keys(destinationResolutionMessages['fa-IR']).sort();
    for (const locale of locales) {
      expect(Object.keys(destinationResolutionMessages[locale]).sort()).toEqual(keys);
      expect(destinationResolutionMessages[locale].ambiguous).toContain('{phrase}');
      expect(destinationResolutionMessages[locale].unavailable.length).toBeGreaterThan(20);
      expect(destinationResolutionMessages[locale].none.length).toBeGreaterThan(10);
    }
  });
});
