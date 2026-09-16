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

## v2開発フェーズ（完了・統合済み）

| タスクID | 概要 | 状態 |
|---|---|---|
| T-0043 | src配下を責務別フォルダ(ui/layer/logic/canvas)へ再構成。ロジック変更なし、ファイル移動+import文の追従修正のみ | 完了 |
| T-0044 | QSpinBoxへの安全なQSS適用パターン確立(矢印つぶれ対策)。試行錯誤の詳細は`.claude/logs/implement/2026-09-16-T-0044-qspinbox-safe-qss.md`参照。確定した安全パターン: ①ボタン`subcontrol-position`必須指定 ②矢印グリフはborder-triangleハック不可・base64データURIも不可(QTBUG-51081)、`src/icon/`の実SVGファイルを絶対パスurl()参照 ③押下フィードバックはボタン背景色変化ではなく矢印アイコン自体の色替え(`::up-arrow:pressed`等)で行う(背景色変化はフォーカス枠等とのボックスモデル重なりを誘発するため不採用) | 完了 |
| T-0045〜T-0045-b | CoreUI試作(`src/ui/core/`新設: field_spec.py/builder.py/rules.py/validators.py)、tab1_image.pyへ適用。UI構築の宣言化・値の抜き出し/書き込み共通化(BuiltPanel.get_value/set_value/collect_values)・スキーマ統合(`src/ui/schemas.py`)・座標変換後ダイアログ廃止・バリデーション/エラー表示ヘルパー化(Validator+show_validation_error)・LayerManager高レベルAPI追加(clear_drawing_name_for_layer/rename_drawing_name)。tab1_image.py 1151→1046行。storage/upload側の汎用ルール化(CommitRule等)はT-0047へ据え置き。基準点系の別ファイル分割は効果薄のため見送り。人手確認済み。詳細は`.claude/state/v2-coreui-plan.md`、実装ログは`.claude/logs/implement/2026-09-16-T-0045-coreui-tab1.md`・`2026-09-16-T-0045-b-tab1-dialog-validators-layermanager.md` | 完了 |

## 進行中

**巨大ファイル対応の計画（T-0045〜T-0051）**: 詳細計画は`.claude/state/v2-coreui-plan.md`を参照。
T-0045/T-0045-b完了。`docs/fromGemini/`の2改定案を検討した結果、T-0046以降を以下の通り再構築
（2026-09-16確定）。採用方針（UI→Logic→Layer→QGIS/Diskの単方向依存・薄いコントローラー化）、
却下項目（core/2ファイル再編・SymbologyMixin剥離）の詳細は同ファイル「T-0046以降の方針確定」節
を参照。tab2改修（T-0050）時の申し送り事項は同ファイルの「⑤tab2改修（旧T-0046、現T-0050）への
申し送り事項」節を参照。

| タスクID | 概要 | 状態 |
|---|---|---|
| T-0046 | start_dialog.py（実測1101行）へCoreUI適用 | 承認待ち |
| T-0047 | dialogs.py（実測808行）へCoreUI適用（GridInputDialog/FeatureCreateDialog/PointNameEntryDialog） | 承認待ち |
| T-0048 | tab3_settings.py（実測367行）へCoreUI適用（最小規模から着手） | 承認待ち |
| T-0049 | src/logic/分離状況の棚卸し（調査のみ、実装なし） | 承認待ち |
| T-0050 | tab2_plot.py（実測1905行）へCoreUI適用＋T-0049結果に基づくlogic移管 | 承認待ち |
| T-0051 | map_tool.pyのdock逆参照排除（getattr(self.dock_widget, "tab2_current_mode", "new")をPush通知化） | 承認待ち |

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
