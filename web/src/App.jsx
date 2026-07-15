import { useState, useCallback, useRef } from 'react'
import ConfigPanel from './components/ConfigPanel.jsx'
import ImageLibrary from './components/ImageLibrary.jsx'
import PosterPreview from './components/PosterPreview.jsx'
import { exportPoster } from './utils/exportPoster.js'

export const FILM_ASPECT = 2.20

const DEFAULT_CONFIG = {
  columns: 3,
  rows: 4,
  frameWidth: 900,
  marginTop: 200,
  marginBottom: 200,
  marginLeft: 150,
  marginRight: 150,
  hSpacing: 80,
  vSpacing: 80,
  bgColor: '#000000',
}

function makeSlot() {
  return { imageId: null, vAnchor: 0.5 }
}

export function posterDims(cfg) {
  const fh = cfg.frameWidth / FILM_ASPECT
  const w = cfg.marginLeft + cfg.columns * cfg.frameWidth +
    (cfg.columns - 1) * cfg.hSpacing + cfg.marginRight
  const h = cfg.marginTop + cfg.rows * fh +
    (cfg.rows - 1) * cfg.vSpacing + cfg.marginBottom
  return { w: Math.round(w), h: Math.round(h), fh }
}

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [library, setLibrary] = useState([])
  const [slots, setSlots] = useState(() =>
    Array.from({ length: DEFAULT_CONFIG.rows * DEFAULT_CONFIG.columns }, makeSlot)
  )
  const [exporting, setExporting] = useState(false)
  const nextId = useRef(0)

  const updateConfig = useCallback((key, value) => {
    setConfig(prev => {
      const next = { ...prev, [key]: value }
      if (key === 'rows' || key === 'columns') {
        const total = next.rows * next.columns
        setSlots(prev =>
          Array.from({ length: total }, (_, i) => i < prev.length ? prev[i] : makeSlot())
        )
      }
      return next
    })
  }, [])

  const addImages = useCallback(files => {
    const entries = Array.from(files).map(f => ({
      id: `img-${nextId.current++}`,
      url: URL.createObjectURL(f),
      name: f.name,
    }))
    setLibrary(prev => [...prev, ...entries])
  }, [])

  const removeFromLibrary = useCallback(id => {
    setLibrary(prev => prev.filter(img => img.id !== id))
    setSlots(prev => prev.map(s => s.imageId === id ? { ...s, imageId: null } : s))
  }, [])

  const setSlotImage = useCallback((idx, imageId) => {
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, imageId } : s))
  }, [])

  const swapSlots = useCallback((a, b) => {
    setSlots(prev => {
      const next = [...prev]
      ;[next[a], next[b]] = [next[b], next[a]]
      return next
    })
  }, [])

  const setSlotAnchor = useCallback((idx, vAnchor) => {
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, vAnchor } : s))
  }, [])

  const clearSlot = useCallback(idx => {
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, imageId: null } : s))
  }, [])

  const doExport = useCallback(async format => {
    setExporting(true)
    try {
      await exportPoster(config, slots, library, format)
    } finally {
      setExporting(false)
    }
  }, [config, slots, library])

  const dims = posterDims(config)

  return (
    <div className="app">
      <div className="sidebar">
        <div className="app-title">Film Collage</div>
        <ConfigPanel
          config={config}
          onUpdate={updateConfig}
          posterW={dims.w}
          posterH={dims.h}
          onExport={doExport}
          exporting={exporting}
        />
        <ImageLibrary library={library} onAdd={addImages} onRemove={removeFromLibrary} />
      </div>
      <PosterPreview
        config={config}
        library={library}
        slots={slots}
        onSetSlotImage={setSlotImage}
        onSwapSlots={swapSlots}
        onSetSlotAnchor={setSlotAnchor}
        onClearSlot={clearSlot}
      />
    </div>
  )
}
