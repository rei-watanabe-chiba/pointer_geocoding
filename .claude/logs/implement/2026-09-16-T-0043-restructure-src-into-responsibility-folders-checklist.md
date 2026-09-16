## 人手確認チェックリスト

### 確認手順
1. `sync_test.bat` を実行し、ローカル環境の `test` ブランチを最新化する（本タスクの変更を取得する）。
2. QGISを起動し、プラグインマネージャー等から「点群座標取得」（pointer_geocoding）プラグインを有効化し、エラーダイアログ（ImportError等）が出ずにプラグインアイコン/ツールバーボタンが表示されることを確認する。
3. ツールバーボタンまたはメニューから `StartDialog` を開き、新規セッション作成 または 既存セッション読込を行い、右ドックの `MainDockWidget` が表示されることを確認する。
4. 右ドック上部の「画像」ボタンをクリックし、`ImageDialog`（IMG画面）が開くことを確認する。画像ファイルを選択し、基準点を数点設置し、「座標変換」→「レイヤ出力」を実行して、画像がメインキャンバスへ配置されることを確認する。
5. メインキャンバス上（PLOT画面 = Tab2常時表示エリア）で、対象図面選択後にクリックして打刻点が作成されることを確認する。点名/枝番/属性(S/P/C/SP)の入力・既存点編集（点名変更・削除）も一通り確認する。
6. 「設定」ボタンをクリックし、`Tab3SettingsMixin`（SET画面）のシンボル色・ラベル設定変更→「適用」で、打刻点/基準点のシンボロジが即時反映されることを確認する。
7. 「出力」ボタンをクリックし、CSV出力ダイアログ（OUT画面）でCSV出力先を指定し、「CSV出力」を実行してファイルが生成されることを確認する。
8. プラグインを一度アンロード（無効化）→再度有効化し、エラーなく再起動できることを確認する（`plugin.py`のimport経路変更が正しく機能しているかの再確認）。

### 各手順で期待される挙動（設計書ベース）
- 手順2: `docs/integrated_master_design.md` 77行目「plugin.py: エントリポイント。QGISメニューへの登録と StartDialog の起動。」の記述通り、`src/plugin.py`が`src/ui/start_dialog.py`・`src/layer/manager.py`・`src/ui/constants.py`を正しくimportしてエントリポイントとして機能することが前提。import経路の変更ミスがあれば、この時点でプラグイン有効化自体が失敗する。
- 手順3: 同79行目「main_dock.py: メイン操作UIの共通基盤。（中略）`MainDockWidget`は**単一の`QDockWidget`**のみで構成される。」の通り、`src/ui/dock.py`（旧main_dock.py）が`src/ui/tab1_image.py`/`tab2_plot.py`/`tab3_settings.py`/`dialogs.py`/`constants.py`および`src/canvas/map_tool.py`/`src/ui/style.py`を正しくimportしてMainDockWidgetを構築できることが前提。
- 手順4: 同82行目・123-131行目「画像ダイアログ（内部識別子ではTab1）」の一連の記述通り、`src/ui/tab1_image.py`（Tab1GeorefMixin）が`src/logic/transform.py`（CoordinateTransformer）・`src/logic/core.py`・`src/ui/constants.py`・`src/ui/dialogs.py`（GridInputDialog）を正しくimportして座標変換・レイヤ出力処理が機能することが前提。
- 手順5: 同83行目「tab2_digitizing_mixin.py: `Tab2DigitizingMixin`。（中略）新規/編集モード切替トグル・打刻・既存点削除/選択解除・リアルタイムコミット」の記述通り、`src/ui/tab2_plot.py`が`src/logic/core.py`・`src/logic/transform.py`・`src/ui/dialogs.py`（FeatureCreateDialog/PointNameEntryDialog）を正しくimportして打刻・編集機能が動作することが前提。
- 手順6: 同84行目「tab3_settings_mixin.py: `Tab3SettingsMixin`。（中略）`LayerManager.settings_changed`購読ハンドラを提供する」の記述通り、`src/ui/tab3_settings.py`が`src/layer/manager.py`（LayerManager、settings_changedシグナル経由）と連携し、設定変更が`src/layer/symbology.py`（SymbologyMixin）のシンボロジ適用処理に伝播することが前提。
- 手順7: 同83行目「CSV出力UI(`_create_tab4_ui`)とそのハンドラ（中略）この出力UIは（中略）独立した`self.output_dialog`に格納される」および96行目「transform.py: （中略）スリム化されたCSV(7項目)出力ロジック」の記述通り、`src/ui/tab2_plot.py`から`src/logic/transform.py`のexport_points_to_csvが正しく呼び出されることが前提。
- 手順8: `src/canvas/map_tool.py`および`src/layer/symbology.py`内の関数内ローカルimport（`from ..ui.dock import UIConfig`）が、プラグインの起動・停止のたびに正しく解決されることの確認（循環import回避のための遅延import機構が、フォルダ移動後も同様に機能するかの確認）。

### 注意喚起
- 本タスクは純粋なファイル移動+import文の追従修正のみであり、ロジック・クラス名・メソッド名は変更していないが、import経路の変更漏れがあると **プラグインの起動そのものが失敗する**（ImportError）ため、最も影響範囲が広く壊れやすい変更である。特に以下の関数内ローカルimport（遅延import、循環import回避のため）は書き換え箇所が分散しており重点確認対象:
  - `src/canvas/map_tool.py` 内の `from ..ui.dock import UIConfig`
  - `src/layer/symbology.py` 内の `from ..ui.dock import UIConfig`
  - `src/plugin.py` 内の `from .ui.dock import MainDockWidget`
- `src/ui/dock.py`冒頭のコメント（91-94行目付近）に旧ファイル名`main_dock.py`を言及する説明文が残っているが、これはコメントのみでimport文自体は新パスに追従済みであり、動作に影響しない（タスク指示に基づき意図的に未修正）。
- `docs/integrated_master_design.md`自体は本タスクのスコープ外のため、旧ファイル名（main_dock.py/layer_manager.py/core_logic.py等）の記述のまま残っている。設計書の更新が必要な場合は別タスクとして依頼すること。
