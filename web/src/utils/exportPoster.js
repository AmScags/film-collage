const FILM_ASPECT = 2.20

export async function exportPoster(config, slots, library, format = 'png') {
  const fh = config.frameWidth / FILM_ASPECT
  const posterW = Math.round(
    config.marginLeft + config.columns * config.frameWidth +
    (config.columns - 1) * config.hSpacing + config.marginRight
  )
  const posterH = Math.round(
    config.marginTop + config.rows * fh +
    (config.rows - 1) * config.vSpacing + config.marginBottom
  )

  const canvas = document.createElement('canvas')
  canvas.width = posterW
  canvas.height = posterH
  const ctx = canvas.getContext('2d')

  ctx.fillStyle = config.bgColor
  ctx.fillRect(0, 0, posterW, posterH)

  const byId = Object.fromEntries(library.map(img => [img.id, img]))

  const imageEls = await Promise.all(
    slots.map(slot => {
      if (!slot.imageId) return Promise.resolve(null)
      const entry = byId[slot.imageId]
      return entry ? loadImage(entry.url) : Promise.resolve(null)
    })
  )

  slots.forEach((slot, idx) => {
    const el = imageEls[idx]
    if (!el) return
    const col = idx % config.columns
    const row = Math.floor(idx / config.columns)
    const dx = Math.round(config.marginLeft + col * (config.frameWidth + config.hSpacing))
    const dy = Math.round(config.marginTop + row * (fh + config.vSpacing))
    drawCropped(ctx, el, dx, dy, config.frameWidth, Math.round(fh), slot.vAnchor)
  })

  return new Promise(resolve => {
    const mime = format === 'jpeg' ? 'image/jpeg' : 'image/png'
    const ext  = format === 'jpeg' ? 'jpg' : 'png'
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `poster.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      resolve()
    }, mime, format === 'jpeg' ? 0.95 : undefined)
  })
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function drawCropped(ctx, img, dx, dy, dw, dh, vAnchor) {
  const iw = img.naturalWidth, ih = img.naturalHeight
  // Scale to fill slot: try scaling to slot width first
  let scale = dw / iw
  if (ih * scale < dh) scale = dh / ih   // image too short → scale to height instead

  const srcW = Math.round(dw / scale)
  const srcH = Math.round(dh / scale)
  const cx = Math.round((iw - srcW) / 2)
  const cy = Math.max(0, Math.min(Math.round((ih - srcH) * vAnchor), ih - srcH))

  ctx.drawImage(img, cx, cy, srcW, srcH, dx, dy, dw, dh)
}
