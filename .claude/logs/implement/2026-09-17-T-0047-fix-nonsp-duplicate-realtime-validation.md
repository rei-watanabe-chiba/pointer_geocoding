## タスクID
T-0047（追加修正: 非SP属性のリアルタイム重複チェック未実装の是正 + デバッグログ除去）

## 変更ファイル一覧
- `src/ui/dialogs.py`

## 変更概要

### 判明した真因
コミット`82c48a8`で仕込んだデバッグログ（`QgsMessageLog`）による実機切り分けの結果、
リアルタイムバリデーションが非SP属性（S/P/C）で動作しない不具合は、シグナル配線
（textChanged/textEdited）の不具合ではなく、**そもそも非SP属性の重複チェック
（`DuplicateValidator`）がリアルタイム接続の実装スコープに含まれていなかった**ことが
原因と判明した。

- `PointNameEntryDialog.__init__`では、`self._is_sp_attribute`が真の場合のみ
  `edit_point_name_sp.textChanged`/`textEdited`を`_on_realtime_validate`に接続しており、
  非SP属性の`spin_point_name`(QSpinBox)・`edit_branch_no`は一切接続されていなかった。
- 加えて、`_on_realtime_validate`自体もSP専用の`RequiredValidator`（必須チェック）しか
  実行しておらず、SP/非SP共通で必要な`DuplicateValidator`（点名+枝番の重複チェック）は
  `_on_ok_clicked`（確定時）のみで実行される設計だった。
- 非SP属性は「QSpinBoxは常に有効な整数を持つため必須チェック不要」という理由で
  リアルタイム接続自体が見送られていたが、重複チェックの必要性が見落とされていた。

### 修正内容（`src/ui/dialogs.py`、`PointNameEntryDialog`）
1. **重複チェックの共通化**: `_on_ok_clicked`内にあった`build_point_ident`+
   `DuplicateValidator`のロジックを`_check_duplicate(point_name, branch_no)`という
   private methodに切り出した。`_on_realtime_validate`/`_on_ok_clicked`の両方から呼ぶ。
2. **`_on_realtime_validate`の拡張**: SP属性時の`RequiredValidator`チェックに加えて、
   SP/非SPどちらでも`_check_duplicate`を実行し、結果をステータスパネルに反映するように
   変更。いずれかの検証が失敗した時点で`btn_ok`を無効化する。
3. **シグナル接続の追加**（`__init__`）:
   - 非SP属性: `spin_point_name.valueChanged`を`_on_realtime_validate`に新規接続。
   - SP/非SP共通: `edit_branch_no.textChanged`を`_on_realtime_validate`に新規接続
     （枝番はSPでも非SPでも共通して重複チェックに使われるため）。
   - SP属性の`edit_point_name_sp.textChanged`/`textEdited`の既存接続はそのまま維持
     （コミット`2986548`のtextEdited併用接続は、副作用がないため残した。実際の原因は
     この接続自体ではなく非SP側の実装スコープの見落としだったため、SP側の対称性を
     崩す理由がないと判断）。
   - 枝番(`edit_branch_no`)については新規追加であり、原因がシグナル発火不良でないと
     判明したこともあり、`textChanged`単独接続とした（`textEdited`との併用はしていない）。
4. **`_on_ok_clicked`の簡素化**: `_check_duplicate`を呼び出す形に置き換え、
   `build_point_ident`/`DuplicateValidator`の重複コードを除去した。ロジック自体は
   従来の確定時チェックと等価（必須チェック→重複チェックの順）。
5. **クラスdocstringの更新**: 「重複チェックはOK-click時のみ」という誤った設計方針の
   記述を撤回し、SP/非SP共通でリアルタイム実行される旨に更新。

### パフォーマンスに関する懸念
`_check_duplicate`は`core_logic.check_point_duplicate`経由で`self._point_layer`への
問い合わせ（属性フィルタでの走査）を伴うため、キー入力/スピンボックス変更のたびに
実行されることになる。既存のSP属性側の実装（必須チェックのみ）と異なり、非SP属性でも
毎回レイヤ問い合わせが発生する点は、レイヤの点数が非常に多い場合に体感遅延が出る可能性が
ゼロではない。ただし、依頼元の指示により「リアルタイム表示」を優先する方針が明示された
こと、また`check_point_duplicate`は単純な属性フィルタでの探索であり通常の点群図面規模
（数百～数千点程度）では問題にならないと考えられることから、今回はデバウンス等の追加対策は
実施していない。実機で顕著な遅延が確認された場合は、別タスクでのデバウンス実装
（例: `QTimer.singleShot`によるまとめ実行）を検討されたい。

### デバッグログの除去（コミット`82c48a8`分）
`.claude/logs/implement/2026-09-17-T-0047-debug-realtime-validate-logging.md`の除去手順に
従い、以下を除去した。
1. `from qgis.core import QgsRasterLayer, Qgis, QgsMessageLog  # DEBUG T-0047 temp import ...`
   を`from qgis.core import QgsRasterLayer`に戻した。
2. `FeatureCreateDialog._on_realtime_validate`冒頭の`QgsMessageLog.logMessage(...)`行を削除。
3. `PointNameEntryDialog._on_realtime_validate`冒頭の`QgsMessageLog.logMessage(...)`行を削除
   （このメソッドは今回のロジック変更でも書き換えられているため、除去は書き換えの一部として
   実施済み）。
4. `python3 -m py_compile src/ui/dialogs.py`で構文確認、`Qgis`/`QgsMessageLog`/`DEBUG T-0047`
   の残存がないことをgrepで確認済み。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
`python3 -m py_compile src/ui/dialogs.py`による構文確認を実施し、エラーなし。
`grep -n "DEBUG T-0047\|QgsMessageLog\|Qgis\." src/ui/dialogs.py`で残存なしを確認。

## スコープ外変更の有無
なし。変更は`src/ui/dialogs.py`の`PointNameEntryDialog`（および前回デバッグ用に触れた
`FeatureCreateDialog._on_realtime_validate`のデバッグ行削除）のみ。他ファイルへの変更なし。
