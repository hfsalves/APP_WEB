SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AGORA DATETIME2(3) = SYSUTCDATETIME();

    DECLARE @FAMILIAS TABLE
    (
        CODIGO      NVARCHAR(50) NOT NULL,
        NOME        NVARCHAR(100) NOT NULL,
        TITULO      NVARCHAR(150) NULL,
        DESCRICAO   NVARCHAR(500) NULL,
        ORDEM       INT NOT NULL,
        ATIVO       BIT NOT NULL
    );

    INSERT INTO @FAMILIAS (CODIGO, NOME, TITULO, DESCRICAO, ORDEM, ATIVO)
    VALUES
        (N'MAIS_POPULARES', N'Mais populares', N'Mais populares', N'Selecao de artigos com maior procura para chegada.', 10, 1),
        (N'PEQUENO_ALMOCO', N'Pequeno almoco', N'Pequeno almoco', N'Essenciais para um pequeno-almoco completo a chegada.', 20, 1),
        (N'MERCEARIA', N'Mercearia', N'Mercearia', N'Produtos base para cozinha e despensa.', 30, 1),
        (N'BEBIDAS', N'Bebidas', N'Bebidas', N'Bebidas frescas, agua, vinho e mixers.', 40, 1),
        (N'HIGIENE_PESSOAL', N'Higiene pessoal', N'Higiene pessoal', N'Artigos de higiene e conveniencia pessoal.', 50, 1),
        (N'SURPRESAS', N'Surpresas', N'Surpresas', N'Pequenos mimos para tornar a estadia especial.', 60, 1),
        (N'UTILITARIOS', N'Utilitarios', N'Utilitarios', N'Itens praticos para apoio a estadia.', 70, 1),
        (N'ADULT_MATERIAL', N'Adult material', N'Adult material', N'Artigos discretos de bem-estar intimo para adultos.', 80, 1);

    UPDATE F
       SET F.NOME = S.NOME,
           F.TITULO = S.TITULO,
           F.DESCRICAO = S.DESCRICAO,
           F.ORDEM = S.ORDEM,
           F.ATIVO = S.ATIVO,
           F.ALTERADO_EM = @AGORA
      FROM dbo.SHOP_FAMILIAS AS F
      INNER JOIN @FAMILIAS AS S
              ON S.CODIGO = F.CODIGO;

    INSERT INTO dbo.SHOP_FAMILIAS
    (
        CODIGO,
        NOME,
        TITULO,
        DESCRICAO,
        ORDEM,
        ATIVO,
        CRIADO_EM,
        ALTERADO_EM
    )
    SELECT
        S.CODIGO,
        S.NOME,
        S.TITULO,
        S.DESCRICAO,
        S.ORDEM,
        S.ATIVO,
        @AGORA,
        @AGORA
    FROM @FAMILIAS AS S
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.SHOP_FAMILIAS AS F
        WHERE F.CODIGO = S.CODIGO
    );

    DECLARE @PRODUTOS TABLE
    (
        CODIGO              NVARCHAR(50) NOT NULL,
        FAMILIA_CODIGO      NVARCHAR(50) NOT NULL,
        NOME                NVARCHAR(150) NOT NULL,
        TITULO              NVARCHAR(200) NULL,
        SUBTITULO           NVARCHAR(200) NULL,
        DESCRICAO_CURTA     NVARCHAR(500) NULL,
        DESCRICAO           NVARCHAR(MAX) NULL,
        PRECO               DECIMAL(19,4) NOT NULL,
        ORDEM               INT NOT NULL,
        ATIVO               BIT NOT NULL
    );

    INSERT INTO @PRODUTOS
    (
        CODIGO,
        FAMILIA_CODIGO,
        NOME,
        TITULO,
        SUBTITULO,
        DESCRICAO_CURTA,
        DESCRICAO,
        PRECO,
        ORDEM,
        ATIVO
    )
    VALUES
        (N'POP_AGUA_6X33', N'MAIS_POPULARES', N'Agua mineral 6x33cl', N'Pack agua mineral', N'Pack compacto para chegada', N'Seis garrafas de agua mineral natural de 33cl.', N'Ideal para ter agua fresca disponivel logo a chegada ao alojamento.', 2.90, 10, 1),
        (N'POP_LEITE_PAO', N'MAIS_POPULARES', N'Kit leite e pao', N'Leite e pao fresco', N'Basico para primeira manha', N'Leite meio-gordo e pao de forma prontos a consumir.', N'Combina dois essenciais para quem chega tarde e quer pequeno-almoco assegurado.', 3.80, 20, 1),
        (N'POP_CAFE_CAPS', N'MAIS_POPULARES', N'Capsulas de cafe x10', N'Cafe em capsulas', N'Compativel Nespresso', N'Caixa com dez capsulas de cafe torrado e moido.', N'Cafe pratico para uma primeira pausa apos check-in.', 4.50, 30, 1),
        (N'POP_VINHO_TINTO', N'MAIS_POPULARES', N'Vinho tinto regional 75cl', N'Garrafa de vinho tinto', N'Selecao regional', N'Vinho tinto portugues de perfil suave e facil.', N'Boa opcao para receber os hospedes com um toque local.', 7.90, 40, 1),
        (N'POP_CHIPS_SNACK', N'MAIS_POPULARES', N'Batatas fritas gourmet', N'Snack salgado', N'Embalagem familiar', N'Batatas fritas crocantes em embalagem partilhavel.', N'Snack rapido para relaxar apos a viagem.', 2.40, 50, 1),
        (N'POP_HIGIENE_SET', N'MAIS_POPULARES', N'Kit higiene express', N'Kit basico de higiene', N'Escova, pasta e gel', N'Conjunto com essenciais de higiene pessoal.', N'Pensado para chegadas com bagagem reduzida ou esquecimentos de ultima hora.', 5.90, 60, 1),

        (N'PA_LEITE_1L', N'PEQUENO_ALMOCO', N'Leite meio-gordo 1L', N'Leite meio-gordo', N'Formato familiar', N'Leite UHT meio-gordo pronto a consumir.', N'Essencial para pequeno-almoco, cafe ou cereais.', 1.35, 10, 1),
        (N'PA_OVOS_6', N'PEQUENO_ALMOCO', N'Ovos classe M x6', N'Caixa de 6 ovos', N'Origem nacional', N'Caixa com seis ovos frescos classe M.', N'Perfeito para ovos mexidos, omeletes ou cozidos.', 2.10, 20, 1),
        (N'PA_PAO_FORMA', N'PEQUENO_ALMOCO', N'Pao de forma integral', N'Pao de forma', N'Fatiado e versatil', N'Pao de forma integral fatiado.', N'Uma base pratica para torradas ou sandes de pequeno-almoco.', 1.95, 30, 1),
        (N'PA_MANTEIGA_250', N'PEQUENO_ALMOCO', N'Manteiga 250g', N'Manteiga tradicional', N'Bloco refrigerado', N'Manteiga tradicional com sal em bloco de 250g.', N'Ideal para barrar torradas ou cozinhar.', 2.45, 40, 1),
        (N'PA_COMPOTA_30', N'PEQUENO_ALMOCO', N'Compota de morango 30g x4', N'Dose individual', N'Quatro doses prontas', N'Conjunto com quatro doses individuais de compota de morango.', N'Formato pratico para pequeno-almoco sem desperdicio.', 2.20, 50, 1),
        (N'PA_CEREAIS_375', N'PEQUENO_ALMOCO', N'Cereais crocantes 375g', N'Cereais de pequeno-almoco', N'Formato standard', N'Cereais crocantes para servir com leite ou iogurte.', N'Opcao simples e rapida para adultos e criancas.', 3.25, 60, 1),

        (N'MER_ARROZ_1KG', N'MERCEARIA', N'Arroz agulha 1kg', N'Arroz agulha', N'Embalagem 1kg', N'Arroz agulha de grao longo para refeicoes do dia a dia.', N'Ingrediente base para varias refeicoes no alojamento.', 2.10, 10, 1),
        (N'MER_MASSA_500', N'MERCEARIA', N'Massa esparguete 500g', N'Esparguete', N'Formato classico', N'Massa esparguete de trigo duro em embalagem de 500g.', N'Facil de preparar e util para refeicoes rapidas.', 1.45, 20, 1),
        (N'MER_ATUM_3X', N'MERCEARIA', N'Atum em azeite x3', N'Pack de 3 latas', N'Conserva pronta a usar', N'Tres latas de atum em azeite.', N'Boa base para saladas, massas ou refeicoes leves.', 3.90, 30, 1),
        (N'MER_AZEITE_75', N'MERCEARIA', N'Azeite virgem extra 75cl', N'Azeite virgem extra', N'Garrafa vidro', N'Azeite portugues virgem extra para temperar e cozinhar.', N'Produto essencial na cozinha e com perfil local.', 6.90, 40, 1),
        (N'MER_SAL_1KG', N'MERCEARIA', N'Sal fino 1kg', N'Sal alimentar', N'Formato 1kg', N'Sal fino alimentar em embalagem de 1kg.', N'Essencial para preparacao basica de refeicoes.', 0.85, 50, 1),
        (N'MER_ACUCAR_1KG', N'MERCEARIA', N'Acucar branco 1kg', N'Acucar branco', N'Formato 1kg', N'Acucar branco em embalagem familiar.', N'Indicado para cafe, cha e preparacoes simples.', 1.20, 60, 1),

        (N'BEB_AGUA_1L5', N'BEBIDAS', N'Agua mineral 1.5L', N'Agua mineral', N'Garrafa grande', N'Agua mineral natural em garrafa de 1.5L.', N'Solucao pratica para o dia a dia da estadia.', 1.10, 10, 1),
        (N'BEB_SUMO_LARANJA', N'BEBIDAS', N'Sumo de laranja 1L', N'Sumo refrigerado', N'Pronto a beber', N'Sumo de laranja em embalagem de 1 litro.', N'Ideal para pequeno-almoco ou lanche.', 2.30, 20, 1),
        (N'BEB_REFRIG_COLA', N'BEBIDAS', N'Refrigerante cola 1.5L', N'Refrigerante cola', N'Formato familiar', N'Refrigerante de cola em garrafa de 1.5L.', N'Boa opcao para acompanhar refeicoes ou snacks.', 2.60, 30, 1),
        (N'BEB_CERVEJA_6X', N'BEBIDAS', N'Cerveja lager x6', N'Pack cerveja', N'Seis unidades 33cl', N'Pack com seis garrafas de cerveja lager 33cl.', N'Pratico para uma rececao descontraida a chegada.', 5.50, 40, 1),
        (N'BEB_VINHO_BRANCO', N'BEBIDAS', N'Vinho branco 75cl', N'Garrafa vinho branco', N'Selecao regional', N'Vinho branco portugues fresco e leve.', N'Opcao versatil para aperitivo ou jantar.', 7.90, 50, 1),
        (N'BEB_TONICA_4X', N'BEBIDAS', N'Agua tonica x4', N'Pack tonica', N'Quatro garrafas 20cl', N'Conjunto de quatro garrafas de agua tonica.', N'Ideal para servir com gelo ou como mixer.', 3.40, 60, 1),

        (N'HIG_GEL_BANHO', N'HIGIENE_PESSOAL', N'Gel de banho 250ml', N'Gel de banho', N'Fragrancia neutra', N'Gel de banho suave para uso diario.', N'Boa opcao para estadias curtas ou esquecimentos de bagagem.', 3.20, 10, 1),
        (N'HIG_CHAMPO_250', N'HIGIENE_PESSOAL', N'Champo 250ml', N'Champo uso frequente', N'Formato standard', N'Champo suave para uso frequente.', N'Essencial de higiene pessoal para a estadia.', 3.40, 20, 1),
        (N'HIG_ESCOVA_PASTA', N'HIGIENE_PESSOAL', N'Escova e pasta dentes', N'Kit oral', N'Pronto a usar', N'Escova de dentes e pasta dentifrica de viagem.', N'Solucao rapida para chegadas imprevistas.', 2.95, 30, 1),
        (N'HIG_GILETE_2X', N'HIGIENE_PESSOAL', N'Gillette descartavel x2', N'Laminas descartaveis', N'Pack com duas unidades', N'Duas laminas descartaveis para barbear.', N'Item util para quem viajou sem necessaire completa.', 1.95, 40, 1),
        (N'HIG_DESOD_150', N'HIGIENE_PESSOAL', N'Desodorizante spray 150ml', N'Desodorizante', N'Formato 150ml', N'Desodorizante spray de uso diario.', N'Pratico para reforcar o conforto durante a estadia.', 3.90, 50, 1),
        (N'HIG_PENSOS_10', N'HIGIENE_PESSOAL', N'Pensos diarios x10', N'Pensos diarios', N'Embalagem compacta', N'Embalagem com dez pensos diarios.', N'Item de conveniencia para necessidades imediatas.', 2.10, 60, 1),

        (N'SUR_BALOES_SET', N'SURPRESAS', N'Kit baloes decorativos', N'Decoracao simples', N'Conjunto pronto a montar', N'Conjunto de baloes e fita para pequena surpresa.', N'Ideal para preparar um gesto especial sem complicacoes.', 4.90, 10, 1),
        (N'SUR_VELAS_6', N'SURPRESAS', N'Velas aromaticas x6', N'Conjunto de velas', N'Aroma suave', N'Seis velas aromaticas de ambiente.', N'Ajuda a criar um ambiente acolhedor no alojamento.', 6.50, 20, 1),
        (N'SUR_CHOCOLATE_BOX', N'SURPRESAS', N'Caixa mini chocolates', N'Caixa de chocolates', N'Selecao premium', N'Caixa com selecao de pequenos chocolates.', N'Mimo simples para surpreender quem chega.', 5.80, 30, 1),
        (N'SUR_FLORES_SECAS', N'SURPRESAS', N'Arranjo flores secas', N'Decoracao floral', N'Pequeno arranjo', N'Pequeno arranjo decorativo de flores secas.', N'Adiciona um toque visual elegante e duradouro.', 9.50, 40, 1),
        (N'SUR_CARTAO_WELCOME', N'SURPRESAS', N'Cartao welcome', N'Cartao de boas-vindas', N'Mensagem curta', N'Cartao simples com mensagem de boas-vindas.', N'Detalhe discreto para personalizar a rececao.', 1.50, 50, 1),
        (N'SUR_PROSECCO_20', N'SURPRESAS', N'Espumante mini 20cl', N'Mini espumante', N'Garrafa individual', N'Garrafa individual de espumante seco.', N'Perfeito para celebrar um momento especial na chegada.', 4.70, 60, 1),

        (N'UTI_GUARDA_CHUVA', N'UTILITARIOS', N'Guarda-chuva compacto', N'Guarda-chuva', N'Dobravel', N'Guarda-chuva compacto e leve.', N'Util para dias de chuva sem necessidade de comprar fora.', 7.50, 10, 1),
        (N'UTI_CARREGADOR_USB', N'UTILITARIOS', N'Carregador USB duplo', N'Carregador USB', N'2 portas', N'Carregador de tomada com duas portas USB.', N'Ajuda a resolver esquecimentos frequentes de viagem.', 8.90, 20, 1),
        (N'UTI_CABO_USB_C', N'UTILITARIOS', N'Cabo USB-C 1m', N'Cabo carregamento', N'Compativel USB-C', N'Cabo USB-C para carregamento e dados.', N'Artigo pratico para smartphones e dispositivos recentes.', 4.90, 30, 1),
        (N'UTI_PILHAS_AA_4', N'UTILITARIOS', N'Pilhas AA x4', N'Pack pilhas AA', N'Quatro unidades', N'Conjunto com quatro pilhas AA alcalinas.', N'Pode ser util para equipamentos pequenos e comandos.', 3.60, 40, 1),
        (N'UTI_SACO_LAVANDARIA', N'UTILITARIOS', N'Saco lavandaria', N'Saco reutilizavel', N'Formato medio', N'Saco reutilizavel para roupa ou lavandaria.', N'Ajuda a organizar a bagagem durante a estadia.', 2.80, 50, 1),
        (N'UTI_KIT_COSTURA', N'UTILITARIOS', N'Kit costura viagem', N'Kit costura', N'Compacto', N'Pequeno kit com linha, agulha e botoes.', N'Solucao rapida para pequenos imprevistos de roupa.', 2.40, 60, 1),

        (N'ADU_PRESERV_12', N'ADULT_MATERIAL', N'Preservativos x12', N'Caixa preservativos', N'Pack de 12 unidades', N'Caixa com doze preservativos.', N'Artigo discreto de bem-estar intimo para adultos.', 8.90, 10, 1),
        (N'ADU_LUBR_100', N'ADULT_MATERIAL', N'Lubrificante 100ml', N'Lubrificante base agua', N'Formato 100ml', N'Lubrificante intimo de base aquosa em embalagem discreta.', N'Pensado para conforto e bem-estar de adultos.', 9.50, 20, 1),
        (N'ADU_MASSAGEM_100', N'ADULT_MATERIAL', N'Oleo de massagem 100ml', N'Oleo de massagem', N'Aroma neutro', N'Oleo corporal de massagem com aroma suave.', N'Opcao discreta para relaxamento e ambiente mais intimista.', 11.90, 30, 1),
        (N'ADU_VELA_MASSAGEM', N'ADULT_MATERIAL', N'Vela de massagem', N'Vela aromatica', N'Ritual de relaxamento', N'Vela de massagem com fragancia suave.', N'Combina ambiente acolhedor e experiencia sensorial.', 12.90, 40, 1),
        (N'ADU_KIT_BEM_ESTAR', N'ADULT_MATERIAL', N'Kit bem-estar adulto', N'Kit discreto', N'Essenciais selecionados', N'Kit com selecao de artigos de bem-estar para adultos.', N'Conjunto pratico e discreto para maior conveniencia.', 18.50, 50, 1),
        (N'ADU_GEL_AQUEC_50', N'ADULT_MATERIAL', N'Gel aquecimento 50ml', N'Gel efeito aquecimento', N'Formato compacto', N'Gel intimo com efeito aquecimento em embalagem discreta.', N'Artigo de bem-estar para adultos, pensado para uso responsavel.', 10.90, 60, 1);

    ;WITH PRODUTOS_SOURCE AS
    (
        SELECT
            P.CODIGO,
            F.FAMILIA_ID,
            P.NOME,
            P.TITULO,
            P.SUBTITULO,
            P.DESCRICAO_CURTA,
            P.DESCRICAO,
            P.PRECO,
            P.ORDEM,
            P.ATIVO
        FROM @PRODUTOS AS P
        INNER JOIN dbo.SHOP_FAMILIAS AS F
                ON F.CODIGO = P.FAMILIA_CODIGO
    )
    UPDATE PR
       SET PR.FAMILIA_ID = S.FAMILIA_ID,
           PR.NOME = S.NOME,
           PR.TITULO = S.TITULO,
           PR.SUBTITULO = S.SUBTITULO,
           PR.DESCRICAO_CURTA = S.DESCRICAO_CURTA,
           PR.DESCRICAO = S.DESCRICAO,
           PR.PRECO = S.PRECO,
           PR.ORDEM = S.ORDEM,
           PR.ATIVO = S.ATIVO,
           PR.ALTERADO_EM = @AGORA
      FROM dbo.SHOP_PRODUTOS AS PR
      INNER JOIN PRODUTOS_SOURCE AS S
              ON S.CODIGO = PR.CODIGO;

    ;WITH PRODUTOS_SOURCE AS
    (
        SELECT
            P.CODIGO,
            F.FAMILIA_ID,
            P.NOME,
            P.TITULO,
            P.SUBTITULO,
            P.DESCRICAO_CURTA,
            P.DESCRICAO,
            P.PRECO,
            P.ORDEM,
            P.ATIVO
        FROM @PRODUTOS AS P
        INNER JOIN dbo.SHOP_FAMILIAS AS F
                ON F.CODIGO = P.FAMILIA_CODIGO
    )
    INSERT INTO dbo.SHOP_PRODUTOS
    (
        FAMILIA_ID,
        CODIGO,
        NOME,
        TITULO,
        SUBTITULO,
        DESCRICAO_CURTA,
        DESCRICAO,
        PRECO,
        MOEDA,
        ORDEM,
        ATIVO,
        CRIADO_EM,
        ALTERADO_EM
    )
    SELECT
        S.FAMILIA_ID,
        S.CODIGO,
        S.NOME,
        S.TITULO,
        S.SUBTITULO,
        S.DESCRICAO_CURTA,
        S.DESCRICAO,
        S.PRECO,
        N'EUR',
        S.ORDEM,
        S.ATIVO,
        @AGORA,
        @AGORA
    FROM PRODUTOS_SOURCE AS S
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.SHOP_PRODUTOS AS PR
        WHERE PR.CODIGO = S.CODIGO
    );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
