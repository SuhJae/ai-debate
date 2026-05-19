import type { JTReading } from '#shared/types/chat'

export type AnnotatedSegment
  = | { kind: 'text', text: string }
    | { kind: 'entity', text: string, source: string, entityType: string }

export type AnnotationCandidate = {
  variant: string
  source: string
  type: string
  pattern: RegExp
}

// ── Korean syllable decomposition ────────────────────────────────────────────

function choseongIndex(char: string): number | null {
  const code = char.codePointAt(0) ?? 0
  if (code < 0xAC00 || code > 0xD7A3) return null
  return Math.floor((code - 0xAC00) / 588)
}

function jungseongIndex(char: string): number | null {
  const code = char.codePointAt(0) ?? 0
  if (code < 0xAC00 || code > 0xD7A3) return null
  return Math.floor(((code - 0xAC00) % 588) / 28)
}

function replaceChoseong(char: string, newChoseong: number): string {
  const code = char.codePointAt(0) ?? 0
  const offset = code - 0xAC00
  const jung = Math.floor((offset % 588) / 28)
  const jong = offset % 28
  return String.fromCodePoint(0xAC00 + newChoseong * 588 + jung * 28 + jong)
}

// ── 두음법칙 (Korean initial sound law) ──────────────────────────────────────

// Vowel indices that trigger the ㄹ→ㅇ and ㄴ→ㅇ shifts: ㅑ ㅕ ㅖ ㅛ ㅠ ㅣ
const IY_VOWELS = new Set([2, 6, 7, 12, 17, 20])

function dueumVariantSyllable(char: string): string | null {
  const choseong = choseongIndex(char)
  const jung = jungseongIndex(char)
  if (choseong === null || jung === null) return null

  // ㄹ (5): i/y-vowels → ㅇ (11); other vowels → ㄴ (2)
  if (choseong === 5) return replaceChoseong(char, IY_VOWELS.has(jung) ? 11 : 2)

  // ㄴ (2): i/y-vowels → ㅇ (11)
  if (choseong === 2 && IY_VOWELS.has(jung)) return replaceChoseong(char, 11)

  return null
}

function dueumVariants(text: string): Set<string> {
  const variants = new Set([text])
  let changed = true
  while (changed && variants.size < 64) {
    changed = false
    for (const variant of [...variants]) {
      for (let i = 0; i < variant.length; i++) {
        const replacement = dueumVariantSyllable(variant[i]!)
        if (!replacement) continue
        const next = variant.slice(0, i) + replacement + variant.slice(i + 1)
        if (!variants.has(next)) {
          variants.add(next)
          changed = true
        }
      }
    }
  }
  return variants
}

// Optional whitespace between chars to handle model-inserted spaces
function variantPattern(text: string): RegExp {
  const parts = [...text].map(c => c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  return new RegExp(parts.join('[ \\t]*'))
}

// ── Candidate building ────────────────────────────────────────────────────────

export function buildAnnotationCandidates(readings: JTReading[]): AnnotationCandidate[] {
  const candidates: AnnotationCandidate[] = []
  const seen = new Set<string>()

  for (const reading of readings) {
    const sourceText = reading.source_text
    const selected = reading.selected
    const spanType = (reading.type ?? 'other').toLowerCase()
    if (!sourceText || !selected) continue

    // 1-character spam prevention: single syllables are too ambiguous
    if ([...selected].length < 2) continue

    for (const variant of dueumVariants(selected)) {
      const key = `${variant}|${sourceText}`
      if (seen.has(key)) continue
      seen.add(key)
      candidates.push({ variant, source: sourceText, type: spanType, pattern: variantPattern(variant) })
    }
  }

  // Longest-first so longer matches win at the same position
  candidates.sort((a, b) => [...b.variant].length - [...a.variant].length)
  return candidates
}

// ── Full-text annotation ──────────────────────────────────────────────────────

export function annotateText(text: string, candidates: AnnotationCandidate[]): AnnotatedSegment[] {
  if (!candidates.length || !text) return [{ kind: 'text', text }]

  const segments: AnnotatedSegment[] = []
  let remaining = text

  while (remaining) {
    let best: RegExpExecArray | null = null
    let bestCandidate: AnnotationCandidate | null = null

    for (const candidate of candidates) {
      const match = candidate.pattern.exec(remaining)
      if (!match) continue
      if (
        best === null
        || match.index < best.index
        || (match.index === best.index && match[0].length > best[0].length)
      ) {
        best = match
        bestCandidate = candidate
      }
    }

    if (!best || !bestCandidate) {
      segments.push({ kind: 'text', text: remaining })
      break
    }

    if (best.index > 0) {
      segments.push({ kind: 'text', text: remaining.slice(0, best.index) })
    }
    segments.push({ kind: 'entity', text: best[0], source: bestCandidate.source, entityType: bestCandidate.type })
    remaining = remaining.slice(best.index + best[0].length)
  }

  return segments
}
