import { isToday, isYesterday, subMonths } from 'date-fns'

export interface UIChat {
  id: string
  label: string
  to: string
  icon: string
  createdAt: string
}

export function useChats(chats: Ref<UIChat[] | undefined>) {
  const groups = computed(() => {
    const today: UIChat[] = []
    const yesterday: UIChat[] = []
    const lastWeek: UIChat[] = []
    const lastMonth: UIChat[] = []
    const older: Record<string, { label: string, items: UIChat[] }> = {}

    const oneWeekAgo = subMonths(new Date(), 0.25)
    const oneMonthAgo = subMonths(new Date(), 1)

    chats.value?.forEach((chat) => {
      const chatDate = new Date(chat.createdAt)

      if (isToday(chatDate)) {
        today.push(chat)
      } else if (isYesterday(chatDate)) {
        yesterday.push(chat)
      } else if (chatDate >= oneWeekAgo) {
        lastWeek.push(chat)
      } else if (chatDate >= oneMonthAgo) {
        lastMonth.push(chat)
      } else {
        const monthKey = `${chatDate.getFullYear()}-${String(chatDate.getMonth() + 1).padStart(2, '0')}`
        const monthLabel = chatDate.toLocaleDateString('en-US', {
          month: 'long',
          year: 'numeric'
        })

        if (!older[monthKey]) {
          older[monthKey] = {
            label: monthLabel,
            items: []
          }
        }

        older[monthKey].items.push(chat)
      }
    })

    const sortedMonthKeys = Object.keys(older).sort((a, b) => b.localeCompare(a))

    const formattedGroups = [] as Array<{
      id: string
      label: string
      items: Array<UIChat>
    }>

    if (today.length) {
      formattedGroups.push({
        id: 'today',
        label: 'Today',
        items: today
      })
    }

    if (yesterday.length) {
      formattedGroups.push({
        id: 'yesterday',
        label: 'Yesterday',
        items: yesterday
      })
    }

    if (lastWeek.length) {
      formattedGroups.push({
        id: 'last-week',
        label: 'Last 7 Days',
        items: lastWeek
      })
    }

    if (lastMonth.length) {
      formattedGroups.push({
        id: 'last-month',
        label: 'Last 30 Days',
        items: lastMonth
      })
    }

    sortedMonthKeys.forEach((monthKey) => {
      if (older[monthKey]?.items.length) {
        formattedGroups.push({
          id: monthKey,
          label: older[monthKey].label,
          items: older[monthKey].items
        })
      }
    })

    return formattedGroups
  })

  return {
    groups
  }
}
