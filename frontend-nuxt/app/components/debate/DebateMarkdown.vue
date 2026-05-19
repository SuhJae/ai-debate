<script setup lang="ts">
import { defineComponent, h, resolveComponent, type Component } from 'vue'
import type { DebateChatAgent, DebateToolEvent, DebateToolKind } from '~/types/debate-chat'
import { agentColor } from '~/utils/debate-config'

type ComarkAttributes = Record<string, unknown>
type ComarkElement = [string, ComarkAttributes, ...ComarkNode[]]
type ComarkNode = string | ComarkElement | [null, ComarkAttributes, string]
type ComarkTree = {
  nodes: ComarkNode[]
}
type ComarkPlugin = {
  name: string
  post: (state: { tree: ComarkTree }) => void
}

const props = defineProps<{
  content: string
  agents?: DebateChatAgent[]
  tools?: DebateToolEvent[]
}>()

const emit = defineEmits<{
  agentMention: [agentId: string]
  evidenceCitation: [citationId: string]
}>()

const inlineTokenKey = computed(() => [
  (props.agents ?? []).map(agent => `${agent.id}:${agent.name}:${agent.color}`).join('|'),
  (props.tools ?? []).map(tool => `${tool.id}:${tool.kind}:${tool.actor ?? ''}:${tool.title}`).join('|')
].join('::'))
const agentByMention = computed(() => {
  const agents = props.agents ?? []
  const entries = new Map<string, DebateChatAgent>()

  for (const agent of agents) {
    entries.set(agent.id.toLowerCase(), agent)
    entries.set(agent.name.toLowerCase(), agent)
  }

  return entries
})
const citationByToken = computed(() => {
  const entries = new Map<string, DebateToolEvent>()

  for (const tool of props.tools ?? []) {
    const keys = new Set([tool.id])
    if (tool.id.startsWith('tool-')) keys.add(tool.id.slice(5))
    if (tool.proposalId) keys.add(tool.proposalId)

    for (const key of keys) {
      entries.set(key.toLowerCase(), tool)
    }
  }

  return entries
})

const inlineComponents = computed<Record<string, Component>>(() => ({
  'agent-mention': defineComponent({
    props: {
      agentId: {
        type: String,
        required: true
      },
      label: {
        type: String,
        required: true
      },
      name: {
        type: String,
        required: true
      },
      color: {
        type: String,
        required: true
      }
    },
    setup(componentProps) {
      return () => {
        const color = agentColor(componentProps.color)

        return h(
          'button',
          {
            type: 'button',
            class: [
              'inline-flex h-5 max-w-full cursor-pointer items-center rounded px-1 align-baseline font-brand-serif text-[0.875em] font-semibold leading-none transition hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary dark:hover:brightness-125',
              color.softClass,
              color.textClass
            ],
            title: `Open ${componentProps.name} (<@${componentProps.agentId}>)`,
            onClick: () => emit('agentMention', componentProps.agentId)
          },
          componentProps.label
        )
      }
    }
  }),
  'evidence-citation': defineComponent({
    props: {
      label: {
        type: String,
        required: true
      },
      title: {
        type: String,
        required: true
      },
      icon: {
        type: String,
        required: true
      },
      citationId: {
        type: String,
        required: true
      },
      color: {
        type: String,
        required: true
      }
    },
    setup(componentProps) {
      const UIcon = resolveComponent('UIcon')

      return () => {
        const color = agentColor(componentProps.color)

        return h(
          'button',
          {
            type: 'button',
            class: [
              'inline-flex h-5 max-w-full cursor-pointer items-center gap-1 rounded border bg-transparent px-1 align-baseline font-mono text-[0.78em] font-semibold leading-none transition hover:bg-muted/60 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
              color.borderClass,
              color.textClass
            ],
            title: componentProps.title,
            onClick: () => emit('evidenceCitation', componentProps.citationId)
          },
          [
            h(UIcon, { name: componentProps.icon, class: 'size-3 shrink-0' }),
            h('span', { class: 'min-w-0 truncate' }, componentProps.label)
          ]
        )
      }
    }
  }),
  'file-reference': defineComponent({
    props: {
      label: {
        type: String,
        required: true
      },
      path: {
        type: String,
        required: true
      },
      line: {
        type: String,
        required: false,
        default: ''
      }
    },
    setup(componentProps) {
      const UIcon = resolveComponent('UIcon')

      return () =>
        h(
          'span',
          {
            class: [
              'inline-flex h-5 max-w-full items-center gap-1 rounded border border-default bg-transparent px-1 align-baseline font-mono text-[0.78em] font-semibold leading-none text-toned',
              'cursor-default'
            ],
            title: componentProps.line
              ? `${componentProps.path}:${componentProps.line}`
              : componentProps.path
          },
          [
            h(UIcon, { name: 'i-ph-file-text', class: 'size-3 shrink-0' }),
            h('span', { class: 'min-w-0 truncate' }, componentProps.label)
          ]
        )
    }
  })
}))

const mentionPlugin = computed<ComarkPlugin>(() => ({
  name: 'debate-inline-tokens',
  post(state) {
    state.tree.nodes = state.tree.nodes.map(node => transformInlineTokenNode(node))
  }
}))

function transformInlineTokenNode(node: ComarkNode, parentTag?: string): ComarkNode {
  if (typeof node === 'string') {
    if (parentTag && shouldSkipInlineTokenTransform(parentTag)) return node

    const parts = splitInlineTokenText(node)
    if (parts.length === 1) return node

    return ['span', {}, ...parts]
  }

  if (!Array.isArray(node) || typeof node[0] !== 'string') return node

  const [tag, attributes, ...children] = node
  if (tag === 'a') {
    const fileReference = malformedFileUrlToReference(String(attributes.href ?? ''), children)
    const fileReferenceElement = fileReferenceNode(fileReference)
    if (fileReferenceElement) return fileReferenceElement
  }
  if (shouldSkipInlineTokenTransform(tag)) return node

  return [tag, attributes, ...transformInlineTokenChildren(children, tag)]
}

function shouldSkipInlineTokenTransform(tag: string) {
  return tag === 'code' || tag === 'pre' || tag === 'a' || tag === 'agent-mention' || tag === 'evidence-citation' || tag === 'file-reference'
}

function splitInlineTokenText(text: string): ComarkNode[] {
  const nodes: ComarkNode[] = []
  const inlineTokenPattern = /<@([A-Za-z][\w-]{0,63})>|<((?:ev|consensus)-[A-Za-z0-9][\w.-]{0,127})>|<file:([^>\n]{1,240})>|(https?:\/\/[^\s<>()]+)/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = inlineTokenPattern.exec(text))) {
    const tokenStart = match.index
    const node = match[1]
      ? agentMentionNode(match[1])
      : match[2]
        ? evidenceCitationNode(match[2])
        : match[3]
          ? fileReferenceNode(parseFileReference(match[3]))
          : fileReferenceNode(malformedFileUrlToReference(match[4] ?? ''))

    if (!node) continue

    if (tokenStart > lastIndex) nodes.push(text.slice(lastIndex, tokenStart))
    nodes.push(node)
    lastIndex = tokenStart + match[0].length
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex))

  return nodes.length ? nodes : [text]
}

function transformInlineTokenChildren(children: ComarkNode[], parentTag: string): ComarkNode[] {
  const nodes: ComarkNode[] = []
  let buffer = ''

  const flush = () => {
    if (!buffer) return
    nodes.push(...splitInlineTokenText(buffer))
    buffer = ''
  }

  for (const child of children) {
    const transparentText = transparentTextNode(child)
    if (transparentText !== null) {
      buffer += isOpenFileReferenceBuffer(buffer) && isTransparentSpanNode(child)
        ? `[${transparentText}]`
        : transparentText
      continue
    }

    flush()
    nodes.push(transformInlineTokenNode(child, parentTag))
  }

  flush()
  return nodes
}

function isOpenFileReferenceBuffer(text: string) {
  const openIndex = text.lastIndexOf('<file:')
  return openIndex !== -1 && text.indexOf('>', openIndex) === -1
}

function isTransparentSpanNode(node: ComarkNode): boolean {
  return Array.isArray(node) && node[0] === 'span'
}

function transparentTextNode(node: ComarkNode): string | null {
  if (typeof node === 'string') return node
  if (!Array.isArray(node) || node[0] !== 'span') return null

  const [, attributes, ...children] = node
  if (Object.keys(attributes).length > 0) return null

  const text = flattenText(children)
  return text || null
}

type FileReference = {
  path: string
  line?: string
}

function parseFileReference(value: string): FileReference {
  const trimmed = value.trim()
  const lineMatch = trimmed.match(/^(.*?):(\d{1,6}(?:-\d{1,6})?)$/)
  if (!lineMatch) return { path: trimmed }
  return {
    path: lineMatch[1] ?? trimmed,
    line: lineMatch[2]
  }
}

function malformedFileUrlToReference(href: string, children: ComarkNode[] = []): FileReference | null {
  const childText = flattenText(children)
  const source = href || childText
  const match = source.match(/^https?:\/\/(.+?\.(?:c|cc|cpp|css|go|h|hpp|html|java|js|jsx|json|kt|md|py|rs|sh|sql|swift|toml|ts|tsx|vue|ya?ml)):(\d{1,6})\/?$/)
  if (!match) return null

  return {
    path: match[1] ?? childText,
    line: match[2]
  }
}

function flattenText(nodes: ComarkNode[]): string {
  return nodes.map((node) => {
    if (typeof node === 'string') return node
    if (Array.isArray(node) && typeof node[0] === 'string') {
      return flattenText(node.slice(2) as ComarkNode[])
    }
    if (Array.isArray(node) && node[0] === null) return String(node[2] ?? '')
    return ''
  }).join('')
}

function fileReferenceNode(reference: FileReference | null): ComarkNode | null {
  if (!reference?.path) return null
  const label = reference.line ? `${reference.path}:${reference.line}` : reference.path
  return [
    'file-reference',
    {
      label,
      path: reference.path,
      line: reference.line ?? ''
    },
    label
  ]
}

function agentMentionNode(mentionName: string): ComarkNode | null {
  const agent = agentByMention.value.get(mentionName.toLowerCase())
  if (!agent) return null

  const label = `@${agent.name}`
  return [
    'agent-mention',
    {
      agentId: agent.id,
      label,
      name: agent.name,
      color: agent.color
    },
    label
  ]
}

function evidenceCitationNode(citationId: string): ComarkNode | null {
  const evidence = citationByToken.value.get(citationId.toLowerCase())
  if (!evidence) return null

  const actorColor = evidence.actor
    ? agentByMention.value.get(evidence.actor.toLowerCase())?.color
    : undefined

  return [
    'evidence-citation',
    {
      label: citationId,
      citationId,
      title: evidence.title,
      icon: evidenceIcon(evidence.kind),
      color: actorColor ?? 'slate'
    },
    citationId
  ]
}

function evidenceIcon(kind: DebateToolKind) {
  if (kind === 'file_evidence') return 'i-ph-file-text'
  if (kind === 'terminal_probe') return 'i-ph-terminal-window'
  if (kind === 'web_evidence') return 'i-ph-globe'
  if (kind === 'mcp_proposal') return 'i-ph-book-open-text'
  if (kind === 'consensus') return 'i-ph-handshake'
  return 'i-ph-file-text'
}
</script>

<template>
  <div class="debate-markdown min-w-0 max-w-full overflow-hidden text-sm leading-6 text-default">
    <ClientOnly>
      <Comark
        :key="inlineTokenKey"
        :markdown="content"
        :options="{ html: false }"
        :plugins="[mentionPlugin]"
        :components="inlineComponents"
      />
      <template #fallback>
        <p class="whitespace-pre-wrap">
          {{ content }}
        </p>
      </template>
    </ClientOnly>
  </div>
</template>

<style scoped>
.debate-markdown {
  overflow-wrap: anywhere;
}

.debate-markdown :deep(:where(p, ul, ol, pre, blockquote, table)) {
  margin-block: 0.65rem;
}

.debate-markdown :deep(:where(p:first-child, ul:first-child, ol:first-child, pre:first-child, blockquote:first-child)) {
  margin-top: 0;
}

.debate-markdown :deep(:where(p:last-child, ul:last-child, ol:last-child, pre:last-child, blockquote:last-child)) {
  margin-bottom: 0;
}

.debate-markdown :deep(:where(h1, h2, h3, h4)) {
  color: var(--ui-text-highlighted);
  font-weight: 650;
  line-height: 1.25;
  margin-block: 0.85rem 0.45rem;
}

.debate-markdown :deep(h1) {
  font-size: 1.25rem;
}

.debate-markdown :deep(h2) {
  font-size: 1.1rem;
}

.debate-markdown :deep(h3) {
  font-size: 1rem;
}

.debate-markdown :deep(:where(ul, ol)) {
  padding-inline-start: 1.25rem;
}

.debate-markdown :deep(ul) {
  list-style: disc;
}

.debate-markdown :deep(ol) {
  list-style: decimal;
}

.debate-markdown :deep(li + li) {
  margin-top: 0.25rem;
}

.debate-markdown :deep(a) {
  color: var(--ui-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.debate-markdown :deep(blockquote) {
  border-inline-start: 2px solid var(--ui-border-accented);
  color: var(--ui-text-toned);
  padding-inline-start: 0.75rem;
}

.debate-markdown :deep(:not(pre) > code) {
  background: var(--ui-bg-accented);
  border-radius: 0.25rem;
  color: var(--ui-text-highlighted);
  font-family: var(--font-mono);
  font-size: 0.85em;
  padding: 0.08rem 0.3rem;
}

.debate-markdown :deep(pre) {
  background: var(--ui-bg-muted);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius);
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  padding: 0.8rem;
  white-space: pre;
}

.debate-markdown :deep(pre code) {
  background: transparent;
  color: var(--ui-text);
  display: block;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.65;
  min-width: 100%;
  padding: 0;
  white-space: pre;
  width: max-content;
}

.debate-markdown :deep(table) {
  border-collapse: collapse;
  display: block;
  max-width: 100%;
  overflow-x: auto;
  width: 100%;
}

.debate-markdown :deep(:where(th, td)) {
  border: 1px solid var(--ui-border);
  padding: 0.4rem 0.55rem;
  text-align: start;
}

.debate-markdown :deep(th) {
  background: var(--ui-bg-muted);
  color: var(--ui-text-highlighted);
  font-weight: 600;
}
</style>
