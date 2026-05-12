/**
 * API 工具函数
 * 封装后端接口调用
 */
import axios from 'axios'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 120000,  // 2分钟超时，工具调用可能需要较长时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 生成会话ID
export const createSessionId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// 聊天相关 API
export const chatAPI = {
  // 发送消息
  sendMessage: async (data) => {
    return apiClient.post('/api/chat', {
      message: data.message,
      session_id: data.session_id,
      stream: false,
      context: data.context || {}
    })
  },

  // 流式发送消息
  sendMessageStream: async (data, onMessage) => {
    console.log('[Stream] Starting stream request...')
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: data.message,
        session_id: data.session_id,
        stream: true
      })
    })
    
    console.log('[Stream] Response received, status:', response.status)

    if (!response.body) {
      throw new Error('Response body is null')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('[Stream] Stream completed')
        break
      }

      const chunk = decoder.decode(value, { stream: true })
      
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            onMessage(data)
          } catch (e) {
            console.error('Parse SSE data error:', e)
          }
        }
      }
    }
  },

  // 获取会话历史
  getHistory: async (sessionId, limit = 50) => {
    return apiClient.get(`/api/sessions/${sessionId}/history`, {
      params: { limit }
    })
  },

  // 清空会话
  clearSession: async (sessionId) => {
    return apiClient.delete(`/api/sessions/${sessionId}`)
  }
}

// 工具相关 API
export const toolsAPI = {
  // 获取工具列表
  listTools: async () => {
    return apiClient.get('/api/tools')
  },

  // 执行工具
  executeTool: async (toolName, parameters) => {
    return apiClient.post('/api/tools/execute', {
      tool_name: toolName,
      parameters
    })
  },

  // POI 搜索
  searchPOI: async (params) => {
    return apiClient.post('/api/tools/amap/poi-search', params)
  },

  // 天气查询
  getWeather: async (city, extensions = 'all') => {
    return apiClient.get('/api/tools/amap/weather', {
      params: { city, extensions }
    })
  },

  // 联网搜索
  webSearch: async (query, numResults = 10) => {
    return apiClient.post('/api/tools/web-search', {
      query,
      num_results: numResults
    })
  }
}

// 用户相关 API
export const userAPI = {
  // 获取用户画像
  getProfile: async (userId) => {
    return apiClient.get(`/api/users/${userId}/profile`)
  },

  // 更新用户画像
  updateProfile: async (userId, updates) => {
    return apiClient.post(`/api/users/${userId}/profile`, updates)
  }
}

// 健康检查
export const healthAPI = {
  check: async () => {
    return apiClient.get('/api/health')
  }
}

// WebSocket 连接
export class ChatWebSocket {
  constructor(sessionId, onMessage, onConnect, onDisconnect) {
    this.sessionId = sessionId
    this.onMessage = onMessage
    this.onConnect = onConnect
    this.onDisconnect = onDisconnect
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 3
  }

  connect() {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat/${this.sessionId}`
    
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      if (this.onConnect) this.onConnect()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (this.onMessage) this.onMessage(data)
      } catch (e) {
        console.error('Parse WebSocket message error:', e)
      }
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      if (this.onDisconnect) this.onDisconnect()
      
      // 尝试重连
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        setTimeout(() => this.connect(), 3000)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  close() {
    if (this.ws) {
      this.ws.close()
    }
  }
}

export default apiClient
