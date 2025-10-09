import { Module } from 'vuex';
import { VideoState, VideoPayload } from '../modules/video/videoTypes';

const videoStore: Module<VideoState, any> = {
  namespaced: true,
  state: {
    currentTime: 0,
    duration: 0,
    isPlaying: false,
    volume: 1,
    muted: false,
    playbackRate: 1,
  },
  mutations: {
    SET_CURRENT_TIME(state, time: number) {
      state.currentTime = time;
    },
    SET_DURATION(state, duration: number) {
      state.duration = duration;
    },
    SET_PLAYING(state, isPlaying: boolean) {
      state.isPlaying = isPlaying;
    },
    SET_VOLUME(state, volume: number) {
      state.volume = volume;
    },
    TOGGLE_MUTED(state) {
      state.muted = !state.muted;
    },
    SET_PLAYBACK_RATE(state, rate: number) {
      state.playbackRate = rate;
    },
  },
  actions: {
    updateCurrentTime({ commit }, time: number) {
      commit('SET_CURRENT_TIME', time);
    },
    updateDuration({ commit }, duration: number) {
      commit('SET_DURATION', duration);
    },
    togglePlay({ commit, state }) {
      commit('SET_PLAYING', !state.isPlaying);
    },
    updateVolume({ commit }, volume: number) {
      commit('SET_VOLUME', volume);
    },
    toggleMute({ commit }) {
      commit('TOGGLE_MUTED');
    },
    updatePlaybackRate({ commit }, rate: number) {
      commit('SET_PLAYBACK_RATE', rate);
    },
  },
  getters: {
    isPlaying: (state) => state.isPlaying,
    currentTime: (state) => state.currentTime,
    duration: (state) => state.duration,
    volume: (state) => state.volume,
    muted: (state) => state.muted,
    playbackRate: (state) => state.playbackRate,
  },
};

export default videoStore;