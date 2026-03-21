import { alpha, createTheme } from '@mui/material/styles'

declare module '@mui/material/styles' {
  interface Palette {
    brand: {
      primary: string
      primaryHover: string
      secondary: string
      primarySoft: string
      primaryGlow: string
      gradient: string
    }
    surface: {
      base: string
      low: string
      container: string
      high: string
      bright: string
      input: string
      sidebar: string
      sunken: string
      glass: string
    }
    border: {
      default: string
      soft: string
      strong: string
      accent: string
    }
    status: {
      success: string
      danger: string
      warning: string
      info: string
    }
  }
  interface PaletteOptions {
    brand?: Palette['brand']
    surface?: Palette['surface']
    border?: Palette['border']
    status?: Palette['status']
  }
  interface Theme {
    bg: {
      canvas: string
      app: string
      surface1: string
      surface2: string
      surface3: string
      elevated: string
      input: string
      sidebar: string
      sunken: string
      glass: string
    }
    border: {
      default: string
      soft: string
      strong: string
      accent: string
    }
    motion: {
      quick: string
      regular: string
    }
  }
  interface ThemeOptions {
    bg?: Theme['bg']
    border?: Theme['border']
    motion?: Theme['motion']
  }
  interface TypeText {
    tertiary: string
  }
}

const colors = {
  bg: {
    canvas: '#10131A',
    app: '#10131A',
    surface1: '#191C22',
    surface2: '#1D2026',
    surface3: '#272A31',
    elevated: '#363940',
    input: '#1D2026',
    sidebar: '#10131A',
    sunken: '#0B0E14',
    glass: 'rgba(50, 53, 60, 0.6)',
  },
  text: {
    primary: '#E1E2EB',
    secondary: '#BBC9CF',
    tertiary: '#859399',
    disabled: '#5E6A70',
    inverse: '#001F28',
  },
  brand: {
    primary: '#00D1FF',
    primaryHover: '#4CD6FF',
    secondary: '#A4E6FF',
    primarySoft: alpha('#00D1FF', 0.14),
    primaryGlow: alpha('#00D1FF', 0.32),
    gradient: 'linear-gradient(135deg, #00D1FF 0%, #A4E6FF 100%)',
  },
  border: {
    default: alpha('#3C494E', 0.18),
    soft: alpha('#3C494E', 0.12),
    strong: alpha('#3C494E', 0.28),
    accent: alpha('#00D1FF', 0.28),
  },
  status: {
    success: '#36E6A0',
    danger: '#FF7F86',
    warning: '#FFCE73',
    info: '#7ACFFF',
  },
}

const headlineFontFamily = '"Space Grotesk", "Freesentation", "Pretendard", "Apple SD Gothic Neo", sans-serif'
const bodyFontFamily = '"Inter", "Freesentation", "Pretendard", "Apple SD Gothic Neo", sans-serif'

const filledChip = (color: string) => ({
  backgroundColor: alpha(color, 0.1),
  color,
  boxShadow: `0 0 8px ${alpha(color, 0.22)}`,
})

const outlinedChip = (color: string) => ({
  backgroundColor: alpha(color, 0.04),
  borderColor: alpha(color, 0.2),
  color,
})

export const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: colors.bg.canvas,
      paper: colors.bg.surface1,
    },
    primary: {
      main: colors.brand.primary,
      dark: colors.brand.primaryHover,
      contrastText: colors.text.inverse,
    },
    secondary: {
      main: colors.brand.secondary,
    },
    error: { main: colors.status.danger },
    warning: { main: colors.status.warning },
    info: { main: colors.status.info },
    success: { main: colors.status.success },
    text: {
      primary: colors.text.primary,
      secondary: colors.text.secondary,
      tertiary: colors.text.tertiary,
      disabled: colors.text.disabled,
    },
    divider: colors.border.soft,
    brand: colors.brand,
    surface: {
      base: colors.bg.canvas,
      low: colors.bg.surface1,
      container: colors.bg.surface2,
      high: colors.bg.surface3,
      bright: colors.bg.elevated,
      input: colors.bg.input,
      sidebar: colors.bg.sidebar,
      sunken: colors.bg.sunken,
      glass: colors.bg.glass,
    },
    border: colors.border,
    status: colors.status,
  },
  bg: colors.bg,
  border: colors.border,
  motion: {
    quick: '160ms ease-out',
    regular: '220ms ease-out',
  },
  typography: {
    fontFamily: bodyFontFamily,
    h1: { fontFamily: headlineFontFamily, fontSize: 52, fontWeight: 700, lineHeight: 1.02, letterSpacing: '-0.04em' },
    h2: { fontFamily: headlineFontFamily, fontSize: 42, fontWeight: 700, lineHeight: 1.08, letterSpacing: '-0.035em' },
    h3: { fontFamily: headlineFontFamily, fontSize: 30, fontWeight: 700, lineHeight: 1.12, letterSpacing: '-0.03em' },
    h4: { fontFamily: headlineFontFamily, fontSize: 24, fontWeight: 700, lineHeight: 1.18, letterSpacing: '-0.025em' },
    h5: { fontFamily: headlineFontFamily, fontSize: 19, fontWeight: 700, lineHeight: 1.24, letterSpacing: '-0.02em' },
    h6: { fontFamily: headlineFontFamily, fontSize: 16, fontWeight: 700, lineHeight: 1.3, letterSpacing: '-0.015em' },
    subtitle1: { fontFamily: headlineFontFamily, fontSize: 14, fontWeight: 600, lineHeight: 1.35, letterSpacing: '-0.01em' },
    body1: { fontSize: 14, fontWeight: 400, lineHeight: 1.55 },
    body2: { fontSize: 13, fontWeight: 400, lineHeight: 1.5 },
    caption: { fontSize: 11, fontWeight: 500, lineHeight: 1.45, letterSpacing: '0.03em' },
    button: { fontFamily: headlineFontFamily, fontSize: 12, fontWeight: 700, lineHeight: 1.2, letterSpacing: '0.02em', textTransform: 'none' },
    overline: { fontFamily: headlineFontFamily, fontSize: 10, fontWeight: 700, lineHeight: 1.4, letterSpacing: '0.28em', textTransform: 'uppercase' },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: {
          fontFamily: bodyFontFamily,
          backgroundColor: colors.bg.canvas,
        },
        body: {
          background:
            `radial-gradient(circle at top left, ${alpha(colors.brand.primary, 0.08)} 0%, transparent 26%),` +
            `radial-gradient(circle at top right, ${alpha(colors.brand.secondary, 0.06)} 0%, transparent 18%),` +
            colors.bg.canvas,
          color: colors.text.primary,
          fontFamily: bodyFontFamily,
        },
        'h1, h2, h3, h4, h5, h6': {
          fontFamily: headlineFontFamily,
        },
        'input, button, textarea, select': {
          fontFamily: bodyFontFamily,
        },
        '*': {
          boxSizing: 'border-box',
        },
        '*::selection': {
          backgroundColor: alpha(colors.brand.primary, 0.24),
          color: colors.text.primary,
        },
        '::-webkit-scrollbar': {
          width: 6,
          height: 6,
        },
        '::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '::-webkit-scrollbar-thumb': {
          background: colors.border.strong,
          borderRadius: 999,
        },
        '::-webkit-scrollbar-thumb:hover': {
          background: alpha(colors.text.tertiary, 0.88),
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface2,
          border: 'none',
          borderRadius: 12,
          backgroundImage: 'none',
          boxShadow: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface2,
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '10px 16px',
          minHeight: 40,
          transition: `transform ${colors.brand.primary ? '160ms ease-out' : '160ms ease-out'}, filter 160ms ease-out, background-color 160ms ease-out`,
          boxShadow: 'none',
        },
        containedPrimary: {
          backgroundImage: colors.brand.gradient,
          color: colors.text.inverse,
          '&:hover': {
            backgroundImage: colors.brand.gradient,
            filter: 'brightness(1.04)',
            transform: 'translateY(-1px)',
            boxShadow: `0 14px 30px ${alpha(colors.brand.primary, 0.18)}`,
          },
        },
        outlined: {
          borderColor: alpha('#859399', 0.2),
          color: colors.brand.secondary,
          backgroundColor: 'transparent',
          '&:hover': {
            borderColor: alpha('#859399', 0.32),
            backgroundColor: alpha(colors.bg.surface3, 0.6),
          },
        },
        text: {
          color: colors.brand.secondary,
          '&:hover': {
            backgroundColor: alpha(colors.brand.primary, 0.08),
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface2,
          borderRadius: 8,
          '& fieldset': {
            borderColor: colors.border.soft,
          },
          '&:hover fieldset': {
            borderColor: colors.border.default,
          },
          '&.Mui-focused fieldset': {
            borderColor: colors.border.accent,
            boxShadow: `0 0 0 1px ${alpha(colors.brand.primary, 0.16)}`,
          },
        },
        input: {
          paddingTop: 11,
          paddingBottom: 11,
        },
      },
    },
    MuiFormLabel: {
      styleOverrides: {
        root: {
          color: colors.text.tertiary,
          fontSize: 12,
          letterSpacing: '0.04em',
          '&.Mui-focused': {
            color: colors.text.secondary,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontFamily: headlineFontFamily,
          fontWeight: 700,
          fontSize: 10,
          letterSpacing: '0.02em',
          '& .MuiChip-icon': {
            color: 'inherit',
          },
        },
      },
      variants: [
        { props: { variant: 'filled' }, style: { backgroundColor: alpha(colors.bg.surface3, 0.92), color: colors.text.primary } },
        { props: { variant: 'filled', color: 'success' }, style: filledChip(colors.status.success) },
        { props: { variant: 'filled', color: 'error' }, style: filledChip(colors.status.danger) },
        { props: { variant: 'filled', color: 'warning' }, style: filledChip(colors.status.warning) },
        { props: { variant: 'filled', color: 'info' }, style: filledChip(colors.status.info) },
        { props: { variant: 'outlined' }, style: { backgroundColor: 'transparent', borderColor: alpha('#859399', 0.15), color: colors.text.secondary } },
        { props: { variant: 'outlined', color: 'success' }, style: outlinedChip(colors.status.success) },
        { props: { variant: 'outlined', color: 'error' }, style: outlinedChip(colors.status.danger) },
        { props: { variant: 'outlined', color: 'warning' }, style: outlinedChip(colors.status.warning) },
        { props: { variant: 'outlined', color: 'info' }, style: outlinedChip(colors.status.info) },
      ],
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          height: 2,
          borderRadius: 999,
          backgroundColor: colors.brand.primary,
          boxShadow: `0 0 10px ${alpha(colors.brand.primary, 0.26)}`,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          minHeight: 42,
          color: colors.text.tertiary,
          fontFamily: headlineFontFamily,
          fontWeight: 700,
          letterSpacing: '0.02em',
          '&.Mui-selected': {
            color: colors.text.primary,
          },
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
        },
      },
    },
    MuiTable: {
      styleOverrides: {
        root: {
          borderCollapse: 'separate',
          borderSpacing: '0 4px',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            borderBottom: 'none',
          },
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover .MuiTableCell-root': {
            backgroundColor: alpha(colors.bg.surface3, 0.86),
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: 'none',
          backgroundColor: colors.bg.surface1,
          color: colors.text.primary,
          paddingTop: 12,
          paddingBottom: 12,
        },
        head: {
          backgroundColor: 'transparent',
          color: colors.text.secondary,
          fontFamily: headlineFontFamily,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          paddingTop: 0,
          paddingBottom: 6,
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface1,
          borderRadius: '8px !important',
          '&::before': {
            display: 'none',
          },
        },
      },
    },
    MuiAccordionSummary: {
      styleOverrides: {
        root: {
          minHeight: 52,
        },
        content: {
          margin: '10px 0',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          border: `1px solid ${colors.border.soft}`,
          backgroundColor: alpha(colors.bg.surface3, 0.82),
        },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: alpha(colors.bg.surface3, 0.8),
        },
      },
    },
  },
})
