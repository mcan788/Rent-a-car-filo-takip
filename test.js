fetch('http://127.0.0.1:8080/api/auth/login?username=deneme&password=123')
  .then(r => r.text())
  .then(t => console.log(t.substring(0, 100)))
  .catch(console.error);
