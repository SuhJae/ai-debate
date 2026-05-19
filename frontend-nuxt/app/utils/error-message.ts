function getRawErrorMessage(error: unknown) {
  if (typeof error === 'string') return error

  if (error && typeof error === 'object') {
    if ('data' in error && error.data && typeof error.data === 'object') {
      const data = error.data as Record<string, unknown>
      if (typeof data.statusMessage === 'string') return data.statusMessage
      if (typeof data.message === 'string') return data.message
    }

    if ('statusMessage' in error && typeof error.statusMessage === 'string') return error.statusMessage
    if ('message' in error && typeof error.message === 'string') return error.message
  }

  return ''
}

export function userFriendlyErrorMessage(error: unknown, fallback = '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.') {
  const message = getRawErrorMessage(error).trim()
  if (!message) return fallback

  if (/csrf|token mismatch|xsrf/i.test(message)) {
    return '보안 확인 시간이 지나 요청을 완료하지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.'
  }

  if (/network|fetch|terminated|load failed|connection|failed to fetch/i.test(message)) {
    return '연결이 잠시 끊겼습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.'
  }

  if (/unauthorized|unauthenticated|jwt|session/i.test(message)) {
    return '로그인 상태를 확인하지 못했습니다. 다시 로그인한 뒤 시도해 주세요.'
  }

  if (/forbidden|permission|not allowed/i.test(message)) {
    return '이 작업을 할 권한을 확인하지 못했습니다. 다시 로그인한 뒤 시도해 주세요.'
  }

  if (/timeout|timed out/i.test(message)) {
    return '응답 시간이 길어 요청을 마치지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }

  if (/internal server error|server error|500/i.test(message)) {
    return '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }

  if (/[가-힣]/.test(message)) return message

  return fallback
}
