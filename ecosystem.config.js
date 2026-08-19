module.exports = {
  apps : [{
    name   : "redis",
    script : "redis-server.exe",
    cwd    : "C:\\SUNUCU_PAKETI\\Redis"
  }, {
    name   : "rentacar-backend",
    script : "serve.py",
    cwd    : "C:\\SUNUCU_PAKETI\\RentACar_Sistem",
    interpreter: "python"
  }, {
    name   : "turtakip-api",
    script : "index.js",
    cwd    : "C:\\SUNUCU_PAKETI\\TurTakip_API"
  }, {
    name   : "turtakip-arayuz",
    script : "serve",
    env: {
      PM2_SERVE_PATH: "C:\\SUNUCU_PAKETI\\TurTakip_Arayuz\\client\\dist",
      PM2_SERVE_PORT: 5173,
      PM2_SERVE_SPA: "true"
    }
  }]
}
