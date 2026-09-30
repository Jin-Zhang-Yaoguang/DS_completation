"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)VGmOZkwlck<m7}+hf<QS8IFc=^c1PCUJNp?a0_ekpQ_wKFxBhMkLUMmK&(o?^WTOTBgJUnFm>A#=+>tFu<x4-`V$v=GYrzdZozkU1U{g+=n`M1CP$G`mN$3K1i&)@#?_kaKEe|`MlpPu~i%OC&z=Jw|0FE8Fb`S8}SKVCoo_~P5A@8AE=mtX9D?B|=?cR%L8_V)Vq>+R2c^WBF}+&$#&_4Ui`Th9*f{B-^L=I0MDuD<^C){n1lub-4&ef+WKKfn6v`KK|wxcT+NKVQQ;Z-2bLe)H+Q!yJFTe*11e#Se@4>ct;^dGqj-pMLM*W1B_U{&Dz*TBR#*9Ggd-A8<F9aVVRYKm79Q^~*nh5QKNXd|W4U|6xdPUO)f&-Fcse!3~eu5AyC;$C2SAK0M{cbz$WmcGsK3ug~9I-yZgN_sDR2aXK%a)1pof6L$aZNwA||;@)g0arbKVAai-xD8s|@Zg%;!51>Ggvgezp{{Ex+8CDFI_%egLeh&5qHuJpu`NEFheT?yDn>j4--6vNM>S1wM{%}m=dM;Ov!@<k@y0tG4Z*R=YZnKk(wJgYHpU__LHqw@PVsW-V_{+za;vtLHl)f^4?xL%Ee7S0MA3nGfoKLGZv$UJFJ3k;@+3nw)$1hvYyYY1<d;hm!InQtRmvi`ue8HAKYP*~lnoRggJ>ckA#Sw-R3wZK%ebg25;5~}~u~FbL;=$w@z=wl$`;7D9%BJ=1eeuI|fTsTD<^kjZA0Ke@`t|jTcYpr<_3gV?uV4N1(IMkc2%n6;)Uc%|M=E~!S)||I{Bqo?v%|3Y3E?$Bgnj?ph9`6SWH9>q;eCT1KdqCsjc4<-8G7z}`D2AZo~+hcq&s1q^@z<0yg8ue5961&H*dy6>8$z-?D%#?R-O-+I(JAl{|^uMx3;_&a((`PxcFnA{bvUo_|f`jPFP~0D_HFa34ePu<K*(>o*SJhMZ~~&(T+d?97WpsL5QO49-<Gbe%gybX&cf|-XAq>#c_PCxLGee273aLw4w|41F93qr60F;h4}M`tsmAaE{1Qd3;M}hzmj~fAD`d;lQRce^z(M&#unitT7Dk=Y0N8ye)Fh(7;(TNJPj6@@Qeab#4#RDfh3(bD%kko82jdQJdLSDf_cZ(pd40TYS6s1))qyEe_5dV9@I9Z*5uGdoNcL6?hu)R_gIeB)7?Wx3GL;;4Zo_6h!u|**KxBCG0)Yi`*qc$v*OJ0%fm3%sppI%<~ti`(EHw=oXYMLG@nyB1$jc4kL%}aqC=gmpzErLBO#f=u)@Wo2t@@KF<s?`tgx3JtgU&3NKrwbPq<DKj;wGtk7HQ%5QM8{9JQzKL(@o4712iEusuDUdxpbiBqB~A@n(lJv1_bMY>N1$$Z&>$Ofk_D1O@}j*0D(kx9&@Fp3BeDyLtY>GlFhsb=ux${|SZ6@xWOdXR01_@I=4eJ$96^IsbEf=fgtY-ULao&kXrp(jQD5(5^<Kx?!SAK61N3Z{OWM|MiFK+uJ|#V`-B%s$K9y+kQPxvhI);PJcYUyvGPWZ?H`(uvzvTTn{r}c=EOy?qmfuBwtG;oyF5d(tWdN2Z<vM^7w&5f6n4{^a2_?#;(NXuOUQMAYm3fs~wGusTa8j`SvjfIub8*?cTBjwAB6Ze|YV-E}0tAa`GRZ-lzPTXMeGZ@nI<RZTKJ;Oq6&v&U*B`b_Y9nUylZS=I&-Y!%Y4sP?>7@=Quh^I7AbGN%o8Rwnz;0r+9SAQc0RT5Y_;tST+;*25X+!^1Z4L>Fn-$H<;aRI7$0SLxViHnnoX?%mg`~r`b3G!u>lrIvah;-%t~m3`$pnMQoYo0c_jF4+$iJL(D2mp^!<%d3i1kJ_UVz%JSR7hUIOClB-mp8Z3jnLXqQ*SfDMI4b9WA7!z_r219`J2cD;RgkrK}p0E9oyy_LaNq%a|VwT=18Xc3koqOfg<+yl3%TYPTwW{a!U0?U;r=76YMF)VWYC(ZP@BjGO!a2sPpeD4jbh&H()R-044W%>k)Sn8H>G{s*#Pfsoz-nU{0T)!%hEQ<?@hRI{q{jD@v3M|(zuw$@l*OyB3_F@ENy5@HhPR2!HpA(a%m~B$@b-s8`{h~D;`SPwXDCcgIO24~Qq@cRxq=-j4m~CO(a>;SgoLh}Lsk`)m0AV}?J-NcnTS@nd|q?m0F4r>m2p2rSXY4(54DMbXhRJn{0X@kF+I0o%u?aq^MZynGdCXz$|o~o*Svh2x#P1?hXDvFu2B@4HDcL5!kns?eA5w6TDhzG29!W`vw;#hN*G5qDsZd;a6C%<Hx5n5L)z$l&={rLh(-{z%eWXv)&%nigL)pr0p@5dhpq@;0iAijV{R%fB#L*^yyD}l2oUOHGl!z<!Pw;vs_UCP*oE)S()O4&Xzou!Se)3{z(SL?LuBPNs%Rf^xl5bwA0nmh8bfr^ZN#V2apOC?(4(BKW0%frzA-L<+g8wI8sH%OKgI}(^PL5C8iz(A@p{wgwKjQqK9bIFpI;^UDK&sX?rZbB;CMQJcJoSyNz1X4o!iTvZ1~mS?+(;a0P>b$2Ra^2gILA$t_3WeY+$&siV_xnae5*pR=r?1(tyvrWgTZ_Wf0w65kro31|SkdJC;;=3F?Lzf^vh!h|sy=wl<l1$z0qL1}&ah*bgsSls<n|EtE_2l`q9O{6e3D7Wyk`?v_{*!a|Eae7};KM5(JvDCYuCnGqoIJYK_gTSO7&V<?#emF*0z;!<VHKZ=W=zcyRDQY4+RVR2DbEzkMaHa_6_Z?SXtSiLCe72-|B=fe?dZt}-RJW6molas#BnFlmdKa<p%o|=S6WUJtj49N};DQ1yQ2i#AuUjO04zrPzsMnRf9rQ!VC{JcCP&%$^At;0PBVV)!14Z7jr!BaoJliYovx_}9f4<SZG=qwm{Ts%Jsgq}2}c!moI9@bLP3{*C;4ZNT*;?tImtFo|_eALm!^ylHe6f0aR%>=lF?<-)aT=ES|d9@j#4yyB#z;qZYw5OO7<!%rr3K!F#nO^Q@>NN;qa-7x=*jLIv;z{C2)^Tc1Bd+W~4)pDVzoWjUaxeM-SssSlB@X@C7%PvLwnR}eB|2*{5gzHd-9b;ARl@3*yI>C5Fg(TWM}Jr3%tbawMYVQ!l!TpumfB5DM2e-PXhA+mY_&=EmnLjlPP2q|LXjQbM#<eDe5$}V!1O1I-_h^U=`cl`srKcw8bTV>ksPLxr7XQl-G)SM+SZ7@NSYl+Z!fB5XeIeS$@G#kh@b}7DqeU{&Ps7^gv`{7Yh_)-F>Y_Mma!pST1P<d=B`wErgN?!CH`qxo4Agy8+2#lrQ&76A4e$3&4nO%c3Edq|8p-*$>|ppDB6ll%~hMElqDIfHf@X|BVr0+X3~9*k!}gcl7b>)`Tl~I$^{G`#cTF7I0pSXT}5K!m{CRHW6jccs*31*OK%E4(`n?UGd9cRi@8YUyQzS|>r}@`M8s^jCzuW01wp%#(aUSAD2;i^s-4XmDfvK8_96=_fibGIK%!PPxCvB;YTp9QDM@ItP%~GgEb`T=#TD<gk~I!nb;o<E<O}Qsk4KSx@yU6iVKERC^dbtb^~$Oh>yJ#Z`A(4^1<S1Y?#iW<N&}^n(}7SvFI+o?sEySQW<!?>kaCT;)P-xlv;~7f1&L9Mm9WJ5)npH{{VM^^%A~KZbJ(ZEGr)n&tXr_rnA?Tmm!~w(_6-{IVKJdHRgOU`=BT`6)>g1VHNe6TEo2_P!nBRfsh#I?01d=GP}m>08{<jDpU-=h?YF5vUUZA2N23!*4wLO5tQxTjKJcT0^zSxP77mo|4JI!Nknr8z4eAe!wQ(OJL%IJ}q_EhDRQU`zvVdC4ldx-K_FoJBOzf~d5^@Oo)T(`*wrGVl;mie(mz7RWKZp7?I&IGV3fx<fm|;j$Z+`ADQ3>C1?WPm}cGBeb9wtkR;kMV$c8yj6R#q=VHIa;y+f1G(m)|^Z*u5nCGtO~(Q_qvV8}^GExNt-&F;G=D%fxlDvglD%x%anKa5|kv8KeIN5-N$+(|eaT;bG#2aylz2=y_!$>--ac9FK^N)i_Usy448wEf;LbiIwQ@F1SF&C28ND%_8Iy8L>+%$KkNJYA0bXf+(n4M&QjD0-zq&sxfRr{iy87-hya_DNTC!Dw4AV_{T~mqW~&;C15P<3GlorC~e3r99^{yz#7&NxQd}YxH{IroWhP{TT{2=>GyX^v>wINL4*rzjf*zhizVvjI7Kg#c`JkA?sVXi5Fk^2$(hdM-Q{d0RiKL|A5)^Gb+U4|f<TkA!|;G%-iJB9%2KN`zlb{{YfoezaQv<&e5D>%Xd55q<-yM-u0l8$7EunoC_<NNR!GppEVJ6SMY@zB+~spG&?ZBX4VhIGD^ZFuyB8R^IWp$7v6L!>gw%<K3ohstu5qXsh29a<`-JcsMskiN6xSRh^&va$#K!R8v8Ko84iQ7xFXp@4PUICz7{=)d<lkSjA-OfJ#dV@zNU&TBcZqF*Fl>qGiJT^z4kva*dfQGHeBB8-J%(5|C9~HnOhBK*h7B7RgvO@3T?*i}pfSgW_Rl9&iQzNEOQIgrL&H(#5(8;YF<8Oh3uK32&c<nW*uQ1cje`|unO695zeXErwC&|w9pPT0ys_7S2*XPce<DG#p}S65T~#`o6txa$<-Th5w2d1R#k{QOvw4YGrPlQdsx4*WPL!G3rEqP^iY`ZhQ@LK3S1o5ZT$hTQ<8Ez?_uSX5xOKmTQfz)g!!#Mt5L(q!@r`9v5hTD!N|mftE0Y4XAXz->?V)3mYN%Dd(0p1pYXuT1p{BQzhFGdSHHdb_0{Q?lC2OZrlV+Bm{-$_0CH#{{Z1FiIigt(-E-kZ_C`MH(3Om)h<3P_q)hgvBHHYX&EI5e+q7-y&t_HD09YjSAu(&-zdK=4R6cUn;TXEwf>(z(U4TLtjhJ)5opbIO=_E-lKTf}hPt8fuI8+f+o4PLNg$`Li`EK)@RG0muGS?1A5tQ<L@nsTH>j65lwMCmkgQ7=Z3xy5m5EMg~`UQh$ZL1wi#@Uu@3e4I#pD*j$mD;0ffT&&j630<}s+<6@CnV-Uax9B|to_89Q_e*YSu(j&a(danS7;_q%WDl48f&zh}dI)9-^Y~O@l8neqReP_9^itI0H3y8R5>2Ikfq7mgqO#hJTEq-gAvF)Vl92JPW%buwT?n4@sZ^po33SA`{D$gLDI;=mm|$*as~w=A*ySpZT?DhOhBSFlf}LHgKn6y=X;$?hhD=>X8Cu7KOhiRqbRvd`{hjkfzv}Wq0$g1=<0?9BeVM(M*X-DVS3_E5Pw#ePB?@9zh-jXx2+my5Qq(fDxmdF1*bE%XEI*!rvXv1!m)De-Wm9=@%ubWx<5b8TVwqP2`O0()Jb+&H*H>!pRP=8m5vM3N=@mTg!)MR9V>l21m|2<0m`~>t(^{tv1W3l!$!bT;`{Ma}9Tj=08VlJoBbx4R6f^fr8f7bJ8sm{;o&Vi%pB_E{xmz)1lLd~Rkr&X3fQ2fjk5?|qjVtCs?50F=%?a?zix%URKdqg8;^tV^$b>lbg%AX4s9!vgA86?*1Hj-9k1*dSBaTl$QJ+u;TdL`UNc>x#Wh^~xX4IuHoCLyYlfchqnMH(%C2Jgcn1Wq}J_`tK)J<uH_*P}L)>J6)>?jB!u~{XyJd7~qEa>`G__ids`7JrIlY=s(U6>-4B*I4wk4y1<0+!CnZ6UUdI8}w>l8%tJb0I>rGE{Y?<Z|eS)>SwVMc`Qwd-7XxLSfb1c|u4VLlrE!oa?Xhcs8M~O2c4mL*P&zQo0|Q1$;1>u5iUqO{hs~7gry&84sn|h%t8Q5xZC?>B#XJi4oBGSd)<j1)MlwPRET13xWCsQ9Dj>4>g$1LjJr|L(@grlftDzq~zJetg*Wzu|k6MxItcTlPFncaKuOiP5ZRhZ)6SprHz|nXoRNaRan5)Ro2aZcPQX)YBd)NH!Q8c>8ySUo<xAN)ckJ|*&|-qJZ{K^T&Q<=FVN^LP?47?x>Sf`U+9D0aq&9MNzpDc+i#M@5Pab;6Ik^1KOT`i5`6=gSQHo!tNQZQKc;p$mv{xI3GaBHZGdzG3X6;#cN5I(Z>O{&<@WUiN?{PSBY+bAGlMqdN%&OgFi_Lp`(~Pl`#nbR{JuT6m+QL!xdHs1GPgp*NokbZ*=N)#zn=(<<y+<QsrLzt@tItt*9fpbY3<M%wqnc$;HctZXTsJQrUYYicZVd}sN<}WFn3)nzl$dj(fruo(YKchl-~w>hVhr>r&43q>uwqgS(P4xP>@aFw2>n5K~Eu$#(dnt&(4ogsFiaaN}<|cBPHWiNXq~s*UMuPLZ$LY088obQJ|BQ^h6e6PoO}r_bb=yO<4gn>)annijsZJ5+kLIb#g&a!8^fSS%t;GI8fnAbry=7Sq@3jMePkEvMq?$$cm<^rV`S0shuEMk6p|1suN0z*<>Dac$`<f6m-G+j<*0v4E{_FkcrU2HQsIMHtYfFh=Am+9~?xx{iLNIRruXfB1O=p2Ob9*J@&C}QGg>!FE=PeFjT}iBHsrm^<gH#d2M0^c1uZ>(yszh{L}sF5o0KL7DrYiu-SoD9n?U~fC^0#me#mRIf+VMRbRAZy68mElnz+fcbUP+({dqeD9>1&9$cjoin|AM!&=6y<|6#{ilSS$pjd{$N1hirW|)BQOR6IaG(Z-2hV=gO6N(5#Wh5(T0e_(@`n1O7DA*}kqW6#P!%A)QdD80e%?p$A()6GOy1q0gZ%VVGol1!c6lp?*Sw!7_S5%1!#?ydnd>?<Zj*JNfIX!ZkHTBs6Gm69TBoP&2hax(59-Ad)JN)P3q$*uFH^qbsKWMY3in9<L5jBD$U#gl75=a2KTL#WT;1iv<)zJ#tMV|`AV2Tlti^`T#S7ZQDOGGOP@2PL8YoaDLDJPC>wPhDX>4qg%T~0ZO)VN+Ah*a`nc^?Q7#Z+_tQ&f@Z)+Ssi+M%S!<)bKm1r*i~<0DH~Cnaie6Lc#vw#t<!agA6<?`7~F2$-}=0ydgb^ZtplUGfNrHMCK6VVb$Z#pjbSKonstK?*B26urF(@YuL?`opn049{i9@-F!8LQc=G?n}<M8YD|Jmg9L3Wnv96vd-PEd>cg4*5;ULi=63{Fvf;Y8lAkV4QA`tz;k~AuPN_-j*;VEg&V|x^Zv(qm)u6br6qz=>5?pZQHe@F=$tKv9)Ox(CHAM)AsL73-1@=zQgT*AU@2Hygtl-&erHT^3f8g@j$v58eVB_f4FaM`u`Rn;>|nK=?#XFuq20|ik6B=-vML#DHX?$WFGgG9+8Y&s`A4Zh>{JE+k$fjcuEQ`9XJNp`YzE_wgplvoXUXIV(nN9MW-O!PwfXc$brL!#TqV`N!#KE@8k}xnIn4X#9d3OXOXiTb=-^l*wr?6eNxC#|nr^Y86+|8pyQ3i5p}1pIVTV`-RZWD`jhTpkVw?P?M;TpAH&m{*h+k5i74xculW(}Rf_*u=E9CjuO??8Ug(8d=xmMo3XkrD8ThtOGV3Ct%Ql($TSW*yKrZnWe=#wV%?jjo|lSkxHMte5rl!-e!CTRGI*hb@0CsG%@?To+H%$-0GRC38_nxKG5yeBSc#{<J|O=PzgFo|EeB?&?52rMy8t5)`?NBJtuqh#QeBaLpFAZ6w3t#Y-34h*m;EIuI0Hra4XlVudsBQqU{;Wv(f&NI^@g{C$q5<>tqNF@ad%BwgL%gKn*>c;h(D!n}P*HWpCZbfB$cvXm7p{?Jx6<!LoEh<bD{iAX$ZNj5aYKt6uvnN@ecw91k$;1%liiRIosjTs45;hTS^TyQNJYr%vgG!X}Fohy=pgD}9{KO7M9oCP6Kk{^F9Og^@3QK^;UaB;b$3q`gcbcVDuGVt00w`uiG}<Soh3V=QKB<tm5vAH8sAD=tlyNCwil!V1-f0AL=>lRm$9Q#~+7D2!B3mfb8`g#(fvB-r=0>-!jQ0c$^(K;Xo&VrUO&PpuZL>lhiSE_}%c_VckFA&jF@%c(ETyf2-sw7R6LN&(m&H>?)vj<PbFpzseN^YLz^Z81kn?D5PqU851)|1D6<Lg_GP72eu}w`wq1)F?1||3^fHDZF;--;&Qp12OUJ;(&Xb${rmeB~LDq>Yil%WRLi#<<nRZh=}ha<^TX{{r13S}_^tyu}kq8iS`VZF@MgWDQtMUd#GZ+j@y^M7+hHxU)MP4M-NfjP?E0OF3<%`L^;YzCk?F%dGkx5YB9DWsBcZDv1^H_M+y{7amGPSmYaL2+J>T-u2?O3u}AVm3}m2xb<YUigvoQ}iG6DHU)zKOJ5{;#Bop17XZ~vTzEKDJXZa(u^!ocCCm>-t?$D2UrJHXN>++6^J~w^*BBwnp&1mmxd$Qf??RzOYT?Tlp;IrLH<rjW`sU42}aOB48&>kL^1jj7ln=~gSSG5Y!r_!Aj@$Ih){1Dx5z5Bi(Vx!F4pL(YFG!6=Gj}BiSNnUQI5YtHHj4_uq84&md9NY=+oq1%u%40+c!3He(&(0hVrPkeCjS%?e?IVssa*HhaAEgDV!*9NE{$FV%_wvx1cHgj91%2@Q#ZT834&H6P1v;D;el^P}GfEwWJ}WqPyB1-trciiHlIxZ&H%1YxJNV_+*Db#d~xR?`ef`8E@@yOcfkDTzpSy;G7J+$)u$_-E>f?+E&!=Y60|-r8q9eXGh<VNEsAER$A~E?->}eDi;yh_p4ZXH-TMo&xdCYr{#Yuo~(hQP#T2Cs_t=D07!AXBy&2o5k&|!uil@ETe=&p{#p{7Y!s8tD^eZ_r`al?TaK}9O|FE<<Nat#Mc}EYIk_*5PJQ0!)<>UeWWJ(O)wtoFQ^5!AanCQNWR;hqcY6+=dJvhdQW44(-$<ad`{@F#J7fZ{mpyBQ{W5;&=A{^NPbC6!j!w8sWr#RH#p4rkN~82UylgFuSVYySUm@mMwLO5Q?o^X~=v2zmI&JlOluoK@ch&%y;grqJ90)+)0TpJPPeDrb<87xIQhK<~^!;OoVgwk~P9s(0so<w|jTt#a7I_r`*0EGY24L@r?k{0Eu`P&E#sJ9JZiCP<QB{YeA_0upRp{erE!Gin9B2|0cq+JD_zptwaI}T%1VkS<!!Xmfy1agK`7L+1atQ(3b43P(iS{>XQIj?cv2FC=`>iqA1Ys*}&sJixi5yL%Wc2ZSvyJYGZcithCP9o8XI8wU2tW}<%gZ?e>fk^JAu;4ahXn7Az(*O!)p)u_d$Bdy!z}x$dl4w%io$W+uQm$GXM$)yP>4zdbtcjYAZs^?Y&7WzE~xbcVb?SVR{SE`<_ZAhm=ku4ti7MB*Oz*J;=h@5o@#Gp7z%^SRRbvPYJfQgu;P^Re#KFDfH*X`VUn2>T1l;AZeCy2<eO|u$j{~Rx~QvTUn(FFLJq^%qMbj{>76*yyur}M!nxn;we%esODImHb>O|p*)q|bPgLLf9UjIB`5>or?MsD+F9Jem{KIdXmAoz&h#X#tBax=1u%|NK>R1YMUg@1eQO!6Z7UUsLA36C>JDuoFo}4h_28!rfcgdSWbX-Xk-VlHg#>pliUuZRH4#$;ac>)a*cT<QG<U1D?GAn{MhoFwQc7lDl^gEVqn&imgmNajpsNn4G4JMK!Cn|Gkr)+>v*Qu5-e=Q<<Bg^aR{nnSDq`@UIz$SMtxo5LNsAJTsK9>bWsF+R>jrYCjicTx^sz7lv`z_{vfJkgEnnA<RRapl<Jy5WK1>daP;ttVH&D$u9J*C80qGSR)K^$Gn8S~LgrHg6o6U{58l;z5S+Y}WgL`R9b=aV$hjYE@(tx+bU_S@#l%au5$7{t6G6cs5M#V~0%j8(J&FGMORnBq1^D@y?Z#<!qRZS|4JM1DbAv*6Fwr%NeM<%(ZVe4@SdeA7}dKa`1LIS?oHtT4Q8@$#%gFfO4D>c}oo0WIC(Bx=53nonz_9hB+qs7PK~&8U=M&0;;q_?<{}Ha%^|*%Z0gfiP)3F;gNDBeR$s5$RXAwC-$WT$mR6R)t9xXtZ7c2l4|m>S85$qk`O{DW+EU`26gQ@4O6s7o-If>LGZg-ssy$q`DbYkY#;D$C`)kh|%l<SLdD8#OE|o#dedx)&h#07%Mm)k;dPj?_WRr^y`Fm-M#ZUZcP|Dx0U-0h8-?6VEZy2(9`i)m;%tM<TnyP%CF~zpsICM4lG$TB=mbJWscC1y7)b!kab5Jwt6l1JId;iY5E~EN04wtGOW?_y$U7O!uG<BnG?!E2l*1UA+9}+XV#~9?e0}UJP-&Cp{R;3YxH)AG>vWYzZ(~7J>xHKY=ojKOo_N20s~8)UJ5A8Y`Ry!K10n}(JI^E`XsTkwLVw0K8S<|k{<)bfo%<mks5q1#P7#MBP7MeiH-(KAr`^zm9Svv)XW<$kTb%?X=zw5keG7yZvCjIG*+$37k5#0qO2Ji3e-`ys+8HyqydzO)TD|+icKT38_8G5JQbpInwh^n6YwwT2owGb`7N0&J}{XsrzqAbBsxAS4pzwnF|TrwV-|U8rSbu0Vm7=yqN;ViYeW^toGN8KFf6%*l;!u7i4G~gL@@!lFGJ*b8s~<}MG<6mB#YZ8cd4{i51H^P<US(uW>Wr5F4*PjQ41~KEQD^7wswE{5VF?pLJmUmu2w;Li)d@e#0U^M*+n9#o>~FMnamuT*f#y6Z<D|TQGDk@g4#uEqvoa43}lh9N1bTWA*Ru~5`x><<jrZxXh)Hed|9aj_Jqo?z!TLxs?bc-d5Y~2mBMxqG_@rgCnMSyrxJ5YQ&7SwhLKrO<WKmK;!~QO$?6jEI|VjQlKphtfB1pho1;Lu!q!xtEiFREHhI`0>685q!&R+lU-z)xgnYKP5h&=1>kcZ_p()btcpD<(cvXmEa0IC)hj-#4+5mn_H&&6+)f}oNbc4fjr}|kkj1<=B)T5T1D_ZDIF(+uis!Le(HNEQURg@7_fm-vgGk0Ms(^4UnrqaWLDVlp#gAQTNYn~)Ze&(pCtuTuLWLIKk=VhL%Ed5Qj#r!KGBe>Qh=)23wK8=SDSiw4d##2wy4|DdSw+Va*7xcDAAyZ0~txeCU=ETj)E9=W*kX@W=7wX>O9FNmW%>u=XHwlciuX>GT^sRCEE?#H34L^73GD!<V11iX{#`UH%Rh7~M6~4AA>8VyBPJ?ICl{KQ(2nG50;GRVi09sBX*uRQC3r>|KD1cxx1{jt>MQtWk;*Jk`ySg-*-MY4DeosM3{ZY4(WU0^oM4!?`lf;L438-})edx86P}exZBz5!{WHVQV8qCwA%qQOI+`r4!Ihm`1%Zo)sHEwF~2_^IuUB4IU?@N<b?Q0aGQK6OKt)4ddb*{Kwh*t;y&}5WDz#eX0j4z1x4_XM-op_4(SE1n!ebMpK1SOIE$|O~Fz>$2KKxrfn{4Q~95``10`i~dcaD|HXonq|ZgYRP<vgli)z*QQ&YHgl#Ct$n-Gd=Du+(<>E)CLz>8H@?GB3hmNZVdZ_f*&xG=_tU?@};bgEVeo@t57*lPTQfYpfkvHTC@?-tSqpowkh9PLiT(Wj>fD!VE~O3L}W4V59F&meCd(y90>es{|e9F#Zq_t@U!6)N$p#-O4NK3<HiNVFEo=8X$@n|l>SzLg{-3~*h~91Lh`Z9J_^;LlHL|?8!U3qp{610I?`Ke!}&dpBOQ<kgYvR1F?MDieiNJe8O{dVQ_<zFRuQugYxWTg<ijwiCLK{OLg0UEh_vWMj1K*{Q(A9mjoWGPlicQLO0;!J`Dag|ObdnVpggd%ESV@zJ`2`S@zJl#LzD^cjs{9%ze>kt(BeA%IX`jw=GaIOxHQ@h<_{9TZ)AV+9f-B^FkVL!1Wib>%_1}^O-YFjqr)9lqQoR(yW>-{s|NwqL+ZG_aEFBeSLejSJhPd2SYg;SdexIc*Vu>@P%5%{j*)j{g;Qm$L|NtBVRQlmn-CW)wo5X4`I(w@jbFF4x>AGOo0G~4=2gGru<mP$08gIv*y<yG-RI&Zg#U^m(HmY<SOvArM7njjr_jHvj#lC*qwP951dj^;oSd9Z9-e!A=AZ^BUZY@bmy%jQibB0ri70p_YTDvOiY9um<`2*j$FARgwh3A3{+^09IYa7DP04Fwq?`=NKxyaMYM7&YIlr7fwOf}qg4^9{`4f<RsyMz};#wD8i}z#BuSNBh8<3*_(QF%id(~`EIh5=hyOF006O7!N2%H5)2DWf76%k;fQO0;AUwu6cSw`uBy9kC}Ws}94&s0At!iSLn=Xo~y3bAd%L)VZSe@x-}_ZXI6XI@2XuPVDD0pxPclu#JKlG8lb0{bxwWTL&9Uw?ITzz9`d9qv9?Q%svOM-w|gt=b(ukcTRBCXh?}g0Tzjk)BY1X>e?u&P%4sS{&1pK%D}WXR-8gj*CNV!ObwErf0EzYqdEEOvK_wN%=;ax!XcNr@*uHu@5nyY0;y}u+5rn1TU`i^s3_uOJ9JM=v95XV(dN%>BQ7|R2VAH2)Ha72do<By?`Z@51t)DLG#P!ZhM7$1%#l;=YcBA-^6vi6g%P7I7+Ac1CP|3o*1YGX$p`Q#|AnBIZ<NWV{*p%Ar$y>Nj`4B$@-9ihr-8HzQvURwG=t7tVNle>&Pse{3tk+Q7&YnGf;Fj>HNbTu_)AX;E2Q@tDKua7$SWRf*YRH%iEhbhd+uAu#rU6fLXoA=dn5SGwM&xzyOXonm}fZ!XrW`tC)lklx3szNtR_=4@Qc#=RC$hCU|a2fFeo2%Hd55hT@#i$!Jxw+2tB_6@6GMnPxjLYM!Kx&Y0vX!Eiqwy3uANUC*Uf@+BN;64YFK<(yn<g%QZ=c5TroXf}r29du33*3}-gljl+Tsb`ct<>)Sjy~%A5_i1)FL3~=6=DZm;;yCE|Y9Z6a+wrr~ppmJ*vf!d|Ro?$E4nL~T")).decode())
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = _ACTIONS
_selected_route = "v39_pure_tape"


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
_V17_LEAD = False
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
                route = _selected_route(obs)
                tape = _HIGH_ROUTE_ACTIONS if route == "high" else _LOW_ROUTE_ACTIONS
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
