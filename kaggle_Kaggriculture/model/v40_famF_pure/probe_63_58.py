"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHtVf!1D3Tef9qCrdrCFdDbel4DE;!oWZ#2oOvbPIf{5_ekpQ_wKFxBhMkLUMmK&(o?^WTOTBgJUnFm<-ec&>o33l{cpcM`G?>A<;k1pZ{I$7|Hbc~{M#@8@h|`R@lPNB^Y>qV{rA89*T?_;<;nLy{rRtNZf{=x^y1x<4{!ba!}arzFTQ#D{{8=a@w?rR{djZx?uY!>-d?|cz5SW5zy0uuyNA5JzJ9rV>)GL*KV84R`SHVxt1myj^~0;%>nEjGAAjumkFWmp{L>g--2D9EpD*E^w?AB8zxnjuVU9mvzkRo#;)g|i_2Q2|y?OY_Prvu@vCX1v|2TX@t<se@j?JUa54fAlIF!xH?|*vr`sH6g2*SIcKCY9w|1hLCub=<;?z~UK;D*QS2YL6a<H&FlAD;5!y0CH&yX(#2=jZRPZx8#sdt|u1IGq>IX;G(#3A=yyB-qg}aBsGgxO=sFkhwf;l;L4{H@ke=2T-6#+4Id)|M1cL3@Zjpe3`*rKL>jQn|a>-d|}7$KE`;n%^Vi^?vtwr^{_ZBe>kRbJ(nxT;o#+c-P)Ijw>Rcxx7o?YS{7upPiQZA8)?ftu{hfw{N>|I@sLGpN?#d2chS{7zFf7s4<FnK&ZkwIS=!Cooga{{?DlWY<Cm@H-S|3_z5iRVoaeXu%Q^f+zF^BAwO!5&O(uM$9&mK5;t0cu1w8q>KI#g2@Sa70*eLKA@nG@{;KM<>ea884Wz%~1zW8A}KvREn^8oUIj}N$c{rdXFyTAV7`u5$c*RTHh=#cRzgil6aYS_|~BNadVEYfdpemZW|*<slHgzy?5!oL4)!;?9EG8p~*@V-KipVrCR#<Tg^3_bU~{INnHPgd(J(w(r*dc@`g-W*W#hw;nXn>XX3bXNTZc6_@cE6;~ZojatO|A&YBTU*`>xjz3tT>P=m{<DJ({Am3%CoHkh6|8oIgugzTadLTb&yCKMB4XgXXh)y`jw0>+AVg7i577rzKkY@Jv<+z}?~j_c;yAum+^iQKgFS&rTG0jj0o4iQ(vMraLi~Be)(`6y7sI#K1^wi$UrD~#56^G^$(aK!`guEXV~g++EkBR`H0G5;zj@R?j5uHso(2m{ct!yz;usI7K$6ZI6>NNPjD2-Fp2k!n!MtN?P!6jvHE7;hYl|YozbsIF4{94yYjWr!&bCx3cZf{Edn`xm>Fyz;g!XdahF?`j#EM6Z>$us6nCEKM{krPWS#jq0<zX1>)N{rW^PLSe=zVWbPGxrrn$M}6f;=J2$My3y(V<RO&~;VBk&w(_SmEMPgrb6rn67d|R@h4q*48{iq^O|JCtRlqM^-qS$1$vW2*On}j@r}rp=qS2ifAKn*q)xwJ;Px$5)mhmc(cQq*fmxrHbwkWWH>`WrkLmn0)qi%>)51&TlWPy&*f+7-8}!`89}$RI&E*W|Aa#3c;Kv!GgS{dc%onL9y?0doc}q#^I;)xZ-OM)XNLSP=?^9jXjh|A-7wK5AGzJ2x9@JB|NQ;+?d_lWv9w7W)h_s<ZNDBTS$9Yar#~KF-eUxxH`t~X*erVvu7{Z~Jb7CUcd~*SlCLF_&f@7J>AqRCgT#>rdHg`3KWFhedI60cV^?DH*AOBrkT46L)s9BS)Qen%eEXOK9f=pZc5m4MTIzoIKfHEZmrM<5Ir$Gy?^FKFv%gry_%IauI((1|CQ7^-XFYmeyMrCPuSWwub9b|yVJ80*s7y8da~z!{9HI%pB>TmDTO<bhQ#?9lsU%Gv2y1{+ESm{@gEdcV`CiqBbar>W8_e!DoTUAvp+O#8O{0%cW`dm0(`=jo;r^W*osB-_Z>Wh&2BoXPBDPHP0JiPohXj(qA!e1OP{^d>ygZi%pMpL<W%+Gk!}7L6$yF*)4VFP(p~&$@EYKFqhURHlj0rg*gCW5A1J6@DLNQq~&)0rPUiAvzBtJD}F-z|hjgCp&&b{*La$LNi<)|FvTGjLVuCIIa(@t3Hq60uwwV=SD_ka9s;T+>tP!rl%y4*E?YRn4jhSC{%>Q4p9^nB-Y;`zaPV6`!ffD0;WL#Q}{_>^reQsaBdSUi}?pKoqH%Hq}U4Lh1FNy5@HhPR2!HpA(a%m~B$@b-s8`{h~D;`SPwXDCcgIO24~Qq@cRxq=-j4m~CO(a>;SgoLh}Lsk`)m0AV}?J-NcnTS@nd|q?m0F4r>m2p2rSXY4(54DMbXhRJn{0X@kF+I0o%u?aq^MZynGdCXz$|o~o*Svh2x#P1?hXDvFu2B@4HDcL5!kns?eA5w6TDhzG29!W`vw;#hN*G5qDsZd;a6C%<Hx5n5L)z$l&={rLh(-{z%eWXv)&%nigL)pr0p@5dhpq@;0iAijV{R%fB#L*^yyD}l2oUOHGl!z<!Pw;vs_UCP*oE)R()O4&Xzou!Se)3{z(SL?LuBPNs%Rf^xl5bwA0nmh8bfr^ZN#V2apOC?(4(BKW0%frzA-L<+g8wI8sH%OKgI}(^PL5C8iz(A@p{wgwKjQqK9bIFpI;^UDK&sX?rZbB;CMQJcJoSyNz1X4o!iTvZ1~mS?+(;a0P>b$2Ra^2gILA$t_3WeY+$&siV_xnae5*pR=r?1(tyvrWgTZ_Wf0w65kro31|SkdJC;;=3F?Lzf^vh!h|sy=wl<l1$z0qL1}&ah*bgsSls<n|EtE_2l`q9O{6e3D7Wyk`?v_{*!a|Eae7};KM5(JvDCYuCnGqoIJYK_gTSO7&V<?#emF*0z;!<VHKZ=W=zcyRDQY4+RVR2DbEzkMaHa_6_Z?SXtSiLCe72-|B=fe?dZt}-RJW6molas#BnFlmdKa<p%o|=S6WUJtj49N};DQ1yQ2i%`tz5e5ef4><<MnRf9rQ!VC{JcCP&%$^At;0PBVV)!14Z7jr!BaoJliYovx_}9f4<SZG=qwm{Ts%Jsgq}2}c!moI9@bLP3{*C;4ZNT*;?tImtFo|_eALm!^ylHe6f0aR%>=lF?<-)aT=ES|d9@j#4yyB#z;qZYw5OO7<!%rr3K!F#nO^Q@>NN;qa-7x=*jLIv;z{C2)^Tc1Bd+W~4)pDVzoWjUaxeM-SssSlB@X@C7%PvLwnR}eB|2*{5gzHd-9b;ARl@3*yI>C5Fg(TWM}Jr3%tbawMYVQ!l!TpumfB5DM2e-PXhA+mY_&=EmnLjlPP2q|LXjQbM#<eDe5$}V!1O1I-_h^U=`cl`srKcw8bTV>ksPLxr7XQl-G)SM+SZ7@NSYl+Z!fB5XeIeS$@G#kh@b}7DqeU{&Ps7^gv`{7Yh_)-F>Y_Mma!pST1P<d=B`wErgN?!CH`qxo4Agy8+2#lrQ&76A4e$3&4nO%c3Edq|8p-*$>|ppDB6ll%~hMElqDIfHf@X|BVr0+X3~9*k!}gcl7b>)`Tl~I$^{G`#cTF7I0pSXT}5K!m{CRHW6jdHs*31*OK%E4(`n?UGd9cRi@8YUyQzS|>r}@`M8s^jCzuW01wp%#(aUSAD2;i^s-4XmDfvK8_96=_fibGIK%!PPxCvB;YTp9QDM@ItP%~GgEb`T=#TD<gk~I!nb;o<E<O}Qsk4KSx@yU6iVKERC^dbtb^~$Oh>yJ#Z`A(4^1<S1Y?#iW<N&}^n(}7SvFI+o?sEySQW<!?>kaCT;)P-xlv;~7f1&L9Mm9WJ5)npH{{VM^^%A~KZbJ(ZEGr)n&tXr_rnA?Tmm!~w(_6-{IVKJdHRgOU`=BT`6)>g1VHNe6TEo2_P!nBRfsh#I?01d=GP}m>08{<jDpU-=h?YF5vUUZA2N23!*4wLO5tQxTjKJcT0^zSxP77mo|4JI!Nknr8z4eAe!wQ(OJL%IJ}q_EhDRQU`zvVdC4ldx-K_FoJBOzf~d5^@Oo)T(`%wrGVl;mie(mz7RWKZp7?I&IGV3fx<fm|;j$Z+`ADQ3>C1?WPm}cGBeb9wtkR;kMV$c8yj6R#q=VHIa;y+f1G(m)|^Z*u5nCGtO~(Q_qvV8}^GExNt-&F;G=D%fxlDvglD%x%anKa5|kv8KeIN5-N$+(|eaT;bG#2aylz2=y_!$>--ac9FK^N)i_Usy448wEf;LbiIwQ@F1SF&C28ND%_8Iy8L>+%$KkNJYA0bXf+(n4M&QjD0-zq&sxfRr{iy87-hya_DNTC!Dw4AV_{T~mqW~&;C15P<3GlorC~e3r99^{yz#7&NxQd}YxH{IroWhP{TT{2=>34TZv>wINL4*rzjf*zhizVvjI7Kg#c`JkA?sVXi5Fk^2$(hdM-Q{d0RiKL|A5)^Gb+U4|f<TkA!|;G%-iJB9%2KN`zlb{{YfoezaQv<&e5D>%Xd55q<-yM-u0l8$7EunoC_<NNR!GppEVJ6SMY@zB+~spG&?ZBX4VhIGD^ZFuyB8R^IWp$7v6L!>gw%<K3ohstu5qXsh29a<`-JcsMskiN6xSRh^&va$#K!R8v8Ko84iQ7xFXp@4PUICz7{=)d<lkSjA-OfJ#dV@zNU&TBcZqF*Fl>qGiJT^z4kva*dfQGHeBB8-J%(5|C9~HnOhBK*h7B7RgvO@3T?*i}pfSgW_Rl9&iQzNEOQIgrL&H(#5(8;YF<8Oh3uK32&c<nW*uQ1cje`|unO695zeXErwC&|w9pPT0ys_7S2*XPce<DG#p}S65T~#`o6txa$<-Th5w2d1R#k{QOvw4YGrPlQdsx4*WPL!G3rEqP^iY`ZhQ@LK3S1o5ZT$hTQ<8Ez?_uSX5xOKmTQfz)g!!#Mt5L(q!@r`9v5hTD!N|mftE0Y4XAXz->?V)3mYN%Dd(0p1pYXuT1p{BQzhFGdSHHdb_0{Q?lC2OZrlV+Bm{-$_0CH#{{Z1FiIigt(-E-kZ_C`MH(3Om)h<3P_q)hgvBHHYX&EI5e+q7-y&t_HD09YjSAu(&-zdK=4R6cUn;TXEwf>(z(U4TLtjhJ)5opbIO=_E-lKTf}hPt8fuI8+f+o4PLNg$`Li`EK)@RG0muGS?1A5tQ<L@nsTH>j65lwMCmkgQ7=Z3xy5m5EMg~`UQh$ZL1wi#@Uu@3e4I#pD*j$mD;0ffT&&j630<}s+<6@CnV-Uax9B|to_89Q_e*YSu(j&a(danS7;_q%WDl48f&zh}dI)9-^Y~O@l8neqReP_9^itI0H3y8R5>2Ikfq7mgqO#hJTEq-gAvF)Vl92JPW%buwT?n4@sZ^po33SA`{D$gLDI;=mm|$*as~w=A*ySpZT?DhOhBSFlf}LHgKn6y=X;$?hhD=>X8Cu7KOhiRqbRvd`{hjkfzv}Wq0$g1=<0?9BeVM(M*X-DVS3_E5Pw#ePB?@9zh-jXx2+my5Qq(fDxmdF1*bE%XEI*!rvXv1!m)De-Wm9=@%ubWx<5b8TVwqP2`O0()Jb+&H*H>!pRP=8m5vM3N=@mTg!)MR9V>l21m|2<0m`~>t(^{tv1W3l!$!bT;`{Ma}9Tj=08VlJoBbx4R6f^fr8f7bJ8sm{;o&Vi%pB_E{xmz)1lLd~Rkr&X3fQ2fjk5?|qjVtCs?50F=%?a?zix%URKdqg8;^tV^$b>lbg%AX4s9!vgA86?*1Hj-9k1*dSBaTl$QJ+u;TdL`UNc>x#Wh^~xX4IuHoCLyYlfchqnMH(%C2Jgcn1Wq}J_`tK)J<uH_*P}L)>J6)>?jB!u~{XyJd7~qEa>`G__ids`7JrIlY=s(U6>-4B*I4wk4y1<0+!CnZ6UUdI8}w>l8%tJb0I>rGE{Y?<Z|eS)>SwVMc`Qwd-7XxLSfb1c|u4VLlrE!oa?Xhcs8M~O2c4mL*P&zQo0|Q1$;1>u5iUqO{hs~7gry&84sn|h%t8Q5xZC?>B#XJi4oBGSd)<j1)MlwPRET13xWCsQ9Dj>4>g$1LjJr|L(@grlftDzq~zJetg*Wzu|k6MxItcTlPFncaKuOiP5ZRhZ)6SprHz|nXoRNaRan5)Ro2aZcPQX)YBd)NH!Q8c>8ySUo<xAN)ckJ|*&|-qJZ{K^T&Q<=FVN^LP?47?x>Sf`U+9D0aq&9MNzpDc+i#M@5Pab;6Ik^1KOT`i5`6=gSQHo!tNQZQKc;p$mv{xI3GaBHZGdzG3X6;#cN5I(Z>O{&<@WUiN?{PSBY+bAGlMqdN%&OgFi_Lp`(~Pl`#nbR{JuT6m+QL!xdHs1GPgp*NokbZ*=N)#zn=(<<y+<QsrLzt@tItt*9fpbY3<M%wqnc$;HctZXTsJQrUYYicZVd}sN<}WFn3)nzl|pl(fruo(YKchl-~w>hVhr>r&43q>uwqgS(P4xP>@aFw2>n5K~Eu$#(dnt&(4ogsFiaaN}<|cBPHWiNXq~s*UMuPLZ$LY088obQJ|BQ^h6e6PoO}r_xG;Xo3a9E*112D6eatbB}Pga>*Ru<f_H+uvI>iVaiGGL>MRsDvmBD5i`pATWLprgkrho-O(mr1QaeGi9=n$1RVS1bv&lT<@Hnq{Dd>Xt9d7}U82p(UAQPd3YrNaiZP)|U5dq0tKRAeX`$<bbs_?s|M2etG4?GSsdhBD{q5wydUT#o`V5o?3M7|GB>cdQe^V-A;?3R)$rC$Z2_^12TBgRnhERL*3V6y|QI;eq|0Tr4gEUj^sauSuis=jE+bkT{RDIKt|Z!?3Dr{zM{P@b_kJ-A9G6n78ihP8}Y%|-a@6-BphL9q;hk327M%rF7pmsCd<Xn-v44C(#lClnEg%1Bnw0{%i*^l6RDQLt08MDHKnhn3pq^Q6_`n-?bKrRhNnbbV<~-jrrVJCza@DAI%qvxvI=uBZ|djHdzD_%8lr9T^h}a(d)6YwEKDW)z3vNg^u54n=hAJT^<pcKFZ5NmaUVZi)#Ne$Zx56=xwhB5DLhzEm|EB#;1dw+x(xz$ZFytD_aPi#`>K!4xAP7nLoguE+qQmWWmo-c#RF*F;ThQcfJ%YRfK&(hW<jx}0(lsd2qL5UJ$D@;(qEimB%Or>G*+txdR4v_nac%STcC3Mi}}#z&T}PD<3`Cg@gTY?Uid;u^7z-pk-U5HM+#1Z*^==KT|8yW|lLYiOhD!ZdS*i_a%vfGEOPf)rM4D0+Jn;IVP(^oL`07@o_H<z4XGg`A#W-IttiHAt3dEXVU6%ETICWSzTR`8J58t<5ph7CF-?VT=u*G&*@z8_d?Pf#?1LUQ^!v93#iS3O9%W=lzfKF1d|<OG^Z$(j{5+q7s#U&^cQSJpeU-pV*&Phh!YCbL$7=OUYRgfu&$+5!%89`No*y6s%<*9K*1F`!E+}8U#d>Vq12x*uiQ!-ILSSLc5!39<#tuWmPiRY(xY#UyQcIwKpmN^N&)2*r^KsBl%8@T!&#I&cc9=*$l=V2_fIF&yvX#q>19h%~(doYxC)i>LhefxJs&jhjDN*H8|bEa+vqeJKXv(mdqh<(ZR7sY~M6`l5}a_G~HrFD~LQIc1J<9LvhEb!Va+vs+tI=8#598#5Va&k21QLZm3*q5x=B3E9O-RC*N>s1^aS#SIG0RoB9My3q=?$a;?05(ZmWGx2PpXz#=Ejq)NYvv7{ifOlin_(I-vj-9<J`CXdLYjP`8KDHC^eOwjNZv5m&1PNXh)+ZlhYnLB|XsN|B<G(iEAcu!o?jt7R_n#gV~U=qJ_OA><A5m;iHR;}z&kMdQRN6Ek`M;hHULCVV6Tjgp69T;FySbRW~ZL;B(Cd(+MM`k(@!>=3zooA*+3QcWJB!&QJkV*;^lvi;gmXi^q)s5>nReE{ouccBO-HOWi@Tw5ELR-IWE4&nFTU3}R`bXth+Jr};)D}7RW>2y_@wjC8l8GV86%9YGQd#58By1wu=8dVjdBntU29+q`VG2d$Kyw&H`H3BjI;<ZBf8^=VILw#)6_x;xy;Nx=kB2_0?leoQT&?9~1yIb4XtYmE3)9srd{QBABTBVHP{(wPDC1JV6iqo2yweEg(gnnBj`8X|wI85dMYd3=H>?do0#ReL%#Chc8Se=i>P;l&I{(3ynlgCR+Gd4165Xu{mQ@i?9$PU5Vh9%nSV~(3z0-BtCgcdmFN>#)s$Jno=3?WN`l!xffmPA2A?MNBo@O193q*~RDzX?;WoE4`W1E_WLbtD(3`+1-0A&zT#Z4pmq=o@mydpfk(H!{METa)fRm7^4C_@df7ki%Es+^t`4@Z)x(ppF26v|=-TC)<6MKzp>!+M#i2e&oQiXhQV-}X?Z=l|x2ZXzmho8apk19OzS0mL1zn_G&x*$hB)Vj^U6Z;NGIQ%EJ@+RT0+Z<ara_?I{Vov2%<g5ta$xwI2)l$@*K#B7|B5X>w(z3?OFr|3WCQ!3zcemcB@#Hs4H2Ev%}WZ@JdQ&8?;r5RbG>{=0%yy;PQ4zLcY&KUitDiC>U>v4QWG_@?BE)7Sp1;enbm)x(wDMfbLgZ!P6%m{s85{#gM7>Lv6iDL96E(#q}25*H9*(e@eK$hba5TV{QZjn`L7rjbeT&&Sm)vyjC&9k>M6W@`wqa1&QY7#3<U`u3lERVY)(5K12n4>@~w{L9Z{NCX~4dqd7`P5yk+U-FzRRtuZ4mpG~QaDlIkT^hU#JcHSZ$VS~8Lzg5;2jqwG60fYCMqFwS2ED;pr{+SYDq&#MR&D3yyY!26BnVX-=rj2*XTh#@W~E=iudRs-qQ->GTz$Zm?}7QxcHvZz&ROslSxZ=y6K=&wXLY#)dJ`vOL1I`&yKz!kuoTTthC@S-ZL;_RW2g1?^m((ZUVdFo)6C)PRsvRJXr%pp)?4ORo&yR0FdH%N#=BFBZ?4eUcEmRw{$mH{k0@E*(fHPSEM`=PP0`&w;W^Jnp_Ey$NSNgiojD(b8=rAo%+1dt&cv{$b3bms&T_Tr-BdK<DOqk$to{J@Ae!#^&m1^r6QCozL7v@_tOPfcgO@@FMHMq`(^yl%}X)lo=ODd9G!5N$`EmYipMA7lt$@yc-dMQv52Zuze3EjYI^`p-Ki$~(5aNAb=vCnD4kT*?yLbY!zr7cIS_!p11iiopMsR=$J<Ubr1Wr|>HEhF#RxE}okpt0Q^8N`8Z&Z;Eb=M>tYfK)48YzK-Cx3TVp|ZSi~*3b-3Fm!qN)x_MFJSHtI)^MTC5}DIM5_0@KkWQ@EwHU;b;rj35Y&!hGC{{b$R{f@>}k1<q`t6=ZXvn6YX!(q9$z?V%zA!_giDK3Bp#|o~^`W6FHhj$>`(vW*glV-JVW1O@bIH&a8Mx5r86!mX~t`)WLxcLSo2;4hh~JfsZndtMPP=_F`+YhgtSh_aacj6@}xtUu_hW&jitapb(V^>P(~)K-O*&*=W)cTu|!?!meo!toTK=%@qL1F(>R8S$jWMuP^od#D6pAJk{RHFcb!ts|HZo)c|u0V8tor{feXR0C8w=!z42&w31rK+`PW3$v4@Ske|!rbx~KxzEnUUgdB#iMLU0@(>rmZd4r*ig>%2xYw24umQb8X>%e=Hvt^<=pQyg|J3NdN@<C4L+LsCsUj&5C_=n#%D|uZm5IMXOM<Pv2VNYee)v*-jywW>`qMC6+EXYHgK63J%b~@3UJUL;;4HVI}?vgi$=(v(7ydeM~jFU}3zR+sY9F8l;@&p<r?xqkW$agL(WL5-i4nZAp?F9R9>31yKG|7>}Eot6HQNh{W8%!iePE_X7PT2sTu2U^v{#r!zMwZvr`>iiQNrOvbfKBdPa?fUkP{*iMeJ%@%P%)h%8t;446`fY-Re|DU_FK&T0Fl^SG=qkrtFjJ!dZ1td3%*&o#T}xZnzvCHdrFD1M9Bnpf;hUCGv=e0N*B}ECz@AGDa(}uw<#)0h>j9<&nIc18;2$nTcb=y?YGU9mn(5hF^G9XC@NAiieb`j7^`RlUWimsFvV?-R+a(+jBi1s+Ug^biTr}LX2GAUPnS}j$`!w!_(Xf@`KF~_ekc>gav)CXSz&nH;^kR~U|d2Q)RA4F0$RGmNz{D7G@sT;J1EoJQIWi~no%jin#FpI@jH>|Y<k*^vng_~17Xs7Vx~kQMrJWNBGRvJY2De%xG*jBtqPMY&}h8?4&(=B)Wu5hMg_S?Q%tSy@%h;q-+3AOE=UU|)I;z}z0tRiNOd!)Aj|rQjx`V65u@1!uFgBFiO*@GitQ$WtpyZ0F;;LqB8|U4-@knJ>DLMCx_jqy+?p_QZY%d03_DzC!1hHvpr_-pFa@Ah$!{cplwZ#aK~?Lj99XhwNa*)c${e91b@6*dA?uDdZ1r01ca+s3)AU1Tjv(QPWLTr;dlgEmh3$nMGbfaT4)P^xLtJ|t&#X`J+TE*ycpwlOLQxf6*68gJX&T$)e>*PJdd6Se*a$^em=bY41O}Eoy%bQG*>tadeTJH|qE)uR^+{r7YkjV0eGmx`BtHg<1KS!BBQ^M3h~JNiMo5Z_6CDkfLM(#aD`COTshKxiAZLV&)6%eBATj0Y-TF~aX{=h6FYco1L|HR36sV(YRVlNZNdqVmsYw-u6q`n5H<GWAc`8KbG&6sDCg5Mv5hnZ>@>?=ld|)zNPEo8=NOXKu9ITQDVqWDU$1L*HO63F0#B6wZL{;m2*N7^PIaSJfU|4bqDa-FE6CF}~iDCk9Uxvu>G|ml`iz3MCNEWwG?ow&39x~xo$bCfQ&7}OBT(Ha4qZV4eSqR-EZSDT@A!M!Hg&c(BU9E!h7SYy_i4h=jvWrAeJ+%UiGnqLwv2FTC-zI?xqWI2*1htFSM$Jp78OS1Ik2=w$LrkM}B?Pyz$(z%X(T*Y``La?6><N`&fhVeYRH2!u^Ay`5DuwMJXlhF~PDZpZP9^4)rl5pV3?s9m$e-{d#iukmlhq~ScM5ErB>U;O|L_C1H%EbRg{`SPTUvySZSt^1(kJ^JhO1i9zV2bW3HfYoBT&#2*Bw-<LsO*P@is)n@v0ET;0RJp4)4T8v;q8<Zmc4st2tCl=mv-5PW7{77%8mLsYfk2SG3TbVouP2RhO{nYkJkyt0*I=0=4E}XYRsOrlmqCO{IqgQ#ALg1|7nj*E~s-{LE2NTVWOh$gaf7&dWSiS^Ar5i}_bXMsTf1(07-UeHsrRu!42^jHjNYALi^uZxi?sF6eEKLZ*}|TbrIy&54_pSJs!sAiFr#F4VolIUc8%ngxm%ZxR@3U-cTx=v(9RUA)e68-DK6Ws(+#22_w?jq6Qksw$-iDtv8K(o?NMoCeRND{Dln5eoA0!99y40JNM&uzwYO7Mv<ePyoSX3@|K%irP%7#2p{>c6DhqyLD~R{GNi6`lD_m$x@&Fi9V%?CW#O85>V?p`p|1Bp{{X+N$Th^$Y!nzHJGPKnNPgaxqp|db23*2mlunOYTVS|6H4eSx_&Rx-<2k<+Se#Vqe3geTRm;^>s)cW5U&pYp~)zRfIZy07+(<WAG8pvJMk3nuR_Be`l92d2}&aSl}W1VfFt=dfzn7E_+8@IBnl@~^&c;?;R+S&JH^<+2j9gyWYM=ofvYrl)!IDgPQZ8vW_sLRxRHuRsSPf&G8hwVMYKBk-5B-<1wUXW(@}t(<x5!~S!{J+R-tm9oVG((L1&QZv}hxuSy^CFZBxFpgzWh$9F19d!T=g6h{$5zAIMjC_|hZYIS}~O{uQ3z#8P+s@U!6)N$p#-O4NK3<HiNVFEo=8X$@n|l>SzLg{-3~*h~91Lh`Z9J_^;LlHL|?8!U3qp{610I?`Ke!}&dpBOQ<kgYvR1F?MDieifVg8O{dVQ_<zFRuQugYxWTg<ijwiCLK{OLg0UEh_vWMj1K*{Q(A9mjoWGPlicQLO0;!J`Dag|ObdnVpggd%ESV@zJ`2`S@zJl#LzD^cjs{9%ze>kt(BeA%IX`jw=GaIOxHQ@h<_{9TZ)AV+9f-B^FkVL!1Wib>%_1}^O-YFjqr)9lqQoR(yW>-{s|NwqL+ZG_aEFBeSLejSJhPd2SYg;SdexIc*Vu>@P%5%{j*)j{g;Qm$L|NtBVRQlmn-CW)wo5X4`I(w@jbFF4x>AGOo0G~4=2gGru<mP$08gIv*y<yG-RI&Zg#U^m(HmY<SOvArM7njjr_jHvj#lC*qwP951dj^;oSd9Z9-e!A=AZ^BUZY@bmy%jQibB0ri70p_YTDvOiY9um<`2*j$F5(0wh3A3{+^09IYa7DP04Fwq?`=NKxyaMYM7&YIlr7fwOf}qg4^9{`4f<RsyMz};#wD8i}z#BuSNBh8<3*_(QF%id(~`EIh5=hyOF006O7!N2%H5)2DWf76%k;fQO0;AUwt_YSw`uBy9kC}Ws}94&s0At!iSLn=Xo~y3bAd%L)VZSe@x-}_ZXI6W?n^WuPVDD0pxPclu#JKlG8lb0{bxwWTL&9Uw?ITzz9`d9qv9?Q%svOM-w|gt=b(ukcTRBCXh?}g0Tzjk)BY1X>e?u&P%4sS{&1pK%D}WXR-8gj*CNV!ObwErf0EzYqdEEOvK_wN%=;ax!XcNr@*uHu@5nyY0;y}u+5rn1TU`i^s3_uOJ9JM=v95XV(dN%>BQ7|R2VAH2)Ha72do<By?`Z@51t)DLG#P!ZhM7$1%#l;=YcBA-^6vi6g%P7I7+Ac1CP|3o*1YGX$p`Q#|AnBIZ<NWV{*p%Ar$y>Nj`4B$@-9ihr-8HzQvURwG=t7tVNle>&Pse{3tk+Q7&YnGf;Fj>HNbTu_)AX;E2Q@tDKua7$SWRf*YRH%iEhbhd+uAu#rU6fLXoA=dn5SGwM&xzyOXonm}fZ!XrW`tC)lklx3szNtR_=4@Qc#=RC$hCU|a2fFeo2%Hd55hT@#i$!Jxw+2tB_6@6GMnPxjLYM!Kx&Y0vX!Eiqwy3uANUC*Uf@+BN;64YFK<(yn<g%QZ=c5TroXf}r29du33*3}-gljl+Tsb`ct<>)Sjy~%A5_i1)FL3~=6=DZm;;yCE|Y9Z6a+wrr~ppmJ*vf!d|Ro?$E^>M1v")).decode())
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
