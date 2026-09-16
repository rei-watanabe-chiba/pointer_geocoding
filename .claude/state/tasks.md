# タスク状態

状態遷移: 承認待ち → 実装中 → 静的検証中 → 人手確認待ち → 完了

詳細な実装内容・検証根拠は各タスクの実装ログ（`.claude/logs/implement/{日付}-T-XXXX-*.md`、
タスクIDでglob検索可能）を参照。本表は要約のみとし、定期的に完了・統合済みタスクを圧縮する
（下記「圧縮ルール」参照）。

## v1開発フェーズ（完了）

| タスクID | 概要 | 状態 |
|---|---|---|
| T-0002〜T-0042 | v1開発フェーズ全体（基盤リファクタリング／WinError32対策と画像管理設計転換／左右ドック→右ドック1枚統合／点番号採番・SP属性自動化／UI4パネル常時展開化／新規・編集モード分離とリアルタイムコミット方式の確立 等）。詳細は`.claude/logs/archive/v1-summary.md`（フェーズ別要約）および`.claude/logs/implement/v1/`（個別実装ログ）を参照 | 完了 |

v2開発はタスクIDをT-0043から連番継続する。

## 進行中

| タスクID | 内容 | 状態 | 実装ログ | 検証結果 | 人手確認 |
|---|---|---|---|---|---|
| T-0043 | v2開始: src配下を責務別フォルダ(ui/layer/logic/canvas)へ再構成。ロジック変更なし、ファイル移動+import文の追従修正のみ。マッピング: ui/(start_dialog.py, dock.py←main_dock.py, constants.py←main_dock_constants.py, dialogs.py←main_dock_dialogs.py, tab1_image.py←tab1_georef_mixin.py, tab2_plot.py←tab2_digitizing_mixin.py, tab3_settings.py←tab3_settings_mixin.py, style.py←style_helper.py) / layer/(manager.py←layer_manager.py, models.py←layer_manager_models.py, settings_io.py←settings_metadata_mixin.py, gpkg.py←gpkg_cache_mixin.py, grid_csv.py←grid_csv_mixin.py, session_io.py←session_io_mixin.py, symbology.py←symbology_mixin.py) / logic/(core.py←core_logic.py, transform.py) / canvas/(map_tool.py)。__init__.py/plugin.py/metadata.txt/icon/はルート据え置き。クラス名・メソッド名は変更しない。設計書(docs/integrated_master_design.md 1.3/1.4節)も新パスへ追従更新済み | 人手確認待ち | `.claude/logs/implement/2026-09-16-T-0043-restructure-src-into-responsibility-folders.md` | 静的検証: 問題なし | - |

## 使い方
- 新しいタスクを開始する際は、この表に1行追加し「承認待ち」から開始する
- `/implement-scope` でimplementerに委譲したら「実装中」に更新する
- implementer完了後、verifierに検証を依頼し「静的検証中」に更新する
- verifierが「静的検証: 問題なし。実行環境での確認が必要」を返したら「人手確認待ち」に更新し、
  implementerが作成した `.claude/logs/implement/{日付}-{タスク名}-checklist.md` の内容をユーザーに提示する
- ユーザーから人手確認完了の報告を受けたら「完了」に更新する
- verifierが不整合を報告した場合は「実装中」に戻し、implementerに再依頼する

## 圧縮ルール（トークン消費抑制のため）
- 「完了」または「統合済み」になったタスクは、次にtasks.mdを編集するタイミングで
  「完了・統合済み」表へ1行（タスクID・概要・状態のみ）に要約して移動する
  （検証結果・人手確認欄の詳細な経緯はここでは保持しない。実装ログに残っているため参照可能）
- 一連の試行錯誤（バグ調査で複数タスクに分岐した場合等）は、最終的に解決したタスクへの
  誘導コメント1行にまとめ、個別の経緯は展開しない
- 「進行中」表の行は、人手確認完了まで詳細を保持してよいが、完了確認後は上記ルールで圧縮する
- **v1〜v2フェーズ境界（本ファイル導入時点のルール）**: v1開発フェーズ完了時、それまでの
  「完了・統合済み」表全体を`.claude/logs/archive/v1-summary.md`へ切り出し、本表には
  1行の要約のみを残した（2026-09-16）。今後v2の完了タスクが蓄積し本表が肥大化した場合も、
  同様に`.claude/logs/archive/v2-summary.md`等へ切り出して圧縮してよい。
