# mcAI
## 説明
Minecraftという仮想世界の中でAIを野放しにして、人の手を一切加えずに学習させたらどうなるのだろうというコンセプトの元で作成した個人的なプロジェクトです。

現状成果はありませんが、管理のこともありソースコードを公開することにしました。

## インストール方法
### 1. 用意するもの
- 以下の種類をそれぞれ実行できるLinuxサーバー（できればUbuntu・最低4台）
  - 中央サーバー（推奨メモリ: 1GB）`central`
  - AI実行サーバー（推奨メモリ: 6GB）`client`
  - AI学習サーバー（推奨メモリ: 2GB）`learn`
  - Minecraftサーバー（推奨メモリ: 4GB）`server`

`最低でも4台必要となるため、VMでの実行をおすすめします。`
`AI実行サーバーは複数台での実行ができます。その他は1台のみです。`

### 2. インストール手順
 1. クリーンインストールされたLinuxサーバーを必要台数分用意してください。
 2. それぞれのサーバーで以下のインストール用コマンドを実行してください。
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/takpika/mcAI/main/setup.sh)" -t <YOUR_SERVER_TYPE> -i <NIC_INTERFACE> -p <IP_ADDRESS/MASK>
```
  - **必要に応じてコマンドの一部を書き換えてください。**
| 書き換える部分 | 説明 | 入力例 |
| ---- | ---- | ---- |
| <YOUR_SERVER_TYPE> | サーバーの種類 | {`central`, `client`, `learn`, `server`} |
| <NIC_INTERFACE> | サーバー間での通信用NIC | `eth0` |
| <IP_ADDRESS/MASK> | サーバーに割り当てる固定IPとネットマスク | `192.168.1.10/24` |
  - AI実行サーバー(`client`)は複数台用意できるため、番号を割り振ることができます。割り振るにはコマンドに`--number <割り振りたい番号>`を追記してください。
  - インストールするとホスト名が上記の英語名に変更されます。干渉しないようにご注意ください。AI実行サーバーは`client00`のような名前になります。

## その他
コードを書く前に書いたメモなども同梱しました。適当に色々と書いただけですので、今の仕様と違っている部分とかもあったりします。
[メモ](description/description.txt) | [図形](description/diagram.drawio.svg) | [MODのソースコード](https://github.com/takpika/mcAIj)