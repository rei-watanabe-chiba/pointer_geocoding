"""
/***************************************************************************
 PointerGeocoding Plugin - CoreUI field_spec (declaration-only data types)
 ***************************************************************************/

T-0045: pure dataclasses describing "what a panel looks like" (widget kind /
label / choices / visibility / event-hook name). No PyQt widget is ever
constructed in this module -- that is CoreUIBuilder's job (builder.py). This
mirrors the "宣言のみ" design described in .claude/state/v2-coreui-plan.md.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class WidgetType(Enum):
    """Kinds of rows/fields CoreUIBuilder knows how to construct.

    Only the kinds actually needed by a real screen's schema are implemented
    here (originally tab1_image.py's TAB1_* specs; RADIO_ROW was added for
    start_dialog.py's T-0046 adoption); new kinds should be added only once
    a real screen needs them (avoids speculative/unused surface area, per
    the CoreUI plan's "逃げ道" principle for screen-specific exceptions).
    """
    LINEEDIT_ROW = "lineedit_row"
    COMBOBOX_ROW = "combobox_row"
    BUTTON = "button"
    BUTTON_ROW = "button_row"
    TABLE = "table"
    SEGMENTED_TOGGLE = "segmented_toggle"
    INFO_PANEL = "info_panel"
    #: T-0046: a labeled row of mutually-exclusive QRadioButtons (e.g.
    #: start_dialog.py's session-type / grid-mode selectors), distinct from
    #: SEGMENTED_TOGGLE's iOS-style button group. Uses FieldSpec.options for
    #: the radio labels and FieldSpec.default_index for the initially
    #: checked option, same as SEGMENTED_TOGGLE.
    RADIO_ROW = "radio_row"
    #: T-0047: a labeled row wrapping a single UIStyleHelper.create_spinbox()
    #: QSpinBox (e.g. dialogs.py's PointNameEntryDialog 点名 numeric input),
    #: distinct from LINEEDIT_ROW since it carries an int range/default
    #: instead of free text. Uses FieldSpec.spin_min/spin_max/spin_default.
    SPINBOX_ROW = "spinbox_row"


@dataclass
class ButtonDef:
    """One button, either standalone within a BUTTON_ROW field or as the
    trailing button of a LINEEDIT_ROW field (e.g. Tab1's "参照..." button).

    :param field_id: Key the built QPushButton is registered under on the
        BuiltPanel (retrieved via ``panel.get(field_id)``).
    :param text: Button label text.
    :param on_click: Event-hook name connected to ``clicked``; bound later
        via ``panel.bind(on_click, callback)``. None if the button has no
        event (rare).
    :param style_variant: Optional UIStyleHelper button style
        ("primary"/"accent"/"success"), or None for the default style.
    :param enabled: Initial enabled state.
    :param stretch: Layout stretch factor within its row.
    """
    field_id: str
    text: str
    on_click: Optional[str] = None
    style_variant: Optional[str] = None
    enabled: bool = True
    stretch: int = 1


@dataclass
class InfoLine:
    """One line within an INFO_PANEL field (T-0045: models Tab1's status
    panel, which stacks a bold header / separator / plain status line / a
    word-wrapped multi-line residual summary).

    :param kind: "bold" | "separator" | "plain" | "wrap".
    :param field_id: Sub-key the built QLabel is registered under, as
        ``f"{field.field_id}.{field_id}"`` (ignored for "separator").
    :param text: Initial label text (ignored for "separator").
    :param min_height: Optional minimum height in px (used for "wrap" lines
        that need to reserve space for multiple lines up front).
    """
    kind: str
    field_id: Optional[str] = None
    text: str = ""
    min_height: Optional[int] = None


@dataclass
class FieldSpec:
    """One declared row/field within a PanelSpec.

    Only the attributes relevant to ``widget_type`` need to be set; unused
    attributes are ignored by CoreUIBuilder for that kind.

    :param field_id: Key the built primary widget is registered under on the
        BuiltPanel (retrieved via ``panel.get(field_id)``); also used as the
        key for the row container widget (``panel.get_row(field_id)``),
        which is what callers show()/hide() to toggle a whole row.
    :param widget_type: Which WidgetType to construct.
    :param label: Leading row label text (LINEEDIT_ROW/COMBOBOX_ROW), or the
        button text (BUTTON).
    :param placeholder: Placeholder text (LINEEDIT_ROW).
    :param on_change: Event-hook name for value-changed signals
        (LINEEDIT_ROW -> textChanged, COMBOBOX_ROW -> currentIndexChanged,
        TABLE -> cellChanged, SEGMENTED_TOGGLE/RADIO_ROW -> "toggled to
        index").
    :param on_click: Event-hook name for BUTTON's ``clicked`` signal.
    :param style_variant: UIStyleHelper button style for BUTTON.
    :param enabled: Initial enabled state for BUTTON.
    :param trailing_button: Optional ButtonDef appended after the input
        widget within a LINEEDIT_ROW (e.g. "参照..." next to the image path
        field).
    :param buttons: Button list for BUTTON_ROW.
    :param options: Segment/option labels for SEGMENTED_TOGGLE/RADIO_ROW.
    :param default_index: Initially-checked segment/option index for
        SEGMENTED_TOGGLE/RADIO_ROW.
    :param table_headers: Column header labels for TABLE.
    :param table_min_height: Minimum table height in px for TABLE.
    :param table_col_resize_modes: Per-column resize mode tokens for TABLE
        ("contents" or "stretch"; defaults to "contents" if the list is
        shorter than the header count).
    :param info_lines: Ordered InfoLine entries for INFO_PANEL.
    :param main_ratio: Override for UIStyleHelper.build_flex_row's
        main_ratio (label vs. content stretch). Defaults to
        UIConfig.MAIN_RATIO when None (LINEEDIT_ROW/COMBOBOX_ROW), or
        (0, 10) when None for SEGMENTED_TOGGLE.
    :param row_height: Override for UIStyleHelper.build_flex_row's
        row_height. Defaults to UIConfig.ROW_HEIGHT when None.
    :param visible: Initial visibility of the row container.
    :param spin_min: Minimum value for SPINBOX_ROW (default 0).
    :param spin_max: Maximum value for SPINBOX_ROW (default 999999).
    :param spin_default: Initial value for SPINBOX_ROW (default 0).
    :param centered: T-0047: for BUTTON_ROW only, wraps the buttons in a
        leading/trailing stretch (mirrors UIStyleHelper.
        build_centered_button_row's "stretch - buttons - stretch" pattern),
        matching the OK/キャンセル row convention used by dialogs.py's modal
        confirmation dialogs. False (the default) preserves BUTTON_ROW's
        original left-anchored, edge-to-edge layout used by e.g. Tab1's
        rename_delete/transform_actions rows.
    """
    field_id: str
    widget_type: WidgetType
    label: Optional[str] = None
    placeholder: Optional[str] = None
    on_change: Optional[str] = None
    on_click: Optional[str] = None
    style_variant: Optional[str] = None
    enabled: bool = True
    trailing_button: Optional[ButtonDef] = None
    buttons: List[ButtonDef] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    default_index: int = 0
    table_headers: List[str] = field(default_factory=list)
    table_min_height: Optional[int] = None
    table_col_resize_modes: List[str] = field(default_factory=list)
    info_lines: List[InfoLine] = field(default_factory=list)
    main_ratio: Optional[Tuple[int, int]] = None
    row_height: Optional[int] = None
    visible: bool = True
    spin_min: int = 0
    spin_max: int = 999999
    spin_default: int = 0
    centered: bool = False


@dataclass
class PanelSpec:
    """A named collection of FieldSpecs built together into one container
    widget (a vertical stack, one row per field, in declared order).

    :param panel_id: Identifying name for the panel (informational only;
        not currently used for lookups).
    :param fields: Ordered FieldSpec list.
    :param rules: Optional list of generic business-logic rule instances
        (see rules.py) applied to the BuiltPanel once construction
        completes. Empty for tab1 (no generic rule is needed yet); reserved
        for T-0047's mode-visibility/realtime-commit style rules.
    :param margins: Container QVBoxLayout content margins
        (left, top, right, bottom).
    :param spacing: Container QVBoxLayout spacing between rows.
    """
    panel_id: str
    fields: List[FieldSpec]
    rules: List = field(default_factory=list)
    margins: Tuple[int, int, int, int] = (0, 0, 0, 0)
    spacing: int = 6
