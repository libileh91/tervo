<template>
    <div class="app">
        <!-- Login page: full screen, no nav -->
        <template v-if="hideNav">
            <router-view />
        </template>

        <!-- Pages with nav: content + bottom nav -->
        <template v-else>
            <main class="app-content">
                <router-view v-slot="{ Component, route }">
                    <Transition :name="route.meta.noTransition ? '' : 'slide-fade'" mode="out-in">
                        <component :is="Component" :key="route.path" />
                    </Transition>
                </router-view>
            </main>
            <BottomNav />
        </template>

        <Toast />
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import BottomNav from "@/components/BottomNav.vue";
import Toast from "primevue/toast";

const route = useRoute();
const hideNav = computed(() => route.meta.hideNav === true);
</script>

<style>
/* Global reset & base */
*,
*::before,
*::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html,
body {
    height: 100%;
    font-family:
        "Inter",
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        sans-serif;
    background: #f3f4f6;
    color: #1f2937;
    -webkit-font-smoothing: antialiased;
}

#app {
    min-height: 100dvh;
}

/* ── iOS input font-size fix (prevents auto-zoom on focus) ── */
input,
textarea,
select,
.p-inputtext,
.p-password input,
.p-datepicker input,
.p-select-label,
.p-inputtextarea {
    font-size: 16px !important;
}
</style>

<style scoped>
.app {
    min-height: 100dvh;
}

.app-content {
    /* Bottom nav is 60px + extra spacing + safe area for iPhone X+ */
    padding-bottom: calc(60px + 12px + env(safe-area-inset-bottom, 0px));
}

/* ── Page transitions ──────────────────────────────────── */

.slide-fade-enter-active,
.slide-fade-leave-active {
    transition: all 0.25s ease;
}

.slide-fade-enter-from {
    transform: translateX(20px);
    opacity: 0;
}

.slide-fade-leave-to {
    transform: translateX(-20px);
    opacity: 0;
}
</style>
