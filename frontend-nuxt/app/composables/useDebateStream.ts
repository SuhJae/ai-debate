import type { Ref } from 'vue'
import type { DebateChatMessage } from '~/types/debate-chat'
import type { DebateState } from '~/types/debate-state'
import { debateCitationTools } from '~/utils/debate-transcript'

type DebateStreamEvent
  = | { type: 'subscribed', debate_id: string }
    | { type: 'pong' }
    | { type: 'state_snapshot', state: DebateState }
    | { type: 'agent_status', agent: string, status: string }
    | { type: 'agent_output_start', agent: string }
    | { type: 'agent_output_chunk', agent: string, chunk: string }
    | { type: 'agent_output_end', agent: string }
    | { type: 'event', event: Record<string, unknown> }

export interface StreamingMessage {
  id: string
  agentId: string
  content: string
  active: boolean
}

export function useDebateStream(
  debateId: Ref<string>,
  debate: Ref<DebateState | null | undefined>,
  options: {
    enabled: Ref<boolean>
    wsBaseUrl: string
  }
) {
  const streaming = ref<Record<string, StreamingMessage>>({})
  const connected = ref(false)
  const socket = shallowRef<WebSocket | null>(null)
  const pendingChunks = new Map<string, string[]>()
  const flushTimers = new Map<string, ReturnType<typeof setTimeout>>()
  const reconnectTimer = shallowRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = ref(0)

  const streamingMessages = computed<DebateChatMessage[]>(() =>
    shouldShowMainStream()
      ? Object.values(streaming.value).map((message) => {
          const display = mainStreamDisplay(message)
          return {
            id: message.id,
            role: 'agent',
            agentId: message.agentId,
            content: display.content,
            createdAt: message.active ? 'streaming' : '',
            citations: debate.value ? debateCitationTools(debate.value) : [],
            streamPreview: display.preview
          }
        })
      : []
  )
  const thesisStreams = computed<Record<string, StreamingMessage>>(() =>
    shouldShowThesisStreams() ? streaming.value : {}
  )

  function connect() {
    disconnect()
    if (!options.enabled.value || !debateId.value) return

    const ws = new WebSocket(`${options.wsBaseUrl}/debates/${debateId.value}`)
    socket.value = ws

    ws.addEventListener('open', () => {
      connected.value = true
      reconnectAttempts.value = 0
      ws.send(JSON.stringify({ type: 'subscribe' }))
    })

    ws.addEventListener('close', () => {
      if (socket.value === ws) {
        connected.value = false
        socket.value = null
        scheduleReconnect()
      }
    })

    ws.addEventListener('error', () => {
      if (socket.value === ws && ws.readyState < WebSocket.CLOSING) {
        ws.close()
      }
    })

    ws.addEventListener('message', (message) => {
      applyEvent(JSON.parse(message.data) as DebateStreamEvent)
    })
  }

  function disconnect() {
    connected.value = false
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
    for (const timer of flushTimers.values()) clearTimeout(timer)
    flushTimers.clear()
    pendingChunks.clear()
    const ws = socket.value
    socket.value = null
    if (ws && ws.readyState < WebSocket.CLOSING) {
      ws.close()
    }
  }

  function scheduleReconnect() {
    if (!import.meta.client || !options.enabled.value || !debateId.value) return
    if (reconnectTimer.value) return

    const delay = Math.min(1000 * 2 ** reconnectAttempts.value, 10000)
    reconnectAttempts.value += 1
    reconnectTimer.value = setTimeout(() => {
      reconnectTimer.value = null
      connect()
    }, delay)
  }

  function applyEvent(event: DebateStreamEvent) {
    if (event.type === 'state_snapshot') {
      debate.value = event.state
      clearCompletedStreams(event.state)
      return
    }

    if (event.type === 'agent_status') {
      const agent = debate.value?.agents[event.agent]
      if (agent) {
        agent.status = event.status
      }
      if (event.status === 'running' && shouldStoreStream()) {
        ensureStream(event.agent)
      }
      return
    }

    if (event.type === 'agent_output_start') {
      if (!shouldStoreStream()) return
      ensureStream(event.agent)
      return
    }

    if (event.type === 'agent_output_chunk') {
      if (!shouldStoreStream()) return
      enqueueChunk(event.agent, event.chunk)
      return
    }

    if (event.type === 'agent_output_end') {
      flushChunks(event.agent)
      const current = streaming.value[event.agent]
      if (!current) return
      streaming.value[event.agent] = {
        ...current,
        active: false
      }
    }
  }

  function ensureStream(agentId: string, initialContent = '') {
    const current = streaming.value[agentId]
    streaming.value = {
      ...streaming.value,
      [agentId]: current
        ? {
            ...current,
            active: true
          }
        : {
            id: `stream-${agentId}-${Date.now()}`,
            agentId,
            content: initialContent,
            active: true
          }
    }
  }

  function enqueueChunk(agentId: string, chunk: string) {
    ensureStream(agentId)
    pendingChunks.set(agentId, [...(pendingChunks.get(agentId) ?? []), chunk])
    if (flushTimers.has(agentId)) return

    flushTimers.set(
      agentId,
      setTimeout(() => {
        flushTimers.delete(agentId)
        flushChunks(agentId)
      }, 32)
    )
  }

  function flushChunks(agentId: string) {
    const chunks = pendingChunks.get(agentId)
    if (!chunks?.length) return
    pendingChunks.delete(agentId)
    const current = streaming.value[agentId]
    if (!current) return
    streaming.value = {
      ...streaming.value,
      [agentId]: {
        ...current,
        content: current.content + chunks.join(''),
        active: true
      }
    }
  }

  function shouldStoreStream() {
    return shouldShowMainStream() || shouldShowThesisStreams()
  }

  function shouldShowMainStream() {
    const phase = debate.value?.phase
    return phase === 'debating' || phase === 'drafting_final' || phase === 'revising_final'
  }

  function shouldShowThesisStreams() {
    const phase = debate.value?.phase
    return phase === 'starting_theses' || phase === 'awaiting_theses'
  }

  function mainStreamDisplay(message: StreamingMessage) {
    if (debate.value?.phase !== 'debating') {
      return {
        content: latestActivityPreview(message.content) || latestContentPreview(message.content) || 'Preparing final draft...',
        preview: true
      }
    }

    const discussion = extractJsonStringField(message.content, 'discussion')
    if (discussion.trim()) {
      return {
        content: discussion,
        preview: false
      }
    }

    return {
      content: latestActivityPreview(message.content),
      preview: true
    }
  }

  function latestActivityPreview(content: string) {
    return content
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)
      .filter(line => !line.startsWith('[event]'))
      .filter(line => line.startsWith('[') || line.startsWith('Thinking'))
      .slice(-2)
      .join('\n')
  }

  function latestContentPreview(content: string) {
    return content
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)
      .slice(-2)
      .join('\n')
  }

  function extractJsonStringField(content: string, fieldName: string) {
    const fieldPattern = new RegExp(`"${fieldName}"\\s*:\\s*"`, 'g')
    let match: RegExpExecArray | null
    let fieldStart = -1

    while ((match = fieldPattern.exec(content))) {
      fieldStart = match.index + match[0].length
    }

    if (fieldStart === -1) return ''

    let result = ''
    let escaping = false

    for (let index = fieldStart; index < content.length; index += 1) {
      const char = content[index]

      if (escaping) {
        result += decodeJsonEscape(char)
        escaping = false
        continue
      }

      if (char === '\\') {
        escaping = true
        continue
      }

      if (char === '"') break
      result += char
    }

    return result
  }

  function decodeJsonEscape(char = '') {
    if (char === 'n') return '\n'
    if (char === 'r') return '\r'
    if (char === 't') return '\t'
    if (char === 'b') return '\b'
    if (char === 'f') return '\f'
    return char
  }

  function clearCompletedStreams(state: DebateState) {
    if (!shouldStoreStream()) {
      streaming.value = {}
      return
    }

    streaming.value = Object.fromEntries(
      Object.entries(streaming.value).filter(([agentId, message]) =>
        message.active
        || state.agents[agentId]?.status === 'running'
        || (shouldShowThesisStreams() && !state.theses[agentId])
      )
    )
  }

  watch([debateId, options.enabled], () => {
    streaming.value = {}
    if (import.meta.client) connect()
  })

  onMounted(connect)
  onBeforeUnmount(disconnect)

  return {
    connected,
    streamingMessages,
    thesisStreams,
    reconnect: connect,
    disconnect
  }
}
