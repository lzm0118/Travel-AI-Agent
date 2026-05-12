import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatAPI, createSessionId } from '../utils/api'

export const useChatStore = defineStore('chat', () => {
  // State
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)

  // Getters
  const currentSession = computed(() => {
    return sessions.value.find(s => s.id === currentSessionId.value)
  })

  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) => 
      new Date(b.updatedAt) - new Date(a.updatedAt)
    )
  })

  // Actions
  const createNewSession = () => {
    const sessionId = createSessionId()
    const session = {
      id: sessionId,
      title: '新对话',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messageCount: 0
    }
    
    sessions.value.unshift(session)
    currentSessionId.value = sessionId
    messages.value = []
    
    return sessionId
  }

  const setCurrentSession = (sessionId) => {
    currentSessionId.value = sessionId
    messages.value = []
    // 这里可以加载历史消息
  }

  const sendMessage = async (content) => {
    if (!currentSessionId.value) {
      createNewSession()
    }

    // 添加用户消息到列表
    const userMessage = {
      role: 'user',
      content,
      timestamp: new Date()
    }
    messages.value.push(userMessage)

    // 更新会话
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session) {
      session.updatedAt = new Date().toISOString()
      session.messageCount++
      if (session.title === '新对话') {
        session.title = content.slice(0, 20) + (content.length > 20 ? '...' : '')
      }
    }

    isLoading.value = true

    try {
      const response = await chatAPI.sendMessage({
        message: content,
        session_id: currentSessionId.value
      })

      if (response.data && response.data.success) {
        // 添加助手回复
        messages.value.push({
          role: 'assistant',
          content: response.data.message,
          tools_used: response.data.tools_used || [],
          timestamp: new Date()
        })

        // 更新会话ID（如果后端返回了新的）
        if (response.data.session_id !== currentSessionId.value) {
          currentSessionId.value = response.data.session_id
        }

        return { success: true }
      } else {
        throw new Error(response.data?.message || '发送失败')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      
      // 添加错误消息
      messages.value.push({
        role: 'assistant',
        content: '抱歉，服务暂时不可用，请稍后重试。',
        isError: true,
        timestamp: new Date()
      })

      return { success: false, error }
    } finally {
      isLoading.value = false
    }
  }

  const deleteSession = (sessionId) => {
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index > -1) {
      sessions.value.splice(index, 1)
      
      // 如果删除的是当前会话，切换到第一个或创建新会话
      if (currentSessionId.value === sessionId) {
        if (sessions.value.length > 0) {
          setCurrentSession(sessions.value[0].id)
        } else {
          createNewSession()
        }
      }
    }
  }

  const clearAllSessions = () => {
    sessions.value = []
    currentSessionId.value = null
    messages.value = []
  }

  return {
    // State
    sessions,
    currentSessionId,
    messages,
    isLoading,
    
    // Getters
    currentSession,
    sortedSessions,
    
    // Actions
    createNewSession,
    setCurrentSession,
    sendMessage,
    deleteSession,
    clearAllSessions
  }
})
