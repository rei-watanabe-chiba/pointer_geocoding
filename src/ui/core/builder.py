"""
/***************************************************************************
 PointerGeocoding Plugin - CoreUI builder (PanelSpec -> real widgets)
 ***************************************************************************/

T-0045: CoreUIBuilder.build(spec, parent) turns a declarative PanelSpec
(field_spec.py) into a real vertical stack of PyQt widgets, one row per
FieldSpec, reusing UIStyleHelper's existing row/button/table helpers
(ui/style.py) as the actual widget factories. This module is a thin layer
over ui/style.py, not a replacement for it.

Event wiring is deferred: building a panel never touches the caller's
business-logic methods directly. Instead, each field that declares an
on_click/on_change hook name registers a "pending connector" closure; the
caller later attaches its real callback via ``BuiltPanel.bind(hook_name,
callback)``. This is what lets tab1_image_schema.py stay a pure data file
with zero references to Tab1GeorefMixin's methods.
"""
from typing import Callable, Dict, List, Optional

from qgis.gui import QgsFilterLineEdit
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ..style import UIStyleHelper
from ..constants import UIConfig
from .field_spec import ButtonDef, PanelSpec, WidgetType

_STYLE_APPLIERS = {
    "primary": UIStyleHelper.set_primary_button,
    "accent": UIStyleHelper.set_accent_button,
    "success": UIStyleHelper.set_success_button,
}

_RESIZE_MODES = {
    "contents": QHeaderView.ResizeToContents,
    "stretch": QHeaderView.Stretch,
}


class BuiltPanel:
    """Result of CoreUIBuilder.build(): the container widget plus lookup
    tables for retrieving individual field widgets/rows and binding event
    hooks to caller-supplied callbacks.
    """

    def __init__(
        self,
        widget: QWidget,
        field_widgets: Dict[str, QWidget],
        row_widgets: Dict[str, QWidget],
        buttons_lists: Dict[str, List[QPushButton]],
        pending_hooks: Dict[str, List[Callable[[Callable], None]]],
    ) -> None:
        self.widget = widget
        self._field_widgets = field_widgets
        self._row_widgets = row_widgets
        self._buttons_lists = buttons_lists
        self._pending_hooks = pending_hooks

    def get(self, field_id: str) -> QWidget:
        """Return the primary built widget registered under ``field_id``."""
        return self._field_widgets[field_id]

    def get_row(self, field_id: str) -> QWidget:
        """Return the row container widget for ``field_id`` (what callers
        show()/hide() to toggle an entire row, e.g. Tab1's row_edit_layer).
        """
        return self._row_widgets[field_id]

    def get_buttons(self, field_id: str) -> List[QPushButton]:
        """Return the button list for a SEGMENTED_TOGGLE field."""
        return self._buttons_lists[field_id]

    def bind(self, hook_name: str, callback: Callable) -> None:
        """Attach ``callback`` to every pending connector registered under
        ``hook_name`` (e.g. a FieldSpec's on_click/on_change, or a
        ButtonDef's on_click). No-op if no field declared that hook name.
        """
        for connector in self._pending_hooks.get(hook_name, []):
            connector(callback)


class CoreUIBuilder:
    """Builds a PanelSpec into a real QWidget tree. Stateless: all state
    lives in the returned BuiltPanel.
    """

    @classmethod
    def build(cls, spec: PanelSpec, parent: Optional[QWidget] = None) -> BuiltPanel:
        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(*spec.margins)
        layout.setSpacing(spec.spacing)

        field_widgets: Dict[str, QWidget] = {}
        row_widgets: Dict[str, QWidget] = {}
        buttons_lists: Dict[str, List[QPushButton]] = {}
        pending_hooks: Dict[str, List[Callable[[Callable], None]]] = {}

        def register_hook(hook_name: Optional[str], connector: Callable[[Callable], None]) -> None:
            if hook_name:
                pending_hooks.setdefault(hook_name, []).append(connector)

        for f in spec.fields:
            builder_fn = cls._BUILDERS[f.widget_type]
            row_widget = builder_fn(
                f, container, field_widgets, buttons_lists, register_hook
            )
            row_widgets[f.field_id] = row_widget
            layout.addWidget(row_widget)
            if not f.visible:
                row_widget.hide()

        panel = BuiltPanel(container, field_widgets, row_widgets, buttons_lists, pending_hooks)
        for rule in spec.rules:
            rule.apply(panel)
        return panel

    # -- per-WidgetType builders -------------------------------------------------
    # Each returns the widget to place directly into the panel's QVBoxLayout
    # (also used as the "row" for show()/hide() purposes).

    @staticmethod
    def _apply_button_style(button: QPushButton, style_variant: Optional[str]) -> None:
        applier = _STYLE_APPLIERS.get(style_variant)
        if applier:
            applier(button)

    @classmethod
    def _make_button(cls, b: ButtonDef, parent: QWidget, register_hook) -> QPushButton:
        btn = QPushButton(b.text, parent)
        cls._apply_button_style(btn, b.style_variant)
        btn.setEnabled(b.enabled)
        register_hook(b.on_click, lambda cb, btn=btn: btn.clicked.connect(cb))
        return btn

    @classmethod
    def _build_lineedit_row(cls, f, parent, field_widgets, buttons_lists, register_hook):
        label = QLabel(f.label, parent) if f.label else None
        edit = QgsFilterLineEdit(parent)
        if f.placeholder:
            edit.setPlaceholderText(f.placeholder)
        field_widgets[f.field_id] = edit
        register_hook(f.on_change, lambda cb, edit=edit: edit.textChanged.connect(cb))

        content = [(edit, 6 if f.trailing_button else 1)]
        if f.trailing_button:
            btn = cls._make_button(f.trailing_button, parent, register_hook)
            field_widgets[f.trailing_button.field_id] = btn
            content.append((btn, f.trailing_button.stretch))

        return UIStyleHelper.build_flex_row(
            label,
            content,
            main_ratio=f.main_ratio or UIConfig.MAIN_RATIO,
            row_height=f.row_height or UIConfig.ROW_HEIGHT,
        )

    @classmethod
    def _build_combobox_row(cls, f, parent, field_widgets, buttons_lists, register_hook):
        label = QLabel(f.label, parent) if f.label else None
        combo = QComboBox(parent)
        field_widgets[f.field_id] = combo
        register_hook(f.on_change, lambda cb, combo=combo: combo.currentIndexChanged.connect(cb))
        return UIStyleHelper.build_flex_row(
            label,
            [(combo, 1)],
            main_ratio=f.main_ratio or UIConfig.MAIN_RATIO,
            row_height=f.row_height or UIConfig.ROW_HEIGHT,
        )

    @classmethod
    def _build_button(cls, f, parent, field_widgets, buttons_lists, register_hook):
        b = ButtonDef(
            field_id=f.field_id,
            text=f.label or "",
            on_click=f.on_click,
            style_variant=f.style_variant,
            enabled=f.enabled,
        )
        btn = cls._make_button(b, parent, register_hook)
        field_widgets[f.field_id] = btn
        return btn

    @classmethod
    def _build_button_row(cls, f, parent, field_widgets, buttons_lists, register_hook):
        row = QWidget(parent)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        for b in f.buttons:
            btn = cls._make_button(b, row, register_hook)
            field_widgets[b.field_id] = btn
            row_layout.addWidget(btn, b.stretch)
        return row

    @classmethod
    def _build_table(cls, f, parent, field_widgets, buttons_lists, register_hook):
        table = QTableWidget(0, len(f.table_headers), parent)
        table.setHorizontalHeaderLabels(f.table_headers)
        header = table.horizontalHeader()
        for col in range(len(f.table_headers)):
            token = f.table_col_resize_modes[col] if col < len(f.table_col_resize_modes) else "contents"
            header.setSectionResizeMode(col, _RESIZE_MODES.get(token, QHeaderView.ResizeToContents))
        if f.table_min_height:
            table.setMinimumHeight(f.table_min_height)
        field_widgets[f.field_id] = table
        register_hook(f.on_change, lambda cb, table=table: table.cellChanged.connect(cb))
        return table

    @classmethod
    def _build_segmented_toggle(cls, f, parent, field_widgets, buttons_lists, register_hook):
        container, buttons = UIStyleHelper.build_segmented_toggle(
            f.options, default_index=f.default_index, parent=parent
        )
        field_widgets[f.field_id] = container
        buttons_lists[f.field_id] = buttons

        def connect_index_hook(cb, buttons=buttons):
            for idx, btn in enumerate(buttons):
                btn.toggled.connect(lambda checked, idx=idx, cb=cb: cb(idx) if checked else None)

        register_hook(f.on_change, connect_index_hook)

        return UIStyleHelper.build_flex_row(
            None,
            [(container, 1)],
            main_ratio=f.main_ratio or (0, 10),
            row_height=f.row_height or UIConfig.ROW_HEIGHT,
        )

    @classmethod
    def _build_info_panel(cls, f, parent, field_widgets, buttons_lists, register_hook):
        frame = QFrame(parent)
        UIStyleHelper.set_status_panel(frame)
        panel_layout = QVBoxLayout(frame)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(4)

        for line in f.info_lines:
            if line.kind == "separator":
                hr = QFrame(frame)
                hr.setFrameShape(QFrame.HLine)
                hr.setStyleSheet("border-top: 1px dashed palette(mid); background: transparent;")
                panel_layout.addWidget(hr)
                continue

            label = QLabel(line.text, frame)
            if line.kind == "bold":
                label.setStyleSheet("font-weight: bold;")
            elif line.kind == "wrap":
                label.setWordWrap(True)
                if line.min_height:
                    label.setMinimumHeight(line.min_height)
            panel_layout.addWidget(label)
            if line.field_id:
                field_widgets[f"{f.field_id}.{line.field_id}"] = label

        field_widgets[f.field_id] = frame
        return frame


# NOTE: populated after class definition (not inside the class body) so that
# each entry is CoreUIBuilder's already-bound classmethod (cls fixed to
# CoreUIBuilder), letting CoreUIBuilder.build() call `builder_fn(f, ...)`
# without re-passing cls itself.
CoreUIBuilder._BUILDERS = {
    WidgetType.LINEEDIT_ROW: CoreUIBuilder._build_lineedit_row,
    WidgetType.COMBOBOX_ROW: CoreUIBuilder._build_combobox_row,
    WidgetType.BUTTON: CoreUIBuilder._build_button,
    WidgetType.BUTTON_ROW: CoreUIBuilder._build_button_row,
    WidgetType.TABLE: CoreUIBuilder._build_table,
    WidgetType.SEGMENTED_TOGGLE: CoreUIBuilder._build_segmented_toggle,
    WidgetType.INFO_PANEL: CoreUIBuilder._build_info_panel,
}
