import type { AnnotatedSegment } from '~/utils/translation-annotator'

const WORD_FINAL_NUMERIC_ARTIFACT_RE = /(\p{L})\d+\)(?=$|[^\p{L}\p{N}])/gu
const LEADING_NUMERIC_ARTIFACT_RE = /^\d+\)(?=$|[^\p{L}\p{N}])/u
const LETTER_RE = /\p{L}/u

export function stripDisplayTranslationArtifacts(text: string) {
  return text.replace(WORD_FINAL_NUMERIC_ARTIFACT_RE, '$1')
}

function endsWithLetter(text: string) {
  const chars = [...text]
  const last = chars[chars.length - 1]
  return Boolean(last && LETTER_RE.test(last))
}

function compactAnnotatedSegments(segments: AnnotatedSegment[]) {
  const compacted: AnnotatedSegment[] = []

  for (const segment of segments) {
    if (!segment.text) continue

    const previous = compacted[compacted.length - 1]
    if (previous?.kind === 'text' && segment.kind === 'text') {
      previous.text += segment.text
    } else if (
      previous?.kind === 'entity'
      && segment.kind === 'entity'
      && previous.source === segment.source
      && previous.entityType === segment.entityType
    ) {
      previous.text += segment.text
    } else {
      compacted.push(segment)
    }
  }

  return compacted
}

export function normalizeDisplayAnnotatedSegments(segments: AnnotatedSegment[]) {
  const normalized: AnnotatedSegment[] = []
  let previousEndedWithLetter = false

  for (const segment of segments) {
    let text = stripDisplayTranslationArtifacts(segment.text)

    if (previousEndedWithLetter) {
      text = text.replace(LEADING_NUMERIC_ARTIFACT_RE, '')
    }

    if (text) {
      normalized.push({ ...segment, text })
      previousEndedWithLetter = endsWithLetter(text)
    }
  }

  return compactAnnotatedSegments(normalized)
}
