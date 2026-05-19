import type { JTChatMessage, JTChatMessagePart, JTChatTextPart } from '#shared/types/chat'

function sourceToInlineMdc(url: string) {
  return `\n\n${url}`
}

export function isTextPart(part: JTChatMessagePart): part is JTChatTextPart {
  return Boolean(
    part
    && typeof part === 'object'
    && 'type' in part
    && part.type === 'text'
    && 'text' in part
    && typeof part.text === 'string'
  )
}

export function getMergedParts(parts: JTChatMessagePart[] = []): JTChatMessagePart[] {
  const result: JTChatMessagePart[] = []

  for (const part of parts) {
    const prev = result[result.length - 1]

    if (part?.type === 'source-url' && 'url' in part && typeof part.url === 'string') {
      if (prev && isTextPart(prev)) {
        result[result.length - 1] = { type: 'text', text: prev.text + sourceToInlineMdc(part.url) }
      }
      continue
    }

    if (isTextPart(part) && prev && isTextPart(prev)) {
      result[result.length - 1] = { type: 'text', text: prev.text + part.text }
    } else {
      result.push(part)
    }
  }

  return result
}

export function getTextFromMessage(message: Pick<JTChatMessage, 'parts'>) {
  return getMergedParts(message.parts)
    .filter(isTextPart)
    .map(part => part.text)
    .join('\n')
    .trim()
}
