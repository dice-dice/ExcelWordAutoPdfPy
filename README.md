# Excel/Word 自動PDF化アプリ (Python版)

Excel/WordファイルをLibreOffice経由で定期的にPDF化する、クロスプラットフォーム(Windows/Mac/Linux)対応の常駐アプリです。
指定したファイルの更新日時をチェックし、前回変換時から変わっていれば自動でPDF化します。

## 動作環境

- Python 3.9以降(標準搭載のTkinterのみ使用。追加ライブラリ不要)
- [LibreOffice](https://ja.libreoffice.org/download/libreoffice/) がインストールされていること(PDF変換に使用)

## 使い方

### そのまま実行する場合

```bash
cd ExcelWordAutoPdfPy
python3 app.py
```

### 実行ファイル(exe/アプリ)化したい場合

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name ExcelWordAutoPdf app.py
```

生成された実行ファイル(`dist/ExcelWordAutoPdf` または `dist/ExcelWordAutoPdf.exe`)を、
PDF化したいExcel/Wordファイルと同じフォルダにコピーして使います。
**PyInstallerはビルドを実行したOS向けの実行ファイルしか作れません**(Windows用exeが欲しい場合はWindows機でビルドしてください)。

### 起動後の操作

1. アプリを起動すると、実行フォルダに設定ファイル `config.json` が作成されます。
2. 初回起動時、LibreOffice(soffice)を自動検出します。見つからない場合は
   「ファイル」→「LibreOfficeの設定...」から手動でパスを指定してください。
   - Mac: `/Applications/LibreOffice.app/Contents/MacOS/soffice`
   - Windows: `C:\Program Files\LibreOffice\program\soffice.exe`
3. 「ジョブ追加」ボタンで変換対象を登録します。
   - **変換対象ファイル**: PDF化したいExcel/Wordファイル。アプリと同じフォルダに置く場合はファイル名だけでもOKです。
   - **出力方法**:
     - 「同名で上書き」: 元ファイルと同じ名前・同じフォルダ(または指定した出力先フォルダ)にPDFを出力し、既存PDFを上書きします。
     - 「別名で保存」: 指定したファイル名でPDFを出力します。
   - **出力先フォルダ**: 空欄なら変換対象ファイルと同じフォルダに出力します。別の場所に出力したい場合はここで指定します。
   - **変換周期**: この間隔でファイルの更新日時をチェックし、更新されていれば自動でPDF化します。
4. 「監視開始」ボタンでバックグラウンド監視を開始します。ウィンドウを閉じるとタスクバー/Dockに最小化し、監視を継続します
   (`pystray`と`Pillow`をインストールしている場合は、システムトレイに常駐する形になります。任意: `pip install pystray pillow`)。
   完全に終了する場合は「ファイル」→「終了」を選んでください。
5. 「今すぐ変換」ボタンで、選択したジョブを更新チェックを無視してすぐに変換できます。

## 設定の保存場所

- `config.json`: アプリの実行フォルダに保存されます(LibreOfficeのパス、登録したジョブの一覧、最終変換日時など)。

## プロジェクト構成

- `app.py` — メインウィンドウ・アプリのエントリポイント
- `models.py` — ジョブ・設定のデータモデル
- `config_service.py` — `config.json`の読み書き
- `libreoffice_locator.py` — OS別のsoffice自動検出
- `conversion_service.py` — LibreOffice headless変換の実処理
- `monitor_service.py` — 周期チェック・変更検知を行うバックグラウンド監視
- `job_edit_dialog.py` / `settings_dialog.py` — 設定用ダイアログ

## 動作確認済みの内容

開発環境(macOS + LibreOffice 7.1)で、以下を実サンプルファイル(xlsx/docx)を使って動作確認済みです。

- xlsxを同名上書きモードでPDF化
- docxを別名・別出力フォルダ指定でPDF化
- 相対パス指定(アプリと同じフォルダに置くケース)でのファイル解決
- 変更検知: ファイル未変更時は再変換をスキップし、変更後は次回チェックで再変換される動作

## 既知の制限

- PDF変換はLibreOfficeのheadless変換(`soffice --headless --convert-to pdf`)を利用しています。
  Excel/Wordのマクロや一部の独自フォントを使ったレイアウトは、Microsoft Officeで開いた場合と見た目が変わることがあります。
- LibreOfficeのheadless変換はプロセスの競合を避けるため、常に1件ずつ直列実行します。
  ジョブ数が多い、または変換に時間がかかるファイルが多い場合、周期どおりのタイミングからずれることがあります。
- 変換対象ファイルを他のアプリ(Excel/Word本体など)で開いたまま保存していない状態だと、
  ディスク上のファイルの更新日時が変わらないため検知されません。保存後に変換されます。
