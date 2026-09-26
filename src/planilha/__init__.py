"""Carga da planilha da pesquisadora no OLTP de curadoria (issue #3).

xlsx.py lê o arquivo, abas.py diz o que cada coluna significa, normalizar.py produz os
atos (com descartes e avisos contados), relatorio.py e carga.py geram as saídas.
Só biblioteca padrão; roda no serviço `carga` do compose (make carga).
"""
