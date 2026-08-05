declare global {
  interface Window {
    readonly desktop: {
      readonly platform: NodeJS.Platform
    }
  }
}

export {}
