"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%0RpL62QWZiWBKKx;45YT5E+C(AvtFtS@{NiimdU>L{*0fNcG$u7u$kEHH?@7}79Jcq2?61?)Y`n`9niewdec*y$Ye;@t(Z@>TJ@4r9#r$7Dj==JkAZyvq>>Q9gU<G26%xBve5Paps1AHV(npMU?KkN@|}qwn7R?bp{g*WbT;@%GV&KmGi})$@-Jmyh4S|G%&PwEMB2u5aG{(E7EnKYZ@?k8iH7zTf`k+4PqmuU=jM^x@&+$)`X4@bc#BQR(U9k3IkC<&V!_ef+r>*FS&w&lC8|n;)*OUVr-AG}E82-n`vU^utoVeDT+Jug^bu@#!b;Ke<_*?LW?6+OL@P=FKmkfA4<u7vsw}kKes}`Re;$Kj^^QcOMr=y!!R4=RdtYOJEqp@LT)A+)HyBOf=pP?|N|+FUv2F-dw$UHUDy;UKb$2=WnlWCJ~Nr4J8;&?ZxwXA!)FdTyK921oah4V>{H_r=>*$wa+zRqt*B8xEJba&A}L!hWeCDlmxta?Rjy}<A!BEV00kudD~@y{^jGIH*OicxZ~G9$B;9D4#U6w<lzcQgUWZ@QSM(#wA;<({?E5RJIgx}Y*kLUZLk<gWJL+^FVBySmo(OtzA}F9L05NvJZg2Xp1+wD=hK&0mUgpt=NF_ayZyKB>s#yDpX}Yg1<QH<^8s(zJcSE(_^YNxI({<YlX}7AMP2S*H}1`jhd;gK{tya;el<(l+m!APlEZ)Z`qite7jJ+4%hk=>m#<#_E4ZoSFYaGc_UdoliOu_NPd$DmxuV0Yqa$^CLmXXN!R74mYA4uJkHEV}*8-(F`w`&1kOpzIkuGpUgC@rew+!(b41#mj>`Nry&b$HV7K;P6wy}!Ew)e{WBZ+^uePF%0em9%d5nDTMD^HeR6znEv{04TDZ%hDZVK7NR@L9AYSM3K<x`UM?K64h8!;R7onAjidXQyNC>Fy=t;u1c4i`+h_V^%!SUB9dxg;ostU{9fHFpPoZ7>qI*binZVEUzqS0*1Ne06JHO^QkHD$TeM97{Bdf9pUw=5wBYx57?7rbHz`u`QiD^zc@1x9?=GA0i41^k?hq!jrk~zKTVDyhzHmR7nDEuKF*Roi^P>N@28i>yKJEc8|&r!dq;IlL6VmODaFI1B7a{WjbQDEamaW2>55M+OM-`~S9~s)D@VL$-@tXZ632@U6$eRKI$h|;?DOjYIHmE{#>SU=K{$+#5xHrVqdc(Li5wpLh^d^)?g$J#XbMbPk@)6#4AKmgs%sx+;Ym-&jeE8Upfs7mxZR8M&0KX<EnM7m^&7gyerK@e-pSK+eT3WPO|j#c&SN<0CE4P-$G7Qy(Mv^Ka)kF)k@ZHv98@kWOzhrl-paPK29nvK#8$m){*dqyw?B;Zx(7t+zrVSDJ#NPjgvz#GV0)=shq?8l$#4C7_u5g#4g&-a@J3MzGQ;<fu3_SfcI@Sx&C7hw?k+%5+1O>l>uh`R29dPxj7ou_l&0N%oTBL!<uO<wM+R^g{4mS|H+;@~qa!~{JD6*UH1M+c`v-Ynn?*Y_3=<VWGU2^*(v&87OtW9GBue&a12w78CM&|-anS;YsR_@SmTLK?{l&<Ii{6$QzS!V!{=*L?*@da)U@`vivYhgFo*l?T(&Jx;FIr5GKRxX`3k>InfJVD6<|5!}ZWL{omecMJ=IWw%nBbz(^fRALn)q}khT|b$Ps|!?XM)527*v+TDnZifOFF_lzwP#u>J>e~QR<C1oUJ$W=Izb%pTE1hx%nGw5$&eJXNw=(^ri@UCLDTkM<0Qmvv5zo%Vy2;KXgH#(dFC;$z_3TYHG6dfW2J&l0X$W7Okp+q8E4Ob->CZu1Kr^d!kqu$9&*O*LLssUYb@n2H0h21MO)VyUBtI(QYE3>#AX35SpN`hbaheU{B+hruq>&q6hez$JPWL;MdN&KQ2bSgkAcbjH^q~69tHV`TW_!ffEdRv#;dCzBGnSPx+8NYr~RUc)#;G@%~^vsB)P`fUa9{2o;|U-?FW^ZhTJ}@BOy)^Y!&dWxIH6?OSsjf}A>tR3#NIZAR27fjU<-d^iX1G%4>~vH1~&X$i;od}`6tS+nEM6*hz7&=n_+Mu$^7o5w>;V-}+U>hcE7w!iT#Ff+QDsJ6R&-fR9jxj?ky9GSBmYy@4!oKrPpU=dLD2>(RWN@%u?eeN!QD<Oe7;ma*V!p$+|Wv!b96nGM*a#r^+8X$X5Czf^lz_%1<8^n9jHejYejnE}+7o)lcl%R04BNDk_WFms3>6r)(fCEdSxJ_`1L-?kDqZLGrxC}MI%t4WZNrD$WTIwY!7+DhnBzF1p7$%gXA?wgUX69oDRI`AIt}c|E1YCbKCLFznk@}TMTYC#3;?T=3Iw72p52=L}Y-v=~17sgmEt}{IQz^2dk97enXEd7OUEp)8(}mob`*aAE#_sSC&hqYSe-1}$vP_X)5R9(+?|D|u`{n@!ADeYoR5d!(j?H|YPpb2u&reCZOAVlqO540IIJM57-8|_y?r=<J=YWSkb@=Vz-%V7efGZw`g6ObWh1-e>UW=i+9Pwm@ae#YTUijVR8D$Lo(Fsx+Guk>g!=fpj`Oj8}nAKEt1t><H+8Llfh~mg&tP!ZXDa!<GHb$;|ak00d`@|j4gc-}6U_UHXKsh$^i`K>F(;g*se~D8TvwSR!-ir;eN7A%0D4M<?fG;c;`yNK@QK(5@z#HNgQ|aK)q6F}?V%8K0WhGhXFNrZwqBvg@jDd4FSkp-QEqd)mT3}Sw7YRAKxI?xFAl6`Gfw8~(xw>`Yun1f$z8{Y2QOg#?a65bd^>F^~S+I-AIKM$cHQn!3S?veDLtu*d*6C>a@#U+(KKj_jE(#|Vxi)gNrk^*;o9-9=?pqgW<Gssa;d8g&x_LqMEMw4P`ziz}g&$@&idybyis`KBl7uJmE}6M1#srFKIrX-~##LF^O8#ti0R4Hmk2DiEL0zgV1+?Z?W8%X@5?ejTJT(4g1}quGd7i-rt6G;pw~Zw;=tgX!>N5SAsx*#DGY2lT1d{z2KQx_&bs)kePHi2bj#-ty5ONH1AKA?oovOa*coZ{hTze&(pfeNw*BI%K*S$mrGBrN1M#@d|@VG)GU+0D*qx;z!yg_>CCty+5Jd9|^5Dd&}NQyhRK}9WWXe<WzP7c3+Ro>uC9Ph!Ie#8<RCB8{sUI4~{y0h7}3SeQUK;8D&S||7vt;n25xo7YgEg7_#yog$s@$^cPm&(YMc&xe+J@`hc2U+^L{u&S7+dr?@h@79g)gqU{#u%3`N8r!F#n(Bmu$U3fOFHPUxieOt=bAG~+y)xfCUz7TSr(ZYNH>tA1{|Vfn3u!w{<>DU4SH;qM^knBMIVZqBlCLIelTTK#(LEp2+0$CUXKw`{Hzjqnq(vJfc|opDmDzCMP%{WXY;tdnCcUBK8`D8kAR_i>|0gL^=-Z%&qvYuicU9OvRN))$pv@7O*af)s5(U=dTG07!)kahnCX@5US0tgmo&9D5P7U|D6KR-AKUW6N@R^HQ;>T$IpJaz1Jj`j#lUh(8d@xw%?&9FgtcjL&sAE<8YizR@t!I93hU_sR{&^6Grl}82Q3DIf`3H8wO(AcX#J5%`r#$ZCpLa}<)Rx7mT;PcJu-|fY_!%}?O@zroA$No|I-C18X93RLt@n8NLb?hwAjFH|HM^q@t?=Z>)MWeRz8CqXs30nR~mDBAo%5y=6Qa@Aq6^>N5W;QG>2B$QF&w%S0JDoV&O*@GTUF_=|<<&&Uu+o10e^B`{O=rJc;=8Q4=@HRrbe=o^kYQ^yBho8*7b>?GdZ^13xNC6qYVw6QhjUO!K3}?{2T0zbD3xa)>s{{kI~6#g?neXTXsKL|dMOUHP;BTJX<AP}_qcQ{1Ok?Md2;7S@C_7d&1zIz9ay?AP$LIrj_5;fch|8D1LZr{$mfOjN2kFW-_4fG}+a@jTyPN!)u1GV#$`!20UNs3w^WG6K&Jx<Ih*8&#jMu;WaZ1w8hzcySFkuSlB)g3AVl;96i=;u-ZIK0>~NXzFwu89g#kRmtdH7GK&3iOC(x4XxN>1?i#=lLHU_V!ERqh<E4tQ4=A*08aaK@-hh~<hwWom8GN|l{Slzt7^n&t(=_0;_jzz%|%cTb=wTQNJPNd!&)_lO#tC$Q_kw|f}J5)VM?h|=kOV)11JM)oD6bP^dt~3?2+)isVHr9EgW67C&DoVBk(H2{oo?$K{b~Ie^}a^Yop6v+!19F@YC^zi-C=cwt`q@9Xj{UXpxH~vs?zD-sx{9(L%xA-A}Sms&@ptNmcgZu8%p?(o$K;UctA?*<^UeFj2%DUuCIP?O{Z<kp(X@aX5Zg^TSdnE8HIM=jDObC2~VJ7gkXY%_x|k9MHaiMOzBaE3Dg6hKHArzQCFcLpF3)ak8uqD}7mDQ0M5F(<fA#6cSh$8a22OS-8fbVHA2!EXxVOI1J{Tolsl}ja-TBv=f5i!DFG2Pc|Y(v0p*>aFWQ&o-mTr6Ue`Rj6m|;v=-WlP9wo`9VjK<3&h5jY(0_FWb@~QM5M#*RE_C2)#)+Bx+$r^ULgbe95$rbxKcIVy4#flUY8nkY`FjV^eZuZhJQ)bV?Jp(%3Nb0DJljl2!Da@5YpK=&8qc=zINka#aX5eew5d^N6t-R&CH&t+obZyUiTslFFgo~6vamGIz@O@?PwC(I=Gel)a?2jbxMj^T+wIqk~ERe-J>>;Ly>tsac!ktI@cz+==udXmFsnU)f#!jb*Z>Hi=xeni0>+3-11?9FE&4+@tX{R2)El)8IQHwB6@%!mMVR#);I<BLP|Ot^wj%Fwf`z#0l%!YwNi_em(yEGLoJm|4ZfbYnhHy$ZBV5xO=<xBo8s=2fKeK;MGKYi+7v)Mw9Zz-8&&ft_Nmq#5PAlx>M1YInZhEm;G_-+U(k7aG`c0qDJpt^Rq_c0+*l@~B$1roihm#NUVW_HfNsyD4qPh&uo-qZg0qk1H1UoYu6q?nLT3Zd_PlirHeQ+Gl+GemG!XNTipymljl|fI1F9KEO47)))k*kHBNt_76tY|Vm&PJ?!t4V|$vFDdWR-n@`RvmRKTn9h6qp}Vaut1RT&&j633j$w;CX=VZ9j!OjL~}tJnuAG?^o{B@NCuZqtUshG3GQj$zCpr2L)zD^$^T5>G7$;>=}`=s&;V^d8er3Y>p%^WuWYfpN2EKz{<5-zK9v9dTbtYB~#<wr|Yk|y5v14TB!_r66lC=`R(7Miby2sF!|h0V>>`Wv0GLiy9ml#4QcYAgi1?Z8!|A;R<lwGF=Xm-%9uMIWFji^q7yMh>^7Y<093yaQsC;!8Q1pd-Ir-?d7+OTcr~<Db{KEBXrdtI2o=qf7{Qq<I+I%4Y_67UIW{$iQqG@GL3x)EHka3%cn+2bj@fB4e4Gl)LoD+VLB86$1s*_8{q>cWyA=JKNW>|MO<E3*a`@t@cnk;9UhZG*<{Bm1xiq!b@FOeR*_WV1g(Z|;AczBR15%-vs=koDH=_COMzM0Srcu*^dt*Fu>=$r5+{@_$kh~RBHu>S`8hH_&h*+rPdcGk_3a*$4v6~yoH7CR?uV{={{<L=Xk(+~ABNbxmFCnPaP~14NA86?*1;FSJk1&^$5y+>Xs86T^F4gQoWd1GJGS(j6X4C~WoCU&Zlftj1nMH_*#cUjUn2KG+J_`_S)RpN7^{wh^tvONP+EEljYIBs@@-V`jvmo+U@!OK#298{%6fZE>K4PDfPH>SF?Y&V1vZl9%;4&gr70OOJO4?3_2+PV~)gv{RV>jGgg#%GUo&~cfxNk=_j?=7qf=J&7zCkAz5d68kJV0gmY^q(ApuwnzK&U(nHCo&R5@DKM;SQmiwv##^T(HpQLX>7B##kjzoJWu}@A!f|3FxP+xygbNPLwdGIY)$y-15+S;Wwh0!SoGOAg}Y#loEEfaJ_H?eYP-bY$Qp{ksyU`5Zv2DOI9QtF_J~omhkmEWCNFK<H;CiqN#form(ax)E5ZJb;IEug1DP=%{@a&rd2&1v6P@q1V>992M=P3#0#6p9J%%jyAQ7?8vO|>9TTOT3a#v0L(r5iUZ*uJ+C_DHAxZqfSN<~lMc+c?vEU=sH!zKZg6d&azkm79>4u$ayn^CN(TRK0xr{q^6U?i6m#iTr2KE$6;TN?dfY<^ngEsU@I9upRP`}{2E}hdIBO~yB*CIT~lWoH8Jy^c9#R{t?Ls32`+sR!_G!7JlOBEpy^RaxfUA_cX%IgBUs|MV{=!`CMbwuJIX&@oYK{c*GIRrqfB6Vkq*cqk-c60ZKwB0BQtuZ=x?J~cOClGN4+5gd3s)~$(jSmguFY8aGV6E3iHCD1J*9Oren+<A%OX7o`LChQdD8VmIwoyQrb45#`b%2Ic2B>CSus*zW*P!1FpV1*?u0y55NP<%r=}%HvlvEFmi#K~I`*%Nf9pjXAK(o!=m!#;q?zD&zQ(`>1&#2(cphzU16U;((a1m%gsjfqDLCZx5X0zbt$f6wyQ6E`Uwba)_Zg@&KWDc=IT80w{gvER|4>@!KD!vUm^Znu_0kaqko*JwZVT{N4#HFjf2f!r4skh#95Ht6)qkb&nH*ARvL03O`G-&km$IeLs8YO+>pccX~5#tn%_SqqEX6?3iPfNudsA5+9)0LP8W=Q2L#u)LCj`oaT#|~_2G6JENROyni#Kz^zNnEN_s~X$usuw|%n((x5v+W|!`Gu^dJnM0Kah1v_?oiCP)iU<AiV6fC<+8!(9x|w&A!w5480KshL}_F~vQh+ea<|#s-OxfIgDBBtLoMucbmgG7yc|J0C0?}r=r*r(^FB{n9l?2pR9+(=G-=m2`{dnmj_B)BVje}7P$4o=KjI_G)daz606zX4f3l9M)wZ!JGwX{ZY!rgwF(T^IfGb6QW3!-bhiDzl;R4!Xz9<huyb3>PleLPo5X=)bf+9Vuno|<U06Aa=?n3w!oxIi23NlBZdBxz05ul4&n^Fg7z+Fr9Er|fCZ>cM-7KD`3QMT5y3#)Vw6{}LHToIsgzC1LkWYzN46e6yvvI>?6D9hbexOBC{g^vqbQT+<2tRL7%J6)aXsMSr7xWw2h*R#Y`YaP3n;e4QAa#s=v(~_C@Pn7MFN4TtEjjA!!%5^h7D}^DW2z3dvUGYZIlTConCY-Lv<M3S0Ela`gU~&gEJ>Gn+DxsX)HRzb=ddDj;l(3DH5xHWhP@oxEhjiB%3@+=UB+r^;=0S48RYGPPK529(t2WJr6I0BATPApohWB%fB8Mt+AqJfHbj~~fHhM@cWB@C?0-6EiV0n!qbORSd5Ae~)$+p$%`i#SMZZcu0DmiQ-+!YKQQ8HYRZ;UA}A!PP`H4N*I51vudLSQ^8VrCb&O}m!U5gNg?!7F%bEJhh&Gn-23oNP)|yPx<7K5Dia$;sV>R9NSquL1{DoeF05pOk+i-V*^GMutqIFz$!QIEa0QPM)4kY%Fd?GumjqDquH5K%|YrD|B+W0IYxMb8wS4`1?XM(j5;Ry)b&sL3Yu`vPQ_?G`o^CZ<dg5Govj<o+-PtBT~G$YgR!*tZ=H9!)ZxPRKtd58HBkE;YIDK^~pb^$Sh`diKxKvfd&6_RVw5v*^P|?mWQIO7Kvb<Tr{bJ#w}{15g5sdJE_qh#hOx}TxK-n+2~^>^ZcyClY%AkHY1s>Ic(yh5>GDZQz~*DjZ2+KUAVY2{#r+SLQT-fC7-IlJ!ya_F3raS!|uXlw@5HaXZcPN!r~FSVs5S4*rP`6M}Z`z4NiH@=%xumSk4?P*GuRq0E^k;1ERbq8*XW`jADAUO$TcD)Y+i(T)0Tu`Bg>Z$Sji-uqm(NLf|IDLux!Wg$aP<{GqByr$%EcJ<=}@y@-#r3W01~%!8phYC~{PQKjgcmBVifj)t;kr2m_}*z&yRA;XuH5K&rbxObJ3A8#f*N2tUIE0tFAK_?J*7XaB>hmI)j=T$@*G{aJq%k%?Rg^T2g)j0l_R2tR+*Du$Kg(GjU-;Qd6<dJhpfsB~6PlyY%+(&q(Lb*n)YKNna2^&#Rrr;@>vM_$|*-EJcVpYeeb<PL~u&yFYDYP55h9K{#5nASCONcSS`#N?LX}L~$a51S2VYRg#lLV<LmQ|Tg4q7o0Vkj4dS;|@kt<?3=7W4?mFUz-#!eZe!7S%>IJ`1)G?e=l%tnEeCLAXG#IFBN0KUGTBN-VbNYp7xS63w9QUj;`7>s4H^l21w%w-fgWk7~4iKY?X*9}z0%6nj;fREA|>^Z7i*RXIH?9**Q(rPY>1MU+Jpv}PqZi>gQyhxK8m9^6|&D}wwueeXrNEZ`5vj}uXWdjWvHJTb?*8^GIq@!rwE8$hWxozR@F2&CNWbVGnss4KzVOpYKomp_R(m^dw+a9n4K;<O+6x(j`toZIunY@8YuOguVw0Yr{c(bvqU6hU!dHGa0d0=}toycMi;w(@f8EKS4`_1$GY5?Qk<R7OXr3Ll<2gv{@VbS6uWOG6Kqb{KZ$Rw{B@(jB08siG%Gr=~N45t!2=SRDp*w0UDF(p#hsx+9g?CUnvm%oI8*qww<pIvi(n2+^i-iv&@-kXAC^Vk56wi*=T0mi_T8xY#y=Z9@jR@+2yPbDFk`c?C3R`@Ts|!A&n}7=`Ngr*4wf9trM9Rp?6EhC>x2LlOlFiEk3^q`M|bIuT;D*6S^NN-$%oSb*KUc+pBo{+K9^%)P;24+sjyQKV&5TUZdv$L=4Ocj!#KhUz{*#*{U!9?S^e>`<gwMw5CkpC>M-tsPOR8bpU}?->nj7=eSCca*1V7%H{gioabgi=L^7<9d8?a1Gg#K{aIM5`ZGlZ3La%xPIS;;;4%g?ki5+jK0_gF{2`w_V91{(d=3fr9*hE>Kc0mZWPB$nyB*`QRq-}_x-8JRLNeg{GIJs3Y+X#lg-$hTHVvp!Lq90NiMO-QG*AumE8TtI3Vw+tFS36Oe@+<jrHw06MVYPg6m18cC~?g6fNU(eAE+@Z5I*X72kHCllbWZ9A_7Sx62+iB7hmebMyEhCJ_*BbP`<}L&WPTo{or58b#gV^>1OMBI-%~+AjgGs|(#^`#K}HXdRGx_G^a=iVn|mwuaF71(NST2P>YWpcVR2wbKPDJvUc61~SJmf`w{lkE+%5L8h2^)b8@gfw9Q32$YT$Et=HmDt}ssA^AozSb%(toiqp*69sd~6cUJtU0^<r)}j&-KY=Defu+LJh4Ubc2}fJFr9kv_Gxll{tKIeuMsGQ{m5U5`KUZ`<m{ngQ2X$w&aM^|w{%Bk@L9R;svX!`KB4bnO)OHj`#tby@+z82unE^(-I@uEm0;M>u;vGi-ZzyJ6P7qLs2l@@kW-d%i@a70$l)+q$fNQi0vnEpG+Dz3fs?~r}t|%r)c@;E_$o^nBe1?d&1BEC?aBPHdXv7f`P;2DDPG^ppl<|$6Kx1Uv{T#c#$nz6LEm9p-O;KqmW!SDkx2ge$HuHXsRI6y3EU!2|4zPiSrAS6ixN&I%ar5k|+}$KZUU(dR0VL5OCp%GMg21;TwE;^ZE%Ze&tg&zu7mbJ}#*3ZPQKCtl=(Y8WH$oGd70<kKTXysEX=>(Q*>k8+AWU~t$xIR1gi)nf<bxeeVLmFoJ1DBrCNO~<w`e-ZY*S!$h2N&SeJwKG#Kv#Hf$mC44MyZ!DJHi4M|k42=^)+bXxbZ&D+lES(jzXMu!y>X<%Z~txHy7cy!1QXP}eAJxc<%iBr52*dk2Z6w22~Fl9Y|q>5|d%O|V61PTZw)C&Y&Y@S5DV<a*5t;f*8z`dm8A*TPlD+Zisvf2X|<^C!BSzPE6qWePnN$VsLbk~<h8zj@FM8rx)*YT#4;1m#yS#mcSe5Z%;djl$Sd9*m_*W`%VSq}Ni%d~j3gVj71j1xqafWfGMeM5m6r6_m{Fa9GGP6Qc^-ro78(&&dKYNs&oWe35n=SC#SaqpN|PDB5wfj1&T3V0@%uNU$TnXRTSx_oXeRa@DV=K9MXv+bH$cL!Bs=@Nh293cMSJB7qK}`s$c1aP}-i;Y4S?I-2-u<RQwNs$ma#?K4AEg5HXC5#x9EBL_CraydbuOxh^S97#l`bfMn(>T8i4b<5$-yNrwcLLaFx5tFt*mk2?AU`Ab~1PfG9bu?j=CRIE;<Etw}-vxQT1bqmWs5kod5veZt6x3HA*0JWHyI3^4vej8+HT5}7RB_iNx^)2IO^g*B53!p)dG_ho3H-YK%a^#gV5G}d?h_a!Txf{)RXm`}@uXNn)O;LG^1e_xDL<drZ>nxmId)`mrO+p)lslqB>T>vq71kYX*r~PL(kLq`rs;>w9zo)<Q)3E3LY0agDFa5T#rg$NdLe;8D&!-YNnA@D&#WRCD5nT@QglM2KZn@T*t`DQapH@lJW?*P3y3QhFofg*r#L}Fi<WpcN3@+bh&xG~+uZ|W^flPJLf)cAbXTHjaX6xhE36<``x3sI$J2M2F!N4vD#9V8Sn#Vc@D~A*OI@g*q?8D%7004vRWC<b6DDJ1)VC_5bu($e10pl20)R^UfJa1hHqyC}EGpFLG+SR}3ur9a4b$cei6ohVov1{Xt|1)Lwkqoo65SLPJF4U)oMKzco-}J;q=(f$5nvo<Q^^?^1y4>;UL*Q9W;ZEIfuVx0hHIWD7FQ!8X=@g9fD6=5pq1F3sBsFZq!M9IGc!C=skQP}J!Ar&khX{rn#u1snOzT8CR%8=W<hOL5*kA~`&;?$PTyO!i6FU)qcFLH2x&-`2%t6D+~F7i?a6LM?}=#7cK<pM#H?foO?sQ-(N{QN7AU^bAc5a3-GTr@=Mrce#~yK_uZEaL_r?WoHIp}(r9C|g&E#XHOn0Yp+M%0O&e*#bihfi*nkdAK)*#N3in3ojK3fvt#+4DeRxuV-ate-Q_7kZSZG0*Z|0xD?GUliA{lgF3T+c#tA+@H?Z#fP!+Q|bM$zSaE^Q~%b`@V&(5c1i&a;a#(>;EZZped4cJb{RiU)7Nq>^`cWVM)|*CAhA<WG3LHbfXp-fLXefn+C__PHD4b3zd<|l6ORF*Qw$JZ9nS96Mea@y08?*j_O|Pu61S@ETvg0w9iykSPProvrOkMheWn(TXO@^05S(8niXH8kX$_EH?>dJIMzV<113SVXXThrMU(^uFha+>9P4E~e82{dGk-h~C8sc_Bzi*N^SNN=Jzkiyv}|p9dvMOitUOs?7K1zlv%1AK2%Wn9%V)oEv)Ipn<Z{(3DWh+V%Xe@!<$fpLV-030*fu!bW$7dV40l{Xi8U@AT`7^2POI?SRbfxHq;MHslYX%g`9`S6#~1guFafXSEQkG5^jUD)EJblI%Z!VmqSlcr9mt-6T`DRh;dk?sq#$+IN0trk${?@7L9?~<%?98Zhlykco^M;I%Q09`D)JVTwGqLy<OFGsVtr1Ht{HqnX`Z$ge}1aRi^38r)DOJ8vPb<amvswu>3|WM7cxc9%B&#R7mW|JzNxF<6o*fQz)HdTwK<Ag&tY$xTF?Oe6in8sDazAQKAGyL?ef$X>(%1Ub+>`}-s6^KXw6oYQaYdBK4h|Y|0vsBiP|^kp1fF?D{bj=4`a9f0XwX3d>Uys*vM+@S>Pt({*_-dVSiBM?N?HF1vFVc%HqUgp8>N3l+)294qcU;L7Qs0mA<mQTO>u*in{*8Iya8OyO>E=P4CQ^1+n`aU;lW1a(!|CzRPc7rJFzeZ1_Y{TP6;v%W$G)k`{O)xIIP$GYm0Ps#*bsDMZ9Xo)5%p-{MCOpV{f43S*Ha7ccHBQp};wA?phw#$SwTi9ekVNQ78<aaN>2)Hrpl$#8EQdK#Y<E4&TfkVUIG8HwyIXWtZ1apo|-CzDb>Mi35YXtU^sjETQdQrgUDjoaz*lbYukjyM6R5UOW?=7xq0p*#Y$Ha<}&d{(S^pFqbj4}ccjLmDWl{ZTe9qn@Q2TB-92bC3n&T+`e@9riWRV*?~&v)qr@u>?UMQjD_*7)w)0LSW<zph=V%M!fI%gzM@-KqZwr@Gsm_A#mO`wJ^_YCLdO)G`bVLWzaR^Aw{H$6rRKN9bMrp85>bnM>ma5AZ!cjf~9v!GA}<<lP>SaEv>G<Aou2EvVvmOZ~Lpek|IKsCt$Yrh+i*X0#MpDv~+9Msel=4^&^m@3=S1qZPl?&9Oe7SCAdHRk0(E!pW;B`4m!CUR@CkK4OZ4DJG)O!JPD^!<~r@`BF7-H+|Aov1yRcuFKe_k`;h~=|1*u;VifeOx5@cYhighc6C>rUN``Jb?^eSc-OTmn^a<X&a1q>ZH|)7P%8;2LaDTaywJy3AO{ll-wTi+#wvQ%dx7YPFS}Cltwt2EJLCOzUWF=ysRj|<7VmwJd9b%;thQOtRO<1LjMNgRX2pb7Q#V9e-+&s||$Dz>`R<5+6<%%0rN$#v&ux2c?gl)?eOwq*ljR;&aZH01LAUbBT#=}WQ_2D0(!;9$xa5crW#c?#TViUN?8Z=2k6FFt5705_ky0s`RJ+%OB;6OH=VKIqi+R;h1PVUvSSPwb-#PP78UF4cK4Cc7bBEe>HaNnX_klvY8X|EJ`hdxjt=CiDNG#TE#RvWB~%Q3wIwZhUDFd%xWPgjiH=NFw=IG+_W%CUNvDB~bY<Gk0{K@$AQC&o^rVE5(g()1i5QSQ?})v3@#VZ6jR0na!}r*Q+1)SI3dsD@Mu02Id$I&Zj80o@~T##tRy_;STOir?gF$iPLRS>-HApaW_ta=2HkGP&R#6_A<8z^2vw@(*`3pimWpBNG2uCB+1Ck4!g+c6d_X-(0_*{!uh+6~iUmR15Sx5N9$*A*dM)K;nWXkZm&I)-Q}uOro*O0zXmblc%k|;$m>9Mz&?GvQDrBlmbPXu*oyde(e61=N&OzcLfyFw<$uQ6hv{UVGz@p?^jW#!OqK_=U1ayCU^Knk~+1D&2AF%oapoD0}wp->1f-^?OM)>ynl2~(Oh-YwCEEw0Yk4Q!;=$qGsN3m<5|Z@UMj(f+NRvuL&0(K7*O%mR7#yrD~0B#+Doq=O%CpmS!liU1g`WeX(0oqHKQ@(zWDzC0i_)7{r")).decode())
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
