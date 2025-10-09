# Testes Frontend - EditorPage

## Estrutura

```
tests/
├── setup.ts                          # Configuração global (mocks de Canvas, ResizeObserver, etc)
├── TEST_REPORT.md                    # Relatório detalhado dos resultados
└── frontend/
    └── editor_page/
        └── generate_caption.test.ts  # Testes do fluxo de geração de legendas
```

## Executar Testes

### Modo watch (desenvolvimento)

```bash
npm run test
```

### Executar uma vez

```bash
npm run test -- --run
```

### Com interface gráfica

```bash
npm run test:ui
```

## Tecnologias

- **Vitest 1.0+** - Test runner rápido e moderno
- **@vue/test-utils 2.4+** - Utilitários oficiais para testar componentes Vue
- **jsdom** - Ambiente DOM simulado para Node.js
- **@vitest/ui** - Interface gráfica para visualizar resultados

## Cobertura Atual

### EditorPage - Generate Captions Flow (6 testes)

- ✅ Renderização do componente
- ✅ Presença do textarea
- ✅ Binding do modelo (localTranscript ↔ workflow.rawText)
- ✅ Botão desabilitado sem texto
- ✅ Botão habilitado com texto e vídeo
- ✅ Chamada do workflow.doGenerate ao clicar

### useSubtitleWorkflow - rawText binding (3 testes)

- ✅ Aceitação e armazenamento via ref
- ✅ Abort quando rawText vazio
- ✅ Prosseguimento quando rawText tem conteúdo

## Mocks Configurados

### Canvas API (setup.ts)

```typescript
HTMLCanvasElement.prototype.getContext = ...
```

Necessário para componentes que usam `<canvas>` (OverlayCanvas.vue)

### ResizeObserver (setup.ts)

```typescript
global.ResizeObserver = class ResizeObserver { ... }
```

Necessário para composables que observam redimensionamento

### APIs Externas

Mockadas nos testes individuais:

- `audioService` - upload, listAudioFiles, alignBasic
- `subtitlesService` - generateSubtitles, listPresets
- `subtitleExportService` - exportSubtitles, downloadBlob
- `videoExportService` - exportVideoWithSubtitles

## Debugging

### Ver logs dos testes

Os testes usam `console.log` extensivamente. Execute com:

```bash
npm run test -- --run --reporter=verbose
```

### Logs importantes a observar

```
WORKFLOW -> LOCAL TRANSCRIPT: { length: 39 }
LOCAL TRANSCRIPT -> WORKFLOW: { length: 39, preview: '...' }
GEN UI - (1/4) iniciar geração ...
SUBS WORKFLOW - generate (1/4) início ...
```

### Troubleshooting

#### Erro: "Cannot find module '@/...'"

- Verificar `vite.config.ts` tem alias `@` configurado
- Verificar `/// <reference types="vitest" />` no topo do vite.config.ts

#### Erro: "HTMLCanvasElement.getContext not implemented"

- Verificar `tests/setup.ts` está sendo carregado
- Verificar `setupFiles` em `vite.config.ts`

#### Erro: "ResizeObserver is not defined"

- Adicionar mock no `tests/setup.ts` (já está implementado)

## Adicionar Novos Testes

### Template básico

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import SeuComponente from '@/pages/SeuComponente.vue';

describe('SeuComponente', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('deve fazer algo', () => {
    const wrapper = mount(SeuComponente);
    expect(wrapper.exists()).toBe(true);
  });
});
```

### Mockar API

```typescript
vi.mock('@/api/seuService', () => ({
  suaFuncao: vi.fn(() => Promise.resolve({ data: 'mock' })),
}));
```

## CI/CD

Para integração contínua, adicione ao pipeline:

```yaml
- name: Run tests
  run: npm run test -- --run --coverage
```

## Contato

Para dúvidas sobre os testes, consulte:

- **Relatório detalhado:** `tests/TEST_REPORT.md`
- **Documentação Vitest:** https://vitest.dev
- **Documentação @vue/test-utils:** https://test-utils.vuejs.org
