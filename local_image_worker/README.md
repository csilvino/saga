# Gerador local de imagens (FLUX.1 Kontext)

Gera cenários e sprites na **sua GPU**, sem custo e sem cota. Usa o FLUX.1 Kontext [dev], que
recebe uma imagem de referência. Com isso todas as cenas saem no mesmo estilo da primeira.

Este gerador é um processo à parte, com ambiente Python próprio, porque as dependências passam de
10 GB. O Saga o chama quando, em **Configurações → API Keys → Fonte das imagens**, está escolhido
**Local**.

## Requisitos

- GPU NVIDIA com 12 GB de VRAM (testado numa RTX 3060 12 GB, com 16 GB de RAM).
- Cerca de 17 GB livres para os modelos (cache do Hugging Face; aponte `HF_HOME` para outro disco
  se precisar).
- Cada imagem leva de 3 a 5 minutos numa RTX 3060. A primeira demora mais, porque carrega o modelo.

## Instalação

```bash
cd local_image_worker
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

## Modelos e licença

O pipeline base `black-forest-labs/FLUX.1-Kontext-dev` é **restrito** no Hugging Face, e a licença
é **FLUX.1 [dev] Non-Commercial**:

1. Aceite a licença na página do modelo.
2. Faça `huggingface-cli login`.

O transformer vem em versão comprimida (GGUF Q4) de `QuantStack/FLUX.1-Kontext-dev-GGUF`.

Para usar outros repositórios, defina estas variáveis de ambiente ou as chaves equivalentes em
`~/.saga_engine_settings.json`:

| Variável | Chave em `~/.saga_engine_settings.json` | Padrão |
|---|---|---|
| `FLUX_BASE` | `flux_base_repo` | `black-forest-labs/FLUX.1-Kontext-dev` |
| `FLUX_BASE_REVISION` | `flux_base_revision` | (última) |
| `FLUX_GGUF_REPO` | `flux_gguf_repo` | `QuantStack/FLUX.1-Kontext-dev-GGUF` |
| `FLUX_GGUF_FILE` | `flux_gguf_file` | `flux1-kontext-dev-Q4_K_S.gguf` |
| `HF_HOME` | `hf_home` | cache padrão do Hugging Face |

## Rodar

```bash
.venv\Scripts\python worker.py            # escuta em 127.0.0.1:8071
```

## Como funciona

- Uma GPU de 12 GB não comporta o T5 (~9,5 GB) e o transformer (~7 GB) juntos. Por isso o gerador
  primeiro codifica o prompt com o T5, descarrega o T5 e só então carrega o transformer.
- Os prompts já codificados ficam em cache.
- Com imagem de referência, o Kontext só cria uma cena **nova** no estilo da referência quando a
  imagem gerada tem tamanho **diferente** da referência. Com o mesmo tamanho, ele apenas edita a
  referência. Por isso a cena é gerada em 1456×720 e depois recortada e redimensionada para o
  tamanho pedido.
