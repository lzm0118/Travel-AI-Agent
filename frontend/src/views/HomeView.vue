<template>
  <div class="home-page">
    <div class="hero-section">
      <div class="content">
        <div class="logo">✈️</div>
        <h1>智能旅游助手</h1>
        <p class="subtitle">基于 AI 的一站式旅游陪伴服务</p>
        <p class="description">
          智能行程规划 · 景点推荐 · 实时天气 · 联网搜索
        </p>
        
        <div class="features">
          <div class="feature-item">
            <el-icon><MapLocation /></el-icon>
            <span>智能规划</span>
          </div>
          <div class="feature-item">
            <el-icon><Search /></el-icon>
            <span>POI 搜索</span>
          </div>
          <div class="feature-item">
            <el-icon><Sunny /></el-icon>
            <span>天气查询</span>
          </div>
          <div class="feature-item">
            <el-icon><Globe /></el-icon>
            <span>实时资讯</span>
          </div>
        </div>
        
        <el-button 
          type="primary" 
          size="large" 
          class="start-btn"
          @click="startChat"
        >
          开始对话
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="tech-section">
      <h3>技术栈</h3>
      <div class="tech-tags">
        <el-tag effect="dark">LangChain 1.0</el-tag>
        <el-tag effect="dark" type="success">LangGraph</el-tag>
        <el-tag effect="dark" type="warning">MCP 协议</el-tag>
        <el-tag effect="dark" type="danger">A2A 协议</el-tag>
        <el-tag effect="dark" type="info">Vue 3</el-tag>
        <el-tag effect="dark">通义千问</el-tag>
        <el-tag effect="dark" type="success">智谱 AI</el-tag>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router'

export default {
  name: 'HomeView',
  setup() {
    const router = useRouter()
    
    const startChat = () => {
      router.push('/chat')
    }
    
    return {
      startChat
    }
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: white;
}

.hero-section {
  text-align: center;
  max-width: 600px;
}

.logo {
  font-size: 80px;
  margin-bottom: 20px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

h1 {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.subtitle {
  font-size: 24px;
  margin-bottom: 12px;
  opacity: 0.95;
}

.description {
  font-size: 16px;
  opacity: 0.8;
  margin-bottom: 32px;
}

.features {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(255,255,255,0.1);
  border-radius: 12px;
  min-width: 80px;
}

.feature-item .el-icon {
  font-size: 28px;
}

.feature-item span {
  font-size: 14px;
}

.start-btn {
  padding: 16px 48px;
  font-size: 18px;
  border-radius: 30px;
  background: white;
  color: #667eea;
  border: none;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.3);
  background: white;
  color: #764ba2;
}

.tech-section {
  margin-top: 60px;
  text-align: center;
}

.tech-section h3 {
  font-size: 18px;
  margin-bottom: 20px;
  opacity: 0.9;
}

.tech-tags {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.tech-tags .el-tag {
  padding: 8px 16px;
  font-size: 14px;
  border-radius: 20px;
}

@media (max-width: 768px) {
  h1 {
    font-size: 36px;
  }
  
  .subtitle {
    font-size: 18px;
  }
  
  .features {
    gap: 16px;
  }
  
  .feature-item {
    min-width: 70px;
    padding: 12px;
  }
}
</style>
