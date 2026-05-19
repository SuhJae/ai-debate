export const JT_CHAT_INPUT_MAX_LENGTH = 2000

export type JTChatRole = 'user' | 'assistant' | 'system'

export type JTChatTextPart = {
  type: 'text'
  text: string
}

export type JTChatSourcePart = {
  type: 'source-url'
  url: string
}

export type JTChatMessagePart = JTChatTextPart | JTChatSourcePart | Record<string, unknown>

export type JTChatMessage = {
  id: string
  role: JTChatRole
  parts: JTChatMessagePart[]
  createdAt?: string | Date
}

export type JTAnnotationSegment = {
  text: string
  label?: string | null
  type?: string | null
  start: number
  end: number
}

export type JTAnnotationState = {
  segments: JTAnnotationSegment[]
}

export type JTReadingAlternative = {
  text: string
  score?: number | null
  reason?: string | null
}

export type JTReading = {
  span_id?: string | null
  source_text: string
  type?: string | null
  selected: string
  confidence?: number | null
  route?: string | null
  alternatives?: JTReadingAlternative[]
}

export type JTReadingState = {
  readings: JTReading[]
}
