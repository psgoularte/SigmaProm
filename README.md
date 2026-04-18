# SigmaProm

Uma interface completa para análise de dashboards Grafana com dados do Prometheus, incluindo análise estatística avançada de múltiplas execuções de benchmark.

## Funcionalidades

### Dashboard em Tempo Real
- **Importação de dashboards**: Carrega JSON exportado do Grafana
- **Renderização em tempo real**: Exibe gráficos com dados brutos do Prometheus via `query_range`
- **Layout responsivo**: Grid 24-col igual ao Grafana
- **Filtro inteligente**: Mantém gráficos constantes (mesmo que zero) para benchmarks

### Análise Estatística Avançada
- **Múltiplas execuções**: Processa array de runs com timestamps
- **Normalização temporal**: Converte execuções com durações diferentes para eixo relativo (0% a 100%)
- **Interpolação inteligente**: Garante mesmo número de pontos entre execuções
- **Estatísticas robustas**: Calcula média ± desvio padrão ponto a ponto
- **Visualização avançada**: Área sombreada mostrando intervalos de confiança
- **Exportação CSV**: Botões individuais em cada gráfico para download de dados específicos

## Comportamento dos Gráficos

### Tempo Real
- Os gráficos **não aplicam médias móveis** no app ou UI
- Renderizam **dados brutos** retornados pelo Prometheus via `query_range`, ponto por ponto
- Se a query Grafana usa `avg_over_time`, `rate()`, `quantile_over_time()`, ou outras funções de janela PromQL, esses valores já são computados pelo Prometheus

### Análise Estatística
- **Normalização**: Todas as execuções são normalizadas para timeline relativa
- **Interpolação**: Usa número configurável de pontos (padrão: 100)
- **Área sombreada**: Visualiza média ± desvio padrão para análise de ruído
- **Exportação de dados**: Botões "↓ CSV" em cada gráfico para download individual dos dados
- **Grid consistente**: Mantém layout 24-col igual ao dashboard original

## Requisitos

- Python 3.9+
- Poetry
- Prometheus rodando e acessível
- Pandas e NumPy (para análise estatística)

## Instalação

```bash
poetry install
cp .env.example .env
```

Edite `.env` se o Prometheus não estiver em `http://127.0.0.1:9090`.

## Configuração

No `.env`, configure:

```env
PROMETHEUS_URL=http://127.0.0.1:9090
WEB_PORT=3030
```

## Execução

```bash
poetry run prom-web
```

Abra `http://127.0.0.1:3030` no seu navegador.

## Como Usar

### Dashboard em Tempo Real
1. **Exporte dashboard**: No Grafana: Share → JSON Model / Export JSON
2. **Cole o JSON**: Cole no campo principal da interface
3. **Configure janela**: Ajuste janela de tempo (5m, 15m, 30m, 1h, 6h, 1d)
4. **Renderize**: Clique em "Render dashboard"

### Análise Estatística
1. **Cole dashboard**: Use o mesmo JSON do dashboard acima
2. **Adicione runs**: Cole array JSON com execuções do benchmark:
   ```json
   [
     {
       "status": "success",
       "prometheus_timestamps": {
         "start_ms": 1776488154750,
         "finish_ms": 1776488291033
       },
       "readable": {
         "start": "2026-04-18T04:55:54Z",
         "finish": "2026-04-18T04:58:11Z",
         "duration_ms": 136283
       }
     }
   ]
   ```
3. **Configure pontos**: Ajuste número de pontos de interpolação (10-500)
4. **Analise**: Clique em "Analyze Runs"

## Endpoints Úteis

### Saúde e Diagnóstico
- `GET /api/health` — verifica serviço
- `GET /api/diagnostics` — verifica conectividade Prometheus

### Renderização
- `POST /api/grafana/render-dashboard` — renderiza dashboard em tempo real
- `POST /api/grafana/statistical-analysis` — análise estatística de múltiplas execuções

## Testes

```bash
poetry run pytest
```

## Dicas de Uso

### Para Benchmarks
- **Métricas constantes**: O filtro inteligente mantém gráficos importantes mesmo com valores zero
- **Janelas relativas**: Use botões 5m, 15m, 30m para análise de períodos
- **Análise de ruído**: Use análise estatística para identificar padrões entre execuções

### Para Análise Estatística
- **Número de pontos**: 50-300 pontos para interpolação (padrão: 100)
- **Execuções consistentes**: Todas as runs devem ter `status: "success"`
- **Timestamps precisos**: Use `prometheus_timestamps.start_ms` e `finish_ms`

## Notas

- A janela de tempo padrão é `5m`
- O sistema usa **grid 24-col** para layout consistente com Grafana
- **Auto-detecção** disponível para pontos ótimos de interpolação
- **Área sombreada** mostra intervalos de confiança de ±1 desvio padrão

## Desenvolvimento

### Estrutura do Projeto
```
src/prom_bench_stats/
├── api/
│   ├── dashboard.py      # Endpoints de renderização
│   ├── health.py        # Saúde do serviço
│   └── metrics.py       # Métricas da aplicação
├── static/
│   ├── index.html       # Interface principal
│   ├── js/
│   │   ├── app.js         # Controles gerais
│   │   ├── dashboard.js   # Dashboard em tempo real
│   │   └── statistical.js # Análise estatística
├── grafana_import.py      # Parser de dashboards Grafana
├── prometheus_fetch.py   # Cliente Prometheus
├── statistical_analysis.py # Análise estatística avançada
└── settings.py           # Configurações
```

### Tecnologias
- **Backend**: FastAPI, Python 3.9+
- **Frontend**: Chart.js, HTML5, CSS3
- **Processamento**: Pandas, NumPy
- **Dados**: Prometheus HTTP API
