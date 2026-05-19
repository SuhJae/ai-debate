export type JTQueueEta = {
  usersAhead?: number
  jobsAhead?: number
  queuePosition?: number
  activeJobAhead?: boolean
  estimateOverdue?: boolean
  estimatedStartSeconds?: number | null
  estimatedCompletionSeconds?: number | null
}

export type JTQueueStatusLike = {
  phase?: string
  status?: string
  eta?: JTQueueEta
  queueEnteredAt?: string | null
  l4StartedAt?: string | null
}

export function formatQueueDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.floor(totalSeconds))
  if (seconds < 60) return `${seconds}초`

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  if (minutes < 60) return remainder ? `${minutes}분 ${remainder}초` : `${minutes}분`

  const hours = Math.floor(minutes / 60)
  const minuteRemainder = minutes % 60
  return minuteRemainder ? `${hours}시간 ${minuteRemainder}분` : `${hours}시간`
}

export function formatTranslationQueueStatus(job: JTQueueStatusLike | null | undefined, nowMs = Date.now()) {
  if (!job) return '번역하는 중...'

  if (job.status === 'queued' && job.phase === 'queued_layer4') {
    const jobsAhead = job.eta?.jobsAhead ?? 0
    const usersAhead = job.eta?.usersAhead ?? 0
    const queuePosition = job.eta?.queuePosition ?? jobsAhead + 1
    const startSeconds = job.eta?.estimatedStartSeconds ?? 0
    const enteredAt = job.queueEnteredAt ? Date.parse(job.queueEnteredAt) : NaN
    const elapsedSeconds = Number.isFinite(enteredAt) ? Math.max(0, (nowMs - enteredAt) / 1000) : null

    const position = `대기열 ${Math.max(1, queuePosition)}번째${usersAhead > 0 ? ` · 앞에 ${usersAhead}명` : ''}`
    const eta = job.eta?.estimateOverdue
      ? '이전 작업 처리 중'
      : startSeconds && startSeconds > 0
        ? `시작 예상 ${formatQueueDuration(startSeconds)}`
        : '시작 준비 중'
    const elapsed = elapsedSeconds !== null ? `대기 ${formatQueueDuration(elapsedSeconds)}` : null

    return ['대기 중', position, eta, elapsed].filter(Boolean).join(' · ')
  }

  if (job.status === 'running' && job.phase === 'layer4') return '번역하는 중...'
  if (job.status === 'queued' || job.status === 'running') return '번역 준비 중...'

  return '번역하는 중...'
}
