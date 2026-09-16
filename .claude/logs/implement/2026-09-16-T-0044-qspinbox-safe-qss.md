## タスクID
T-0044

## 変更ファイル一覧
- src/ui/style.py

## 変更概要
`UIStyleHelper.get_style_sheet()` の QSS 文字列に、`QSpinBox` / `QSpinBox:focus` / `QSpinBox::up-button, QSpinBox::down-button` の3ルールを追加した（`QLineEdit, QgsFilterLineEdit, QComboBox` のフォーカスルールの直後に挿入）。

- `QSpinBox`: `background-color: palette(base)`, `color: palette(text)`, `border: 1px solid palette(mid)`, `border-radius: 4px`, `padding: 0px 4px`, `min-height: 28px`, `min-width: 70px`, `selection-background-color: palette(highlight)`, `selection-color: palette(highlighted-text)`。既存の `QLineEdit, QgsFilterLineEdit, QComboBox` ルールと同じ palette ロール参照方式に揃えた（依頼文中の `#B0B0B0` / `white` 等のハードコード色は、本ファイル内の入力系ウィジェットが一貫して palette ロール参照を採用しているため、既存パターンに合わせて palette(base)/palette(mid) 等に置き換えた）。
- `QSpinBox:focus`: `border: 1.5px solid palette(highlight)`（`QLineEdit:focus` 等と同じ幅・色指定に統一）。
- `QSpinBox::up-button, QSpinBox::down-button`: `subcontrol-origin: border; width: 18px;` のみ。依頼の制約通り、`QSpinBox::up-arrow` / `QSpinBox::down-arrow` に対するルールは一切追加していない（`image` プロパティ等も未指定）。矢印描画は完全にプラットフォームのベーススタイルに委ねている。

`min-width` は依頼のガイド値である70pxをそのまま採用した（`edit_point_name` / start_dialog.py のグリッド設定スピンボックス行はいずれも `build_flex_row`/`build_child_container` でストレッチ配分される構成であり、70px固定は最小幅の下限としてのみ機能し、レイアウト崩れの要因にはならないと判断した）。

`UIStyleHelper.create_spinbox()` 自体のロジックは変更していない（依頼通り、テーマQSS追加のみで対応可能と判断）。

## 自動テスト実行結果
自動テストなし。`python3 -m py_compile src/ui/style.py` で構文エラーがないことを確認した（成功、エラーなし）。

## スコープ外変更の有無
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内へのQSS追加のみで、他ファイル（tab2_plot.py, tab1_image.py, start_dialog.py, dialogs.py, tab3_settings.py 等）や `create_spinbox()` 自体には手を加えていない。
