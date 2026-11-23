/**
 * Fold diacritics (NFD + strip combining marks + lowercase) so ASCII queries
 * such as "rama", "sita", or "balakanda" match IAST text like "rāma" / "sītā".
 */
export function foldDiacritics(input: string): string {
  return input
    .normalize('NFD')
    .replace(/\p{M}+/gu, '')
    .replace(/ṛ/gi, 'r')
    .replace(/ṝ/gi, 'r')
    .replace(/ḷ/gi, 'l')
    .toLowerCase();
}
