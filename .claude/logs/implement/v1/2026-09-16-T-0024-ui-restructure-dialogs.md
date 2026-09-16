## タスクID
T-0024

## 変更ファイル一覧
- `src/main_dock.py`
- `src/main_dock_dialogs.py`
- `src/main_dock_constants.py`
- `src/plugin.py`
- `src/tab1_georef_mixin.py`
- `src/tab2_digitizing_mixin.py`
- `docs/integrated_master_design.md`
- `.claude/state/tasks.md`

(`src/tab3_settings_mixin.py`, `src/style_helper.py` は本タスクの変更対象スコープに含まれていたが、要件を満たすために既存コードの変更は不要だったため無変更。)

## 変更概要

### 左ドック廃止
- `main_dock.py`: `_init_left_dock()`、アイコンレール(`nav_btn_drawing`/`nav_btn_settings`/`nav_button_group`)、サイドパネル(`side_panel`/`side_stack`)、`_on_nav_button_clicked()`/`_on_panel_changed()`/`_close_side_panel()`、`self.left_dock`を全て削除。
- `plugin.py`: `_setup_dock_widget()`/`_teardown_dock_widget()`から左ドックの`addDockWidget`/`removeDockWidget`/`deleteLater`処理を削除。単一の右ドックのみを登録する構成に変更。

### 右ドック上部4ボタン化
- `main_dock.py`の`_init_ui()`冒頭に「画像」「設定」「出力」「保存」の4ボタンをQHBoxLayoutで配置。アイコンは`_load_icon()`ヘルパー（`os.path.join(os.path.dirname(__file__), "icon", filename)`）で`src/icon/{image,setting,output,save}.svg`を`QIcon`として読み込み`setIcon()`。各ボタンに`setObjectName()`で一意な名前(`btnTopImage`等)を付与。
- `plugin.py`の`_get_icon()`のSVGパスを`os.path.join(self.plugin_dir, "icon", "icon.svg")`に修正（アイコン移設への追従）。

### 画像/設定/出力ダイアログ（新規、モードレス）
- `main_dock_dialogs.py`に`ModelessSectionDialog`（設定/出力用の汎用モードレスラッパー。単一content_widgetを表示、`on_show`/`on_close`コールバックを持つ）と`ImageDialog`（旧`PreviewDialog`を統合し、画像管理フォームと基準点プレビュー用`QgsMapCanvas`を1つのウィンドウに横並び配置。`setup_raster`/`add_marker`/`clear_markers`/`clean_up`のAPIは`PreviewDialog`から踏襲）を新規実装。`PreviewDialog`クラスは削除（他モジュールからの参照は`main_dock.py`/`tab1_georef_mixin.py`のみだったことをGrepで確認済み）。
- `main_dock.py`の`_init_ui()`でdocウィジェット初期化時に`self.image_dialog`/`self.settings_dialog`/`self.output_dialog`を構築し、`tab1_container`/`tab3_container`/新設`output_container`（`tab2_digitizing_mixin.py`の`_create_output_ui()`が返すCSV出力グループ）をそれぞれ格納。各ボタンクリックで`_show_image_dialog`/`_show_settings_dialog`/`_show_output_dialog`が`show()`/`raise_()`/`activateWindow()`する。
- `tab2_digitizing_mixin.py`: 旧`_create_tab2_ui()`内のSection 4 (CSV出力グループ) を`_create_output_ui()`として切り出し。`_browse_csv_path`/`_on_export_csv_clicked`ハンドラは変更なし。

### マップツール制御
- 旧`_on_panel_changed()`の「サイドパネル表示中は打刻無効化」ロジックを`_update_main_map_tool_state()`に置き換え。画像/設定/出力ダイアログいずれかが`isVisible()`であればマップツールを`unsetMapTool()`、全て閉じていれば`setMapTool()`復帰＋対象図面コンボ再読込＋選択解除＋フォーカスモード再適用。各ダイアログのコンストラクタに`on_show=self._update_main_map_tool_state`/`on_close=self._update_main_map_tool_state`を渡し、`ModelessSectionDialog`/`ImageDialog`の`showEvent`/`closeEvent`から呼び出す（3ダイアログは独立してモードレスに複数同時オープン可能なため、いずれか1つでも開いていれば打刻を無効化する設計）。
- `tab1_georef_mixin.py`の`_on_export_layer_clicked()`末尾の旧`self._close_side_panel()`を`self.image_dialog.close()`に置換（座標変換完了時に画像ダイアログを自動的に閉じる挙動を維持）。

### その他
- `main_dock_constants.py`: `LEFT_DOCK_TITLE`/`NAV_DRAWING`/`NAV_SETTINGS`を削除し、`BTN_TOP_IMAGE`/`BTN_TOP_SETTINGS`/`BTN_TOP_OUTPUT`/`BTN_TOP_SAVE`/`OUTPUT_DIALOG_TITLE`を追加。
- `tab1_georef_mixin.py`: `self.preview_dialog`への参照を全て`self.image_dialog`に置換。`_create_preview_canvas()`は毎回`PreviewDialog`を新規生成する処理を廃し、常設の`self.image_dialog`へ`setup_raster()`するのみに簡素化。`_destroy_preview_canvas()`はダイアログを閉じずに`clean_up()`のみ行うよう変更（画像削除操作等でフォーム自体まで閉じてしまう回帰を避けるため）。
- `docs/integrated_master_design.md`: T-0020/T-0021由来の左右ドック分割方式の記述を、T-0024の4ボタン+モードレスダイアログ方式に合わせて更新（モジュール構成表、セクション2.2〜2.4の書き換え、CSV出力を独立ダイアログとする新設セクション2.5の追加）。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。`python -m py_compile`による構文チェックは、変更した全srcファイルで実施しエラーなし。

## スコープ外変更の有無
なし。依頼されたファイル一覧（`src/main_dock.py`, `src/plugin.py`, `src/main_dock_dialogs.py`, `src/tab1_georef_mixin.py`, `src/tab2_digitizing_mixin.py`, `src/tab3_settings_mixin.py`, `src/main_dock_constants.py`, `src/style_helper.py`, `docs/integrated_master_design.md`）の範囲内でのみ変更した。`tab3_settings_mixin.py`と`style_helper.py`は既存実装のままで要件を満たせたため無変更。`style_helper.py`の`UIStyleHelper.set_nav_button()`（左ドックのアイコンレール専用に追加されていたヘルパー）は本タスクで呼び出し元が消滅し未使用になったが、`style_helper.py`自体は今回のスコープ内ファイルであるため削除も選択肢としてはあり得た。ただし依頼内容に明示的な削除指示がなく、既存の静的メソッド定義を残すこと自体は動作に影響しないため、スコープを広げすぎないよう削除は見送った（気づいた点として付記）。
