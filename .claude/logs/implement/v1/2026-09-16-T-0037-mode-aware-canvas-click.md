## タスクID
T-0037 キャンバスクリック挙動のモード連動（3段階UX改善の2/3）

## 変更ファイル一覧
- `src/map_tool.py`
- `src/tab2_digitizing_mixin.py`

## 変更概要

### `src/map_tool.py`（`CanvasDigitizingTool._handle_digitize_click`）
- クリック処理の冒頭で `self.dock_widget.tab2_current_mode`（T-0036で新設された文字列状態、"new"/"edit"）を
  `getattr(self.dock_widget, "tab2_current_mode", "new")` で取得するように変更。
  値が `"new"`/`"edit"` のいずれでもない場合（未定義・想定外の値）は `"new"` にフォールバックする。
- **新規モード（"new"）**: `find_nearest_feature_id()` による既設フィーチャへのスナップ判定を一切行わず、
  常に選択マーカーをクリアした上で `canvas_clicked` シグナルをemitし、新規打点フローに進む。
- **編集モード（"edit"）**: `find_nearest_feature_id()` によるスナップ判定のみを行う。
  - ヒットした場合: 従来通り `show_selected_marker()` → `existing_point_selected` をemit。
  - ヒットしなかった場合（空白クリック）: 何もしない（`canvas_clicked` はemitしない＝新規点は作成されない）。
- 参照経路: `map_tool.py` のコンストラクタが既に受け取っている `dock_widget`（`MainDockWidget` インスタンス。
  `Tab2DigitizingMixin` をミックスインしているため `tab2_current_mode` 属性を直接持つ）をそのまま利用した。
  新たなシグナル/参照経路は追加せず、既存の `self.dock_widget` 経由のプルパターン
  （`find_nearest_feature_id()` が `self.dock_widget.layer_manager` を参照するのと同様）に揃えた。

### `src/tab2_digitizing_mixin.py`
- `_on_canvas_clicked()` 冒頭の `if self.selected_edit_point_id is not None: self._reset_point_selection(); return`
  （T-0027で実装された「空白クリックでの選択解除」分岐）を削除。
  - この分岐は、`map_tool.py` 側の変更により編集モードでは `_on_canvas_clicked()` 自体が呼ばれなくなるため、
    新規モードでは `selected_edit_point_id` が非nullになることは通常ないが、コードとして明示的に削除・整理した。
  - docstringも、T-0037時点での呼び出し条件（新規モードでのみ到達）と、T-0027の選択解除挙動廃止を反映して更新。
- `_on_tab2_mode_changed()` のdocstringを更新し、「クリック挙動の分岐は `map_tool.py` の
  `CanvasDigitizingTool._handle_digitize_click` が `tab2_current_mode` を直接参照して行う（T-0037で統合済み）」
  という実装済みの事実を反映（従来は「T-0037で別途統合予定」という記述だった）。

### 変更していないもの（スコープ厳守）
- `_on_canvas_clicked()` 内の打点作成ロジック本体（入力検証・重複チェック・feature構築・自動連番等）は無変更。
- `_on_existing_point_selected()` 内の処理本体は無変更。
- T-0038（属性のリアルタイム反映化）relevantコードには手を加えていない。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定）。
`python3 -m py_compile src/map_tool.py src/tab2_digitizing_mixin.py` による構文確認を実施し、エラーなし。

## スコープ外変更の有無
なし。`src/map_tool.py` と `src/tab2_digitizing_mixin.py` の、依頼された分岐ロジックとその関連docstringのみを変更した。
