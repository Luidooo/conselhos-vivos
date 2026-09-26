"""Vocabulário único das 5 abas: cada coluna da planilha -> um campo, e o porquê.

As colunas são achadas pelo texto do cabeçalho, não pela letra: se a pesquisadora
reordenar ou renomear uma coluna, a carga para com erro em vez de ler a coluna errada.
O relatório de carga reproduz estas tabelas; decisões do diário de 26/09 (#3).
"""

from dataclasses import dataclass

REVISOR = "curadoria@pesquisa.local"  # 'Pesquisadora Principal' do sql/002_seeds.sql
TIPOLOGIAS = ("DEF", "FISC", "GEST", "AUTO", "IP", "99")  # 99: sql/005

# Campo do vocabulário único -> (destino no banco, por quê)
CAMPOS = {
    "id_versao": ("ato.id_planilha", "chave do ato na planilha, junto com o conselho (sql/003)"),
    "data": ("ato.data_publicacao", "serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura"),
    "ano": ("não carregado", "redundante com a data; conferido, e a divergência vira aviso"),
    "ementa": ("ato.ementa", "resumo do ato escrito pela pesquisadora"),
    "conteudo": ("ato.conteudo", "texto do ato transcrito pela pesquisadora, inteiro ou em trecho"),
    "ref_legal": ("ato.ref_legal", "como está na planilha; informativa, não é chave"),
    "tipologia": ("classificacao.tipologia_sigla", "rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora"),
    "referente": ("não carregado", "outro rótulo dela (a quem o ato se dirige); o esquema não tem onde guardar, fica no CSV normalizado"),
    "autor": ("não carregado", "a aba já identifica o conselho; os valores encontrados estão no relatório"),
    "emissao": ("não carregado", "diz quem emitiu; os valores encontrados estão no relatório"),
}


@dataclass(frozen=True)
class Mapa:
    aba: str
    conselho: str       # nome vigente em orgao_nome (sql/004)
    cabecalho: int      # linha do cabeçalho no Excel
    colunas: dict       # campo -> texto do cabeçalho (comparado sem espaços nas pontas)


MAPAS = [
    Mapa("CNAS", "Conselho Nacional de Assistência Social", 1, {
        "id_versao": "ID_VERSAO", "ano": "ANO", "data": "DATA", "ementa": "TEMA",
        "autor": "AUTOR", "referente": "REFERENTE", "tipologia": "TIPOL_DECIS (M e J)"}),
    # cabeçalho na linha 2: a linha 1 está vazia; o TEMA é o texto do ato, desde o cabeçalho do DOU
    Mapa("CONAMA", "Conselho Nacional do Meio Ambiente", 2, {
        "id_versao": "ID_VERSAO", "data": "ANO E DATA", "ano": "ANO", "conteudo": "TEMA",
        "ref_legal": "DISP_LEG", "referente": "REFERENTE", "tipologia": "TIPO Incidência (geral)"}),
    # o TEMA traz a parte dispositiva ("RESOLVE: ...") e o TEMA_RESUM, o resumo
    Mapa("CONCIDADES", "Conselho das Cidades", 1, {
        "id_versao": "ID_VERSAO", "ano": "ANO", "data": "DATA", "conteudo": "TEMA",
        "ref_legal": "DIS_LEG", "emissao": "REF_EMI_CON", "autor": "AUTOR",
        "referente": "REFERENTE", "ementa": "TEMA_RESUM", "tipologia": "TIPOL_DECIS"}),
    Mapa("CONDRAF", "Conselho Nacional de Desenvolvimento Rural Sustentável", 1, {
        "id_versao": "ID_VERSAO", "ano": "ANO", "data": "DATA", "ementa": "TEMA",
        "ref_legal": "DIS_LEG", "emissao": "REF_EMI_CON", "autor": "AUTOR",
        "referente": "REFERENTE", "tipologia": "TIPOL_DECIS"}),
    # DIS_LEG (ATO/ANO): o Excel leu "1/2005" como data; normalizar.py recupera o número do ato
    Mapa("CNPIR", "Conselho Nacional de Promoção da Igualdade Racial", 1, {
        "id_versao": "ID_VERSAO", "ano": "ANO", "data": "DATA (MÊS/DIA/ANO)", "conteudo": "TEMA",
        "ref_legal": "DIS_LEG (ATO/ANO)", "tipologia": "TIPOL_DECIS"}),
]
