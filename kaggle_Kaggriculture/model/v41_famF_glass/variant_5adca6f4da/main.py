"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>TaR7GafSbi!Dl^)6e-(zqo{F2n9>NmSa1wMFc1d;0_VZWTaf=Ak~4GmrN64Rs=5zp19{RB=bXL!QdM2GYE|{0{^!xZ{rPWy{mb7T{nM}h^ytUuZ{9rm`HNpY`u9Ko=fD2fhkyF;KY#u6-~Qt-|NY_r{`BaZcYpll`42C@fBx#x`@g)n{ptOGp8Wjt|9<hS!-Iafef{>k{7K)ve0}rb8~&%`yWf0wbMxc-50A&U|8(=_?eXRBr}py2@8A8n4f^rNM?QRWH{$(2jz6OH`0@4ax9?uO{qVJ)zPow;_VV-(e|&Ru^X-Sfe1G%m_J_k?+EdvLbsOOJjMHp(AHR9`^3}J$yx-)v?>?-lJ(porKfZeY!`p3Er}3R$a~$V!g^a1Zf7gqfhb_P{k4ro*<MX#SuLqGhJUJAHXzVYZM~mnT2=?{vfv{0u;F9l$d-v%$mg27Mr2b)D?l$7?1rG}dn&K=0*a+N{-NS$P;Sr~K!opZnzj+Q80akR|f_yp7ziqreThY_>@4lHWv$i|10S}X9DZoLU*QY7{<2l3IvDd<fKi^Gt+@s2VkoN8N19gqJ%io$Om90U6*|Z(UGJgELyF))YfA6aMG=6mU>8pv|c=+N$G(WE9HMU~6*4vBIo!I{y4C{L9e>XnQf_aN@|8K$aZ-2JtnZIH8DO||qui7tj`i7F<=FT(xH1Te9qvqoSe*`GaH>1Xq|G#@|zP}Lp#4aSBwrISE_dK`<``2tP10M@_e-{rXuORhIcP}89cznU_t5-KK-v08to7Zn&zIypDqZ7#A5Pl&2NQ@-#3h%tV-E+q6+SKCB?K?VZ-`u=<1y31<aQ}0|3A=nV9-}#kn%2Y%Vr|)G#&#26=h0m=vSOQrHX}FdExYr5cg&?nz4hF0U*G<CKEgI-X3IOXTATRpS8L@#W*=YG=Yk6U9S`>(ZF#TcLH+-5@nL1R>ghU{PEBMmolg%hIS<(J)+`?;cgQTTC&x7=d@k*|AZSv45BiYm(HP=dOP*o~h1G#&AIIke=8c8NC{Q4kR)D}qesu!5q~q4E5Op50^<cf?V)zx%(sPUV4kWo>-#vf*2WM`y8QV7FhUd7IJuTWUp4DY8E0tvTs$(=UfEu303s`#^ilbcFB@s8ASQw`~{W&&BH{+HEA{2PrPfO#21f(39ErQ+|!lt1pXZ&Q5%^(0U-opEYoE*9c!!7;Goux!t!9N4+_>=i(Umad@9&jz&z5qHa9%Qa7c(tQ)#TzQ_A%7f(u}&9fTsz-=L6dK!ql$;7oZ{j9T;<&d4oGaHi|3u22#nkWGLf!RB+iRuW~Y@eo>M4VxVY)+FO)5gAA&VE&mAdR=yeJw%{#8ql@{*qIEGa(L1@gI2s?OR{T!NDdaH<o0!I(dbt8*$fuwi)m<d;F{%1FmeSFp(&dQ3cf#K@rDWo6@Ie~f|b2YewUj%-4`E`1?w+C)uej{I$c#^L3YQJ?R4SpidooC;e-ssUjI}D{Drsuca{p&v>M0rgQG;w)5%7+=a>XT`?ce=b9p2RUL$93v-$K%O+ji3Stt3Kr(3AC6!h7d!U@X5A~BJZo=c2@9B^1Vd9TfALl{dbEwNa&mbZ8A4{1Pix|-HqM9x=~5R%Q|r2LJo&Qa^19gj))|#XJZ4|uUU$H%{;i^8%?|h$vXLiy%o<Nym@m~gbs!9S@<G9IgBFu>@z}-o}+doLSGGhJior>;&J->YOWs=_pay#dcNA6YZ9H1Yu?!MOsX&GY}I<_k)2dHYWhh#gT2>I=Dm6Q`uR`a+`NAMM<3ygfLua#?HJy}Pj<As2Tx%)gZvMAVO;M*L|7@zJ{iUZqQFsDl~z#5O5(f%^dyuwcWKc@rW|}EZM89A>Dy57mC9O!AduG_vd<pNx<#m=c^bxMLc++L2()`3X^K}Ua!Tfl+Aql~R)L1VZxv-o0j;6vN|KLUo$n_rO#$d}R1DK@e_Z#Xd+UB$Rat_<fG+&_-SaX8Biq@cd~9DCW5YU}bX=Z-QaLfb-}#<+f3O}{Tnr=NT87#XDqbGGWnb0P_?^=B2SfJL?d=EcdHkhi>Bgo3abgdRP&mS!9`8mZlVR^q$9rKhQ)9y0rIU(ELgMd{6<okhqgUg&36IOiXaEdDwGn}SnCIIKOiQt|mIfkP@~deAM^jGg$U(HVx<lz)Ac|082mgdQ{+Ljj=wBsf%!q;*ppO|#Zm|)U{$+%t$dsrkk3ft~v_sdMbkQqY%=(J#-_o5Brf#&mpO%-ZLi?Ex3^GnLkw*+LR#cqO060)11{TL`=Y!E`7|<A{+r35bhG&W6xYHB@V5CZbi!jIA&<9MRv5LA9dId`5J;#&<T1eE2q*26&PZ9dEP7J6gk<d3M!Izr`v3wZ1#LPEy3lq}a#NPX4IR-N>ql&f~m$oDqW#2NI;eAwacZ7^=rjG+#73k-u4!eGKhl%q9Tce5IR{i%3k#K*xpuAvckrA&m9cydTe%qn5{dxP8B!kod3W=uO`+@^#`|j?Oj<6V3nuwkC_%hEp{B`i}CMr>27Mlq%9mcBgS8<SwxJ{Zv%a%!zk+R?V11}s+IjfFFwy|EVpetk8TcZ|kOrvXPrV;?HAVeZhmU$kzUk9J0!%yCt@QTSa72QfV-^VRvgc{2v*%B@(9*x-CE?Uk$GgGaVOL>(aud~&DCCp$>{0*o=Xbq7hM7J0{^oy5CJiCgGy3@js8mq|aL*wAJ_3&~?oeFFM1KAw5ZD(;67c1MAvlxYm-ewy~3ga`5Dz3?@)!Cl5^Io@qi+$2h)svDwAx73r&Htv=NIvm1CIfLhul?+Fb{|QjezLALN|EhW5iOa51IFTH#jsaZ!PC1OhTp$@_51h#{rWT=3OA)A0B7y)@y2=jAX)dndVHpK@Z`q7JT$bYOqS@grF}z$ClT?pkZWNo&?U!&)X>iVNo+kcC#N&YJh7(UcD->`@?)ca=nvNYsD@i9Cj`WW?+;+WT$2ChnZ~y42GwRs?0Xt4v}G`@W<B7@WxX4;iPFCGF&+}%%oPVQh=hrK2w<gtAjBmOUmd>|dA~WJc#P6U#ZARuw9T=?7q=Z7dYUmFAFtm$f7`El<bq2aAXhm^n9c9xti{zYZoxFSVPcB1fxfLs%j=|)3PY=$b2PzjG9*$mB~J_TPhw|HLcX+FnWjyNYnB&JsI#X(qW~XII=6d=N;dd)-{>Uiw4CDg6iZ{ho{9!ZB?nhz5lW{Zc8fo~A^<IJyT&eJqmoX7(Vq)5OFQ`g)`>CmUV%gVlw+a8DS!D<Tc)cWwogq0!n49D@H9UiLXYRXQ1eidpjGdR5qsp|b`3G++Vj+)!~E9njXlD134v>sc<jNK9maiW8Uv#UimgO)P9YIuoA9_RLj(5pGo|B;5f0esQufnXbGtiGUg@A9)-+=&mb`y&4zHD#`EJ&=4J3*jpD*O5zj~IFiMB|%YF*!r7d~P>8b#4bhtWd2C6N=3hDy|Q&M{tF5kwc$+RliFO~jLmogwneQV$ff$JzzE$db_-KPjB*#X=1humV+Y=AR<)cs)Ey%U1d_7TsDcf2VadulLpMOmo<;y6oiliVT}<v&vsc_#ks*#1K2{96;s!X7AYKEX8o~YxmxUC#U(9J0Ikq%$9i3miV)KSX;&s=0=`zWU3oezBn%Kixz#V{X*!#e7lI5PhxNeX=Np1vVH28lE@InIP=sTCmXwk!)*UVY~z|boM*|m)mn?EsqrH@QA|M5g`{&iJV1;xK*nS=gzlR3k`F#vwYe%Cym5ar!xxLbpLd?hp4guVo`X>w7kx!i$jZT<J=E<VHwnZ)=byG8yFF?J;~U4Iy5Wa6b=}k0?r)6$`t-2eS2_MF$RAK2QF?8_qU90p=3w-f(=$eoTs&E=%41-kV(Nj16q)LPI4tL-zf2I=;<*N4A&n+)yK(%k@;e3vmh%}~JGAeC7e$#0aS>?cf(C|TTpls<B+71`OWW7)`Zv6|9q+d=?_&>S!Z%n3o{3&h$VXAk;l1U``><vymTbGLjf5CehSJ?2&!);e;Lm4NuQ?rGZ~<y#j(`RE9Dh!izt7eCl<o(R$Cad<(x?1&$H{v3FvkXCYW=+_w#$k#SUR)|hgX?)L2z$`C#edx0@Qbxz&CrwCmMp9Pb?Zi6c;&+bMcXq9#V-Q%rdH(OdQ4tu4cP}<`C2D1g_HCbRqfY<XSOkSZjO|F8x`HJLT<>|BVMUQG(73u?Ck*ruFdWyB?ComL(b^Qp{t`)uqFy$elLx%|_F8bjxK*C@0P?Ac7Z~s-QPQo|oOp%VkonnJapueLp8H^9fvt#CxyZXQYHwT`z%aE!gq0xH;Fu&#H6AULb0-FSj(8B0P{Dp0!>Hi~He}Ib_VKnVqDg&w$iw)d;;}fO)M$7u~UtQ8km4)ItVq1us$+E*XP&mZQXtTtX8=n1m@1nj$qx*sHgBT}vn{^z7U-Ytoos<Y9zRlF>kwQBIVL9jQK&ETm1z6lJ};Ig!paB~#M8*YqQ0pKELpjp4h$aUxr#tbB}P90j4;7P`V<D;Z2?w2_i|+gj~{>(Rh0L9CDrr!pkqFCs)NI87of70~%a-)46AfX|mhml;L1x!PRh+D_i&gi6(YVQ_;w8;~zyu_n$Rzp_epbE<azUjB*X!$a{5M%fC4?y77vjnL_uy*vwIv1bFmQ2^W1YwX)Psc27(E~mSQ6r}ibaiQ{7<cDIcQg~VV^5CRIVt*KqpO8#T2%`(EIKJYr^4pjHJp9{0b&!)XQ^O#lc;4n`Iom|an^t{s>`Nn#=%C0Egs7+ZrT*2G(>J3QbX3pq2q+$xlt{^SH{-BieUaCL+aFOEuHvDK@+E3GM+;5*!(Ecb$m?42N>D<xVMMv!=M4S+))e9-XL0<br~@8~{M+!DFfrHM)DnY$m5+$DP5q-`A}%K=YEpbJN7~YBg0y+lE`$)_<j+kjlDA0^H^-QTRlf3-GIWSRhzcoeuTc{M+i@wBu?;ujbn;8^#2G#*c{Mnttt=|&IdqQVtqHg%o<SECk*(2wI2wDoopugrV60BEy`aLZUj8=O^yk?{A^|b@wPTs0*IXp~PUw?nN>_jk7!+`VunHHZU$d4BJtyd}anFGTVROxj>onJo%7mruf|F4mRv}5xYgfTLm#k#>IQ0uGIZRuUbXLR^)r!H*i%m%**YU6?s%zrP>((TW7&7Tyo+~L({Svt@JdrZ0LXoyoHG<HHuTWCDXa!Y2S6Z~Z-I)Ziyv%*2Wou1B<(5t?r|R082KbiJBP7?B!dl;-ZN=03uv<&%H%HASHsXs+3T*<pjkg`Nh&IW+QKn#H`QaVv^VP)3Hb6+F5Rpu@v}nv~8}3y|dK#O3=$j3b6bn|CqNQx~A?Mz(;mV24aol{M!-7wna-@KjEV<81_6)fyK$O`ps1w`umRGWFvfBtWkO`11$#t3!K{20#aj<>DLq4G<kdotlOAjV&_s3J*@1-RoTlpEu2xR<g1w%XGy?hr?5n<2LOQEbYCYYc=QgcG7@>7y9p<^=$_dvH(6F)GGoz`|ena;Eso)rhRWLbc*C&pJw2P+P*NKfd%kthp|WU#18>z;N)#*1vBkxe6yjm_|hL~>W`LbQ)4m_gCe1c!kp61PbJhfd0Tp?yG3C&BQ8SIwgMKm|}qL2OoM7yMbSD(t}(RF<s$uq|SkL!tj~LhV4+zKkw$_@qBs(Te>zr*e6Pik2YcQD>IVyK#qHY&aI_Xc~aW{c?pUp^K1nhWCt$gB%&>M6C{PjhCYYMdGX(GAhO<IPrG(G?h14#Kfw|uQm|D`Q=&l?hHf(8Xx?YDCY;3jr4aUTEKB^#D#%Lz?7Bi&s32CEF&CLHb1_2cf}M4Ih7leKmoDJP<UM4j`2XK;Sl^B1ewSYk~6)u?XM5AECp1EV?KnV$L@*eCkKtCKbn!xSH%$kAX#r)is|!v+FVA*dC4Z{mSP9dRZ(YDLYNWRJECSs#5Cyg?;O@T)=q~<ml(QdVDhp1H+?I6ZI$VC4n_0WHhj&~lQ4qHI~I3#KzCdYG+IFBoMN#(?zv4N2R4bdJkRNjQvAkS64ABv@-TO2&H|UKh%Dg-Up_Hkbo9+<JgZ6*d(AS-sH%#*ERztrgpd&Gi>w_nDDl-~Ss-C(HZc+`m6V93SXHjhSgq8VQ_1Jy`-LNiYg5{WY(h!A3Z8Hi<n2r|r;A_9qufb!7GkVZ4A+ny(uhji5QAf%KJH2u7&JohP!etytiMMb>elKRs9qHXJ!W-M404601SN<E*+VGZ?&cDJpp*fulB2nuF1}9_Ny#~>-5Ib<Yq;uN6d*m0S93Qo@3xO^mkB$W$`ouIoPFD&a~_9^TnMC+b%Mm3VOovNy&DD|)~gJYr<=I!Dk4=_ILgOE_G!2UqF&gwJ*tg|O*J(6dxgj@kNomZ9zP8{7Wg;D#ZMXVGG1zI5P717Dc#UsCQkLrtrRSlf`k-D$V(OmE>#~!%R^>l=fe4r?f)Pw<*XkD6YMKXR+1=OR=t=P4S02HVVDWyX-g8W($xu>L8<l_b6(g}pw=u2QG|MVLA+!h#*yEmkoQbPH#y?`IY=%FU};<2gr@-<w0&yc4oMcX*dSzu6-E%0I7nIQrP$q@;AkeYub2#!2GKHjR4aD?l|$EdU|=j3z+PyQe+xQA>2(Rxs!n=Fr4g;kL6s`JQF=%epH86V+=(~mHb#|25lA8kD_1eR-2B>MOl7;JFecz*o+q`O32B@koEfAE<`7%Tmyfiq$P7B52~SVYFL|Ph&Duol^T6gbd=JXnkQ~KU<YgM}_Y$!}k`1!v_1L{9fJDd3I>o+@xJmX3sCFs6CQzjg12UXel_-Xtq$HA*qKLXd(Ye`=m_mb1b}dLvj8u2?xeoeuJ}=(he*gUK?ISG0$UT@QNh~h0>lM~r^zj~-?XvBXi@Wl5h@hX+{bhN{q4h<UpW<XFGa3bCG!(m&GUUGQMKQI$7jd;?Xz=w#<3t>}jErp(w6!CKucEmma!!>e(EKLKxs52Fn?1y|4u+xSzfyn^iQ+;8THt9a+OAB?6GM#f0<NOCJv#?xBQJ&rKUYabqNhEwI?=O9N38G`9P?PcR7a7b8r^yV;~p{M=nd0?nroQ|Whh`eutk-7>-LA9;ExJ=^#PZOfEBb#VwHTkv`#q-;A?S3K8`SRKt<#Fv`9zHRD^*jX;HEcK}&gT%cb#+>U0W;bFKm6ty;82E5^(fQ!;Jv0gBxZ_hCk7c92NodATM<@M_}AH6@+1%;Zkfn~35lKc}1_6xgQFzVyweLy*tCDwAS9g3^t;WAUNgotYcHIJ1H`3r9(8KuBr29&%plc#?b1LC~2YaUH7{AjDsuMzasn?Aymq^5@+kd3;6AsymO_WJ`X1UV}!>DKb0z53*+Hn)c{nM?TXXHuZPX$;*cp2`P-uq|_gD%2Ef&@t!3dxA?MFL*PFNK~B$EKyN8Td7l2l;VUO7=r;pDN^V^i22hN<MvxJ<5Al+$3r%C}2CPzw97@f^JgUZm9a7EE#J$R=Z!7#GE3guS*C>T@*z}jZ!b!&D{hA88nJCBAN`27`MG|a2RhHD)n--NJ=bTk}K0X&#%oaB*rDJBVmwtL2XV6t*DI9l}PW#R;@Zk-8l=dV-X$;0sLmR7F=hqt4DLc%F635n5d=+LLQCh1#<|i&I7d6ghhFM_QN68Tp(@F0vSry%SrnrtyX{motjiUQZM8b;NINPl&S4P`LOl{D8e=Elq>97(+1vi=ukI<7c|J7IyZA@ce!#c;76t7GI7=qytm^#=H)x}G-!N_;fFJA?^R%EIS<1MilGOu)6FM<ul^m1-oP*ivMyXFG!cy@jLBSIbP(o=pxESUL~gIcdNk5C?Ota-q^U0#-J1B(3u-BV+?1_g1*Pk$7=PlOT14eEM)L>C;ShH%ls9MXS<$)U?pz$}MOdoBv-)Ty3+cAopX%L~+w<+Q|TDnXOJKDDF(5=q_}Wxh;Oml*oNUD3mrAH#-q#blRxg}s;^dp-fh|KPXD+^*V4<8T?of-G}0jFQROsG5enInhb4kn**m!cZ>t6eM{JcQIG7y!~ZI3MB-{p{b%B_4RB?*I-{1+hm>+G@9wIm<ndPOGU0$pC45#pS)wWY8AKyk(no(LHdN@)dVk`_u1eMRMc>1BBVB@=CPqf7E-BbFQuGbr|wKl%#gh7cnq~a&`NO;Nj0byIC_AEDJBw(mK25w4Q<Ab0hfq1=d4UcMKXHJ*|ZHQ9ACCnH#Ug|Yn7;cBj3Gc1?Yj@K6pt1tH~kt=hW{WbP3EPg|X*OpK_as%uTvyPt3C9*}@AyT=2yVF0MGA=5{MbyHv+NdvY4U3kt&)lmaIm13DGKr$Uh@;m@~feS5bK&kR}xeE3ra|E+A&cQ>57cYfX$eS4W;pzN%T5oko;fCp*3u)-re?$DQq{XGuvI^4=IawCh$o>!W%cH2X=??zS0E3}d^KZP7ORfN3+R>XSA6&JqMu&ZhS=M>@@H3wZtzyK>(Q*0u{G2q=rKqUTFL6TRm*}||!)X4?Dq`F|Sye~NqU~jo1f%Eh!MG&-JsmhF1Fe67jtPrsnR$`o7Qq+V%^z8FQ(_lM5frT9EjY#Az@5#<YYmTYib)U5c3I?@QC^E%6<KR4ouM^gcLw&VyZc6m^SRqUrI8!aMaJlGMP=jJ4pjq46C#kd;U0#T1K=!$FDvC{1A+iTKs>3%2K)4Ix854(y_Q_fI#1(8k2*GVPAv>eml_R0CHNb9v8<&B2p>d$2wwig@8oWYU4c@;XTRzE`BI0d&SG!mEU2Z{3y<cL*TSg~a!r7Da<f>oM*-sPjSg{T7TjWRk>72P1eo+vqN_unR=n9+_2R?dDhg^<W0iQbWq;CqW!UqRcU1%}$$+B%`tHKOMjN2M=!mkYz-l1eEHr!<;Qj$Yd66NlcT}sg895R~A!;e&&2!;7oP^#8IM7Ewk|L{187@`*xxC9}g9=mYB*gahE;c@%1p92s)2IV0k+EY34$y_iEz8}A|#&lzmvf^s?X8m4zp64zWzEICk9-V4jU5<uHdjg$6HHbFBaNs<Qt}APxS*oK^q!cl9)g|WTfrv61QjHAFP;sK{+hr(XTrzv!RNae9uq^$)46-S$xcawDZ4>8H=?(<pCXjN?Fy)QoDQ{n<xHs9Q;?>(Zv?c}7UwkzLgoXVxtaN-^W>pfNs!R~k-_KBa{IY$f2{LMRI;447?YBm>4ZTH#BKop54bnn1P3U8@^}ru#Ownf<Ep!SU7hPXiCOg!sxa@eeIXtA&oilX6S-|z<fxtL_M|zYKP{)4-bAv;k6jssYB=OixRO7?to)`Vj*3BTL2$1-5sz@962RgQERaJyX1_*D)<srAiY9c7Mhj2vL<m0E{3(h|aK+&)%(Otr@KM;?G7V5#n`K0#;cbs@#ksJ2rBNZY%GFqezPNa(d+4hE-B_>)J<-Md+)NUcxs1llr&_-p69STb^tk$b<+{Ce>BecR81+$~x##)jM<wv8+szcM6EECfXO~9Q}z<feT?d?Um-&>?7A<IU>2?EyWCA31|1!05s^*uhmIPPq3!w_F7MG%}7ue8XLJ2rC}pB}bHqk-=q$|8j6zVF7R^em{ka49&tXo4&1z-05Gq^P}}LiANsu#g5W=`?sy*$q`sznePCxP}wo<MrR&x$Qa0OyCE7)^D^!s$kO~s+UU0mJt$j+NE77tolLXgDz%7g~H}!qEmqeB<N2`Tkga|$-9xR0DHUD^n#deH{Vz>o2+6dd|i#YTVqkSl*uKh9gSAZ$J5+j6j>wsv9~Yg;eGgp+cc0T`8X75oK|k%(QOuz3&y5NzkD1n2cSO$ZJ8NNPoJ&cF0?k61*x)YXL<?hlIgswq}XKj=TA4iPW!|JmL!X0;*SkN<FS<YfJ?3Kq1a%>Y5F2oR!1e%KDLGp+*^~xqza59FKW*5K|T%!gy}rVV8l#2$O==CO)lUZbIjX63T@We5uKzg-JT|EiPW^_!b-$THCA&u3?!0hI2`h0*rULiG?=&wnJ4Eu(4m;eF5=&IfM0V*bG;LAn>Y}Yw0u&w;`TNCjH;=a80>BFN0yk`Z6#Q?*6u)=ABUop*0dL`k*Syw>5rmo(x_YxbG@vk1xWJ{a-<_K#{$B1bXoD%+8U{n0rJsRNgHYsv@Nld7@4cPJ1ez~<o*=uW9L}aq-9o-dH^&yH){xll~=SVphWZpm8=|M?Glq{O=4JK`t;+>W~o}lZ|93uVyOw6$*cyl7VL@4+2jRXe5!}C=$+K#Rodb<30=NXu`O9@<*ZuvB@q=nf?7}EpeA0i*$}nhO1p@io682}sB^;GZnPV%4|gUpe7rj!e|3!lu7Ks1pmD&@jkHtL{)!er(aKz2Z9#QNW)z^J&HvoC*+Kuzt*&Cmc4@ezP}V-3rxRe1+pUICGe_7-aL__=c+iAn(eUR(DTh9bY;^L=imTr^y!6TGYX$I<Wzt{2);%7oqpiLfB?msqA8;t9QOP|e$%8_N;F#Z&+jQAtK9g!Wv*?CWI^i*o+?d0V!4q=`rAjvqx6Zi&!XntQ=AMv9<ye1EQDpRJRAbKrb~5`-eiM5Wx@;Nqy|spd82}%iG>w9x__`Rm-btPBxu?Ad@i?epcskX?;Lun@E;?)=U~~>=89(}~Gl<?oVaNDXj7L~fBP#YuFkOqw@g6FjxMoH1E7KE%Rd-RpGu39!yk2G4Go!)ToYh6Lw-yO94K)sxz}<qV_(UIUP8!kO2uhI2D^1m`ZuH<ZHRtJEMHWP`DUv6_>vnsze*ZJHGOTQ(HH5G-3Jz^wuYu6gv^hbqoK$LxNo(AXR6CukZ6g$Viy1e2#*nEL4!O+gV91%}C)<TL?GBizGSVFK8J?RKzhgv^Pn>h}L;-+b!6!ei9kwhQuU1DWijh;%JvF5%mSiAj^wl#Sdscn~2l2L<#SF^3m@&I3<&&3mS9(5{i@N6+lng?ub@I4xIZ`O@wUc?cd_m5WuZ$ZjP{5@uz*ULoz0)h9_)IX&O{+ylFp}-)GO^#?nnk7kqNH)ct~o539NaznGw&DS^=;t7-8&lkx*_zm*()x!VyeZom#F~h<Kj--e<{?IC}`0okrGV7r3s|X-z4-pfkU=U-14e9;N3r@*j5#s)%KLZGp$AktY&HOx1W4T4JTz6)DYQZI8bOwe}8U1b4_Mm_7n>6>6m_2R!WUd=B?&)^pqEAv_nhv(y%k#3yFd%#<a*woN%aTxn&XDR!wFy&;fN)U)_+PO^*~wV-i_dyHxrdq8tXmovqHfpbg3MZC>dL6{B|tu)16)QCI;54Jdv-x8A58?}3|$oj2S=D`0Kvatzf++n_#nYoaoR5@(exMU9+?%X(1$M0&-6l3mBCWZ&O`@TL2xn@@#xfI<NUtnSfaot><K)({3YCL(u4bbS!tM7R&#qQ?2t!tL<tXzxdnb$fgJ{qwiCBN^}rBt5$rKNIjn`xjc+hor)<?}X#iG;LJZBx?i@+6`v7*3(!fC2W|}Y_f)q_p|$Tvb&GH1tYHngL*u+(W<C}Php`II8YJq!~hD(M)HM)!6>0=vxBN#r>vZanbWhHmQjcqhZRS|+o_z+T)kW^MCplv)9R|SgGc1n<mAz<LN^&#qroXGE)D0cJ+V<i4Nfbb?h?^8idxD|t%~E~oThN`boZnQ`(XFxP>zo%>~CYwQ0*myyzt5^tHzviRTf*ysw-?pbjOeYxX8jrbOCuKr)O{O-l;Ll#tx%Dc}>u%Y7TY^$X^v(;}d%(V}A5WWOJ5zlM@|y8FnXxUF3&V`cc^&9~D*r`-Cg2Qf&<Gbs6FXN27Tb3-c#Xb*rFRjU0@-(mrEifm9bdS+9a$bKqAFL$!aXP|Y(#BzjNqIAvd!ssqPGSXMiRG<>M2hf%S^_!S<R%#O=UppZABw29m!U6&%a4$6`PcS5^+)!Jc2s8e4RwZ}V%&q*t9{)q|9jW+H4hU>s@+oxi-D?-EqD_Y^`&BAUQc6x00c;PS}yR{$ih9hn7aI;F%&!Dh^h#&;5Ho|quW3j}6ik8fu6FNRYt`@z9JfaMql)_5Fa43Jd%Hd-~kHW(epLsev7KFX}5NSh@7Rzz`Y4=D5#*s|yi}sIE5U3Ef;V|jWNrd~VuGr^U?Iz8Y8U-*TvLbOm6ZEFErYQDMfefPKUwp!PN}#MsGt@EiH$z>|{Gj&aB&wq7+n}H**gZNv0#9QKd!U*cO~si7BE|zjj2)L=bJQ?MwmUMkt{&*x#o#d0Shr^RM!!^BYX>U1Nk<2;cG-g|M8{VoaLiH*pf^B*d4<iaVn@VRsrFG(h~5Gkl7vzxH%ZoiR+1b(`scNfQ4YJf!lrrB=MhR7qoh?A>`g>k3TI0OJXzA?5{727tZ{lQ$oH1py;{6AVWdT4A>W7LJy8(gh_rRYjeG4FsH@g)1+nepl8Bde7D;{KV_upY&1R-}mlw;W?tR%L;C*taugkfsV0Hp5(Y(BmVQaML7p~$Rc*Qp{K0EyFD2_)=aAy+t{~X-3>^ij~<iLB2hGlttUQL40tQNv7cGV;;8nDY$Fa%6nO0XN0@m+*%ta13zhAAM@XUW%d<idZWHfRn>L~1mTKc&QrnFPK>en&|J){zq^8I}zO=r`|PzWVl;7q@rmA6Xg>f=`$NLvV`PU=fHa)nl~aRMVhcYR!3TNPdc*ZJ(svvpC5;pxu~o$6&xpbTPa{SWGh4#E7vVMZ_Zk6eoqvKq*DVp+`j!{(9x|>qG1aPPGvlyA{dc_X=^+x|eEAPR^-^R)Lv^H*5IKxAFlBIcMVYRwbyNX<24`9Ic5i1bMuWqpWe!6#J@9gPpH|29-T~^@`7uYC$v=3?e*(6$jzc^|Afzv?`->tf7z2B-$KPl%Q9`ds|5r)JmhIh~K;*S!GloD;%q&!q%8`OzKz~P9wt9g|51Bi2H&Ka~Yd^w$bewmQPgam1nn^GY^m>;;~&#wg1-xM$)3KjmB{O6&Bm4b_Ra_-$G$}SlF-Pm3@3ft<p<)7fewVf(r0EH3JjGv4Y_egH>3g(+5(R+`?ehKdu<9IGXvGZ5L~<7_l^^Mh&J>v8m3reJUpHw0XgPt3`lOhE>tyEz&}?Eq$S}am#p38LSZWk{O|q(i;rF$P4L@Thb1URTW?xnilREvcRBN@>l{UXrhqE>j?<Q7WuIrOeHW-v^%*$iP@4QE!|#2G&2+scLH_UHiOS-v<5`c9=pN~Y2=a7ps}m&8v9J2Gu{W`;}cW39ID%Em2D~p55E7g+sXZj`nBiMa?0y6cl<}Zys~!MnlqzYM~!RXOJuX4NLhmsrK--VNalM*!f9ZOw1q;D-Hz$|E!#`unVqt3H}R0$hP#1bm}b^XWUQyVB+w2u4=-B*PYy}b%9!Ja;Wuxi4zSE%c@g83fDUO%q1(T8zv@|efBrv*??<@")).decode())
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = _ACTIONS
_selected_route = "v41_famF_glass"


def agent(obs, configuration=None):
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    t = day * 24 + hour
    a = _ACTIONS[t] if 0 <= t < len(_ACTIONS) else None
    if not isinstance(a, dict):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return {
        "farmer": list(a.get("farmer") or ["PASS"]),
        "hands": [list(h) for h in (a.get("hands") or [])],
        "market": [list(o) for o in (a.get("market") or [])],
    }


# ==================== V17 market guard (appended) ====================
_V17_BASE_AGENT = agent
_V17_ORDER = {"BUY_ANIMAL": 0, "HIRE": 1, "BUY_SEED": 2, "BUY_PRODUCT": 3}
_V17_EXPECT = {}
_V17_BOUGHT = {}
_V17_ATTACK = False  # cand_2 带自带扰动开局(t0买53麦/t1卖48)，护栏不再叠加
_V17_LEAD = True
_V17_LEAD_ITEMS = ("STRAWBERRY", "MILK", "WOOL", "MELON")


def _v17_count_animals(obs, seat):
    cows = sheep = 0
    farm = (obs.get("farms") or [])[seat]
    for row in farm.get("tiles") or []:
        for x in row or []:
            if isinstance(x, dict):
                a = x.get("animal")
                if isinstance(a, dict):
                    if a.get("kind") == "COW": cows += 1
                    elif a.get("kind") == "SHEEP": sheep += 1
                elif x.get("kind") == "COW": cows += 1
                elif x.get("kind") == "SHEEP": sheep += 1
    shed = (obs.get("private") or {}).get("shed") or {}
    cows += int(shed.get("COW", 0)); sheep += int(shed.get("SHEEP", 0))
    for i in (obs.get("private") or {}).get("inventories") or []:
        cows += int(i.get("COW", 0)); sheep += int(i.get("SHEEP", 0))
    return cows, sheep


def _v17_wrapped(obs, configuration=None):
    act = _V17_BASE_AGENT(obs, configuration)
    try:
        seat = obs.get("player", 0)
        day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
        market = [list(o) for o in (act.get("market") or []) if o]
        exp = _V17_EXPECT.setdefault(seat, {"COW": 0, "SHEEP": 0})
        if t == 0:
            exp["COW"] = 0; exp["SHEEP"] = 0; _V17_BOUGHT[seat] = 0
        for o in market:
            if o and o[0] == "BUY_ANIMAL" and len(o) >= 3 and str(o[1]) in exp:
                exp[str(o[1])] += int(o[2])
        # V39: cand_2 依赖 t1 先卖后买的严格顺序回笼现金，禁止重排市场单
        if 1 <= day <= 2 and _V17_BOUGHT.get(seat, 0) < 4:
            cows, sheep = _v17_count_animals(obs, seat)
            money = (obs.get("farms") or [])[seat].get("money", 0)
            for kind, have in (("SHEEP", sheep), ("COW", cows)):
                need = exp.get(kind, 0) - have
                if need > 0 and money >= 500 and len(market) < 10:
                    market.insert(0, ["BUY_ANIMAL", kind, 1])
                    _V17_BOUGHT[seat] = _V17_BOUGHT.get(seat, 0) + 1
                    break
        if _V17_LEAD and 24 <= t < 700:
            try:
                tape = _ACTIONS
                nxt = tape[t + 1] if t + 1 < len(tape) else None
                if nxt:
                    shed0 = dict((obs.get("private") or {}).get("shed") or {})
                    selling_now = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}
                    for o in (nxt.get("market") or []):
                        if (o and o[0] == "SELL" and len(o) >= 3 and o[1] in _V17_LEAD_ITEMS
                                and o[1] not in selling_now and len(market) < 10):
                            q = min(int(o[2]), int(shed0.get(o[1], 0)))
                            if q > 0:
                                market.insert(0, ["SELL", o[1], q])
                                selling_now.add(o[1])
            except Exception:
                pass
        if _V17_ATTACK:
            if t == 0:
                market.insert(0, ["BUY_PRODUCT", "WHEAT", 30])
            elif t == 1:
                market.insert(0, ["SELL", "WHEAT", 25])
        act["market"] = market[:10]
    except Exception:
        pass
    return act


def kaggriculture_agent(obs, configuration=None):
    return _v17_wrapped(obs, configuration)


# ==================== V24 hybrid layer (appended) ====================
_V24_W13 = False
_CROP_INFO = {"WHEAT": (2, 4, 0, 6, False), "CARROT": (2, 3, 0, 4, False), "TOMATO": (8, 8, 1, 4, True),
              "STRAWBERRY": (10, 10, 2, 4, True), "MELON": (10, 12, 0, 6, False)}
_V24_STATE = {}


def _v24_inplace_fill(obs, action, seat):
    """tape 给 PASS 的工人：若脚下格需要浇水/可安全收获，就地作业（不移动，保 tape 位置）。"""
    farm = (obs.get("farms") or [])[seat]
    tiles = farm.get("tiles") or []
    day = int(obs.get("day", 0))
    units = [("farmer", farm.get("farmer"))] + [(i, p) for i, p in enumerate(farm.get("hands") or [])]
    orders = [action.get("farmer")] + list(action.get("hands") or [])
    for k, (tag, pos) in enumerate(units):
        if k >= len(orders): break
        od = orders[k]
        if not od or str(od[0]) != "PASS": continue
        if not pos or len(pos) < 2: continue
        x, y = int(pos[0]), int(pos[1])
        if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])): continue
        t = tiles[y][x]
        if not isinstance(t, dict): continue
        new = None
        if t.get("kind") == "PLANT":
            crop = t.get("crop"); info = _CROP_INFO.get(crop)
            if info:
                first, maxd, inter, maxy, ongoing = info
                age = day - int(t.get("planted_day", day))
                yu = int(t.get("yield_units", 0) or 0)
                if ongoing and yu >= 2:
                    new = ["HARVEST"]
                elif (not ongoing) and yu >= maxy and age >= first:
                    new = ["HARVEST"]
                elif not t.get("watered_today") and (ongoing or age <= maxd) and day <= 28:
                    new = ["WATER"]
        elif "animal" in t:
            if t.get("fertilizer_available"):
                new = ["COLLECT_FERTILIZER"]
            elif int(t.get("yield_units", 0) or 0) >= 4:
                new = ["HARVEST"]
        if new is not None:
            if k == 0: action["farmer"] = new
            else: action["hands"][k - 1] = new
    return action


_V24_PREV_AGENT = kaggriculture_agent


def kaggriculture_agent_v24(obs, configuration=None):
    act = _V24_PREV_AGENT(obs, configuration)
    try:
        seat = obs.get("player", 0)
        act = _v24_inplace_fill(obs, act, seat)
        if _V24_W13:
            day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0))
            farm = (obs.get("farms") or [])[seat]
            hired = int(farm.get("hires_today", 0) or 0)
            money = float(farm.get("money", 0) or 0)
            if hour <= 2 and 6 <= day <= 26 and hired == 12 and money > 700:
                mk = [list(o) for o in (act.get("market") or []) if o]
                if len(mk) < 10:
                    mk.append(["HIRE"]); act["market"] = mk
    except Exception:
        pass
    return act


# ==================== V25 market maker (appended) ====================
_MM_BASE = {"STRAWBERRY": 120, "MILK": 160, "WOOL": 200, "MELON": 250}
_MM_STATE = {}
import os as _os
_MM_CFG = {}
try:
    _MM_CFG = __import__("json").loads(_os.environ.get("MM_PARAMS", "{}"))
except Exception:
    pass
_MM_BUY_FRAC = float(_MM_CFG.get("buy", 0.80))
_MM_SELL_FRAC = float(_MM_CFG.get("sell", 0.93))
_MM_LOT = int(_MM_CFG.get("lot", 8))
_MM_BUDGET_FRAC = float(_MM_CFG.get("budget", 0.25))
_MM_POS_CAP = int(_MM_CFG.get("cap", 24))


def _mm_layer(obs, act, seat):
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
    st = _MM_STATE.setdefault(seat, {"pos": {}, "last": -1})
    if t <= st["last"]: st.clear(); st.update({"pos": {}, "last": -1})
    st["last"] = t
    if not (10 * 24 <= t <= 27 * 24):
        # 出场清仓：把持仓卖掉
        if t > 27 * 24 and st["pos"]:
            mk = [list(o) for o in (act.get("market") or []) if o]
            shed = (obs.get("private") or {}).get("shed") or {}
            for it, q in list(st["pos"].items()):
                have = int(shed.get(it, 0))
                if q > 0 and have > 0 and len(mk) < 10:
                    mk.insert(0, ["SELL", it, min(q, have)]); st["pos"][it] = 0
            act["market"] = mk[:10]
        return act
    market = obs.get("market") or {}
    prices = market.get("prices") or {}
    farm = (obs.get("farms") or [])[seat]
    money = float(farm.get("money", 0) or 0)
    shed = (obs.get("private") or {}).get("shed") or {}
    shed_room = 100 - sum(int(v) for v in shed.values())
    mk = [list(o) for o in (act.get("market") or []) if o]
    selling = {o[1] for o in mk if o and o[0] == "SELL" and len(o) > 1}
    for it, base in _MM_BASE.items():
        pr = prices.get(it, base)
        pos = int(st["pos"].get(it, 0))
        if pos > 0 and pr >= _MM_SELL_FRAC * base and int(shed.get(it, 0)) >= 1 and len(mk) < 10:
            q = min(pos, int(shed.get(it, 0)))
            mk.insert(0, ["SELL", it, q]); st["pos"][it] = pos - q
            continue
        if (pr <= _MM_BUY_FRAC * base and it not in selling and pos < _MM_POS_CAP
                and money > 3000 and shed_room > 12 and len(mk) < 10):
            lot = min(_MM_LOT, int((money * _MM_BUDGET_FRAC) // max(1, pr)), shed_room - 10)
            if lot >= 3:
                # BUY_PRODUCT 仅 WHEAT/FERTILIZER 合法：该单从不成交，只作内部择时状态触发器，不再挂出占槽
                st["pos"][it] = pos + lot; money -= lot * pr
    act["market"] = mk[:10]
    return act


_V25_PREV = kaggriculture_agent_v24


def kaggriculture_agent_v25(obs, configuration=None):
    act = _V25_PREV(obs, configuration)
    try:
        act = _mm_layer(obs, act, obs.get("player", 0))
    except Exception:
        pass
    return act
