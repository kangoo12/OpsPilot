export const workspaceTabs = { overview: 'Overview', order: 'Order Details', reply: 'AI Reply', activity: 'Activity History' }
export type WorkspaceTab = keyof typeof workspaceTabs

export default function WorkspaceTabs({ active, onChange, idPrefix: id }: { active: WorkspaceTab; onChange: (tab: WorkspaceTab) => void; idPrefix: string }) {
  const keys = Object.keys(workspaceTabs) as WorkspaceTab[]
  return <div role="tablist" aria-label="Ticket workspace" className="sticky top-0 z-10 flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
    {keys.map((key, index) => <button key={key} id={`${id}-${key}`} role="tab" aria-controls={`${id}-${key}-panel`} aria-selected={active === key} tabIndex={active === key ? 0 : -1}
      onClick={() => onChange(key)} onKeyDown={event => {
        const next = event.key === 'ArrowRight' ? (index + 1) % keys.length : event.key === 'ArrowLeft' ? (index + keys.length - 1) % keys.length : event.key === 'Home' ? 0 : event.key === 'End' ? keys.length - 1 : null
        if (next === null) return
        event.preventDefault(); onChange(keys[next])
        document.getElementById(`${id}-${keys[next]}`)?.focus()
      }} className={`flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${active === key ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-indigo-50'}`}>
      {workspaceTabs[key]}
    </button>)}
  </div>
}
