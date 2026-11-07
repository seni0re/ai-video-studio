# Baseline: o que o Vital Video Studio aprende do Reels Editing Engine

O Reels Editing Engine (REE, Startup Mom / Homewell LLC, v2.5.2) é a referência de produto deste fork. Ele é proprietário: a licença permite uso pessoal e proíbe redistribuir ou derivar produto do código. Por isso este documento descreve **comportamento, contratos e decisões de design** observados nele, escritos por nós, e cada item é reimplementado do zero em cima do studio do Matt Paige (MIT). Nenhum arquivo, skill ou prompt do REE entra neste repositório. O mapa completo da arquitetura dele está no vault (`maquina-de-edicao/anexo-b-arquitetura-ree.md`).

Método: **spec primeiro.** Cada módulo abaixo tem o contrato (entradas, saídas, regra), o veredito (copiar a ideia, melhorar, descartar) e onde ele pousa no studio. Implementação sem spec aqui não entra.

## 1. Contrato de pasta do projeto

REE: `projects/<job>/{raw, transcript/{words,cuts}, outputs/<job>.mp4 + <job>.transcript.json, hf-captions, hf-graphics, beat-sheet, review, subject-zones.json, graphics-plan.json, caption-plan.json}`.
Studio do Matt: `projects/<slug>/{raw (imutável), broll, audio, graphics/assets, work, exports, edit-plan.json, STORYBOARD.md, selects.csv, sound-cues.csv, asset-ledger.csv, review-feedback.json}`.

**Decisão:** manter a pasta do Matt (o site dele lê essa estrutura) e acrescentar o que falta do REE dentro de `work/`:

| Arquivo | Origem da ideia | Função |
|---|---|---|
| `work/transcripts/<stem>.words.json` | REE `transcript/words.json` | uma escuta por projeto, timing por palavra |
| `work/cut/cuts.json` | REE `transcript/cuts.json` | segmentos escolhidos `{source, in, out, text, take, reason}` |
| `exports/assembly-vNN.transcript.json` | REE `outputs/<job>.transcript.json` | transcript **remapeado para o relógio do corte** por aritmética, sem segunda escuta. Única verdade para legendas, gráficos e QA |
| `work/subject-zones.json` | REE | caixa cabeça-queixo por trecho + zonas abertas (YuNet) |
| `work/plan.json` | REE `graphics-plan.json` + `caption-plan.json` | o plano criativo por linha (ver §5) |
| `work/beat-sheet/` | REE | stills numerados + HTML |
| `references/<slug>/beats.json` | nosso | beat sheet medido de um Reel de referência (ver §9) |

## 2. Transcrição (status: feito)

Contrato: uma escuta por projeto, modelo grande, alinhamento por palavra obrigatório, idioma detectado e gravado. Nunca cair silenciosamente para um modelo menor.
REE: WhisperX large-v3 + wav2vec2, com um marcador `.whisperx-crashed` que degrada para faster-whisper medium na CPU sem avisar (atrito observado).
**Nosso:** `scripts/transcribe_whisperx.py` (GPU, PT, alinhado). Sem fallback: se falhar, para e diz por quê. Palavras sem timing herdam o ponto médio dos vizinhos e ficam marcadas com `probability: null`.

## 3. Corte guiado pelo transcript (status: próximo)

Contrato REE que vale copiar:
- O **texto decide o corte, nunca o volume**. Detecção de silêncio é só sugestão.
- Linha dita duas vezes: **a última take vence**, salvo nota explícita.
- Vícios de fala removidos por lista por idioma. REE não tem português; a nossa `FILLER_PT` começa com: né, tipo, então, aí, assim, tá, é..., hum, ok.
- Cues faladas no footage ("isso aqui é um card", "corta") viram instruções, nunca vão para a tela.
- Saída: `cuts.json` + script falado montado (o Matt já tem `assembled-script.txt`).

Melhoria nossa: as retakes aparecem como **opções no storyboard do studio** (a take escolhida e as alternativas), não só como resultado. O Sergio troca de take no editor.

Onde pousa: `scripts/transcript_cut.py` → escreve `work/cut/cuts.json` e preenche `edit-plan.json.cuts` no formato que `studio.py assemble` já lê (`source, source_in, source_out, text, reason`).

## 4. Stitch e masterização (status: próximo)

Contrato REE: corte ajustado ao som real (entrada −42 ms / saída +60 ms em torno da voz medida por RMS), pausas acima de 0,7 s fechadas, tudo num filtergraph ffmpeg só, master a **−16 LUFS integrado, true peak ≤ −1,5 dBTP**, ganho estático único (nunca compressão agressiva), segunda ASR independente para conferir palavras cortadas.
Matt: `studio.py assemble` concatena cortes no grid de frames, sem snap-to-sound nem master.

**Nosso:** estender o `assemble` com (a) snap-to-sound por RMS, (b) close-pauses, (c) `loudnorm` de dois passos no fim, (d) transcript remapeado. O "trim-restarts" por MFCC/DTW do REE fica para depois: o corte por transcript resolve as retakes em 90% dos casos.

## 5. Plano criativo e gates mínimos

Contrato REE: só duas perguntas que a máquina não deriva (registro: ensino ou confissão; rota de saída). O resto aplica o default forte, diz numa linha, e a criadora subtrai. Cada linha do script recebe: tipo de gráfico (card, lista, cutaway, takeover, nada), lugar (zona medida, não número digitado), ideia.
Matt: `STORYBOARD.md` por frame, com os mesmos campos em prosa, aprovado no site.

**Nosso:** `work/plan.json` gerado a partir de `cuts.json` + `references/<slug>/beats.json` quando houver referência. Com referência, o plano é a **réplica cena a cena** (decisão do Sergio: sem restrição); sem referência, segue os defaults do registro. O storyboard do Matt é a visualização desse JSON, e o feedback por timestamp do site volta como edição do JSON.

Eixo de registro nosso: **talking-head × No-Voice × carrossel**, não teaching × confessional.

## 6. Geometria medida (status: a fazer)

Contrato REE: zonas seguras por plataforma (Reels: y 269→1536 de 1920; rail em x < 900), cabeça-queixo medida por YuNet em cada trecho, corpo de texto ≥ 32 px, headline ≥ 90 px; o guard avisa, nunca bloqueia. Preferências guardam *qual zona* ("legenda acima da cabeça"), não o pixel.
Matt: `studio.config.json.safe_area` com margens fixas.

**Nosso:** `scripts/subject_zones.py` (OpenCV + YuNet onnx, Apache) → `work/subject-zones.json`; `safe_area` do config vira default, as zonas medidas vencem.

## 7. Gráficos, captions e motion (o motivo deste fork)

Contrato REE: composição HTML+GSAP por camada, renderizada com alpha (ProRes 4444) e composta sobre o vídeo com ffmpeg; style pack = JSON com fonte, tamanho, tracking, altura de linha, y e caixa por papel (headline, takeover, caption, thought bubble, accent); três modos de legenda (uma palavra, karaokê, takeover em pilha); doutrina drop/rail/embed (a legenda é overlay, nunca reserva faixa). Render gateado (`hyperframes check`) e cache por hash: "uma mudança custa uma camada".

O que ele entrega hoje ficou abaixo do esperado em motion. A diferença nossa:
- Cada cena do beat sheet é **autorada como composição própria** com as skills oficiais da HyperFrames (`hyperframes`, `media-use`, `reverse-any-video`, Apache, em `.claude/skills/`), não escolhida de um catálogo fechado de looks.
- Style pack = `studio.config.json.design` + `captions` (já existe no Matt) estendido com os papéis do REE.
- Render: `scripts/hf.py` (pinado, sem telemetria) + composite ffmpeg com cache por hash de `index.html`.
- Edição ao vivo: "Open in HyperFrames" do studio abre a composição no navegador; o site versiona. O chat dentro do editor (REE v2.5.2: `POST /chat` → tarefa da sessão) pode ser reimplementado no `serve.py` do Matt depois, como rota local que grava `review-feedback.json`.

## 8. Beat sheet antes do render (status: a fazer)

Contrato REE: still de cada beat no instante em que o elemento "pousou" (~0,6 s após a entrada), legenda estampada (beat, tempo, tipo, palavras, movimento), HTML 3 por linha, aprovação por número, `sandbox beat N` renderiza um só.
Matt: `prepare` gera contact sheets do raw; o storyboard é texto.

**Nosso:** `scripts/beat_sheet.py` renderiza um frame por beat via `hf.py` (frame único), monta `work/beat-sheet/index.html` e registra como artefato do projeto para o site mostrar e receber notas por cena.

## 9. Reel de referência (status: beats.json manual feito para o Harvey)

REE: fingerprint numérico (cadência de cortes, hook-burst, BPM) + leitura visual, com regra "formato sim, conceito nunca".
**Nosso:** sem essa regra. `scripts/reference_beats.py`: detecção de cena (ffmpeg, threshold 0,2) + contact sheet 1 fps + transcrição do áudio da referência → esqueleto de `references/<slug>/beats.json`, que o modelo completa cena a cena (visual, layout, movimento) lendo os quadros, como feito à mão com o Harvey em 06/11. O `beats.json` alimenta o §5 diretamente.

## 10. Som (status: a fazer)

Contrato REE: SFX CC0 em rotação (nunca o mesmo clique duas vezes), entrada tem som e saída é muda, música 15 dB abaixo da voz com ducking medido, nada automático sem a criadora pedir.
Matt: `docs/SOUND-DESIGN.md` com a mesma filosofia (sparse, físico, sem "squishy"); `media-use` traz SFX e ducking prontos.
**Nosso:** `sound-cues.csv` do Matt preenchido a partir do `plan.json`; `media-use/scripts/audio-duck.mjs` para o ducking.

## 11. Aprendizado (status: a fazer)

Contrato REE: no fim de cada Reel, as notas viram uma lista de regras para marcar; cada regra grava duas metades, prosa para o humano e JSON clampado que o builder lê, com escopo por registro e formato.
Matt: `writing-voice.json` para texto e reference notes; nada para edição.
**Nosso:** `style-library/editing-memory.json` com o mesmo padrão de duas metades, lido pelo §5.

## 12. O que fica de fora de propósito

- Rota CapCut (VectCut, drafts): v1.1, como exportação. Saída padrão é MP4.
- Multi-OS, setup assistido, report-a-problem, update assinado: uma máquina só (Targaryen, Windows, RTX A5000).
- Editor visual próprio de 7,5 mil linhas: o site do Matt + HyperFrames editor cobrem.
- Registro teaching/confessional e voz "big sister".
- Inglês como default: tudo em PT-BR, com `FILLER_PT` e correções do transcritor (ex.: "Cloud Code" → "Claude Code", "Claudio" → "Claude").

## Ordem de implementação

1. §3 corte por transcript (Harvey: escolher entre as 3 takes do "transformar" e as 2 do "leads")
2. §4 stitch + master + transcript remapeado
3. §9 `beats.json` → §5 `plan.json` (Harvey já tem o beats.json)
4. §7 primeira cena em HyperFrames (caixote + personagem); comparar com a versão do Fabiano
5. §8 beat sheet das 15 cenas, aprovação no site
6. §6 geometria, §10 som, §11 aprendizado
