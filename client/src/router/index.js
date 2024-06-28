import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Slide View',
      component: () => import('../views/slideView.vue')
    }, 
    {
      path: '/upload', 
      name: 'Upload',
      component: () => import('../views/uploadView.vue')
    }
  ]
})

export default router
