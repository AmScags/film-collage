import { useRef, useEffect, useState } from 'react'
import { FILM_ASPECT } from '../App.jsx'
import Slot from './Slot.jsx'

export default function PosterPreview({ config, library, slots, onSetSlotImage, onSwapSlots, onSetSlotAnchor, onClearSlot }) {
  const containerRef = useRef(null)
  const [scale, setScale] = useState(1)

  const fh = config.frameWidth / FILM_ASPECT
  const posterW = config.marginLeft + config.columns * config.frameWidth +
    (config.columns - 1) * config.hSpacing + config.marginRight
  const posterH = config.marginTop + config.rows * fh +
    (config.rows - 1) * config.vSpacing + config.marginBottom

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const aw = entry.contentRect.width - 56
      const ah = entry.contentRect.height - 56
      setScale(Math.min(1, aw / posterW, ah / posterH))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [posterW, posterH])

  const slotRect = idx => {
    const col = idx % config.columns
    const row = Math.floor(idx / config.columns)
    return {
      x: config.marginLeft + col * (config.frameWidth + config.hSpacing),
      y: config.marginTop + row * (fh + config.vSpacing),
      w: config.frameWidth,
      h: fh,
    }
  }

  const byId = Object.fromEntries(library.map(img => [img.id, img]))

  return (
    <div ref={containerRef} className="canvas-area">
      {/* Outer div sized to scaled poster dimensions so container scrolls correctly */}
      <div style={{ width: posterW * scale, height: posterH * scale, flexShrink: 0 }}>
        <div
          className="poster"
          style={{
            width: posterW,
            height: posterH,
            background: config.bgColor,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        >
          {slots.map((slot, idx) => (
            <Slot
              key={idx}
              idx={idx}
              rect={slotRect(idx)}
              image={slot.imageId ? byId[slot.imageId] : null}
              vAnchor={slot.vAnchor}
              onSetImage={onSetSlotImage}
              onSwap={onSwapSlots}
              onSetAnchor={onSetSlotAnchor}
              onClear={onClearSlot}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
