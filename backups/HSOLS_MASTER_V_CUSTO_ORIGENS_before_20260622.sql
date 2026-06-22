






CREATE view [dbo].[V_CUSTO_ORIGENS] as

select 'GR360_TRAD' BDADOS, *, isnull((select fn.u_matricul from gr360_trad..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from gr360_trad..v_custo union all
select 'GR360' BDADOS, *, isnull((select fn.u_matricul from gr360..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from gr360..v_custo union all
--select 'HSOLS_CH' BDADOS, *, isnull((select fn.u_matricul from HSOLS_CH..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_CH..v_custo union all 
select 'HSOLS_DE' BDADOS, *, isnull((select fn.u_matricul from HSOLS_DE..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_DE..v_custo union all 
select 'HSOLS_ES' BDADOS, *, isnull((select fn.u_matricul from HSOLS_ES..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(1 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_ES..v_custo union all 
select 'HSOLS_FR' BDADOS, *, isnull((select fn.u_matricul from HSOLS_FR..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_FR..v_custo union all 
select 'HSOLS_G2S' BDADOS, *, isnull((select fn.u_matricul from HSOLS_G2S..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_G2S..v_custo union all 
--select 'HSOLS_GHA' BDADOS, *, isnull((select fn.u_matricul from HSOLS_GHA..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_GHA..v_custo union all 
select 'HSOLS_GRE' BDADOS, *, isnull((select fn.u_matricul from HSOLS_GRE..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_GRE..v_custo union all 
select 'HSOLS_IND' BDADOS, *, isnull((select fn.u_matricul from HSOLS_IND..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_IND..v_custo union all 

select 'INTERSOL-ALSACE' BDADOS, *, isnull((select fn.u_matricul from INTERSOL..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, 
		substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO 
		from INTERSOL..v_custo WHERE CCUSTO IN (SELECT PROCESSO FROM INTERSOL..OPC WHERE OPC.U_ORIGEM = 'INTERSOL-ALSACE')		
union all 
select 'INTERSOL-LORRAINE' BDADOS, *, isnull((select fn.u_matricul from INTERSOL..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, 
		substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO 
		from INTERSOL..v_custo WHERE CCUSTO IN (SELECT PROCESSO FROM INTERSOL..OPC WHERE OPC.U_ORIGEM = 'INTERSOL-LORRAINE')		
union all 
select 'INTERSOL-CHAMPAGNE' BDADOS, *, isnull((select fn.u_matricul from INTERSOL..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, 
		substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO 
		from INTERSOL..v_custo WHERE CCUSTO IN (SELECT PROCESSO FROM INTERSOL..OPC WHERE OPC.U_ORIGEM = 'INTERSOL-CHAMPAGNE')		
union all 

select 'HSOLS_MA' BDADOS, origem, cabstamp, stamp, nmdoc, nrdoc, data, nome, ccusto, ref, design, qtt, epv_euro, total_euro, familia, isnull((select fn.u_matricul from HSOLS_MA..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_MA..v_custo union all 
select 'HSOLS_PT' BDADOS, *, isnull((select fn.u_matricul from HSOLS_PT..fn where fn.fnstamp = v_custo.stamp),'') u_matricul, substring(ccusto,3,4) as ccusto_geral,CAST(0 AS BIT) AS INSTRAGRUPO, CASE WHEN CAST(1 AS BIT) = 1 THEN 'Tem INSTRAGRUPO' ELSE '' END AS PBI_TEM_INSTRAGRUPO from HSOLS_PT..v_custo 



