type JtHealth = {
  ok: boolean
  version: string | null
  checkedAt: string | null
}

export function useJtHealth() {
  return useFetch<JtHealth>('/api/jt/health', {
    key: 'jt-health',
    server: true,
    default: () => ({
      ok: false,
      version: null,
      checkedAt: null
    })
  })
}
