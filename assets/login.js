document.addEventListener('DOMContentLoaded', () => {
    console.log('[assets/login.js] DOMContentLoaded');
    const form = document.getElementById('loginForm');
    if (!form) {
        console.log('[assets/login.js] loginForm not found');
        return;
    }

    console.log('[assets/login.js] attaching submit handler');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);

        try {
            const res = await fetch(form.action, {
                method: (form.method || 'POST').toUpperCase(),
                body: formData,
                credentials: 'same-origin'
            });

            if (res.redirected) {
                window.location.href = res.url;
                return;
            }

            if (res.ok) {
                // Recarrega a página para exibir mensagens do servidor (cookies, etc.)
                window.location.reload();
                return;
            }

            alert('Login inválido');
        } catch (err) {
            console.error('Erro no login:', err);
            alert('Erro de conexão. Tente novamente.');
        }
    });
});