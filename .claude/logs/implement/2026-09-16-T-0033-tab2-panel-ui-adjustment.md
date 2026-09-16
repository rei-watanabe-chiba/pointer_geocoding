## タスクID
T-0033（T-0032のUI調整、実際にQGIS上で動作確認した上でのフィードバック反映）

## 変更ファイル一覧
- `src/tab2_digitizing_mixin.py`（主対象。UI構築・イベントハンドラを調整）
- `src/style_helper.py`（`build_separator()`/`set_error_border()`新設、`set_panel_status()`と
  対応するT-0032専用QSS（`QLabel[banner="editing"/"error"]`/`QGroupBox[panelStatus=...]`）を削除）
- `src/main_dock_constants.py`（`BTN_UPDATE_OPACITY`/`MSG_ATTR_CONFIRM_TITLE`/`MSG_ATTR_CONFIRMED`削除）

## 変更概要

### ① グループボックスのタイトル削除、HLine区切りへ変更
`group_point_info`/`group_attribute_panel`/`group_focus`の3つの`QGroupBox`について、
コンストラクタに渡していたタイトル文字列（`UILabels.GROUP_POINT_INFO`等）を除去し
（`QGroupBox(container)`のみに変更）、各パネルの直前に`UIStyleHelper.build_separator()`
（新設。`QFrame.HLine`+`QFrame.Sunken`）を`layout.addWidget()`で挿入した。
`group_drawing_list`（図面選択リスト）はスコープ外のためタイトルのまま維持。

### ②③ 点情報パネルをフラットな複数行テキストに統一
従来のステータス帯用`QLabel`（`UIStyleHelper.set_banner_status()`による専用強調スタイル）と、
出土形態/点名+枝番/XY座標をそれぞれ独立行（`lbl_info_group_value`等3組のQLabel+`build_flex_row`）
で表示していた構成を廃止。代わりに`UIStyleHelper.create_status_panel()`で生成した単一の
`QFrame`+`QLabel`（`self.panel_point_info`/`self.lbl_point_info_status`）に、状態文言＋
出土形態＋点名/枝番＋XY座標を改行区切りでまとめたテキストを表示するよう変更した
（`_build_point_info_text()`新設。項目順序はT-0032の実装順を踏襲）。
`_refresh_point_info_labels()`は個別QLabelへの`setText()`をやめ、`self._point_info_summary`
（dict）に値を保持するのみに変更。`_update_point_info_status()`が状態文言と合わせて最終テキストを
組み立て、`UIStyleHelper.update_status_panel()`で反映する。

### ④ インプット・ボタンをパネル外に、パネルは左ボーダー色分け方式へ
点名/枝番インプット（`edit_point_name`/`edit_point_name_sp`/`edit_branch_no`）と
「点名変更」「削除」ボタン（`row_existing_actions`）は、③の色分けパネル（`self.panel_point_info`）
の**下**（`info_layout`内で後続）に配置する構成に変更（元々同じ`group_point_info`内の並び順
だったため、旧・個別行を削除しパネルに置き換えたことで自然にこの配置になった）。
パネル自体は`start_dialog.py`の`panel_preview_status`と同じ`create_status_panel()`/
`update_status_panel()`のQFrame（左ボーダー3px＋薄い背景色）を流用し、新規スタイル追加なしで
以下の対応とした:
- 新規点作成中: `status_type="info"`（既存の青系ボーダー、`QFrame[statusType="info"]`を流用）
- 既設点編集中: `status_type="warning"`（オレンジ系、既存定義をそのまま流用。専用の"editing"は
  新設せず既存の"warning"で代替）
- エラー時: `status_type="error"`（赤、既存定義を流用）
なお`btn_update_attribute`（属性変更ボタン）は元々`group_attribute_panel`内にあり色分けパネルの
内側ではなかったため、位置は変更していない。

### ⑤ カラーボタン無効時のグレー表示
`_update_color_picker_button()`を、`self.btn_color_picker.isEnabled()`を見て有効時は
`self.current_feature_color`、無効時は固定グレー（`#9E9E9E`）を背景色に設定するよう修正。
`_update_feature_related_visibility()`の`setEnabled()`呼び出し直後に`_update_color_picker_button()`
を呼ぶよう追加し、有効/無効切替のたびに見た目が追従するようにした。また`_create_tab2_ui()`の末尾で
`self._update_feature_related_visibility()`を1回呼び出し、プラグイン起動直後（デフォルト出土形態=
グリッド）から正しくグレー表示になるようにした（従来は初期化時に一度もこの関数が呼ばれておらず、
起動直後はボタンが有効かつオレンジ色のまま矛盾した見た目になっていたための追加呼び出し）。

### ⑥ 透明度「更新」ボタンの削除
フォーカスモードパネルの`btn_update_opacity`（「更新」ボタン）と、そのクリックハンドラ
`_on_update_opacity_clicked()`を削除。スライダーの幅比率を`(slider,2),(label,0),(button,1)`から
T-0032以前の`(slider,3),(label,1)`に戻した。透明度反映は既存の`sliderReleased`→
`_on_slider_released()`→`update_symbology_opacity()`のみに戻っている（ロジック自体は変更なし）。
関連する未使用定数`BTN_UPDATE_OPACITY`/`MSG_ATTR_CONFIRM_TITLE`/`MSG_ATTR_CONFIRMED`は
`main_dock_constants.py`から削除した。

### ⑦ エラー時の入力欄への赤枠追加
`UIStyleHelper.set_error_border(widget, has_error)`を新設（`border: 2px solid #C62828;`を
適用/解除するだけの薄いラッパー）。`_update_error_borders()`を新設し、`_update_point_info_status()`
の末尾から呼び出す。遺構名未指定エラー時は`combo_feature_name`に、点名重複エラー時は現在表示中の
点名インプット（`edit_point_name`または`edit_point_name_sp`、`_is_sp_attribute()`で判定）に
赤枠を適用し、エラー解消時は空文字列のスタイルシートで解除する。

### 副次的なクリーンアップ（スコープ内の直接関連分のみ）
- `UIStyleHelper.set_panel_status()`（T-0032でこの点情報パネル専用に追加されたメソッド）と、
  対応する`QGroupBox[panelStatus="info"/"editing"/"error"]`QSSを削除（本タスクで採用した
  「左ボーダー色分けフレーム」方式に置き換わり完全に不要になったため）。
- `QLabel[banner="editing"]`/`QLabel[banner="error"]`QSS（同じくT-0032でこの点情報パネル専用に
  追加されたもの）を削除。ただし`QLabel[banner="info"/"success"/"warning"]`と汎用メソッド
  `UIStyleHelper.set_banner_status()`自体はT-0013由来の汎用ヘルパーであり他機能転用の可能性を
  考慮しそのまま維持した。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定のため未実施）。
`python3 -m py_compile`および`python3 -m pyflakes`による静的構文チェックを実施し、
変更対象ファイル群および`src/`全体で新規の未定義名・構文エラーなしを確認
（既存の無関係な未使用import警告のみ、いずれも本タスクの変更箇所外）。

## スコープ外変更の有無
なし。変更は依頼スコープに明記された`src/tab2_digitizing_mixin.py`・`src/style_helper.py`・
`src/main_dock_constants.py`のみ。T-0032実装ログにあった`src/main_dock.py`の
`update_symbology_opacity()`修正のような追加の連鎖修正は今回発生していない。
