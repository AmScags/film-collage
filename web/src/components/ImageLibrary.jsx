import { useRef } from 'react'

export default function ImageLibrary({ library, onAdd, onRemove }) {
  const inputRef = useRef(null)

  const handleDragStart = (e, img) => {
    e.dataTransfer.setData('x-drag-type', 'library')
    e.dataTransfer.setData('x-image-id', img.id)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div className="library-panel">
      <div className="library-header">
        <span className="library-count">Library ({library.length})</span>
        <button className="btn btn-secondary" style={{ padding: '4px 10px' }} onClick={() => inputRef.current?.click()}>
          + Add
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: 'none' }}
          onChange={e => { onAdd(e.target.files); e.target.value = '' }}
        />
      </div>

      <div className="library-grid">
        {library.map(img => (
          <div
            key={img.id}
            className="lib-thumb"
            draggable
            onDragStart={e => handleDragStart(e, img)}
            title={img.name}
          >
            <img src={img.url} alt={img.name} />
            <button className="lib-remove" onClick={() => onRemove(img.id)}>✕</button>
          </div>
        ))}
      </div>
    </div>
  )
}
