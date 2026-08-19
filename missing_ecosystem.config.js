module.exports = {
  apps: [
    {
      name: "turtakip-arayuz",
      script: "npm.cmd",
      args: "run dev",
      cwd: "C:\\SUNUCU_PAKETI\\TurTakip_Arayuz\\client"
    },
    {
      name: "redis",
      script: "redis-server.exe",
      args: "redis.windows.conf",
      cwd: "C:\\SUNUCU_PAKETI\\Redis"
    }
  ]
};
