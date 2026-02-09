import { cn } from '../../lib/utils'

function Card({ className, ...props }) {
  return <div className={cn('panel', className)} {...props} />
}

function CardHeader({ className, ...props }) {
  return <div className={cn('px-4 py-3 border-b border-border', className)} {...props} />
}

function CardTitle({ className, ...props }) {
  return <h3 className={cn('text-sm font-semibold tracking-wide', className)} {...props} />
}

function CardContent({ className, ...props }) {
  return <div className={cn('p-4', className)} {...props} />
}

export { Card, CardHeader, CardTitle, CardContent }
