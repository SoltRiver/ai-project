(function() {
    const root = document.documentElement;
    const saved = localStorage.getItem('theme');
    if (saved) {
        root.setAttribute('data-theme', saved);
    }
    const toggle = document.querySelector('[data-action="toggle-theme"]');
    const apply = (theme) => {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    };
    if (toggle) {
        toggle.addEventListener('click', () => {
            const current = root.getAttribute('data-theme') || 'light';
            apply(current === 'light' ? 'dark' : 'light');
        });
    }
})();
