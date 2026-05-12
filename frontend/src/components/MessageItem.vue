<template>
  <div 
    class="message-item"
    :class="{ 
      'user-message': isUser,
      'assistant-message': isAssistant,
      'error-message': isError
    }"
  >
    <div class="message-avatar">
      <div v-if="isUser" class="avatar user-avatar">
        <el-icon><User /></el-icon>
      </div>
      <div v-else class="avatar assistant-avatar">
        <span v-if="isError">⚠️</span>
        <span v-else>✈️</span>
      </div>
    </div>
    
    <div class="message-content">
      <div class="message-header">
        <span class="role-name">
          {{ isUser ? '您' : (isError ? '系统' : '智能助手') }}
        </span>
        <span class="message-time">{{ formatTime(message.timestamp) }}</span>
      </div>
      
      <div class="message-body">
        <!-- 思考过程显示 -->
        <div v-if="isThinking" class="thinking-process">
          <div class="thinking-header" @click="toggleThinking">
            <el-icon class="thinking-icon"><Loading /></el-icon>
            <span>深度思考中</span>
            <el-icon class="expand-icon" :class="{ expanded: showThinking }"><ArrowDown /></el-icon>
          </div>
          <div v-show="showThinking" class="thinking-steps">
            <div 
              v-for="(step, idx) in message.thinking_steps" 
              :key="idx"
              class="thinking-step"
              :class="{ 
                'step-active': idx === message.current_step,
                'step-completed': idx < (message.current_step || 0) || message.thinking_complete
              }"
            >
              <span class="step-number">{{ idx + 1 }}</span>
              <span class="step-text">{{ step }}</span>
            </div>
          </div>
        </div>
        
        <!-- 内容显示 -->
        <div v-if="isAssistant && message.isStreaming && !isThinking" class="streaming-content">
          {{ message.content }}
          <span class="cursor">▊</span>
        </div>
        <div 
          v-else-if="!isThinking || message.content_started || message.thinking_complete"
          class="message-text"
          v-html="renderedContent"
        />
      </div>
      
      <!-- 工具调用显示 -->
      <div v-if="hasToolsUsed" class="tools-used">
        <div class="tools-label">
          <el-icon><Tools /></el-icon>
          <span>使用了以下工具：</span>
        </div>
        <div class="tools-tags">
          <el-tag 
            v-for="tool in message.tools_used" 
            :key="tool"
            size="small"
            effect="plain"
            type="info"
          >
            {{ formatToolName(tool) }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import highlight from 'highlight.js'
import 'highlight.js/styles/github.css'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: (code, lang) => {
    if (lang && highlight.getLanguage(lang)) {
      return highlight.highlight(code, { language: lang }).value
    }
    return highlight.highlightAuto(code).value
  }
})

export default {
  name: 'MessageItem',
  props: {
    message: {
      type: Object,
      required: true
    },
    isLast: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const isUser = computed(() => props.message.role === 'user')
    const isAssistant = computed(() => props.message.role === 'assistant')
    const isError = computed(() => props.message.isError || false)
    
    // 是否显示思考过程
    const isThinking = computed(() => {
      return props.message.type === 'thinking' || 
             (props.message.isStreaming && !props.message.content_started && !props.message.thinking_complete)
    })
    
    // 控制思考步骤展开/收起
    const showThinking = ref(true)
    const toggleThinking = () => {
      showThinking.value = !showThinking.value
    }
    
    const hasToolsUsed = computed(() => {
      return props.message.tools_used && props.message.tools_used.length > 0
    })
    
    // 渲染 Markdown 内容
    const renderedContent = computed(() => {
      const content = props.message.content || ''
      
      if (isUser.value) {
        // 用户消息直接显示，不解析 markdown
        return escapeHtml(content).replace(/\n/g, '<br>')
      }
      
      // 助手消息解析 markdown
      try {
        return marked(content)
      } catch (e) {
        return escapeHtml(content).replace(/\n/g, '<br>')
      }
    })
    
    // 转义 HTML
    const escapeHtml = (text) => {
      const div = document.createElement('div')
      div.textContent = text
      return div.innerHTML
    }
    
    // 格式化时间
    const formatTime = (timestamp) => {
      if (!timestamp) return ''
      
      const date = new Date(timestamp)
      const now = new Date()
      const isToday = date.toDateString() === now.toDateString()
      
      const hours = date.getHours().toString().padStart(2, '0')
      const minutes = date.getMinutes().toString().padStart(2, '0')
      
      if (isToday) {
        return `${hours}:${minutes}`
      }
      
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const day = date.getDate().toString().padStart(2, '0')
      return `${month}-${day} ${hours}:${minutes}`
    }
    
    // 格式化工具名称
    const formatToolName = (toolName) => {
      const toolNames = {
        'amap_poi_search': 'POI 搜索',
        'amap_weather': '天气查询',
        'amap_geocode': '地理编码',
        'web_search': '联网搜索',
        'calculator': '计算器',
        'datetime': '日期时间'
      }
      return toolNames[toolName] || toolName
    }
    
    return {
      isUser,
      isAssistant,
      isError,
      isThinking,
      showThinking,
      toggleThinking,
      hasToolsUsed,
      renderedContent,
      formatTime,
      formatToolName
    }
  }
}
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  transition: background 0.3s ease;
}

.message-item:hover {
  background: rgba(0, 0, 0, 0.02);
}

.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.user-avatar {
  background: #667eea;
  color: white;
}

.assistant-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 60px);
}

.user-message .message-content {
  text-align: right;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 13px;
}

.user-message .message-header {
  justify-content: flex-end;
}

.role-name {
  font-weight: 600;
  color: #333;
}

.message-time {
  color: #999;
  font-size: 12px;
}

.message-body {
  display: inline-block;
}

.message-text {
  background: white;
  padding: 12px 16px;
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  text-align: left;
  line-height: 1.6;
  color: #333;
  font-size: 15px;
}

.user-message .message-text {
  background: #667eea;
  color: white;
}

.error-message .message-text {
  background: #fff5f5;
  border: 1px solid #feb2b2;
  color: #c53030;
}

/* Markdown 样式 */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4) {
  margin: 16px 0 8px;
  font-weight: 600;
  color: #333;
}

.message-text :deep(h1) { font-size: 1.5em; }
.message-text :deep(h2) { font-size: 1.3em; }
.message-text :deep(h3) { font-size: 1.1em; }

.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-text :deep(li) {
  margin: 4px 0;
}

.message-text :deep(code) {
  background: #f4f4f4;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
  color: #333;
}

.message-text :deep(pre) {
  background: #f8f8f8;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
}

.message-text :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #e0e0e0;
  padding: 8px 12px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.message-text :deep(blockquote) {
  border-left: 4px solid #667eea;
  margin: 12px 0;
  padding: 8px 16px;
  background: #f8f9ff;
  color: #555;
}

.streaming-content {
  background: white;
  padding: 12px 16px;
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  text-align: left;
  line-height: 1.6;
  color: #333;
  font-size: 15px;
  white-space: pre-wrap;
}

.cursor {
  animation: blink 1s infinite;
  color: #667eea;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 思考过程样式 */
.thinking-process {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
  border: 1px solid #e0e6ff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 600;
  color: #667eea;
  user-select: none;
}

.thinking-icon {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.expand-icon {
  margin-left: auto;
  transition: transform 0.3s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.thinking-steps {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thinking-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  border-left: 3px solid #ddd;
  transition: all 0.3s;
  font-size: 13px;
  color: #666;
}

.thinking-step.step-active {
  border-left-color: #667eea;
  background: #f8f9ff;
  color: #333;
  font-weight: 500;
}

.thinking-step.step-completed {
  border-left-color: #52c41a;
  color: #52c41a;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #e0e6ff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  flex-shrink: 0;
}

.thinking-step.step-completed .step-number {
  background: #d4edda;
  color: #52c41a;
}

.step-text {
  flex: 1;
  line-height: 1.4;
}

.tools-used {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f8f9ff;
  border-radius: 8px;
  border: 1px solid #e0e6ff;
}

.tools-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

.tools-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 768px) {
  .message-item {
    gap: 8px;
    padding: 12px;
  }
  
  .avatar {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }
  
  .message-content {
    max-width: calc(100% - 48px);
  }
  
  .message-text {
    padding: 10px 14px;
    font-size: 14px;
  }
}
</style>
