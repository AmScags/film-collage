#!/usr/bin/env python3
"""Film Collage Poster Designer
Arrange favorite 70mm film frames into printable poster layouts.
"""

import sys
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QSlider, QLineEdit, QGroupBox, QFormLayout,
    QFileDialog, QGraphicsView, QGraphicsScene, QGraphicsObject, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QColorDialog,
    QScrollArea, QMenu, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QRectF, QMimeData, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QDrag, QFont, QTransform,
    QIcon, QIntValidator,
)

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
FILM_ASPECT   = 2.20   # 70mm standard width:height
# When frozen by PyInstaller the executable sits in its own dir; use that as base.
if getattr(sys, "frozen", False):
    _BASE = Path(sys.executable).parent
else:
    _BASE = Path(__file__).parent
IMAGES_DIR    = _BASE / "current_images"
EXPORTS_DIR   = _BASE / "exports"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
MIME_PATH     = "application/x-image-path"
MIME_SLOT     = "application/x-slot-index"


# ── Layout config ─────────────────────────────────────────────────────────────
@dataclass
class Config:
    columns:       int = 3
    rows:          int = 4
    frame_width:   int = 900   # px; height is always frame_width / 2.20
    margin_top:    int = 200
    margin_bottom: int = 200
    margin_left:   int = 150
    margin_right:  int = 150
    h_spacing:     int = 80
    v_spacing:     int = 80
    bg_color:      str = "#000000"

    @property
    def frame_height(self) -> float:
        return self.frame_width / FILM_ASPECT

    @property
    def poster_width(self) -> int:
        return round(
            self.margin_left + self.columns * self.frame_width
            + (self.columns - 1) * self.h_spacing + self.margin_right
        )

    @property
    def poster_height(self) -> int:
        return round(
            self.margin_top + self.rows * self.frame_height
            + (self.rows - 1) * self.v_spacing + self.margin_bottom
        )

    def compute(self):
        """Returns (frame_width, frame_height, rows) — same shape as callers expect."""
        return float(self.frame_width), self.frame_height, self.rows

    def total_slots(self) -> int:
        return self.columns * self.rows

    def slot_rect(self, idx: int) -> QRectF:
        fw  = float(self.frame_width)
        fh  = self.frame_height
        col = idx % self.columns
        row = idx // self.columns
        x   = self.margin_left + col * (fw + self.h_spacing)
        y   = self.margin_top  + row * (fh + self.v_spacing)
        return QRectF(x, y, fw, fh)


# ── Image slot (graphics item) ────────────────────────────────────────────────
class SlotItem(QGraphicsObject):
    """A single 70mm-ratio image slot inside the poster scene."""

    def __init__(self, idx: int, rect: QRectF, parent=None):
        super().__init__(parent)
        self.idx         = idx
        self._rect       = rect
        self.image_path: Optional[str] = None
        self._pixmap:    Optional[QPixmap] = None
        self._highlight  = False
        self.v_anchor    = 0.5   # 0.0 = top, 0.5 = center, 1.0 = bottom
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)

    # ── Geometry / image ──────────────────────────────────────────────────────

    def set_rect(self, r: QRectF):
        self.prepareGeometryChange()
        self._rect = r

    def set_image(self, path: Optional[str]):
        self.image_path = path
        self._pixmap    = QPixmap(path) if path else None
        self.update()

    def boundingRect(self) -> QRectF:
        return self._rect

    # ── Painting ──────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None):
        r = self._rect
        if self._pixmap and not self._pixmap.isNull():
            pm = self._pixmap
            sw, sh = r.width(), r.height()
            scale  = max(sw / pm.width(), sh / pm.height())
            dw     = pm.width()  * scale
            dh     = pm.height() * scale
            dx     = r.x() + (sw - dw) / 2          # always center horizontally
            dy     = r.y() + (sh - dh) * self.v_anchor
            painter.setClipRect(r)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(QRectF(dx, dy, dw, dh), pm, QRectF(pm.rect()))
            painter.setClipping(False)
        else:
            painter.fillRect(r, QColor(28, 28, 30))
            painter.setPen(QPen(QColor(65, 65, 70), 1.5))
            painter.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
            painter.setPen(QColor(85, 85, 90))
            f = QFont()
            f.setPointSizeF(max(7.0, r.height() * 0.07))
            painter.setFont(f)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, f"#{self.idx + 1}")

        if self._highlight:
            painter.fillRect(r, QColor(80, 170, 255, 55))
            painter.setPen(QPen(QColor(80, 170, 255), 2.5))
            painter.drawRect(r.adjusted(1, 1, -1, -1))

    # ── Mouse / drag initiation ───────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            view  = self.scene().views()[0]
            drag  = QDrag(view)
            mime  = QMimeData()
            mime.setData(MIME_SLOT, str(self.idx).encode())
            mime.setData(MIME_PATH, self.image_path.encode())
            thumb = self._pixmap.scaled(
                160, 73,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            drag.setPixmap(thumb)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene = self.scene()
            if hasattr(scene, "file_requested"):
                scene.file_requested.emit(self.idx)

    def contextMenuEvent(self, event):
        if not self.image_path:
            return
        menu  = QMenu()
        clear = menu.addAction("Clear Slot")
        menu.addSeparator()

        crop_menu = menu.addMenu("Crop Position")
        top_act    = crop_menu.addAction("Top")
        center_act = crop_menu.addAction("Center")
        bot_act    = crop_menu.addAction("Bottom")
        crop_menu.addSeparator()
        custom_act = crop_menu.addAction(f"Custom…  ({int(self.v_anchor * 100)}%)")

        for act_, val in ((top_act, 0.0), (center_act, 0.5), (bot_act, 1.0)):
            act_.setCheckable(True)
            act_.setChecked(self.v_anchor == val)

        act = menu.exec(event.screenPos())
        if act == clear:
            self.set_image(None)
        elif act == top_act:
            self.v_anchor = 0.0;  self.update()
        elif act == center_act:
            self.v_anchor = 0.5;  self.update()
        elif act == bot_act:
            self.v_anchor = 1.0;  self.update()
        elif act == custom_act:
            self._show_crop_dialog(event.screenPos())

    def _show_crop_dialog(self, screen_pos):
        dlg = QDialog()
        dlg.setWindowTitle("Crop Position")
        dlg.setFixedWidth(280)

        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        info = QLabel("0% = show top  ·  50% = center  ·  100% = show bottom")
        info.setStyleSheet("color:#aaa; font-size:10px;")
        lay.addWidget(info)

        sl = SliderControl(0, 100, int(self.v_anchor * 100))
        lay.addWidget(sl)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.v_anchor = sl.value() / 100.0
            self.update()

    # ── Drop target ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_PATH):
            self._highlight = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._highlight = False
        self.update()

    def dropEvent(self, event):
        self._highlight = False
        self.update()
        mime     = event.mimeData()
        path     = mime.data(MIME_PATH).data().decode() if mime.hasFormat(MIME_PATH) else None
        src_slot = int(mime.data(MIME_SLOT).data().decode()) if mime.hasFormat(MIME_SLOT) else None
        if path:
            self.scene().handle_drop(self.idx, src_slot, path)
        event.acceptProposedAction()


# ── Poster scene ──────────────────────────────────────────────────────────────
class PosterScene(QGraphicsScene):
    file_requested = pyqtSignal(int)

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.cfg   = cfg
        self.slots: List[SlotItem] = []
        self.rebuild()

    def rebuild(self):
        """Recreate all slots, preserving existing image assignments and anchors."""
        saved_paths   = [s.image_path for s in self.slots]
        saved_anchors = [s.v_anchor   for s in self.slots]
        for s in self.slots:
            self.removeItem(s)
        self.slots.clear()

        for i in range(self.cfg.total_slots()):
            item = SlotItem(i, self.cfg.slot_rect(i))
            self.addItem(item)
            if i < len(saved_paths):
                item.set_image(saved_paths[i])
                item.v_anchor = saved_anchors[i]
            self.slots.append(item)

        self.setSceneRect(0, 0, self.cfg.poster_width, self.cfg.poster_height)

    def update_layout(self):
        """Update slot geometry; rebuild only if count changed."""
        if self.cfg.total_slots() != len(self.slots):
            self.rebuild()
            return
        for i, slot in enumerate(self.slots):
            slot.set_rect(self.cfg.slot_rect(i))
            slot.update()
        self.setSceneRect(0, 0, self.cfg.poster_width, self.cfg.poster_height)

    def handle_drop(self, dst: int, src: Optional[int], path: str):
        dst_slot = self.slots[dst]
        if src is not None and src != dst and src < len(self.slots):
            src_slot = self.slots[src]
            old_dst  = dst_slot.image_path
            dst_slot.set_image(path)
            src_slot.set_image(old_dst)
        else:
            dst_slot.set_image(path)

    def get_assignment(self) -> List[Optional[str]]:
        return [s.image_path for s in self.slots]

    def get_anchors(self) -> List[float]:
        return [s.v_anchor for s in self.slots]

    def clear_all(self):
        for s in self.slots:
            s.set_image(None)


# ── Poster view (canvas) ──────────────────────────────────────────────────────
class PosterView(QGraphicsView):
    def __init__(self, poster_scene: PosterScene, parent=None):
        super().__init__(poster_scene, parent)
        self._ps = poster_scene
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform,
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setBackgroundBrush(QBrush(QColor(35, 35, 37)))
        self._zoom = 1.0

    def drawBackground(self, painter: QPainter, rect):
        super().drawBackground(painter, rect)
        painter.fillRect(self._ps.sceneRect(), QColor(self._ps.cfg.bg_color))

    def zoom_in(self):  self._apply_zoom(self._zoom * 1.25)
    def zoom_out(self): self._apply_zoom(self._zoom / 1.25)

    def zoom_fit(self):
        self.fitInView(self._ps.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()

    def _apply_zoom(self, z: float):
        self._zoom = max(0.04, min(z, 12.0))
        self.setTransform(QTransform().scale(self._zoom, self._zoom))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
        else:
            super().wheelEvent(event)


# ── Image library ─────────────────────────────────────────────────────────────
class ThumbItem(QListWidgetItem):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        pm = QPixmap(str(path)).scaled(
            110, 50,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setIcon(QIcon(pm))
        self.setText(path.stem[:22])
        self.setToolTip(path.name)
        self.setSizeHint(QSize(120, 82))


class LibraryList(QListWidget):
    """QListWidget that initiates custom MIME drags to the poster slots."""

    def startDrag(self, actions):
        item = self.currentItem()
        if not isinstance(item, ThumbItem):
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_PATH, str(item.path).encode())
        pm = QPixmap(str(item.path)).scaled(
            160, 73,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(pm)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class ImageLibraryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        title = QLabel("Image Library")
        title.setStyleSheet("font-weight:bold; font-size:13px; padding:2px;")
        lay.addWidget(title)

        self.list = LibraryList()
        self.list.setIconSize(QSize(110, 50))
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setSpacing(4)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(False)
        lay.addWidget(self.list, 1)

        add = QPushButton("+ Add Images")
        add.clicked.connect(self._add_images)
        rem = QPushButton("Remove Selected")
        rem.clicked.connect(self._remove)
        lay.addWidget(add)
        lay.addWidget(rem)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#888; font-size:11px;")
        lay.addWidget(self._count_lbl)

    def refresh(self):
        IMAGES_DIR.mkdir(exist_ok=True)
        self.list.clear()
        imgs = sorted(
            p for p in IMAGES_DIR.iterdir()
            if p.suffix.lower() in SUPPORTED_EXT
        )
        for p in imgs:
            self.list.addItem(ThumbItem(p))
        self._count_lbl.setText(f"{len(imgs)} image(s)")

    def _add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Images to Library", "",
            "Images (*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.webp)",
        )
        if not paths:
            return
        IMAGES_DIR.mkdir(exist_ok=True)
        for p in paths:
            dst = IMAGES_DIR / Path(p).name
            if not dst.exists():
                shutil.copy2(p, dst)
        self.refresh()

    def _remove(self):
        item = self.list.currentItem()
        if not isinstance(item, ThumbItem):
            return
        if QMessageBox.question(
            self, "Remove Image",
            f"Remove '{item.path.name}' from library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            item.path.unlink(missing_ok=True)
            self.refresh()


# ── Controls panel ────────────────────────────────────────────────────────────
class SliderControl(QWidget):
    """Slider + editable spinbox + ±1 arrow buttons for fine control."""

    valueChanged = pyqtSignal(int)

    def __init__(self, lo: int, hi: int, val: int, parent=None):
        super().__init__(parent)
        self._lo   = lo
        self._hi   = hi
        self._busy = False

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(lo, hi)
        self._slider.setValue(val)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(max(1, (hi - lo) // 20))

        self._edit = QLineEdit(str(val))
        self._edit.setFixedWidth(52)
        self._edit.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._edit.setValidator(QIntValidator(lo, hi))
        self._edit.editingFinished.connect(self._commit_edit)

        def arrow(symbol: str, delta: int) -> QPushButton:
            b = QPushButton(symbol)
            b.setFixedSize(20, 22)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(350)
            b.setAutoRepeatInterval(55)
            b.clicked.connect(lambda: self._nudge(delta))
            return b

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        row.addWidget(self._slider, 1)
        row.addWidget(arrow("−", -1))
        row.addWidget(self._edit)
        row.addWidget(arrow("+", 1))

        self._slider.valueChanged.connect(self._on_slider)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, v: int):
        v = max(self._lo, min(self._hi, v))
        if self._busy:
            return
        self._busy = True
        self._slider.setValue(v)
        self._edit.setText(str(v))
        self._busy = False
        self.valueChanged.emit(v)

    def _on_slider(self, v: int):
        if self._busy:
            return
        self._busy = True
        self._edit.setText(str(v))
        self._busy = False
        self.valueChanged.emit(v)

    def _commit_edit(self):
        try:
            self.setValue(int(self._edit.text()))
        except ValueError:
            self._edit.setText(str(self.value()))

    def _nudge(self, delta: int):
        self.setValue(self.value() + delta)


class ControlsPanel(QWidget):
    config_changed = pyqtSignal()

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()
        self.setFixedWidth(300)

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(10)

        def group(title, rows):
            g   = QGroupBox(title)
            frm = QFormLayout(g)
            frm.setSpacing(5)
            frm.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            for label, widget in rows:
                frm.addRow(label, widget)
            return g

        # Grid — columns and rows set the layout; poster size is derived
        self.sc_cols = SliderControl(1, 12, self.cfg.columns)
        self.sc_rows = SliderControl(1, 16, self.cfg.rows)
        outer.addWidget(group("Grid", [
            ("Columns:", self.sc_cols),
            ("Rows:",    self.sc_rows),
        ]))

        # Frame width (height always follows from 2.20:1)
        self.sc_fw = SliderControl(50, 4000, self.cfg.frame_width)
        outer.addWidget(group("Frame Width (px)", [("Width:", self.sc_fw)]))

        # Spacing
        self.sc_hs = SliderControl(0, 600, self.cfg.h_spacing)
        self.sc_vs = SliderControl(0, 600, self.cfg.v_spacing)
        outer.addWidget(group("Spacing (px)", [
            ("Horizontal:", self.sc_hs),
            ("Vertical:",   self.sc_vs),
        ]))

        # Margins
        self.sc_mt = SliderControl(0, 2000, self.cfg.margin_top)
        self.sc_mb = SliderControl(0, 2000, self.cfg.margin_bottom)
        self.sc_ml = SliderControl(0, 1500, self.cfg.margin_left)
        self.sc_mr = SliderControl(0, 1500, self.cfg.margin_right)
        outer.addWidget(group("Margins (px)", [
            ("Top:",    self.sc_mt),
            ("Bottom:", self.sc_mb),
            ("Left:",   self.sc_ml),
            ("Right:",  self.sc_mr),
        ]))

        # Background color
        self._bg_btn = QPushButton()
        self._bg_btn.setFixedHeight(26)
        self._refresh_bg_btn()
        self._bg_btn.clicked.connect(self._pick_color)
        outer.addWidget(group("Background", [("Color:", self._bg_btn)]))

        # Derived info readout
        self._info = QLabel()
        self._info.setStyleSheet("color:#999; font-size:10px;")
        self._info.setWordWrap(True)
        outer.addWidget(self._info)

        outer.addStretch()
        scroll.setWidget(inner)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

        for sc in (self.sc_cols, self.sc_rows, self.sc_fw,
                   self.sc_hs, self.sc_vs,
                   self.sc_mt, self.sc_mb, self.sc_ml, self.sc_mr):
            sc.valueChanged.connect(self._emit)

    def _emit(self):
        self.cfg.columns       = self.sc_cols.value()
        self.cfg.rows          = self.sc_rows.value()
        self.cfg.frame_width   = self.sc_fw.value()
        self.cfg.h_spacing     = self.sc_hs.value()
        self.cfg.v_spacing     = self.sc_vs.value()
        self.cfg.margin_top    = self.sc_mt.value()
        self.cfg.margin_bottom = self.sc_mb.value()
        self.cfg.margin_left   = self.sc_ml.value()
        self.cfg.margin_right  = self.sc_mr.value()
        self._update_info()
        self.config_changed.emit()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.cfg.bg_color), self, "Background Color")
        if c.isValid():
            self.cfg.bg_color = c.name()
            self._refresh_bg_btn()
            self.config_changed.emit()

    def _refresh_bg_btn(self):
        self._bg_btn.setStyleSheet(
            f"background:{self.cfg.bg_color}; border:1px solid #555;")

    def update_info(self):
        self._update_info()

    def _update_info(self):
        fh    = self.cfg.frame_height
        total = self.cfg.total_slots()
        self._info.setText(
            f"Poster:  {self.cfg.poster_width} × {self.cfg.poster_height} px\n"
            f"Frame:   {self.cfg.frame_width} × {fh:.0f} px  (2.20:1)\n"
            f"Slots:   {self.cfg.columns} cols × {self.cfg.rows} rows = {total}"
        )


# ── Export ────────────────────────────────────────────────────────────────────
def export_poster(
    cfg: Config,
    assignment: List[Optional[str]],
    out_path: str,
    anchors: Optional[List[float]] = None,
):
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow not installed — run: pip install Pillow")

    bg  = QColor(cfg.bg_color)
    img = PILImage.new(
        "RGB",
        (cfg.poster_width, cfg.poster_height),
        (bg.red(), bg.green(), bg.blue()),
    )
    sw, sh, _ = cfg.compute()
    sw_i, sh_i = round(sw), round(sh)

    for i, path in enumerate(assignment):
        if not path:
            continue
        v_anchor = (anchors[i] if anchors and i < len(anchors) else 0.5)
        r        = cfg.slot_rect(i)
        x, y     = round(r.x()), round(r.y())
        frm      = PILImage.open(path).convert("RGB")
        fw, fh   = frm.size
        sc       = max(sw_i / fw, sh_i / fh)
        nw, nh   = round(fw * sc), round(fh * sc)
        frm      = frm.resize((nw, nh), PILImage.LANCZOS)
        cx       = (nw - sw_i) // 2
        cy       = round((nh - sh_i) * v_anchor)
        cy       = max(0, min(cy, nh - sh_i))
        frm      = frm.crop((cx, cy, cx + sw_i, cy + sh_i))
        img.paste(frm, (x, y))

    img.save(out_path)


# ── Main window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Film Collage Poster Designer")
        self.resize(1440, 900)
        self.cfg = Config()
        self._build()

    def _build(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # ── Left: image library ───────────────────────────────────────────
        self.library = ImageLibraryPanel()
        self.library.setMinimumWidth(140)
        self.library.setMaximumWidth(215)
        splitter.addWidget(self.library)

        # ── Center: poster canvas ─────────────────────────────────────────
        center = QWidget()
        cv     = QVBoxLayout(center)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        # Toolbar above canvas
        tb = QWidget()
        tl = QHBoxLayout(tb)
        tl.setContentsMargins(6, 4, 6, 4)
        tl.setSpacing(6)

        for txt, fn in [("Fit", self._fit), ("＋", self._zi), ("－", self._zo)]:
            b = QPushButton(txt)
            b.setFixedSize(36, 26)
            b.clicked.connect(fn)
            tl.addWidget(b)

        self._zoom_lbl = QLabel("—")
        self._zoom_lbl.setStyleSheet("color:#aaa; font-size:11px; padding:0 4px;")
        tl.addWidget(self._zoom_lbl)
        tl.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet("color:#c88;")
        clear_btn.clicked.connect(self._clear_all)
        tl.addWidget(clear_btn)

        exp_btn = QPushButton("Export Poster →")
        exp_btn.setFixedHeight(26)
        exp_btn.setStyleSheet(
            "background:#26824a; color:white; font-weight:bold; border-radius:3px;")
        exp_btn.clicked.connect(self._export)
        tl.addWidget(exp_btn)

        cv.addWidget(tb)

        self.scene = PosterScene(self.cfg)
        self.view  = PosterView(self.scene)
        self.scene.file_requested.connect(self._open_for_slot)
        cv.addWidget(self.view, 1)
        splitter.addWidget(center)

        # ── Right: controls ───────────────────────────────────────────────
        self.controls = ControlsPanel(self.cfg)
        self.controls.config_changed.connect(self._on_cfg)
        self.controls.update_info()
        splitter.addWidget(self.controls)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        self.statusBar().showMessage(
            "Drag images from the library to slots  •  "
            "Double-click a slot to pick a file  •  "
            "Drag slots to swap  •  Ctrl+Scroll to zoom  •  "
            "Right-click slot to clear"
        )

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_cfg(self):
        self.scene.update_layout()
        self.view.update()

    def _fit(self):
        self.view.zoom_fit()
        self._zoom_lbl.setText(f"{self.view._zoom * 100:.0f}%")

    def _zi(self):
        self.view.zoom_in()
        self._zoom_lbl.setText(f"{self.view._zoom * 100:.0f}%")

    def _zo(self):
        self.view.zoom_out()
        self._zoom_lbl.setText(f"{self.view._zoom * 100:.0f}%")

    def _clear_all(self):
        if QMessageBox.question(
            self, "Clear All Slots",
            "Remove all images from slots?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self.scene.clear_all()

    def _open_for_slot(self, idx: int):
        """Double-click on slot: pick file(s) and fill starting from that slot."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Image(s)", "",
            "Images (*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.webp)",
        )
        if not paths:
            return
        IMAGES_DIR.mkdir(exist_ok=True)
        for offset, p in enumerate(paths):
            dst = IMAGES_DIR / Path(p).name
            if not dst.exists():
                shutil.copy2(p, dst)
            slot_idx = idx + offset
            if slot_idx < len(self.scene.slots):
                self.scene.slots[slot_idx].set_image(str(dst))
        self.library.refresh()

    def _export(self):
        if not PIL_AVAILABLE:
            QMessageBox.warning(
                self, "Missing dependency",
                "Pillow is not installed.\n\nRun:\n  pip install Pillow",
            )
            return
        EXPORTS_DIR.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Poster",
            str(EXPORTS_DIR / "poster.png"),
            "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if not path:
            return
        try:
            export_poster(self.cfg, self.scene.get_assignment(), path,
                          self.scene.get_anchors())
            QMessageBox.information(self, "Export complete", f"Saved to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    EXPORTS_DIR.mkdir(exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = app.palette()
    for role, color in {
        pal.ColorRole.Window:          QColor(45, 45, 48),
        pal.ColorRole.WindowText:      QColor(215, 215, 215),
        pal.ColorRole.Base:            QColor(28, 28, 30),
        pal.ColorRole.AlternateBase:   QColor(36, 36, 38),
        pal.ColorRole.Button:          QColor(58, 58, 62),
        pal.ColorRole.ButtonText:      QColor(215, 215, 215),
        pal.ColorRole.Highlight:       QColor(42, 130, 218),
        pal.ColorRole.HighlightedText: QColor(255, 255, 255),
        pal.ColorRole.Text:            QColor(215, 215, 215),
        pal.ColorRole.BrightText:      QColor(255, 255, 255),
        pal.ColorRole.ToolTipBase:     QColor(50, 50, 53),
        pal.ColorRole.ToolTipText:     QColor(200, 200, 200),
    }.items():
        pal.setColor(role, color)
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    QTimer.singleShot(200, win._fit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
