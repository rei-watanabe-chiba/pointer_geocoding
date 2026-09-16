# 実装ログ

## タスクID
T-0020

## 変更ファイル一覧
- `src/main_dock.py`
- `src/tab1_georef_mixin.py`
- `src/style_helper.py`
- `src/main_dock_constants.py`
- `docs/integrated_master_design.md`
- `.claude/state/tasks.md`（タスク表への実装ログパス追記のみ）

## 変更概要

### 1. `src/main_dock.py`
- `_init_ui()`を全面改修。従来の`QTabWidget`（画像管理／遺物点作成／設定の3タブ）を廃止し、
  以下の構成に再編した。
  - `root_widget (QVBoxLayout)`
    - `btn_save_project`（変更なし）
    - `content_row (QHBoxLayout)`
      - `icon_rail`（固定幅52px、`nav_btn_drawing`「図面」／`nav_btn_settings`「設定」の
        チェッカブル`QToolButton`2つ＋`addStretch()`）
      - `side_panel`（固定幅300px、`QStackedWidget`（`side_stack`）に`tab1_container`（図面管理）
        ／`tab3_container`（設定）を積み、初期状態`.hide()`）
      - `tab2_container`（遺物点作成。タブなしで常時表示のメインエリア、`content_row`にstretch=1で追加）
  - `self.tab1_container`/`self.tab2_container`/`self.tab3_container`属性名は維持（他ファイルからの
    参照を壊さないため）。`self.tab_widget`は廃止。
- ナビゲーションボタンの開閉制御として`self.nav_button_group`（`QButtonGroup`, `setExclusive(True)`）
  を導入し、2ボタン間の排他選択を担わせつつ、`clicked`シグナル経由の`_on_nav_button_clicked(panel)`で
  「開いている側のボタンを再クリックしたら`setChecked(False)`して閉じる」制御を明示的に実装
  （exclusiveなQButtonGroupは再クリックだけではチェック解除されない仕様のため）。
- 旧`_on_tab_changed(index: int)`（`QTabWidget.currentChanged`ハンドラ）を`_on_panel_changed(self)`に
  置き換え。`self._active_panel`（`"drawing"`/`"settings"`/`None`）を見て、
  - `"drawing"`: `side_panel.show()`+`side_stack`を`tab1_container`に切替、`canvas.unsetMapTool()`
    （旧index==0相当）
  - `"settings"`: 同上+`tab3_container`に切替、`canvas.unsetMapTool()`＋`update_settings_ui_from_dict()`
    （旧index==2相当）
  - `None`（両パネル閉）: `side_panel.hide()`、`_update_drawing_combo()`・`canvas.setMapTool()`・
    `_reset_point_selection()`・フォーカスモード時`update_symbology_opacity()`（旧index==1相当。
    これが既定状態）
  を実行するよう再設計した。
- `__init__()`末尾の「Initial active tab handling」（`raster_layer`の有無で`tab_widget.setCurrentIndex`
  を条件分岐していた箇所）を撤廃し、`self._on_panel_changed()`を無条件で1回呼ぶだけに変更した。これにより
  起動直後は常に「両パネル閉・メインエリア（遺物点作成）表示・マップツール有効」という既定状態になる
  （ユーザー要件の「起動直後は遺物点作成エリアがメインに表示され、パネルは閉じている」を満たすため、
  旧来のraster_layer有無による分岐条件は撤去した）。
- 新規メソッド`_close_side_panel()`を追加。両ナビボタンを`setChecked(False)`し`self._active_panel = None`
  にした上で`_on_panel_changed()`を呼ぶ。旧`self.tab_widget.setCurrentIndex(1)`（座標変換→レイヤ出力
  完了後のTab2自動遷移）の置き換え先として使用。
- モジュール冒頭のdocstring・`update_symbology_opacity()`のdocstring内の`_on_tab_changed`言及を
  `_on_panel_changed`に追随更新。

### 2. `src/tab1_georef_mixin.py`
- `_on_export_layer_clicked()`末尾の`self.tab_widget.setCurrentIndex(1)`を`self._close_side_panel()`
  に置き換え。
- `_create_tab1_ui()`内の情報パネル（`self.panel_tab1_info`）について、生成コード自体の位置は変えず、
  `layout.addWidget(self.panel_tab1_info)`の呼び出し位置のみをレイアウト先頭（モードトグルの直前）から
  末尾（`sec_transform`の後、`layout.addStretch()`の直前）へ移動し、パネル最下部に表示されるようにした。
  内部のラベル・入力欄・テーブル・ボタン構成、新規追加/編集削除トグル、レイヤ名変更/削除/基準点設置
  ボタンのロジックは一切変更していない。

### 3. `src/style_helper.py`
- QSSに`QToolButton[navButton="true"]`（通常時/`:hover`/`:checked`）のスタイル定義を追加
  （左アイコンレールのナビゲーションボタン用。`:checked`時は`palette(highlight)`背景でパネル開状態を表現）。
- 静的メソッド`UIStyleHelper.set_nav_button(button)`を追加（`navButton`プロパティを立てて`polish()`する、
  既存の`set_primary_button`等と同パターン）。

### 4. `src/main_dock_constants.py`
- `UILabels`に`NAV_DRAWING = "図面"` / `NAV_SETTINGS = "設定"`を追加（アイコンレールのボタンラベル用）。

### 5. `docs/integrated_master_design.md`
- 1.4節の`main_dock.py`の説明を、新しいアイコンレール＋サイドパネル＋メインエリア構成、
  `_on_nav_button_clicked`/`_on_panel_changed`/`_close_side_panel`の役割を反映する内容に更新。
- 2.2節見出しを「Tab 1」→「図面管理サイドパネル（旧Tab 1）」に変更し、パネルの開閉操作・情報パネルの
  位置（最下部）を追記。座標変換→レイヤ出力完了時の遷移先の記述を「Tab 2へ遷移」→「サイドパネルが
  自動的に閉じてメインエリアに戻る」に更新。
- 2.3節見出しを「Tab 2」→「メインエリア（旧Tab 2）」に変更し、タブ化されていない旨・サイドパネルが
  開いている間はマップツールが無効化される旨を追記。
- 2.4節見出しを「Tab 3」→「設定サイドパネル（旧Tab 3）」に変更し、設定パネルを開くたびに
  `update_settings_ui_from_dict()`が呼ばれる旨を追記。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile` による構文チェックのみ実施し、変更対象ファイル・`src/`配下全ファイルとも
エラーなくコンパイルできることを確認した（静的な構文確認であり、QGIS実行時の動作を保証するものではない）。

## スコープ外変更の有無
なし。依頼スコープ（`src/main_dock.py`中心、必要に応じて`tab1_georef_mixin.py`・`style_helper.py`・
`main_dock_constants.py`・設計書）の範囲内で完結しており、`tab2_digitizing_mixin.py`・
`tab3_settings_mixin.py`・その他ファイルへの変更は行っていない（`tab_widget`/`tab1_container`等の
参照箇所をgrepで確認した結果、`main_dock.py`と`tab1_georef_mixin.py`以外に該当箇所は無かった）。
`.claude/state/tasks.md`への実装ログパス追記は運用ルールに基づくものでありスコープ外変更ではない。
