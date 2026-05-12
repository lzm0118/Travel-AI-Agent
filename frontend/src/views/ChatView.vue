<template>
  <div class="chat-page">
    <!-- 头部导航 -->
    <header class="chat-header">
      <div class="header-left">
        <el-button 
          text 
          class="back-btn"
          @click="goHome"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <span class="title">智能旅游助手</span>
      </div>
      <div class="header-right">
        <el-button 
          text 
          class="new-chat-btn"
          @click="newChat"
        >
          <el-icon><Plus /></el-icon>
          <span>新对话</span>
        </el-button>
      </div>
    </header>
    
    <!-- 主内容区 -->
    <main class="chat-main">
      <ChatComponent 
        :session-id="sessionId"
        @update:sessionId="updateSessionId"
      />
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ChatComponent from '../components/ChatComponent.vue'

export default {
  name: 'ChatView',
  components: {
    ChatComponent
  },
  props: {
    sessionId: {
      type: String,
      default: null
    }
  },
  setup(props) {
    const router = useRouter()
    const route = useRoute()
    
    const currentSessionId = ref(props.sessionId || route.params.sessionId)
    
    const goHome = () => {
      router.push('/')
    }
    
    const newChat = () => {
      currentSessionId.value = null
      router.push('/chat')
    }
    
    const updateSessionId = (newId) => {
      currentSessionId.value = newId
      if (newId && route.params.sessionId !== newId) {
        router.replace(`/chat/${newId}`)
      }
    }
    
    onMounted(() => {
      if (route.params.sessionId) {
        currentSessionId.value = route.params.sessionId
      }
    })
    
    return {
      sessionId: currentSessionId,
      goHome,
      newChat,
      updateSessionId
    }
  }
}
</script>

<style scoped>
.chat-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-header {
  height: 60px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  font-size: 20px;
  color: #666;
}

.back-btn:hover {
  color: #667eea;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #667eea;
}

.new-chat-btn:hover {
  color: #764ba2;
}

.chat-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 768px) {
  .chat-header {
    padding: 0 12px;
  }
  
  .title {
    font-size: 16px;
  }
}
</style>
