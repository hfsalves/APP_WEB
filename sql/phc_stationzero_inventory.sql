/*
  P0.1 — Inventário de governação PHC ↔ StationZero
  Executar em cada base PHC, com uma conta apenas de leitura.

  O script não altera dados nem objetos. Guarde cada conjunto de resultados
  com o nome da base e a data de execução.
*/

SET NOCOUNT ON;

/* 1) Contexto e utilizadores/roles que podem escrever. */
SELECT
    DB_NAME() AS database_name,
    @@SERVERNAME AS server_name,
    SUSER_SNAME() AS executed_by,
    SYSDATETIMEOFFSET() AS executed_at;

SELECT
    principal.name AS principal_name,
    principal.type_desc AS principal_type,
    role_principal.name AS database_role
FROM sys.database_role_members membership
INNER JOIN sys.database_principals role_principal
    ON role_principal.principal_id = membership.role_principal_id
INNER JOIN sys.database_principals principal
    ON principal.principal_id = membership.member_principal_id
ORDER BY role_principal.name, principal.name;

SELECT
    principal.name AS principal_name,
    principal.type_desc AS principal_type,
    permission.state_desc,
    permission.permission_name,
    COALESCE(OBJECT_SCHEMA_NAME(permission.major_id), '') AS object_schema,
    COALESCE(OBJECT_NAME(permission.major_id), '') AS object_name
FROM sys.database_permissions permission
INNER JOIN sys.database_principals principal
    ON principal.principal_id = permission.grantee_principal_id
WHERE permission.permission_name IN ('INSERT', 'UPDATE', 'DELETE', 'EXECUTE', 'CONTROL', 'ALTER')
ORDER BY principal.name, permission.permission_name, object_schema, object_name;

/* 2) Triggers ativos e respetiva definição. */
SELECT
    SCHEMA_NAME(parent.schema_id) AS parent_schema,
    parent.name AS parent_table,
    trigger_object.name AS trigger_name,
    trigger_object.is_disabled,
    module.definition
FROM sys.triggers trigger_object
INNER JOIN sys.objects parent
    ON parent.object_id = trigger_object.parent_id
LEFT JOIN sys.sql_modules module
    ON module.object_id = trigger_object.object_id
WHERE trigger_object.is_ms_shipped = 0
ORDER BY parent_schema, parent_table, trigger_object.name;

/* 3) Procedures, funções e views que contêm DML ou chamadas remotas. */
SELECT
    SCHEMA_NAME(object_item.schema_id) AS object_schema,
    object_item.name AS object_name,
    object_item.type_desc,
    object_item.modify_date,
    module.definition
FROM sys.objects object_item
INNER JOIN sys.sql_modules module
    ON module.object_id = object_item.object_id
WHERE object_item.is_ms_shipped = 0
  AND object_item.type IN ('P', 'PC', 'V', 'FN', 'IF', 'TF', 'TR')
  AND (
      module.definition LIKE '%INSERT %'
      OR module.definition LIKE '%UPDATE %'
      OR module.definition LIKE '%DELETE %'
      OR module.definition LIKE '%MERGE %'
      OR module.definition LIKE '%OPENQUERY%'
      OR module.definition LIKE '%EXEC (%'
  )
ORDER BY object_item.type_desc, object_schema, object_name;

/* 4) Objetos PHC a proteger: existência, triggers e permissões explícitas. */
WITH protected_objects AS (
    SELECT object_name
    FROM (VALUES
        ('CL'), ('FL'), ('BO'), ('BO2'), ('BO3'), ('BI'), ('BI2'), ('BOT'),
        ('FO'), ('FO2'), ('FN'), ('FOT'), ('FT'), ('FI'), ('FP'), ('CR'),
        ('ANEXOS'), ('US')
    ) item(object_name)
)
SELECT
    protected.object_name,
    object_item.object_id,
    object_item.modify_date,
    SUM(CASE WHEN trigger_object.object_id IS NOT NULL AND trigger_object.is_disabled = 0 THEN 1 ELSE 0 END) AS enabled_trigger_count
FROM protected_objects protected
LEFT JOIN sys.objects object_item
    ON object_item.name = protected.object_name
   AND object_item.schema_id = SCHEMA_ID('dbo')
   AND object_item.type = 'U'
LEFT JOIN sys.triggers trigger_object
    ON trigger_object.parent_id = object_item.object_id
GROUP BY protected.object_name, object_item.object_id, object_item.modify_date
ORDER BY protected.object_name;

SELECT
    OBJECT_SCHEMA_NAME(permission.major_id) AS object_schema,
    OBJECT_NAME(permission.major_id) AS object_name,
    principal.name AS principal_name,
    permission.state_desc,
    permission.permission_name
FROM sys.database_permissions permission
INNER JOIN sys.database_principals principal
    ON principal.principal_id = permission.grantee_principal_id
WHERE OBJECT_SCHEMA_NAME(permission.major_id) = 'dbo'
  AND OBJECT_NAME(permission.major_id) IN
      ('CL', 'FL', 'BO', 'BO2', 'BO3', 'BI', 'BI2', 'BOT', 'FO', 'FO2', 'FN',
       'FOT', 'FT', 'FI', 'FP', 'CR', 'ANEXOS', 'US')
ORDER BY object_name, principal_name, permission.permission_name;

/* 5) Linked servers visíveis ao utilizador. Permite detetar integrações DB-a-DB.
   Se devolver erro de permissões, esse facto deve constar do levantamento. */
SELECT
    name AS linked_server,
    product,
    provider,
    data_source,
    is_data_access_enabled,
    modify_date
FROM sys.servers
WHERE is_linked = 1
ORDER BY name;
