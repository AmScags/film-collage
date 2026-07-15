import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import CropDialog from './CropDialog.jsx'

export default function Slot({ idx, rect, image, vAnchor, onSetImage, onSwap, onSetAnchor, onClear }) {
  const [dragOver, setDragOver] = useState(false)
  const [menu, setMenu] = useState(null)   // { x, y }
  const [cropOpen, setCropOpen] = useState(false)

  const handleDragStart = e => {
    if (!image) { e.preventDefault(); return }
    e.dataTransfer.setData('x-drag-type', 'slot')
    e.dataTransfer.setData('x-slot-index', String(idx))
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = e => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(true)
  }

  const handleDrop = e => {
    e.preventDefault()
    setDragOver(false)
    const type = e.dataTransfer.getData('x-drag-type')
    if (type === 'library') {
      onSetImage(idx, e.dataTransfer.getData('x-image-id'))
    } else if (type === 'slot') {
      const from = Number(e.dataTransfer.getData('x-slot-index'))
      if (from !== idx) onSwap(from, idx)
    }
  }

  const handleContextMenu = e => {
    if (!image) return
    e.preventDefault()
    // Keep menu within viewport
    const mx = Math.min(e.clientX, window.innerWidth - 170)
    const my = Math.min(e.clientY, window.innerHeight - 180)
    setMenu({ x: mx, y: my })
  }

  return (
    <>
      <div
        className={`slot${dragOver ? ' drag-over' : ''}${!image ? ' empty' : ''}`}
        style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onContextMenu={handleContextMenu}
      >
        {image ? (
          <>
            <img src={image.url} alt="" style={{ objectPosition: `center ${vAnchor * 100}%` }} />
            <div
              className="slot-drag-layer"
              draggable
              onDragStart={handleDragStart}
            />
          </>
        ) : (
          <span>+</span>
        )}
      </div>

      {menu && createPortal(
        <ContextMenu
          x={menu.x} y={menu.y}
          vAnchor={vAnchor}
          onClose={() => setMenu(null)}
          onSetAnchor={v => { onSetAnchor(idx, v); setMenu(null) }}
          onCustom={() => { setMenu(null); setCropOpen(true) }}
          onClear={() => { onClear(idx); setMenu(null) }}
        />,
        document.body
      )}

      {cropOpen && createPortal(
        <CropDialog
          vAnchor={vAnchor}
          onApply={v => onSetAnchor(idx, v)}
          onClose={() => setCropOpen(false)}
        />,
        document.body
      )}
    </>
  )
}

function ContextMenu({ x, y, vAnchor, onClose, onSetAnchor, onCustom, onClear }) {
  const ref = useRef(null)

  useEffect(() => {
    const handler = e => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    // Defer so the right-click event that opened us doesn't immediately close us
    const id = setTimeout(() => document.addEventListener('mousedown', handler), 0)
    return () => {
      clearTimeout(id)
      document.removeEventListener('mousedown', handler)
    }
  }, [onClose])

  const anchors = [
    { label: 'Top', value: 0.0 },
    { label: 'Center', value: 0.5 },
    { label: 'Bottom', value: 1.0 },
  ]

  return (
    <div ref={ref} className="ctx-menu" style={{ left: x, top: y }}>
      <div className="ctx-label">Crop Position</div>
      {anchors.map(({ label, value }) => (
        <div key={label} className="ctx-item" onClick={() => onSetAnchor(value)}>
          <span className="ctx-check">{Math.abs(vAnchor - value) < 0.01 ? '✓' : ''}</span>
          {label}
        </div>
      ))}
      <div className="ctx-item" onClick={onCustom}>
        <span className="ctx-check" />
        Custom… ({Math.round(vAnchor * 100)}%)
      </div>
      <div className="ctx-sep" />
      <div className="ctx-item ctx-danger" onClick={onClear}>
        <span className="ctx-check" />
        Clear Slot
      </div>
    </div>
  )
}
