CREATE PROCEDURE dbo.sp_sync_compras
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @newfo varchar(25);
    DECLARE @docnome varchar(50);
    DECLARE @doccode int;
    DECLARE @erro varchar(max);

    DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
        SELECT TOP 20 fostamp
        FROM GESTAO..FO
        WHERE sync = 0
          AND ISNULL(sync_erro, 0) = 0
          AND obs = 'Ok - Tudo validado'
        ORDER BY ousrdata, ousrhora, fostamp;

    OPEN cur;
    FETCH NEXT FROM cur INTO @newfo;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            BEGIN TRAN;

            DELETE fo 
            WHERE plano = 0 
              AND fostamp COLLATE SQL_Latin1_General_CP1_CI_AI = @newfo;

            DELETE fo2 
            WHERE fo2stamp COLLATE SQL_Latin1_General_CP1_CI_AI = @newfo
              AND fo2stamp NOT IN (SELECT fostamp FROM fo);

            DELETE fot 
            WHERE fostamp COLLATE SQL_Latin1_General_CP1_CI_AI = @newfo
              AND fostamp NOT IN (SELECT fostamp FROM fo);

            DELETE fn 
            WHERE fostamp COLLATE SQL_Latin1_General_CP1_CI_AI = @newfo
              AND fostamp NOT IN (SELECT fostamp FROM fo);

            UPDATE gestao..fo 
            SET 
                eivain = ettiliq,
                eivav1 = ISNULL((SELECT ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido - (etiliquido / (1+(taxaiva/100))) ELSE etiliquido * (taxaiva / 100) END),2) FROM gestao..fn WHERE fn.tabiva = 1 AND fn.fostamp = fo.fostamp),0),
                eivav2 = ISNULL((SELECT ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido - (etiliquido / (1+(taxaiva/100))) ELSE etiliquido * (taxaiva / 100) END),2) FROM gestao..fn WHERE fn.tabiva = 2 AND fn.fostamp = fo.fostamp),0),
                eivav3 = ISNULL((SELECT ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido - (etiliquido / (1+(taxaiva/100))) ELSE etiliquido * (taxaiva / 100) END),2) FROM gestao..fn WHERE fn.tabiva = 3 AND fn.fostamp = fo.fostamp),0),
                eivav4 = ISNULL((SELECT ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido - (etiliquido / (1+(taxaiva/100))) ELSE etiliquido * (taxaiva / 100) END),2) FROM gestao..fn WHERE fn.tabiva = 4 AND fn.fostamp = fo.fostamp),0)
            WHERE fostamp = @newfo;

            SELECT TOP 1 @docnome = ISNULL(docnome,'') 
            FROM gestao..fo 
            WHERE fostamp = @newfo;

            IF @docnome = 'V/Fatura Recibo'
                INSERT INTO fo2 (fo2stamp, ivatx1, ivatx2, ivatx3, olcodigo) 
                SELECT @newfo, 6, 23, 13, 'P10001';
            ELSE
                INSERT INTO fo2 (fo2stamp, ivatx1, ivatx2, ivatx3) 
                SELECT @newfo, 6, 23, 13;

            SELECT TOP 1 
                @doccode = 
                    CASE
                        WHEN docnome = 'V/Fatura' THEN 55
                        WHEN docnome = 'V/Fatura Recibo' THEN 56
                        WHEN docnome = 'V/Nt. Crédito' THEN 3
                        WHEN docnome = 'V/Nt. Crédito DD' THEN 102
                        WHEN docnome = 'V/Fatura Comissões' THEN 104
                        ELSE 55 
                    END
            FROM gestao..fo 
            WHERE fostamp = @newfo;

            INSERT INTO fo
            (
                fostamp, docnome, adoc, nome, total, etotal, data, tipo, docdata, foano, doccode, no, fref, ccusto, ncusto, moeda, totmoeda, pdata, pctacres, valacres, 
                zona, encomenda, ivain, ivatx, ttiva, finv, fin, ttiliq, ivamin, tmiva, finmv, tmiliq, plano, estab, pais, ivainsns, descc, descm, eivain, ettiva, efinv, 
                ettiliq, eivainsns, edescc, evalacres, introfin, final, cambiofixo, memissao, ivav1, eivav1, ivamv1, ivav2, eivav2, ivamv2, ivav3, eivav3, ivamv3, ivav4, 
                eivav4, ivamv4, ivav5, eivav5, ivamv5, ivav6, eivav6, ivamv6, ivav7, eivav7, ivamv7, ivav8, eivav8, ivamv8, ivav9, eivav9, ivamv9, morada, local, codpost, 
                ncont, nmaprov, nmemail, dtaprov, aprovado, intid, nome2, tpstamp, tpdesc, erdtotal, rdtotal, rdtotalm, aivav1, eaivav1, aivamv1, paivav1, epaivav1, paivamv1, 
                aivav2, eaivav2, aivamv2, paivav2, epaivav2, paivamv2, aivav3, eaivav3, aivamv3, paivav3, epaivav3, paivamv3, aivav4, eaivav4, aivamv4, paivav4, epaivav4, 
                paivamv4, aivav5, eaivav5, aivamv5, paivav5, epaivav5, paivamv5, aivav6, eaivav6, aivamv6, paivav6, epaivav6, paivamv6, aivav7, eaivav7, aivamv7, paivav7, 
                epaivav7, paivamv7, aivav8, eaivav8, aivamv8, paivav8, epaivav8, paivamv8, aivav9, eaivav9, aivamv9, paivav9, epaivav9, paivamv9, aivain, eaivain, aivamin, 
                paivain, epaivain, paivamin, atotal, eatotal, atotmoeda, patotal, epatotal, patotmoeda, dplano, dinoplano, dilnoplano, diaplano, planoonline, 
                dostamp, pscm, zncm, excm, ptcm, encm, ntcm, pscmdesc, znregiao, excmdesc, ptcmdesc, encmdesc, ncin, ncout, usaintra, pscmori, pscmoridesc, series, series2, 
                despinc, edespinc, eprocesso, dprocesso, cambio, ollocal, telocal, contado, site, pnome, pno, cxstamp, cxusername, ssstamp, ssusername, classe, virs, evirs, txirs, 
                lang, moeda2, valorm2, arstamp, arno, eanfl, ettieca, ttieca, mttieca, iectisento, iecacodisen, processo, subproc, multi, crend, introvalacres, czonag, sujirsisen, 
                exportado, identdecexp, nprotri, hora, ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada
            )
            SELECT 
                fostamp, docnome, LEFT(adoc,20) AS adoc, nome, etotal * 200.482 AS total, etotal, data, tipo, docdata, foano, @doccode, 
                no, '' fref, ccusto, '' ncusto, 'EURO' moeda, 0 totmoeda, pdata, 0 pctacres, 0 valacres, 
                '' zona, '' encomenda, eivain * 200.482 AS ivain, 0 AS ivatx, ettiva * 200.482 AS ttiva, 0 finv, 0 fin, ettiliq * 200.482 AS ttiliq, 0 ivamin, 0 tmiva, 0 finmv, 0 tmiliq, plano, 0 estab, 
                CASE WHEN fo.docnome IN ('V/Fatura Comissões') THEN 2 ELSE 1 END pais, 
                0 ivainsns, 0 descc, 0 descm, eivain, ettiva, efinv, 
                ettiliq, 0 eivainsns, 0 edescc, 0 evalacres, 0 introfin, 0 final, 0 cambiofixo, 'EURO' memissao, 0 ivav1, eivav1, 0 ivamv1, 0 ivav2, eivav2, 0 ivamv2, 0 ivav3, eivav3, 0 ivamv3, 0 ivav4, 
                eivav4, 0 ivamv4, 0 ivav5, 0 eivav5, 0 ivamv5, 0 ivav6, eivav6, 0 ivamv6, 0 ivav7, eivav7, 0 ivamv7, 0 ivav8, eivav8, 0 ivamv8, 0 ivav9, eivav9, 0 ivamv9, morada, local, codpost, 
                ncont, nmaprov, '' nmemail, dtaprov, aprovado, '' intid, nome2, tpstamp, tpdesc, 0 erdtotal, 0 rdtotal, 0 rdtotalm, 0 aivav1, 0 eaivav1, 0 aivamv1, 0 paivav1, 0 epaivav1, 0 paivamv1, 
                0 aivav2, 0 eaivav2, 0 aivamv2, 0 paivav2, 0 epaivav2, 0 paivamv2, 0 aivav3, 0 eaivav3, 0 aivamv3, 0 paivav3, 0 epaivav3, 0 paivamv3, 0 aivav4, 0 eaivav4, 0 aivamv4, 0 paivav4, 0 epaivav4, 
                0 paivamv4, 0 aivav5, 0 eaivav5, 0 aivamv5, 0 paivav5, 0 epaivav5, 0 paivamv5, 0 aivav6, 0 eaivav6, 0 aivamv6, 0 paivav6, 0 epaivav6, 0 paivamv6, 0 aivav7, 0 eaivav7, 0 aivamv7, 0 paivav7, 
                0 epaivav7, 0 paivamv7, 0 aivav8, 0 eaivav8, 0 aivamv8, 0 paivav8, 0 epaivav8, 0 paivamv8, 0 aivav9, 0 eaivav9, 0 aivamv9, 0 paivav9, 0 epaivav9, 0 paivamv9, 0 aivain, 0 eaivain, 0 aivamin, 
                0 paivain, 0 epaivain, 0 paivamin, 0 atotal, 0 eatotal, 0 atotmoeda, 0 patotal, 0 epatotal, 0 patotmoeda, 0 dplano, 0 dinoplano, 0 dilnoplano, 0 diaplano, 0 planoonline, 
                '' dostamp, '' pscm, 0 zncm, 0 excm, '' ptcm, '' encm, 0 ntcm, '' pscmdesc, '' znregiao, '' excmdesc, '' ptcmdesc, '' encmdesc, 0 ncin, 0 ncout, 0 usaintra, '' pscmori, '' pscmoridesc, '' series, '' series2, 
                0 despinc, 0 edespinc, 0 eprocesso, '' dprocesso, 0 cambio, 
                CASE WHEN fo.docnome IN ('V/Fatura Recibo','V/Fatura Comissões') THEN CASE 
                    WHEN TPDESC = 'DÉBITO DIRETO' THEN 'Santander  DO' 
                    WHEN TPDESC = 'CARTÃO STD' THEN 'Santander  CARTAO STD' 
                    WHEN TPDESC = 'CC STD' THEN 'Santander  CC STD' 
                    WHEN TPDESC = 'AIRBNB' THEN 'AIRBNB     AIRBNB' 
                    ELSE 'Santander  DO' END
                ELSE '' END AS ollocal, 
                CASE WHEN fo.docnome IN ('V/Fatura Recibo','V/Fatura Comissões') THEN 'B' ELSE 'C' END AS telocal, 
                CASE WHEN fo.docnome IN ('V/Fatura Recibo','V/Fatura Comissões') THEN CASE 
                    WHEN TPDESC = 'DÉBITO DIRETO' THEN 1 
                    WHEN TPDESC = 'CARTÃO STD' THEN 3 
                    WHEN TPDESC = 'CC STD' THEN 4 
                    WHEN TPDESC = 'AIRBNB' THEN 13 
                    ELSE 1 END
                ELSE 1 END AS contado, 
                '' site, '' pnome, 0 pno, '' cxstamp, '' cxusername, '' ssstamp, '' ssusername, '' classe, 0 virs, 0 evirs, 0 txirs, 
                '' lang, 'EURO' moeda2, 0 valorm2, '' arstamp, 0 arno, '' eanfl, 0 ettieca, 0 ttieca, 0 mttieca, 0 iectisento, '' iecacodisen, '' processo, '' subproc, 0 multi, '' crend, 0 introvalacres, '' czonag, 0 sujirsisen, 
                0 exportado, '' identdecexp, 0 nprotri, '' hora, ousrinis, ousrdata, ousrhora, ousrinis AS usrinis, ousrdata AS usrdata, ousrhora AS usrhora, 0 AS marcada
            FROM gestao..fo fo
            WHERE fostamp = @newfo;

            INSERT INTO fn 
            (
                fnstamp, fostamp, ref, design, docnome, adoc, unidade, qtt, epv, tabiva, iva, etiliquido, armazem, cpoc, data, stns, fnccusto, familia, ivaincl, u_dtcusto
            )
            SELECT
                gfn.fnstamp,
                gfn.fostamp,
                gfn.ref,
                gfn.design,
                gfo.docnome,
                gfo.adoc,
                gfn.unidade,
                gfn.qtt,
                gfn.epv,
                gfn.tabiva,
                gfn.taxaiva AS iva,
                gfn.etiliquido,
                1 AS armazem,
                0 AS cpoc,
                gfo.data,
                1 AS stns,
                gfn.fnccusto,
                gfn.familia,
                gfn.ivaincl,
                gfn.dtcusto
            FROM gestao..fn gfn
            JOIN gestao..fo gfo
              ON gfo.fostamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                 gfn.fostamp COLLATE SQL_Latin1_General_CP1_CI_AI
            WHERE gfn.fostamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                  @newfo COLLATE SQL_Latin1_General_CP1_CI_AI
              AND NOT EXISTS (
                    SELECT 1
                    FROM fn x
                    WHERE x.fnstamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                          gfn.fnstamp COLLATE SQL_Latin1_General_CP1_CI_AI
              );

            INSERT INTO fot 
            (
                fotstamp, fostamp, codigo, taxa, ebaseinc, evalor
            )
            SELECT 
                LEFT(NEWID(),25),
                x.fostamp,
                x.codigo,
                x.taxa,
                x.ebaseinc,
                x.evalor
            FROM
            (
                SELECT 
                    fostamp, 
                    tabiva AS codigo, 
                    iva AS taxa, 
                    ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido / (1+(iva/100)) ELSE etiliquido END),2) AS ebaseinc, 
                    ROUND(SUM(CASE WHEN ivaincl = 1 THEN etiliquido - (etiliquido / (1+(iva/100))) ELSE etiliquido * (iva / 100) END),2) AS evalor 
                FROM fn 
                WHERE fostamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                      @newfo COLLATE SQL_Latin1_General_CP1_CI_AI
                GROUP BY fostamp, tabiva, iva
            ) x;

            IF NOT EXISTS (
                SELECT 1
                FROM fo
                WHERE fostamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                      @newfo COLLATE SQL_Latin1_General_CP1_CI_AI
            )
                THROW 51003, 'Falhou integração: FO não existe no PHC.', 1;

            IF NOT EXISTS (
                SELECT 1
                FROM fo2
                WHERE fo2stamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                      @newfo COLLATE SQL_Latin1_General_CP1_CI_AI
            )
                THROW 51004, 'Falhou integração: FO2 não existe no PHC.', 1;

            IF NOT EXISTS (
                SELECT 1
                FROM fn
                WHERE fostamp COLLATE SQL_Latin1_General_CP1_CI_AI =
                      @newfo COLLATE SQL_Latin1_General_CP1_CI_AI
            )
                THROW 51005, 'Falhou integração: FN não tem linhas.', 1;

            UPDATE gestao..fo 
            SET sync = 1,
                sync_erro = 0,
                sync_msg = NULL,
                sync_data = GETDATE()
            WHERE fostamp = @newfo;

            COMMIT;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0
                ROLLBACK;

            SET @erro = ERROR_MESSAGE();

            UPDATE gestao..fo 
            SET sync = 0,
                sync_erro = 1,
                sync_msg = @erro,
                sync_data = GETDATE()
            WHERE fostamp = @newfo;
        END CATCH;

        FETCH NEXT FROM cur INTO @newfo;
    END;

    CLOSE cur;
    DEALLOCATE cur;

    DECLARE @stampfo varchar(25);

    SELECT TOP 1 @stampfo = fostamp 
    FROM GESTAO..fo 
    WHERE etotal = 0 
      AND qr_code > ''
      AND sync = 0
      AND ISNULL(sync_erro, 0) = 0;

    IF ISNULL(@stampfo,'') > ''
        EXEC GESTAO.dbo.sp_FO_ApplyQrCode @stampfo;

    UPDATE ol
       SET ol.[DATA] = fo.PDATA
    FROM dbo.OL ol
    JOIN dbo.FO fo
      ON fo.FOSTAMP = ol.FOSTAMP
    WHERE fo.PDATA IS NOT NULL
      AND NULLIF(LTRIM(RTRIM(ol.FOSTAMP)), '') IS NOT NULL
      AND (ol.[DATA] IS NULL OR ol.[DATA] <> fo.PDATA);
END;
