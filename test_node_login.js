const fetch = require('node-fetch');

async function testLogin() {
    try {
        const response = await fetch('http://localhost:5000/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: 'Enes_d', password: '123' }) // We don't know the password, but wait
        });
        const text = await response.text();
        console.log("Response:", text);
    } catch (e) {
        console.error(e);
    }
}
testLogin();
