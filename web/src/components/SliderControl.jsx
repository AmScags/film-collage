import { useState, useRef, useEffect } from 'react'

export default function SliderControl({ min, max, value, onChange, step = 1 }) {
  const [text, setText] = useState(String(value))
  const repeatRef = useRef(null)

  useEffect(() => { setText(String(value)) }, [value])

  const clamp = v => Math.max(min, Math.min(max, v))

  const commit = v => {
    const c = clamp(v)
    setText(String(c))
    if (c !== value) onChange(c)
  }

  const nudge = delta => commit(value + delta * step)

  const startRepeat = delta => {
    nudge(delta)
    repeatRef.current = setTimeout(() => {
      repeatRef.current = setInterval(() => nudge(delta), 55)
    }, 350)
  }

  const stopRepeat = () => {
    clearTimeout(repeatRef.current)
    clearInterval(repeatRef.current)
  }

  const handleTextKey = e => {
    if (e.key === 'Enter') {
      const v = parseInt(text, 10)
      if (!isNaN(v)) commit(v); else setText(String(value))
    }
  }

  const handleTextBlur = () => {
    const v = parseInt(text, 10)
    if (!isNaN(v)) commit(v); else setText(String(value))
  }

  return (
    <div className="slider-ctrl">
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => { const v = Number(e.target.value); setText(String(v)); onChange(v) }}
      />
      <button className="arrow-btn" onMouseDown={() => startRepeat(-1)} onMouseUp={stopRepeat} onMouseLeave={stopRepeat}>−</button>
      <input
        type="number"
        value={text}
        onChange={e => setText(e.target.value)}
        onBlur={handleTextBlur}
        onKeyDown={handleTextKey}
      />
      <button className="arrow-btn" onMouseDown={() => startRepeat(1)} onMouseUp={stopRepeat} onMouseLeave={stopRepeat}>+</button>
    </div>
  )
}
