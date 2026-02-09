import { cn } from '../../lib/utils'

function Separator({ className }) {
  return <div className={cn('h-px w-full bg-border', className)} />
}

export { Separator }
