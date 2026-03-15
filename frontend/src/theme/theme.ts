import { alpha, createTheme } from '@mui/material/styles'
import freesentationRegular from '@/assets/fonts/Freesentation-4Regular.ttf'
import freesentationMedium from '@/assets/fonts/Freesentation-5Medium.ttf'
import freesentationSemiBold from '@/assets/fonts/Freesentation-6SemiBold.ttf'
import freesentationBold from '@/assets/fonts/Freesentation-7Bold.ttf'

// Define custom colors in the theme
declare module '@mui/material/styles' {
  interface Palette {
    brand: {
      primary: string
      primaryHover: string
      primarySoft: string
      primaryGlow: string
    }
    surface: {
      1: string
      2: string
      3: string
      input: string
      sidebar: string
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
    brand?: {
      primary: string
      primaryHover: string
      primarySoft: string
      primaryGlow: string
    }
    surface?: {
      1: string
      2: string
      3: string
      input: string
      sidebar: string
    }
    border?: {
      default: string
      soft: string
      strong: string
      accent: string
    }
    status?: {
      success: string
      danger: string
      warning: string
      info: string
    }
  }
  interface Theme {
    bg: {
      canvas: string;
      app: string;
      surface1: string;
      surface2: string;
      surface3: string;
      elevated: string;
      input: string;
      sidebar: string;
    };
    border: {
      default: string;
      soft: string;
      strong: string;
      accent: string;
    };
  }
  interface ThemeOptions {
    bg?: {
      canvas?: string;
      app?: string;
      surface1?: string;
      surface2?: string;
      surface3?: string;
      elevated?: string;
      input?: string;
      sidebar?: string;
    };
    border?: {
      default?: string;
      soft?: string;
      strong?: string;
      accent?: string;
    };
  }
  interface TypeText {
    tertiary: string;
  }
}

const colors = {
  bg: {
    canvas: '#0E0E10',
    app: '#121119',
    surface1: '#17161F',
    surface2: '#1D1B26',
    surface3: '#24222D',
    elevated: '#2A2733',
    input: '#1A1822',
    sidebar: '#15141C',
  },
  text: {
    primary: '#F5F7FA',
    secondary: '#B7BDC8',
    tertiary: '#7E8594',
    disabled: '#5A606C',
    inverse: '#0F1115',
  },
  brand: {
    primary: '#22E76B',
    primaryHover: '#18C95B',
    primarySoft: 'rgba(34, 231, 107, 0.14)',
    primaryGlow: 'rgba(34, 231, 107, 0.28)',
  },
  border: {
    default: 'rgba(255, 255, 255, 0.08)',
    soft: 'rgba(255, 255, 255, 0.05)',
    strong: 'rgba(255, 255, 255, 0.12)',
    accent: 'rgba(34, 231, 107, 0.45)',
  },
  status: {
    success: '#22E76B',
    danger: '#FF5A5F',
    warning: '#F5B942',
    info: '#4DA3FF',
  },
}

const appFontFamily = '"Freesentation", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif'
const fontFaces = `
  @font-face {
    font-family: 'Freesentation';
    src: url(${freesentationRegular}) format('truetype');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
  }

  @font-face {
    font-family: 'Freesentation';
    src: url(${freesentationMedium}) format('truetype');
    font-weight: 500;
    font-style: normal;
    font-display: swap;
  }

  @font-face {
    font-family: 'Freesentation';
    src: url(${freesentationSemiBold}) format('truetype');
    font-weight: 600;
    font-style: normal;
    font-display: swap;
  }

  @font-face {
    font-family: 'Freesentation';
    src: url(${freesentationBold}) format('truetype');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
  }
`

const createFilledChipStyles = (color: string) => ({
  backgroundColor: alpha(color, 0.14),
  color,
  boxShadow: `inset 0 0 0 1px ${alpha(color, 0.06)}`,
})

const createOutlinedChipStyles = (color: string) => ({
  backgroundColor: alpha(color, 0.08),
  borderColor: alpha(color, 0.24),
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
      main: '#7CFFB2',
    },
    error: {
      main: colors.status.danger,
    },
    warning: {
      main: colors.status.warning,
    },
    info: {
      main: colors.status.info,
    },
    success: {
      main: colors.status.success,
    },
    text: {
      primary: colors.text.primary,
      secondary: colors.text.secondary,
      disabled: colors.text.disabled,
      tertiary: colors.text.tertiary,
    },
    divider: colors.border.default,
    brand: colors.brand,
    surface: {
      1: colors.bg.surface1,
      2: colors.bg.surface2,
      3: colors.bg.surface3,
      input: colors.bg.input,
      sidebar: colors.bg.sidebar,
    },
    border: colors.border,
    status: colors.status,
  },
  bg: colors.bg,
  border: colors.border,
  typography: {
    fontFamily: appFontFamily,
    h1: { fontSize: 32, fontWeight: 700, lineHeight: 40 / 32 },
    h2: { fontSize: 28, fontWeight: 700, lineHeight: 36 / 28 },
    h3: { fontSize: 24, fontWeight: 600, lineHeight: 32 / 24 },
    h4: { fontSize: 20, fontWeight: 600, lineHeight: 28 / 20 },
    h5: { fontSize: 18, fontWeight: 600, lineHeight: 24 / 18 },
    h6: { fontSize: 16, fontWeight: 600, lineHeight: 24 / 16 },
    body1: { fontSize: 14, fontWeight: 500, lineHeight: 20 / 14 },
    body2: { fontSize: 13, fontWeight: 500, lineHeight: 18 / 13 },
    caption: { fontSize: 12, fontWeight: 500, lineHeight: 16 / 12 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: {
    borderRadius: 12, // default md
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        ${fontFaces}

        html {
          font-family: ${appFontFamily};
        }

        body {
          background-color: ${colors.bg.canvas};
          color: ${colors.text.primary};
          font-family: ${appFontFamily};
        }

        input,
        button,
        textarea,
        select {
          font-family: ${appFontFamily};
        }

        * {
          box-sizing: border-box;
        }

        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: ${colors.border.strong};
          border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: ${colors.text.disabled};
        }
      `,
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface1,
          border: `1px solid ${colors.border.default}`,
          borderRadius: 16,
          backgroundImage: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: colors.bg.surface1,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '8px 16px',
          transition: 'all 160ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        },
        containedPrimary: {
          backgroundColor: colors.brand.primary,
          color: colors.text.inverse,
          '&:hover': {
            backgroundColor: colors.brand.primaryHover,
          },
        },
        outlined: {
          borderColor: colors.border.default,
          color: colors.text.primary,
          '&:hover': {
            borderColor: colors.border.strong,
            backgroundColor: colors.bg.surface2,
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: colors.bg.input,
            borderRadius: 12,
            '& fieldset': {
              borderColor: colors.border.soft,
            },
            '&:hover fieldset': {
              borderColor: colors.border.strong,
            },
            '&.Mui-focused fieldset': {
              borderColor: colors.border.accent,
              boxShadow: `0 0 0 1px rgba(34,231,107,0.28), 0 0 18px rgba(34,231,107,0.18)`,
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 600,
          letterSpacing: '-0.01em',
          '& .MuiChip-icon': {
            color: 'inherit',
          },
        },
      },
      variants: [
        {
          props: { variant: 'filled' },
          style: {
            backgroundColor: alpha(colors.text.primary, 0.08),
            color: colors.text.primary,
          },
        },
        {
          props: { variant: 'filled', color: 'success' },
          style: createFilledChipStyles(colors.status.success),
        },
        {
          props: { variant: 'filled', color: 'error' },
          style: createFilledChipStyles(colors.status.danger),
        },
        {
          props: { variant: 'filled', color: 'warning' },
          style: createFilledChipStyles(colors.status.warning),
        },
        {
          props: { variant: 'filled', color: 'info' },
          style: createFilledChipStyles(colors.status.info),
        },
        {
          props: { variant: 'outlined' },
          style: {
            backgroundColor: alpha(colors.text.primary, 0.04),
            borderColor: colors.border.default,
            color: colors.text.secondary,
          },
        },
        {
          props: { variant: 'outlined', color: 'success' },
          style: createOutlinedChipStyles(colors.status.success),
        },
        {
          props: { variant: 'outlined', color: 'error' },
          style: createOutlinedChipStyles(colors.status.danger),
        },
        {
          props: { variant: 'outlined', color: 'warning' },
          style: createOutlinedChipStyles(colors.status.warning),
        },
        {
          props: { variant: 'outlined', color: 'info' },
          style: createOutlinedChipStyles(colors.status.info),
        },
      ],
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${colors.border.default}`,
        },
      },
    },
  },
})
