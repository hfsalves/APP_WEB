SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET XACT_ABORT ON
GO

BEGIN TRY
    BEGIN TRANSACTION;

    ;WITH Traducoes AS
    (
        SELECT * FROM (VALUES
            (N'Tickets', N'Tickets de support'),
            (N'Autos Subempreitada', N'Véhicules de sous-traitance'),
            (N'SAF-T', N'Fichier SAF-T'),
            (N'Frota', N'Flotte'),
            (N'Viaturas', N'Véhicules'),
            (N'Motoristas', N'Chauffeurs'),
            (N'Mecanicos', N'Mécaniciens'),
            (N'Oficina', N'Atelier'),
            (N'Trabalhos pre-definidos', N'Travaux prédéfinis'),
            (N'Planeamento', N'Planification'),
            (N'Obras', N'Chantiers'),
            (N'Equipas', N'Équipes'),
            (N'Encarregados', N'Chefs de chantier'),
            (N'Gestão de Equipas', N'Gestion des équipes'),
            (N'Planeamento Macro', N'Planification macro'),
            (N'Folha Mensal Intersol', N'Feuille mensuelle Intersol'),
            (N'CRM', N'Gestion client (CRM)'),
            (N'Pipeline CRM', N'Pipeline commercial'),
            (N'Menus', N'Gestion des menus'),
            (N'Database Manager', N'Gestionnaire de base de données'),
            (N'Widgets', N'Widgets du tableau de bord'),
            (N'Configuração de Widgets', N'Configuration des widgets'),
            (N'Perfis de Email', N'Profils d''e-mail'),
            (N'DEV SZ-UI', N'Développement SZ-UI'),
            (N'StationZero Amin', N'StationZero Admin'),
            (N'Registos de Produção', N'Enregistrements de production'),
            (N'Registo de Central', N'Registre de centrale'),
            (N'Materiais da Obra', N'Matériaux de chantier'),
            (N'Registo Camião', N'Registre de camion'),
            (N'Registo de Bomba', N'Registre de pompe'),
            (N'Documents AI', N'Documents IA'),
            (N'Inbox', N'Boîte de réception'),
            (N'Colaboradores', N'Collaborateurs'),
            (N'Despesas', N'Dépenses'),
            (N'Marcação de férias', N'Demande de congés'),
            (N'Processamento de Despesas', N'Traitement des dépenses'),
            (N'Recibos', N'Bulletins'),
            (N'Aprovação de férias', N'Approbation des congés')
        ) AS T(TEXTO_BASE, TRADUCAO)
    )
    UPDATE I
    SET TRADUCAO = T.TRADUCAO
    FROM dbo.I18N_TRADUCOES I
    INNER JOIN dbo.MENU M
        ON M.MENUSTAMP = I.ORISTAMP
    INNER JOIN Traducoes T
        ON T.TEXTO_BASE = M.NOME
    WHERE I.ORIGEM = 'MENU'
      AND I.IDIOMA = 'fr'
      AND (LTRIM(RTRIM(ISNULL(I.TRADUCAO, ''))) = '' OR LTRIM(RTRIM(I.TRADUCAO)) = LTRIM(RTRIM(M.NOME)));

    ;WITH Traducoes AS
    (
        SELECT * FROM (VALUES
            (N'Tickets', N'Tickets de support'), (N'Autos Subempreitada', N'Véhicules de sous-traitance'),
            (N'SAF-T', N'Fichier SAF-T'), (N'Frota', N'Flotte'), (N'Viaturas', N'Véhicules'),
            (N'Motoristas', N'Chauffeurs'), (N'Mecanicos', N'Mécaniciens'), (N'Oficina', N'Atelier'),
            (N'Trabalhos pre-definidos', N'Travaux prédéfinis'), (N'Planeamento', N'Planification'),
            (N'Obras', N'Chantiers'), (N'Equipas', N'Équipes'), (N'Encarregados', N'Chefs de chantier'),
            (N'Gestão de Equipas', N'Gestion des équipes'), (N'Planeamento Macro', N'Planification macro'),
            (N'Folha Mensal Intersol', N'Feuille mensuelle Intersol'), (N'CRM', N'Gestion client (CRM)'),
            (N'Pipeline CRM', N'Pipeline commercial'), (N'Menus', N'Gestion des menus'),
            (N'Database Manager', N'Gestionnaire de base de données'), (N'Widgets', N'Widgets du tableau de bord'),
            (N'Configuração de Widgets', N'Configuration des widgets'), (N'Perfis de Email', N'Profils d''e-mail'),
            (N'DEV SZ-UI', N'Développement SZ-UI'), (N'StationZero Amin', N'StationZero Admin'),
            (N'Registos de Produção', N'Enregistrements de production'), (N'Registo de Central', N'Registre de centrale'),
            (N'Materiais da Obra', N'Matériaux de chantier'), (N'Registo Camião', N'Registre de camion'),
            (N'Registo de Bomba', N'Registre de pompe'), (N'Documents AI', N'Documents IA'),
            (N'Inbox', N'Boîte de réception'), (N'Colaboradores', N'Collaborateurs'), (N'Despesas', N'Dépenses'),
            (N'Marcação de férias', N'Demande de congés'), (N'Processamento de Despesas', N'Traitement des dépenses'),
            (N'Recibos', N'Bulletins'), (N'Aprovação de férias', N'Approbation des congés')
        ) AS T(TEXTO_BASE, TRADUCAO)
    )
    INSERT INTO dbo.I18N_TRADUCOES (ORIGEM, ORISTAMP, IDIOMA, TRADUCAO)
    SELECT 'MENU', M.MENUSTAMP, 'fr', T.TRADUCAO
    FROM dbo.MENU M
    INNER JOIN Traducoes T
        ON T.TEXTO_BASE = M.NOME
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.I18N_TRADUCOES I
        WHERE I.ORIGEM = 'MENU'
          AND I.ORISTAMP = M.MENUSTAMP
          AND I.IDIOMA = 'fr'
    );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH
GO
