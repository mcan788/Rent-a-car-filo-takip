USE [baysalrentacar];
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[vehicles]') AND name = 'bakim_gonderen')
BEGIN
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gonderen] NVARCHAR(100) DEFAULT '';
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_km] INT DEFAULT 0;
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[services]') AND name = 'gidis_tarihi')
BEGIN
    ALTER TABLE [dbo].[services] ADD [gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
GO

USE [deneme];
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[vehicles]') AND name = 'bakim_gonderen')
BEGIN
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gonderen] NVARCHAR(100) DEFAULT '';
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_km] INT DEFAULT 0;
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[services]') AND name = 'gidis_tarihi')
BEGIN
    ALTER TABLE [dbo].[services] ADD [gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
GO

USE [rentacardemo];
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[vehicles]') AND name = 'bakim_gonderen')
BEGIN
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gonderen] NVARCHAR(100) DEFAULT '';
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_km] INT DEFAULT 0;
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[services]') AND name = 'gidis_tarihi')
BEGIN
    ALTER TABLE [dbo].[services] ADD [gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
GO

USE [www];
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[vehicles]') AND name = 'bakim_gonderen')
BEGIN
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gonderen] NVARCHAR(100) DEFAULT '';
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_km] INT DEFAULT 0;
    ALTER TABLE [dbo].[vehicles] ADD [bakim_gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[services]') AND name = 'gidis_tarihi')
BEGIN
    ALTER TABLE [dbo].[services] ADD [gidis_tarihi] NVARCHAR(20) DEFAULT '';
END
GO
