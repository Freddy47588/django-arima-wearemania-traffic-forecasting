(function () {
    const body = document.body;
    const menuButton = document.querySelector('.mobile-menu-btn');
    const closeButton = document.querySelector('.sidebar-close');
    const overlay = document.querySelector('.sidebar-overlay');

    function openSidebar() {
        body.classList.add('sidebar-open');
        if (menuButton) {
            menuButton.setAttribute('aria-expanded', 'true');
        }
    }

    function closeSidebar() {
        body.classList.remove('sidebar-open');
        if (menuButton) {
            menuButton.setAttribute('aria-expanded', 'false');
        }
    }

    if (menuButton) {
        menuButton.addEventListener('click', openSidebar);
    }

    if (closeButton) {
        closeButton.addEventListener('click', closeSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    window.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });
})();
