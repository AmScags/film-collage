import { useRef } from 'react'
import SliderControl from './SliderControl.jsx'

export default function ConfigPanel({ config, onUpdate, posterW, posterH, onExport, exporting }) {
  const colorInputRef = useRef(null)

  const row = (label, key, min, max, step = 1) => (
    <div className="cfg-row" key={key}>
      <span className="cfg-label">{label}</span>
      <SliderControl min={min} max={max} step={step} value={config[key]} onChange={v => onUpdate(key, v)} />
    </div>
  )

  return (
    <div className="config-panel">
      <div className="section-title">Grid</div>
      {row('Columns', 'columns', 1, 12)}
      {row('Rows', 'rows', 1, 20)}
      {row('Frame width', 'frameWidth', 100, 3000, 10)}
      <div className="poster-dims">{posterW} × {posterH} px</div>

      <div className="section-title">Spacing</div>
      {row('H spacing', 'hSpacing', 0, 500)}
      {row('V spacing', 'vSpacing', 0, 500)}

      <div className="section-title">Margins</div>
      {row('Top', 'marginTop', 0, 1000)}
      {row('Bottom', 'marginBottom', 0, 1000)}
      {row('Left', 'marginLeft', 0, 1000)}
      {row('Right', 'marginRight', 0, 1000)}

      <div className="section-title">Background</div>
      <div className="cfg-row">
        <span className="cfg-label">Color</span>
        <div className="color-row">
          <div
            className="color-swatch"
            style={{ background: config.bgColor }}
            onClick={() => colorInputRef.current?.click()}
          />
          <input
            ref={colorInputRef}
            type="color"
            value={config.bgColor}
            style={{ display: 'none' }}
            onChange={e => onUpdate('bgColor', e.target.value)}
          />
          <input
            className="color-hex"
            type="text"
            value={config.bgColor}
            maxLength={7}
            onChange={e => {
              if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) onUpdate('bgColor', e.target.value)
            }}
          />
        </div>
      </div>

      <div className="export-row">
        <button className="btn btn-primary" disabled={exporting} onClick={() => onExport('png')}>
          {exporting ? 'Exporting…' : 'Export PNG'}
        </button>
        <button className="btn btn-secondary" disabled={exporting} onClick={() => onExport('jpeg')}>
          JPEG
        </button>
      </div>
    </div>
  )
}
