export type TripRequirements = {
  requestText: string;
  destination: string;
  durationDays: number;
};

export type TripIntakeInput = {
  requestText: string;
  destination: string;
  durationDays: string;
};

export type TripIntakeResult =
  | { kind: 'invalid'; reason: 'request-required' | 'request-too-long' | 'destination-too-long' | 'duration-invalid' }
  | { kind: 'clarification'; missing: Array<'destination' | 'duration'> }
  | { kind: 'ready'; requirements: TripRequirements };

const digitMap: Record<string, string> = {
  '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
  '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
};

export function extractDurationDays(requestText: string): number | null {
  const normalized = Array.from(requestText, character => digitMap[character] ?? character).join('');
  const match = normalized.match(/(?:^|[\s,:;])([0-9]+|one|two|three|یک|دو|سه|واحد|اثنان|اثنين|ثلاثة|ثلاث)\s*(?:days?|روز|أيام|ايام|يوم)(?=$|[\s,.!?؛،])/iu);
  if (!match) return null;
  const words: Record<string, number> = {
    one: 1, two: 2, three: 3, 'یک': 1, 'دو': 2, 'سه': 3,
    'واحد': 1, 'اثنان': 2, 'اثنين': 2, 'ثلاثة': 3, 'ثلاث': 3,
  };
  return words[match[1].toLocaleLowerCase()] ?? Number(match[1]);
}

export function createTripRequirements(input: TripIntakeInput): TripIntakeResult {
  const requestText = input.requestText.trim();
  const destination = input.destination.trim();
  if (requestText.length < 5) return { kind: 'invalid', reason: 'request-required' };
  if (requestText.length > 1200) return { kind: 'invalid', reason: 'request-too-long' };
  if (destination.length > 120) return { kind: 'invalid', reason: 'destination-too-long' };

  const parsedDays = input.durationDays ? Number(input.durationDays) : extractDurationDays(requestText);
  if (parsedDays !== null && (!Number.isInteger(parsedDays) || parsedDays < 1 || parsedDays > 3)) {
    return { kind: 'invalid', reason: 'duration-invalid' };
  }
  const missing: Array<'destination' | 'duration'> = [];
  if (!destination) missing.push('destination');
  if (!parsedDays) missing.push('duration');
  if (missing.length) return { kind: 'clarification', missing };

  return {
    kind: 'ready',
    requirements: { requestText, destination, durationDays: parsedDays as number },
  };
}
