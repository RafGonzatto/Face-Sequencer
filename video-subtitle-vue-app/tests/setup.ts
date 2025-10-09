/**
 * Setup global para testes com Vitest
 * Configurações iniciais para testar componentes Vue
 */

import { config } from '@vue/test-utils';

// Configurar stubs globais para componentes customizados se necessário
config.global.stubs = {
  // Adicione aqui componentes que precisam ser mockados globalmente
};

// Suprimir avisos específicos do Vue em testes
config.global.config.warnHandler = () => {};

// Mock do window.matchMedia (usado por componentes responsivos)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock do HTMLCanvasElement.getContext (usado pelo OverlayCanvas)
HTMLCanvasElement.prototype.getContext = function (contextId: any) {
  return {
    fillStyle: '',
    strokeStyle: '',
    font: '',
    textAlign: '',
    textBaseline: '',
    fillRect: () => {},
    strokeRect: () => {},
    clearRect: () => {},
    fillText: () => {},
    strokeText: () => {},
    measureText: () => ({ width: 0 }),
    save: () => {},
    restore: () => {},
    beginPath: () => {},
    closePath: () => {},
    moveTo: () => {},
    lineTo: () => {},
    stroke: () => {},
    fill: () => {},
    drawImage: () => {},
  } as any;
};

// Mock do ResizeObserver (usado pelo useResizeObserver)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;
