/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surface layers
        "surface-0": "hsl(var(--surface-0))",
        "surface-1": "hsl(var(--surface-1))",
        "surface-2": "hsl(var(--surface-2))",
        "surface-3": "hsl(var(--surface-3))",

        // Text
        "text-primary":   "hsl(var(--text-primary))",
        "text-secondary": "hsl(var(--text-secondary))",
        "text-tertiary":  "hsl(var(--text-tertiary))",

        // Border
        "border-default": "hsl(var(--border-default))",
        "border-hover":   "hsl(var(--border-hover))",
        "border-accent":  "hsl(var(--border-accent))",

        // Brand
        "brand-indigo": "hsl(var(--brand-indigo))",
        "brand-cyan":   "hsl(var(--brand-cyan))",
        "brand-violet": "hsl(var(--brand-violet))",

        // Semantic
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        danger:  "hsl(var(--danger))",
        info:    "hsl(var(--info))",

        // Glow (for box-shadow usage via inline styles, not Tailwind color)
        "glow-indigo": "hsl(var(--glow-indigo))",
        "glow-cyan":   "hsl(var(--glow-cyan))",
        "glow-violet": "hsl(var(--glow-violet))",

        // Backward compat — keep old shadcn names working
        border:     "hsl(var(--border-default))",
        background: "hsl(var(--surface-0))",
        foreground: "hsl(var(--text-primary))",
        card:       "hsl(var(--surface-1))",
        "card-foreground": "hsl(var(--text-primary))",
        muted:      "hsl(var(--surface-2))",
        "muted-foreground": "hsl(var(--text-secondary))",
        accent:     "hsl(var(--brand-indigo))",
        "accent-foreground": "hsl(0 0% 100%)",
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      fontFamily: {
        sans:  ['Inter', 'HarmonyOS Sans SC', 'PingFang SC', 'Microsoft YaHei', 'system-ui', '-apple-system', 'sans-serif'],
        mono:  ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      fontSize: {
        // Typography scale (base 16px)
        '2xs':  ['0.6875rem', { lineHeight: '1.4' }],        // 11px — labels, timestamps
        xs:    ['0.8125rem', { lineHeight: '1.5' }],         // 13px — secondary text, badges
        sm:    ['0.9375rem', { lineHeight: '1.6' }],         // 15px — body
        base:  ['1rem',      { lineHeight: '1.6' }],         // 16px
        lg:    ['1.125rem',  { lineHeight: '1.4' }],         // 18px — card titles
        xl:    ['1.375rem',  { lineHeight: '1.3' }],         // 22px — section titles
        '2xl': ['1.75rem',   { lineHeight: '1.2' }],         // 28px — page titles
        '3xl': ['2.25rem',   { lineHeight: '1.2' }],         // 36px — KPI numbers
        '4xl': ['3rem',      { lineHeight: '1.1' }],         // 48px — hero KPIs
      },
    },
  },
  plugins: [],
}
