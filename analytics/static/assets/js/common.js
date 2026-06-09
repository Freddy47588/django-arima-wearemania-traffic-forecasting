(function () {
    const body = document.body;
    const menuButton = document.querySelector('.mobile-menu-btn');
    const closeButton = document.querySelector('.sidebar-close');
    const overlay = document.querySelector('.sidebar-overlay');

    function openSidebar() {
        body.classList.add('sidebar-open');
        if (menuButton) {
            menuButton.setAttribute('aria-expanded', 'true');
            const menuText = menuButton.querySelector('.mobile-menu-text');
            if (menuText) {
                menuText.textContent = 'Tutup';
            }
        }
    }

    function closeSidebar() {
        body.classList.remove('sidebar-open');
        if (menuButton) {
            menuButton.setAttribute('aria-expanded', 'false');
            const menuText = menuButton.querySelector('.mobile-menu-text');
            if (menuText) {
                menuText.textContent = 'Menu';
            }
        }
    }

    function toggleSidebar() {
        if (body.classList.contains('sidebar-open')) {
            closeSidebar();
            return;
        }

        openSidebar();
    }

    if (menuButton) {
        menuButton.addEventListener('click', toggleSidebar);
    }

    if (closeButton) {
        closeButton.addEventListener('click', closeSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    document.querySelectorAll('.sidebar a').forEach(function (link) {
        link.addEventListener('click', function () {
            closeSidebar();
        });
    });

    window.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });
})();
