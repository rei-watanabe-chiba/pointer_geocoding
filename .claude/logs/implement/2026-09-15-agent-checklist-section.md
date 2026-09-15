## タスクID
2026-09-15-agent-checklist-section

## 変更ファイル一覧
- `.claude/agents/explorer.md`
- `.claude/agents/implementer.md`

## 変更概要
- `.claude/agents/explorer.md` と `.claude/agents/implementer.md` の末尾に、「PyQGISコード削減チェックリスト(pointer_geocoding特化)」セクションを追記した。
- 追記内容は依頼文で指定された内容（Enum/dataclass/contextmanager/pathlib/QGIS標準ウィジェット/シグナルconnect-disconnect対称性/QActionのsetObjectName に関するチェック項目、および「本プロジェクトでは非採用」として QgsSettings・Qt Designer(.uiファイル)・Processing Framework を明示的に対象外とする記述）をそのまま両ファイルに追加した。
- 両ファイルとも既存の frontmatter・役割説明・出力形式・禁止事項等の既存内容は変更せず、末尾への追記のみを行った。
- `.claude/agents/verifier.md` は依頼どおり変更していない。
- `src/` 配下の Python コードは変更していない。

## 自動テスト実行結果（なければ「自動テストなし」）
自動テストなし（本プロジェクトには自動テストコマンドが設定されていないため）。設定ファイル(Markdown)の追記のみであり、コードの構文/型チェック対象にも該当しない。

## スコープ外変更の有無
なし。依頼された `.claude/agents/explorer.md` と `.claude/agents/implementer.md` の末尾追記のみを行い、`.claude/agents/verifier.md`、`CLAUDE.md`、`settings.json`、`.claude/state/tasks.md`、`src/` 配下のファイルはいずれも変更していない。
