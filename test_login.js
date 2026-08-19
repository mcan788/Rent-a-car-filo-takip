async function testLogin() {
    try {
        const response = await fetch('http://localhost:5000/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: 'personel_alanya',
                password: '123'
            })
        });
        const data = await response.json();
        console.log("LOGIN SUCCESS:", data);
    } catch (err) {
        console.error("LOGIN ERROR:", err);
    }
}

testLogin();
