import type { ProductionCatalogue, ProductionDestinationCandidate, ProductionDestinationCatalogPort } from './destinationResolution';

type CatalogueApiItem = {
  destination_id: string;
  destination_key: string;
  canonical_name: string;
  localized_names: Record<'fa-IR' | 'en-US' | 'ar', string | null>;
  aliases: Array<{ locale: 'fa-IR' | 'en-US' | 'ar'; value: string; alias_type: 'canonical_display_name' | 'spelling_variant' | 'alternate_script_name' | 'exonym' }>;
  destination_type: string;
  province_name: string;
  city_name: string | null;
  latitude?: number | null;
  longitude?: number | null;
  coordinate_role?: 'unknown' | 'representative_point' | 'property_reference' | 'visitor_entrance' | null;
};

type CatalogueApiResponse = {
  status: 'available';
  complete: true;
  count: number;
  items: CatalogueApiItem[];
};

const API_PATH = '/api/v1/catalog/destinations';
const MAX_CATALOGUE_ITEMS = 1_000;
const MAX_ALIASES_PER_ITEM = 32;
const unavailable: ProductionCatalogue = { kind: 'unavailable' };
const locales = ['fa-IR', 'en-US', 'ar'] as const;
const aliasTypes = ['canonical_display_name', 'spelling_variant', 'alternate_script_name', 'exonym'] as const;

function boundedText(value: unknown, maximum: number): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= maximum;
}

function isCatalogueApiItem(value: unknown): value is CatalogueApiItem {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  const latitude = item.latitude ?? null;
  const longitude = item.longitude ?? null;
  const role = item.coordinate_role ?? null;
  const validRole = role === null || role === 'unknown' || role === 'representative_point'
    || role === 'property_reference' || role === 'visitor_entrance';
  const validPoint = latitude === null && longitude === null || (
    typeof latitude === 'number' && Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
    && typeof longitude === 'number' && Number.isFinite(longitude) && longitude >= -180 && longitude <= 180
    && role !== null && role !== 'unknown'
  );
  return typeof item.destination_id === 'string'
    && /^\d+$/.test(item.destination_id)
    && boundedText(item.destination_key, 240)
    && boundedText(item.canonical_name, 240)
    && typeof item.localized_names === 'object'
    && item.localized_names !== null
    && locales.length === Object.keys(item.localized_names).length
    && locales.every(locale => {
      const name = (item.localized_names as Record<string, unknown>)[locale];
      return name === null || boundedText(name, 240);
    })
    && boundedText(item.destination_type, 64)
    && boundedText(item.province_name, 240)
    && (boundedText(item.city_name, 240) || item.city_name === null)
    && validRole && validPoint
    && Array.isArray(item.aliases)
    && item.aliases.length <= MAX_ALIASES_PER_ITEM
    && item.aliases.every(alias => Boolean(alias) && typeof alias === 'object'
      && locales.includes(alias.locale)
      && boundedText(alias.value, 200)
      && aliasTypes.includes(alias.alias_type));
}

function isCatalogueApiResponse(value: unknown): value is CatalogueApiResponse {
  if (!value || typeof value !== 'object') return false;
  const response = value as Record<string, unknown>;
  return response.status === 'available'
    && response.complete === true
    && Number.isInteger(response.count)
    && (response.count as number) >= 0
    && (response.count as number) <= MAX_CATALOGUE_ITEMS
    && Array.isArray(response.items)
    && response.items.length === response.count
    && response.items.every(isCatalogueApiItem);
}

/** Same-origin, read-only catalogue transport. It never includes traveler input. */
export class ApiDestinationCatalogPort implements ProductionDestinationCatalogPort {
  constructor(
    private readonly fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
    private readonly timeoutMs = 4_000,
  ) {}

  async load(): Promise<ProductionCatalogue> {
    try {
      const response = await this.fetcher(API_PATH, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(this.timeoutMs),
      });
      if (!response.ok) return unavailable;
      const payload: unknown = await response.json();
      if (!isCatalogueApiResponse(payload)) return unavailable;

      const destinations: ProductionDestinationCandidate[] = payload.items.map(item => ({
        destinationId: item.destination_id,
        destinationKey: item.destination_key,
        canonicalName: item.canonical_name,
        localizedNames: Object.fromEntries(Object.entries(item.localized_names).filter(([, name]) => typeof name === 'string')) as Partial<Record<'fa-IR' | 'en-US' | 'ar', string>>,
        aliases: item.aliases.map(alias => ({ locale: alias.locale, value: alias.value, aliasType: alias.alias_type })),
        destinationType: item.destination_type,
        provinceName: item.province_name,
        cityName: item.city_name,
        ...(item.latitude != null && item.longitude != null && item.coordinate_role
          && item.coordinate_role !== 'unknown' ? { coordinate: {
            latitude: item.latitude, longitude: item.longitude, role: item.coordinate_role,
          } } : {}),
      }));
      return { kind: 'available', boundary: 'knowledge.production_destinations', destinations };
    } catch {
      return unavailable;
    }
  }
}
