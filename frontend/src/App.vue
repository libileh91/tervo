<template>
    <div class="app">
        <!-- Login page: full screen, no nav -->
        <template v-if="hideNav">
            <router-view />
        </template>

        <!-- Pages with nav: content + bottom nav -->
        <template v-else>
            <main class="app-content">
                <router-view />
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
    min-height: 100vh;
}
</style>

<style scoped>
.app {
    min-height: 100vh;
}

.app-content {
    padding-bottom: 72px; /* space for bottom nav */
}
</style>
