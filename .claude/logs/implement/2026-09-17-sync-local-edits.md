## タスクID
軽微修正-02（sync_local_edits.bat新規作成）

## 変更ファイル一覧
- `sync_local_edits.bat`（新規作成）
- `.claude/state/tasks.md`（1行追加、状態: 静的検証中）

## 変更概要
CLAUDE.mdのGit運用ルールでは`test`/`main`ブランチ上で直接コミットを作ることが禁止されている
（`sync_test.bat`/`sync_main.bat`が`git reset --hard origin/<branch>`でリモートへ強制一致させる
運用のため）。しかしユーザーがQGIS上での動作確認中にローカルで直接ファイルを編集してしまう
ケースに対応するため、その編集を「正」として開発フローに載せ直すスクリプトを新設した。

`sync_local_edits.bat`の処理内容:
1. 冒頭で`set BRANCH_NAME=local-edits`としてブランチ名を変数化（将来変更しやすくするため）。
2. `choice /c YN /m "Continue"`で実行前に確認を求める（依頼要件5を満たす。既存2バッチには
   確認ステップがないため、この点のみ新規パターンとして追加）。
3. `git diff --quiet` / `git diff --cached --quiet`（既存batと同じロジック）に加え、
   `git status --porcelain | findstr "^??"`で未追跡ファイルの有無も確認し、いずれもなければ
   「No changes to sync.」を表示して終了する。
4. 変更がある場合は`git stash push -u -m "..."`で未追跡ファイルも含めて退避。
5. 既存の`local-edits`ブランチがあれば`git branch -D local-edits`で削除（`>nul 2>&1`でエラー抑制。
   存在しない場合のエラーは無視してよいという要件どおり）。
6. 現在のブランチ（想定test）から`git checkout -b local-edits`で新規作成・チェックアウト。
7. `git stash pop`で退避内容を復元。
8. `git add -A` → `git commit -m "Local edits synced via sync_local_edits.bat (%date% %time%)"`。
9. `git push -u origin local-edits --force`でリモートへ強制push（ブランチを毎回作り直す前提のため）。
10. `git checkout test`で元のブランチへ復帰。
11. 各ステップは`if not %errorlevel%==0 goto <ラベル>`で失敗時に処理を中断しエラーメッセージを表示
    （既存2バッチと同じパターン）。特にcheckout失敗時・stash pop失敗時は、変更が失われないよう
    「stashは残っている」「branchにはpush済み」等の状況をechoで案内する文言を追加した。
12. 最後に「Claude Codeセッションにブランチ名`local-edits`をpushした旨を伝えてください」という
    案内を表示。

## 既存bat（sync_test.bat/sync_main.bat）との整合性確認
- 冒頭`@echo off` / `setlocal` / `cd /d "C:\claude\project\pointer_geocoding"`は既存2ファイルと同一。
- ASCII文字のみで記述（Pythonスクリプトでバイト列を検査し、CR/LF/TAB以外の制御文字・非ASCII
  バイトが含まれないことを確認済み）。
- 改行コードはCRLF（`file`コマンドで`DOS batch file, ASCII text, with CRLF line terminators`と
  確認済み。Writeツールでの初回出力はLFだったため、Pythonで`\n`→`\r\n`変換を実施した）。
- 未コミット変更検知ロジック（`git diff --quiet` / `git diff --cached --quiet`とerrorlevel判定）は
  既存batを踏襲し、未追跡ファイル検知のみ`git status --porcelain`で追加。
- エラー時に`pause`で待機し`exit /b 1`で終了するパターンは既存2ファイルと同一。
- 既存2ファイルにはない要素（`choice`による事前確認、`git branch -D`、`stash push/pop`、
  `push --force`）は、依頼要件に明記された処理のため新規追加した。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
なお本バッチファイル自体はWindows専用スクリプトであり、Linux環境の本セッションでは
実行による動作確認はできない（構文・エンコーディング・改行コードの静的確認のみ実施）。

## スコープ外変更の有無
なし。`sync_local_edits.bat`の新規作成と`.claude/state/tasks.md`への1行追加のみ。
`src/`配下・既存の`sync_test.bat`/`sync_main.bat`には一切手を加えていない。
