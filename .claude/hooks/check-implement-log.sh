#!/usr/bin/env bash
# SubagentStop hook: implementerの実装ログを静的にチェックする。
# 1. .claude/logs/implement/ 配下にログが存在し、自動テスト結果が記載されているか
# 2. ログ内に実行時の挙動を断定する表現（越権記述）が含まれていないか
#
# stdinからフックイベントのJSONを受け取るが、内容は使わずファイルシステムのみを見る
# （どのサブエージェントが停止したかを厳密に判別できないため、実装ログが存在する場合のみチェックする）。
cat >/dev/null 2>&1 || true

LOG_DIR=".claude/logs/implement"

if [ ! -d "$LOG_DIR" ]; then
  # implementerがまだ一度も実行されていない場合は何もしない
  exit 0
fi

# checklistファイルを除いた実装ログの中で最新のものを対象にする
LATEST_LOG=$(ls -t "$LOG_DIR"/*.md 2>/dev/null | grep -v -- '-checklist\.md$' | head -n 1)

if [ -z "$LATEST_LOG" ]; then
  echo "[check-implement-log] 警告: $LOG_DIR 配下に実装ログ(.md)が見つかりません。implementerは完了時に必ずログを作成してください。" >&2
  exit 0
fi

WARN=0

# 1. 自動テスト結果の記載有無チェック
if ! grep -q "自動テスト" "$LATEST_LOG"; then
  echo "[check-implement-log] 警告: $LATEST_LOG に自動テスト実行結果の記載が見つかりません（『自動テストなし』の明記も含む）。" >&2
  WARN=1
fi

# 2. 動作を断定する越権記述のチェック
BANNED_PATTERNS='動作確認済み|正常に動作|問題なく動作|動作OK|動作した|動いた'
HIT=$(grep -nE "$BANNED_PATTERNS" "$LATEST_LOG" 2>/dev/null)
if [ -n "$HIT" ]; then
  echo "[check-implement-log] 越権記述の警告: $LATEST_LOG に実行時の挙動を断定する表現が含まれています。verifierによる差し戻し対象です。" >&2
  echo "$HIT" >&2
  WARN=1
fi

# 対応する人手確認チェックリストの存在チェック（実行環境依存の確認項目が「有り」の構成のため）
CHECKLIST="${LATEST_LOG%.md}-checklist.md"
if [ ! -f "$CHECKLIST" ]; then
  echo "[check-implement-log] 警告: 対応する人手確認チェックリスト ($CHECKLIST) が見つかりません。" >&2
  WARN=1
fi

exit 0
