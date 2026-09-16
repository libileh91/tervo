/**
 * Tervo — Router.
 *
 * Route definitions + auth guard.
 */

import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/pages/LoginPage.vue"),
    meta: { guest: true, noTransition: true },
  },
  {
    path: "/",
    name: "Dashboard",
    component: () => import("@/pages/DashboardPage.vue"),
    meta: { requiresAuth: true, title: "Accueil" },
  },
  {
    path: "/jobs",
    name: "Jobs",
    component: () => import("@/pages/JobsPage.vue"),
    meta: { requiresAuth: true, title: "Interventions" },
  },
  {
    path: "/jobs/:id",
    name: "JobDetail",
    component: () => import("@/pages/JobDetailPage.vue"),
    meta: { requiresAuth: true, title: "Intervention" },
  },
  {
    path: "/jobs/:id/inspection",
    name: "Inspection",
    component: () => import("@/pages/InspectionPage.vue"),
    meta: { requiresAuth: true, title: "Inspection" },
  },
  {
    path: "/clients",
    name: "Clients",
    component: () => import("@/pages/ClientsPage.vue"),
    meta: { requiresAuth: true, title: "Clients" },
  },
  {
    path: "/clients/:id",
    name: "ClientDetail",
    component: () => import("@/pages/ClientDetailPage.vue"),
    meta: { requiresAuth: true, title: "Client" },
  },
  {
    path: "/profile",
    name: "Profile",
    component: () => import("@/pages/ProfilePage.vue"),
    meta: { requiresAuth: true, title: "Profil" },
  },
  {
    path: "/review/:token",
    name: "Review",
    component: () => import("@/pages/ReviewPage.vue"),
    meta: { hideNav: true, title: "Votre avis" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// ── Auth guard ────────────────────────────────────────────
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();

  if (to.meta.requiresAuth && !auth.isAuthenticated()) {
    next({ name: "Login" });
  } else if (to.meta.guest && auth.isAuthenticated()) {
    next({ name: "Dashboard" });
  } else {
    next();
  }
});

export default router;
