---
description: implementerサブエージェントにpointer_geocodingの実装を委譲する
argument-hint: <実装スコープ>
---

`implementer` サブエージェントを起動し、以下のスコープで実装させてください。

実装スコープ: $ARGUMENTS

implementerには以下を伝えること:
- 対象コードは `src/`、設計書は `docs/`（および既存の `dcs/integrated_master_design.md`）
- 依頼されたスコープ外の変更は行わない
- 完了時は `.claude/logs/implement/{日付}-{タスク名}.md` に実装ログを必ず作成する
  （タスクID/変更ファイル一覧/変更概要/自動テスト実行結果/スコープ外変更の有無）
- 実装ログに実行時の挙動を断定する記述（「動作確認済み」等）を書かない
- 実行環境依存の確認項目があるため、`.claude/logs/implement/{日付}-{タスク名}-checklist.md` に
  人手確認チェックリストを必ず作成する

implementerの完了後、統括は `.claude/state/tasks.md` を「静的検証中」に更新し、
続けて `verifier` サブエージェントに静的検証を依頼すること。
verifierの結果が「静的検証: 問題なし。実行環境での確認が必要」であれば、
`.claude/state/tasks.md` を「人手確認待ち」に更新し、生成された人手確認チェックリストの内容を
ユーザーに提示して確認を依頼すること。ユーザーから確認完了の報告を受けて初めて「完了」とする。
