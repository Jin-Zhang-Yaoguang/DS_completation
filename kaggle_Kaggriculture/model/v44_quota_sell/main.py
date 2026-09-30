"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>OOIX0ZiWAfp|J;+<!5HH)HfC^yM>k%;l?lw1Gzzf;AY@t7UaK2tyZ72ckPc{i>x}b9Au=UK99{}v8u?$Mb^*%{or4J`~B~K`~AT`eDd>y7mr`QeDKSspFH@t-~QuY{`2-vxBvP3Z@>Th-~Q|Ne?LF??)6`PeQ|UB^!1Zh58l4@=KHJ1w=W((`sJ7Z`Sg?BkNtFg^XmKj*Ir&df4=>hZ{B|3?inwyuAXk+`TFqAk5|vHf4Y72=kMP7{@KmdgVL+pAA9`MvmYP76XD7Ao45ab4)47D{_5(*yY~)5d~@~k)qaF;b@=Sb53gU`|Kz*hyZ_imC)+;`-%v_==*h8p)cFB-V;M!+y!`I<v*%BLeQO7=Uf=4;o&KXpFP=aC>D76j2H}Rs?1jAh)lo7W#M`GlxhiPxes;Yvym|cU>gF)NyGMr8i^F;Hn3Os#Cd~fblVC<a#ktuI;_lUIA#;1!EQWjaZf5y353qnf$eeGU`j^}7XV4g^_%gy>J%;@TCi6V|xnjrfeh7K9$s81X_sP{l-7AOf4`mwlxqNXP&Rw3@?f!EA_GWw8O?EP|)(*0nC)_W18fnTrvpDZR_{+za;vtK4N?#d2cTw#gU#`;b{Rel3^G<6ss@>@B{D4%m+rK%FU#8DH`8tDr|F=M$=ePUn9DX8K*z!kh)p?=8gs;>Cj*e9vU^uaWXJ1#xwL%`ew<ADk6nKnyFnJr`{Xx2Y#`$pNt@ZAG@xye0rvB#U0ptN6A8`Hr`PGwGzy9Uw=GC+3&;I%7kntykPexyA?4>71Dt`Fcq+edYK2FuyVc7hH@ERb%e*fEsCv*B_ApN{}U!ccNda|bRy!~uM&wVdnRtV&2*E*YYC#<s`u{nV^2h{vw{PgDf#ds*4m;Qo%e5;X_=fkDW9a@?nvABOW^<K#J`G0Zo$Nuo29rnQ6-9K}}k{!B&)sB$xm&a|KT%O!>qcf$582B#Q5h#G8NIO3WQIy?7^g-26dl4v2LmJBaQqxo%<!i;wTJad{2}IJ0F4zyK4j{LFoZ1!U&k|cdtTisgxAcO3^46~;-|PFwH~-{}fs}rpPMp{xd_?MJ=}$7RH2Te>_F=>Ui||&kz=UTO07V?*;S^ZXd7^@e500@fPRG-jN+g(fObtr0`c{M6JFnWJ$?z`=RNsTzhSZuAUBubeQpz17)9^l&qxER_kkLYWIdH?Tsv}~>BgS>y>_g0Rwd#Id_2{fPbNuok#=7M><B0jr25#tmZ%+<ocM6)%shom5Ak4@0^EJ_-PP?G%s)!>Y8Ns08;!%XAf=W!a+^`k)(gWR^M~E~P^!bGAG~vh!XY(k-s)rz4HRGr~`X$^N>8T>x2pqOYr*qG6*o;KP2_)XkaAtN5&BR*~zZ4nH5RfS*dV;`UK-oHb(!s6!l$_`Cv-E79fAEZ;+gY8qx7mL}A#*%%*2a;l2OT`oFL#d}Eo{#J9N&4X$eZgR3HAp=ewXwI69=@rqH(!lqDww<J3%jB-8_Et-PO&_U-_{#Nt>lz@I%{vJr1(&kQPpVJiffg2tIExO)Icj_8eRfGgmx$TMc)zf*O*qC6dnK=_2XAQQE=cXa#xvK(T(#=5_P}8Z*YO#OALdL{=bS7CfsRjf|-mxe59EV-9pAUg+AnWd~@f`{Doa+G$-fG^FL^KRi88`7_V{Vin`VQ0U9>K`xjm@oF6P=y~l9cJRJF81R|9o9zrU`JX^#s^Oobbdqq0TL326FXr1KG0-34(J4zUY4Si=1C(OfOyC==d1A}=sy?JMyX)OxcDLaq?I#Tl^5AM3eS|U-<a{1x;{*uj@8sxg)>Hn58n|Rox+_@3mT4Zq-n;lAfhBN=S!F2{GO0K&&!xeqppQ>ke%sivyzNkOl^RroWsp}Wa=Z~6w8gTaaT+_ugq_faA;9?q&r>`?F<COt*M3M|^$Ol3KQ(1BOYamn9h117d*xMiT)d#=xHv{#)${tUuY2^<PFU-r13*-@puwQ`fBbCW9Aho00d01=+%<n>j0)?9(h+&fp9+%c`OfFW^8<ZgwJ}J*1r;?BDvlsNWm}8X_@3G<?zhP|*VnhU`0z7hA5Bz}u(S;EHgVZToL<R{*qHC%etT#?JukGly~gGl3X>C#I32N6^%8%su#Xf)PYHh{8jg#Q&~;<Ts-m(|%K)K0W@$GA(F-mg*IYP2Qew3-&W8x=Dp2B~HZd@5s9}UZAvYtY=QcL8)Oh#2pdro7%}0Xr$&A=FZ{KF__-xc+0747bC<@IQv1}h<4%JJ(>4+z-+*N%8N}#&gK#3eBjH4PAIF<k$j}rflL(}n)HhLd4q;wn62x4{_7vsp9U>>odo@F?|91V5oitrWCnfE*9q>>`hyp!e?x33~VsE^GYimr#vE_YB}-{gK@_|`0Kk6DA}{3L|MiHQw%Xxi-%Svg4+%_FM2H0k~!QtGZTL>Jvgd@3C`zOxHG%Go-0>AdC}qXOKvf+o`dh4B9vBPh;y7Sw4R8i~aErqgR}^74Eno!>scO7c@mfI{wT^St1AI)8TaN{30yv67wJ%bslb)!^?A)KLKPmSG1v9!-N-#q+KOES+p%s8~e_3%@u$kP@q2up3F>GjCbPSy>rGcUFYR@tOgM1ksKqRbGO+Aw*Dau#gCy8*XcpEiajiTf(5lGYk9SMM~-OSCyh%qOW`@<nRl94y(}Dq&ZtcC4_|*efWMQHJMU(DWRPUJY~j!#Pe8(?Y4*_%*RkN2P)ecTE(Tx)IXYwpT9O+yHX^bv0+gutJHJ;wT%yW{#)$aeW+fP^a}B&;`8AMH7EJ@5g#PDoykeR&zT1_Qa_W_8J-%1NMx(vkv5VY9#YIAoesDkpFRKK?Z00Ql2MQ*PiZ(mH$N}W$g}ai|JLE2gD}sL&Ia9ZaPO%f-%0L1P+h=;$A=IjB6JpvJSxvm0--03DW2g1f_q&mnt{qDwt*KkMts^bxhjgS<fD!*raun%rO<GxG!x(wzOR6xa>+L=<<(}4I;hS|0@FcMXiqU^%H1GL6fUMeGp+7s>NN;qa-7x=*jL&<;z{C2)^Tc1Bd*Lq4)pDVzvFsM?OyZ&vOEm8OC0*OF;*U{wnR}eEjnv45gzF{-9b;ARmSR<yI>C5*m#Q5kN&R6nTu?WifZldC<!|QcWO5|5iKlbMGNvlVyaELzudy6?KDehCluM?ZM59|!KVs*15AIS_#OQooeop9nQC7?t0AO89m!!DS<2F@)NNSQrfrRwi=^3M^!B1^hE|gQolP$(g9vJHt>T6I#aSuNjgXmoajmRtIL7TQ)-pDvOX~>e-Q1Nbk95uzq{KgowTbKKx<Pj&UMgND{82(lZY~7Dvud45{m;ELEvH{hplB;HHCJttQnqBQ+O#o>jEE_WnMwCKM!F>&OA3mJ<@*XPl?xa?ir4IEa18o&x{AccF{6sY$C{;YR29+rmfjS8rqjqxXKd8vo4H8kyQzS|>r}@`M8s^jCzuW01wp%#(aUSAD2;i^s-2CFlzpHldlAJ-V2mm)kf>D+Zi1ylwQs@7DOqT-P%~dhS>&si7FWEJCTkqF>Wuf6l5emRJRU{%#V6;5hQ&Zo(2FRz)|yos>q{ose5c5df@NO$uI5rorGe7P;Xo*#7p|Q`)P}Z$(a@y=w7AAw>O!3_ZNXqrL1NTmB`k4%HQ9q~|4M+fGU==99QG;k3~-=r)-Bj*jO{}3%Oe_R`v#5qu$WMpD#xG|b5ve3Yb%(b8erjv7BUZCVcJIL)XsA`fCge7DD02hjqxDj&*#0$_S4jt7v19M(dfjH!(=-Mt0Y#z2YytL{@rHE!hzDg!Q@2&627~;LH(YwHqJw|QSQGLEm-VCs(c2NETGo%AnY2M{nvs&6FY2=gdBoCrM1t~7OkKY&Rnp(yy*1sbEsdV)8^P8f_p0xGYo0!$<G}oD&afoZfXI*Oq$%@!(d4nZhQS~)<_GWS*?a@A{hs_89Wazzj@x+_mb?-IL7HoJrDLy>?hZ7;fP$sKvmhOiR)rz(W9tx?@z1XbUKYPM*j;eR1&MF=Pqr+!^92cbXJz2=ar4D^LPAlJR&x`#(5ajtwykKxnN5UtVDlz!38QVN&EI}l#p9w#4fEIhl6s}Ou|?MQBb#xz?(4yKt1THAvU3YRCZ)fL8M_ylit0G>?{HPu~Nw>fQnuT7z=v>JZ>6F8!`)}tF{5S9Bb&|u}7)fzVzF>6|o+Y(-DD-QjHpzZLAWtW}M;*$t09PS9jWJNj#7FyW|<qrU7&CK%z(I{RoqoC1qIIRzZ2m`CND;FjK>nucB&Im>02KWVMLQ+>PJW6s^=JDsO*PDnTeX+at$C6hJRrIHD(m;_7!7P6j|X<^`9Iv1$ziRSYOmDKR@27*{zq=5(2q>j(Lw6a5feOe)lIxG)N>9j50A(Ju_NoNZ6sLX6CW>}V4c!@^_9jZf_%0<T|dce$C!3y3hv(gVo9zh*-6-Lw{ViFO`=x)#n7?*(FGOSYcKL$cXwVn(F@>@=y@jf&G_h;366Z@sz!^f_!)uW^58ymhyk`d)_^Q#RcHe7=(qpAlFx^_aaGN|{>>WFdvHf?gNc4xx~Z)9f&R%d8uP6=#`V@Z)@Swt9r1M5SS`7ZApc9u!1IVWViB3b(2yG}&Su$jN=xYA+l22#P6E(P#5&FR!jdX39iew_SVI=7?ziKb*7mLbz)ExZ#Xc9GCV4j+G>Cp)KJKo1f4qO9mZu_DPKKF%VJ(Vb!{yU=5Jr9hc&vACYQTRlY8K+7N5y2Ps{pr%A&G)tnkMwqkjD0B_RPrV@W<4xRqy>6K0v63?PWO2q5n(_h*^D-nk(`kR2Sw4kcGCoe)d1SE}FN8o_Yz16sqs2r$FH<p7Z;A=xoM(G{7q7`pD+L8Jww*i_)7gvxTMZmv;o{p6x@h%tYy^7$V1A*st-Vz0Sj2wZC)@D+$Kuq%~B9nRC5syU*R9hS=b-}9u1}Q}~6$Q%{1Ee8JC%|1$A;odu9~}Tsg}rO4g`#hb3TcT>0Itnp&I4m_J1N}wirzrr9j8%pzv!ff468mBjh-tFnbY_od$>&D&kz#Cp_b*O<5Pl3CnEV%?LHzhI8m3=9Fv{O<&-++<*AQ|%xSkO5hGBg#4K_p=iyyU>g!xxiJkM4R4zIRT!dVHOYx|f59uyUvF;~?i%p&Kz(df&YS51t?%UbAN?31{S7s!CAu=`9WMCUlEfLaqp@k3;+ZpGHbJf&>thK5+<K{KJ)iN6_FHy0hriQi37S`=PLKKy(Fws0y5FD_ggQm5o=4Qz&$7ZxpruM@bDDN_2&E+K&W|dGL?XrhtI5ZV<#EP(3`n^mWFhk_NF6Ann3f)b8ox;<k4etIoK7tH3`uPFUm=#@&`Dw16tTmwsFJT#Otn}~+ydFlyO{(HR_IwaVQ$bQV{tR5)s71l3hDV1FK)$mv2=r9EXi7v2RJeP*@uwkj-m^9;2hO!g&=M8MfphR)EB4uzLquc7|IlziP=B4mI7G!6Kw)w688Bku^b<n*4j5CjVUf+Y3^%q5-Urk@BAf-mVOw@vO0$Y63u~s>d+(a8zzPeHX4HV^kFeERADX~pB1fLgW|i5p7-7y;P{^xzXUT5!i&bL30&S?_HRO1V2*EJKEXBkLy0~nQRq<Iw6e<)vbd0o}JP<1@gCSR1E{8<8y9(E!h|~&ZOMa0`XsnvgO(<hSR6+g9`R6L}HNg_gc?gUT2rS1#8--v@5G&jOQ!`+)(8Y}ScFMmr8X@Bfe!#=-&AQ770?-3j6K4fCnYc|(yM_o=fO~;NnKGdx)M_{jwev~=O`Bi`sY|KD!C^Z;B0&V%V1rM+LSU3#P$~1q-1RFs18-;JWEh68S!ERxYgNm-yXy`%+YPPeAmN0i^&cJWm+(A91WVoC7I7P5#pYgrZscNlFRDjXa9-cOgT7#~O6Ck^7eejlLk9c4otL=<`f3-CavfQ@0U#`jU<a)}efE#(7MvTm!o4O4S~8T|4I?kxoU-|po7OWM1qsylbjo4R2yIx6@P*I=pth^;+aVrqXc&R(_YIc&@~e<LuTCQ1bHd&+Y*Su1(dx>#edR;%)9T`*v&aJxh<Z}f-w|6;y8;AKv4b;X>xd~4&)h2^i#93%Yt+D9L&9(30YrQ>_Eq$)k^)L!f~bgxL<;ORmyB(xO5s4L#U>QmNR0Skm%F+D!bia2P^ge|8%3e^Tf-CMO*G3;8EB1(E*j_MD`h7F%}IZcVv(etL>M6ZplN=bhLQUbNy)0eRD`6I&P^^{DR>pA=2cJ!$bl=U#M)Qnza<p&rWny?fpCbdkC|#CAon6Q6J+bLOIX%AfsmMLWs$@4x#C@*>)dyk1t?*VOKKoU1ir2DN=vs35AZ^S({BCOAolEM^!#YR?~f5J1kG*th_C2rk6md3>_)n+0n@#At$Xq4rA^iD=cjVlRfvawx?gHwh=S*8v;zeDZ?HlRCM`xlRS5|lY1C5A7LwO^7k4FHp&<A;2bAfXZ1LwAtdJhlT>*GdDdu;fFziD`)YFSXH{?JQ41tCshE7XDGWWs8cH8#*3t-4=7v*uh@D{C?97j5(3iOQ7O+V?*dLEiO2J^a<yyQ6O9<8qf$(x6)sQD?eSR&i5kYcD&>WU&ELDm@{gKy(c)<Gvz`yXZZkMk=l{K11jR0ACfrr2j|mk(Wt{G;okrWiZn2iLNEh$f-}SCpVg_^IYeM669tkbz_nyhEpDRa!wN=yQ1(t}sGgQCKn8JXQ&%csB(a)bX_LOhrz5*sh6P0HfPTSj8V@4@u)=c@R)Z6y*i`D<TNP%eJE9=^hkZK{&yCMq4XDmwvn)ZC-VvoVG2&3lg$bE_R5kjyj5$QF35Satjjp%+#9h9}-)YN8qKg^i(698DgMMo?s-#xOv?xy6MeL0Aj{vwhuoW#d8^(JPY&L>xf(o#ywb(=;Os>9Eyw@;#vo4*Om=-<C=+JTtBDqBvh#3lSVJ4Viy=8FV~oR{Y&@biG1{G#4iNSTgB#0MjPF2mKa5)p{(fqBWl8+$*>STKo37l_L^2RSrpf~;ea8Y${Bzd5)S(-V<1!b(f@fQiLiJ9jim6AU1fCGg68iCURzeCvI!XoH9~2cutbV>w*(dY_$Qmdzf?K)k^Lnk*Ab8iaWGcm?7PwNJtUm<PwqSkm@J35v&Oib+PrO}f(3mDuB7Q-k{aB63qG(Ikn~~$KPrsba<o|VudA`8H~n}dIhSWhH^<PcLGJRq-F)42uyrX`z0+luC}$114dPUWSfZ)aT3;_I+KCxH!oxQFNx=i0ofYy_?A|K@cR*1Wi%g+a^Z}Av6pbP>kkdfY6~2l;pm3*b(U4!F&ydV-6T=~oFq)Y;r%K!~FoAh1@)gOY4w)|Q*^$52otkh4T*{K4GeKRFkV;&(jK_lAC&mpBat@z=sda)qn46_uzEOka8iY{Vn3QXazLX#n<*cJJ-(9=vSSJ*3?B%`G@EsF1Ha6bC*uHSK+&m{M@=4{%q2(n2Le|wp3?(BqtIg4$s^;#{%}62q-BP;v(5cXmMoliovKG~<iH<!vTs3j%t96J}ZL`@^o@!enzT_E*3O2*lsuWvzBMF->wuw$^Y#x)&AHhk`VxX?6b)r_GANwh2A<y&0A+#i1@T9s<ueKDFyg`Us)tAMK_sD>ZfUnPy3X`rYoJ3(<Bixf-L@ug%6v9J87SfmCbK=g%kZzuh4zQtO#1SqMHvJ$?rV&kM-nQ<2_N)pQNo3MGAHdalGC<TzYfXlrW>{85Gr3pAEP-KM6yB(%DVT<?hc#hGD8DSZF)B5M*H<(f)t)KXLbTJyd8M`wSckI$yW+fqtiV%gNh|B-AqHek`$D;(Hd=)-2I*1UkI=4K!=o0Lv!BB;8ZlI@rpnJTEE}6g=P8}a>DO>a@<KLZt4XdqsiuSjQGs6KL{5z`XbevSM-G*4EMMkr|LMq8!XbAXbL&gLa>Ta*SB+OsErzRX)|ojl5v{nFJ2Ltwtdh`Q&ft@8$)7~%NE};MB1oo1;;a=pm=jHDoGYiqXq;LB%$qrlyCd(U=-?HH<fn8iAeJhAngJ1y3%T6QM{|Nifoz!?Lu*!5dZLd~h2c&O6OPZAUb=xA2NA2cLazYnM6T3RfKx3OMdM7e5Hte=f!RE<v#|9}6)h4G!&6w@X!4a)t~h@|kT1zCQX=hoM9Hp-S8sJ`SVw{8VXtRe#S0<WBV-gQkC-B$rKzC^yyNP%uU+G$)8RplMWI@bsS6dgLxI~*HE@?}!yzisLK4LG#Oate`=&xuDidql0<Vrr5hE0(Xt|RXtl*$p7AIs$OFKn|w0l|QP5zPtzPgHODP%othed!-c4#_0M+YOGUKTEUsvXX#A~A=LEk+r5d`VwuYL{Lqj#c#DYB}JM*S7z{M}Scw^)4uAtMu_MHY*<yojh)yfuo?6xn07{M_vvu<$o)lhryB{ke_8$S12o}peQd{mj>=5f4$~o`$KVa0)h6|@}Xo$jci<E0Jfp)c1yfhCT->O82ci2pZl-qNaqbU%cu>-IYs-gk$=7OoKL^w#9eGXR9=e4&pC4FO_RMYB6uinO|G-asRGumi@@Pzrxx+Dj6%41d66X%usn3;S1yK#Oj11Q5a2V)Y{T1<!eBuZ{rTlQQzk|#w%GH0)aen<9UwS8cq+5ShYMU_+fIZ&<M|1`njgG6tzFWyai%*Nlh-1QrFOoka=J2N({3Nfk*G*92z-mJN{k=?2gcq5gdB;wCgi0E(4bnSOS~1zl9Q+uswr4l9N`^l3r)pED=A|)rOBINL0K+lrSCZJxQYn|qw3GdqIOXhK-rjuKO6B$@O#n@QYGS(NIZOOJ*7t9K{v~i{a+viiE{?R&J-;x&rqw)9na)s8y3O}-W7puG8n4SF^%R&YjRv!j!xHQD-()hTAZ&o>c^YBD8()W0)n{FkT?pMYb^}emCK=pG7OLtHH@sTpUc&k)4k(3H5RV{7ghnYVsZ|jxxDj)@{H4L@?o^`f2OEElAsZ8LwX&!iC<MO+=pNVghI!Y?23obczIz+y-(DN8w;#(Ru<O<4UBb~Qy!v0oS2pM4)+UJg-uBpA&n#J@Y`k~p-bK%4^Lthv>H-qZT6T5GbQO&8d1qA1=!>gO&<aIOgp`sP5P49Rt==8ICjKYmEB<HYz(zes~ia)tGP@lR}L@<)I#)Zx7M(rE+Nt&datvalzzt(b&jWm`fs*mufVg#QHoMQnhzUW(iL@o<`(5mHd1nzTZN+3VHRDe_zj_U(T>_1uIRTwuiCp%e(H);)x`vrdr&nq?6a)|NwP}c!NV23cf@WC{9VbO(iVjDx!s4*Q@5^yO0Cl1Vani9^$`y{+SAnqakQ$I!xPqOFls|>F0dT-5rP(j6ezsP@V9#`s<iF$b)tx!ks8U3#@KJ=!jKVqe%(*AM(K}UDV19vJ@bj?(pwv)Hd|;D#o7kW@K_;gW1+|(Uzol+O=p-?v`{#GmTO1T5e+=Nyr~-NAus7<ct(&8k$FCTM@U|zsRo9l7l4V&M^v{3DJ$6k=~w`C-acGx5}MG2NWar`I6v>Ajx>UHCzuzSp=XJnAARu!Xrb$YtV+TK1TD{#zJ0=}YvKgg(8oNiap>CmX5*$hDX3;Xr-3Rel7xO1@Rx+F;5Y2Q!AQ~9ck=%M9l=L7W2IO3Fqeh4NuS07JsP+9Dfp>MOd?auZ(z4`SpwxKl913rrQ9qcGU^`Ri1^c$Hte8S?vaw!Mbhv?R)-*PR5LngIk7`yKsUAcx-etrfO2#|zQolKS4hSqbEBNV!bDRfdOL(|#&*!(jN_Z6SCI{gH7&ZBV|2y>ry+R5Sf+RvE1J6+M2;kc?AlulYz7-q$UxIz=}e$1jyhb)Dhv;FUxF^%<_5J51h@+FE5^?vFmbc!)iaRNCbh~xoJG~b&0h3mK~);!W@r#&M}}WT%fv{CutZiAviXF8oJQtP!URl7D}h<cg$#>KK^}N2ms<|jNg<k~DTd7jPI66-7THg=umf<Q+apeJ5hJQCX7C7!M-TiG7M0&lBbpxg*2Cn?wVt1G5~%zL;V?%6u5Bfy$~`SIfiTEoLpaH#Oq&#-%T>S?x-D6-(+alI!&M;EBDxZ$@dGSL7K*Pyj6U~hN;HOT&OtXS$E-x$&O3pYgyCp#o3>2s>Le=bg|w}v;@nLlZ^B5sY7~sfm+g8%V<(&_VNeA#q99D!OkPrGhZj?t_j?LgOdL&<A_191!vy+#Y>NVt!|&u$Pe<e1AGo<bPMT{FO#|O%x~0#byYrI8)^B%NwcK{+@a-hzqqP@m!SY?#Ni7B%BF)Z3+gI76rNZ%|N(7#Xi>wCl6uN%Bj6@df?Hr6c^^}q>QpVFtt_$g|Q+ozRy{bjOzSK}%REN`!R^94{Qvvxae7@8y*y5_qaD<mGcH^3}h9;eP4vi%#yI-m;S*AnER^42Vn2N)IAN4xomb>)aqYtqt@ida`ube#QiOh#%VL|q|J!-XNy6H_q&YP>evc4>Y{Fo}k&aW)=w%BcYq~g@8#-eYHI=Xn}*fyHm<!~fb2e(8)MU)rCS)07{@`OLD${wn9Rnu6JbR><4FhT=vA3VFoqtJPxdjBf=EO<UbRz|kMijb(En#v9FL2Q@Bi9z^{vLt;&wUp0NV~wR}U0oZV<0T9)j*={+uGAYC6ciO?3ck>YNi|pG66Ra*31u@4J6GKtR1jRr!{g0ib+TMmOCaXB6D;c_{UPFOtXc&O8TDJr2dE}?`^5u_F3bU33R*XyUB4d@?;OH~QO#P*q&&MObZ5G|sPWs_$}QrFs4APXYwNzCSlu)2lrG#wK*Na!2~w@;2~rhq40)?>`-38LIs-fxAVc|5)+-e&hs~-mPA$@O=-R^!7MnJ0M6D_c7M%EU3wGMPSHUMtD5~yuM@V`9g|!&T`IYO5`d55?72DVG!(R`dNNQ0WeH1AxxW7fr8s|Fo$ac+Jri6_IQ)6FhM4pgYc3c&e7F_WjqawEzIMZ1{eoxhgi+YkH6-a~=dFh6bojFrq#C!Bi?wdD4(VNLV$1$8Fb63Z7;P7fht9X)+9`vYmy#z>I?bPDQ1aoAdd^A}L!Q5Gp9g&Ak)(#}9_RdyxT(Ia!<uSp8J4J$$jjvjpGD?`rf=dHefwC;$<kG`_sC<&bv2VeYP#l^FcS(}~LVh}G(a=j|3f?*<xSwJ#r|Ksi{<f~3pD1JQb)ph<stOsQ(OsC9X^mq=ahamI<^XTURygs&izus|IY=j<qzQAua+@SSlb@7H2jF$8)l_iuP)<u$kW~6zD|NR$#7S~2f4d&>>t%{kY1h!RTU(t9o|p+T>kvty2TeUPKq>d%`Cy32$szgi+4CRXlSR12Tn-$-a<a==me56T;i>Ekyb@I}u|7H*!+QCw%x-TLHCYqtkV{!QLQ=-~GpyBlwi0u6_vY2<Gf;Ic6S%<(>gc6&XXJI1iu*O54&zX2E)SBULG?Q|qVX!*G<2J1sS<>Dfs)k}`#I%_3i9zxd-(YvvJ74WFADZsm8&!>mh>emf+%3*Qh88wd2T$_42$pu2sOK&_gK=V#4pQb5FJ%l7<UCySmu{ct68;N9x<|qhkHWRNYZwgLViLVB5T!|YE5vHk;VnouH_CQX%5m-@u$)yCsTMI?4EM20@WdrD&+@Wk)2d|uqGGx)yVa4rriqdKLYQ`kDbMMT#F%@d6Ss!c`L5$^6E_r8ZMv@^r}AG@}9W=!UsbuayZx}G&q=sGr%HYBNv{XBSDqQ$6oc2e8!yGf16N&mm4LN5~XwsnpskBctTJe_ZLtS_J(zmX`%+P$9aoW0BF|b0#%%TGhHwJa|OASA@#rplqz!MQJXS3tQ`}OX{%sOtMTO@?pQ#9&5ja@KUR4W!MsOHH;4^*P)~2JUmX4@I{FE53GvetdKSbPj8O<?x!ojdwx5K%yjX8S-VY_EPfS|_-q7^2jKTEt*p#iziHgU6tMtaEoC|^P$14*kXT{`+vuLYNZWmJfC~Qz_&V?6B#*?q8&R%ascDhqf^a&E&u#bbOcMKYLq_aSN>JROs>=l+!>5XRd`>wib6`vMkX<S>3&Y(6M%_1B>TNZu%!Y}^|#1mf!")).decode())
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
_V17_LEAD = False  # V44: 先手功能由配额层吸收
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


# ==================== V44 quota sell layer (appended) ====================
_Q_QUOTA = {int(k): v for k, v in json.loads(zlib.decompress(base64.b85decode("c$|Hd!ES>v42EB&;=BWKLP&OFQ>LQPA!SI_`YILgzF^v7$AO!P{D1x($J{HWs`t~qx`bi;Ns)rLQ}q?%)DQhF#O1`KlS@B*r`V?OdJf%`Vn3%31*ql%%o@ib#qLO}3)=QbU<!hI6DYS8#y+^ZSsNv}oaBfCn|`8}_;-rk^&`aiw{(R(%XsB`V={U%teQn$OL<=4Y9g+wSe8MY%W+g(K=0weAkHK1n8D_7Y!B+=S%TV`<&Hm4%%7Mpn2en<NQDOwC=g`B!iW|2AHbETnL#BC?x{gs;L0;}zR>1bT5lJqZC=gi+W`%=C-Rji?!?0eO;<-F&lcwEgh}#$pxcY>WI(na62&&Q5&o$|Xc4$B$m_7lI{fTn9H-JMf*6UR#R2J_(G`wEKA=|-Ql0Fop67pBeM&U")).decode()).items()}
_Q_STATE = {}


def _quota_sell_layer(obs, act, seat):
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
    st = _Q_STATE.setdefault(seat, {"owed": {}, "day": -1, "psum": {}, "pn": {}, "last": -1})
    if t <= st["last"]:
        st.clear(); st.update({"owed": {}, "day": -1, "psum": {}, "pn": {}, "last": -1})
    st["last"] = t
    if day < 11:
        return act
    if day != st["day"]:
        st["day"] = day
        st["psum"] = {}; st["pn"] = {}
        for it, q in (_Q_QUOTA.get(day) or {}).items():
            st["owed"][it] = st["owed"].get(it, 0) + int(q)
    prices = (obs.get("market") or {}).get("prices") or {}
    farm = (obs.get("farms") or [])[seat]
    money = float(farm.get("money", 0) or 0)
    shed = (obs.get("private") or {}).get("shed") or {}
    mk = [list(o) for o in (act.get("market") or []) if o]
    selling = {o[1] for o in mk if o and o[0] == "SELL" and len(o) > 1}
    for it in list(st["owed"].keys()):
        owed = int(st["owed"].get(it, 0))
        if owed <= 0:
            continue
        pr = prices.get(it)
        if pr is not None:
            st["psum"][it] = st["psum"].get(it, 0.0) + float(pr)
            st["pn"][it] = st["pn"].get(it, 0) + 1
        have = int(shed.get(it, 0))
        if have <= 0 or it in selling or len(mk) >= 10:
            continue
        shed_load = sum(int(v) for v in shed.values())
        base = _MM_BASE.get(it)
        # v1：默认货到即卖（先手）；仅当对手正在倾销该品（价<0.85基准）时持货等回升
        force = (hour >= 20) or (money < 800) or (shed_load >= 50)
        dumping = (base is not None) and (pr is not None) and (pr < 0.85 * base)
        recovered = (base is not None) and (pr is not None) and (pr >= 0.95 * base)
        if force or (not dumping) or recovered:
            q = min(owed, have)
            mk.insert(0, ["SELL", it, q])
            st["owed"][it] = owed - q
            selling.add(it)
    act["market"] = mk[:10]
    return act


_V44_PREV = kaggriculture_agent_v25


def kaggriculture_agent_v44(obs, configuration=None):
    act = _V44_PREV(obs, configuration)
    try:
        act = _quota_sell_layer(obs, act, obs.get("player", 0))
    except Exception:
        pass
    return act
