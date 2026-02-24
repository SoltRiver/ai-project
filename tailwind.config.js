/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/js/**/*.js",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                brand: {
                    accent: '#0ea5e9',
                    positive: '#22c55e',
                    negative: '#ef4444',
                }
            },
            borderRadius: {
                'xl': '12px',
                '2xl': '16px',
            },
            boxShadow: {
                'soft': '0 16px 30px rgba(15, 23, 42, 0.12)',
            }
        },
    },
    plugins: [],
}
