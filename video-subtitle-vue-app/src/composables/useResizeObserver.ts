import { ref, onMounted, onBeforeUnmount } from 'vue';

export function useResizeObserver(callback: ResizeObserverCallback) {
  const observer = ref<ResizeObserver | null>(null);

  onMounted(() => {
    observer.value = new ResizeObserver(callback);
  });

  const observe = (element: Element) => {
    if (observer.value) {
      observer.value.observe(element);
    }
  };

  const unobserve = (element: Element) => {
    if (observer.value) {
      observer.value.unobserve(element);
    }
  };

  onBeforeUnmount(() => {
    if (observer.value) {
      observer.value.disconnect();
      observer.value = null;
    }
  });

  return { observe, unobserve };
}