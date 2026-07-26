# セルフレビュー報告書

本ドキュメントは、エアコンおよびシーリングライトのスマートホーム遠隔操作システムにおけるプログラムソースコードのセルフレビュー結果をまとめたものです。

---

## 1. レビュー実施概要

- **実施日**: 2026年7月19日
- **対象コード**:
  - **Python**: 
    - バックエンドLambda: `get_appliance_state/handler.py`, `set_appliance_state/handler.py`
    - エッジ側スクリプト: `edge/ir_control.py`, `edge/shadow_agent.py`
  - **JavaScript**:
    - フロントエンド: `frontend/app.js`
- **レビュー観点**:
  1. セキュリティ情報（APIキー、認証情報、パスワード等）がハードコードされていないか
  2. ゴースト変数（未使用の変数や定数）が定義されていないか
  3. 各言語の標準的な命名規約（Python: PEP 8, JS: CamelCase）が守られているか

---

## 2. 言語ごとのレビュー結果

### 2.1 Python
バックエンドおよびエッジデバイス用スクリプトを対象に検証しました。

| レビュー項目 | 判定 | 状況・乖離内容と対応 |
| :--- | :---: | :--- |
| **セキュリティ情報の埋め込み** | **適合** | AWS IoT エンドポイント、認証情報、デバイス名等はすべて環境変数 (`os.environ`) から取得しており、コード内のハードコードはありません。 |
| **ゴースト変数の定義** | **適合 (修正済)** | **[乖離と修正]**<br>- `edge/shadow_agent.py` 内で、MQTTサブスクライブの戻り値 `packet_id` が定義されていましたが、使用されていませんでした。これをアンダースコア `_` に変更し、未使用変数としてクリーンアップしました。<br>- Lambdaハンドラーの引数 `context` はシグネチャ上必須ですが、内部で未使用だったため `_context` に改名し、静的解析警告を抑止しました。 |
| **命名規約 (PEP 8)** | **適合** | - 変数名、関数名はすべて `snake_case`。<br>- 定数はすべて大文字の `UPPER_SNAKE_CASE` (例: `IOT_DATA_ENDPOINT`, `VALID_POWERS`)。<br>- PEP 8の規約に準拠しています。 |

### 2.2 JavaScript
フロントエンド操作ロジック (`frontend/app.js`) を対象に検証しました。

| レビュー項目 | 判定 | 状況・乖離内容と対応 |
| :--- | :---: | :--- |
| **セキュリティ情報の埋め込み** | **適合** | API接続情報（URL、APIキー）は外部の `config.js`（git無視対象）から動的オブジェクト `window.LED_IOT_CONFIG` を経由して取得しており、埋め込みはありません。 |
| **ゴースト変数の定義** | **適合** | DOM要素、状態キャッシュ変数、ユーティリティ関数など、定義されているすべての変数・関数が処理の中で適切に使用されています。 |
| **命名規約** | **適合** | - 変数・関数名はすべて `camelCase` (例: `cardAircon`, `renderState`)。<br>- 外部接続パラメータなどの定数は `UPPER_SNAKE_CASE` (例: `API_BASE_URL`)。<br>- JavaScriptにおける一般的な命名規則に従っています。 |

---

## 3. 乖離修正のまとめ

セルフレビューで検出された軽微なゴースト変数の乖離について、以下の修正を適用しました。すべての修正適用後、ユニットテストが正常にパスすることを確認しています。

### 3.1 `edge/shadow_agent.py`
- **修正前**: `subscribe_future, packet_id = mqtt_connection.subscribe(...)`
- **修正後**: `subscribe_future, _ = mqtt_connection.subscribe(...)`

### 3.2 `backend/lambda/get_appliance_state/handler.py`
- **修正前**: `def handler(event, context):`
- **修正後**: `def handler(event, _context):`

### 3.3 `backend/lambda/set_appliance_state/handler.py`
- **修正前**: `def handler(event, context):`
- **修正后**: `def handler(event, _context):`
