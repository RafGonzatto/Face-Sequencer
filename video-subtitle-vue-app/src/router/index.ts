import { createRouter, createWebHistory } from 'vue-router';
import EditorPage from '../pages/EditorPage.vue';
import NotFoundPage from '../pages/NotFoundPage.vue';

const routes = [
  {
    path: '/',
    name: 'Editor',
    component: EditorPage,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundPage,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;