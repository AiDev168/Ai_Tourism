import type { Locale } from '../i18n/messages';

/** Minimal response projection from the same-origin published-catalogue API. */
export type ProductionDestinationCandidate = {
  destinationId: string;
  destinationKey: string;
  canonicalName: string;
  localizedNames: Partial<Record<Locale, string>>;
  aliases: readonly { locale: Locale; value: string; aliasType: string }[];
  destinationType: string;
  provinceName: string | null;
  cityName: string | null;
};

export type ProductionCatalogue =
  | { kind: 'unavailable' }
  | { kind: 'available'; boundary: string; destinations: readonly ProductionDestinationCandidate[] };
export interface ProductionDestinationCatalogPort {
  load(): Promise<ProductionCatalogue>;
}

export type DestinationChoice = Pick<ProductionDestinationCandidate,
  'destinationId' | 'destinationKey' | 'canonicalName' | 'localizedNames' | 'provinceName' | 'cityName'>;
export type DestinationResolutionItem =
  | { kind: 'resolved'; originalPhrase: string; destination: DestinationChoice }
  | { kind: 'confirmed'; originalPhrase: string; destination: DestinationChoice }
  | { kind: 'ambiguous'; originalPhrase: string; candidates: readonly DestinationChoice[] }
  | { kind: 'not-found'; originalPhrase: string }
  | { kind: 'catalogue-unavailable'; originalPhrase: string }
  | { kind: 'catalogue-empty'; originalPhrase: string };

export type DestinationResolution = {
  locale: Locale;
  originalPhrases: readonly string[];
  items: readonly DestinationResolutionItem[];
  kind: 'resolved' | 'needs-clarification' | 'catalogue-unavailable' | 'catalogue-empty';
};

/**
 * Conservative comparison normalization only. It never replaces the user text
 * or canonical identity. No transliteration, diacritic removal, or fuzzy match.
 */
export function normalizeDestinationName(value: string): string {
  return value.normalize('NFC')
    .replace(/[\u0640]/g, '') // Arabic tatweel is ornamental.
    .replace(/[\u200c\u200d\u2060]/g, '') // join controls are comparison-only formatting marks.
    .replace(/[يى]/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/\p{P}+/gu, ' ')
    .replace(/[\p{Z}\s]+/gu, ' ')
    .trim()
    .toLocaleLowerCase('en-US');
}

function choice(candidate: ProductionDestinationCandidate): DestinationChoice {
  return {
    destinationId: candidate.destinationId,
    destinationKey: candidate.destinationKey,
    canonicalName: candidate.canonicalName,
    localizedNames: candidate.localizedNames,
    provinceName: candidate.provinceName,
    cityName: candidate.cityName,
  };
}

export function resolveDestinationNames(
  originalPhrases: readonly string[],
  locale: Locale,
  catalogue: ProductionCatalogue,
): DestinationResolution {
  if (catalogue.kind === 'unavailable') {
    return { locale, originalPhrases: [...originalPhrases], kind: 'catalogue-unavailable',
      items: originalPhrases.map(originalPhrase => ({ kind: 'catalogue-unavailable', originalPhrase })) };
  }

  // Reject any repository projection that does not name the approved boundary.
  if (catalogue.boundary !== 'knowledge.production_destinations') {
    return { locale, originalPhrases: [...originalPhrases], kind: 'catalogue-unavailable',
      items: originalPhrases.map(originalPhrase => ({ kind: 'catalogue-unavailable', originalPhrase })) };
  }

  const eligible = catalogue.destinations;
  if (eligible.length === 0) {
    return { locale, originalPhrases: [...originalPhrases], kind: 'catalogue-empty',
      items: originalPhrases.map(originalPhrase => ({ kind: 'catalogue-empty', originalPhrase })) };
  }

  const items = originalPhrases.map((originalPhrase): DestinationResolutionItem => {
    const needle = normalizeDestinationName(originalPhrase);
    if (!needle) return { kind: 'not-found', originalPhrase };
    const matches = new Map<string, ProductionDestinationCandidate>();
    for (const candidate of eligible) {
      const names = [candidate.canonicalName, ...Object.values(candidate.localizedNames), ...candidate.aliases.map(alias => alias.value)];
      if (names.some(name => typeof name === 'string' && normalizeDestinationName(name) === needle)) {
        matches.set(candidate.destinationId, candidate);
      }
    }
    const found = [...matches.values()];
    if (found.length === 1) return { kind: 'resolved', originalPhrase, destination: choice(found[0]) };
    if (found.length > 1) return { kind: 'ambiguous', originalPhrase, candidates: found.map(choice) };
    return { kind: 'not-found', originalPhrase };
  });
  const kind = items.every(item => item.kind === 'resolved' || item.kind === 'confirmed') ? 'resolved' : 'needs-clarification';
  return { locale, originalPhrases: [...originalPhrases], items, kind };
}

/** Explicit traveler choice resolves a collision without altering their phrase. */
export function confirmDestinationCandidate(
  resolution: DestinationResolution,
  itemIndex: number,
  destinationId: string,
): DestinationResolution {
  const item = resolution.items[itemIndex];
  if (item?.kind !== 'ambiguous') return resolution;
  const candidate = item.candidates.find(option => option.destinationId === destinationId);
  if (!candidate) return resolution;
  const items = [...resolution.items];
  items[itemIndex] = { kind: 'confirmed', originalPhrase: item.originalPhrase, destination: candidate };
  const kind = items.every(result => result.kind === 'resolved' || result.kind === 'confirmed') ? 'resolved' : 'needs-clarification';
  return { ...resolution, items, kind };
}
