import { createStore } from 'vuex';
import videoStore from './videoStore';

const store = createStore({
  modules: {
    video: videoStore,
  },
});

export default store;
