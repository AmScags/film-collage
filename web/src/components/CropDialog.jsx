import { useState } from 'react'
import SliderControl from './SliderControl.jsx'

export default function CropDialog({ vAnchor, onApply, onClose }) {
  const [val, setVal] = useState(Math.round(vAnchor * 100))

  const confirm = () => {
    onApply(val / 100)
    onClose()
  }

  return (
    <div className="overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <h3>Crop Position</h3>
        <p className="modal-hint">0% = top &nbsp;·&nbsp; 50% = center &nbsp;·&nbsp; 100% = bottom</p>
        <SliderControl min={0} max={100} value={val} onChange={setVal} />
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={confirm}>Apply</button>
        </div>
      </div>
    </div>
  )
}
