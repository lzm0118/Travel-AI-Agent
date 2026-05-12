import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ChatView from '../views/ChatView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/chat',
    name: 'chat',
    component: ChatView
  },
  {
    path: '/chat/:sessionId',
    name: 'chat-session',
    component: ChatView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
