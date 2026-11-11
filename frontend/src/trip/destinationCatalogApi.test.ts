import { describe, expect, it, vi } from 'vitest';
import { ApiDestinationCatalogPort } from './destinationCatalogApi';

const available = (items: unknown[]) => new Response(JSON.stringify({
  status: 'available', complete: true, count: items.length, items,
}), { status: 200, headers: { 'Content-Type': 'application/json' } });

describe('same-origin destination catalogue port', () => {
  it('maps a complete empty catalogue to available-empty', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(available([]));
    const result = await new ApiDestinationCatalogPort(fetcher).load();
    expect(result).toEqual({ kind: 'available', boundary: 'knowledge.production_destinations', destinations: [] });
    expect(fetcher).toHaveBeenCalledWith('/api/v1/catalog/destinations', expect.objectContaining({
      method: 'GET', credentials: 'same-origin', cache: 'no-store',
    }));
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty('body');
  });

  it('maps the bounded API identity projection without sending traveler text', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(available([{
      destination_id: '17', destination_key: 'shiraz-city', canonical_name: 'شیراز',
      localized_names: { 'fa-IR': 'شیراز', 'en-US': 'Shiraz', ar: 'شيراز' },
      aliases: [{ locale: 'en-US', value: 'Shiraz', alias_type: 'canonical_display_name' }],
      destination_type: 'city', province_name: 'فارس', city_name: 'شیراز',
    }]));
    const result = await new ApiDestinationCatalogPort(fetcher).load();
    expect(result).toMatchObject({ kind: 'available', destinations: [{
      destinationId: '17', destinationKey: 'shiraz-city', canonicalName: 'شیراز',
      localizedNames: { 'fa-IR': 'شیراز', 'en-US': 'Shiraz', ar: 'شيراز' },
      aliases: [{ locale: 'en-US', value: 'Shiraz', aliasType: 'canonical_display_name' }],
      destinationType: 'city', provinceName: 'فارس', cityName: 'شیراز',
    }] });
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/catalog/destinations');
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty('body');
  });

  it('preserves a valid reference point and rejects malformed coordinates', async () => {
    const item = {
      destination_id: '1', destination_key: 'site', canonical_name: 'Site',
      localized_names: { 'fa-IR': null, 'en-US': null, ar: null }, aliases: [],
      destination_type: 'heritage_site', province_name: 'Fars', city_name: 'Shiraz',
      latitude: 29.6254, longitude: 52.5583, coordinate_role: 'representative_point',
    };
    const valid = await new ApiDestinationCatalogPort(vi.fn<typeof fetch>().mockResolvedValue(available([item]))).load();
    expect(valid).toMatchObject({ kind: 'available', destinations: [{
      coordinate: { latitude: 29.6254, longitude: 52.5583, role: 'representative_point' },
    }] });
    for (const invalid of [
      { ...item, longitude: null }, { ...item, latitude: 91 },
      { ...item, coordinate_role: 'unknown' }, { ...item, coordinate_role: 'test_fixture' },
    ]) {
      expect(await new ApiDestinationCatalogPort(vi.fn<typeof fetch>().mockResolvedValue(available([invalid]))).load())
        .toEqual({ kind: 'unavailable' });
    }
  });

  it.each([
    ['503 unavailable', async () => new Response(JSON.stringify({ status: 'unavailable', error: { code: 'catalogue_unavailable' } }), { status: 503 })],
    ['incomplete result', async () => available([{ destination_id: '1' }])],
    ['invalid alias locale/type', async () => available([{
      destination_id: '1', destination_key: 'sample', canonical_name: 'Sample',
      localized_names: { 'fa-IR': null, 'en-US': null, ar: null }, aliases: [
        { locale: 'fr-FR', value: 'Sample', alias_type: 'made_up' },
      ], destination_type: 'city', province_name: 'Province', city_name: null,
    }])],
    ['count mismatch', async () => new Response(JSON.stringify({ status: 'available', complete: true, count: 1, items: [] }), { status: 200 })],
    ['transport failure', async () => { throw new TypeError('private connection detail'); }],
  ])('fails closed on %s', async (_label, response) => {
    const result = await new ApiDestinationCatalogPort(vi.fn<typeof fetch>().mockImplementation(response as typeof fetch)).load();
    expect(result).toEqual({ kind: 'unavailable' });
    expect(JSON.stringify(result)).not.toContain('private connection detail');
  });
});
