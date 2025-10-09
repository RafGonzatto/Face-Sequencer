<template>
  <div class="not-found">
    <h1>404 - Page Not Found</h1>
    <p>Sorry, the page you are looking for does not exist.</p>
    <router-link to="/">Go back to Home</router-link>
  </div>
</template>

<script lang="ts">
export default {
  name: 'NotFoundPage',
};
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  text-align: center;
}

.not-found h1 {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.not-found p {
  margin-bottom: 1rem;
}

.not-found a {
  color: #007bff;
  text-decoration: none;
}

.not-found a:hover {
  text-decoration: underline;
}
</style>