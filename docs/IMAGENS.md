# Imagens: cenários no mesmo estilo

Um adventure point & click precisa que todas as cenas pareçam do **mesmo jogo**: mesmo traço, mesma
paleta, mesma luz. Gerar cada cena separada, só com texto, dá imagens bonitas que não combinam entre
si. A solução do Saga é gerar **uma primeira imagem** e usá-la como **referência de estilo** para
todas as outras.

![As 6 cenas de O Farol, geradas pelo Diretor com FLUX.1 Kontext numa RTX 3060](images/flux-kontext/o-farol-6-cenas.jpg)

*As 6 cenas do projeto de exemplo [O Farol](../projects/O%20Farol/project.json). Quem pediu as
imagens foi o Diretor, pela conversa: a Praia foi gerada só com texto, e as outras 5 usaram a Praia
como referência. Tudo rodou numa RTX 3060 12 GB, sem custo.*

## Como fazer

### 1. A primeira imagem

Ela define o estilo do jogo inteiro. Há três caminhos:

- **Gemini na web, de graça.** Gere a imagem conversando no [Gemini](https://gemini.google.com),
  que usa o Nano Banana, e ajuste até gostar. Salve o arquivo e coloque-o como fundo da primeira cena
  no editor.
- **Gerador local (FLUX), de graça.** Peça ao Diretor a primeira cena sem referência. Foi assim
  que nasceu a Praia de O Farol.
- **Chave paga da Gemini.** O Nano Banana (`gemini-2.5-flash-image` e similares) **não tem cota no
  plano gratuito** da API, só no site. Com faturamento ativado no
  [Google AI Studio](https://aistudio.google.com/apikey), o Saga gera todas as imagens pela nuvem, e
  o Nano Banana também aceita imagem de referência.

### 2. As outras cenas

Com a primeira cena pronta, peça ao Diretor no chat, por exemplo:

> Crie os cenários de todas as cenas no mesmo estilo da primeira. Use a primeira cena como referência.

O Diretor chama `generate_image_and_set_as_background` uma cena por vez, passando
`reference_scene` = a primeira. A imagem nova vai para `backgrounds/` e vira o fundo da cena.

A fonte das imagens se escolhe em **Configurações → API Keys → Fonte das imagens**:

- **Gemini (nuvem):** usa a chave da Gemini e precisa de cota de imagem.
- **Local (sua GPU):** usa o [gerador local](../local_image_worker/README.md).

## O gerador local: FLUX.1 Kontext na sua GPU

O [FLUX.1 Kontext \[dev\]](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev) é um modelo
aberto que gera uma imagem nova **a partir de uma imagem de referência**. Ele roda num processo
separado, [`local_image_worker/worker.py`](../local_image_worker/worker.py), e o backend do Saga
fala com ele por HTTP. Assim o Saga não precisa instalar torch.

### Exemplos

| Referência (só texto) | Trilha, com a referência | Topo do farol, com a referência |
|---|---|---|
| ![](images/flux-kontext/1-referencia-praia.jpg) | ![](images/flux-kontext/2-trilha-com-referencia.jpg) | ![](images/flux-kontext/3-topo-com-referencia.jpg) |

### O que aprendemos

- **Cabe numa GPU de 12 GB, mas não tudo de uma vez.** O codificador de texto T5 ocupa ~9,5 GB e o
  transformer, mesmo comprimido em GGUF Q4, ocupa ~7 GB. O gerador faz duas etapas:
  1. carrega o T5 direto na GPU, codifica o prompt e libera o T5;
  2. carrega o transformer e gera a imagem.

  O pico ficou em 8,9 GB de VRAM, numa máquina com 16 GB de RAM.
- **Tempo:** cerca de 4 minutos por imagem numa RTX 3060. Com a troca de modelos, cada cena levou
  uns 6 minutos.
- **O tamanho de saída precisa ser diferente do tamanho da referência.** Com o mesmo tamanho, o
  Kontext entende que é para **editar** a referência e devolve quase a mesma imagem:

  ![A trilha gerada no mesmo tamanho da referência saiu como uma cópia da praia](images/flux-kontext/erro-mesmo-tamanho-copiou-a-referencia.jpg)

  Por isso o gerador cria a cena em 1456×720 e depois recorta e redimensiona para o tamanho pedido.
  Isso também resolveu um farol duplicado que aparecia nas primeiras tentativas.
- **Negação não funciona bem.** Um prompt com "pavio apagado" ainda desenha uma chama. No exemplo
  acima, a trilha mostra o farol aceso, embora no jogo ele esteja apagado. Descreva o que **deve**
  aparecer, não o que deve faltar.
- **Prompts em inglês** funcionam melhor; o Diretor já os escreve assim.
- **Ainda falta:** os sprites saem sem transparência. Os fundos funcionam bem; para objetos, ainda
  é preciso recortar o fundo.

### Licença

Os pesos do FLUX.1 Kontext [dev] usam a licença **FLUX.1 [dev] Non-Commercial**. As imagens geradas
podem ser usadas, mas leia os termos antes de um uso comercial. A instalação está em
[`local_image_worker/README.md`](../local_image_worker/README.md).
