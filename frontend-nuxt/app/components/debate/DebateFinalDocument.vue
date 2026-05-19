<script setup lang="ts">
import DebateMarkdown from '~/components/debate/DebateMarkdown.vue'
import type { DebateChatAgent } from '~/types/debate-chat'
import type { DebateState } from '~/types/debate-state'
import { agentColor } from '~/utils/debate-config'

const props = defineProps<{
  state: DebateState
  agents: DebateChatAgent[]
  contents?: Record<string, string>
  loadingPaths?: Record<string, boolean>
}>()

const agentById = computed(() => new Map(props.agents.map(agent => [agent.id, agent])))
const finalDocument = computed(() => props.state.final_document ?? null)
const visible = computed(() =>
  Boolean(
    finalDocument.value
    || ['drafting_final', 'reviewing_final', 'revising_final', 'accepted'].includes(props.state.phase)
  )
)
const title = computed(() => props.state.phase === 'accepted' ? 'Final Document' : 'Final Draft')
type DraftRow = {
  draft_version: number
  draft_path: string
  status: string
  accepted_by: string[]
  reviews: Record<string, Record<string, unknown>>
  current: boolean
}

type ReviewRow = {
  agentId: string
  name: string
  color: ReturnType<typeof agentColor>
  verdict: string
  reason: string
  requiredChanges: string[]
  state: 'reviewing' | 'accepted' | 'rejected' | 'pending'
  icon: string
}

const selectedReview = ref<ReviewRow | null>(null)
const draftRows = computed<DraftRow[]>(() => {
  const document = finalDocument.value
  if (!document) return []

  return document.drafts.map(draft => ({
    draft_version: draft.draft_version,
    draft_path: draft.draft_path,
    status: draft.status,
    accepted_by: draft.accepted_by ?? [],
    reviews: draft.draft_path === document.draft_path && !Object.keys(draft.reviews ?? {}).length
      ? props.state.reviews
      : draft.reviews ?? {},
    current: draft.draft_path === document.draft_path
  }))
})
function reviewRowsForDraft(draft: DraftRow): ReviewRow[] {
  return (
    props.state.turn_order
      .filter(agentId => props.state.agents[agentId]?.status !== 'disabled')
      .map((agentId) => {
        const agent = props.state.agents[agentId]!
        const chatAgent = agentById.value.get(agentId)
        const review = draft.reviews[agentId] ?? {}
        const verdict = typeof review.verdict === 'string'
          ? review.verdict
          : typeof review.status === 'string'
            ? review.status
            : ''
        const accepted = draft.accepted_by.includes(agentId) || verdict === 'accept' || verdict === 'accepted'
        const rejected = verdict === 'reject' || verdict === 'rejected'
        const working = draft.current && agent.status === 'running' && props.state.phase === 'reviewing_final'

        return {
          agentId,
          name: chatAgent?.name ?? agent.display_name ?? agentId,
          color: agentColor(chatAgent?.color),
          verdict,
          reason: typeof review.reason === 'string' ? review.reason : '',
          requiredChanges: Array.isArray(review.required_changes) ? review.required_changes as string[] : [],
          state: working ? 'reviewing' : accepted ? 'accepted' : rejected ? 'rejected' : 'pending',
          icon: working ? 'i-ph-spinner-gap' : accepted ? 'i-ph-check' : rejected ? 'i-ph-x' : 'i-ph-clock'
        }
      })
  )
}

function rowClasses(row: ReviewRow) {
  if (row.state === 'accepted') return [row.color.softClass, row.color.textClass, row.color.borderClass]
  if (row.state === 'rejected') return ['border-error/30 bg-error/5 text-error']
  if (row.state === 'reviewing') return ['border-info/30 bg-info/5 text-info']
  return ['border-default bg-muted/40 text-muted']
}

function statusLabel(row: ReviewRow) {
  if (row.state === 'reviewing') return 'reviewing'
  if (row.state === 'accepted') return 'accepted'
  if (row.state === 'rejected') return 'changes requested'
  return 'waiting'
}

function hasReviewDetails(row: ReviewRow) {
  return row.state === 'rejected' && Boolean(row.reason || row.requiredChanges.length)
}

function acceptedReviewCount(draft: DraftRow) {
  return reviewRowsForDraft(draft).filter(row => row.state === 'accepted').length
}

function draftTitle(draft: DraftRow) {
  if (draft.current && props.state.phase === 'accepted') return 'Final Document'
  return draftRows.value.length > 1 ? `Final Draft v${draft.draft_version}` : title.value
}

function draftContent(draft: DraftRow) {
  return props.contents?.[draft.draft_path] ?? ''
}

function draftLoading(draft: DraftRow) {
  return Boolean(props.loadingPaths?.[draft.draft_path])
}
</script>

<template>
  <div v-if="visible" class="grid gap-3">
    <section
      v-if="!draftRows.length"
      class="grid gap-3 rounded-md border border-default bg-default/45 p-4"
    >
      <UAlert
        color="neutral"
        variant="soft"
        icon="i-ph-file-text"
        title="Final draft is being prepared"
        description="The generated markdown will appear here as soon as the artifact is written."
      />
    </section>

    <section
      v-for="draft in draftRows"
      :key="draft.draft_path"
      class="grid gap-3 rounded-md border border-default bg-default/45 p-4"
    >
      <div class="flex min-w-0 items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 class="truncate text-sm font-semibold text-highlighted">
            {{ draftTitle(draft) }}
          </h2>
          <p class="truncate font-mono text-xs text-muted">
            {{ draft.draft_path }}
          </p>
        </div>
        <UBadge size="sm" variant="soft" color="neutral">
          v{{ draft.draft_version }}
        </UBadge>
      </div>

      <div
        v-if="draftLoading(draft)"
        class="grid h-16 min-w-0 grid-rows-[1rem_2.5rem] gap-1 overflow-hidden rounded-md bg-info/5 p-2 ring ring-info/15"
      >
        <div class="flex min-w-0 items-center gap-1.5 text-xs font-medium leading-4 text-info">
          <UIcon name="i-ph-spinner-gap" class="size-3.5 shrink-0 animate-spin" />
          <span class="truncate">Loading final draft</span>
        </div>
        <p class="line-clamp-2 text-xs leading-5 text-toned">
          Fetching the generated markdown artifact.
        </p>
      </div>

      <div
        v-else-if="draftContent(draft)"
        class="max-h-[34rem] min-w-0 overflow-y-auto rounded-md border border-default bg-default/50 p-3"
      >
        <DebateMarkdown :content="draftContent(draft)" :agents="agents" />
      </div>

      <UAlert
        v-else
        color="neutral"
        variant="soft"
        icon="i-ph-file-text"
        title="Final draft is being prepared"
        description="The generated markdown will appear here as soon as the artifact is written."
      />

      <div v-if="finalDocument" class="grid gap-2">
        <div class="flex h-5 min-w-0 items-center justify-between gap-2">
          <span class="text-xs font-semibold uppercase text-muted">Review Status</span>
          <span class="text-xs text-muted">
            {{ acceptedReviewCount(draft) }} / {{ reviewRowsForDraft(draft).length }} accepted
          </span>
        </div>
        <div class="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="row in reviewRowsForDraft(draft)"
            :key="`${draft.draft_path}-${row.agentId}`"
            class="flex h-8 min-w-0 items-center gap-2 rounded-md border px-2 text-xs"
            :class="rowClasses(row)"
            :title="row.reason || row.requiredChanges.join('; ') || statusLabel(row)"
          >
            <UIcon
              :name="row.icon"
              class="size-3.5 shrink-0"
              :class="row.state === 'reviewing' ? 'animate-spin' : ''"
            />
            <span class="min-w-0 flex-1 truncate font-brand-serif font-semibold">
              {{ row.name }}
            </span>
            <span class="shrink-0 text-[0.7rem]">
              {{ statusLabel(row) }}
            </span>
            <UTooltip v-if="hasReviewDetails(row)" text="Show requested changes">
              <UButton
                type="button"
                icon="i-ph-arrows-out-simple"
                size="xs"
                color="error"
                variant="ghost"
                aria-label="Show requested changes"
                class="-mr-1 shrink-0"
                @click.stop="selectedReview = row"
              />
            </UTooltip>
          </div>
        </div>
      </div>
    </section>

    <UModal
      :open="Boolean(selectedReview)"
      :title="selectedReview ? `${selectedReview.name} requested changes` : 'Requested changes'"
      :description="selectedReview ? `Final review · ${selectedReview.verdict}` : undefined"
      :ui="{ content: 'max-w-2xl overflow-hidden' }"
      @update:open="selectedReview = $event ? selectedReview : null"
    >
      <template #body>
        <div v-if="selectedReview" class="grid min-w-0 gap-4">
          <div v-if="selectedReview.reason" class="grid min-w-0 gap-1.5">
            <div class="text-xs font-semibold uppercase text-muted">
              Reason
            </div>
            <p class="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm leading-6 text-default ring ring-default">
              {{ selectedReview.reason }}
            </p>
          </div>

          <div v-if="selectedReview.requiredChanges.length" class="grid min-w-0 gap-1.5">
            <div class="text-xs font-semibold uppercase text-muted">
              Required changes
            </div>
            <ul class="grid max-h-56 min-w-0 gap-2 overflow-y-auto rounded-md bg-error/5 p-3 text-sm leading-6 text-default ring ring-error/20">
              <li
                v-for="(change, index) in selectedReview.requiredChanges"
                :key="`${selectedReview.agentId}-change-${index}`"
                class="flex min-w-0 gap-2"
              >
                <UIcon name="i-ph-arrow-right" class="mt-1 size-3.5 shrink-0 text-error" />
                <span class="min-w-0 whitespace-pre-wrap">{{ change }}</span>
              </li>
            </ul>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
