const sql = require('mssql');
require('dotenv').config({ path: 'c:\\Users\\MCAN\\Desktop\\Masa Üstü Ana Klasör\\Proje Dosyaları\\Proje kod dosyaları\\Rent A Car - Tur Takip\\tur_takip_otomasyonu\\server\\.env' });

async function check() {
    try {
        const pool = await sql.connect(process.env.TUR_MASTER_DB_URI);
        const res1 = await pool.request().query("SELECT Username, Role FROM SystemUsers WHERE Username = 'Enes_d'");
        console.log("SystemUsers:", res1.recordset);
        
        const res2 = await pool.request().query("SELECT Username, Role FROM Staff WHERE Username = 'Enes_d'");
        console.log("Staff:", res2.recordset);
        
        process.exit(0);
    } catch(e) {
        console.error(e);
        process.exit(1);
    }
}
check();
