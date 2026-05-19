import { LazyModalConfirm, LazyModalRename } from '#components'

interface ChatListItem {
  id: string
  label: string
  to: string
  icon?: string
  createdAt: string | Date
}

export function useChatActions() {
  const route = useRoute()
  const toast = useToast()
  const overlay = useOverlay()
  const { csrf, headerName } = useCsrf()

  const renameModal = overlay.create(LazyModalRename)
  const deleteModal = overlay.create(LazyModalConfirm, {
    props: {
      title: '대화 삭제',
      description: '이 대화를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.',
      color: 'error'
    }
  })

  async function renameChat(id: string, currentTitle?: string | null): Promise<string | null> {
    const instance = renameModal.open({ title: currentTitle ?? '' })
    const result = await instance.result

    if (!result || result === currentTitle) return null

    try {
      await $fetch(`/api/chats/${id}/title`, {
        method: 'PATCH',
        headers: { [headerName]: csrf },
        body: { title: result }
      })

      const chatsCache = useNuxtData<ChatListItem[]>('chats')
      if (chatsCache.data.value) {
        chatsCache.data.value = chatsCache.data.value.map(c =>
          c.id === id ? { ...c, label: result } : c
        )
      }

      const chatCache = useNuxtData<{ title: string | null }>(`chat-${id}`)
      if (chatCache.data.value) {
        chatCache.data.value = { ...chatCache.data.value, title: result }
      }

      return result
    } catch (error) {
      toast.add({
        description: userFriendlyErrorMessage(error, '대화 이름을 바꾸지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.'),
        icon: 'i-ph-warning-circle',
        color: 'error'
      })

      return null
    }
  }

  async function deleteChat(id: string): Promise<boolean> {
    const instance = deleteModal.open()
    const result = await instance.result

    if (!result) return false

    try {
      await $fetch(`/api/chats/${id}`, {
        method: 'DELETE',
        headers: { [headerName]: csrf }
      })

      toast.add({
        title: '대화가 삭제되었습니다',
        description: '대화가 삭제되었습니다.',
        icon: 'i-ph-trash'
      })

      const chatsCache = useNuxtData<ChatListItem[]>('chats')
      if (chatsCache.data.value) {
        chatsCache.data.value = chatsCache.data.value.filter(c => c.id !== id)
      }

      if (route.params.id === id) {
        navigateTo('/chat')
      }

      return true
    } catch (error) {
      toast.add({
        description: userFriendlyErrorMessage(error, '대화를 삭제하지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.'),
        icon: 'i-ph-warning-circle',
        color: 'error'
      })

      return false
    }
  }

  return {
    renameChat,
    deleteChat
  }
}
