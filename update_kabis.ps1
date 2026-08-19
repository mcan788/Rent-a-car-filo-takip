$dbs = @('www', 'rentacardemo', 'fuglarentacar', 'melisturizm', 'yadelrentacar', 'baysalrentacar', 'zyronova')
$query = "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('rentals') AND name = 'kabis_kiralama_status') BEGIN ALTER TABLE rentals ADD kabis_kiralama_status NVARCHAR(20) DEFAULT 'bekliyor'; ALTER TABLE rentals ADD kabis_kiralama_hata NVARCHAR(MAX) NULL; ALTER TABLE rentals ADD kabis_teslim_status NVARCHAR(20) DEFAULT 'bekliyor'; ALTER TABLE rentals ADD kabis_teslim_hata NVARCHAR(MAX) NULL; END"

foreach ($db in $dbs) {
    Write-Host "Updating $db..."
    Invoke-Sqlcmd -Query $query -Database $db -ServerInstance ".\SQLEXPRESS"
}
