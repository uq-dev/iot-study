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
| **g. ディレクトリ配置** | `~/led_iot_edge/` に本リポジトリの `shadow_agent.py` と `ir_control.py` を配置し、仮想環境を作成して `awsiotsdk` をインストール。 | 後述の手順参照。 |

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
- **pigpio** の PWM 周波数は `38000` Hz（38 kHz）に設定し、`set_PWM_dutycycle` で約 33 % のデューティ比を使用します（実装は `ir_control.py` 参照）。

---

## 📦 3️⃣ 実装コードの簡易説明
- **`ir_control.py`**: `pigpio` を利用して NEC 形式の赤外線パルスを生成し、`transmit_raw(pulses)` が実際に GPIO 17 へ波形を書き込みます。
- **`shadow_agent.py`**: AWS IoT デバイスシャドウから `delta` メッセージを受信し、`transmit_ir(payload)` を呼び出して上記回路に指示を送ります。

> **Zero W での注意点**: `pigpio` はデフォルトで `GPIO` の **PWM 周波数** が 800 Hz ですが、`pi.set_PWM_frequency(IR_GPIO, 38000)` により 38 kHz に上書きします。Zero W のハードウェアはこの周波数に対応していますが、**電源が不安定だと波形が歪む**ことがあるので、外部 5 V 電源と十分なデカップリング（100 µF コンデンサ）を推奨します。

---

## ✅ まとめ
- **Zero W でも同じ GPIO 配線**で動作しますが、電源供給方式が異なる点に留意してください。
- **トランジスタのコレクタは LED カソード**に接続し、GPIO 17 はベース側に 1 kΩ 抵抗で接続します。
- `pigpio` デーモンと 38 kHz PWM 設定が正しく行われていれば、`shadow_agent.py` → `ir_control.py` → ハードウェア の流れで赤外線送信が可能です。

質問や配線図の画像が必要であれば、遠慮なくお知らせください！
