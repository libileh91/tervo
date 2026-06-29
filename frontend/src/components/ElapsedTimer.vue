<template>
  <span class="elapsed-timer">{{ display }}</span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  startedAt: string
}>()

const now = ref(Date.now())
let interval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  interval = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})

const display = computed(() => {
  const start = new Date(props.startedAt).getTime()
  const diff = Math.floor((now.value - start) / 1000)

  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60

  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})
</script>

<style scoped>
.elapsed-timer {
  font-variant-numeric: tabular-nums;
  font-size: 1.5rem;
  font-weight: 700;
  color: #2563eb;
}
</style>
