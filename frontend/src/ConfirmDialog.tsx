import { useEffect, useId, useRef, type ReactNode } from 'react'

export default function ConfirmDialog({ title, children, confirmLabel, busy, onConfirm, onCancel }: {
  title: string; children: ReactNode; confirmLabel: string; busy: boolean; onConfirm: () => void; onCancel: () => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const titleId = useId()
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    container.current?.querySelector<HTMLElement>('textarea, input, button')?.focus()
    return () => previous?.focus()
  }, [])
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" onClick={event => { if (event.target === event.currentTarget && !busy) onCancel() }}>
    <div ref={container} role="dialog" aria-modal="true" aria-labelledby={titleId} className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
      onKeyDown={event => {
        if (event.key === 'Escape' && !busy) onCancel()
        if (event.key === 'Tab') {
          const nodes = [...(container.current?.querySelectorAll<HTMLElement>('button:not(:disabled), textarea, input, select') ?? [])]
          const first = nodes[0], last = nodes.at(-1)
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
          if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
        }
      }}>
      <h3 id={titleId} className="text-lg font-semibold text-slate-900">{title}</h3>
      <div className="mt-3 space-y-3 text-sm leading-6 text-slate-600">{children}</div>
      <div className="mt-6 flex flex-wrap justify-end gap-3"><button type="button" disabled={busy} onClick={onCancel} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50">Cancel</button>
        <button type="button" disabled={busy} onClick={onConfirm} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{busy ? 'Saving…' : confirmLabel}</button></div>
    </div>
  </div>
}
