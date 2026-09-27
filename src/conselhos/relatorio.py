"""Relatório da identidade dos conselhos (docs/carga/relatorio-conselhos.md). Determinístico:
as mesmas entradas geram o mesmo arquivo, byte a byte."""

import collections


def _br(n):
    return f"{n:,}".replace(",", ".")


def _d(d):
    return d.strftime("%d/%m/%Y") if d else "não verificada"


def _cel(t):
    return (t or "").replace("|", "\\|")


def relatorio(res):
    pendentes = [a for a in res.aliases if a.status != "RESOLVIDO"]
    chaves_pendentes = {a.chave for a in pendentes}
    chaves_ambiguas = {a.chave for a in pendentes if a.status == "AMBIGUO"}
    chaves_certas = res.chaves - len(chaves_pendentes)
    fusoes = chaves_certas - len(res.orgaos)
    status = collections.Counter(a.status for a in res.aliases)
    com_siorg = [o for o in res.orgaos if o.codigo_siorg is not None]
    L = []
    w = L.append

    w("# Identidade dos conselhos")
    w("")
    w("> Gerado por `make carga` (`python -m conselhos relatorio`); não editar à mão. "
      "As mesmas entradas geram este mesmo arquivo. Decisão de método: [ADR 0004](../adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md).")
    w("")
    for rotulo, (caminho, sha) in res.arquivos.items():
        w(f"- **{rotulo[0].upper() + rotulo[1:]}:** `{caminho}` · sha256 `{sha}`")
    m = res.siorg
    w(f"- **SIORG:** consultado em {m.get('data', '?')}, {_br(int(m.get('unidades', 0)))} unidades, "
      f"sha256 `{m.get('sha256', '?')}`")
    w("")
    w("## Resumo")
    w("")
    w(f"**{len(res.orgaos)} conselhos distintos** nas {len(res.aliases)} linhas da aba \"Conselhos mapeados no DOU\", "
      f"e até **{len(res.orgaos) + len(chaves_ambiguas)}** se cada nome ambíguo se mostrar um órgão próprio.")
    w("")
    w("| Linhas | Situação |")
    w("|---|---|")
    w(f"| {status['RESOLVIDO']} | apontam para um órgão |")
    w(f"| {status['INDEFINIDO']} | indefinidas: nome genérico, sem como saber o órgão |")
    w(f"| {status['AMBIGUO']} | ambíguas: à espera de decisão da squad ou da pesquisadora |")
    w(f"| **{len(res.aliases)}** | toda linha tem um órgão ou está marcada, com o motivo |")
    w("")
    w("## Como se chega ao número")
    w("")
    w("| Passo | Nomes | Por quê |")
    w("|---|---|---|")
    w(f"| Linhas da aba | {len(res.aliases)} | cada grafia conta como um nome |")
    w(f"| Chave normalizada | {res.chaves} | junta o que só difere em caixa, acento, espaços, quebra de linha e sigla no fim |")
    w(f"| Sem as pendências | {chaves_certas} | {len(chaves_pendentes)} chaves indefinidas ou ambíguas saem da conta |")
    w(f"| Decisões de grafia e renomeação | **{len(res.orgaos)}** | {fusoes} chaves juntadas a outra por decisão registrada, abaixo |")
    w("")
    w("## Renomeações")
    w("")
    w("Nome antigo em `orgao_nome`, com a vigência fechada no dia anterior ao ato; o nome novo vale a partir do ato.")
    w("")
    w("| Órgão (nome vigente) | Nome antigo | Início do nome antigo | Fim | Ato |")
    w("|---|---|---|---|---|")
    for o in res.orgaos:
        for a in o.nomes_antigos:
            w(f"| {_cel(o.nome)} | {_cel(a.nome)} | {_d(a.inicio)} | {_d(a.fim)} | {_cel(a.ato)} |")
    w("")
    w("## Grafias juntadas por decisão")
    w("")
    w("Nomes que a chave não junta e que uma decisão registrada junta. As grafias que só diferem em caixa, "
      "acento ou sigla estão na tabela de órgãos.")
    w("")
    w("| Linha | Nome na planilha | Órgão | Motivo |")
    w("|---|---|---|---|")
    for a in res.aliases:
        if a.como == "grafia":
            w(f"| {a.linha} | {_cel(a.nome)} | {_cel(a.orgao)} | {_cel(a.motivo)} |")
    w("")
    w("## Pendências")
    w("")
    w("Entram em `orgao_alias` sem órgão, com o motivo. Resolvida a dúvida, a decisão muda no CSV e a próxima carga aponta o alias para o órgão.")
    w("")
    w("| Linha | Nome na planilha | Situação | Motivo |")
    w("|---|---|---|---|")
    for a in pendentes:
        w(f"| {a.linha} | {_cel(a.nome)} | {a.status.lower()} | {_cel(a.motivo)} |")
    w("")
    w("## Órgãos")
    w("")
    w(f"{len(com_siorg)} dos {len(res.orgaos)} órgãos têm código SIORG. O nome vigente vem do SIORG quando a chave "
      "casa com uma unidade só; senão, da decisão \"nome\" no CSV. \"Nome vigente desde\" vem das renomeações "
      "e das decisões; os 5 conselhos da #3 têm a data de criação no `sql/004`, que a carga não altera.")
    w("")
    w("| Órgão | Sigla | SIORG | Nome vigente desde | Linhas da planilha |")
    w("|---|---|---|---|---|")
    for o in res.orgaos:
        siorg = str(o.codigo_siorg) if o.codigo_siorg is not None else "—"
        w(f"| {_cel(o.nome)} | {_cel(o.sigla) or '—'} | {siorg} | {_d(o.inicio)} | {', '.join(map(str, o.linhas))} |")
    w("")
    return "\n".join(L)
