import type { DebateState } from '~/types/debate-state'

export function useActiveDebateState() {
  return useState<DebateState | null>('active-debate-state', () => null)
}
