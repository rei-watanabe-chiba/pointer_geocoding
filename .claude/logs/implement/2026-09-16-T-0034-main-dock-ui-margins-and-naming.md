## タスクID
T-0034: main_dockのUI/余白調整とタブ名称変更（3点セット、いずれもUI/表示のみでロジック変更なし）

## 変更ファイル一覧
- `src/main_dock.py`
- `src/main_dock_constants.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_dialogs.py`（コメントのみ）

## 変更概要

### ① top_row と tab2_container の視覚的区別
`main_dock.py` の `_init_ui()` 内、`root_layout.addWidget(top_row)` の直後・
`self.tab1_container = self._create_tab1_ui()` の前に、
`UIStyleHelper.build_separator(root_widget)` で生成した `QFrame(HLine)` を
`root_layout.addWidget()` で1本追加した。背景色等のスタイル変更は行っていない。

### ② 余白定数の新設と適用
`main_dock_constants.py` の `UIConfig` に以下の定数を追加した（既存の書き方
（`UIConfig` に定数を並べるフラットな形）に合わせ、新規クラスは設けなかった）。

- `DOCK_OUTER_MARGIN = 6`（旧 `root_layout.setContentsMargins(6, 6, 6, 6)`）
- `TOP_ROW_BUTTON_SPACING = 6`（旧 `top_layout.setSpacing(6)`）
- `SECTION_GAP = 6`（旧 `root_layout.setSpacing(6)`）
- `PANEL_CONTAINER_MARGIN_LEFT = 4` / `PANEL_CONTAINER_MARGIN_TOP = 4` /
  `PANEL_CONTAINER_MARGIN_RIGHT = 16` / `PANEL_CONTAINER_MARGIN_BOTTOM = 4`
  （旧 `tab2_digitizing_mixin.py` の `layout.setContentsMargins(4, 4, 16, 4)`。
  依頼文では「LR/TB」の2定数と書かれていたが、右マージンのみスクロールバー
  避けで非対称という既存コメントの意図を保ったまま個別に調整可能にするため、
  実装では左右上下を4つの独立した定数に分解した）
- `PANEL_GROUP_SPACING = 8`（旧 `layout.setSpacing(8)`、4パネル間の縦間隔）
- `PANEL_INNER_SPACING = 6`（旧 `info_layout`/`attr_layout`/`focus_layout` の
  それぞれの `setSpacing(6)`。3箇所とも同一値だったため単一定数に集約）
- `SEPARATOR_MARGIN_TOP = 4` / `SEPARATOR_MARGIN_BOTTOM = 4`（新設。
  `PANEL_GROUP_SPACING`（8）の半分を初期値とした）

区切り線（`UIStyleHelper.build_separator()`）を独立余白で囲むため、
`tab2_digitizing_mixin.py` の3箇所（点情報パネル/属性パネル/フォーカスモード
パネルの各前段）と `main_dock.py` の新設1箇所、計4箇所すべてで
`layout.addSpacing(SEPARATOR_MARGIN_TOP)` → `layout.addWidget(separator)` →
`layout.addSpacing(SEPARATOR_MARGIN_BOTTOM)` の形に変更した
（`main_dock.py` 側は `root_layout` に対して同様の形で追加）。
これにより区切り線の上下余白は `PANEL_GROUP_SPACING`（パネル間隔）から独立し、
今後は `SEPARATOR_MARGIN_TOP`/`BOTTOM` のみを調整すればよい状態にした。

### ③ タブ名称の表示文字列変更
`main_dock_constants.py` の `UILabels`:
- `TAB_1_TITLE`: "画像管理" → "IMG"
- `TAB_2_TITLE`: "遺物点作成" → "PLOT"
- `TAB_3_TITLE`: "設定" → "SET"
- `OUTPUT_DIALOG_TITLE` を `TAB_4_TITLE` にリネームし、値を "CSV出力" → "OUT"
  に変更。

内部識別子のリネーム（4点、依頼スコープ通り）:
- `main_dock.py`: `self.output_container` → `self.tab4_container`
- `tab2_digitizing_mixin.py`: `_create_output_ui()` → `_create_tab4_ui()`
  （呼び出し元 `main_dock.py` の `self._create_output_ui()` も
  `self._create_tab4_ui()` に追従）
- `main_dock_constants.py`: `UILabels.OUTPUT_DIALOG_TITLE` →
  `UILabels.TAB_4_TITLE`

`output_dialog`/`_show_output_dialog`/`btn_top_output` はスコープ指示通り
変更していない（`image_dialog`/`settings_dialog` と同じ命名系統のため対象外）。

`output_container`/`_create_output_ui`/`OUTPUT_DIALOG_TITLE` への
コメント・docstring言及は `grep` で全て洗い出し、`main_dock.py` /
`main_dock_dialogs.py` / `tab2_digitizing_mixin.py` の該当箇所を
「T-0034でリネームされた」旨の注記付きで追従修正した
（履歴として旧名を残す注記コメント自体は意図的に残置）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。
代わりに `python3 -m py_compile src/main_dock.py src/main_dock_constants.py
src/tab2_digitizing_mixin.py src/main_dock_dialogs.py` による構文チェックを
実施し、エラーなく完了した。

## スコープ外変更の有無
なし。対象ファイルは依頼で指定された4ファイル（`main_dock.py`,
`main_dock_constants.py`, `tab2_digitizing_mixin.py`,
`main_dock_dialogs.py`（コメントのみ））のみを変更した。ロジック（信号接続、
ハンドラの処理内容、フィールド名等）は一切変更していない。
