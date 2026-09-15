# タスク状態

状態遷移: 承認待ち → 実装中 → 静的検証中 → 人手確認待ち → 完了

| タスクID | 内容 | 状態 | 実装ログ | 検証結果 | 人手確認 |
|---|---|---|---|---|---|
| (例) T-0001 | (タスク概要をここに) | 承認待ち | - | - | - |
| T-0002 | Stage A: to_excel_column/from_excel_column 重複統合（layer_manager.py, start_dialog.py → core_logic.py） | 完了 | `.claude/logs/implement/2026-09-14-stageA-excel-column-utility-consolidation.md` | 静的検証問題なし | ユーザーがQGIS上で動作確認済み（グリッド座標プレビュー・グリッドCSV生成・既存セッション読込） |
| T-0003 | Stage B: main_dock.py のMixinベース分割（main_dock.py 3,088行→308行、tab1_georef_mixin.py/tab2_digitizing_mixin.py/tab3_settings_mixin.py/main_dock_constants.py/main_dock_dialogs.pyへ分割） | 完了 | `.claude/logs/implement/2026-09-14-stageB-main-dock-mixin-split.md`（+差し戻し修正ログ `.claude/logs/implement/2026-09-14-stageB-docs-checklist-fix.md`） | 静的検証問題なし（差し戻し修正後、再検証で確認済み） | ユーザーがQGIS上で動作確認済み（プラグイン起動、Tab1画像管理〜変換〜レイヤ出力、Tab1編集削除、Tab2打刻〜CSV出力〜フォーカスモード、Tab3設定適用、いずれも問題なし） |
| T-0004 | Stage C: layer_manager.py のMixinベース分割（layer_manager.py 約1,380行→大幅縮小、layer_manager_models.py/settings_metadata_mixin.py/symbology_mixin.py/gpkg_cache_mixin.py/grid_csv_mixin.py/session_io_mixin.pyへ分割） | 完了 | `.claude/logs/implement/2026-09-14-layer-manager-mixin-split.md` | 静的検証問題なし | ユーザーがQGIS上で動作確認済み（プラグインロード、新規/既存セッション、Tab1〜3操作、打刻時のObserver同期、設定適用、プロジェクト保存、いずれも問題なし） |
| T-0005 | デッドコード削除（A+B+C区分：後方互換エイリアス2メソッド・未使用属性・未使用UI定数5個・defensive re-export削除） | 完了 | `.claude/logs/implement/2026-09-15-deadcode-removal.md` | 静的検証問題なし | ユーザーがQGIS上で動作確認済み |
| T-0006 | Stage D+E: 低リスク共通化（レイヤ編集ヘルパー化/JSON IO統一/QMessageBoxヘルパー化、シンボロジ・透過度操作の一元化） | 完了 | `.claude/logs/implement/2026-09-15-stage-d-common-helpers.md`, `.claude/logs/implement/2026-09-15-stageE-symbology-opacity-consolidation.md` | 静的検証問題なし | ユーザーがQGIS上で動作確認済み（「安定動作を確認しました」） |
| T-0007 | Stage F: `_on_canvas_clicked()`の責務分解（次点ID採番ロジックを`get_next_point_id()`、GeoPackage書き込みを`insert_feature_to_layer()`として`core_logic.py`へ抽出） | 完了 | `.claude/logs/implement/2026-09-15-stageF-on-canvas-clicked-decomposition.md` | 静的検証問題なし | ユーザーがQGIS上で動作確認済み（「動作確認した。問題ない」） |
| T-0008 | 第1フェーズ アプローチB+G: UIコンボ/リスト更新パターンの共通ヘルパー化（`_update_drawing_combo`/`_refresh_edit_layer_combo`/`_refresh_ref_points_table_and_markers`等）＋UIコンポーネント生成ヘルパー拡張（Tab3のみ実施、Tab1/2は未着手）を`style_helper.py`へ集約（ファイル分割なし） | 完了 | `.claude/logs/implement/2026-09-15-T-0008-ui-helper-consolidation.md` | 静的検証問題なし（`rebuild_table_rows`内add_marker呼び出し順序の軽微な差異あり、実害なしと判断） | ユーザーがQGIS上で動作確認済み（チェックリスト全項目クリア）。人手確認中に報告された読込速度低下は、diff比較の結果T-0008のコード変更とは無関係と判明。QGIS再起動を挟んだ再テストで速度低下も解消したため、プラグインリロードを繰り返した際のシグナル接続蓄積等、環境要因と結論 |
| T-0009 | 第2フェーズ アプローチF: 属性値取得・型変換の統一ヘルパー（`core_logic.py`にNULL/型変換を一元化する`safe_get_str()`/`safe_get_float()`等を新設し、`core_logic.py`/`tab1_georef_mixin.py`/`tab2_digitizing_mixin.py`内の重複パターンを置換、`main_dock_dialogs.py`は該当パターンなしのため無変更、ファイル分割なし） | 人手確認待ち | `.claude/logs/implement/2026-09-15-T-0009-attr-safe-get-helpers.md` | 静的検証問題なし（`_apply_feature_color_group`の`.strip()`新規付与について、書き込み経路を追跡し実運用上の挙動差なしと判断。念のため人手確認推奨） | T-0009の人手確認手順4実施中に既存バグ(T-0010)を発見、そちらを優先対応中のため保留 |
| T-0010 | バグ修正: 画像レイヤ名変更時の`os.rename()`が`[WinError 32]`で失敗する不具合（`tab1_georef_mixin.py`の`_on_confirm_image_clicked()`編集モード分岐。QGISにラスタレイヤが読み込まれたままファイルリネームを行いGDALのファイルハンドルと衝突、Windows環境で再現）。改修前(Initial commit)から存在する既存バグでT-0008/T-0009由来ではないことをgit logで確認済み。リネーム前にレイヤを解放→リネーム→新パスで再読込（スタイル/グループ/位置/表示状態を復元）する方式に変更 | 静的検証中 | `.claude/logs/implement/2026-09-15-T-0010-image-rename-winerror32-fix.md` | - | - |

## 使い方
- 新しいタスクを開始する際は、この表に1行追加し「承認待ち」から開始する
- `/implement-scope` でimplementerに委譲したら「実装中」に更新する
- implementer完了後、verifierに検証を依頼し「静的検証中」に更新する
- verifierが「静的検証: 問題なし。実行環境での確認が必要」を返したら「人手確認待ち」に更新し、
  implementerが作成した `.claude/logs/implement/{日付}-{タスク名}-checklist.md` の内容をユーザーに提示する
- ユーザーから人手確認完了の報告を受けたら「完了」に更新する
- verifierが不整合を報告した場合は「実装中」に戻し、implementerに再依頼する
