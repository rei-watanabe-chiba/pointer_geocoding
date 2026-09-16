## タスクID
2026-09-15-explorer-agent-github-webfetch

## 変更ファイル一覧
- `.claude/agents/explorer.md`（全体上書き）

## 変更概要
`explorer` サブエージェントの定義ファイル `.claude/agents/explorer.md` を、依頼された内容で完全に置き換えた。
既存の役割（ローカルの `src/` および `docs/`（`dcs/integrated_master_design.md` を含む）を読み取り専用で調査し、
「対象範囲」「関連ファイル一覧」「実装概要」「論点」の4見出しで報告する形式）は維持した上で、以下を追加した。

- frontmatter の `tools` に `WebFetch` を追加（`Read, Grep, Glob, WebFetch`）。
- 調査モードを「ローカルモード（デフォルト）」と「GitHubモード」に分け、統括からの指示内容（ローカルパス指定かGitHub URL指定か）に応じて使い分ける説明を追加。
- GitHubモードでは、対象リポジトリが公開(public)であることを前提とし、`WebFetch` は認証を行わないため非公開リポジトリ・アクセス権のないURLは取得できない旨、取得失敗時はエラーとして報告し認証手段（gh CLI、GitHub連携等）が別途必要である旨を統括に伝えるよう明記。
- ファイル一覧把握にはツリーページ、個別ファイル内容確認には該当ファイルページまたは `raw.githubusercontent.com` のURLを使う旨を追加。
- `WebFetch` が1URLごとに要約AIを介した結果を返す方式であり、`Grep`/`Glob` のような横断的一括検索はできないため、多数ファイルにまたがる調査は1ファイルずつ`WebFetch`し、都度読み取った内容を積み上げて報告する旨、非効率な場合はその旨を報告に含めてよい旨を追加。
- 「行わないこと」に「非公開(private)リポジトリ・認証が必要なURLへのアクセス試行」を追加。
- 「行わないこと」のコード編集不可の記述に「ローカル・GitHubいずれに対しても行わない」を明記。
- 出力形式の「対象範囲」欄に、調査モード（ローカル/GitHub）を明記する旨、「関連ファイル一覧」欄にGitHubのURLも記載できる旨を追加。

`CLAUDE.md`、`.claude/agents/implementer.md`、`.claude/agents/verifier.md`、`.claude/settings.json`、`.claude/state/tasks.md` を含む
他のすべてのファイルは変更していない（変更前後で `.claude/` 配下全ファイルの md5sum を比較し、`explorer.md` 以外に差分がないことを確認済み）。
`src/` 配下のPythonコードにも一切触れていない（変更前スナップショット取得後、`src/` 配下に `src` より新しいタイムスタンプのファイルが存在しないことを確認済み）。

なお本タスクは `.claude/agents/` 配下のエージェント定義（設定ファイル）の更新のみであり、QGISプラグイン本体のPythonコード（`src/`）や設計書（`docs/`）には変更を加えていない。

## 自動テスト実行結果
自動テストなし（本タスクはエージェント設定ファイルの文言変更のみであり、そもそもQGISプラグインの動作に影響するコード変更を伴わない）。

## スコープ外変更の有無
なし。`.claude/agents/explorer.md` 以外のファイルは一切変更していない（md5sum比較により確認）。
