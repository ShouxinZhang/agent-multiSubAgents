/**
 * Shared CLI helpers for generic scripts.
 */

function parseCliFlags(args, options = {}) {
  const flags = {};
  const boolValue = options.booleanAsString ? 'true' : true;

  for (let i = 0; i < args.length; i += 1) {
    const token = args[i];
    if (!token.startsWith('--')) continue;

    const key = token.slice(2);
    const next = args[i + 1];
    if (!next || next.startsWith('--')) {
      flags[key] = boolValue;
      continue;
    }

    flags[key] = next;
    i += 1;
  }

  return flags;
}

export function parseArgs(args) {
  return parseCliFlags(args, { booleanAsString: false });
}

export function parseFlags(args) {
  return parseCliFlags(args, { booleanAsString: true });
}

export function globToRegex(pattern) {
  const re = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*\*/g, '{{GLOBSTAR}}')
    .replace(/\*/g, '[^/]*')
    .replace(/\?/g, '[^/]')
    .replace(/\{\{GLOBSTAR\}\}/g, '.*');

  return new RegExp(`^${re}$`);
}

