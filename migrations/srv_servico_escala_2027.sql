SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @WeekStart date = '2026-10-26';
    DECLARE @LastWeekStart date = '2027-12-27';
    DECLARE @Cycle int = 0;
    DECLARE @DayOffset int;
    DECLARE @User varchar(50);
    DECLARE @ServiceDate date;

    WHILE @WeekStart <= @LastWeekStart
    BEGIN
        SET @User = CASE (@Cycle % 3)
            WHEN 0 THEN 'rosa'
            WHEN 1 THEN 'elisabete'
            ELSE 'maria'
        END;

        SET @DayOffset = 0;
        WHILE @DayOffset < 7
        BEGIN
            SET @ServiceDate = DATEADD(day, @DayOffset, @WeekStart);

            IF NOT EXISTS (
                SELECT 1
                FROM dbo.SRV
                WHERE CAST(DATA AS date) = @ServiceDate
                  AND ISNULL(ATIVO, 0) = 1
                  AND FEID IS NULL
            )
            BEGIN
                INSERT INTO dbo.SRV
                    (DATA, UTILIZADOR, FEID, USERCRIACAO, USERALTERACAO)
                VALUES
                    (@ServiceDate, @User, NULL, 'MIGRATION', 'MIGRATION');
            END;

            SET @DayOffset += 1;
        END;

        SET @WeekStart = DATEADD(day, 7, @WeekStart);
        SET @Cycle += 1;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
