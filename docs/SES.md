# SES: Saga Engine Script

SES é a linguagem da lógica do jogo: o que acontece quando o jogador examina, pega, usa, abre ou fala
com algo, e quando entra numa cena. Ela foi feita pequena de propósito, para que uma pessoa ou a IA
consigam escrever scripts certos de primeira. Tudo o que está aqui está implementado:

- o parser fica em [`backend/ses/language.py`](../backend/ses/language.py);
- quem executa é [`backend/ses/engine.py`](../backend/ses/engine.py);
- os testes estão em [`tests/test_ses.py`](../tests/test_ses.py).

Qualquer palavra fora desta lista é um erro de sintaxe, com linha e coluna.

## O modelo do jogo

Um projeto tem **cenas** (salas) e **objetos**. O motor de jogo, sem script nenhum, já faz o
básico de um adventure em texto:

| O jogador digita | Sem script, o motor... |
|---|---|
| `olhar` | descreve a cena, lista os objetos visíveis e as saídas |
| `examinar X` | mostra a descrição de X |
| `pegar X` | pega X se ele for `portable` ("pode ser pego") |
| `largar X` | larga X na cena |
| `usar X`, `usar X em Y` | "nada acontece" |
| `abrir`, `fechar`, `empurrar`, `puxar`, `falar com` | respostas padrão |
| `norte`, `n`, `ir para leste`, `subir`, `entrar`... | segue pela saída, se ela existir |
| `inventário`, `i` / `ajuda` | o que você carrega / os comandos |

Os objetos são encontrados pelo nome, pelos **outros nomes** (aliases) ou pelo id, sem diferenciar
acentos nem maiúsculas: `pegar a chave velha` encontra "Chave Enferrujada" se ela tiver o alias
"chave velha".

O script entra quando o objeto precisa fazer algo diferente.

## Handlers

Um script é uma lista de handlers:

```
on <evento> { comandos }
on use with <objeto> { comandos }      // "usar <objeto> em mim" (ou "usar mim em <objeto>")
```

- **Eventos de objeto:** `examine`, `take`, `drop`, `use`, `open`, `close`, `push`, `pull`, `talk`
- **Eventos de cena:** `enter` (toda vez que o jogador entra) e `first_enter` (só na primeira vez)

Um handler **substitui** o comportamento padrão. Por exemplo, um `on take` decide sozinho se o objeto
vai para o inventário, e só vai se o script chamar `take`.

`usar chave na porta` procura `on use with chave` na porta e, se não achar, `on use with porta` na
chave. Assim, tanto faz em qual dos dois objetos a regra foi escrita.

## Comandos

Os comandos são separados por `;` ou por quebra de linha.

| Comando | Faz |
|---|---|
| `say "texto"` | mostra um texto ao jogador |
| `take [obj]` | põe o objeto (ou este, se omitido) no inventário |
| `drop [obj]` | larga o objeto na cena atual |
| `remove [obj]` | tira o objeto do jogo |
| `show obj` / `hide [obj]` | mostra um objeto escondido (`hidden`) / esconde |
| `move obj to cena` | leva o objeto para outra cena |
| `goto cena` | leva o jogador para outra cena (depois que o script termina) |
| `link direção to cena [in cena]` | abre uma saída (na cena atual ou na indicada) |
| `unlink direção [in cena]` | fecha uma saída |
| `set flag` / `set flag = valor` | marca uma flag (`true`) ou guarda um número/texto |
| `clear flag` | apaga a flag |
| `inc flag [n]` / `dec flag [n]` | soma/subtrai n (padrão 1) |
| `end "texto"` | termina o jogo com esse texto |
| `play "descrição do som"` | toca um som; a geração de som da ficha cria o arquivo a partir da descrição |
| `stop` | para o script aqui |
| `if cond { } else if cond { } else { }` | decisão |

## Condições

| Condição | Verdadeira quando |
|---|---|
| `has(obj)` | o jogador tem o objeto |
| `here(obj)` | o objeto está visível na cena atual |
| `flag(f)` | a flag está marcada (e não é 0 nem vazia) |
| `flag(f) == 3`, `!=`, `>`, `<`, `>=`, `<=` | comparação com número, texto ou `true`/`false` |
| `in(cena)` | o jogador está na cena |
| `visited(cena)` | o jogador já esteve na cena |

Elas se combinam com `not` (ou `!`), `and`, `or` e parênteses.

## Referências

Objetos e cenas são citados pelo id ou pelo nome. Nomes com espaço vão entre aspas:
`link norte to "Dentro do Farol"`. Dentro de um objeto, `self` é ele mesmo. As direções são `norte`,
`sul`, `leste`, `oeste`, `nordeste`, `noroeste`, `sudeste`, `sudoeste`, `cima`, `baixo`, `entrar` e
`sair`, mas uma saída pode ter qualquer nome (`"porta"`). Comentários começam com `//` ou `#`.

## Exemplo completo

A porta da base do farol (projeto [`projects/O Farol`](../projects/O%20Farol/project.json)):

```
on examine {
  if flag(porta_aberta) { say "A porta está aberta. Lá dentro, uma escada sobe." }
  else { say "Uma porta de ferro, trancada, com uma fechadura grande." }
}
on open {
  if flag(porta_aberta) { say "Já está aberta." }
  else { say "Trancada. Precisa de uma chave." }
}
on use with chave {
  if flag(porta_aberta) { say "Já está aberta." }
  else { set porta_aberta; link norte to "Dentro do Farol"; say "A chave gira com um rangido." }
}
```

Uma gaivota que muda de resposta:

```
on talk {
  inc conversas_gaivota
  if flag(conversas_gaivota) >= 3 { say "A gaivota suspira e olha para o farol." }
  else { say "A gaivota inclina a cabeça e grita." }
}
```

## Erros

Os erros de sintaxe dizem onde estão e o que se esperava:

```
linha 2, coluna 3: comando desconhecido 'narrate'; comandos: say, take, drop, ...
linha 1, coluna 25: esperava ';' ou nova linha antes de 'de' — nomes com espaço vão entre aspas, ex.: "chave de ferro"
```

O editor valida o script enquanto você digita, em `POST /api/ses/validate`. As ferramentas da IA
recusam salvar um script com erro e devolvem a mensagem para que ela corrija. A validação também
**avisa** quando um objeto ou cena citado ainda não existe.

Um script que não compila não derruba o jogo: o objeto continua funcionando com a descrição e os
comportamentos padrão, e o jogo mostra um aviso no início.

## O estado do jogo

O servidor não guarda sessão. `POST /api/game/start` devolve `{state, messages, view}` e cada
`POST /api/game/command` recebe o `state` e devolve o próximo. O estado guarda:

- a cena atual e onde cada objeto está (cena, inventário ou fora do jogo);
- os objetos mostrados ou escondidos;
- as flags, as saídas abertas ou fechadas e as cenas visitadas;
- se o jogo terminou.

É esse JSON que `/api/game/save` grava. Jogar nunca altera o projeto.
