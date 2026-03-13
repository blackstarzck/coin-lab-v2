declare module 'odometer' {
  interface OdometerOptions {
    el: Element
    value?: number
    format?: string
    theme?: string
    duration?: number
    animation?: 'count' | 'slide'
  }

  export default class Odometer {
    constructor(options: OdometerOptions)
    update(value: number): void
    render(value?: number): void
  }
}
