-- A espinha de tempo diária que o MetricFlow exige (ADR 0011): um dia por linha, de 2002, o primeiro ano
-- dos dados abertos, até 2030.
-- shortcut: o fim é fixo; estender quando a gold chegar perto de 2030.
select cast(range as date) as date_day
from range(date '2002-01-01', date '2031-01-01', interval 1 day)
