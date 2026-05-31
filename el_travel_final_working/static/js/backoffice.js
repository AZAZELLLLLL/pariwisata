/**
 * EL Travel Backoffice — sidebar, user menu, global search
 */
(function () {
    'use strict';

    function initSidebar() {
        const shell = document.querySelector('.bo-shell, .backoffice-shell');
        if (!shell) return;

        const sidebar = shell.querySelector('.bo-sidebar, .backoffice-sidebar');
        const hamburger = document.getElementById('boHamburger');
        let overlay = document.querySelector('.bo-overlay');

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'bo-overlay';
            overlay.setAttribute('aria-hidden', 'true');
            document.body.appendChild(overlay);
        }

        function closeSidebar() {
            if (sidebar) {
                sidebar.classList.remove('is-open', 'active');
            }
            overlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        }

        function openSidebar() {
            if (sidebar) {
                sidebar.classList.add('is-open', 'active');
            }
            overlay.classList.add('is-visible');
            document.body.style.overflow = 'hidden';
        }

        function toggleSidebar() {
            if (sidebar && sidebar.classList.contains('is-open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        }

        if (hamburger) {
            hamburger.addEventListener('click', toggleSidebar);
        }

        overlay.addEventListener('click', closeSidebar);

        window.addEventListener('resize', () => {
            if (window.innerWidth >= 1024) {
                closeSidebar();
            }
        });

        sidebar?.querySelectorAll('.bo-nav-item, .backoffice-nav a').forEach((link) => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 1024) {
                    closeSidebar();
                }
            });
        });
    }

    function initUserMenu() {
        const chip = document.getElementById('boUserChip');
        const dropdown = document.getElementById('boUserDropdown');
        if (!chip || !dropdown) return;

        chip.addEventListener('click', (event) => {
            event.stopPropagation();
            dropdown.classList.toggle('is-open');
            chip.setAttribute('aria-expanded', dropdown.classList.contains('is-open'));
        });

        document.addEventListener('click', () => {
            dropdown.classList.remove('is-open');
            chip.setAttribute('aria-expanded', 'false');
        });
    }

    function initGlobalSearch() {
        const form = document.getElementById('boGlobalSearch');
        if (!form) return;

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const input = form.querySelector('input[name="q"]');
            const query = (input?.value || '').trim();
            const base = form.getAttribute('data-orders-url') || '/backoffice/pesanan';
            const url = query ? `${base}?q=${encodeURIComponent(query)}` : base;
            window.location.href = url;
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initSidebar();
        initUserMenu();
        initGlobalSearch();
    });
})();
