# Análise de LGPD

O que a plataforma guarda de dado pessoal, com que base legal, por quanto tempo e como descarta. A medição é de
24/11/2026, num banco refeito do zero com a planilha e o DOU de julho a setembro de 2026 ([medicoes.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/lgpd/medicoes.txt)).
Esta análise é da squad, não um parecer jurídico.

## O dado pessoal que existe

| Onde | Dado | Titular | Quanto há |
|---|---|---|---|
| `revisor` | nome e e-mail de quem classifica os atos | a pesquisadora e bolsistas | 1 revisor humano; 2 revisores com e-mail, e o outro é o pipeline |
| `ato.conteudo` e `ato.ementa` | nomes de pessoas nomeadas, designadas ou exoneradas em atos de conselho; CPF, quando o ato traz, mascarado pela própria Imprensa Nacional | pessoas citadas no DOU | nenhum ato com CPF mascarado; 1 ato de nomeação, designação ou exoneração, entre 604 atos (389 do DOU e 215 da planilha) |
| `data/bronze/` e `data/silver/mencoes/` | os mesmos textos, como vieram do DOU | idem | os ZIPs inteiros da Seção 1 |
| `alerta.tratado_por` | quem tratou cada alerta | a curadoria | liga ao `revisor` |

**O limite da medição:** a contagem de nomeação procura os três verbos na ementa e nos 300 primeiros caracteres do texto. Um nome citado mais adiante, como o de quem assina o ato ou o de um conselheiro numa ata, não entra nela. O número diz que ato de pessoal é raro nos conselhos; não diz que só um ato tem nome de pessoa.

O que **não** existe: dado sensível (art. 5º, II), dado de criança, login de usuário final ou rastreio de quem abre o painel. O painel e a página Revisar não têm conta: rodam só em `127.0.0.1`.

## Base legal e finalidade

- **Os textos do DOU** são dado tornado público pelo próprio poder público. O tratamento considera a finalidade, a boa-fé e o interesse público que justificaram a publicação (art. 7º, § 3º). A finalidade aqui é a mesma: acompanhar o funcionamento de instâncias de participação social. Nada do texto é usado para perfilar a pessoa citada.
- **O nome e o e-mail do revisor** servem para atribuir cada classificação a quem a fez, o que é a auditoria da curadoria (ADR 0001). A base é a realização de estudo por órgão de pesquisa (art. 7º, IV). O projeto é uma pesquisa acadêmica da UnB com a pesquisadora da UFPB.

## Retenção e descarte

| Dado | Retenção | Descarte |
|---|---|---|
| Textos do DOU (bronze, OLTP, silver) | enquanto durar a pesquisa: o histórico é o objeto do estudo (art. 16, II, conservação para estudo por órgão de pesquisa) | apagar `data/` e o volume do banco ao fim do projeto; o DOU continua público na fonte |
| Nome e e-mail do revisor | enquanto ele participar da curadoria | `make anonimizar-revisor ID=n`: o nome vira "Revisor removido", o e-mail some, e as classificações ficam, sem identificar a pessoa |
| Alertas | enquanto a curadoria precisar do histórico | ficam com o tratado por, que aponta um revisor já anonimizado depois do descarte |

## Segurança e acesso (art. 46)

- **Privilégio mínimo:** cada serviço entra no Postgres por um papel com o mínimo que precisa (ADR 0011, migração `sql/007_alertas_e_papeis.sql`).
  - O app de curadoria **não lê o e-mail** do revisor: esse é o recorte de coluna.
  - O dbt só lê os órgãos, os nomes deles e os conselhos.
  - O ETL reverso só escreve alertas.
- **Prova:** `bash tests/db/test_acesso.sh`, que roda no `make test`.
- **Portas:** banco, pgAdmin, painel e Dagster publicados só em `127.0.0.1`.
- **Senhas:** só no ambiente; o repositório tem o padrão de desenvolvimento.

## Quando revisar esta análise

- A aba Perguntar: ela manda trechos do DOU e a pergunta da pesquisadora à API do Claude, o que é uma transferência internacional (art. 33). O ADR 0012 completa esta análise.
- Se o painel ganhar login ou sair de `127.0.0.1`.
- Se entrar uma fonte com dado pessoal que não seja público, como lista de conselheiros com contato.
