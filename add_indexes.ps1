$dbs = Invoke-Sqlcmd -Query 'SELECT name FROM sys.databases WHERE database_id > 4' -ServerInstance '.\SQLEXPRESS'
$query = "
IF EXISTS(SELECT * FROM sys.tables WHERE name='rentals') 
BEGIN 
    IF NOT EXISTS(SELECT * FROM sys.indexes WHERE name='idx_rentals_alinistaKm' AND object_id = OBJECT_ID('rentals'))
        CREATE NONCLUSTERED INDEX idx_rentals_alinistaKm ON rentals(alinistaKm);
    
    IF NOT EXISTS(SELECT * FROM sys.indexes WHERE name='idx_rentals_kabis_kiralama' AND object_id = OBJECT_ID('rentals'))
        CREATE NONCLUSTERED INDEX idx_rentals_kabis_kiralama ON rentals(kabis_kiralama_status);

    IF NOT EXISTS(SELECT * FROM sys.indexes WHERE name='idx_rentals_kabis_teslim' AND object_id = OBJECT_ID('rentals'))
        CREATE NONCLUSTERED INDEX idx_rentals_kabis_teslim ON rentals(kabis_teslim_status);
END"

foreach ($row in $dbs) {
    $db = $row.name
    Write-Host "Indexing ${db}..."
    try {
        Invoke-Sqlcmd -Query $query -Database $db -ServerInstance ".\SQLEXPRESS" -ErrorAction Stop
    } catch {
        Write-Host "Failed for ${db}: $_"
    }
}
