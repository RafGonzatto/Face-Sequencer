<template>
  <div class="default-layout">
    <header>
      <h1>Video Subtitle Editor</h1>
    </header>
    <main>
      <slot />
    </main>
    <footer>
      <p>&copy; 2023 Video Subtitle Editor. All rights reserved.</p>
    </footer>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'DefaultLayout',
});
</script>

<style scoped>
.default-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

header {
  background-color: #282c34;
  color: white;
  padding: 20px;
  text-align: center;
}

main {
  flex: 1;
  padding: 20px;
}

footer {
  background-color: #282c34;
  color: white;
  text-align: center;
  padding: 10px;
}
</style>
