$dbs = Invoke-Sqlcmd -Query 'SELECT name FROM sys.databases WHERE database_id > 4' -ServerInstance '.\SQLEXPRESS'
$query = "IF EXISTS(SELECT * FROM sys.tables WHERE name='rentals') AND NOT EXISTS(SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('rentals') AND name = 'kabis_kiralama_status') BEGIN ALTER TABLE rentals ADD kabis_kiralama_status NVARCHAR(20) DEFAULT 'bekliyor'; ALTER TABLE rentals ADD kabis_kiralama_hata NVARCHAR(MAX) NULL; ALTER TABLE rentals ADD kabis_teslim_status NVARCHAR(20) DEFAULT 'bekliyor'; ALTER TABLE rentals ADD kabis_teslim_hata NVARCHAR(MAX) NULL; END"

foreach ($row in $dbs) {
    $db = $row.name
    Write-Host "Updating ${db}..."
    try {
        Invoke-Sqlcmd -Query $query -Database $db -ServerInstance ".\SQLEXPRESS" -ErrorAction Stop
    } catch {
        Write-Host "Failed for ${db}: $_"
    }
}
