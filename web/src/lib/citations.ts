/**
 * The LLM is asked to cite context blocks inline as [1], [2], [1, 3] or [1-3].
 * These helpers find those markers so the UI can link each one to its passage.
 */

const CITATION_RE = /\[(\d+(?:\s*[-–,]\s*\d+)*)\]/g;

/** Expand "1, 3-5" into [1, 3, 4, 5], ignoring anything outside 1..max. */
export function parseCitationGroup(group: string, max: number): number[] {
  const out = new Set<number>();
  for (const part of group.split(",")) {
    const [a, b] = part.split(/[-–]/).map((n) => parseInt(n.trim(), 10));
    if (Number.isNaN(a)) continue;
    const end = Number.isNaN(b ?? NaN) ? a : b;
    for (let i = Math.min(a, end); i <= Math.max(a, end) && i - a < 20; i++) {
      if (i >= 1 && i <= max) out.add(i);
    }
  }
  return [...out].sort((x, y) => x - y);
}

/** All passage numbers cited anywhere in the answer. */
export function citedPassages(answer: string, max: number): Set<number> {
  const cited = new Set<number>();
  for (const m of answer.matchAll(CITATION_RE)) {
    parseCitationGroup(m[1], max).forEach((n) => cited.add(n));
  }
  return cited;
}

/**
 * Rewrite [n] markers as markdown links with a custom scheme so the
 * markdown renderer gives us a hook: [1] -> [[1]](#cite-1).
 * Markers that don't map to a real passage are left untouched.
 */
export function linkCitations(answer: string, max: number): string {
  return answer.replace(CITATION_RE, (whole, group: string) => {
    const nums = parseCitationGroup(group, max);
    if (nums.length === 0) return whole;
    return nums.map((n) => `[[${n}]](#cite-${n})`).join("");
  });
}

/** "pubmed:12345" -> "PMID 12345", "pdf:review.pdf" -> "review.pdf" */
export function formatSource(source: string): string {
  if (source.startsWith("pubmed:")) return `PMID ${source.slice(7)}`;
  if (source.startsWith("pdf:")) return source.slice(4);
  return source;
}
