"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)VGmOZkwlck<m7}+hf<QS8IFc=^c1PCUJNp?a0_ekpQ_wKFxBhMkLUMmK&(o?^WTOTBgJUnFm>A#=+>tFu<x4-`V$v=GYrzdZozkU1U{g+=n`M1CP$G`mN$3K1i&)@#?_kaKEe|`MlpPu~i%OC&z=Jw|0FE8Fb`S8}SKVCoo_~M(V@8AE=mtX9D?B|=?cR%L8_V)Vq>+R1x{qDmj?jG{?`ugSet!IaKe!6~r^Ye!nS6_d6>&I8O*H22XKK|JApI`m-{L>g--2D3CpReJaw?AHAzxnjuVUE9EzkRo#;)g|i_2Lh|ym|P^Prvu@vCX1v|2TX@t<se@j?JUa54fAlIF!xHAAWiD`sJTL2*SHxKCY9w|1hLCub=<??z~UK;D*QS2YL6a<H&FlAD;5!y0CH&yX(#2*XQr9Zx8#sdt|u1IGq>IX;G(#3A=yyB-qg}ac{PhxO=sFkhwf;l;L4{H@ke=2T-6#+4Id)fB(_^3@Zjpe3`*rKL>jQn|a>-d|}7$KE`;n%^Vi^?vtwr^{_ZBe>kRbJ(nxT;o#+c-P)Ijw>Rcxx7o?YS{7upPiQZA8)?ftu{hfw{N>|I@sLGpN?#d2chS{7zFf7s4<FnK&ZkwIS=!Cooga{{?DlWY<Cm@H-S|3_z5iRVoaeXu%Q^f+zF^BAwO!5&O(uM$9&mK5;t0cu1w8q>KI#g2@Sa70*eLKA@nG@{;KM<>ea884Wz%~1zW8A}KvREn^8oUIj}N$c{rdXFyFdT_`u5$c*RTHh=#cRzgil6aYS_|~BNadVEYfdpemQQ{*<slHgzy?5!oL4)!;?9EG8p~*@V-HhpVrCR#<Tg^3_bU~{INnHPgd(J(w(r*dc@`g-W*W#hw;nXn>XX3bXNTZc6_@cE6;~ZojatO|A&YBTU*`>xjz3tT>P=m{<DJ({Am3%CoHkh6|8oIgugwSadLTb&yCKMB4XgXXh)y`jw0>+AVg7i577rzKkY@Jv<+z}?~j_c;yAum+^iQKgFS&rTG0jj0o4iQ(vMraLi~Be)(`6y7sI#K1^wi$UrD~#kI!%a$(aK!`guEXV~g++EkBR`H0G5;zj@R?j5uHso(2m{ct!yz;usI7K$6ZI6>NNPjD2%Dp2k!n!MtN?P!6jvHE7;hYl|YozbsIF4{94yYjWr!&bCx3cZf{Edn`xm>Fyz;g!XdahF?`j#EM6Z>$us6nCEKM{krPWS#jq0<zX1>)N{rW^PLSe=zVWbPGxrrn$M}6f;=J2$My3y(V<RO&~;VBk&w(_SmEMPgrb6rn67d|R@h4q*48{iq^O|JCtRlqM^-qS$1$vW2*On}j@r}rp=qS2ifAKn*q)xwJ;Px$5)mhmc(cQq*fmxrHbwkWWH>`WrkLmn0)qi%>)51&TlXb7&*f+7-8}!`89}$RI&E*W|Aa#3c;Kv!GgS{dc%t9#9y?0doc}q#^I;)xZ-OM)XNLSP=?^9jXjh|A-7wK5AGzJ2x9@JB|N6uA?d>1=v9w7W)h_s<ZNDBTS$9Yar#~KF-eUxxH`t~X*erVvu7{Z~Jb7CUcd~*SlCLF_&f@7J>AqRCgT#>rdHg`3KWFhedI60cV^?DH*AOBrkT46L)s9BS)Qen%eEXOK9f=pZc5m4MTIzoIKfHEZmrM<5Ir$Gy?^FKFv%gry_%IauHhho^CQ7^-XFYmeyMrCPuSWwub9b|yVJ80*s7y8da~z!{9HI%pB>TmDTO<bhQ#?9lsU%Gv2y1{+ESm{@gEdcV`CiqBbar>W8_e!DoTUAvp+O#8O{0%cW`dm0(`=jo;r^W*osB-_Z>Wh&2BoXPBDPHP0JiPohXj(qA!e1OP{^d>ygZi%pMpL<W%+Gk!}7L6$yF*)4VFP(p~&$@EYKFqhURHlj0rg*gCW5A1J6@DLNQq~&)0rPUiAvzBtJD}F-z|hjgCp&&b{*La$LNi<)|FvTGjLVuCIIa(@t3Hq60uwwV=SD_ka9s;T+>tP!rl%y4*E?YRn4jhSC{%>Q4p9^nB-Y;`zaPV6`!ffD0;WL#Q}{_>^reQsaBdSUi}?UvF+c%Hq{mh8<0oBw=Y8!`sAVo8k0IW`tpWc>BYl{qn46aeIx;GZZE#9C12gsp=*ET)~bMhn^DtXlOVuLPFQgA*+hYN-YC~_L!yJOhhYOKCiiOfJTYc%D5jQtgAqYhuXwIw4sI({)F6&n4a4(W~uP*c|k*(nVXLU<&zn)YhJ$1-0@kc!vKU7*C-0j8nJ92VNTUczUhc3t=v_814^K}*+7XLC5)pQ6*$%aI36Yb8;7RjA#L<NXpGWrL?ejVWn7FSYl3-%K|PP*0CO~!Lsx{afX=+%F*lVK62&`dUh(l&1PJx9nM2X_VC-@S)%8st?85hEX?x5XH1{VVEKY1}V4=y{A+mBBRkV+|+@($T50O%LjUl?|HsVw1xbdA`=uytru}kMQ-xwFbZ7XOp4R8?tA7cc?`ObnmjYA`mc)jWLTARE)A4%u8&##jFlo~)G_qBOma6FwqyLqL<q~%!2&h2GSHvDSvcL(Yy0C~%>109d1L9F6=*8-MKHZWXRMF|VPI6aXPt6s1hX~1XRvW~N|GKlW3h#|*10}u(K9ZRab1a(6ULAk+VMCjabTboS1WG-$AgBH&$?1vXEN}s=~7Rn|1%9mmsexc7n3;mTecS|e@VWCAIzF$dAqSRF-lyiZn%m|Qp9<O1$EuskXF_g@K%65iUajCN9AH~JbUz@F6DU#0Eu(&9zmgoFy8z1oex7fLRtX`D#3h}1m^Wg|JH~Hfu9woS)$w}Ym%mW&!pGoRWPfbE3vQ_X%hGd6_6thUD1Ma6+umAAj-`@=*qaaP5(r|umeqNrDXW_g5*5RImFwc?h2HkM*;He+qN$x&SUBHCLhY%wobQX*}E}owRLQfh~Ji`S94{NDt1}dA_23}AY@oCG(Raw|dKI-UV`txvKiWM%EW&&Ko_Z2WyF8PL~yxNRV2i18=U^)yH+EYx4ayJMQg^TIWOfPpc^%{gQIZo>b>?>s-@g#91>o_&15m$B~2m1EG-%(#vxfgwaEDyu&5{G_mjFrbrTcW6#5}mb}2#<8!?x3g5Dq;1@T`&i27@p$xqrWS1<|3P;qFTE<O2W=SOYJ5nBE?ctv>+cOw%VloOA|INr&&Tfp~wzzqvY-nK2_iwVEPlq@96jFbeN*eRQvK-4IvHcNDkA;QkGt&ZbPCrZEM6{B+U+^w-;42w37UvWO_*%L{Nik6)!v}XQendLT2j4wX&|^7`L}r%h-@Ets|g!b62W7(>Yg=68|);O<YIU4Z1V&Qt>k3k0X@i=0XrWyR0**|GAf@<n)UP6m3PO=BiCn%94y#n>I#~5ix}@GwD9ZNVkMzNkI{@e1Abp<pPF};x&639D{zHt|GB<%&4O9v1aKzRYi2Zr8kA2=`?cF8Jp$u#ayKF-BiHfb*f_|B4W1N6U>J0f}mZ==;gIll*YVd)y`&(lzgBkdy$2ez!+6pAW^Ft+ytsawQqsulq9rRsF^EL7Wrz`;)-`#$r^{Py5l`n@&$H+$D_!;_~g9MuowsmdJzTJdS%s$^+zVye5c5df@RixcjZz_rGe7P=|Cu-7p|Q`)W&KDv!P1`NV&#a>cTZ&+JeELg2brBN?79jYO)8}{*?e{WztvIIqXy78Q?%>)-Bj*%<V$(%Tt<X`v#5qu$WMpD#xG|b5ve3Yb)5G8erjv7BUZCVcJIL)XsA`fCge8DD02hjqxPn&*#0$_S@7SFS^CiqtS^YhskyjR*hH%ANWy0`gfZt3kOQ~29p;BNcisV2K5KV+PDvqq1=BfQdsOns(c0<SwOAjN!T?q`>zFmCU)2!2{{CPYSq3@TeQNOaOQ%?%SxxGpF{l`oi^uw1@5g#%rK;>H$QinsD$shc2f!fJ85!z50j<EaNFx=yGE-3E322Gnn=dUZ6?o?%Ws}H>|T=n8Rs~?sprYw4g19nTsR_?7^o_nW#YP6S@bBX-22-qIGs+TjM4uB36;d^>Ag#v@Gx;hIh_?1^t`f>b^eJzjz`4CYMiG*-D(8;mJ7Dz#7gvc7hIs?lC*EnW)X6UjM$}><8WA9wUaOxK@`+2Bk*Pn0Z<QX)fhIRepGg3Z$Y%elqS7<70Fow{9~n(Q2-Ua5-=9_1bE&Qls04*j;`7UU=3>sT*c5HTpep*PGQHft*P7b^!qy{T94xCAi@Q<#zmX$#S(RMoT3-Wyp_RlcRFxM2#_hi<V@%B?sB%0D$qrfk15g8I$60}L7>UmVR*nW@53BlWvNw}U&Nh}wI?zUIDS_XzETe>w2cq*^5EwZS0S7Wizo+P6roEsD<tS)mRW7vB3;T5?((@8Xp^DHhRiC8l_<rS-3tud92s-kSW1;bLh3}r1sC)R*Em#+Lhp#_eL{E*BRR(siffLM`jDM=Vq<vlSkvQkhlnBU7xP_iC-Mp<4CC|!^6#(NkldQq;yTeUBv`J6yTrCY7`DXpL{5`UhZ8#@y=|upzV3va9z!gflG*DOCZNw@!-kCuLSxh2E(P#f(3oRG`{xs?#PAv7B~g#*q2VZViGehy7_8v$1+qghXX7+G?B6o!#=(lSOe_4jU!#pQ+V*m;j&Ltg-q>qEgyE%!Karr=&|Rmjt|}c(idqM>a$mK2+QyBEVqRAC*}TN8QtNsJ)s`}GC(6w2Qn)r{MVBMMsa&titCq7Hu1m$uakn<cd+zI2+`3;vDK<Z$VVVqR2(9X=_{K7-2ohi<rApSSl}UkGkSrec_Ruj&HPk9!Xg)2QwE~HhP}5sULoC&v8brHd0et|OlC@K*Ni)k&e^b1h68=dew)mV9MLWa^mzLQ|6r(B?g`H~MaiC|QYL)VmnnUy>7M#QZQ3^UXSA$rh4x%ClSlpf<y^Uou3JJ-_t+?@#_3A_F20|NM!$IpP(1jIbd#r<rEn>LtRk#S94LsZP1~1q#<%pVe7O5hEm}XS8Ec0k2R*oD{O*v8`MxK;TqI4R$s28Ki+~T-27O@jeFQ@_IAhX&V_}QliK29V)6@Ra(m5RPKE>>&kgf80*?mQ0n%unIITl5|R&pQpu`z1Fu*jjbzXmp%uj5&=>vWH84L4iO~Jp{9ad3>rcNk(L*s=Zf4dMWDhnghmDiKbG&z&tM#QCaOqEn)_$keY{FNyvEDvifVTE(Fi{R4P%P1Uh0|ena)Blo7c&Ofa{z)ecZl>~fXIE`r%sLz+A&!OkvLAOoY`G^=_LL#8gH46WlqCZZxQIuS#}{?2)#Uv>E)0j{o`aTT4mzRX_BYj*6wt0Aqjr+2%t5(P0UL^RJ;1ZS>jDQcP7Tr630Yz7WxmLE?**~$o=%WF!^vZ*{cW~a&UaVlgEvCJ!id}X=?9zd`9>nk;PD*88(h*K1s^a>vL;j?GlF&qd0%&g30%%^jSX{}QS0wm+=WVIvaeery~j*7fgjfL!)5lweDikbT*jj|Oqjq%8_&i`(>PY)k}+^v|h$pS~u$P4I1z(SSN$19iQ#uf7*c2gp`<^*`<MT_yupVrPkadRwdWI`PJLI?si)Gr>$547}@0buZlN0{%E5yz*Ws86VaE!FfvB>pYWGL{}TGwM<pP6FYyN#N(Q%pyX>k~NMzOu?=~p9O?A>ZY_pe5<lrYbq3Yb`*q=*sKy;9!8jQ7Igh8d|Q&+{Fa>9$w3*?E=&<i65%6;$EA2a0ZZrPwh&uJoT@@`Nk>TAxe%dQ8LGNcayfKE>na?GBJeDTJ^8ITp|EQ1JRziwp$e8<&h=M$JeyEgrC~6(A#f-UDcuju0zQ~bSGeM*Ce$Rgi>nXXjEB-}#2CBuh+V9cbmaJq#0cnotjWlN0!|z-r{hM1g+P6Rs2wM`hZ;<0A%9+~q3I&*N#W8UQu1tK*4W*VSRp}r+#s*FNt7%zIASD%rhVG$H?ju)(#B0OG(ywzDlFjYD(hyyI}~s?wVI2C8<y7JbXLCvPa?osYW}x~>=7?)9yjDdF4Q}`7ie@AsK`qcT`I(}FZ4n0xOkoBq-YnJ?Keqc2)^)_2`u{hACJf$iN1kLEDDT=RekyDA5*)WOT2>9gm=8pHbA-og+<1Wy9ws?w^Q1Xa{GD$r7(!v5kLw5nL!)!Bz!7#7^rFQeKXC&{T?HDe&3$k%XQuV+yH)0nOmXZq%_Ly>@(_=-%kX_@~v|D)cXX+_)IR+YXsPzw07tWTQTMWa8&WIGhyotQ-ZO%yF(If)N$5Gn7b~P-^CM%XnySP=-W#L%5Q@`!}!bcQ>iiQbvKQLtV)kTD99#o+DMW3pr;T=V?OTSXXnQ#)XKRIrBLm!k&^K$q-6k+>*X;Cp;GxHfTi^JD9}ktdLoOkCs3f*`<3hUrmO&(b?%QOMajNqiIGyqI=LXI;GN*Etiobo9H?-mIt#_kEQh4%qV|Rn*%riWWJS|dQweFh)J~AB$F600)d?lVY%&iyJkBd#3cBEZ$6Ej-27jgo$VBMi8t=Ar8}<NoL_qS^4-TT;e$vv9D*SFKks|2Q1CN7@9{bp~D8P}Vmm3r!7%E~Mk?(_(`Y@B=yf(1{yQQQ`=~sa${^@@8h%ppAizBNM*z7>74r(A~K!qj=OKV)EoJ1wBsxMkHU34O7N(U_LyUbwZX}OR!lxHkX53W)P#odFsVJ%};a}oY}MbWKWP%J~>BhL#QGfcquCDoAy8X${1LwbMt2}J~=GLjXvfWOcceOlvk6zr5N(fddDVWqbDJZW|K=7mXlX?oBCU0<4$H>Fw8PNhTziZr3ZETV3|E2_i<<7vP(zK=gyN5+JLoE|yNn)>X38O33El86eiLlGT2kIj;@9sYB1Qk5>8n_@zRAGFz1#aRfBh#EnWFICM32_%5rEdysE@QKdb>SzV+qECflFvSSSMP*B=D>8tnC8Cvt_tdx4HBl3rloLm`+Oi9xbi)#>E~gwsYFsZ5L@N2PybpwkVyZd+DXPeHYZERM?NHL=@=+AO0t)Mg@sXvglM=PK3A&XSTjk1=xJIm__cC}71WZ~b0UJ%JdH+P&E_sB*8rrD3FwI=y;`2!uAc`=SAcYkhir(G?cx+rc{oz<0hUc<lc^CY4A*bh8_a*0B4U#1q%kjL2GO>mjS?6w7z6~O2Yje!BMb30e7-PdHjZR+G2D9~R;JLqm*OYfZ$H?)o!VO};dH>_QOKzjz(h@<bbV(Mys6?e7bj}t-4?xYY68qEYkc`81Zv9|<DLE@5uoNsULR+{XzcZ#d1#8&{$1tqlKFmd#1_9Be*p^)^cCcDb_vEy-(C%iM$1E^ZS(OYn8xcXx7o#n4?Tre+{G(JLcB+E^NWK#z*I}55voK&|HiL0TLdf^)vt;rFX`(oBGnP^D+I)JWItd*Vu9E8CVH{jc4NkYP9OnJ=4!1sxC3DDIba1Q@+c%A#Bwd;}O}ALl3L=k)-BA$jP~0)9utO|^swTqe#!N&%u}yx{ql_-58!FdY#4jn%ig{JS$v0eD!M>c`74m%Sral4FLJ>xbTq|#1G_iulEozAou*gX>snV}vEGdXAQyTJK^huL>caaT~$s_V8qdl8*%ETQV6Eu89Y@>0h6R8W{cE(?8=1w38D!Jq|O;Erj-V>L!<AGtfCbC-#n8dH#l7t|21eTblRV#bcqkI+SQ8IAKkw!O7kg{_2R=HY12L@Oa79S90n{2qH$uf%Rk(my}@EgZK=b34dLQ|U)i6H<Qq>=&!<yD-B<z&QYb>sR?m0lkDYpK*mx1usWyeh=4(AIC;3NHoP78NFn{!uxWHsMhywMCA-*^?|!JT4i&WMYVNMZ=G)RMvPi37d$vd1GpB9x*YTK_yCfm_iXb&>Tileqsls4(mt3A9*@74)Y~{g(bjaFI5`J<DrkLJI&H6S8F+00TeSM8toI)!gTctpH#@(h*Iqk)G-|+%D5CTMN^Ih?=*tBbOEuOW4t;~?FT4Vku4PJ4QoS?K-AbQbE8{V#(RQ>dJ{>x&VO*FrVL)SwppQ$M0aa~WmUwJ$5u>%7{WyXmeN*1?{uBE2|2>?%i<}cYF9Xtx!5?RKB{wAU{$nh$a%E3r&&kj0#W0niY&%dnOQ5#*rukT(Cup`gA#ldKpBKoanndXsbN4CuLw_XGzWe*%V-2r6|pKM%1{IB#hxd(DyL_~!;$2vwAPV0g|e7|)~p0%Q4MF}uwG{B!EFt+B1m-8w>^~U`M)`$n}`bBCiwcsz#Qdn0CC6b=9Xe^HUrR{m<XBN+hQ5l6jDjJHnShdo8?a;{v}R8C+gOzpg6BbF6~4cCFg25F&n2O1T%|HFZ{^)Df*B3lnS_<pAN4eajN>QfiPw~SvZBr6qGwyX-1YPyH>;`Z+g_71FVCpGe-ZZ3PhgTdK{k-O)bl(OT!Ut!7%LVCHE_EN|BxRAb+PMGeRGj1S4o52I91Nq8NRNi$ceg!CRq2Hi}0VkmWc9M5s57TV$2mMX!<<7i)A?HLQb3^X#q6#P?+FD92x+n#2kd*b*5X%j2#H^l9=h<|t6h?He08zjt_0LwQtNK6MwXc6-oFRRIa9Lk{7L6iyU4Bo2@ov2J?TThNq##;a{1c*jMF41i>piAu=al?-${DC)+oTG9|w(OvBhZ+VN%#6_s;Hz`ThHF{7Fe6mBJ;ypTu_q4*ejJI|;rV0)nF21KUa83r^WYW@|ZaSz`Z7XVbwE+6aQXCiKv!icFqzsB7D=qko_Y90!m5T`M`&BHxo4~HP=fg9H)AGL+Pu4(DC=J46Rrk0n0Hioxk~y8)h$4iVSMN{7E!_=Pe=UhkHj2sS6)BH|(`*&cEyvilCRak_@qRR=BJkAHoZOd2r#^3V>!VLKGG9@tYTR(oso;b5xaSvBvdT-*yFCX_J&4R!sR-qYZzRy!{d57=9WsH}%bqpDei=V>^HL1CrxF1<M<?8+GDIAp;_-<%rBV7FUbYrSETZbvuMqRB+8#htcdE%gbSh<Oowj;CN+(sdJ8J;UaLQ(94g{d@fC@9trywQz@wU?pDLq_g`u;IPF#?Qgr;)1hRPfWf#*7>yi@b^e>sYEH1F-i*_m{Ao*cQYnV*q4qw?XKbsH#I!kpM>QD)e!*7VC&O4m1f0JQZ9nd<P+TINHK>0-}$bVVG%KU0%Pr{Fb|0xrBi2xgrC?MEjexs7afJ*fx6b{nnUlg0PjgXDcz;M2@CWGWz(v*+zFox2Ka$lORTlGb`Rv1fYnb<>ed!b#S1AkQj2ILxOil;G>M=YCK(|z1W)UVV3>Wy$F<WMd3K^R~rT8GeNW;C`2WKIuq#xkhPmcHkxz<7u0%!uxpwFD}E7ea|Hl$%n3V2*51$6>q|X9@!!ljPqnu)428kvssWUCHNYGLSaC{uzv8GnKpYy}Fv-jbt)$j5H?Oa1@=dlS<md8uUDVaFFBK37A&22>(axXf^iG^;-e72B;oR@_TKbNRB@`#pI`H1)Y?)}zC#rA#4iDpme2~+*_NBtZ7XhI&{^7UHN?w->L=LaSkx0{0*i#vAbu5KBuk=o#sAilH3-S=BkDPp`olf*7PfnO|14VSLyX4IwI<6!NZwNpL<75+%FSMF8hvUkzJb?y@yD3Bo@|}wcnH52sLr_OtJHb9&`W?$QO>*RLOPaS)RB(3p1{2AV6P3BNQ#Qb->r~5^zZMa_k>z#ue(Ot6(%_O9V3RwS+_PCB)G=yRpUZ+GR7|Ic#{1rMMW+>dRiHST{T6dSKqNL7&7fiEs;mQ_9w=DAf^SxCaffK9=4}+lo>F2gQ8Iy@Adar(jQQxL(#16PiRKkk%5vqvZHkH#qN7CJ^GO=$#-Yi?)+m!v`)zaO<w_h=3}W68ii(tsVwkiW#wyx?7a|oDOmUl|m8F0H<6F?Ew)#k9BEO)mS@7rT)1{QBa>cJFKG9x!zG<nKAIe0r9Eg*8Rv2ElczM<#7?;onbz~Q)fR^rX5;b2i&8Ice4$Aa)R3tC0W>iYBX0aY){7xh~o1Qk~Y>M3LK$x_im?@Enky%WRi1e#lT6eZGE=&u3tHLA;G+Hl!1Nng&b+Hn>Q9<s}6jQ5ve13MucV33R3(|rK^$@&LZ}jaWQr!$H$g)17W6eW%#AtSbtMkrk;&Ym)V!KITYXL=0j1?S@NaOF%_phIQ`gOv(?%w$vw<e67+sb_g!wwf3uzeX1=;?SYOaW+B@*4>t<=68<P}RCB2bL@v68gQAGDql0UHl$V$hxBqTfLV19c6XMH2sj7BS<(R8P@3eUWJlsVS8c6%n9Y7gM5kF5Z4~ZGwV~lcK50v9tebnP*g>iHF`Tln#MNy-;E2kp79qqHbT)ArbJv1fq^AYF9j54Hr=aVpP}ZgXq9bneUez&TAwRgA4I|f$&Z2Jz_y0ONDV$0;`d{s5t8EKL`Q?A5Q|{<N?5RSYUT|W$Qj|{v^1<2NKCnUw|>-98mm_2i@T^gQPzwM1?nhURm$vU(f~?CYEnfZ#ikM2jpQq2o(j=9&CK7P3HX<EgbDwJ{FY1>ADB#+QxxkI5*;5E2dm_Pm{+;TF^fF4QuzQgF&kbUQPn!%HKK}RPL;AA7?xZ@%JO^4M28e#qL={OmmzXIjdMfgq6o4&lEv+lyHr}MhfH`Cavu?SGb#Tj7wmHNsD+kq7D6{kTf4t}2w7`)AqOFOSF51BMYJ_!Vg!hs>>?3VPptssOlA&EY@7bkw@F}vD86$cLG7ZoQS;Ji2C~T5qfRvG5YuQ~3Bhe_^5(Q;w4=yKzO2*%dqQPc;E8G;RcI#aJjHg1N?|()n%a_$lM(HUQ;9jHDJbC-!^o^C@+bUA@hMHtWOa%7odO#t$$mQSKm5S$%~2p+VQVVSmKGsnn>=ih^vQmQ;i^`&uY1^TLOxsD2o&_hbqAH|&=hHRybTd?yedR7ID%A@!#i;iZ2-Te8>`6ZY7W&By20VNQ~fL%Mha_m>QPJ16)kk9m=iQ$)g>(YnqGDFD#{3|K&|=LnY%ERX{iuOQ|V#B6wSS=L5DEsHBS;HKXX*nR+z;AvMaH&^D<9Wmj0&NV*VA85nSsL^xfrTpT@%ntYDo!<Eba<hdF!E+XOy@3wqn5kSV3g)~07vbK+*@mGxyY$SzK`3w7^sj>qYxW`W|xn*>JMSG~qE`qsF77q7G2hM&81nWTlG0TpCe<9gGXs!HjB3SV25^i-=5r@=Gn${NvXgo1p0aL*zM04=8x>|aHn1*ggq6hJT;0}RWcqBfH%amNR}U0oW@Ze3e6zo($2{;1nXveajPqEBg}N#eu21k}2YKJ;2jsB0Wyk~(?}vYD$w4d!W5<`eI9?%(C=oXl0h<;5bR8aFlggcACSuHTFF_oYdz_B9I8sL)FAR!^J!I#=8-#H)jUXfnznU=O!0#ur5U2Q7r^PCUi?tI%+VzUX*qf|AI7Ws<5o;7C4ApfnN(ewR2liNXn0{l|-JxI)GHPBC`y!S}HaS@bPY;3^GXwKmVW6ENO^nI3l+Zlt17YJ-cc48{ao5v@*sH-`N|!4H_pbQEA``BK(L7F!*dRj8aNr|r;H&>3VpE!v1^Ru))P+m!DtA$z_GM`Ko=Fn~r1BC?qG2lCY&zVt|U4g`L+e}(7oVyQcR_}TD@r1mXZC2Bs2apMBw7n;e4w1%-}N`EWBLe|j~?4^AhA^BKlABE~rNpFj{4HmiQP}7ig9qBE#;ryP)kq$_NL3!Dh7&|i$zllx#3}=JwspxW7tBBc$HTwt#@?jWMla44CA@IL7L|XJBMu&dfDXllO#_crtNp5pACEB{A{IjP}riDUwP#)M>mQ0i<p9Slv_~_T=A<BezM*}6XU!~(RXmOqXoS!&-b8I9CTpDc$^9PCFH?lwZ4#Zk{7_XxVf+nQcW)T{drliD%(cz9NQDPFY-SMf})q{ZQA$8ndxWht#t8-#up4m)1tT1dEz3NG!YivXcC>7Z}$H+Uf!l^P=qO5Z6Fgk&OO^6E?+a(#j{7g-{#;;piU8zCt%}Hei^Qzx*SobwWfG5v-Z1oYp?sM@H!hgk(=nbzatb$r*BHcRNQ|RASM=NoZ(RQ62f=7jaPEO7y56?Y5b5H{muTikJOGzytMWNoRL=?OdHEr=CMH9VO^9SgNW7ls#+k~uie@{i5oFR3nrsOp-Qci|sptSRBHO$eyoL^3#+O10)!R>Cf{0YcDRUBU~ajgrl#rrYm*P{B$4aiY|Xts^My=pe797^_$-N@602}W*B1kQpY16#P4iU=^#C}TX5uf86JETi<mT?9j~vdLo2XR4nR;loIP^E{h;h1fRXp=-#EKc;Z~dko93Gq0kxSCw6n0CKrzN+^tA$!VTzf&G{TGSS}5ufMuEV1z2K4tJlcDW*-CqlulLR_%@+$U~Jm6Ue1~!PtfNNKYuhG&nX+=Ot5REsp6)piY6xvsn5#$HgJG;AWUn)3eyVwc4BnCSq};q<kaI+-;$sQ{Y+p*oT<UwCK@f*k;W(f)`hMdew1-r7yrr^r}8xF?OGXbYki}Dh!op1Y8!416GamUceH{2hR?np!wx<x4pu>0zy#a^FWp5Z{j*$ik<Lk9HrC!fk*01PYhIpGzCbDV*{OmoG7vGF*)P>5DI*`Bp<imWPQlML*Zj8-{Q)ET8bQ3)}l<#bz~M!eiWR^C>Ju(87R7%bpGLvSQKhGa75ydRnAQy43Rzu!3|I9<?YRz!yiQl*hnI3z^vZm^VppE8TF@TU;sxPO&~Ky;SnK}RZKz%%Cb@VB+D|b2O~w=a~@+L6FfI1K#?S1<?yBjLvc>%WV9;T>~f8|iaxBBOtYOAHBZt;XH0UHV7MO--DoqCuIExK`4Wya32Lsra!xL_!U$w_ySC^PG#f+i4!S01>uL|$$@3`v)H6z+a&(u%-sCoj`!u_oAU-WjbKVRaaU67fwUBAz?f6+~(8yF@S#Z&~D)0XnCjP3;")).decode())
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
