"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%0RpL62QWZiWBKKx;45YT5E+C(AvtFtS@{NiimdU>L{*0fNcG$u7u$kEHH?@7}79Jcq2?61=-ozxQrck*p#Q4_Uwb@1uYJ?e~BD{r5-z^rv4Qy?*}Y&7=2U{przv{Pth}_TL}>>*GKE@!RkJ`S<_%_^)3cefREfzrMb?{{G#Iw~s#j>E|D=o_~C}eEk0X|9$nR-H-iree?E*{MX)Gy?V9%nI~U=_{8l?-dtUMzx~s*=`TNCy}JJC!^6dsPk;L1<;~Tj($mKud;ZhQAD@33!;9;mKaK$Y^5%!DtJk0YHqG(pt2b}=Q~a=qFJJui-RtvDUVQq=`%iAxW&5A=m-cIAy?OJ?=ij>@{l)n5&Et3PUcUPN*ALQv`|ji7h*!UU_57!|X9*007=CL%n0skXgNerb;axAT;$@jt=;9<mP}2*L;PbavH<Jj*w}ujoruO3bypS|lORl#+27>wurLi6A?bFhtf!gO9u+i%Kb=(W}wB}$8OGAB1CQ1U{y!O1f=W)X_A22$Q_PpV;K>zY_&l|T4Ufl8PpJT|GK!@Sqe)4dIq(S97?kM*!CED#~a{uSspPl8M2(~IG+%{N@B(kCe_?PF$#!DJ&N?#d2_n@mgKOVKZSI^(fiu38qD@(gsyYmaumEHbd_w}vy>`(UY|AOT_|M`G7Y@WgeJN#ACA{{@O@JYR3@}e$xuN(Jf$HSjqa(@T~Lcf|N?QKf;2g%{Td;RLw)r+^k{^jcC?aNm${}tTS@fY{6DSP#|?!@MOx2GPzl3dYY*3pqVy&;Y(t*~--c(oJksYl@5qicaug&2395@`@e8|eZ!G-z_naLW*{!5}zS&AvqP?aUi+Zm~FEYa6RrY<sV~Ka%)o+XvR0>vywR9kI3Jw(?~8MZs=z#&2LZ`Njlr76y|91fNAaa@Bqyr8`(T;xlJaIov4ifQkLFes((Mp6*^UE-vA-x5({-I%dTK-Sx}LQE0`G5B3zQ2E!Ogj=?CCK?e+v&+^KWCSaIb4xn>oIG>sVk6hD*h4I@y))8K>8u7aI@qj%^Hdp-gnjfCu{EIUK;Sp_+7QiVy6v<xw)0mIa_|xPVf_Q+9a6$QV@8c}lvq)SS^L~11yvr7Pu(4jgzjsu}6eM{mkWxH6D)RUB(FoRl7>9hPpRV}SvLtwzdd25*xpKs7_6=NjD{;K&P;royrPGCe%s#&kfKwW8ZESq07lgy;7?GP+Im!c@oyg&_kC@7-?2f>|gQmcw6^U<-#~{r>sk-)I7M}EU+_-0(07{b?jN839-^^7<)xyP1SHGcK>~{uh?wveM*GITr-V{5I={$y`UXm@YdwiST7rj)(B}aH)6<Kct%t7VC!o=>)=B;cyYap2&N^I4;<_`%Uar?tauX{kG{`;Hj*W-5lK&Wi{1-6&Eb(mW(n*7$Ucds2)>@Yy^0B;nfATxXq=^7@!Xvbd8*}Tl>?Ct_2m5p5%yw0{4ZxBiA&Zra^N@?2N$0?d#Q67T@a%2E^!4JbcaKq=!H#+jOw1c^pNCPj6zkiVTwOO<?!!S`1Bop2{CrxRR$29u|OQK|-Hc*oaZL%WV9TzQdn40jMX{nZP+Fy)Zxae(};foCp=Rf>Vl3kcu4i@7NFUu)^=h=ZgBt8Ch_@c%1_|wzAv%qkE2xzqHVlD!n=0?$WX*uowV6HBDhY2nkO+WM5q=`>wVmKc1^~9{Pb|yINk3nTgtP&)xzN90}^V@Desb0|&9HriP!`XT>Z{FTK|M|PCo14F}7SV1he75+pO>c^zXTqTuck~h1IScpXyKL4h|3eq_8C}kukX#nXrluxK57^7aF9}qEW6`QAD0*>cUI(l!;)=uyuqTRjam)vfbZz&3@1<#VV}M<THqf4?v70QY5bY)cx~>`q2B8W1dYFRn2KF?5X{sNgBYJ?Zd2CJ40e<bQ`{QENOW38~$+)@%JyC$@m(QOq95}(CH~UIH>`P<V^pp?Tvo<Wrh4(w36Yme!gDRJ41n9aIhfwj!@GaYl>&Ew#@!oGsKVM&eRJM!9*1k2jA;_tNNL5nd(q=@R5~y=U!-sS5PLuM^6`LPXn3iyS&!-kWoi#iDTwyaP4qb8LXmmKWvw1wkG-fdxpe}FFZ2KF}0yCqViE6vc=e_2ilM6&E&XGCG!A8(k%sEvv1{MKTkMLhKt%PRV*yrx@w-OSV6TaL+B-|WRUe>x<K!GP=Dra>MqXDw_bYfYz4}42;wn4lXZ3AWs)CgVDb}_1JKnV&rJ0g(_MkXRinx2W!064HDirWOIID~KdKUzW5h|5qT%p4Rsm?U`7qorPwf{`^LKw_6ak6}VN8nO-zWM)2gKs5`P=;}hrNx=0-W5UsE7^z>Gw6(VoA`ZRmq7%Xi`H)&z!InlvJwWzB)v}4cFqI-J`dAmRaz>*W-UU9lI$g+}xle~sY3vRU;VkdI_UCZ4Cd(A*1;Oa5|DR{oyl);*@UdBUMOC9i?byuc`J_7k`TUfmyVL**skF`ef>Z1K+0B!V;||Akb`E&xQ-|LU{@+Ap3b^87D2NW5Rk*FF;I$a4%Mnjj7zeng<%Qo}o>9iYADtkTF{7<>Gc20Yng48sh*?cVSAb&Fsht7(gD8$X#u|aDo3c#6W@F^a7Z-aQx=-8zO_;IF3HHNM1(ahmzi3@-KJ8IL_m?<jG0Vro=)Kqgdn8R8gQDpR0{FsmvF~BT9)+6p1-v0{F_jJuElL1SD`riBP*#$4{*o92C5rPk!5BD)gEft$-=f!Eqy<J*eUXr(i#ud{0AdX`78v`hpQ~FZ4vWCG;``yK9<^*S47aoQUk~T+o&~#@jPn~LRMY)lmDPUWI|QbPZ=H^&A78%u>!Xid?4oc|k!vGIYx;Skyy<??@4j`BHr~4&7Cv|Tt(zBA&oTx*wy#2vQutwZqp0PMrkKu}E=hP2?~<9TVoaczmQ!y#Y+RLvt>n*U2hg8~`$#i!6V#=;Qb22NH6}hhB(c?V%tPZ}X26m`oaY&Au&Q+lblX@mgKoqosxH%?sY>IhG;`oWOCZ^g@k7&TSO+3p;?&j=>X=pO3n9lK_mSOf(W&Z-jz=-G#<f?n2|6>;e~pp;c->26AXDQ5Yoy#X505KE@^x+~GP<9w!5gH9egYO{&BKUx48g#xhNQT28&uT7hQ?xW@8t0NSLF@P#PJ@S=|?QFQR18A<pp3Is5_fos{j^u3e;_Xt#yJ=(TdD@lzRq`(UL)%$&09E8Bebyd8v$CiN~rN(SvW4dXS}`>#y<Pz5VlgjmY__TP<=KY>aXFas>VyTzsA53X2)xyrhHvnmc3Vd9FE=#BHEqZDL1pk!6vYfph~&YQP~%hIu&*@2_ix+n~o*c{Ek0U-Y4<IWn(T?FUm<Wvo}tfsj1G=k*v7#m_2%r%5&f59lvvsba(MSwt3}eKwEVi>W?A=i|6i_6QiN$G%m?T;JyV@q84Wujq8sC7b2)m0WNK+;qd>g{o5|qL;RNHmrvCf|*{)?&TG5aY<8a1ChrXhtf*Z^RX>2tVGtRG6lJ3lM^mhF)$sfPz)@mq@l%<+1!w_Kv<g=_gtlwta0+H67QLkudtpTa0P&7G~>(ja?oNRDELPdT<gVEi`E~Rq#s_gd}8BwS1!8YU<s#5*dxQ(!bWSo)egq}wP|0Q{y$xSqM;E6GbBbWj)W!7Pm2xQ_D@{(7XNviysquoXXP`<fp%KAdZjV92ZCQNX`bgd98#cDc_dt>N^@w19hFBWaRmaZAr^jgA+!Azo^Etb?VOhhH4t*3xIga0#*>IYA2o5KTxEZ}=ov?^Mn5iZwz1a8*dDQpKk%cXL}BR?HZjVm%``ts{O<P3`FmpAD2HgH+<z-FSZukfd<Gm@K(ysa*p)x~uLb{21hqXFGR1vr)t;oiXkkq_bHU?fqtnyR!F~--n{&T_9G*zboZ+Qmep>#y&qSq)^YSg(00`4&5YO`smc+fMAQK<01+1@LjB1kEAS3YnpbG@+zESlF3p>tqS-@leiWk>#^NO@-Ah>K$2(AT|C7w|a;v?iMh^9`rk<lXqRh5kHW$~qrkeJ+|+|Y_GR*)|0FgftxFQz-{fp~YGA2kv33*fX*Cohv=LcWVbP+3aaQE9UXxvEBd*2>8_Ebe~l)?5VjP`Ay%i$nyRJ*-t@*aQ%6Hs!4TF4!4@6{eIbbq=3#I)E~;#>pTzMNb0p!X63Fn~Ks#*TT_Ndm<b|FaobK+z&329#nHl@Q0<nxi-4&#T`)=0Y4pYxER>DXe)?i)}eFnj25{_GRtKU>Ye^(5-k+$-TfpBrFuuOn^a{l?)sQREiILm>=k^QoK1#j3=>7n@l}>u)gDGv8(Huo6Nlq>H9stMvcm20eqJ6}T_QJxb72+b(2Rol$pP&PShS_!yu!LIWq5e`=nJgLFl0k#6(`H;u+o<W26c{(IekK<Ng;uCp;3bik%em<8b+b##Il?ajKg5g*$Ks!(8!g@PCFqO9y}Hb`D7zv6#Er~4=0Jd><J?|J%RlD#|R|fO>3c@=rj^6*MU;vy+CYi$<`A&O*Vf{NJKi^PSu!hQ=J||tecVw>=iPg&tXG~jVo2-t-D=0;B~1n$A<f#PrnkwXZV*?J?4{!qs%o1lA>a;g76pU4k4Y5)2v!==xa9)R-9$p;756ld*s|C*39gQx=kvN>~$}~@X~{zNKtI`u2Y0p)s7~it%F;+PtC5sQKzJs#T9)vFG&;m+&yXoITV@K6W3PSrE_h9i>_aQQ@LKpSFMpZT$hTQvnblEi1@Ao#w{Nv_+s-D8o$X9h;X|-mGM}+Euse)VyV)%YK>E1FQlZiK~KG(RQs>;74XYSTPw9lc{#n6G}Kbb)ZpuRtEsS5+6GnH(xe8^|0(WH2^ggjTeMIKuT25OL+flMyiqleVxMZ=0ikE0s-E)VoGC043r^~Q@CBWxN26P!oT8!!SS6o8z>Q@xN)pNWt@!uR?$yWI4e0hf>cF)k0GnZlBRKn5P808l;ks9GBy=|LY|mTAVB?h;PU$RCMFTPasJL9_(MXIPIiQ+xq$G_zTb+dOG;&dPMj^Y!e`zdYC(J&el#HWKO;*_ln9n}F@biS|OM&?@C0Eh6#>Hw4onU911)c}!-u6?t!x+7X!1GR{^?v0}4bN8nJ{p~C8e>jllkDY^cu-(gR1d){lOCTc%$^Y`t7;b)k#~wZ&gMw+QU=Pt_-Qz!3#?qb<%^hss>kLbS28u;eY*adt4rQ<qLs>^CxMO_m*4(9s)$6A4wKLAG`0g26uV{Rv5TO*)sQ9+N~pBtwIKteY&9#D5JRROr;NGdK_;RiFFFxJ#BS3$13>i)AqB3koN;ZR-hG+YmKXZifmcIYWry*0izW(Uj!@A&i4mN+qBE(r&E{&!mSa<MDCPY56qI)vVRL!CiRWO6;Fz5z!^f$xJj5~|5#+0_Ti^lo)L&m|xl7T%iA0>D*res~D2FeeipOvu?dAT}Zmv<Hol8?|4L`E7oqY*PR9Hgk1%f#6HXs#xsp<>adn20fZWJpQYZ^5zxHrZl$9@5~!@Zn70Lfc1Ws@I{u8|kfiHL<tuIC$~q~MB)5WBgNTysLa@`}cI<xgv8AGtZ0HBup_{t|*(4aJQU`+=68QUHwp@Cb7`8G(HIiTZ>(;8M*VMCRXeEo1HBZAM*C!&xAlHYxmCnpuR1Sj@(uhpE_A?6UyTMqQbXP~WPq)|wLqt{p`oq&7#XEe|8iISV3x6~8U%ZQ#gNO7Q}7?IZR%=>!)^(cT+HAZvPC2reU1RiW&pqonO*h_I{-Ry|U4Id;R{RX7ku<XJF#g8Oz<<2cQ#Cy4ZY;2U&e0l}Zk%L7z~&!*Z{2^x%g2!zVRP@~07AQ7h7748tKX*;R&!37I#E<|ZIVvJSd#CZfs^NugblYoB8nwu;b;Y0~@nsY?R$Sn`O7k(p}8BE_m1@bx%O(|h#3)c%b&}R#?#zvCF90^kB2En~ev}8rX5hGbNZ3$n$LpE@!HlB=OCYrieVG2w8LVbadTsIuvA&9#<*W5FdWLnkJ5lac$L~yj!aqu9fNW8Fl%#mxqu>0_OqS2qA(lJrWsnE*4H3UuR;&ocnqFq$C7m~yueC02*U-T_R9t%EFeFM`tD5xG*_4}9qoNm~;#w#eU6rH#?oy)j$H^IEBcgY%3Vqj096n;@V0*EcJGH64egtLX71oaEP>(V*hF){-0cP+w$JlQ7f-h<^!Tdc5ZG8E;5vYp(;MB_j)xKt4WF(1np+vQ7OrMxbnyK2BKjLzsHS4Sick_HmO98}{9ltTctDpGf*h@D|dU^jPvNZXB~&>Ew2*Dmwhcmfe;ko_NhrK-pn*!a*e{<8j53f6jURAVKpa%~Vjve}?ExFkO48N|HNj}rXiWE%x^Iajn4S_f!IWq@kN1?$60cMbZ@@EILK<~md=j3hX9k^UrwMM?G0xOlUdvVZqu*D+2>2Q=H<eMyR*>rRUpF(t;6`-}?C42neJIl(Ms2N!_`l<GPZ7qnc2U^WYGjx5@d5cQEoRZD#><c6n&L*@`Wq-8jPKv>LY^N>R)pyJ!0Gv6;>5-^Lw;Hkkn5yp6oPh7g%djL!#oO<g$2QhO$JL<<Ge#4f?5Ono}M}tN`f9#wTpi$B{4r(C`6ERNFXrCPtXVz|O_q0^ZfhuOjKV6AwV1`t_VvG?F>1fXgcI?2WCL<7PNtG@MOKe=eoW!L{wW_hbu6hwPsR>W}Hrp=poL|UV%CjD)7gwo_;ts`pTP<T>tEfQWQ7#*d?jeKf8G<Hxj$zJLL6k-&Br8QgCwH68-3=`iGKdmQHq^pCM^_GN%gYh8Q{qL-k8blyH}CVL)e)RmNaZ#1L6dfUvrpa~=ZL;8CFW6N2^As}^&>u_Tul(H2H@k*@h9u3T5TJvGPAxo!bTw&9wVYY4Y*R|H#Q5}c8J!&94??O=8N(m#H;XwHd(7U3&A{5BPi0dsyQWr43Gn6;4Xwu(aBpKtsrysnO6+17y-JdwJCLQ2Hdqo-;xNR`j)!VYC%Xj9c61RyRb_4P_Zh7$`t_`=gUKrN>(jzO(Ei%Dyv|LfU?|eg-cgET==-471ghR%KCwQwA0n8j#}LWiA#*Fay?62wbrqF8O{d^CU+%)FfEyR|3uj?d4$Uv)~Fgotz0+bvr-r`icpsz+ZAsVJ=p~KY{Kb!JPyz0+_Dt>4kmX%)8oz8suIe%U4xE^u6MiwLkZhB8Idc73I&>xbx3!O!QiqkO7g5pW*#IbTqR_-;gd#pvTD;@I5EW>xMhOZXm~%zC~~MG7h=G9Pv^YzZ=;9QLI$wHE1(%L4wly_LN{<R^Z*}yoNQaIuFp7J=Oz<|s*=Md!d=0@5hcR~`No*y5<+J0SHrOW_~02OEd<7sB4&1R+q7#r9ib6S8@z(2#$uEaHnXXe&dH`kwfl*W;G<@%k(}I3NQHI&`6_Tg)u~`+|4I2b;yn@2VPwcO3gdo=jDy%`=;Z0y#Kz)QG^35ys{(d21Vq{>yh1033&8r9J_k2>gTF6CBi-@9(F>#39Ap=5ENg`PO|vUW^JWR@HZ$5%<e9QNJ0iu4yJi(6#0sZsIh>Z%L^W(^mO+@y5MI=tTA%zwip*kWmxu}sA6W1|SEWL(lHJ%SV0kFYYLN)$$wiYoXxySE8iA3VxRV<FQLHHi%4J4Fo{c_MGSAOCJSkWrZ!?nFn!_e8D)HokKBXep(YVx!)P;*X<F9qJC)5OuT=J><+mi-};?jIPFzhZ&c8dg)be8WVAuJxDE9Ta!jXi4AeiTSj+TfJejBc7Bgyqb!a=nC(0<f4ZJ|N0_vf-8{%P6Kt+jO9YPn``q&xMPmonKWnj?6Mi0h{tFE(C5eJfy~BQ<wlq&L66ZbZRuF(j)!i(2Mv;s}RV>#XK0Aqc#Kw6;+D9SvmZ+;AkjoM*6?mi!IN49x{AM2@$20hI>~j`SE75bA(Eauu^FyA9Mn7cL9*Cb?AuVeqKeCK{G5xxlBKBRk%o=SdHU<Nu^;OaQ$+vSUB<q`|YSENFF(t6v&84`-HeK%YB4rDwJ!)s&+W)n6MEAWeT36DGTEVpRJTSAXasZTIY;_0P8BUltQ~<YY6g=8lh!QwuBfHysu+7k(TR}2N#pd5LR2;F-ee`Vp)~><e(K3A%=2Mn5C>$&`Mn&Z9$K4{IYz@C@dC!V^M8X<FjB3(QY57&e~pN9fS+?it{M4_EV)~t;AxRzJ?mMFVPI@{#9^fuwKOlEBT~UaXWF3@Tf-H_Y+t~_Yt9DPO(>&No80DHlNQ^T$R(a;^9cnRa$LHR76=sL2Fimv#5$RaabQ_>cPDgv?9ol)AwGK%L4vz{5TO6xEBEE%M){~y8*n-7w;VnyaAMI(+SP#ia^S}PB#QNg}M^#&EyDjbNQ2qgNf793CDG&C{Fv4ue;Fa$+<mG%*Lrv!Nj9;7eM4F6@AToN)Z$XR^w;OE8v?d$6LWlXDcta&eB9IQQuwWBat<$LS=M>s_@~dL&*G&NN2M2xHR-&X@_A~ZlxlpCEWpfmnwR4bZR;y7=bx0g4JO_N1Hc>BE3cGpgU5DZ9*rF!Azl}G73Krpu=%ChY)QVw@47R3uz_uEjIG1wOD6~X4xOlf{Se<*fwO4D^H>#IHzg5m{&l9w(pzd6x{TphEb?)f9fV#?UCS)RE4gjZ8%ghG9*!;koYFiPP%K7q!S@VYrWpWrvx*WiUrusix;hg<d2Es$lMzY_JE*J97S42wS@(teC+;ld56x#YpCu6WK3Dp>cNcg%??G1Wi+Yx@_FKN+S(D7szG$v_MXweh7mZJc}ID=hM`i+t@zv3vgnzLIIhPR2iK4-8B{}7E&(X=+(yvJjqCSqD2}=~;lAS3&FG755Hl)*X%GLGAI+`>Q96Xjs;;qD;6`!0q=`D85rqylci*3iOqJ}_%HP?JrLf6<HQ9{4sntCl9W1K~p5zjX95r|lTglyTj05tHx(b`J!nC5z)L7r1Gr_0pEV!OjYF8V`N6|7q$45Oe*>({DUh!=QI*Feyz;SjFc)RRTBLbKaJU5RIViE!2MkmpwF+{wc;^~O^q*2rzUjG(GDx#j$ul*A6y1LL!wy!gCi`D_DXTNs1py=={XKM(JUm*Dobg<${3R<BbRXbgf(sOgAV<2-3BUq?*_NZD-A7qM&N9`_;92koni$LjE(V|I>uJWgK7?N)kg9XUP*hzz6F;OswOd)}Y*aha}Xe}xc@e^ng6j&-eT{sWIm~ga(TM9%^H)F3RvD$6lVDy%ATe--9_j5((gIV<@a!_|R3zuz3;g7~e6XdG2FI$O=CNegaPHjhFWXwPV&yA3rm>FQStCKyEAW(|aD&BDf@P=a6<pcqBc%a{qZ05qW1aFQ2Mj6c22)IV8Fl!<;uFX`<qFN0o<%(i*lvhE+i0luB!)J(SJ5Y#X1jj}QhejMB0kuXR>~!XsNg3bB2{cBw-OsV>i#$J3)FRbU)fAP6QikmsbgLS0XfyBENVSTl$?}Th;{Y3ISc+uSgd3MO5I4`R%H2&u<b}u47eEpna<UU8CJ1~hQX8-o(n4PZ!x{@manXoqV!YTn9VME?iC$a3cq25SS@Fy(w`DgkpQdL1l|6?F1;TVUmCO{8O&C>*MLyWk6y~GSyMv+{Z2}X>af_yd%r*s9SNLtJ+t(t~O>F!I9O$l;)L=xum11Jse}pGan-0=_j;6igxN=ZVAU)#335%#JSZ;{Uh>IiG#Y?~A4RwvuhU?$FPojd3yLXUCN}DK>B}v&xoh}(I-vnEP=EPk(cS3wf0I$hyORm?f5Z*ZQug|5^d@Wpcyq)0!{CC>>Fn^-E>3a(&TBgubft+M|A-RJg@|y?Eps`I>sRlmfPf&gZQ>@&Y4$)0b)+mfU<-u60WL8)QL3%B9%m+7>E~asqQn1t#P$p5iL3HY<TS3X(4u^#-Gcl^LZOXfx_M9vblN6a0#TRL}aa9@rKDrv%iJ~1x%Sa&r2F6Dkh6FqEd)Au8d|%p9Dp&n_>J!P*vyD=3J=BR}2@mJutiZcrC=%!ps;`dO0%y-M6i#&JtD}jpMjoQPsT%f>*FG~uCFreK7cqWkKXPD0EteAn%A}3L%#lQ7N*C&luf7(^QMVlKyvw-AFZ7WL6ESJ~bBPe-2WHe&O0Yl$RYwy>X;Q_rGrqbq^j(nWOVEd4iF%`NACc;UPeFb4VI6B8x{F1#D_fmKR#TtTL=|^UqFV<L-o#kJ@esS&lV_iPoxrc#zkG>{3r4zZ<vxKy!i9!tU&RBu98ZcRM9s(1B<~BAlk)R<{if<Bm19R1R|<V%O1UFCq%Mb#SYh4KhMii=Ese6GVw!%)>=7g$J2j>tBvh%`kuqSUTC86Xr56$iq(VNTnZ&ik@ysfMfpUsaCq*YT`g4dajlJu?9Vfm>$|L0xyMVZI0YgY0aEcQ&v}lQEb41%|gSeB#x!pZ5Mqh)iE95O|M0X{c7KbC6xWWp8wJ+hTc|3iW2{Z2$ry?9eiUq$K1Ah?^xzvT~NlJ;JT5&8&R`qg}HDNMFMt!R?S~rshJRmZYDgdao4|qgGXCs{p$)ZA?PP6qzwt&Wx-7sywkVuj#*ojJH=^DZ@ZL6{lA<<1yv7<^(!YQ`3>`AlsMS58669L9yHkF)#QSjsh<u#&zV|J6W6c{S_YPjZkVsSMhlD1|s2e?4}1X_vhi5jPnN-7cdG&92^m0Bxr)k7xW32BQ6p_%-CliBrfWuk><YZla2C805-v%i(^?)1Gyn+TG-I0}<Hh>(V4i2z!Y%^i*b(4Op8^qz?JZ1=wdLCi{a(4@CH9({!aW`W`>4HEdx(k%!ebS{CmaqJN%`f7-2bZ=bXRx^2nS=!U1&`ds7%5--sryaUk<&3?1q3B1|qlrSyXbs{lsVMuk<Fh3JZd@6mYZYTbC8yv>W<QZS(Z;9p@SkEJCu4p(-#`4o&Gjra7gB5L{FdV&qn$jEk^IGeKi{h6w(ncm3L&4ZE0>DqyZ)at2AU#C#}kMM`Bfc>!S18_8J0v1SAy%xOJ)LIN;hhe0hpyrxoL1*?vyr5won<VEO|$?cAY9t(DtKlJkgiistZd|?5OUw?pkMt!BU!~Li<crg|)ERJ<D|Na!6#mwly~p4IpzsqFM1Z3dzMoepCBojbjazKVT9>dsdG5R76Qo03&p~%duX@!v}2OIP=E?QF01%N}?wOKA#I_-s6QSOUu@#w+H8J%*vDXWiiM@FsoZ!gV3qlzkK!!H;euJM=n>rk}~?%xO@j!Q|@=-J=S2Bf^CD-U6xJ~z;MSElvv}^(UlTO>9h*JT^06JOA43KHR%@{k#B^0e0*_l3ls2K&T`m4MV|$y%~BNivdp*`Drz06(t+$5*rlRE5`H&7NeWVTePr3tt_<=T95h=y-)sP$ahOPE;Q6+Nx*UTAr6O-ZSsM{NOHPpHDAwoH=$gSNl;&w`@#m*{yeKT8LjAzYD|^(>a#^=fmkt=Ac_CButjr36ebM+p>zlgzO>y`{2&@#WUz?-2^&Ix5sRa$dPr+oJnxZ@{<&&v?+AdFRv0g3iTz4Co?>%l=hSqFVDW&u2?L#Je_n)%Om8gAl?#YXVxzd&{_b_(rAF#vv#;1{HgN>}Vo&|0q?qB&e6ZQv1-hL%@S3r~HqbyD=_8BlsKsg;v;?Pye8MLW}Tj?v?yG2q|t*GlitaIZiyo;H1)%4DsSrEI=@%4}AC)XGE@4NgaR=WAa&xTJVwPoUvx(p{;CTW2;g4<(6FvActrK%NBm_kHM<oQ6n_AP$o@R^+ssxTH=a`EE6BE=l)9J0P3V*JIZmiW`@fJBIu7iUEZM2%C&nhf{0p{Ma#vBKNn4Oz6Blaa{Ya`sID6=x3Pdon5IV+7%VhBk|C$e8#WC8f=b*0`M>KdE_+;fND}3ZZ)TXKrZ75XvJ^YvU7j!e_;r_X%_i^8jeUJ*0t>+8<@(GU{2Xp_MwXFb7#M&Na;q)L~x}JvKlhHp~5Z9ZL}OA;mb0fUz`{Bm_pj0GdRJVZ{56Pq?lg1XNO~1OLJ;6$0m7Qw#IVX7XW$N~1f`TLxVt9#TZANZ~nL-_aG$lCcqGb#&9{1j4qUE?9b(B=hn!HR<wx+|ug$3vzExCMzgb{kFflD=8vGc>-o@kNEZSB><&eLrb@2oeG$-RzCtc%HU9;)m9zb#8JMFT!Q=4|9JA#`6&)0?x2&)VMX1p-(Y2pva|ct#FKCuWv<h{E^-VK%iX-)RS>mo@v=rsvmZH-`#;mjEk;4ldYhadb-1SFGci)ms$}T4^KLcF(al_6PM_ed3m3utcEg^#qYRk|0{53IS?i)}(S&;IUaKg~WBX`Qc6(h<qm{xMYnvwv6QulrMOGsASp^HNEyk1d(;-$WVF+A0*o0NeSoDNBkFb$2RE!cM&CL@naU2?5VdY92TCTW3mE_La1#8AKOW3wt!4yqw--y5^(^e>_1)^gXYdoA}R3H8kI=q-J09R8?TO3CdD>i|PtU;3$G?7z=T7itzrCW>A(o+l21`cG?85WaRrX8JB>*QWNi}jGRPaF>m+C{E;!(fi<ED~%M2lp+?1?inhmG(-3cjyBZVm`~NN0Z^*Yqi0;xE#|fP%A8b0Ry6^`gFzEeSXo2h4Wc4qa3Sui82ndG|qdC9VEe@d}8c03U*(<E=|u766HSqQ=JM;6vj)86Yz|qbQ(ACNWJNafoe#l06=m4p!0?c70^8bXPnhRg)djkqxem(h74R3npMt{1UjIWB8PjmDw7M|Q308W3~XA>FaK~y0}53kI3n?%RZ>hK_sDdEXon~D{mu33=|4roRxw<{O|?MJ192u}6oQ(;03<GG0@)@LZvDat#UvWbEbtR`K6%>eD=r3yYGhm1D(eJGKq*k937b6Q?8okJdEODjbyq+!eVZZ_N<kEt8U`_q`F<5;8tlB>d44sTWpamKB&k!Y*z6`D&xt;dJ^;aUpN_Vz+^*%E$oog<6wOsPO^ZH36EO5@GCVm!H$%M5HJ){h<fRgvsBOxfJro=#j{y~5O{LW7v{Gn(s=f63(d6I`nT6InPvA<wk`^*xS~D6m?u+mLAGE3L@B")).decode())
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
