## タスクID
T-0013（バグ修正、T-0012後も残るタイミング競合対応）

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`

## 変更概要
`_on_confirm_image_clicked()` のリネーム分岐内、本体ファイルおよびワールドファイルの `os.rename()` 呼び出し
2箇所を、リトライ機能付きの新設ヘルパー関数 `_rename_with_retry()` 経由の呼び出しに置き換えた。

具体的な変更点:
1. `import time` を追加した（`os`/`re`/`math`/`gc` に続く形で追加。`QCoreApplication` は既に
   `qgis.PyQt.QtCore` からインポート済みであることを確認し、そのまま利用した）。
2. `_release_raster_layer_for_rename()` の直前に、新設メソッド `_rename_with_retry(self, src: str, dst: str,
   max_attempts: int = 5, delay_sec: float = 0.2) -> None` を追加した。
   - `os.rename(src, dst)` を試行し、成功すればそのまま return する。
   - `PermissionError` または `OSError`（Windows の `[WinError 32]` はこのいずれかとして送出される）を
     捕捉した場合、最後の試行でなければ `QCoreApplication.processEvents()` を呼んだ後 `time.sleep(delay_sec)`
     で待機し、再試行する（`max_attempts` 回まで、待機時間は固定・指数バックオフ等は行わない）。
   - `max_attempts` 回すべて失敗した場合、最後に捕捉した例外を `raise last_error` で再送出する。呼び出し元
     （`_on_confirm_image_clicked()` の既存 `except Exception as e:` ブロック）が変更なしにそのままエラー
     ダイアログ表示・ロールバック処理を行える形にした。
   - docstring に、統括の再調査に基づく「タイミング競合（レースコンディション）」仮説の要旨、およびこの
     リトライが根本原因の解消ではなく「タイミングのズレを吸収する対症療法」である旨を `NOTE (T-0013):`
     として明記した。
3. `_on_confirm_image_clicked()` 内の2箇所の呼び出しを置き換えた:
   - 本体ファイル: `os.rename(old_path, new_path)` → `self._rename_with_retry(old_path, new_path)`
   - ワールドファイル: `os.rename(base + w_ext, new_base + w_ext)` →
     `self._rename_with_retry(base + w_ext, new_base + w_ext)`
   - いずれも既存の `try`/`except Exception as e:` ブロックの内側にそのまま残しており、リトライ全滅時の
     ロールバック処理（`_reload_raster_layer_after_rename()` による復元、エラーダイアログ表示）の呼び出し
     経路・条件分岐は変更していない。

T-0010〜T-0012で実装済みの以下のロジックは維持し、変更していない（`os.rename()` の呼び出し方法のみを
リトライ対応に変更した）:
- `_release_raster_layer_for_rename()` のレイヤ一致判定（レイヤ表示名 `layer.name() == old_name` ベース、
  T-0012で確定した方式）
- 同関数内のスタイル/グループ/位置/表示状態の保持ロジック、`self.layer_manager.raster_layer` のクリア、
  `QCoreApplication.processEvents()` + `gc.collect()` による防御的対応、`PreviewDialog.raster_layer` の
  解放（`clean_up()`）判定
- `_reload_raster_layer_after_rename()` によるレイヤ再作成・スタイル/グループ/位置/表示状態の復元
- リネーム失敗時のロールバック処理（`_on_confirm_image_clicked()` の `except Exception as e:` ブロック、
  `released_info` を用いた復元パス/レイヤ名の判定ロジック）

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
代わりに以下の静的確認を実施した:
- `python3 -m py_compile src/tab1_georef_mixin.py`: 構文エラーなし。
- `python3 -m pyflakes src/tab1_georef_mixin.py`: 本変更箇所に起因する新規の警告なし。既存の警告1件
  （294行目付近 `f-string is missing placeholders`。本変更とは無関係の既存コードであり、T-0012実装ログにも
  同様の記載がある）のみ検出された。

## スコープ外変更の有無
なし。`src/tab1_georef_mixin.py` 内の、新設メソッド `_rename_with_retry()` の追加、`import time` の追加、
および `_on_confirm_image_clicked()` 内の `os.rename()` 呼び出し2箇所の置き換えのみを行っており、それ以外の
ファイル・関数（`_release_raster_layer_for_rename()`・`_reload_raster_layer_after_rename()` の内部ロジックを
含む）には手を入れていない。

## 付記（重要）
本タスクは統括の再調査に基づく仮説（「レイヤ解放処理〈`removeMapLayer()` + `processEvents()` +
`gc.collect()`〉自体は実行されているが、Windows OS側で実際にファイルハンドルが解放されるまでにタイムラグが
あり、直後の `os.rename()` 時点ではまだ解放が完了していないタイミング競合」）への対応である。
実際にWindows実機で `[WinError 32]` の再現有無が変化するかどうかは、実装エージェント（本セッション）には
確認する手段がなく、本ログでも「解消した」等の断定は行わない。

また、本リトライ対応はあくまで「タイミングのズレを短い待機とリトライで吸収する」対症療法的な性質のもので
あり、根本原因（OS側のファイルハンドル解放タイミングそのもの）を完全に取り除くものではない。もし
「OS側の解放が `max_attempts`（5回）× `delay_sec`（0.2秒、合計最大約1秒程度）よりも長くかかる」ような
環境・状況が存在する場合は、依然として `[WinError 32]` が再現しうる。
