// Development-only structural checker. Input is bounded and never echoed.
import { build } from 'esbuild';

let input = '';
for await (const chunk of process.stdin) {
  input += chunk.toString('utf8');
  if (Buffer.byteLength(input, 'utf8') > 64 * 1024) throw new Error('input exceeds 64 KiB');
}
if (!input.trim()) throw new Error('JSON input required on stdin');
const source = JSON.parse(input);
const bundle = await build({ entryPoints: ['src/trip/tripIntake.ts'], bundle: true, write: false,
  platform: 'node', format: 'esm', logLevel: 'silent' });
const url = `data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].contents).toString('base64')}`;
const { tripRequirementsV1ToTripRequirements } = await import(url);
try {
  const value = tripRequirementsV1ToTripRequirements(source);
  process.stdout.write(`${JSON.stringify({ status: 'converted', destinationKnown: Boolean(value.destinations.value?.length),
    originKnown: Boolean(value.origin.value), durationKnown: Boolean(value.durationDays.value),
    travelerKnown: Boolean(value.travelerCount.value), budgetKnown: Boolean(value.budget.value) })}\n`);
} catch (error) {
  process.stdout.write(`${JSON.stringify({ status: 'failed', errorName: error?.name || 'Error',
    error: 'requirements input did not match the expected contract' })}\n`);
  process.exitCode = 1;
}
