# 0003 — A planilha da pesquisadora entra no OLTP como rótulo da curadoria, lida só com a biblioteca padrão

- **Status:** proposto
- **Data:** 2026-09-26
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O ADR 0001 decidiu que os atos da pesquisadora entram no OLTP como carga inicial, com `origem = 'PLANILHA'`, e deixou para a #3 **como** eles entram. A planilha (`data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx`) é o nosso *ground truth*: é com ela que a classificação automática vai ser medida.

**O que a planilha é** (diário de 26/09, `docs/carga/relatorio-planilha.md`):

| Dimensão | Valor |
|---|---|
| Atos | **215** em 5 abas: CNAS 53, CONAMA 98, CONCIDADES 28, CONDRAF 24, CNPIR 12 (não 2.638: esse número contava linhas só formatadas) |
| Anos | 2003–2020 |
| Esquema | diferente em cada aba: o cabeçalho do CONAMA está na linha 2, o CNAS não tem referência legal, o `TEMA` é resumo em umas abas e texto transcrito em outras |
| Datas | serial do Excel (`37671` = 2003-02-19) |
| Armadilhas | o Excel leu o `DIS_LEG (ATO/ANO)` do CNPIR como data (`1/2005` virou 01/01/2005) em 11 das 12 linhas; tipologia `99` em 6 atos, fora das 5 categorias |

**O que tem que valer** (critérios de aceite da #3):

- **R1** a carga roda com um comando e é **idempotente**;
- **R2** **nenhuma linha some em silêncio**: toda exclusão é contada e justificada;
- **R3** a tipologia é **rótulo dela, não atributo do ato**;
- **R4** Docker e `make` continuam sendo os únicos pré-requisitos (README).

A carga roda uma vez, na subida do projeto, e de novo só se a planilha mudar. Desempenho não decide.

## Alternativas consideradas

Três perguntas, cada uma com suas alternativas.

### 1. Como identificar um ato da planilha (o que torna a carga idempotente)

- **1A. `ref_legal` + órgão** (a D3 do PR #9): não se sustenta. O CNAS não tem coluna de referência legal, o `DISP_LEG` do CONAMA traz só o tipo ("Resolução", "Moção"), sem número, e no CONDRAF "Resolução Nº 61" aparece em dois atos diferentes.
- **1B. Hash do conteúdo da linha:** muda se a pesquisadora corrigir um erro de digitação, e o ato corrigido entraria como ato novo.
- **1C. Conselho + `ID_VERSAO`:** o `ID_VERSAO` existe nas 5 abas e não se repete dentro de nenhuma (contado).

### 2. Onde fica a tipologia dela

- **2A. Coluna em `ato`:** viola R3 e o ADR 0001, em que a classificação é insert-only e tem revisor.
- **2B. Linha em `classificacao`, com a pesquisadora como revisora:** a mesma tabela em que a curadoria vai reclassificar.

E como a carga convive com a curadoria depois:

- **2B-i. A planilha sempre vence:** recarregar grava a classificação da planilha de novo e ela vira a vigente, sobrepondo o que a pesquisadora reclassificou na curadoria.
- **2B-ii. A planilha entra uma vez por ato:** se já existe classificação da pesquisadora para o ato, a carga não faz nada.

E o código `99`:

- **Ato sem classificação:** o `99` não entra, e a carga perde o rótulo dela em 6 atos.
- **`99` como sigla da tabela `tipologia`:** o rótulo entra como está.

### 3. Com o que ler o `.xlsx`, e onde isso roda

- **3A. Python stdlib** (`zipfile` + `xml.etree`): o `.xlsx` é um zip de XMLs.
- **3B. pandas + openpyxl:** o caminho mais comum.
- **3C. DuckDB** (`read_xlsx`).

O polars saiu antes da medição. Rodar no host com `uv run` também foi considerado e descartado por R4: rodamos num container do compose.

## Medição

Os três leitores foram escritos com o mesmo contrato de saída (aba, linha do Excel, id, data, referência legal, tipologia e texto) e medidos contra as armadilhas acima e contra duas mutações da planilha: uma data virando o texto `s/d` e a linha 10 do CNAS esvaziada.

**Condição:** Linux x86_64 (AMD Ryzen 7 2700), Docker 29.7.2, base `python:3.12-slim`, mediana de 5 execuções, três rodadas com resultados estáveis. Dados brutos em `docs/diario/medicoes/2026-09-26-extracao/resultados.json`. O código do benchmark ficou no commit `e4f87eb`; para reproduzir:

```bash
git checkout e4f87eb -- docs/diario/medicoes/2026-09-26-extracao
python3 docs/diario/medicoes/2026-09-26-extracao/bench.py
```

| | 3A stdlib | 3B pandas 3.0.6 + openpyxl 3.1.5 | 3C DuckDB 1.5.5 |
|---|---|---|---|
| Armadilhas e mutações (215 atos, CONAMA na linha 2, datas, CNPIR, `99`, linha do Excel, determinismo; `s/d` para a leitura; linha vazia não some) | todas | todas | todas |
| Os 215 registros, campo a campo | iguais nos três | iguais nos três | iguais nos três |
| Linhas de código | 61 | 34 | 35 |
| Imagem a mais / tempo de build | 0 MB / 0,7 s | 45 MB / 23 s | 30 MB / 10 s |
| Execução no container | 0,7 s | 1,7 s | 0,6 s |
| Chamada mais direta, sem contorno | não existe: toda conversão é escrita à mão | o `max_row` conta 2.638 linhas; o `1/2005` do CNPIR vira uma data que parece válida | para na primeira linha vazia: com a linha 10 esvaziada, devolve 8 dos 53 atos do CNAS, **sem erro** |

**Leitura.** Escritos com cuidado, os três acertam. O que os separa é o comportamento padrão, que pega quem mexer no leitor depois: o 3B produz o 2.638 que já enganou a squad uma vez, e o 3C perde linha em silêncio, que é o que R2 proíbe.

**A carga escolhida, medida** (diário de 26/09, `tests/db/test_carga.sh`):

| Medida | Valor |
|---|---|
| Atos carregados / descartados / com classificação | 215 / 0 / 215 |
| Segunda carga seguida (R1) | 0 atos e 0 classificações novas; relatório com o mesmo sha256 |
| `make setup` em clone limpo, imagens em cache | 11,9 s; `git status` vazio depois (o relatório gerado é idêntico ao versionado) |
| Testes da leitura com 5 defeitos plantados no código | os 5 pegos |
| Reclassificação da curadoria + carga de novo, com a regra 2B-ii removida | a vigente volta para o rótulo da planilha e entram 215 classificações duplicadas (tudo desfeito na transação); com a regra, a reclassificação fica |

## Decisão

1. **Um ato da planilha é identificado por conselho + `ID_VERSAO`** (1C): `ato.id_planilha` e o índice único `uq_ato_planilha (orgao_id, id_planilha)` para `origem = 'PLANILHA'`, em `sql/003`. Substitui a D3.
2. **A tipologia dela vai para `classificacao`, com a pesquisadora como revisora, uma vez por ato, e nunca sobrepõe a curadoria** (2B-ii). O `99` entra como sigla da tabela `tipologia` ("Fora da tipologia"), em `sql/005`.
3. **A leitura usa só a biblioteca padrão do Python** (3A), no serviço `carga` do compose (`python:3.12.14-slim`, sem rede, montagens só de leitura). O Python só escreve SQL no stdout; quem grava é o `psql` do container `db`, como no `migrate.sh`.

Complementam a decisão:
- **Os 5 conselhos entram por migração** (`sql/004`), porque todo ato exige `orgao_id` e a #4 ainda não saiu.
- **Resumo vai em `ementa` e texto transcrito em `conteudo`**, conforme a aba.
- **Toda linha com valor vira ato ou descarte com motivo** no `docs/carga/relatorio-planilha.md`, e qualquer mudança de estrutura da planilha para a carga.

## Consequências

**O que ganhamos:**
- R1 garantido pelo banco (o índice único), não pelo script.
- O julgamento humano feito na curadoria sobrevive a qualquer recarga.
- Nenhuma dependência e nada baixado na carga. Toda conversão (data serial, CNPIR, `99`) é código nosso, coberto pelos 21 testes de `tests/planilha/`.
- As colunas são achadas pelo texto do cabeçalho, então coluna renomeada ou faltando para a carga em vez de carregar dado errado.

**O que perdemos:**
- **Um leitor de `.xlsx` para manter**, com quase o dobro de código dos outros dois (61 linhas, contra 34 e 35). Ele cobre só o que esta planilha usa: strings compartilhadas, números e datas no sistema 1900.
- **Correção na planilha não chega ao banco pela carga.** Se uma versão nova corrigir um rótulo, a correção entra pela curadoria.
- **`AUTOR`, `REF_EMI_CON` e `REFERENTE` ficam fora do banco**, só no CSV em `data/interim/`: o esquema não tem onde guardá-los.
- **O `99` é uma sigla fora da tipologia de Gurza Lavalle et al.** na tabela `tipologia`. Quem calcular o indicador tem que filtrá-lo.
- **Os 5 conselhos entram sem hierarquia nem nomes antigos.** A #4 completa, reaproveitando os mesmos órgãos.

**O que se torna irreversível:** nada. Trocar o leitor é trocar `src/planilha/xlsx.py`, e a chave, a regra 2B-ii e o `99` são migrações e SQL que uma migração nova desfaz. Depois do merge, `003`, `004` e `005` não se editam.

## Em aberto (na issue #3)

- O que o `99` significa para a pesquisadora.
- Quem classificou o CNAS: o cabeçalho diz `TIPOL_DECIS (M e J)`. Por ora, todas as classificações vão para a revisora "Pesquisadora Principal" do seed.
- Se a `DATA` da planilha é de publicação ou de assinatura. Entra em `data_publicacao`.

## Gatilho de revisão

- **A pesquisadora mandar uma versão nova da planilha com rótulos corrigidos** → reavaliar a regra 2B-ii (por exemplo, a carga passar a gravar a correção como nova linha quando o rótulo da planilha mudar).
- **Entrar uma segunda planilha, de outro formato** (`.ods`, datas de 1904, fórmulas) → o leitor da stdlib não cobre; refazer a medição com os três leitores.
- **A #6 padronizar `uv` no host** para o pipeline → mover a carga para o mesmo padrão.
- **A pesquisadora esclarecer o `99`** → decidir se ele continua como sigla ou vira ato sem classificação.
