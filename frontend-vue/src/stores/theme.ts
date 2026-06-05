import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(localStorage.getItem('dlqi-theme') !== 'light')

  function toggle() {
    isDark.value = !isDark.value
  }

  watch(isDark, (dark) => {
    localStorage.setItem('dlqi-theme', dark ? 'dark' : 'light')
    document.documentElement.classList.toggle('light-mode', !dark)
  }, { immediate: true })

  return { isDark, toggle }
})
