# RealMLP / TabMによる補完性

単体AUCだけでなく、既存予測との相関と固定blendの改善を確認した。ここでcurrentは元F80/old20であり、最終hybrid版ではない。

## RealMLP

raw版はOOF約0.938734。55特徴量のengineered版はseed42で0.94523248、seed20260918で0.94532553。公式実装を計算予算に合わせた設定で使っており、論文の全デフォルト再現とは区別する。

current90% + RealMLP10%のrank blendは0.94612582 / 0.94614217。改善は約+0.00001143 / +0.00001603で別seedにも再現したが小さい。最終Public 0.94636の構成には入れていない。

raw版とengineered版では特徴量だけでなく幅・epoch数等も変わるため、両者の差をTEだけの効果とはしない。

## TabM

固定1設定（k=16、3層128、dropout0.1、lr0.002、batch2048、最大64epoch）を5fold完走。55特徴量、fold内TE/frequency、trainだけでfitするquantile変換を使用。内部10%でepochを決め、outer train全体でrefitした。

単体OOFは0.94494217、currentとのSpearmanは0.98606959。current90/TabM10は0.94611808（+0.00000370）、current80/TabM20は0.94609580（-0.00001858）。事前基準を満たさず、別seedや追加HPOへ進まなかった。

相関が低いことは必要な補完性を保証しない。計算コストを増やした割に、最終ensembleへ加える根拠は弱かった。これらの学習コード・重い依存環境は最終提出の再現に不要なので公開版srcには含めない。
