<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <nav class="bg-gray-800 text-white p-4">
    <ul class="flex justify-between">
      <div class="flex space-x-4">
        <li>
          <RouterLink to="/" class="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium">Viewer</RouterLink>
        </li>
        <li>
          <RouterLink to="/upload" class="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium">Upload</RouterLink>
        </li>
      </div>
    </ul>
  </nav>
  <RouterView />
</template>

<script>
export default {
  data() {

  },
  computed: {
  },
  methods: {
  },
};
</script>
