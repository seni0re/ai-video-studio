# Shared studio instructions

Read and follow @AGENTS.md. Read SETUP.md before installing and PROJECT_CONTEXT.md before creative work. Keep production decisions in the project files so another chat or assistant can resume. Do not assume the creator's private chat or external skills exist here.

For application maintenance/releases read docs/RELEASE.md; for upgrading an existing installation read docs/UPDATING.md. Preserve owner data and local customizations. Publishing requires user authorization.

# Vital Video Studio (camada do Sergio sobre o starter do Matt)

Este fork é a máquina de edição do Sergio Vital (@sergiovitalhq, Vital HQ, Austin). Responda em **português do Brasil**, direto e técnico, sem "big sister" nem corporate speak. O AGENTS.md continua mandando no fluxo (spoken cut → storyboard → review → edit → refine); esta seção manda em quem é o dono, no ambiente e nas regras dele. O vault dele (`C:\Users\vital\vaults\personal`) e o agente de lá (Zeus) guardam o contexto do projeto em `01-projects/social-media-manager/maquina-de-edicao/`.

## Ambiente (Targaryen, Windows 11, RTX A5000, Git Bash)

- `python`, não `python3`. Helpers de mídia com `.venv/Scripts/python.exe` (Pillow). HyperFrames 0.9.16 + GSAP pinados em `node_modules` (via `scripts/hf.py`).
- Transcrição: **não existe MLX aqui.** Use `scripts/transcribe_whisperx.py` com o venv `~/.cache/reels-editing-engine/whisperx-venv/Scripts/python.exe` (WhisperX large-v3 na GPU, PT, alinhado por palavra). Saída em `projects/<slug>/work/transcripts/`.
- Variáveis já setadas no sistema: `UV_SYSTEM_CERTS=1`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`. Se algo falhar em TLS, é o padrão desta máquina (truststore / certificado do Windows), não a rede.
- Testes de symlink do studio falham no Windows sem modo desenvolvedor; ignorar esses.

## Regras do Sergio (valem por cima do AGENTS.md onde conflitarem)

1. **Referências sem restrição.** Um Reel de referência em `references/<slug>/` (com `beats.json`) pode ser reconstruído por completo: estrutura, timing, layout, animações, cards, ilustrações, personagem, roteiro. Não diluir, não "adaptar com originalidade" sem ele pedir. O talking-head é sempre o footage dele em `raw/`. O que trocar (língua, vertical do exemplo, paleta, personagem) é escolha dele, por Reel, ao vivo no editor.
2. Nunca apagar arquivo sem perguntar; mover para `_lixeira/` quando ele mandar limpar.
3. Nada sai da máquina sem ele pedir: sem publicar, sem cloud render, sem upload. Push só para `seni0re/ai-video-studio` (branch `vital`) e só de código, nunca de `projects/` ou `references/` (já ignorados).
4. Skills ficam em `.claude/skills/` deste repo (as da HeyGen são Apache 2.0, licença ao lado). Nunca copiar para `~/.claude/skills`.
5. Nada da Dell em tela, legenda ou roteiro.
6. Texto na tela na língua da fala (PT-BR). Sem travessão. Voz, palavras banidas e correções do transcritor: ver `brand-kit.md` do REE (`C:\Users\vital\projects\reels-editing-engine\brand-kit.md`) até migrarmos para `studio.config.json`.

## Motion (o motivo de existir deste fork)

Cada cena do beat sheet vira uma composição HyperFrames autorada com as skills `hyperframes` (ler primeiro), `media-use` e `reverse-any-video`. Barra de qualidade: o Reel `projects/harvey` reconstruído a partir de `references/harvey-jackroberts/beats.json` tem que ganhar em motion da versão PT em `references/harvey-fabiano/`. Edição ao vivo pelo "Open in HyperFrames" do studio; CapCut e DaVinci são exportações posteriores.
