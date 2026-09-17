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

---

## 追記（2026-09-17 軽微修正-02改修: コミットメッセージへの変更ファイル一覧追記）

### タスクID
軽微修正-02（sync_local_edits.bat改修: コミットメッセージへ変更ファイル一覧を動的追記）

### 変更ファイル一覧
- `sync_local_edits.bat`（既存ファイルを修正。新規作成・削除なし）

### 変更概要
従来は固定文言+日時のみの1行コミットメッセージ（`git commit -m "..."`）だったため、
後から「ローカル編集をコミットした」という報告のみを受けたClaude Codeセッションが、
どのファイルが変更されたかをコミットメッセージから特定できなかった。これを解消するため、
`git add -A`実行後・コミット前に以下の処理を追加した。

1. `git diff --cached --name-only`の出力を`%TEMP%\sync_local_edits_files_%RANDOM%.txt`
   （ユニークなランダムファイル名）へリダイレクトし、ステージ済み変更ファイル一覧を取得する。
2. `%TEMP%\sync_local_edits_msg_%RANDOM%.txt`にコミットメッセージ本文を組み立てる。
   - 1行目: 従来と同じ見出し行`Local edits synced via sync_local_edits.bat (%date% %time%)`
   - 空行
   - `Changed files:`
   - `for /f "usebackq delims=" %%F in ("%TEMP_FILES%") do (...)`ループで、ファイル一覧の各行を
     `- <path>`形式で追記（`delims=`指定によりファイル名中のスペースを含む行もそのまま1トークンと
     して扱われる）。
   - 変更ファイルが0件だった場合のガードとして、ループ内で立てるフラグ`HASFILES`が0のままなら
     `- (no files detected)`を1行追記する。
3. `git commit -m "..."`を`git commit -F "%TEMP_MSG%"`に置き換え、複数行メッセージに対応した。
4. コミット失敗時（`errorlevel`が0以外）は、既存の`:commiterror`ラベルへ分岐する前に一時ファイル
   2つを`del ... >nul 2>&1`で削除してから遷移するようにした（エラー時に一時ファイルが残置されない
   ようにするため）。
5. コミット成功時も処理完了後に一時ファイル2つを削除する。

`git add -A`より後・`git commit`より前に`git diff --cached --name-only`を実行する順序としたため、
実際にステージされた変更ファイルのみが一覧に反映される。

### 既存コードとの整合性確認
- 一時ファイル名は`%TEMP%\sync_local_edits_files_%RANDOM%.txt` / `%TEMP%\sync_local_edits_msg_%RANDOM%.txt`
  とし、`%RANDOM%`によって他のバッチ実行・複数回実行との衝突を避けている。
- `echo`による状況表示（`Building commit message with changed file list...` /
  `Committing changes...`）は既存の`echo`パターンを踏襲。
- `if not %errorlevel%==0 goto commiterror`という既存の失敗時分岐パターンは維持しつつ、
  一時ファイル削除処理を追加するため、この箇所のみ`if not %errorlevel%==0 ( ... )`ブロック形式に
  変更した（他の`goto`分岐箇所の形式には手を加えていない）。
- ASCII文字のみ・CRLF改行を維持（下記自動テスト実行結果参照）。

### コミットメッセージの実際の出力例（イメージ）
```
Local edits synced via sync_local_edits.bat (Thu 09/17/2026 21:30:00.00)

Changed files:
- sync_local_edits.bat
```

### 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
本バッチファイルはWindows専用スクリプトであり、Linux環境の本セッションでは実行による動作確認は
できない。以下の静的確認のみ実施した。
- `file sync_local_edits.bat` → `DOS batch file, ASCII text, with CRLF line terminators`
- Python簡易スクリプトによるバイト単位確認: 非ASCIIバイト0件、全行がCRLFで終端（最終行除く）
  であることを確認。

### スコープ外変更の有無
なし。`sync_local_edits.bat`のみを修正。`src/`配下・`docs/`・他のバッチファイル
（`sync_test.bat`/`sync_main.bat`）には一切手を加えていない。
