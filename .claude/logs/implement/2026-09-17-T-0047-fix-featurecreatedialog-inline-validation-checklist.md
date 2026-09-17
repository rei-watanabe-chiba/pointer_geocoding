## 人手確認チェックリスト

### 確認手順
1. QGIS上でプラグインを起動し、タブ2（デジタイジング）で新規モードを選択、対象図面・
   出土形態（遺構）を設定した状態で、属性パネルの「作成」ボタンを押し
   `FeatureCreateDialog`（遺構名入力ダイアログ）を表示させる。
2. 遺構名の入力欄を空欄のまま何も入力しない状態で、入力欄の下にインラインで
   エラーメッセージ（赤系のステータスパネル、`UIMessages.ERR_NEW_FEATURE_REQUIRED`）が
   表示されることを確認する。このとき、確定（OK）ボタンが無効化されていることも確認する。
3. 入力欄に文字を入力すると、リアルタイムでエラー表示が消え（ステータスパネルがinfo表示に
   戻る）、確定ボタンが有効化されることを確認する。
4. 入力欄に文字を入力した状態で確定（OK）ボタンを押す。この際、従来のような
   ポップアップ（QMessageBoxの警告ダイアログ）が表示されないことを確認する。
5. ダイアログが正常に閉じ（accept）、続けて色選択などT-0027以降の既存フローに
   問題なく遷移することを確認する。
6. いったん文字を入力してから全て削除して空欄に戻し、再度インラインエラーが表示され
   確定ボタンが無効化されることを確認する（リアルタイム性の往復確認）。

### 各手順で期待される挙動（設計書ベース）
- 本タスクの依頼文（統括からの指示）に明記された「T-0047で変更したQMessageBox方式から、
  インライン赤字ラベル(またはステータスパネル)方式に戻す」という要件に基づく。
- 参照実装として指定された`PointNameEntryDialog`のT-0047追加修正
  （コミット`40205e6`、`.claude/logs/implement/2026-09-17-T-0047-fix-autonum-and-inline-validation.md`）
  と同一の`UIStyleHelper.create_status_panel`/`update_status_panel`パターン
  （`src/ui/style.py`435-496行、`GridInputDialog`のTier4ステータス・エラー表示パネルと同型）を
  踏襲している。
- T-0027時点の設計（`FeatureCreateDialog`は「作成」ボタン押下で開くモーダルダイアログとして
  遺構名を入力させ、OKで`Tab2DigitizingMixin._on_create_feature_clicked`へ値を返す）自体は
  変更しておらず、バリデーションのUI表現のみをインライン方式に戻したものである。

### 注意喚起
- 本ダイアログは項目数が1つ（遺構名のみ）と単純なため、`PointNameEntryDialog`とは異なり
  `DuplicateValidator`（重複チェック）に相当する処理は持たない。実際の重複チェック・登録は
  呼び出し元の`Tab2DigitizingMixin._on_create_feature_clicked`/`register_new_feature_name()`側で
  行われる想定であり、本ダイアログ内では「非空」の必須チェックのみを検証している
  （この責務分担自体はT-0027時点から変更していない）。
- `edit_name.textChanged`→`_on_realtime_validate`のシグナル接続は、ダイアログのライフサイクル内
  で閉じるため明示的なdisconnectは行っていない（`PointNameEntryDialog`と同じ方針、ダイアログ
  破棄時にQtが自動的にクリーンアップする一般的なパターン）。
- 本修正はT-0047の一部としてまだverifierによる静的検証未実施の状態（`.claude/state/tasks.md`は
  「静的検証中」のまま）である。他のT-0047関連の人手確認項目（`2026-09-17-T-0047-coreui-dialogs-checklist.md`、
  `2026-09-17-T-0047-fix-autonum-and-inline-validation-checklist.md`）と合わせて確認することを推奨する。
