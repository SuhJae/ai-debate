export function useModelOnline() {
  const { data } = useNuxtData<{ ok: boolean }>('jt-health')
  return computed(() => data.value?.ok === true)
}
