

CREATE   VIEW [dbo].[V_CUSTO_ALL_ANALISE]
AS

SELECT 'GR360_TRAD' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM GR360_TRAD..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'GR360' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM GR360..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_CH' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_CH..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_DE' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_DE..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_ES' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_ES..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_FR' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_FR..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_G2S' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_G2S..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_GHA' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_GHA..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_GRE' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_GRE..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_IND' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_IND..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'INTERSOL' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM INTERSOL..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_MA' AS BDADOS, data, ISNULL(familia,'') AS familia, total_euro AS total
FROM HSOLS_MA..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)

UNION ALL
SELECT 'HSOLS_PT' AS BDADOS, data, ISNULL(familia,'') AS familia, total
FROM HSOLS_PT..v_custo where cabstamp not in (select fostamp from v_fo_intragrupo)
