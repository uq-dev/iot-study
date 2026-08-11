# Raspberry Pi Zero W セットアップと赤外線送信回路（TX）

## 📌 前提条件
- 本リポジトリは **Raspberry Pi 4** 用に作成されていますが、**Zero W** でもほぼ同じ手順で動作します。
- GPIO ピン配置はモデル間で互換性があります（BCM 番号ベース）。
- Zero W はサイズが小さく、HDMI がなく、Micro‑USB（USB‑OTG）と **micro‑USB** 経由で電源供給します。これらの点だけ注意してください。

---

## 🛠️ 1️⃣ Raspberry Pi Zero W のセットアップ手順
| 手順 | コマンド / 操作 | 説明 |
|------|----------------|------|
| **a. OS イメージ** | Raspberry Pi Imager で *Raspberry Pi OS Lite (64‑bit)* を micro‑SD に書き込む | GUI が無い最小構成です。 |
| **b. SSH & Wi‑Fi** | 書き込み後、`boot` パーティションをマウントし、空ファイル `ssh` を作成。<br>`wpa_supplicant.conf` を作成して Wi‑Fi 情報を書き込む。 | ヘッドレスで起動できます。 |
| **c. 初回起動** | `sudo apt update && sudo apt -y upgrade` | パッケージを最新にします。 |
| **d. 必要パッケージ** | `sudo apt install -y python3 python3-pip python3-venv git pigpio` | Python 環境と `pigpio` デーモン。 |
| **e. pigpio デーモン** | `sudo systemctl enable pigpiod && sudo systemctl start pigpiod` | 0 V から 3.3 V の GPIO を PWM で制御可能にします。 |
| **f. 電源** | 5 V / ≥1 A の安定電源（USB‑C/マイクロ USB）を使用。Zero W は **電流余裕が少ない** ので、外部電源（UPS/HAT）で LED ドライブ回路を供給すると安全です。 |
| **g. ディレクトリ配置** | `~/led_iot_edge/` に本リポジトリの `shadow_agent.py` と `irrp.py` を配置し、仮想環境を作成して `awsiotsdk` をインストール。 | 後述の手順参照。 |

---

## 📡 2️⃣ 赤外線送信（TX）回路の概要
以下は **NPNトランジスタ（例: 2N2222）** を使った **ローサイドスイッチ** 回路です。GPIO 17（BCM 番号）でベースを駆動し、LED のカソードを **トランジスタのコレクタ** に接続します。

```mermaid
flowchart LR
    VCC[+5 V] -->|限流抵抗 (220Ω)| LED[IR LED]
    LED -->|カソード| C[Collector]
    C -->|接続| GND[Ground]
    subgraph Transistor
        B[Base] -. 1kΩ .- GPIO17
        C
        E[Emitter] --> GND
    end
    GPIO17 -->|1kΩ| B
```

### 部品一覧
- **GPIO 17**（BCM 番号） → **1 kΩ** → **ベース**
- **NPNトランジスタ**（例: 2N2222, BC547）
  - **エミッタ** → **GND**
  - **コレクタ** → **IR LED のカソード**（LED のアノードは +5 V へ直結）
- **IR LED**（38 kHz 用）
- **限流抵抗**（約 220 Ω、LED の電流に合わせて調整）
- **外部電源**（5 V、Zero W の 3.3 V では電流が足りません）

### キーポイント
- **コレクタは GPIO ではなく LED のカソードに接続**します。トランジスタはスイッチとして機能し、GPIO がハイになるとベース電流が流れ、コレクタ‑エミッタ間が導通して LED が点灯します。
- **GPIO 17 は 3.3 V 出力**です。ベースに流す電流は 1 kΩ で約 3 mA 程度に抑えると安全です。
- **Zero W の GPIO ピンは 3.3 V しか出せません**が、トランジスタがスイッチングを行うため、LED へは外部 5 V 電源を使用しても問題ありません。
- **pigpio** を用いて `irrp.py` が 38kHz キャリアを生成し、送信を行います。

---

## 📦 3️⃣ 実装コードの簡易説明
エッジ側では pigpio 公式の `irrp.py` を利用して赤外線信号の学習および送信を行います。
詳細は公式ドキュメントを参照してください:
- https://abyz.me.uk/rpi/pigpio/index.html
- https://abyz.me.uk/rpi/pigpio/examples.html#Python%20code

### 赤外線の学習（記録）例
```bash
python3 irrp.py -r -g18 -f codes.json light:on --no-confirm --post 130
```
- `-r`: 記録モード
- `-g18`: 受信ピン (GPIO 18 / 実際の配線に合わせて変更)
- `-f codes.json`: 記録先のファイル
- `light:on`: 記録するキー名
- `--no-confirm`: 確認の手間を省く
- `--post 130`: 記録後の遅延（ミリ秒）

### 赤外線の送信（実行）例
```bash
python3 irrp.py -p -g22 -f codes.json light:on
```
- `-p`: 再生モード
- `-g22`: 送信ピン (GPIO 22 / 実際の配線に合わせて変更)
- `-f codes.json`: 読み込むファイル
- `light:on`: 再生するキー名

- **`shadow_agent.py`**: AWS IoT デバイスシャドウから `delta` メッセージを受信し、内部から `irrp.py` の送信コマンドを実行する等して上記回路に指示を送ります。

> **Zero W での注意点**: `pigpio` を使ったソフトウェア PWM や波形生成は電源が不安定だと波形が歪むことがあるので、外部 5 V 電源と十分なデカップリング（100 µF コンデンサ）を推奨します。

---

## ✅ まとめ
- **Zero W でも同じ GPIO 配線**で動作しますが、電源供給方式が異なる点に留意してください。
- **トランジスタのコレクタは LED カソード**に接続し、GPIO 17 はベース側に 1 kΩ 抵抗で接続します。
- `pigpio` デーモンが正しく動作していれば、`shadow_agent.py` → `irrp.py` → ハードウェア の流れで赤外線送信が可能です。

質問や配線図の画像が必要であれば、遠慮なくお知らせください！
