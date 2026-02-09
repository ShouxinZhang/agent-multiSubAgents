import { cn } from '../../lib/utils'

function Badge({ className, children }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground', className)}>
      {children}
    </span>
  )
}

export { Badge }
