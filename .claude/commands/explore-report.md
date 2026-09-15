---
description: explorerサブエージェントにpointer_geocodingの調査を依頼する
argument-hint: <調査したい内容>
---

`explorer` サブエージェントを起動し、以下の内容を調査させてください。

調査依頼: $ARGUMENTS

explorerには以下を伝えること:
- 対象コードは `src/`、設計書は `docs/`（および既存の `dcs/integrated_master_design.md`）
- 出力形式は explorer.md 記載のとおり（対象範囲/関連ファイル一覧/実装概要/論点）
- 読み取り専用調査であり、コードの変更は行わない

調査結果が返ってきたら、統括（このセッション）はそれをユーザーに要約して提示し、
必要であれば次のステップ（`/implement-scope` での実装委譲、または追加のヒアリング）を提案すること。
