<template>
  <div class="chat-component">
    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesContainer">
      <!-- 欢迎消息 -->
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="welcome-icon">✈️</div>
        <h2>有什么可以帮您的？</h2>
        <p>我可以帮您规划行程、搜索景点、查询天气、获取最新旅游资讯</p>
        
        <!-- 快捷问题 -->
        <div class="quick-questions">
          <div 
            v-for="question in quickQuestions" 
            :key="question"
            class="quick-question"
            @click="sendQuickMessage(question)"
          >
            {{ question }}
          </div>
        </div>
      </div>
      
      <!-- 消息列表 -->
      <div v-else class="messages-list">
        <MessageItem 
          v-for="(message, index) in messages" 
          :key="index"
          :message="message"
          :is-last="index === messages.length - 1"
        />
        
        <!-- 加载指示器 -->
        <div v-if="isLoading" class="loading-indicator">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-wrapper">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入您的问题，例如：我想去杭州玩3天，帮我规划一下行程"
          @keydown.enter.prevent="handleEnter"
          resize="none"
        />
        <el-button
          type="primary"
          class="send-btn"
          :disabled="!inputMessage.trim() || isLoading"
          @click="sendMessage"
        >
          <el-icon v-if="!isLoading"><Promotion /></el-icon>
          <el-icon v-else><Loading /></el-icon>
        </el-button>
      </div>
      
      <div class="input-tips">
        <span>Enter 发送，Shift + Enter 换行</span>
        <span v-if="currentSessionId">会话: {{ currentSessionId.slice(0, 8) }}...</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import MessageItem from './MessageItem.vue'
import { chatAPI, createSessionId } from '../utils/api'

export default {
  name: 'ChatComponent',
  components: {
    MessageItem
  },
  props: {
    sessionId: {
      type: String,
      default: null
    }
  },
  emits: ['update:sessionId'],
  setup(props, { emit }) {
    const messages = ref([])
    const inputMessage = ref('')
    const isLoading = ref(false)
    const currentSessionId = ref(props.sessionId || createSessionId())
    const messagesContainer = ref(null)
    
    const quickQuestions = [
      '我想去杭州玩3天，帮我规划一下行程',
      '北京有什么好吃的推荐？',
      '查询上海明天的天气',
      '2024年最值得去的国内旅游目的地',
      '帮我推荐适合亲子游的海边城市'
    ]
    
    // 监听 sessionId 变化
    watch(() => props.sessionId, (newId) => {
      if (newId && newId !== currentSessionId.value) {
        currentSessionId.value = newId
        messages.value = []  // 清空消息
      }
    })
    
    // 滚动到底部
    const scrollToBottom = async () => {
      await nextTick()
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }
    
    // 发送消息
    const sendMessage = async () => {
      const message = inputMessage.value.trim()
      if (!message || isLoading.value) return
      
      // 添加用户消息
      messages.value.push({
        role: 'user',
        content: message,
        timestamp: new Date()
      })
      
      // 清空输入
      inputMessage.value = ''
      
      // 滚动到底部
      await scrollToBottom()
      
      // 显示加载
      isLoading.value = true
      
      try {
        // 创建思考过程消息
        const thinkingMessage = {
          role: 'assistant',
          content: '',
          type: 'thinking',
          thinking_steps: ['正在初始化...'],
          tools_used: [],
          isStreaming: true,
          timestamp: new Date()
        }
        messages.value.push(thinkingMessage)
        let thinkingMsgIdx = messages.value.length - 1
        
        // 使用流式 API
        console.log('[Chat] Starting stream chat...')
        await chatAPI.sendMessageStream({
          message: message,
          session_id: currentSessionId.value
        }, (chunk) => {
          // 更新会话ID
          if (chunk.session_id && chunk.session_id !== currentSessionId.value) {
            currentSessionId.value = chunk.session_id
            emit('update:sessionId', chunk.session_id)
          }
          
          // 处理不同类型的消息
          if (chunk.type === 'thinking' || chunk.type === 'thinking_complete') {
            // 更新思考过程
            if (chunk.thinking_steps) {
              messages.value[thinkingMsgIdx] = {
                ...messages.value[thinkingMsgIdx],
                thinking_steps: chunk.thinking_steps,
                current_step: chunk.current_step
              }
            }
            if (chunk.type === 'thinking_complete') {
              messages.value[thinkingMsgIdx] = {
                ...messages.value[thinkingMsgIdx],
                type: 'thinking_complete',
                thinking_complete: true
              }
            }
          } else if (chunk.type === 'content') {
            // 内容输出阶段 - 将思考消息转为普通消息或创建新消息
            if (!messages.value[thinkingMsgIdx].content_started) {
              messages.value[thinkingMsgIdx] = {
                ...messages.value[thinkingMsgIdx],
                content_started: true,
                content: chunk.chunk || '',
                type: 'content'
              }
            } else {
              // 追加内容
              messages.value[thinkingMsgIdx] = {
                ...messages.value[thinkingMsgIdx],
                content: messages.value[thinkingMsgIdx].content + (chunk.chunk || '')
              }
            }
            
            // 更新工具使用状态
            if (chunk.tools_used && chunk.tools_used.length > 0) {
              messages.value[thinkingMsgIdx] = {
                ...messages.value[thinkingMsgIdx],
                tools_used: chunk.tools_used
              }
            }
          } else if (chunk.type === 'complete' || chunk.is_finished) {
            // 完成
            messages.value[thinkingMsgIdx] = {
              ...messages.value[thinkingMsgIdx],
              isStreaming: false,
              type: 'complete'
            }
          }
          
          // 滚动到底部
          scrollToBottom()
        })
      } catch (error) {
        console.error('发送消息失败:', error)
        // 如果已经有助手消息，更新为错误；否则添加新消息
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = '抱歉，服务暂时不可用，请稍后重试。'
          lastMsg.isError = true
          lastMsg.isStreaming = false
        } else {
          messages.value.push({
            role: 'assistant',
            content: '抱歉，服务暂时不可用，请稍后重试。',
            isError: true,
            timestamp: new Date()
          })
        }
      } finally {
        isLoading.value = false
        await scrollToBottom()
      }
    }
    
    // 发送快捷问题
    const sendQuickMessage = (question) => {
      inputMessage.value = question
      sendMessage()
    }
    
    // 处理回车键
    const handleEnter = (e) => {
      if (e.shiftKey) {
        // Shift+Enter 换行，不处理
        return
      }
      sendMessage()
    }
    
    onMounted(() => {
      scrollToBottom()
    })
    
    return {
      messages,
      inputMessage,
      isLoading,
      currentSessionId,
      messagesContainer,
      quickQuestions,
      sendMessage,
      sendQuickMessage,
      handleEnter
    }
  }
}
</script>

<style scoped>
.chat-component {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.welcome-message h2 {
  font-size: 28px;
  color: #333;
  margin-bottom: 12px;
}

.welcome-message p {
  font-size: 16px;
  color: #666;
  max-width: 400px;
  line-height: 1.6;
}

.quick-questions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  max-width: 600px;
  width: 100%;
  margin-top: 32px;
}

.quick-question {
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  color: #555;
  text-align: left;
}

.quick-question:hover {
  border-color: #667eea;
  background: #f8f9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.typing-dots {
  display: flex;
  gap: 6px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.input-area {
  background: white;
  border-top: 1px solid #e0e0e0;
  padding: 20px;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  max-width: 900px;
  margin: 0 auto;
  align-items: flex-end;
}

.input-wrapper :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 15px;
  resize: none;
}

.input-wrapper :deep(.el-textarea__inner:focus) {
  border-color: #667eea;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  flex-shrink: 0;
}

.send-btn:hover {
  opacity: 0.9;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-tips {
  display: flex;
  justify-content: space-between;
  max-width: 900px;
  margin: 8px auto 0;
  font-size: 12px;
  color: #999;
}

@media (max-width: 768px) {
  .messages-container {
    padding: 12px;
  }
  
  .welcome-message h2 {
    font-size: 24px;
  }
  
  .quick-questions {
    grid-template-columns: 1fr;
  }
  
  .input-area {
    padding: 12px;
  }
}
</style>
