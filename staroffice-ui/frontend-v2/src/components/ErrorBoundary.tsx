import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="min-h-screen bg-surface-0 flex items-center justify-center">
          <div className="surface-card p-8 max-w-md text-center">
            <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center mx-auto mb-4">
              <span className="text-xl">!</span>
            </div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">Something went wrong</h2>
            <p className="text-xs text-text-secondary mb-4 leading-relaxed">
              {this.state.error?.message || 'An unexpected error occurred in the dashboard.'}
            </p>
            <div className="bg-surface-0 rounded-lg p-3 mb-4 text-left">
              <pre className="text-2xs text-danger/70 font-mono leading-relaxed max-h-32 overflow-y-auto scrollbar-thin whitespace-pre-wrap">
                {this.state.error?.stack?.slice(0, 600) || 'No stack trace available'}
              </pre>
            </div>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-brand-indigo/15 text-brand-indigo border border-brand-indigo/20 hover:bg-brand-indigo/25 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
