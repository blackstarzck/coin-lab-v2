import { Field } from '@base-ui/react/field'
import { NumberField } from '@base-ui/react/number-field'
import { KeyboardArrowDownRounded, KeyboardArrowUpRounded } from '@mui/icons-material'
import Box from '@mui/material/Box'
import { alpha, styled } from '@mui/material/styles'
import type { ReactNode } from 'react'

type FieldSize = 'small' | 'medium'

interface MuiNumberFieldProps {
  label: string
  value: number | null
  onValueChange: (value: number | null) => void
  helperText?: ReactNode
  fullWidth?: boolean
  size?: FieldSize
  min?: number
  max?: number
  step?: number | 'any'
  smallStep?: number
  largeStep?: number
  disabled?: boolean
  required?: boolean
  error?: boolean
  format?: Intl.NumberFormatOptions
}

interface WidthProps {
  fullWidth?: boolean
}

interface SizeProps {
  fieldSize: FieldSize
}

const DEFAULT_FORMAT: Intl.NumberFormatOptions = {
  useGrouping: false,
  maximumFractionDigits: 6,
}

const StyledFieldRoot = styled(Field.Root, {
  shouldForwardProp: (prop) => prop !== 'fullWidth' && prop !== 'fieldSize',
})<WidthProps & SizeProps>(({ fullWidth, fieldSize }) => ({
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  paddingTop: fieldSize === 'small' ? 6 : 8,
  width: fullWidth ? '100%' : undefined,
}))

const StyledNumberFieldGroup = styled(NumberField.Group, {
  shouldForwardProp: (prop) => prop !== 'fullWidth' && prop !== 'fieldSize',
})<WidthProps & SizeProps>(({ theme, fullWidth, fieldSize }) => ({
  position: 'relative',
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) auto',
  alignItems: 'stretch',
  width: fullWidth ? '100%' : undefined,
  minHeight: fieldSize === 'small' ? 40 : 56,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.bg.input,
  border: `1px solid ${theme.border.default}`,
  overflow: 'visible',
  transition: 'border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease',
  '&:hover': {
    borderColor: theme.border.strong,
  },
  '&[data-focused]': {
    borderColor: theme.palette.primary.main,
    boxShadow: `0 0 0 1px ${alpha(theme.palette.primary.main, 0.45)}`,
  },
  '&[data-invalid]': {
    borderColor: theme.palette.error.main,
    boxShadow: `0 0 0 1px ${alpha(theme.palette.error.main, 0.28)}`,
  },
  '&[data-disabled]': {
    opacity: 0.58,
    cursor: 'not-allowed',
  },
  '&[data-focused] .MuiNumberField-label': {
    color: theme.palette.primary.main,
  },
  '&[data-invalid] .MuiNumberField-label': {
    color: theme.palette.error.main,
  },
}))

const StyledFieldLabel = styled(Field.Label, {
  shouldForwardProp: (prop) => prop !== 'fieldSize',
})<SizeProps>(({ theme, fieldSize }) => ({
  position: 'absolute',
  top: 0,
  left: fieldSize === 'small' ? 10 : 12,
  transform: 'translateY(-50%) scale(0.85)',
  transformOrigin: 'top left',
  padding: '0 6px',
  backgroundColor: theme.bg.input,
  color: theme.palette.text.secondary,
  fontFamily: theme.typography.fontFamily,
  fontSize: fieldSize === 'small' ? 12 : 13,
  fontWeight: 500,
  lineHeight: 1,
  pointerEvents: 'none',
  zIndex: 1,
}))

const StyledNumberFieldInput = styled(NumberField.Input, {
  shouldForwardProp: (prop) => prop !== 'fieldSize',
})<SizeProps>(({ theme, fieldSize }) => ({
  appearance: 'textfield',
  minWidth: 0,
  width: '100%',
  border: 0,
  outline: 0,
  backgroundColor: 'transparent',
  color: theme.palette.text.primary,
  fontFamily: theme.typography.fontFamily,
  fontSize: fieldSize === 'small' ? 14 : 16,
  fontWeight: 500,
  lineHeight: 1.5,
  padding: fieldSize === 'small' ? '15px 12px 7px' : '21px 14px 11px',
  '&::placeholder': {
    color: theme.palette.text.tertiary,
  },
  '&::-webkit-outer-spin-button, &::-webkit-inner-spin-button': {
    appearance: 'none',
    margin: 0,
  },
}))

const StyledControls = styled('div', {
  shouldForwardProp: (prop) => prop !== 'fieldSize',
})<SizeProps>(({ theme, fieldSize }) => ({
  display: 'grid',
  gridTemplateRows: '1fr 1fr',
  width: fieldSize === 'small' ? 34 : 38,
  borderLeft: `1px solid ${theme.border.default}`,
}))

const StyledFieldDescription = styled(Field.Description)(({ theme }) => ({
  marginLeft: 14,
  color: theme.palette.text.secondary,
  fontFamily: theme.typography.fontFamily,
  fontSize: 12,
  fontWeight: 500,
  lineHeight: 1.4,
}))

export function MuiNumberField({
  label,
  value,
  onValueChange,
  helperText,
  fullWidth = false,
  size = 'medium',
  min,
  max,
  step = 1,
  smallStep,
  largeStep,
  disabled = false,
  required = false,
  error = false,
  format = DEFAULT_FORMAT,
}: MuiNumberFieldProps) {
  return (
    <StyledFieldRoot fullWidth={fullWidth} fieldSize={size} invalid={error} disabled={disabled}>
      <NumberField.Root
        value={value}
        onValueChange={onValueChange}
        min={min}
        max={max}
        step={step}
        smallStep={smallStep}
        largeStep={largeStep}
        disabled={disabled}
        required={required}
        locale="ko-KR"
        format={format}
      >
        <StyledNumberFieldGroup fullWidth={fullWidth} fieldSize={size}>
          <StyledFieldLabel className="MuiNumberField-label" fieldSize={size}>
            {label}
          </StyledFieldLabel>
          <StyledNumberFieldInput fieldSize={size} inputMode="decimal" />
          <StyledControls fieldSize={size}>
            <NumberField.Increment
              render={(
                <Box
                  component="button"
                  sx={(theme) => ({
                    all: 'unset',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: 'text.secondary',
                    transition: 'background-color 160ms ease, color 160ms ease',
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.common.white, 0.04),
                      color: 'text.primary',
                    },
                    '&:active': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    },
                    '&:disabled, &[data-disabled]': {
                      cursor: 'not-allowed',
                      color: 'text.tertiary',
                    },
                  })}
                />
              )}
              aria-label={`${label} 증가`}
            >
              <KeyboardArrowUpRounded fontSize="small" />
            </NumberField.Increment>
            <NumberField.Decrement
              render={(
                <Box
                  component="button"
                  sx={(theme) => ({
                    all: 'unset',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: 'text.secondary',
                    transition: 'background-color 160ms ease, color 160ms ease',
                    borderTop: `1px solid ${theme.border.default}`,
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.common.white, 0.04),
                      color: 'text.primary',
                    },
                    '&:active': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    },
                    '&:disabled, &[data-disabled]': {
                      cursor: 'not-allowed',
                      color: 'text.tertiary',
                    },
                  })}
                />
              )}
              aria-label={`${label} 감소`}
            >
              <KeyboardArrowDownRounded fontSize="small" />
            </NumberField.Decrement>
          </StyledControls>
        </StyledNumberFieldGroup>
      </NumberField.Root>
      {helperText ? <StyledFieldDescription>{helperText}</StyledFieldDescription> : null}
    </StyledFieldRoot>
  )
}
