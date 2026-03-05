import { useState, useRef, useCallback, useMemo } from 'react'

const API_URL = 'http://localhost:8001'

// ─── ProgressBar ───
function ProgressBar({ progress }) {
    const { percent = 0, message = '', phase = '' } = progress

    return (
        <div className="flex flex-col items-center justify-center gap-5 py-12 px-8 max-w-lg mx-auto">
            <div className="relative w-20 h-20">
                <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="35" fill="none" stroke="rgb(30 41 59)" strokeWidth="5" />
                    <circle cx="40" cy="40" r="35" fill="none" stroke="url(#grad)" strokeWidth="5" strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 35}`}
                        strokeDashoffset={`${2 * Math.PI * 35 * (1 - percent / 100)}`}
                        className="transition-all duration-500"
                    />
                    <defs>
                        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#8b5cf6" />
                            <stop offset="100%" stopColor="#6366f1" />
                        </linearGradient>
                    </defs>
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-white">{percent}%</span>
                </div>
            </div>

            <p className="text-sm font-medium text-slate-300 text-center animate-pulse">{message}</p>

            {/* Steps timeline */}
            <div className="flex items-center gap-1 mt-2">
                {['extracting', 'zoning', 'parsing', 'done'].map((step, i) => {
                    const phases = ['extracting', 'zoning', 'parsing', 'done']
                    const currentIdx = phases.indexOf(phase)
                    const active = i <= currentIdx
                    return (
                        <div key={step} className="flex items-center gap-1">
                            <div className={`w-2 h-2 rounded-full transition-all duration-300 ${active ? 'bg-violet-500 scale-110' : 'bg-slate-700'}`} />
                            {i < 3 && <div className={`w-6 h-0.5 transition-all duration-300 ${active ? 'bg-violet-500/50' : 'bg-slate-800'}`} />}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

// ─── UploadPanel ───
function UploadPanel({ onUpload, loading }) {
    const [file, setFile] = useState(null)
    const [dragOver, setDragOver] = useState(false)
    const inputRef = useRef(null)

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        setDragOver(false)
        const f = e.dataTransfer.files?.[0]
        if (f && f.type === 'application/pdf') setFile(f)
    }, [])

    const handleDragOver = useCallback((e) => { e.preventDefault(); setDragOver(true) }, [])
    const handleDragLeave = useCallback(() => setDragOver(false), [])

    const handleFileSelect = useCallback((e) => {
        const f = e.target.files?.[0]
        if (f) setFile(f)
    }, [])

    const handleSubmit = useCallback(() => {
        if (file) onUpload(file)
    }, [file, onUpload])

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="px-6 pt-6 pb-4">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                        <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-white tracking-tight">Cause List Parser</h1>
                        <p className="text-xs text-slate-500 font-medium">Column-Zone · Regex · Indian Courts</p>
                    </div>
                </div>
            </div>

            <div className="flex-1 px-6 space-y-5 overflow-y-auto">
                {/* Drop zone */}
                <div
                    id="drop-zone"
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => inputRef.current?.click()}
                    className={`relative group cursor-pointer rounded-2xl border-2 border-dashed transition-all duration-300 p-8 text-center ${dragOver
                        ? 'border-violet-400 bg-violet-500/10 scale-[1.02]'
                        : file
                            ? 'border-emerald-500/50 bg-emerald-500/5'
                            : 'border-slate-700 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50'
                        }`}
                >
                    <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={handleFileSelect} id="file-input" />

                    {file ? (
                        <div className="space-y-2">
                            <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/15 flex items-center justify-center">
                                <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <p className="text-sm font-semibold text-emerald-400">{file.name}</p>
                            <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-800 flex items-center justify-center group-hover:bg-slate-700/80 transition-colors">
                                <svg className="w-7 h-7 text-slate-500 group-hover:text-violet-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-slate-300">Drop cause list PDF here</p>
                                <p className="text-xs text-slate-600 mt-1">or click to browse</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Info note */}
                <div className="rounded-xl bg-slate-800/30 border border-slate-700/30 p-4">
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                        <span className="text-violet-400 font-semibold">Column-Zone Parser:</span> Uses coordinate-based column detection with regex extraction. No LLM needed for 99%+ of cases.
                    </p>
                </div>
            </div>

            {/* Submit button */}
            <div className="p-6">
                <button
                    id="parse-btn"
                    onClick={handleSubmit}
                    disabled={!file || loading}
                    className={`w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-300 ${!file || loading
                        ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                        : 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:scale-[1.02] active:scale-[0.98]'
                        }`}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 rounded-full border-2 border-slate-600 border-t-violet-400 animate-spin" />
                            Processing…
                        </span>
                    ) : 'Parse Cause List'}
                </button>
            </div>
        </div>
    )
}

// ─── SummaryBar ───
function SummaryBar({ data }) {
    const total = Array.isArray(data) ? data.length : 0
    const court = total > 0 ? (data[0].court_name || 'Unknown Court') : 'Unknown Court'
    const date = total > 0 ? (data[0].listing_date || '') : ''

    // Count unique courts
    const courts = useMemo(() => {
        if (!Array.isArray(data)) return []
        return [...new Set(data.map(c => c.court_no).filter(Boolean))].sort()
    }, [data])

    return (
        <div className="space-y-3 mb-5">
            <div className="flex items-center gap-3 text-xs flex-wrap">
                <span className="px-3 py-1.5 rounded-lg bg-violet-900/30 border border-violet-700/30 text-violet-300 font-semibold">🏛️ {court}</span>
                {date && <span className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700/40 text-slate-400">📅 {date}</span>}
                <span className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700/40 text-slate-400">⚖️ {total} cases</span>
                <span className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700/40 text-slate-400">🏢 {courts.length} courts</span>
            </div>
        </div>
    )
}

// ─── FilterBar ───
function FilterBar({ data, filters, setFilters }) {
    const caseTypes = useMemo(() => {
        if (!Array.isArray(data)) return []
        const types = new Set(data.map((c) => c.case_type).filter(Boolean))
        return ['All', ...Array.from(types).sort()]
    }, [data])

    const courtNos = useMemo(() => {
        if (!Array.isArray(data)) return []
        const courts = new Set(data.map((c) => c.court_no).filter(Boolean))
        return ['All', ...Array.from(courts).sort()]
    }, [data])

    const selectCls = "rounded-lg bg-slate-800/80 border border-slate-700/50 text-slate-300 text-xs px-3 py-2 focus:outline-none focus:ring-1 focus:ring-violet-500/40 appearance-none cursor-pointer"

    return (
        <div className="flex flex-wrap items-center gap-3 mb-4">
            <select id="filter-case-type" value={filters.caseType} onChange={(e) => setFilters((f) => ({ ...f, caseType: e.target.value }))} className={selectCls}>
                {caseTypes.map((t) => <option key={t} value={t}>{t === 'All' ? 'All Types' : t}</option>)}
            </select>
            <select id="filter-court-no" value={filters.courtNo || 'All'} onChange={(e) => setFilters((f) => ({ ...f, courtNo: e.target.value }))} className={selectCls}>
                {courtNos.map((c) => <option key={c} value={c}>{c === 'All' ? 'All Courts' : `Court ${c}`}</option>)}
            </select>
            <input
                type="text"
                placeholder="Search parties…"
                value={filters.search || ''}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                className="rounded-lg bg-slate-800/80 border border-slate-700/50 text-slate-300 text-xs px-3 py-2 focus:outline-none focus:ring-1 focus:ring-violet-500/40 w-48"
            />
        </div>
    )
}

// ─── CaseCard ───
function CaseCard({ entry }) {
    const [expanded, setExpanded] = useState(false)

    return (
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-sm overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-black/20">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 bg-slate-800/40 border-b border-slate-800/60">
                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 bg-slate-800 rounded-lg px-2.5 py-1">#{entry.item_number}</span>
                    <span className="text-sm font-bold text-white tracking-wide">{entry.case_number || 'No case number'}</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-500 font-medium">
                    <span className="text-violet-400/80">Court {entry.court_no}</span>
                </div>
            </div>

            {/* Body — Parties */}
            <div className="px-5 py-4 space-y-3">
                <div>
                    <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-1">Petitioner</p>
                    <p className="text-sm text-slate-200 font-medium">{entry.petitioner || '—'}</p>
                </div>

                <div className="flex items-center gap-2">
                    <div className="flex-1 h-px bg-slate-800" />
                    <span className="text-[10px] font-bold text-slate-600 tracking-wider">VS</span>
                    <div className="flex-1 h-px bg-slate-800" />
                </div>

                <div>
                    <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-1">Respondent</p>
                    <p className="text-sm text-slate-200 font-medium">{entry.respondent || '—'}</p>
                </div>

                {entry.advocates && (
                    <div className="pt-2 border-t border-slate-800/40">
                        <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-1">Advocates</p>
                        <p className="text-[11px] text-slate-400">{entry.advocates}</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 bg-slate-800/20 border-t border-slate-800/50 flex flex-wrap items-center justify-end gap-3">
                <button
                    onClick={() => setExpanded((s) => !s)}
                    className="flex items-center gap-1 text-[10px] font-semibold text-slate-500 hover:text-violet-400 transition-colors px-2 py-1 rounded-lg hover:bg-slate-800/60"
                >
                    <span className="font-mono">{'{ }'}</span>
                    <span>{expanded ? 'Hide' : 'View'} JSON</span>
                </button>
            </div>

            {expanded && (
                <div className="border-t border-slate-800/50">
                    <pre className="p-4 text-xs font-mono text-slate-400 bg-slate-950/50 max-h-64 overflow-auto leading-relaxed">
                        {JSON.stringify(entry, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    )
}

// ─── ResultsPanel ───
function ResultsPanel({ data }) {
    const [filters, setFilters] = useState({ caseType: 'All', courtNo: 'All', search: '' })

    const filteredCases = useMemo(() => {
        if (!Array.isArray(data)) return []
        return data.filter((c) => {
            if (filters.caseType !== 'All' && c.case_type !== filters.caseType) return false
            if (filters.courtNo !== 'All' && c.court_no !== filters.courtNo) return false
            if (filters.search) {
                const q = filters.search.toLowerCase()
                const searchable = [c.petitioner, c.respondent, c.case_number, c.advocates]
                    .filter(Boolean).join(' ').toLowerCase()
                if (!searchable.includes(q)) return false
            }
            return true
        })
    }, [data, filters])

    const handleDownload = useCallback(() => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `causelist_export.json`
        a.click()
        URL.revokeObjectURL(url)
    }, [data])

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between px-6 pt-6 pb-2">
                <h2 className="text-lg font-bold text-white">Results</h2>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{filteredCases.length} of {data.length}</span>
                    <button
                        id="download-json"
                        onClick={handleDownload}
                        className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-slate-800 border border-slate-700/50 text-slate-300 hover:text-white hover:border-violet-500/40 transition-all"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Export JSON
                    </button>
                </div>
            </div>
            <div className="flex-1 px-6 pb-6 overflow-y-auto">
                <SummaryBar data={data} />
                <FilterBar data={data} filters={filters} setFilters={setFilters} />
                <div className="space-y-4">
                    {filteredCases.length === 0 ? (
                        <div className="text-center py-16">
                            <p className="text-slate-600 text-sm">No cases match the current filters</p>
                        </div>
                    ) : (
                        filteredCases.map((entry, i) => <CaseCard key={i} entry={entry} />)
                    )}
                </div>
            </div>
        </div>
    )
}

// ─── EmptyState ───
function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-slate-800/50 flex items-center justify-center mb-6">
                <svg className="w-10 h-10 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-500 mb-2">No Results Yet</h3>
            <p className="text-sm text-slate-600 max-w-sm leading-relaxed">Upload a cause list PDF to extract structured case data with column-zone parsing</p>
        </div>
    )
}

// ─── App ───
export default function App() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [progress, setProgress] = useState(null)

    const handleUpload = useCallback(async (file) => {
        setLoading(true)
        setError(null)
        setData(null)

        const steps = [
            { percent: 15, message: 'Uploading PDF…', phase: 'extracting' },
            { percent: 40, message: 'Extracting word coordinates…', phase: 'extracting' },
            { percent: 65, message: 'Column zoning & row grouping…', phase: 'zoning' },
            { percent: 85, message: 'Parsing cases with state machine…', phase: 'parsing' },
        ]
        let stepIdx = 0
        setProgress(steps[0])
        const timer = setInterval(() => {
            stepIdx++
            if (stepIdx < steps.length) setProgress(steps[stepIdx])
        }, 1200)

        try {
            const formData = new FormData()
            formData.append('file', file)

            const res = await fetch(`${API_URL}/upload`, { method: 'POST', body: formData })
            if (!res.ok) throw new Error(`Server error: ${res.status}`)

            const json = await res.json()

            clearInterval(timer)
            setProgress({ percent: 100, message: 'Complete!', phase: 'done' })
            await new Promise(r => setTimeout(r, 400))
            setData(json)
        } catch (err) {
            clearInterval(timer)
            setError(err.message)
        } finally {
            setLoading(false)
            setProgress(null)
        }
    }, [])

    return (
        <div className="h-screen bg-slate-950 text-white flex" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
            {/* Left panel — Upload */}
            <div className="w-[380px] min-w-[380px] border-r border-slate-800/70 bg-slate-900/50 flex flex-col">
                <UploadPanel onUpload={handleUpload} loading={loading} />
            </div>

            {/* Right panel — Results */}
            <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900">
                {progress ? (
                    <ProgressBar progress={progress} />
                ) : error ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="max-w-sm text-center">
                            <div className="w-14 h-14 mx-auto rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
                                <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                            </div>
                            <p className="text-sm font-semibold text-red-400 mb-2">Upload Failed</p>
                            <p className="text-xs text-slate-500">{error}</p>
                        </div>
                    </div>
                ) : data ? (
                    <ResultsPanel data={data} />
                ) : (
                    <EmptyState />
                )}
            </div>
        </div>
    )
}
