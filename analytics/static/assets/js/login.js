(function () {
    function setupPasswordToggle() {
        const button = document.getElementById('togglePassword');
        if (!button) return;

        const input = button.parentElement ? button.parentElement.querySelector('input') : null;
        if (!input) return;

        button.addEventListener('click', function () {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            button.textContent = isPassword ? 'Tutup' : 'Lihat';
            button.setAttribute('aria-label', isPassword ? 'Sembunyikan password' : 'Tampilkan password');
        });
    }

    function normalizeAuthInputs() {
        const username = document.querySelector('input[name="username"]');
        const password = document.querySelector('input[name="password"]');

        if (username) {
            username.setAttribute('placeholder', 'Masukkan username');
            username.setAttribute('autocomplete', 'username');
        }

        if (password) {
            password.setAttribute('placeholder', 'Masukkan password');
            password.setAttribute('autocomplete', 'current-password');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        normalizeAuthInputs();
        setupPasswordToggle();
    });
})();
