"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>Pmf*4amBxi!L=3|k&>wFC~_PTrZogfS#S)&Fc1d;0%zf57x=q}!<l*S-oC%8bE>-EFaomT<Geq&tGlYZ>eQ*~KmE^>fBVbd|Mu6vKl!KM{OQTt7w_Lc`Q?k>Jo)#({O7;^*X^Hf|MR!M{QW=v`ro(z`_q%}fBNH}-@dzf_0!7_Pd>i&^AFcAZeLtI{pFW`eDRyzkNtS_?!yoHuf4y1^Je=q&p&?P?iuf|uU~E7`S$S6@2}t7{CNB5uRgu?!|Qj~PfD+Df9%DNuYdpI(-2<X{QU8sui%~cKU`nG{q){J#GkL<f7na-aSmU<{M}D)AAa)F?>&5MGbh_W4&P9dbmfg>^QiL!?qnH<vU&OaPp{v+`twIU`0&&1Jh{t%9Mao2FMj-RUZ-Jj!(;Y?y!+L0WGKYPr@Xu_%-qB3dNTa{;=}d3!}{(X87?o1^YR5v>hv&S_3xepEBXbl%~puJSE~n^>%+zv9;SD*%BOVz1A3G--#qoVx7*J!V=%>+8Qk>?*l%Dl&#RwL?D*Zs7;m<i!vx=ba`m7dCWrM8$2898a^pChyS%R3{pI29&Gxce>||lB9b~gkxL@!x(vo><ao&IMmya*SLl(^`eP#UIMQ8W;a@FiUd~l~YpJr`lYBzIten2|2+rK%FUpAk2<Ld}}|F>W|&u{mqbNGpT!j?a3JDnF2CVZtHaCEHV0K<s|JpH;p+6sB_-i`pFQQ$G+!Q^d#4+rV?8Rx^5x7NG&#ShZ~n);iY2apGRe8A0{H`gye{Q0-n?>@YK^ZH+o4jF$!_+<2@#$I}Iq~eF4Rr>wSPsgP?I}Dqj5MBcW*!RC}crvF?2BV)J-ZS+0X`ZZQJa0dnq36DrKUN6jY1cZdbSJE{9<e!rHwV=GVf^ad&D-%%I-CB2eSAA3E6;~ZojYWj|A&YBYn$E+xjz3tT>P=m{<Fg#c)R;&PFS)-SFqX<68`$Qjg!lhdv0{56cGd8MLPloa1?3h2O)~Gdx$=$`e`o$rDaG%d4JTj6vy$k;$}VZ80-l|(uywF52y-|Yd<dS3iam^TR*I4Tnyiu7xa_2ekJ){KfHMN2S)~)^z(A!!WQ8pntmSrY0N8?e)Fh(7;(TNJPQ_>@QeXa#4#RDfhL_7Dp>g77<+a)p2k!n!MtN?P!6lFHMqUA)fQETe_5dV9@I9Z*5uGdoNbv>?hu)Z_gIeB)7?Wx4ejN?4Zo_6h!u|**KxBCG0)Yi`*qc$v*OJ0%fm3%ndgin<~tj>q4&K#Da!5?G@nyB1z8}>$My3y(V<SepzErLBO#GsnBn44gsOs*n9g!TSJ+Dr=GHtyq^h9LCtRlqM^-qS$1$vW2*On}j@r{-!mW{>Dx!_RVS9Qy_Y8;4NJN}K;>`+YYS);Vcq`(UBEuO1GQ~ts5Eu+7TW3!?xOHEU^IU$GUd{6lo)L6AtJC&2`%frjjt9=#D5-kT!4v&@_t;Ux=KRm`osSdw?j}freP+n-lKx=gfOah!%?%S>@{!vGdjH|wi=V&0e)sN={8(C~jcFJB(6(QXLe?G9!s(C4m-iUK=M9!=1vbl`gX>}D6Hne&!=0?4hU9CBq_cRsNV;z(?VxdFK^{L)*w0zLj$S}x#n_eD{56Eg3M9;eXSJh|G4&!>A%B0&fsVurUAwmI04;St{2yMstV={gT2B7M)9aK!^XxBHF+L21z78Mcf{7BZMyW^7Yj?1N_w{JNXYOvcGtA_F0+p$Te~zP*ghSi{Fv)%~-xi61zKBPsEY+mR17QtNie)o_Z?NWxE#Is9kk0C^cZ1p8hLg0PG&IPAt7-HR%1n^+S<J=>5U$_J(b?Ej{)Q4<GALaO7O`cT2e9`pen_AR9AZ{k3WZE6%H_E<_!RW<Da&sw8<w{nO0H6cYOoCQ3Pp}LVuiL?HYBI9V@&7?Z5RTaKkz)oBNUS*^L*`x<W;ZWP4ZJy7PItDanmu0+qqX>osNqav>c6NoU3|X-}QBme%c9ZU3375suolj^!|^ZEu3RK3re8PPM5ppPYtQCZYY(=Gk+>brsq4K6VDIk1FMZ;1YA&28$!hq#HVa)ks9Aqo5jO6`SZ=qtu9`DY3!rPlq4)IV|bgmY%`o*$&A>TAKw0WXumoeTHIb^^9+T_2}hicSgLx7KUdgCibGEce>60di;&QDGGtXzS*c}!&>pk28$q<e<#Nr112jskR>t)ZVO<4EJk%xzstq-a@F(PE#Pr<8W|k`No)<KvnYsB$P(GOvyXN)V%pISVIt)O_aE+qStP#uh5vHhK@=ZrPY2~i!8&Cq(%?3*3C}AAcsKBuX!0{;Y-#9cK4{4+KL1UC|BN{=>F5_YxSrg17Hq`SN4lqY!I&?+&3h2!H9dl7>B2m4Q<`uWEB0#8*%^ZrZhs`c`P+i~TVPE*pENzcjgXa1qgvE)44R&bS?GRZxjVfA4obJ-1`-e!WyT%Y*bQ|%hblmvPF7zm8>)569ns1B~;I<VsnFcrr|Bo?(;(TX8oyMV&NIc(kdaX@fo{yyS+vitFeo76Xko(#^FF2mgpWVFDVbXG}Wasv>CmVh>_`3sj6o9;C*ny5m(;!yyylVkVCmR?}tfGX4Uz`@C#HttUMjG&$x2)r=tPG;NDq_g7%>YD#XvdN&FG1Z9Lr`w87!f)*+}0*DFPV#5!l1=73;W?klhWs}s)=%mzVf9QhhOM(utI+(&D9c9LRe_ghwoQXlPYyh3H4myDKiQrp2u_8Zi^_wd<-RXpt7BzRa~lU`bTx~^Veo;SBj)FHY`rcs_8lZ+QtVw|1Eaz9;+86y+XXH_<T4*%|*U_#G?eaGdbz|oOwVa^)pEw@stoEk*$J9+DLYINHL3aI^cf)`pxe?{`<`^G78e<DGlf6=I7-Zc~-vrZyoMA2=g52YS0Y_51#t*o#gHV)dfs=d<ZcjLTACq<K+2CAoQd$#WP$$@GzH(W}vc(ZQuo!5udhfT$PEf<fD!*rZ0#4Qp|9vG!x(wzOR6xa>+L=<<(}CI;hS|0@Gor(4JySmAgThC|pc`W_r4tsn;Nc$#GggU|*^Gh$o37S;wh4jkvM`IncKc{*LyV>b>X#WO*2FmpJrmW2`)$+7d;@)ab0mM0lj*atA$aRw=7r?t(dJW8*0<Kl-~OXD+fiDyp@+qa^GM+^OB<L}XY>ix%XA#8R7df4PNC>uHwIPAIa&+o-wwgHILs2AKXt@jLoGIvu8HGu6I)RzpaGI+DXQvXrG)soT(~P1_o=7D=<i=<P+-46P*pC!JnW1`*WYTEz<w##t%OjgXmoajmRtIL7TQ)-pDvOX~>e-Q1NbOFHKYQsSS6wTbKKx<OYGFBLBn{y0KOZY~7Dv(q}0`k#AgYEHkHK+#rYYOdNOrL4(VwP|A%84*(`Gn4LfjC4ylmJ}2b%l9X=R4!onC|<Lt!7=F9=_(Q%$BZfpA8VGLt16=NExjrHOsA2X&e%+sujV3^@1_C<uTvc(5fQW9o?td~7X<A}MlY|eqBQ0ut9CYXr1S$l*^5l91jeY+0*PAH;3hB~s(lMAr=+39Le1QevdCAP7FWE}Ox8GT)fMlVlCQ86JRU{%#V6;5hQ&Zo(2FRz)-$VStUofr<~v1x6fCplyEB(kDh-rQiUXm1UbuD&Q5&-zNJEzjka3N-)P-}tv;~7f1&L9Mm9WJ5)npH{{VM^^%A~KZbJ(ZEGr)niS+`)LA=`!Em!~9W`v#5qu$WMpD#xG|b5ve3Yb#iw8erjv7BUZCVcJIL)XsA`fCge6DD02hjj<5%=ks1=`(^5n7v19M(dfjH!(=-Mt46GX5B#Vg{kzSSg#)E~gUO2mBz$*wgZcwwZCr<FquhThGFa?Hs(c0<SwO92A?zBN{nvs&6FY2=gdBoCHEUm`Em~ntICH_{Wuw#L=TN^!r%l<fz`YfT8HP0V;^z(%mGB+sZpr{)B~5PcL0Fm$x4nM0YBUQlvw9k;iDVRRBRmV2-#l;Zdr9_ZlyQ1d&%)jf`{fN>I3kT0s4AOj;<{K_^eC#_`^zdgolc{S(f<MsmBi}lwM(1uFmXdUofQ-Gyt0vX{)s=1N5p2=IEz8uY6Sb13$~<SCHlJyE>Lkv+P7yj3Asi_?9$3{I83fuNsvVl1$D~^yct6P)WcjghE1p+l^xkj5X~^9N$*}odX@nHSgB+bKt-<vjD<Y`UNjY@4Vi_btF{4H!x|b-pJ&;2@ZffhfZf%xsj1uV^t(F~T94uB5W<DE#wnZa#1i##tdNVgi*#PPdM?Xgy*pjGBrM1@U~;hY7`Vb<GUq4<EhK7n-Ul&xTAICr>~J;<4o*%m!!wGhBlf_pl~EwJDk6-SIkK`vW*NutYC2i!zlA&Rom_4gzY-H7l!eur!#axprNMeuSrR=fr(0x{8K}Ny{m>wdO~TM^Mf4H{AtlO&&`eB7l<mq;b%=pQ^;0!HV_brv3SagHROnzay-o=7VLa*VnBuZ!Bw%DGsaO~uJXRL@3?||!`z3{!TZz0*3WG^4K>qzT3zBcJwdhiGEeWP;;VSW7AU3vS>xuj>o0KP3MEdtmFMi#RIX#A0HzmK=D~~|m#0D=L*ObOvce^0LYlLHt4fj8v)+L6|Kr^X&Oi~R;nQIIrTg6}ni!jg~0$UrW*<t;bX*Uj5oMqbJ$MqWbNCU3pj3J?KqR6t>1_>k7wlJtXHmKMs_!An_T>?7nMtrUVvbnEX9eCq5N->Kp`fOehSE<bHWEn+Gyj{1K$Cw@HM;BGVslKeb5P&vOt#9~575~ZAg&1(UFUxVunh7S^{Dj7dGEgJjEAAfP?$(GtV2GwF@<id4Gs3{ONN<m}f9MgVT8ODD+z%smDd80ju2qSotRkVs(Vb#idDY4rY{Oy~fdJX1T~y^~O{xR^O_7gEFdvQBBDG2o?+~Wc2RyCDmAFb(a8^#fJy#)F5iHe{VyVKey#DAAqzUyWwLvh2PUqEFn<yHoC<k@|NC4@^G#OQw<aSr0jcAuMr?as2V(XK@Q6o4#YhKh@b=r1w-iW#$w~A_^>w<1U-VF!a%N)U-&LmYd5EH73!)6|#L}8Kxsu@ShS`ofqjr${t>j*%w2tkX6*9rRTMReZqFcvO0Tt3sNFOL^Yp#*E{&!TUQb45bfH&LaoAm^^q0q00Ur3~8#H|PLI$0Tt6Q&^!gWSHPew;V?FRU4H?OQ4m)qybenD#_g_kW;EBaz-+Uk2vNgiELiAYmP|CMcsLGkbNpSSL*bb=dvOavfW}wNT5pKdB~L{mUp49Kj-Qy_ngM2$OTE%CC25q!jFnjk<!Ga0d|JpiKUDE$?`x-5DIJXSR4Pale86_!zdokN?7VrP#0OwM&LOp0y!_B5?YV_yK@SK>f%CbUhV8+Ts5foXr>D0HCcA7C<Gt{mOb0sjk753@+LZ0(L7lboXnzSthE{EYRQ&kbDJn<|9A?@8;`KLyk^KOi_7DAcC8Fgs6vyuRNyb2XeO1IAb<!W`XGg38#MrniFrLm-bv5s@pnHvmjQ!|0GrJUjz*>emm1ePwj}*?!pn?0_yu3Hq~bVLK_h#oMB?6$BB@hr-U<z+O1Oo_BgcLZcf);p_yA<Ig~+wK839FABS#S#QE~n8RxTl6Qi^N}n0KL$3jFhxBK$5dc|H9SI7Ig{+2?tVz>P$cLst<&e23~+;6ZFxrI>VOREme4FP;G~q@P$MWd{kX8I|BxG%P75w8Z+z+nu_ki1TbXJ)&wn9C9hQFM?bwiR9p^Z#`Amw*Xs5J-{wxAys3jb;k<aRf@Jq->k^b(03k2NCyxVA5}EFq}};-PqCMVYNdU!B912FWW)hVz(s-`i-G%_xC){pUR<F*siUOr)R3^O3}jxZxg3w;9xQyBA`UM|SNZi$p|a}o3qpq*LlsQNyj(=(J8e>Al_J9+jsV;|NH{#RVkCmukA=IcYD!I7`v?UrZ8l0t!p69})RkR$mNcRHjI0&tmZQ1oq9}k%E_9Qb2=sxv4AG{5a4qVno?#n#wU6fVu*c<BqnPjkN{#JIiI)?w3XIx?i%Nn*38Ha+V}ZPz*azkUPi*4=88)QJm=*4Kwd7a#!`=a;JJD*+8?Izp+$DyNvtL4P5&JFm$6Um!i6=IXNOJ8L8$x(>)_4w@C41<W1-^b;=Y#Hw@iaAr6N<G91NZADF$~`xeD=%v;t5yXn7}F0=VT!UFtR8zA7=X1>wix7_1rKN5GW>Gxg@ARGIrg`mzR)F8BI#H?20T~dC1IesRB#E%(bLrM*)R*haL*`%f9bpd$?L>OfuYe#`n^T_o=`=0y?vciw%KnOu4@nam*D2qhb}O5Kpyy?PESgR=NX)bSuzf&!Nbp5?PX@JBrxNRaX{Vn*bbEME*>9JHwP<bncXqg&4KSHBRoXA?@>6fQaJBZkfJ@SY$bDuxmGd`+E8O>Cw#g+7!o1X7iwwkcfxbtX>-~6CbRsl$9DBf9bPRq7;7T+=Nu<grPB`(G^(+mAP;QGe{~0Y64<Qe~%)#q`XX=qzT8!cGFYx1__-zL`j9cVR4fp5JMojGpyhb;cE3TLD)!S-y(r=lq!1^&$nE~gI;xS7|~{gz?H0_o9ewH_d2x_WF4{hTAp>nkuhP<Lk>NLiX(*4K)+T^z(NMMsRlzuFzFfx+AixmJU>R%x2|>&p7-;@e&FIa6^aZ&m$6uDz(K*-11vzwq$3>^wHPL19IDY-agfA69cd%B8^0>nL=|h}pYB&88AHKCI@&dYJv*?fgBb`3sAwr6!i}?(^VC$;T@?z@1x$hob^!05XB$SIxD1I|dFtkYnq1{?ifc;qeYK39t-=s8j_{=E=w3#ss3F>t=R%HI9hVGE7A9+bKxKFP?fv~~6j6v`T(;u^zVM9Y-u>}hdr~*y9JxE?m-O<}Wqj#of1Vzx&MfWrufv>GtL*X)4Z-aR`qr<!QIubiNAu8;xI_+%Ot-={qqgFH(PU`kxop8rc{_OLyZDoJ<j_mvETGYScHEGnOFSS&ZRDYRlwIOxG35>hyEw~EmyAwP<H8R%=yb6r=7I@UkQ!8xQztTOU2#N$$H15fcq1pGni>>Dn?4_ofg}Tr5am^se(XL=LXK9E+6o-Qqi50;#>Sp0LK*@~-8RUo5c6HlCIZdCU=H?I+6sY-E<(O4r(=pbG~H&1%d0yj62%(V0%YxD9?{lVU>L_@XblvEJTctL#ZGY<<D%t}cu1gza<>ym+!SfIe^6~#A%eCIn^mpUX6~-?SwM`rMX*(nE{wO6-r58Zciem6>dSF>F7ujKp&H|w@HN*BfW8lkC7MIB*h6jO8VRg}ysPmBA9>Akx%U##&a3ul4ciA?v|?ZDx(wXK!|MgUmoW-D%8jM!LgcO3^M>7xK58a;zb;3miM!}KCyHI6vA@`r12p-|WH)OyaL3^~R~#`?W)+UK@JF1FZwv{i@VOqdk7W9_;dPYu5m-|S(%EH@ht17t+V1qfd1g#T4(e@xR4uru%2e5}3>q9!PfZP^)sn?)16g$|d_Q*dk8Xiss%98RR_0PUb#N)7M+`%m<6>MK6VgWe+^IZmp4e;LD`~WMx8S2wm51&VR}A*=pT`&m0|&8TnI%+CQAZdK=P3ixBeqsivFYn3>G-^8y0?)w5P34~PM~OoYK^>fwwpIYu9-Hv!V~>-jVK1MF$1Adp=!5R`1Obri?sJO@}R_Uw*_;zxOSFXX7}6*I5~=JT;%C_CCZv@L*o_&`3TMAjH`5OSjBczSYT#H<PqufDDy8PBkH8Eqa~a3^TZWIm#FzrWJwyZI?uZ3wIx_9Gayr*g!167AenI!#9Rq-#a$!t(6L*M*$q8R`e45Ggz$ZY{Fr;O-W{UL6?y>9C#_$>C``L1Mn))Vi4pJjRzoYnR&oUh=$Hk|9^+G~d=MBOb296eGE{rY?{)l{b6(`M0g<`%7kM`_XqZ6eF5qIG-HGs12Dy2cJ|*I>sv7ywd`~5jx<$tEiCH1>g?r1Eu=`k8<)S)X(OxcxBijL<7`&?athYDJ)5e#QNb+w)MX%wOR*KKOAaCcVl?Z#KB40j3MYf{iYf~`vAVCo_(d1WApk;^LA}i9V{lh8Mo&Ft=NVV5?new5CmFo}C1;H&~n$TCSf^4$JP+yJcy-#Zl846R*ckNoosMvc%s>hU?D56x*9?gO{2i$g5y86^fO5|jY04FRG%R=j7n+fv68Utr`zJzBJtW*ewrW7f@&NFeHw2bDp0a`g5iI3M5%j!o#E@Ls(WGEK}h00n5IoNd(C-ex%FRKKNnt9>2x|Nl2!cw&m40aXmb#lJ4?ZgU*(h)V(K2BcAT4<FNw-UTAXL0KxC3R4wocogHpizd3^bC%(xR|K`NZIHlk<Re!$IZmgCK^qAYy~ZflX2(_!@}z;@`PjMJg)dm3Ukb>e2JGT>uqSxN_ZX>G$&rMsoh1<g9~nGMvxh)FUau=kmMr%+9;DE0C6u0(bvc3*?|TgdAxh{BG9ARU8GV0KFTZtH~02&Mt-}ROt}JPypXfapG4$O9K5inHnMba9+o`ri5_dtg`h$jr??3-!Oo2#kt0@gZ`~67b+m>G2C0fY8_;TgN$K{FN@UtS%8l<dWluCQ@M&sI$;~ZARqvw*S4C$}eSMD4h@?(K54$^)+?RrN90aV~&_{k*x?%OMp<SjlNj%^bLr2IBbFc)b$Uy5hPpruvi&<ho(P3+_rO1bfBK$6vozpxyt4BEr5=A5m-BR^Bqch%hszzy@u)6A`ky47$`Vze<Hnw0FlemIB$a8>oO+^A`kZ{wmZwKZq?%_doX~@J>%Tje=xc2&RBdn4prKLIiNHR-N=94&pYQ(xBXm3JOwj|HC1*RS+CDJej$cQ53+>;JAfS@@8u2j2wWYuDD-RyRkd0XMcIkC5bPL!VY<{#_{hvbm>cvTPfFl}Kj>9QTZs`6l`IK^5#;3@|GZE~LmT})Hy#Gq;&dZpta+L1sz{?cbhK9S=a)Gb#oMk(I@GJ=6Fva+Z^{O$tkMdt!;oR}gLl_~JI{P1?1-N4)^xy8fBAVl)`+9H^|be*q?0-9P7;!EfD3keovEsavPp33BkR!Cudww>q}h`eVf_xa?=MkLWXe6wd}xx0^XN8W(khx#<r)Fkc|EwNTC;dwZG>>o8n&c#Awt-KT$b>xt@yUu-cjj+P_MjFi<N#|tQI+6JWzB|VUh^J<(=grHy6g~3_NMxGEAq^|ysudvxgnEru5aF$#VJIf*%l*<$PZ9Tkqq_G}w$@ZhZR@z#^D%c;)?~(|M?Z!QEZky5qQ*gEEPj3>uD=ZlVy+KTIPKn2|6ry~DzkJWSgv+Ns={vt@~!J*%fN!jj|oVWbuiLA;2e$lwCBLVV$5i4>_ZTwD27E6oWPRoP8LAcE6f93w*jm=qTP_t6sfDMhVXT)MP};jUgQpuvT|pQ=#Xg~Hl$E)O-)*$Ke6&w{7|{<hL0)5vxS)v`eAe~aQPUGi*($kn-<t#(T3CN&P)Ak<D?3HW!kc{#7PyY!$uAKe80|WQ_j&F)GbS8M>_~><BXrVt(Qr(IpswiwdhbKM_E@2!IC8)TgKltioVek(wA_a!*(dGQ|()nHb#&OuCNt^lR@!eCK|I8VoE_Wix$Ue^XeS}By@!T)LJpI^PhufKG2moK*brz>1hW0#OIvoi@QHDQZFxarD375*BJcB8mK*6OLSp&u8Q(f?#*Gs;{WuRn5`brk`EVd;M)9Mij3-aVp6k{)b-442;`L93E9IL(|P`e0E7WI7?$fj(PPKhNeXUHYXkU(7P{6@g=UBsG^f2qvvDdusNb_?Yyuo7`U->7H`6s*L{|b7aHeAT?RH^xn`SFw6A6*hzL4Vo<_S<g{=<B9dO2a#D}>N8^4Z(s6bQMht>z>(R~%~wq~4m8Mjt%I{u2n-Y4<|L;W||nCWiygA#8y}imR+dV~RVcG6CmItU%E)#bs6Occ<SeHAdZvcanKEjThIpdAn65tJRv5uW3%|-5hAGZPZ!!Hdw~vtzyRrhbC#POJdDU#&2?2d4&eds9Rl@cE?oE({wqkEg6%h;vye!=0ry^dR5|Rnp+v{(YZ4u7!8*etFakZIZi%7S`<?VdTqI<EaLf^B~}=FO4GAe$aHlAaHYl~VP}Gh-_uw%k}HN$a;w2*imJh)qfK3>PNwN13ipCt&X|mrBX-G=oQY!+O~_4+)bgC8VyLxyzbhh9n-yEIIaTlxO*TbJh!kAd$RysBUuWAa+HPB2E6%s9PD&?;&N7oX?yTZCE49W&%_){+a=zOFG1gd^gp7pEsIz{Cv20oxQx5Vu)b#>JBCWiQ_Y5iTtHF?<s0zS>xA8lXF!gpY#a_eOn#`nKL@&>g`zjm3Er34nMK071tsTR}-qe*W`Pm!wc@(U6!LQQ<_&J&K!#KWPJan0`_JP13L2xgKwbb8Lx3dd6zmIs4fQ^<)&CaTIvS_MsUI%0PT?zax;I)def<GgUs5@kjFu!l_g!&BEE{$aYl?#!E1unEM{URRF)A1OY0up`ru-I0ch#`3eziR84qhe-_lIL|3odXdsu2PDCl#2+k0}rg4hG_H38c@)Tgq%1*f3tI&MU{))F9Rp5VG@OP?aP>hEb=8<R@`kO7Pe2p+}xQS;Gg>xX+z6JA5(fegxkg&be@m1w}Pfy&AhnUFZL{PD;37iEP0BX^rs-{uV5O-6hCdn-5UnsErABCsk`E-^X(<Z*n`bH<UniOz6Dp{o*^$}&0P@O6%}+7tZNBi_ibW^s83a!ltd7fCkV%g2(`~aZs>058jo5N2-FbOe7d&lxzrHU<tqDrGZ6s&L<U<$goO<!%u?%WUe@Q3fi6__G!Om)PoL{<Ga0gAu3#!8KqbxKK=_mExzbjx<5%=>R_w*5!&Wp-T^l9n4r(I`pf0nkwPJ(E(hBZ-RLO$*dP<C8px9E-xY)fEIbeekguHES<N^Vgwcq#sjiXSdH3_CXR;5I0H`jPU51BAZWFaHkYStooNtz2b4k)y5wNTkf#%5ASa_6xVdV94BzFkDwL^4o-!qyuhIrrRq0POt5F(mUgd#JDF!u(=<Lsf#;M$?vvJd?VnO&xp9icV8Pw%V;)8eexW01;j9=|qU4RQa;7epjAe8r%Cs;h`$V6@~YvqE?$d*wN(FT5a5&NRC!1Y{lTvP$-m>8G9rE`60K9F6W>MibD~b!~Zxr86SV(-OW)UYM6q%dQBVL@_S@FmxpSSW?Z}Jz*O4YBBv5YvdVqC!1>&`y#^~b=sLK{EJ;LKORw3W06$d0nnAOrvOZo3ch*a`1O8Sw`jRnZ1$wNS27?n$R|?6i^U-77S(F5;c!snDoeFiZ4gWH{Rt<W@b`07m5T~r5YiLTfW}S>Z70={Ci-d^Eo$4m5z1^cTg`v{uOq?Gze;I8p^SYEgb2kem6B+BC`~kZQ%&Hv%Sp^6<;rx$q{f=qy)Dnpxm<AzQZV`AOOG0qYCpMSMPM8#Sf*x;EnPfI!dnw(8$?4UVSJs!sAiF@}BUf>sUs>6U;_XW#*|J{Y9erz@zNI}u^TTFHpi15)Zoh(>4rr>SFlJv2=`f4XKo#*-OOdDHNa=bTp?Cxc-9EUtBMFc(r@ic7MV|#X%~BK_Ck?9{qlU~X?aD5JU1A<dciB#ss)#l?)73p~S>n1cD5j@tUEA_nJ={KQs)2z_#}P4^qsJ(DoEzs2dUsN`7wbgs9p;AbUVU&?m>Qni*`mT4TRixLGOx<6qK(IHlUco@UY-J0n3P=il_gZnGsG1=YzUJVFADwd;7gh)bwD#h-Dut+Q16SQtwP<otSGt_rrw^2shffhoa-3l>6b^UGAG7G(%f1lr)0Fu4JK`(T`C_Q!m(FZuCz$?Gkrg!w#OmV^IdHE79&#h29O6qwN}}=;W}QgnSQQjkHv*%s8bzAse{_e+6yJFp%jM=%8-9hFk@yCXoW0<d?|~^(><YGyU)}PS`OV)A_K<Na4T)<dzZnBQo-_-b96?m!aJG1Dz-@@`4pM!{b_M`JU-F|NI_8I-%kHctaQf@e>;34sqSr@wz~jjjv#qj3UB9(7@r6eq}<U0qL-g(J7sd4as=97U#LyaquJJ`hxuIQy6j>(2~<U8J*32bQG^Mo79t&xh#vD2R55m@_&$pdkr|Q^@6@6T>P&U9>SBw~1=)`BJp%V%W8`kgq9hpujd2CFJ<;5^DHkVw&e5+(+FoIN&j!ui4jFKH<Z304M5BkZG9LE|bTad(YQoi|fs(1L+7@I`<whVmzqbbF2BwX9U+gE*Kr2$_$9Ha#n6!FS4MnJoV7xSq*%H)5o6vMhY&hP!I<*mLy1~5#9>Z`RqaEbSe6x)m&nchjOE81C!W^qyG?NJjJ4ub|OJTLD63Nph4KYy9IN8f4ofYXGMl3MI#j1vNy-A)rKlGE^U;KkpO}DPmBG>G+1qkM0znQ*n*^O{mo&ek0GJf6XrxqK8d2OL-!E1)CfGKN1B9NyHjul!#*0Eh2rLyEly)FFYgl!Ui+=M!Zd%*4*#jd+-<6J|=>h`X3jPObn#Kuz>iGOeVX=(G<ft1_7#)kh$qFc-sO9^s8RnQ;o5=}CmI_pzbsIvN+V4UpAk`B&Ll~kjHt!3)0h+nj!OS2(rS(yVT4TX{lk<pQhQEPZ_G4)KTTjYGXEI9-dN!#d$ucSdUQdVNDMxHoMQX`jK7Nspd&7{+VNaZ+2N95|OK^6&~1U@nxPl|&eMA3zpz3W#6jmcnC@DwyTF)cCC!7$X&A8xp6y>#32_}oRpY>QD-T11&UD3@mTSJ-tSD^&RcEjo)DBcXiyZet<U9YZ6gef3o$lIA*(v1cSRri0W%5?B|Rq2}mlLbr^xmo4nhEqj=nxz*Ma5TI0ycBJ!AYqhgrCeWl$s(gw{zm4^tQ@0GV2riQuBBuo}YmGkG(iS)8%XLE7#%5Zk8Vd&gx{sC#A!k(kBqKyvBqMLSvzOC|%iq1?;lhd(@JV`A7gvnk=l-2|V~@)I%TrJ;Q_X=rN4e+dd0D<X6^Wf_!MV+6#P*~OWD?}@ncC{CX##nII=`oZnur{xR8T0VO%My_&4!XIAr1M+0xv=#8(JzRFeUq@4wM$y-EkHa?XKR81!f<$$|PjTm{DP>^-efG;H#!APpD|Cp+F`Y{l>AN9n7sYkpzKYV^UL*f4H$Es8oe2G#sV)qt9$Ct5UR+1Ysx(`s&@y+ruA4Gxtb@TKS*Wh4a`P`HT()W{3s*5eblOdEr?mOkD`EANu7+>65U_H8dD=)0*=b1D#;mlmdmenDGr=wz%*_TeZD*p;+BSALdHti_epqGajN7D!CF`?Tvd+TXmSG@Ik4U2pULFbK_MaUAgC!5z6cKqtPcw8bj?4rY5ERvQ9cA&GTs(sCd4IZB+cXnvJ4=AudbrE{*uKS~EBe^NTGI3PYb;tD~mlkDrx0AFbh)1+D4r>6d@}^1u1yrYr")).decode())
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
