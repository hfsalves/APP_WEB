declare @ano int,
        @detalhe bit,
        @TOTALFT numeric(16,2),
        @TOTALCT numeric(16,2),
        @datafechada date,
        @iniAno date,
        @fimAno date,
        @bdados varchar(80)

set @ano = #1#
set @detalhe = #2#
set @bdados = upper(replace(ltrim(rtrim(isnull(#3#, 'HSOLS_FR'))), '-', '_'))

if @bdados = ''
    set @bdados = 'HSOLS_FR'

set @datafechada = eomonth(dateadd(month, -1, getdate()))
set @iniAno = datefromparts(@ano, 1, 1)
set @fimAno = case
                when @datafechada < datefromparts(@ano, 12, 31) then @datafechada
                else datefromparts(@ano, 12, 31)
              end

if object_id('tempdb..#Base') is not null drop table #Base
if object_id('tempdb..#Meses') is not null drop table #Meses
if object_id('tempdb..#CustoMensal') is not null drop table #CustoMensal
if object_id('tempdb..#FTMensal') is not null drop table #FTMensal
if object_id('tempdb..#TREMensal') is not null drop table #TREMensal
if object_id('tempdb..#Linhas') is not null drop table #Linhas
if object_id('tempdb..#Final') is not null drop table #Final

select *
into #Base
from (
    select 10 as ordem, ref, nome
    from HSOLS_MASTER.dbo.V_STFAMI
    where ref like '[0-7]%'
      and len(ref) <= case when @detalhe = 1 then 6 else 4 end

    union all select 1, 'TRE', 'Solde de trésorerie'
    union all select 2, '--',  '----------------------------'
    union all select 3, 'FT',  'Facturation'
    union all select 4, 'CT',  'Total de Coûts'
    union all select 5, 'MRG', 'Marge'
    union all select 7, '--',  '----------------------------'
    union all select 8, 'NC',  'Coûts Non Classés'
    union all select 9, '--',  '----------------------------'
) x

create index IX_Base_ref on #Base(ref)

select v.mes
into #Meses
from (values (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12)) v(mes)

create index IX_Meses_mes on #Meses(mes)

/* CUSTOS MENSAIS
   Fonte igual à aplicação: HSOLS_MASTER.dbo.V_CUSTO_ORIGENS.
   A origem HSOLS_FR é filtrada pelo campo BDADOS.
*/
select
    year(DATA) as ano,
    month(DATA) as mes,
    ltrim(rtrim(isnull(FAMILIA, ''))) as familia,
    sum(isnull(TOTAL, 0)) as total
into #CustoMensal
from HSOLS_MASTER.dbo.V_CUSTO_ORIGENS
where DATA >= @iniAno
  and DATA < dateadd(day, 1, @fimAno)
  and upper(replace(ltrim(rtrim(isnull(BDADOS, ''))), '-', '_')) = @bdados
  and ltrim(rtrim(isnull(FAMILIA, ''))) <> ''
group by year(DATA), month(DATA), ltrim(rtrim(isnull(FAMILIA, '')))

create index IX_CustoMensal_ano_mes_familia on #CustoMensal(ano, mes, familia)

/* FATURAÇÃO MENSAL
   Fonte igual à aplicação: HSOLS_MASTER.dbo.V_FT_ORIGENS.
   Na aplicação, todos os proveitos entram na família 7.1.1.
*/
select
    year(FDATA) as ano,
    month(FDATA) as mes,
    sum(isnull(ETTILIQ, 0)) as total
into #FTMensal
from HSOLS_MASTER.dbo.V_FT_ORIGENS
where FDATA >= @iniAno
  and FDATA < dateadd(day, 1, @fimAno)
  and upper(replace(ltrim(rtrim(isnull(BDADOS, ''))), '-', '_')) = @bdados
group by year(FDATA), month(FDATA)

create index IX_FTMensal_ano_mes on #FTMensal(ano, mes)

/* TESOURARIA MENSAL
   Mantém a lógica existente, porque não pertence ao mapa GR da aplicação.
*/
select
    m.mes,
    case
        when @datafechada < datefromparts(@ano, m.mes, 1) then cast(0 as numeric(16,2))
        else isnull((
            select sum(ol.EENTR - ol.ESAID)
            from HSOLS_FR.dbo.OL ol with (nolock)
            where ol.TRANSF = 0
              and ol.DATA <= eomonth(datefromparts(@ano, m.mes, 1))
        ), 0)
    end as total
into #TREMensal
from #Meses m

create index IX_TREMensal_mes on #TREMensal(mes)

select @TOTALCT = isnull(sum(total), 0)
from #CustoMensal
where ano = @ano
  and familia not like '7%'

select @TOTALFT = isnull(sum(total), 0)
from #FTMensal
where ano = @ano

select
    b.ordem,
    b.ref,
    b.nome,
    m.mes,
    cast(
        case
            when b.ref = '--' then 0

            when b.ref = 'NC' then
                isnull((
                    select sum(c.total)
                    from #CustoMensal c
                    where c.ano = @ano
                      and c.mes = m.mes
                      and c.familia = ''
                ), 0)

            when b.ref = 'CT' then
                isnull((
                    select sum(c.total)
                    from #CustoMensal c
                    where c.ano = @ano
                      and c.mes = m.mes
                      and c.familia not like '7%'
                ), 0)

            when b.ref = 'FT' then
                isnull((
                    select sum(f.total)
                    from #FTMensal f
                    where f.ano = @ano
                      and f.mes = m.mes
                ), 0)

            when b.ref = 'MRG' then
                isnull((
                    select sum(f.total)
                    from #FTMensal f
                    where f.ano = @ano
                      and f.mes = m.mes
                ), 0)
                -
                isnull((
                    select sum(c.total)
                    from #CustoMensal c
                    where c.ano = @ano
                      and c.mes = m.mes
                      and c.familia not like '7%'
                ), 0)

            when b.ref = 'TRE' then
                isnull((
                    select t.total
                    from #TREMensal t
                    where t.mes = m.mes
                ), 0)

            when b.ref in ('7', '7.1', '7.1.1') then
                isnull((
                    select sum(c.total)
                    from #CustoMensal c
                    where c.ano = @ano
                      and c.mes = m.mes
                      and c.familia like b.ref + '%'
                ), 0)
                +
                isnull((
                    select sum(f.total)
                    from #FTMensal f
                    where f.ano = @ano
                      and f.mes = m.mes
                ), 0)

            else
                isnull((
                    select sum(c.total)
                    from #CustoMensal c
                    where c.ano = @ano
                      and c.mes = m.mes
                      and c.familia like b.ref + '%'
                ), 0)
        end
    as numeric(16,2)) as valor
into #Linhas
from #Base b
cross join #Meses m

create index IX_Linhas_ref_mes on #Linhas(ref, mes)

select
    l.ordem,
    l.ref,
    case
        when l.ref in ('1','2','3','4','5','6','7','NC','CT','FT','MRG','--','TRE') then '<p style="color:grey;font-size:13px"><b>' + l.ref + '</b></p>'
        when len(l.ref) = 3 then '<p style="color:grey;font-size:11px;margin-left:10px"><b>' + l.ref + '</b></p>'
        else '<p style="color:grey;font-size:11px;margin-left:20px"><b><i>' + l.ref + '</i></b></p>'
    end as Code,
    case
        when l.ref in ('1','2','3','4','5','6','7','NC','CT','FT','MRG','--','TRE') then '<p style="color:grey;font-size:13px;"><b>' + max(l.nome) + '</b></p>'
        when len(l.ref) = 3 then '<p style="color:grey;font-size:11px;margin-left:10px"><b>' + max(l.nome) + '</b></p>'
        else '<p style="color:grey;font-size:11px;margin-left:20px"><b><i>' + max(l.nome) + '</i></b></p>'
    end as Description,
    sum(case when l.mes = 1  then l.valor else 0 end) as Janvier,
    sum(case when l.mes = 2  then l.valor else 0 end) as Fevrier,
    sum(case when l.mes = 3  then l.valor else 0 end) as Mars,
    sum(case when l.mes = 4  then l.valor else 0 end) as Avril,
    sum(case when l.mes = 5  then l.valor else 0 end) as Mai,
    sum(case when l.mes = 6  then l.valor else 0 end) as Juin,
    sum(case when l.mes = 7  then l.valor else 0 end) as Juillet,
    sum(case when l.mes = 8  then l.valor else 0 end) as Aout,
    sum(case when l.mes = 9  then l.valor else 0 end) as Septembre,
    sum(case when l.mes = 10 then l.valor else 0 end) as Octobre,
    sum(case when l.mes = 11 then l.valor else 0 end) as Novembre,
    sum(case when l.mes = 12 then l.valor else 0 end) as Decembre,
    sum(l.valor) as Total
into #Final
from #Linhas l
group by l.ordem, l.ref

create index IX_Final_ordem_ref on #Final(ordem, ref)

select
    Code,
    Description,
    case when Janvier = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Janvier AS money), 1) + '</p>' end as Janvier,
    case when Fevrier = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Fevrier AS money), 1) + '</p>' end as Fevrier,
    case when Mars = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Mars AS money), 1) + '</p>' end as Mars,
    case when Avril = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Avril AS money), 1) + '</p>' end as Avril,
    case when Mai = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Mai AS money), 1) + '</p>' end as Mai,
    case when Juin = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Juin AS money), 1) + '</p>' end as Juin,
    case when Juillet = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Juillet AS money), 1) + '</p>' end as Juillet,
    case when Aout = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Aout AS money), 1) + '</p>' end as Aout,
    case when Septembre = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Septembre AS money), 1) + '</p>' end as Septembre,
    case when Octobre = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Octobre AS money), 1) + '</p>' end as Octobre,
    case when Novembre = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Novembre AS money), 1) + '</p>' end as Novembre,
    case when Decembre = 0 then '' else '<p style="text-align:right">' + CONVERT(varchar, CAST(Decembre AS money), 1) + '</p>' end as Decembre,
    case when Total = 0 then '' else '<p style="text-align:right"><b>' + CONVERT(varchar, CAST(Total AS money), 1) + '</b></p>' end as Total,
    case
        when Total = 0 or ref in ('CT','FT','TRE','7','7.1','7.1.1') then ''
        when ref = 'MRG' then '<p style="text-align:right"><b>' + CONVERT(varchar, CAST(case when @TOTALFT = 0 then 0 else Total / @TOTALFT * 100 end AS money), 1) + '%</b></p>'
        else '<p style="text-align:right"><b>' + CONVERT(varchar, CAST(case when @TOTALCT = 0 then 0 else Total / @TOTALCT * 100 end AS money), 1) + '%</b></p>'
    end as P
from #Final
order by ordem, ref
