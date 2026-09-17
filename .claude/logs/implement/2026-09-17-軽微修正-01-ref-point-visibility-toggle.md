## タスクID
軽微修正-01（tab2_plot.py 図面選択リストパネルへの基準点レイヤ表示/非表示トグル追加）

## 変更ファイル一覧
- `src/ui/tab2_plot.py`
- `src/ui/constants.py`
- `.claude/state/tasks.md`（タスク行追加）

## 変更概要

### ①スペース削除
`group_drawing_list`（Panel 4）内の`drawing_list_layout`は、今回の変更前は
`list_drawing_visibility`（QListWidget）1つしか子ウィジェットを持たなかったため
`setSpacing(UIConfig.PANEL_MARGIN)`は実質未使用だった。今回`row_ref_point_visibility`を
追加したことで、このQVBoxLayoutの`setSpacing()`値がそのまま両者の間隔になる。

このレイアウトは`group_drawing_list`専用（他パネルとは独立したQVBoxLayoutインスタンス）
であるため、値を変更しても他パネルの余白感（`layout.setSpacing(UIConfig.PANEL_MARGIN)`が
支配する外側のパネル間隔や、`focus_layout`/`attr_layout`等の内部間隔）には一切影響しない
ことをコードを追って確認した上で、`UIConfig.PANEL_MARGIN // 2`（8→4）に縮小した。
0にはせず半分に留めたのは、視覚的に詰まりすぎて誤操作を招くリスクを避けるため。

### ②「基準点: 」ラベル+ラジオボタンの追加
- `UILabels`に`LBL_REF_POINT_VISIBILITY = "基準点: "`、`RADIO_VISIBLE = "表示"`、
  `RADIO_HIDDEN = "非表示"`を追加（`src/ui/constants.py`）。
- `list_drawing_visibility`の直下（`drawing_list_layout`内）に、
  `UIStyleHelper.build_flex_row()`パターン（既存の`row_encoding`と同じ、
  `QRadioButton`2個+空きストレッチ枠1個の1:1:1構成）で1行追加。
  `QRadioButton`×2を`QButtonGroup`（`self.ref_point_visibility_group`）でグループ化。
  `T-0050`（tab2 CoreUI化）まではCoreUIの`RADIO_ROW`を持ち込まず、既存の素のPyQt実装
  スタイルに統一した（依頼書の指示どおり）。

### ③基準点レイヤの表示/非表示制御
- `_find_ref_point_tree_layer()`を新規追加。`self.layer_manager.ref_point_layer`の
  レイヤIDを使い、レイヤツリー上「基準点データ」グループ（存在すればその中、
  なければルート）から`findLayer()`で対象の`QgsLayerTreeLayer`を特定する
  （`src/layer/grid_csv.py`236-243行の配置ロジックと対称的な検索パターン）。
- `_on_ref_point_visibility_radio_toggled(checked)`を新規追加。
  `radio_ref_point_visible.toggled`のみに接続し（`QButtonGroup`で排他制御されているため
  片方の`toggled(bool)`だけで両状態を判定可能）、`tree_layer.setItemVisibilityChecked(checked)`
  + `self.canvas.refresh()`を実行する（`_on_drawing_visibility_item_changed`と同じパターン）。
- `_sync_ref_point_visibility_radios()`を新規追加。実際のレイヤツリー状態
  （`tree_layer.itemVisibilityChecked()`）からラジオボタンの初期/最新状態を同期する。
  同期中は`blockSignals(True/False)`で囲み、プログラム的なチェック状態変更が
  `_on_ref_point_visibility_radio_toggled`を誤発火させて余分なcanvas.refresh()や
  レイヤツリー書き込みを起こさないようにした。
- **基準点レイヤ未ロード時（`self.layer_manager.ref_point_layer`が`None`）の判断**:
  両ラジオボタンを`setEnabled(False)`で無効化し、デフォルトは「表示」側をチェック済みに
  しておく（依頼書に挙げられた2案のうち「無効化する」を採用。理由: 対象レイヤが
  存在しない状態でユーザーが操作可能に見えるのは誤解を招くため）。
  レイヤが後から追加された場合に備え、`_update_drawing_combo()`（`dock.py`の
  `QgsProject.instance().layersAdded/layersRemoved`シグナル、および`_create_tab2_ui()`
  初期化時に既存で呼ばれている）の末尾に`_sync_ref_point_visibility_radios()`の呼び出しを
  追加し、基準点レイヤが後からロードされた際にも自動的に有効化・状態同期されるようにした
  （新規シグナル接続は追加していない＝既存シグナルの購読先を1つ増やしただけなので、
  接続/解除の対称性は`dock.py`側の既存connect/disconnectペアがそのまま維持される）。

## 自動テスト実行結果
自動テストなし（`python3 -m py_compile src/ui/tab2_plot.py src/ui/constants.py`による
構文チェックのみ実施し、エラーなし）。

## スコープ外変更の有無
なし。変更は依頼書に明記された`src/ui/tab2_plot.py`と、ラベル文言定数追加のための
`src/ui/constants.py`のみ。`.claude/state/tasks.md`へのタスク行追加は運用ルールに基づく
付随的な記録であり、コードロジックの変更ではない。
