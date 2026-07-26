# 命名規約ガイドライン

本プロジェクトの開発において採用されている、各言語（Python、JavaScript、CSS）およびAWS IaCリソースの命名規約ガイドラインです。

---

## 1. Python 命名規約 (PEP 8 準拠)

Pythonコード（バックエンドLambda関数、エッジ側スクリプト）は、標準スタイルガイドである [PEP 8](https://peps.python.org/pep-0008/) に準拠します。

| 対象 | 規約 | 例 | 備考 |
| :--- | :--- | :--- | :--- |
| **ファイル名 / モジュール名** | `snake_case` (小文字) | `ir_control.py`<br>`shadow_agent.py` | 簡潔でわかりやすい名詞または動詞。 |
| **パッケージ / ディレクトリ名** | `snake_case` (小文字) | `get_appliance_state` | 原則アンダースコアは使わず小文字のみが推奨されますが、可読性のために必要な場合は許容します。 |
| **関数名 / メソッド名** | `snake_case` (小文字) | `transmit_code(key)` | アクションを示す動詞から始める。 |
| **変数名** | `snake_case` (小文字) | `clean_pulses` | 役割が明確な名詞。 |
| **定数名** | `UPPER_SNAKE_CASE` (大文字) | `IOT_DATA_ENDPOINT`<br>`VALID_POWERS` | モジュールレベルで定義され、再代入を行わない値。 |
| **プライベート変数 / 関数** | `_` から始まる `snake_case` | `_response(status, body)` | モジュール内でのみ使用されるヘルパー関数など。 |
| **未使用引数** | `_` から始まる変数名 | `_context` | 外部I/Fの制約等で定義は必要だが、内部で参照しない変数。 |

---

## 2. JavaScript 命名規約

フロントエンドの制御コード（`frontend/app.js`）は、JavaScriptで標準的なキャメルケースをベースとします。

| 対象 | 規約 | 例 | 備考 |
| :--- | :--- | :--- | :--- |
| **ファイル名** | `kebab-case` (小文字) | `app.js`<br>`config.js` | すべて小文字で区切り記号にはハイフンを使用。 |
| **変数名 (let / const)** | `camelCase` | `currentState`<br>`ac` | 名詞で定義。DOM要素には要素がわかる記述を含めることが望ましい。 |
| **関数名** | `camelCase` | `renderState()` | アクションを表す動詞。 |
| **定数名** | `UPPER_SNAKE_CASE` | `API_BASE_URL`<br>`API_KEY` | グローバルスコープ、または設定値として固定のもの。 |
| **DOM要素参照変数** | `camelCase` | `cardAircon`<br>`tempValue` | `getElementById`等で取得した要素。HTMLのIDやクラス名と連動。 |

---

## 3. CSS 命名規約 (BEM 規約)

スタイリングファイル（`frontend/style.css`）のクラス設計には、保守性と再利用性を高めるために **BEM (Block, Element, Modifier)** 規約を採用します。

| 対象 | 規約 | 例 | 備考 |
| :--- | :--- | :--- | :--- |
| **Block (ブロック)** | `kebab-case` (小文字) | `.card`<br>`.temp-btn` | スタンドアロンで意味を持つ独立したコンポーネント。 |
| **Element (要素)** | `Block__Element` | `.card__header`<br>`.card__glow` | Blockのパーツであり、単体では意味を持たない要素（アンダースコア2つで連結）。 |
| **Modifier (修飾子)** | `Block--Modifier`<br>`Element--Modifier` | `.card--aircon`<br>`.temp-btn--up` | BlockやElementの外観、状態、挙動を定義（ハイフン2つで連結）。 |
| **CSSカスタム変数** | `--` から始まる `kebab-case` | `--bg-dark`<br>`--color-cool-glow` | `:root` 等でグローバル定義するデザイン設計トークン。 |

---

## 4. AWS / IaC リソース命名規約

Terraform および AWS SAM (CloudFormation) でプロビジョニングする AWS リソースの命名ルールです。

| リソース種類 | 規約 | 例 | 備考 |
| :--- | :--- | :--- | :--- |
| **AWS IoT Thing** | `kebab-case` | `led-device-01` | デバイス名。環境名や番号を付与。 |
| **Lambda関数名** | `kebab-case` | `led-iot-get-appliance-state` | `[Project]-[Env]-[Function]` の形式。 |
| **API Gateway (ステージ)** | `camelCase` / 小文字単語 | `dev`, `prod` | デプロイ環境の識別子。 |
| **API エンドポイントパス** | 名詞・複数形・小文字 | `/appliances/state` | RESTful APIの原則に従う。 |
| **Terraform リソース名** | `snake_case` (小文字) | `resource "aws_iot_thing" "led_device"` | IaC内のコードレベルの論理名。 |
