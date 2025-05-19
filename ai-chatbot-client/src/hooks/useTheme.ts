import { useState, useEffect } from 'react';

export function useTheme() {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const detectTheme = () => {
      try {
        if ((window.frappe.boot as { desk_theme?: string }).desk_theme) {
          const bootTheme = (window.frappe.boot as { desk_theme?: string })
            .desk_theme;
          setTheme(bootTheme === 'Dark' ? 'dark' : 'light');
          return;
        }

        // Fallback if boot data isn't available for some reason
        const root = document.documentElement;
        const themeValue = root.getAttribute('data-theme');

        if (themeValue === 'dark') {
          setTheme('dark');
          return;
        }

        // Check for dark mode class on body
        if (document.body.classList.contains('dark')) {
          setTheme('dark');
          return;
        }
      } catch (error) {
        console.error('Error detecting theme: ', error);
        setTheme('light');
      }
    };

    detectTheme();

    const handleThemeChange = () => {
      detectTheme();
    };

    if (window.frappe) {
      document.addEventListener('frappe-theme-change', handleThemeChange);
    }

    const interval = setInterval(detectTheme, 2000);

    return () => {
      clearInterval(interval);
      if (window.frappe) {
        document.removeEventListener('frappe-theme-change', handleThemeChange);
      }
    };
  }, []);

  return theme;
}
