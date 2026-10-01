# 初めてのKaggle：EV購入予測をbaselineから改善する

[Playground Series S6E9 — Predicting Electric Vehicle Purchases](https://www.kaggle.com/competitions/playground-series-s6e9)で、初めての提出から特徴量・モデル・検証設計を改善した記録です。

**最終Public Score：0.94636。初回CatBoost baseline：OOF 0.94175209 / Public 0.94156。** Public値は提出者の報告に基づきます。Private LB・最終順位はこの記録では確認していません。

このリポジトリは、140件超の実験すべてを並べるのではなく、主要20実験と最終提出の再現コードをまとめた公開用パッケージです。元の学習データ、OOF、学習済みモデル、提出CSVは含みません。

## Results

| Model | Public ROC-AUC |
|---|---:|
| CatBoost baseline | 0.94156 |
| Pure LGBM + Triple TE | 0.94633 |
| Rank ensemble | 0.94635 |
| Final hybrid ensemble | 0.94636 |

Public値は提出者の報告に基づきます。各行は提出構成ごとの結果であり、単一変更の効果を示す比較ではありません。

## 開発支援

実装と実験自動化にはCodexを開発支援として利用しました。実験設計・検証方針・モデル選択・結果解釈は、人間側で確認しました。

## 課題と評価指標

年収、環境への関心、補助金、航続距離への不安などから `Will_Buy_EV`（Yes / No）を予測します。記録したデータはtrain 668,665行、test 286,571行、説明変数13列です。`id`は入力特徴量にしません。

評価は **ROC-AUC**。購入者が非購入者より高い予測値を持つ割合に相当し、同点は半分として扱います。分類閾値を最適化する指標ではありません。最終出力のrankスコアは順位付け用で、校正済み購入確率ではありません。

## 改善の流れ

1. CatBoostで欠損・カテゴリ・提出形式を確認し、OOF **0.94175209** のbaselineを保存。
2. 桁特徴量、exact-value TEなどを検証し、XGBoost / LightGBM / CatBoostのrank ensembleを構築。監査後のOOF **0.94577345**。
3. 公開Pure LGBM Notebookをfold内処理へ移植。FEとTriple TEの組合せが有効で、元Fは **0.94605253**。
4. 分割seedを変えた再学習で頑健性を確認し、F80% / old20%を選択。Public **0.94635**。
5. incomeの細分化とinteraction constraintsを切り分け、主な改善は制約側にあると確認。
6. 元Fと制約Fを固定50:50で併用。最終Public **0.94636**。

数値は指定がなければseed42のOOFです。[主要20実験](experiments/summary.csv)には別seedの結果も記載しています。

## 最終モデル構成

最終提出の **split seedは20260918**。各モデルを同じStratified 5-Foldで学習し、test確率は5モデルのfold平均を取ってからrank化します。

`R(x) = rankdata(x, method="average") / len(x)` として：

```text
old      = mean(R(XGBoost), R(old LightGBM), R(CatBoost))
hybrid_F = 0.5 * R(original_F) + 0.5 * R(constrained_F)
final    = (1 - 0.8) * R(old) + 0.8 * R(hybrid_F)
```

rankを取る段階も構成の一部です。単純に5モデルの確率を同じ係数で足す方法とは異なります。RealMLP、TabM、近傍所得TEはこの最終提出には含みません。

- 元F：Pure LightGBM、raw12列、digit、frequency、固定artifact flag、Triple TE、外部originalデータ由来の平均。
- 制約F：元Fと同じ前処理。元特徴量とその派生列を同じグループにし、木が異なるグループを交差利用しないように制限。全列のmax_binは1024。
- old：CPU XGBoost、LightGBM、GPU CatBoostの等重みrank ensemble。

モデル設定は [src/reproduce.py](src/reproduce.py)、[src/f_features.py](src/f_features.py)、[configs/old_models.json](configs/old_models.json) に固定しています。Fは上限20,000 trees、learning_rate 0.02、depth 5、32 leaves、early stopping 500。subsample指定値は残しますが、subsample_freqの既定値0により行サンプリングは無効です。これも履歴との一致を優先しています。

最終hybrid ensembleのOOFはseed42で **0.94621842**、seed20260918で **0.94622148** です。

## CV・Target Encoding・robustness

- 5-fold Stratified CV、shuffleあり。探索用seed42、確認用seed20260918を固定。同じseed内ではすべて同じ行のfoldです。
- Triple TEは3種類の目的変数ではなく、同じ二値targetを平滑化強度 `auto / 10 / 100` の3通りで符号化します。
- 学習行用TEはouter train内のinner 5-fold cross-fitting。validation/testにはouter trainだけでfitしたencoderを適用。
- frequency、カテゴリ水準、定数・相関1の列削除もouter trainだけで決めます。相関1の判定はライブラリ差に敏感なので、列数を固定値とは扱いません。
- 外部データ10,000行は学習行へ結合せず、元の12列ごとのtarget平均として使用します。記録時の13説明変数完全一致は競技train/testとも0件。ただし合成元との関係がないことまで証明する検査ではありません。
- fold別AUC、予測相関、別seedでの改善を確認し、重みはOOFから選びました。Public LBを使った重み探索は行っていません。

別seedは同じデータの再分割であり、独立holdoutではありません。多数の実験によるCVへの選択過学習や、outer validationによるearly stoppingの楽観性を完全に取り除くものではありません。

## Local CVとPublicが一致しなかった例

制約Fを使った提出はPublic **0.94628** で、当時の **0.94635** を更新しませんでした。しかし、両者はFだけでなくsplit seed、RealMLPの有無、外側rank処理も違いました。制約だけが悪かったと結論付ける比較ではありません。

そこでseed20260918・RealMLPなし・同じold ensembleを維持し、Fだけを50:50 hybridへ変更しました。Local CVは約+0.000095改善しましたが、Public改善は+0.00001でした。小さなCV差がそのままPublicへ移るとは限りません。

最後に試した近傍所得TEは、seed42の最終ensembleを **0.94624653** へ改善しました。しかし事前基準+0.00004に対して改善は+0.00002811にとどまり、別seed確認・提出へは進めていません。これを最終Public提出のOOFと混同しないようにしています。

## 再現方法

### 1. データを取得する

Kaggleにサインインして[Competitionのルール](https://www.kaggle.com/competitions/playground-series-s6e9/rules)を確認・参加し、[Dataページ](https://www.kaggle.com/competitions/playground-series-s6e9/data)から取得します。展開した3ファイルを次の位置に置きます。

```text
data/train.csv
data/test.csv
data/sample_submission.csv
```

次に[EV Adoption Behavior and Range Anxiety](https://www.kaggle.com/datasets/itzzomkar/ev-adoption-behavior-and-range-anxiety)を配布条件に従って取得し、次に置きます。

```text
data/external/EV_Adoption_and_Range_Anxiety_Dataset.csv
```

データやKaggle認証情報はコミットしません。再現用ハッシュは `configs/final.json` にあり、別版の入力なら学習を止めます。

### 2. 環境を準備する

記録環境はPython **3.12.14**、Windows、NVIDIA RTX 3080です。CatBoost部分にはCUDA対応GPUとドライバが必要です。CPUへ変更した場合は同一設定の再現ではありません。

```bash
python -m venv .venv
# 作成した仮想環境を有効化してから実行
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.reproduce validate
```

コマンドはこのREADMEのあるリポジトリルートで実行します。PowerShellでも同じ `python -m ...` コマンドを使えます。

### 3. 最終5モデルを学習する

```bash
python -m src.reproduce train --model xgb
python -m src.reproduce train --model lgbm
python -m src.reproduce train --model catboost
python -m src.reproduce train --model F
python -m src.reproduce train --model constrained_F
python -m src.reproduce blend
```

既定seedは20260918。出力は `outputs/20260918/`、最終CSVは `outputs/20260918/final/submission_hybrid.csv` です。データ・予測・モデルをネットへ送る処理はありません。既存実行フォルダがあれば停止します。やり直しは全コマンドに別の `--output outputs_rerun` を指定してください。

seed42の確認には各コマンドへ `--seed 42` を付けます。5モデル × 5fold = 計25モデル分の学習と、モデル・TEを含む保存領域が必要です。GPU CatBoostの非決定性、OS・ライブラリ・浮動小数点差により、再学習でスコアやCSVの完全一致は保証しません。

整理時の検証は、既存モデルを使った全5系統の実データfold 1の予測再現と、両seedの全OOF/test blendの完全一致を対象としました。整理後コードでの計25モデルの再学習は行っていません。[検証範囲](reports/reproduction_verification.json)

## 今回学んだこと

- 最初に正しいCVと提出形式を作り、baselineを壊さないことが比較の土台になる。
- 特徴量単独の強さだけでなく、TEやモデル設定との組合せをablationで確認する。
- 単体AUCが低いモデルにも補完性はある。ただし改善幅と計算コストを評価する。
- 別seedで改善しても、それだけでCV過学習がないとは言えない。
- 提出ファイル名、構成、seed、rankの順序まで記録しないと、Public差の原因を誤認する。
- 停止基準は結果を見る前に決め、小さな改善を追って無制限に探索しない。

## ファイル案内と出典

- [主要実験](experiments/summary.csv)
- [改善履歴](reports/history.md)
- [公開Notebookのablation](reports/notebook_ablation.md)
- [interaction constraints](reports/interaction_constraints.md)
- [RealMLP / TabM](reports/neural_models.md)
- [採用しなかった実験](reports/rejected_experiments.md)
- [出典・帰属](reports/sources.md)
- [公開前監査](reports/publication_audit.json)

公開前の再監査は `python -B -m src.audit_release` で実行できます。学習後のdata/outputsを含めず、このフォルダのソース一式だけを公開してください。

このフォルダは公開用に新規整理したものです。元の実験ファイルやモデルを削除・書き換える処理はありません。
