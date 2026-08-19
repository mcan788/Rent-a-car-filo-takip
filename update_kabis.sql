DECLARE @db_name NVARCHAR(255);
DECLARE @sql NVARCHAR(MAX);
DECLARE db_cursor CURSOR FOR 
SELECT name FROM sys.databases WHERE name IN ('www', 'rentacardemo', 'fuglarentacar', 'melisturizm', 'yadelrentacar', 'baysalrentacar', 'zyronova');

OPEN db_cursor;
FETCH NEXT FROM db_cursor INTO @db_name;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = 'USE [' + @db_name + ']; ' +
               'IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(''rentals'') AND name = ''kabis_kiralama_status'') ' +
               'BEGIN ' +
               'ALTER TABLE rentals ADD kabis_kiralama_status NVARCHAR(20) DEFAULT ''bekliyor''; ' +
               'ALTER TABLE rentals ADD kabis_kiralama_hata NVARCHAR(MAX) NULL; ' +
               'ALTER TABLE rentals ADD kabis_teslim_status NVARCHAR(20) DEFAULT ''bekliyor''; ' +
               'ALTER TABLE rentals ADD kabis_teslim_hata NVARCHAR(MAX) NULL; ' +
               'END';
    EXEC sp_executesql @sql;
    FETCH NEXT FROM db_cursor INTO @db_name;
END

CLOSE db_cursor;
DEALLOCATE db_cursor;
