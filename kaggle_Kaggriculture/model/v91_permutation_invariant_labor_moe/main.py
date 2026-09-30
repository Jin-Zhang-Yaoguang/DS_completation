"""Standalone permutation-invariant labor matching Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v91-permutation-invariant-labor-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlK+m0m3k=?)ab3KG#;*$F|9M+119kPj@p&As?Ac)mSB7`LclG4k9|E}(?j0kggbF*U}9+_F)11x5X*;SEl$2|OEcI?=HzWLL?|Krbp{mb9q{L3Hy^UeSG)8GE%r@wvt@y&0)`Qe8*AD-U)uRs0ezkm9-k3as$pZ@m0fBMJApa1aY7r*=cAAkGq?Js}#?T>Gs-n{?S^EV&=fBf+Dhd00a?%ng7<cCkc`@{3|FF*d`ub;nv`<pjUbN2D|@5lAyZ+`RLufO^J<3IfHtLNw6iVrRZF@N~*&!@zY@4o%F-~Bdu*k;rp-n@VQ;m6Mp`_0>TKmO|TPgl#=AE@EANACbMKe~!(_MN}@-FM&r@{b??{>R^ahJk$H{yj~`eE-e2&l^n1gFpV$Z+_g|*ZKwj`pMZTLf`!O{O;wCi*MMTd;Kcm!QXyUM`Hhq0v+Lr>+g2QK=2*}#><>)^Wrui$v5F3m)={4`7%@Y(U|}#eOKbJf58s<4{v{G_u=)AS|JdeSGsKft}d^jgv#~>Iw;ILcxYCX?kk7KAfXR*{Ua8FrYBwv<)?#v;xYs5GYO6^5jql$YlOP?AWOvaH)f>slL#H$b^i6*w1EwI<j*edg91kS=<+bb9hYj)&P{OIxufMp-lszPgY=NM-+%x7?T>%_*XMUXe)s)%|LwDrj*g63#~X%L&Q0#L^dLC34NW+-kiDX|JU1TPibdJBS)_06wmuxdu6$(EW>Y@qW%Q;EhIt4x`lAC=A!F9%;vv6$_x88qL#_+A_z><^^TYG^pKfx*;7`jHx6B1?nG3Zue!6=Di@49f>cxEd)ydEM?H5D!ET=*kG6;Y8@!dD?fARe8-S3(0f-!E})3a^9#18oa*<56v;3Ga`qp$78_~F^IPJ_F5{_M6*$+Wj=+c&f7mwO%h$}!tj+rEcwPuHIgZtW+5sE+NdL(sYak=L89OWDUw7`7c16cqQ1RT1iGy;NFa3({6!iHbDt@)ppLeO^DC0*AEY{$mEFdavySVmeb`M;dm0v+TOPBFxPvuviVBhYydr6&sE_&^E0HQg3?4HVh2DWE(aua4&AyV7TSK7gG9e1mClz0}ZehXMf#zY#|qnbNAoFb8O#!i;dW}&v6gZt&~E!dC0Z(IFJP@+qPY4Fx3V43Eg3Yt(tWpV2iNF;(&mA>~&{3?K)VAJ=|u84G(%8IBR3xQug1zeGl!)+c#hTz;uz3H)rNw`(LL!26-(zqjV9pY>m?H(`l#9b4ibYRi0e?IE%k|_h0dWvN!0@$+S<?II((ra5bj3Wt3D*uU{*K4iA94<<PbjzUd}S_PSc=)U>6y1xlEKQ4jBfWZl!kd1&#7bV}>@)-cIjHCG^>Zf)<1c&TW~LzRaUZe3_%hA`(oAPRK-BlaaQJSX3;#_A@_95g=XqpzRS{Z81g?RV^OBozJx-bvf@4PXTQsc|F6j|1XIXWZ!<O)}m0TaA*qMrV1ZzZEU<e3^dO;vKs3GOKX)(<8h-EGJNI`_*6Q6~5RGEF2>Y+1E9nZfp1UL*+hQ{vrp0>DaS9X*=_Au?-8TVA!R!#ju4j-;w{d`cngs0UG@_U5=+Ms?e~^w$h+{r#7YW%j3@$LD@&ae1sE4+5$K1Ck)mWE=X(-pFCk4naW|xa5OUxfkmX^``+f4?4Eok`V%cb6flINP%W9GHY#U1V9y_NZ%Ge%>XwwUo}tw9%ziYHLmEe`HsC-9b1~*VYRE(Ir?B_cgIVJdt#TZZ?_h_hFkI<GJ+*{vHteieqiOHozWum3O*LEcNR_hTtWUF&6t06Q_N#inPbQ33SE30FqciClF4mnFaIi%AN_-N^nIv9vz82#tNi1Ss3gE|PE_Fj~XmtGQ`1lB6@l)x_)LqdQr`T3N;p_^Xr(Uq|BoHKeuRKfC>uLCdq;#CvUtCl6?K6O*HmVXbm8kRaKK9Eu#>0*HP6^&p*Szxmt=$^ho-fo6313uSVSyr|m%NAgMYe!~;p0|zMY%5ZVvN=X54~2cDQq#G&3tu3wOjh0#@n3FJ-;jZ4{c@G%q@eSB%X`4xA^@Q8esX#GiQc!6bB1`_CMd2OztF@F9C<k61kOATxVW}*RswqXB*DM${VRx^GH;-+9{^O+A2@~#xkICohc^_7Yn`3B&wLLdKQ{d`?;0>7H&YQZ;?4wxnb2WaCWy!Q;b;~RC-`b1s->S5pvvyOtP@>N%wC<&{^E~<SQ^!cvXaS>>IH(qo4DzzEohg543%KET7NhO*p<|v4;0uCD|iTWvp#$qL_JTUWBC-hq@Rt6P>$6VU<%NZ?#JLNC8*QHf+s+K@LMY@2VL?wHCEL=b5@j)gjf>OK4>Ma?`?IaGM^vy@eAJ+X*0o48aTrshHrnaJe3_!}kbt1kl2ka(`k@Ib}As>4Xl(?YPYt{5>@YFTAbd`I*@?OxcXut7<r4Y0+-Wl^xT8IFOTQC+{;Ek@D2gWOO<GHm}mqCv&4}s%&At4)$Q>H!FD+)pAHJO%CT5M-!Hd)A9<G(M;yXC7oFt>amLZ6nDxO7X<Z0TF&ea?|ONdY0%?f4noX>G4_w?i<u1tiTAb?A~Uoh<}@bql}uETwS0q{WBXmF9>BK{cjbIaW$KifubdEMV<CyUaxM8Sp0#sK(5#$hWzaV#4fP2;r`MY&p%_k9ZZR0kFiyBoFIbh=Xt?~9ICrY)ol`AXx>LeyDZcRGP_0(1#ctSNWIu$j1Y=d{MGS_Pmz8Z*tKJg0EQ$V|%!Nd`8L%HV<@d@LjyV)E2N&_a(6YGVT$c?l{7;T#R0V3ylTcM<<Y()rN6x+UjLHS?VU~_?g2Yen+n@aMyZ^!-Fm3aY{}K)cePce(Sr?^wfGCqwXj;(AT2>;JOHoOPW^R>uc^9-m@bwAI{lXGckZE@?d0)M1SimS9pp^_rxesPtZ7GkFBH{x3$Z{k{zLZ%M#gl4FMT1CMWmm%nC0Z<I1FwcSiAk4*hq<pcZah%rf)G_+_+J4?S!h=!N*~JDhHStX9-Q-fC|JB)FciaZcu<x~5V`tVy$!j_?v0POcKDA5_KS2k!tPS-a-Vp`?ZGSx*t8<pOAhMyABG#E7bM^{G7D5%5%|s@trS^_DkU0K=TTs#NuUE;A_PvSDIm2S=ud5jd~Q@?si}IH#j0=%a&v2tSvcp2Nrk7%sj}%Z4c8SixXa_#0=Y;rPg{IhJ1uaPh&YFfIXpru)pebjkON3@4r3tNtPpfeD`ipACBGamMs<Ztfuv+&!7P9&Gc9#KQh^y0OQ^ARfnmx8@<(#D%IgaUo*4W%nD<HdEWh2-4OM+5xL8|xKVwndJy;G^d=;cT3$539Y8t)vDkx|&Mhia(??)#&>~dEC*}jr5>TizefS_F(%ezo1y`@fS0dr~a>fDja8^z725c`st16&wVH2J^*qCDlWhlKJ~;O0ED4nbv>bT6x&r;+TM5Lx6f-9{;`UfdrtK`5?fv$9j`ue5!$ma0*}NVSb>dAJY(cs1E~pN)(&30jT4SuM>h-DBR?8Qb_nZL%h)DipG>&^N1U6~_)17E-Z#15&gAO8wOJO(#f(ET2>68W1UpG7Nfze{%1zk-OOAMq`y-%k6<ev}JonvBozAk}w9sNB_Nh`{VU*g$}ZOZ(3zjT2UPj2dSjkl(<j|8-NBpN_ePs6KdO;m7tb5r{MFSfXbmmEJIW?)g%k@lTT)qK$x~tzV&c0Ow7=7k%AVx8Q+KjzN%Gl&`c{d65m3(7)k{IR>5KRWoG5Dl&j#kSkc=S34i1rvew`gCy%Qa^>?T2f=d1vd6VYjZ<2g-G`j#4A}HRT`9rg$wnB~B!R4Z}!bV4Lpyk7=CGVzFqQoZ_gC%S$=<6V_hYan#D}T*!boAOwBrAL}V_-gFr<EKf#do2x`MO)wAdn$*M#_cA(ruT4hwDp?ykN#dp`oHdGE-h%<Yj{a0gr(L2{-waC!8kei&O1gP|3?!)LGD&8J1<1O7oeMYI!ZKMZC+q%3ulAi?OkiZ6WbySwSp=oGCVN6C01Kh$=?Lc!c3QReG(qk)ef4N*S#$#;|XL`Zio^)!HnPAVsS6#Yz~CFxga5ypj@g`Owk>vrOuW%qXNfra_#pW`d+(ta6nB?I^1^nuML1n_j(s3DKohV7JHR;_c#cXekFy-%<jfa6AaERj&u<fF9lDjFz@l$qb`vZhh29Ad69MYbd9Y=}lH)UaXvol}#-V1Cm|=cs<owS+1T78_Wb{)3HFxh@<+&`k~(smMp!xi;Bz$BqC=D%t-H{$j0Muh)3F|?T0b$eUk3HY~h=JEky3G3-)Fy^G_^y(+GxIudwV2y0pi5lIk1nc%f8KaJLJ%_0<7Fp?vwrZqZHUT;*aTlRS90*X{?%T%C?n3$Wdoxk)ju7iTHJwke^2c(2?wPqMlPAs2XYL_pJMcD<)d>k-`WGDC$~g4S?ta>fsaOowzWlf}Z&Tah?9fdUnIvtn+vu%rVb=!_j-C60&G0p|U4Rec1Lpg2bClKab4slQRL34-qLn~AXAg^(`i-vzIWt(T4}Z^43}OdW}T{oVKf#?pqIQAC+X-|i>q!fzGChHrhPGfE$nBNPhiirLbyU-TWhMr=%@53@*Q3FyMufQ&|0u8t6#sKx$Uaw`XDHO+w9LlHn<B#8_lYwB^SEJ&}S7C!Ep+6Nm38Qc66@#48R1x8LJO7#xR8BxuWU<?;D_94ZsIu$ocMN%kL2+U2^rs>#on#v;uv$Ur2*lYri-B~CiJ4>8OV0}&l#RU8Q^0(@jvYx~d>0PqN9r2kQj`Kl!=HJzDS_qvP9b()W%2f-aZ(?IeBw}eiS|F}lwUVe|1&y^#{NfpAcYv)>gamC6zsG{H;`~L1uZB-F@i0NAv|jqtCdw)tLYPY;18Oz$(W>St>nd;zfx5I$_Q`>uN;T(p`EUemVeGIl5TvYG9j@6IYDkc4epT{Ta0N~z%f^&Xs<Yup<Uoz&Ot*_1bka_ZdItcl`bbgJF9SE+zj&;%015?-!=-)B8m1Yv%Uhxx{ldIQ$Q3qj0#;lDIB{;)Q{$oqn0^m(=~SIkFGnuZ#mt*$$_uyO+@ZNv9XEWD5Q7ZDWkC)x;As#%@rk|0a*zQb@3$VzwRcmzjEONEF_jEvzlEfo(%3?*R|AO~w(K{43zo}pl>QU^R8O<d0>j6C$`GUg#5;Sfi-jS)hO<r34&NkCR<e;Y5V09lLmuZR)faX|U9-{$TPXpRsf|{OT4f^D4nbv-vOyNnflXwX)rzINDRFaYMfgmSjD}4?A~P}Jh5Cy`RetF-EEmT!)Ud=RHdy0Q?kuJ9koeIL7M*=45-9~hz=Vvrg$$PM4v*?cl@VeVQ6VSt(;N?_i6;o06KJE^;QCf_<cC`xKt7W}j}Bp2Nh~?h(adlUu)#R4Ni^vf%Ybv2dd2{d6{nGAumw@zv~E9?+Q#M8x>OmetJIX?rP4V}`$lHtb$}?yD!bx7JWl0JMd75Qkg`&VQwbSiQL2NHsG7g3aj2I`9e_DdL()vF5qYuV8;u0)8gxft0cNgDNl2zPDeKC0JW^O$yVM~v*w}31(+s{>X-`>0VLcO8pumf(xFyd1Srr)}0i)mIVHs_kLUMI27oyI#kVWnKAx+hK(2F&qws?tc6NJJfl<kA{*>1V+UyhU`QT?hspds8_L~BytK@;k!8eM;4<eu`)$sZsO5k-+A?BOhgC@pL#UEpeyviinJgt;UM&uv`gHK&XSAhP5~NpvmOI{7C_pdWaZ0C_a2vQgcB)G+b0Ufr?I_$T3$syS`jEfbcJM3DALlr9A3c(jRZS2nyB3oPY%B)tz%<7Sb1$6S|{X(e_gk#(M!P`7%bd6`l5RT)TCFx!c-nVN(GACIj?Xd7&gJQ~$cgtOgbY-_6ahypJ_QVTao1AUFpNms$@2BqJjd}TpdJ3We-!Z!Y9={Nb*XYRei%zAm%V@yjIO{;Fb5`ijpmdeT|EfNi!l!PpVei_SB-GZG#oSRjX<$^UXslt*_$_SenK;@1GYA5>AJ0+=HC<2s^BTTTOWpn$IHFMY~QqUuH0Sx8|O`e~MMpn`%>-2BngE4cpl@A6)AWxRlu~J~n;jK|zb84)&`aWr9i<LA3_V6gCp=7JuIqv`|Oya+r&*}F3Mb(-Hsu+A|XMYisb~03NsJ*0W!B0sxQ|#hruT4HkBYOtoP^obZ7i~Uvy%>7UNasO0Lx76y!V%7)Sgs~8B)xQ3<OB|mb>{(euA*OaMbSIE4X6tNS6C#*)$o`IW|i2Z?Z}-BIt-w3Z6UAF82$C*@$HfuRqcuecAvl|Rsi3#5m;DEubHT9u3}KRi|HXbfeFI|yyRvVO2gPP{A0^k_1Q(aDfVoj(jdEzhjKe*$Ww0pDjuAxVozd|T_B~2zq>GX%b=?z-_09ZaA>2HM3m&DVf7wn3W(Rk7oL~y2AXclXIW54h%Ap_LQ`aYF)dFEi-5{gvmn^T(y^WkJ(S}W#gHWe41j+pNbAv#J(*bj6*K6sUfD<xwz7&fTQ!c#1zN5!JWAS<!brx>Wl*28n|33ESsu@Qqb^O#Nf3G7W(U+F?yw#W+8RkL=7b`8<*`LLqW9OPQO}lg#K;~TXwqA%s%XLLDvD<IsZ*ZEhS%D)2U+yXtFw_wu$MsW%Y?B>`8W~yD!6mS*;UzViFQ_VsI9Y`*V$#|L61RRqcw<eK;(7|5Xnre6tS0)sEx(HQ~alRzF}%v2jqJ%#Jp6PK6=7A7|&AdDj=N%r85+cdX?p2EZzlPWl1d$6F@V>p|llAt@Xj;I;9{BO4X=0*ab5WqS}o?w@I=}(xQ=W$8-Uj@R||GNHLqj9b2}cGX{b}{3atS`vr5`sFA$H3>-6djD(_AyZ{smuNJOL!xQg>coGhXm6vkN9NAlMjV2yw?U62}ZoT$;l#I116s<Iv0EJWqwJABe-;g&bU05ogL*t=)Q1&eKz1Gq<SRIM2aPpCgB##8V>Y?Yl`a2i}^8B%&5_8lrV*TD02oqTpwrC!zek30xQVz`67y{!~L$=Zc6tnIlA|_sQgnI%_b5>JkXlH8S1kogpA%+K(ngK}aT5r$<XlxxRHskN=x_&cO;RyPpIhOYx?&bqB+B78@fc1fEP;)~O{}B_c7gG=*1zlcY+4(N%u7DHAP<*6Q%HeBqN$%lmfSBNlEDS{|CzNXp@&a>cwukai9ek<NdOzu|l0XYdBuR505s`0dJ;Ct~%Ca_5j*yLnNiEXeKO67)E+W;4rExIjmY+*vG2;3zFg~g=pY*GWyif_%wB>Te%Kumz5y~<y2Er3VXi|4%v=56hdd=Olio-wu=0qD&3MO%bJ7a}4hY4VnuS#s@PN~bau=>@ge+E%T!Oqaka}*TE^{z7rCEvzxYp=Z#X%LEtpwxr0x}u?HvH*w;ito4PIYmHGd^Wlbg&r>wvjkwQEJ+ouUJWQ5?nh?M8AyL+XoQAf%Hlz&`6DPHrWGQr3&NABp0nm_V^!~KCy~`<zf^iztL|9n`Y&D$%W)-KZBaR_QL)s{4AvI&Sbm_jg<q|1L}dFL1jpLME}3&jdDhjmoNA^CKOxB?*L+E5f^CL2d9~`gyrDC1G`OCQ;*|@Ltf<3;N5pU<zEaU?>e$doY-46T;g7XVQLXCmSm7D;cIm}E*c8;OYJo-(<{&oKF|0}5PG5^b1sBH5HrAWM@8qG97(Ie;JQDglLS&O)Z8cUYxDHtR+K6pzn*%15rHLvEnIZ$tbu_&H<t>Bhxm8znuNh}A?ye3Vr?@FpHMA2c|JUyU`K#7b0k;TS;+2Zw@7t8naJm~-g(;?|*fFM|R%GgX6QfN%Wx!SQiu(G&x@*Is3qn9r<do!C1o0(l|5r+Fh3MGGXbiMd;IOXh;AuebkO4;hDwj8uI49I_=<Ns84g!W<#~T=QVjQ32R_e8Z!j9I$DmA@MTvSEddFnTPDW0Gm<n(}ZXbCSfF4;a}sc=$@5A9$M<~Yi`si^~He8s`JU?aepqiClD^t{S#MZ$HVmEd?Nj3;dvw(99Nkuv^h%>?LVUYTysf#V=Vg#+#jl9B=QCs5&)x-(U(x-9VoO^mtz6_!qvzM1O4hX}aKHX@Y-g-Q-Li`O#EwK$U@a9}ISav$2;%JVMgqHWJug_#oFHj0i&5kY0@!<BILAPth{Yo7V_<bGvR)M!C`GMs(O8x-tB?Vw~$QtPh}+8C@*jz>IXYK#;mldmDlR-w!$o|tg?aD0O+Zyz%9nrK@!!PX+j$3zDLAT49aN2y6JQLI=jO14wxJWrV`r<y2Ku?7#ydm+Pr(B72BHWng-j*TnJ#mOS&6ze2h@X3&(BY{-cnssMa=t??RJkaaG_a;`*Z0PT!<w4+Nfpn}lNv(A$z<`-sa-JHiWYT79d4XJ-wfLpTsC4Q9+jh2e@hLtBIe4Y`yI9Ec9?^hif_t^=56DEASlXQ$Ih95DD{BNpQe(6FN!yva8XPG2R-u5xjI+{@Z2Cd2%dN+87?*A~D~UIhy!YWNZUG==d#h0p7zFtxLFD_b%`%}Jl3ZBpZmH<6iDEH(uC;{U)L^qb<B4-cjCSyc2VA$IulkZwSqj5%l(^S|H_Xe;Y;3ypkVrB|t~qeBqv0(EPM2~Z2lftDic<@u)ep+r3k{Y6D8gQ1eAN6-EAIh&i$g^rrFcTqQTYH-lf8!>X`j+Ax@M@WshBM^O$Xj0d6%ftz?cO1mG*+YPqh{@)vGFRJJ*8&y{R&Xf?ZCfn4)Ddu@F%KuMJ{gwOl3Hf^W5(<}=WQLG9Iw1&R|j9}jpnmH#=cmntbXW9@YSVQf(A2oe7BXj+(Et!q)Ux+a(yLlm!&@)m2-DiICETMXhYRlIia7qjVmL0GW>ND~5!DEcHY@cjMT-#~StT(UvYCzHey#e<+gqeX-KOp!(Gb+cnG`_dswp7^#mT&~EQ3`a%r2!h5ggq7}y))$?~vAxQ$@6C)~`Znb=q}!&#NzSWQG0eciD<+XG#VDDKjU;pUJ|`kGvp;LG&{ew99cTpMD>6K#x~R@%RUB&()kn@Rc3DHitk~XQW~nH#LE8mF^WkR+KBRGJd+4)F_PADBpi&TJi`)W6H|VS!6V=lLaq@K*V0hVuMM}P4c~msEDlmz_+IWI^&7qWlw=*@xc+S}@L6oHi>D;vH3Mt_TREx(@G<i5)E(+qY;c=zEn#eoV@s${W9Dx_*?4ui|Eymg~eaqk#J|KwL*f@CseM)GbsmIl%)kdAiGJ{Vn0JACaLppfJixeeIJ4udTOYd->>GK$8+cBFA&dZaI?-Enx^9(vpxnnkTWwYjAL#Z1DQfnvH14*>I3c0NM5-2xdT{{rCDjjX2#@d9p6NWB{3=Vb%h!EXTyI(2WywnE-jA9|nrF@XX-}uH3c>S~bbp=l@NWxLVp7m-|DL?7OUgNb!ea+M<p-T*wd+nvvhNMBTHiaG90`OB)BF?e<e$kRN3D5E5>z6-jk&B&lzcVc$L}5G8r)ATKGIk7FV~G(zVVTgM73$Dx)d&V|ROz;s%8g0<1PPTott+d)WgYGNXG^#Yi*)qp!m29YNg2-O4xz?lDJIpWsD%~(Qf}6UdfLkk^zZb-DB<jib!x3z)5d->6y+T$@NCqm6C=YK*-@;ZsgM`A+I@Vo%Pkq~YBPs=CHu*yMpqV`>Qys>v}SEWG-`k|*0fy<R7%_XXH!q#W08~=fw}tnsC7^gnLBMFa?BPgHX;xud>S+tz2*HBB7v2+w4zN0aqxAH95c;ByONyNfmW7>l%_p!M@RS4a+YYJ1xe{$ihOnviDPP|aY+N_aw&wLG+8x%`VXD8<D~F0cx%Q;Mzy-!UY~Q+l%c=OoJ29<UPz=~x1(qrR8hl50LrMZK1+|P!Aa~MCQgMgz7A5}>TjN#o226)dAriWx`ZF7=UW{$S}UlXwi$*^5t@*iljfXGP(F=1aWQDZ={>dO_NwJR1_sEGYKO}E^cAbY$px6crE0S#?e;>$z9@h&9-LcM{raf9y|>aWqzaYt9_(A=Rf-IpSb?BO=+s_fd+hCKlT_h0pJ$q&V4S*)%=L|Fu-*GB%5g32RJD9;!ARBvU8OarbyzJ%r(K?~VBT@kp+RI0_k~h`DqnRA&c%UFta?0KVO&VytBoo|N(TFW&5iw9rAW9gp-<;0Qj03RQ*(19yo?cY%I8`zQ)2pvrN!-STOlbroCphs!X@8nw50}aru6n&5)WYgmz~X2+p^+^CZeZJ4&3mQUEhdN{fQmu%*@%NoJrct1JLM>H+f~^dO+0GF8Idqb+i|$bF){tVL57?eG787?yfNDT|5#X!hs-do)6fCvKW?$kh}I?uyzJM)^8Nii?Eq5-c^{0jhx7`N?ZUEb`Z^(Q)fV1+A8$}Y<Un<`C2TNWt65Zey%bjrC_UY{*g{eS$y!IXb>~ErKYE%X5M?KnXNkPNn!$Ws)$dZ>N2}NGSgh<(3QbIF^(x`IKglsQf}IvG<lC;VtGS6v5-^mKLZH1C}cHfCb2!W#;T<92wVMU?T6+AB1YvwrN4#pPEc0qn1_xx!a(l+=DNQI*><~ZxOPGoIb$N@Kor4yIS4vYZq#~Q0;oX^Rc>0u6uVV6zxqOqT^<djK-cm00$wBbcqjFG<*g|%i#=5GI=>o*t0AO_?a(yTIbB;T<;ybn$iSh)PO=6^$Q5DGqHHPxhB`|?gki8Y7zrp?<ciq!LMmCs=w?VbQLZcSI2EWgSS^Y}qt;bQ6evm6zY-2_jw6*0sM#>>pvVMunL@*oXQy<&sD-EHa#j8{2tXj3r7)>Qo){@sjKSdIi$OdsRgEpEZ*p<2*bYiyH!;72y!$n(#fyPu_0gqfUUrMqPVYEHTT)_Dnqi_R!eHz5U0yP{8<e1~CAHJGleNphOj+27SM!!p7*vZGtF$TR)e$->60fPEBp0~u5|w3fs?EvuSt9JlqfT5az04EE)*&+8+%Xqd<Mrx`wLqPyzF3aleZp!c^GN*n<NSE{_Q$ovo>5R650si$q^3J-uu0lrkStsE;p$Y6jbW_vHZ8{Ql(>kkCe=_^+aBv$_qgly(wo7uCZa4Dt0&nVb+W0y;rVU`3&POOM4QMjG1_-X(*;Z+Zfd4fs9hNaq71Q4{zo(fBKf(EyrA4UL}HNG@}n*S)RW*SCJC7AwV~T)J>Et<2lMFoPGuiXX;dpmcgoB*Oj|{cMy0rQ`H7)G+T7w+7PFIHJ_aIP`rlH9b?B9p0+7TSEY^ZgX6&L_)8UlaMb--7!YwW8i;4#^rPMAme3(-->D2cUX^cF_tii^W(l@u$tq95XYV3?;LRd`8)j}*O_|T>h$T8~kaJ|91V9#+i5n!R=x3=wlj|9QXElIlVF!h|k+O$+T#LG!ygElI)){dvO)xa)&RldznB}iwh6Y|@$ROBiZFJvuA)irIY+~Q|BVk0I))$|V@28LQh$ra9WO0txt!&}kx$tX#ElEi&o(xXFDvf^~%<IZDS58C%?uUNQf9oz39hrX=s%*H-8^=+wQgvu(G@n`1Wqz>RvS6+VN11btSCZ@$T8nhY9W+Nc4v}ELp2^^+u2cJj|GTX@?0c>4cTH{M=n~b%CmBk(Oa&(M-)yy;P*lk(r6@iF%^ayAx>0Y?CqMVb0>^j(TnLi#BH*L6uK-ZQjZB3WUY(u?y0Bb|}0AyY<D`1TpT)R%%8#GHLnc{Jwg*s?-?}2X3vQVJCpbq1tR<`N(R?W=Hrd$jlmgnIP>@D4zr9w(UOkR%7^-swum+~^nWGY3}lTxPjp*G`=HD(6sp3jJGvC(xkgN}4t7MYJwTTbadW?H|LKFVmXt_IGhDxDv=V9rxR7kao;GALC8^;WF=_;|Vj?RH$8dBnCd5JUHUKViw{{>4%oUTIm-8lIZV-WKTIJaWsUK+fi)Hb9~RZiOt>sxm5jQZ-Hf7MVIAYrORGql-yPr>yu9t}9^qs=)kj>i!JmpM=)P;?1fIrIhZrT}W&J6fxM!@dDcV9%IKHb9J(kCg#}>mxJw%r7kOsI|YV0RB2vcp#pG%13MRsVx^^57<MbC9jqD^ntBR@8msl<_cBO{dEztCQsJ106@~^<HFIE}e&+6i6jLe6F3M#xz8N`3^kUx{>)%DbX?5eYosq5+_=L{LHUS!3Z}NDlI8x*;hfS&nF|F{m2TQi4uvg~0VqxQRsIP|R$V${rls*D%a39X-my8n>fEbB5y-w+#jDV_A<6yqHjjQ^M_G-{NPjHbGaW<MxIq<8%RV<<n*%2))u(e7j2B{o@5q~l;&_QWAv8A#qk0-CA9UCf3ojnwumMCo{x7M+%;~HMHCi<m9;5wiW>GiOkM4QxD?9Yc9$V>c3W^s_@7~b3GaZB5!%0ZXKwOrJ|#lpr#Ou{?0`q)vt*3~|7&?k6iPdh}Qf|$~BfblnrVq%fNVA42$2Aegbv@~g6oTWD<W_x6A;j@WjY?5~?XCi;7S}gQJDH4r_=fti<&y5Ao9x8!eY&1belM`YIO1-8IxHZa&iTXzYiq-p8R^igp1DXxoVN63Q=*svd`=u6`y@GR{m}*-~<c#(mD1_>2jF96HT}C~Z?Av)5QeISIgF~c>+SF;HEh_TJqW+43wDfEc4$%ZZI<fM_Gv^ZmgCdV-W&oEt-KgJv&@QG@RkJCe5ZlrS_Kbsz=CTuoWg><k5IH!2_<ftnDOdc0nx_(39nbA)5mQik25$skeOoU2s8xoCIV7ahl$>F0y8!F+t|<NtcT}jpB;brM&%E`?vjFo+W-V#7vHB0_k}NB%9`BWHqPVrpCs3GDQW4bFnD>1rkKr|lcxfU+0TQJYS<@vFrBH}vs~ZZf_omRLBwf5liv?8N!`rA$;2~8aW{6GZG5!lgyW}0y9O1yS>iCYTPQcL^K0H<&b>t`*Cd27Ns+3ft{>HgbtE#TgkpNZ;8aE)R&QU4}WdcTePf2gCcog4drgMeRG=;Hd`!`KjRC48}i8tVd!G_s>U}+bBYa2G88Cj<XmL<sQFN+g|dlyDAV2bEaBl^^}&z0yJ1nCt44$>|^s7s7zM(HDi>xX}SeAYky^tb={(?329^grMHpTGY7&;R)IU;pxX*zr@s<mt_y|MLHS`pZB5`nNy-^!a!G`Ptgy7oYwxe*SO#{1%L#|66&$6ZyZ|!{~pdhrRjXSI^JCee*97dTO{nHK0#j9S=W0e14`s`S}ife(3Q006jl|&-di{@rqTS=Lhoq;bzYdU7zon=R4u~zUld);rYJd`9a0U@_hgK`Js5eJK_26hR>JqamMF6<M{XIJJa*MdHfEVKkM@Yd4A~f{BV7K+`Q2H`H?(7-thUc<MW5&`JR7%!&8I$RA38%k0bRlNB96!e@3t#VB`UT=a#TN^3cP4vemQGlbnLd9E!*b9LX}*``L7h@%XcY{_NrU4gUHKeV_fZbh^*acG|N&`fOi3+n@OCfIr*Yo*hnocGR97&}WC!o*jBUJDsG$g1moIe9Uih`Z{**v)%Sz)3YP~>;bqTw?E_c4(LG0;Sdb?jvZ_}_Q)@AZ9DeJukx+izwf$5`{b7F9^=`;cC`3(`@Z9|ja&47YzdF@Y;S$G>-_9Uwo%u4`+s@%fE_`N+yDM--|^Y8cy>7L+0OE8XMJ|O=d+{j`0#+wjy;~;WqhycBoL1V0%*>m)7?E@7tVtZb0j8z&SgEIm&XIoJ|hqi&{eo05D>0!#u=A&e|>iEAcJdrwzoZd=>BYf4Y|DBO!}S#_ETNIXVa5_zy3U&uv>>ypB=5wcIQ7ki&v=oSA67ef_HN1**%_d(*fP<G_WR0N9Z*0=G(XL_Zcle(@QCQGQjIIi}yu7zxeHy>HYMOgb_?zyXDLFTwr5D!Tx1F2{f2Cf9sd|ETekzm$~HNWI7&LzRaKTWy#Abf9qiXR!_bm|28>kc=&4@zYT^qw0~PUMTgVAE!_CqBKfx1@@@QA?LRO5zt(m5+Tqq;>&VvvvCr7yYr`2|yQp8gr=r%cb?1NWO3E3?*ZNz0txF<25RIV6*LI+z($DM1qA{VO*wRLnr(uZrm@`UyFes?UJc~U!J%paVs%Nl<@1azYl3iws8KGaxu}CQE!x-|hd~KfbNTU<3F%M_vo~!{ExBd49UptVmHOG0-ul2y!4vk-%$I7tp&(R(l6LdYk-}n6f{eRZCq<wCC0zpH(EYv6`reTHT9e3m)=G#JTy@s`~uXIWBTTC8$Tlx<xGFR{Y=ZLKxXALXgpF%P$-+|85FszuRdFaLr?JKeKu((v#{@)-~FKEL$V<3hDB(v`x{eJ!cd&c(|k7?(8A$&}`(Rn)<&W(9EHa!!|0Mom>w;k|3F=-{p`});~Mzri-7?SX9dP)vwe_<eB=<18a`h`~^rhl2TFq+|;9r<Rbe{&@)+BlF<48$h`8L&{BHW2!uVMId`HS%pE^2vz!-)R|OWCs|oB+!Q$V8{-A>i~Vj0G$^`*fKDBT89VbYXh^te{>{6|B?7&KfC%+UJ?3?h#g0npJg1X4$>Ec+;8^smcWcEiH3C>-Wur`2+7B(TVyDwQUBr5K#U_Ncqg4$jH6QKJpKBpe*H^UYOIeU92o^I*xZYwtD{H`!j-9H7|%$KRdn~Au6*;CpKm>$iHv6*!%Nxer};eJd^~gWc;ZRp35UlMPaBUX^XJy%xy8NZW#A22g7Gsj`>kctza@`JDj~X>gXqy?{yYMI9YIi*y&fY7BxbX}PM%Di%C0Goz_*WJA!q$ry2>?R;Dr%*GJ;?jK{#y$&OCxp+4#8uRSwkE@$Ka1eS9yo#MKXgHyWQOSJRjA`4h(Hf$=%h_`*YtZz#s+KaX!v#^=THd0>3rFuqTiT}VP@9bW*(=T978AP4$#eB&L*HxUlHC*ylbLM@x>%>Bma$oSmn@wq#VFI30pnDGr=$LE0YdGq)#>iAs8@uB$b^UpFq?qVA{jn8lKyH8`<v*ouKUr@$J*Oz>J%Q@p?$3bgw_HnrDINT{XiNK^qL7xV+-v&<_P~UO%1*H2Gt4h;<S=gA17MLNL$kzd7eat#qCg-5qfw3Tj&15J*QJ^rCSY?J(rVTAQ*l%BONnt-!(xHUPPy|(&bB7X0U=ABfx~Hi`v6iC8DWUxN<iflUR47U381=Uq=tKrO^c-l^1}eS~Gc!=14Kzq;Hrqh+dwau(7cydZ#)v&U;;dXlrKT+;S?;bON>6eq4>5GKc7Ph=uf{mmn2OSuZbX2M@Fy7&6eDgm_5hB3$i^NGV-N7y!{M>d*LbTZ8k7ThH}+5NH1^uUR9osNlDvBvI5ln(is&E6lrb?S5>xhw@g(e8*Z?2El$e+z9BJ@z%2$aSShW9ZgbrziZSkJAh3$>0+vb%U0&bgl?2z?n8ZBIBTp%~TA))Fa>8G1pSf#a(j3u=Ar<)}mM!bqNM{&gQCL@j@#y85_I&&<c_OmDopcOI;MXPdk%}9vlQ!yr=L_Cg<ETCbAn8<>cZ+^^5)<*N-0tB1*I_!g^m*}yGgiN;`oFn(qG#R@ybM}D5j1Nw`Yu5P{Po|-JcIXo`^!S)V_asFcGX7DxCWxZtM#tq#3yN@Tj0e!MJ80|yIJ!Eu1m&rl1wOHWCRk%(frl;dJuL931q0z)mKKD}f=h1;VowWb5|mm%g|4g?xE>aW!cz{iz$Xd8b1YaIEf|Vfbg5Y2+AN?Diy@i1DZy@vC#HmiAh=5wVACnw!xTpXGl8VKLqgo5ro@v>2}e!wBrp>hQz9vZe|S?Ix$h5K&XbxFZ)-|f4+6^CA-0T7wn!F)8(2W;m6K{gS>oE=o`~Ax1$*Y}e~;M{aeErA2uXG*w_-|YcRj5*JZySl%!fUmJ?z*x?30KPSQ~<or$t}^jhu)cNkC&HxAbXi!KkPR%9q}Ta0?}=m*O|^dh4;tJ&r=?){17xkeUnmoU~5ZZHJ&Si;H06jUC79E8`6$8A!+L4b3d1Z0xU}zkmB1ri9Zp@TJg!C<nffPxiG%8MvOp52YQYO}v%$@Hn+BmycLeY1A@L@`P&&!KRCO*wD;G)Z$QBd`T>hS@JLv7UxK4Z*wP$0~BZKVRs};>CTJ}RlEImPLGM*?sj(fH`gaSO-OQgskuAV(<X~5&=S-@*G4rwX!X8g((;g)?5VT_r?h&wxz%YNO|(CU0|8=AR4*fw-rNJ2L&7+=X~zm&6E()B1A*Hgi2Z?FgJM>LHYTxhYJa#!Pi|v>vc&PV1Sb1^X8&0DKP0TveE05Qe?aVa=h$B!^{D+Lsd)EUS8PfoTVA#OOOmVf<fu84bDL+h6F%8LUc>1&u?Nupa2xw0IXZhX^G70f;|qa{xY<A5(SFy-{wbN^yZuyS$5rh&3S3Kk9pRs9XWWYHxq4&qiTy5H^8>loQU#H9{*RwOxs&~U&87-?F)=%BqxR`vr#7>l9JopUs?}Jv*{R=h+v%CcE2f9SbpJX{pE54jPD9~MkBRA1{dx}Cr<k4w`<gA?8CC1HJ_44;%+m3EOWO>5-NDT9Gq^OSLNx+oawQ#!Bf%CdOh9f_F>Z)@zRVPQg$P%}CXz~}G2ECKX^$mZ%>Y|Jk4cH!ye;)JG3w>NKFLIm#J~wsHt*q^!$x^x)Vv+`*G%!48Sa}VT)c--J~1i~qo(cWmw)xG5!M^nI3+eN8Rg4gt=?_CBsTi(cbvHgkzg_`w0;zUF^js^5m?CWyF_4V(W-CzryC)#)3!JS{I+Q?SCq^MgeC-(t-N;cDy_V1iUadC#8|U(?rNn!-O9jPxm@FC^Jd48D5cC>pxIrmbX{U>7zK|huaD{pVa$T5FXp<$+?UCGxtY1)cIF1f+(2|ba&t|cCdMXny=<aX0?`S8NQ62l0GF0l8z>tE>|@pg2`?gXAuoE|6frm?h67U}pmEkyk#HoSx@<_y1PPZc?2)Vi!xxLhye<Ayf&@LV#%+VANH|N!kMU4|^#mkhfyA^OX-0y?a7DrkNchJ?BI_)%s5A<S#7MM#DH79m?5!aY4j~~FBvuRfLN_GRL>i4y?E&@_2`3`q9tH`yvJ(I%&#<jQN(q>m0JGc&7~!;i4o+^%M5H+zNBWlKI86yo?n}c7xLrDu<D;3LJ@-|jHWJk41T}B#1m1?4OqIPkhBt^kYfWg5aw_R}j#&_TG&ZV<K>yQ##7D3}@6pz|lDx4ty9s&)@zFttV$d;@?;0h^TU9vcv_XgKpz|(2>7X6bbO)IyzVGOLGWtOJ)J3Ak)6y@eJy>|yR9}?R?{WJ{G&S7XRI?_t)pAcPr+q|95x1eCflfOswaIeiBE>`C5(s?OMEmv-M6mJD2@p6If^YzWrHQr*LGb2>AK!iR{uj^h-u<4Fg^}*sb!0+;%tYc16q%7o{0<G>lNyl$3aMd;L_IwLtWbb8F<^xPEO!Q29;gn!FIbLb_#=7G_IGYb>WoLy#_Uyq6>k7mEVe1PZC`u;VHhk2mMCjw!6jISA$s%c@4o-Hw5ecJ$j2#Efu!_lXRt32s_fTF<bpz5PLZRul@d9yZ+z&E+#*oj3gjx+npUXtI=qQUR4hbUi9)r<L(YXNJQh@eXcJIn7?*v%ZiKWvAoPXGoe33wqQ#Jl1#)8*IZrrnLNlpTkc%2}Y|q4Vk;_Hi$E|03`gur@6Vw2YA=e1ZK>(%-08>$h*bG2Krw*24$1t(!6*>}aPMg$gHn(&bIcvlb^O6oT7UM&Qf9H_(*buU=@un$vY|56?Je1vqE8WJ69y4Av-7jhIdV+NzV*4=b{Mm^d8Ru<KAxS;QdSg{PyZOj4JsIYdDDLge?K<(5t;1YM#Cd1o`XrH0dl;U>Kt_w*(^1caUAt^?5Jz+mc0Tp(ImI?6X{gvVTx}}5G~I(G++vfv+B6VK-IU1fHQ96m?-#Rar-7w5%|tuNlNx(>SC%ir@1-^^36X71v;++{ox|xhlX!>1rkB|`Y#LX4_qsa~cN=Y*3o710n~t(`n{8UQxtG!lCqhMy<XU<w!mZUN+IeT*yfP*>jf6)Z2@lHMh%joksic9<8RgHBRMkSbOw+w=f}5C+6?*5CG1eT>%$sc%cA|8)T9^}9eNq!hE%c;02DQ+i!!I*iSejg?srrmw5Xf7%(%JpC+KePjGg*RKhxl|{+UuD0q0okR3CGA0>uERRsOh)e+IrYt+Ndv=f%1eC=(Fy_Po!<i>#>*K#X`c9h#3dcXWe*dSp2T`R#-Eb^)B0AhJ*(ivUmHQ)|am@j>Q9tpiW0Ao25QLDuNm_tpGXxHOYacI<E4n>P-gaN&!A0A4YSC5$(-(szIJH$dgoAOv*o+Lw~n1XeI{jn<14e^@)7cgkRF{V4pASTS(+Ex6c=nt=??kH4TJD#cp7CBmt#e`C%Z(cwaPr{B&J86eN2b7}A_tS(rK|4I$HRm+poz#CyR&`IG}`gyD($=W-x)z`zjhFdN1y47sAhsz>1N48xmmzj^oWE&F>0K%UqW^bvd(g3oZ>2F&<yVI&nFkK$7ro&0jOi3WGz-2bo!+L*|P=2`~>1Dg98Gzyw$K%+&U!v>m1K??_C&auF%0UXx?P7uLyDma4~oY#kjE6_;auYrVa7Nb-p$kbSeJ*j9g(DcD&N@P1PB=NlCGLt?1%fe+6a0wYMfe1<sNnvX!aJk?bh#n_Uor}wL7YI5&zQAW8twr6IexWpW*8`t$SA5u$m<rd#z%_66`V-M7o03w9A&I2+fh#^1To)Fuyci-BaD@b}iBxO(YpU4>7sv-_L+`0PTi+N=O736fHa$_Vo(PyT(L)H>DJi0jZC^c@c@iKdqO5zx_6p{b3BUWF!Q8<NSxzA)LGeIXn?BLp*t1OY>ju+z1M{vaig=u&J7!`Hp*l1@qHj<<;DSDS`WKFv@$~O?g@|M^9!WQJT8oQPk;6^w#ApCH$#o=*+?iNSnaybjwob|+4`%gB>fMRbY5O+OYE2L$lqwNy-NJ3n4~h9X0h^{vCKE>(m6<pd9Gn`G6R1;gLII8=;P^W2yAwFc@8@yAM}li1>9#pL_)iI3zOQ77B-|nWc?HZH!bd}-IeY_wZ%!(Ke}=Ds&tI9$yA16>czhJTr3t<^SqwyS<tS=;54<`~OC}jICv5<|A!X4Mrv_l2bk!A<?N49FOM+9(BySrS*P%rWqo!X2se_$}(_U*-!)a;7>7Z!HEpRHM)-q}#VZbk>7U7b0;#x?u=h6)|ZneG<d_uas2}qZfd~^ab06>Q0K+5!19J=(Ma%qGrr+=)17(@_<dx7Zg2cj&^MZ+O36Nz8*+Y1rsI)r9C1x@h?_fW9<E3A$j@H{ym52O^&0BblV@KP6`P|wF&Wbw98dr}AEu22u87S)p)A7|OqYcu#O#5NY#?gCC@a!UrQ-V|)vT=gqQbW#wF<fJuhxe31|zTtdC2Sn@5C|E>q1>r10NSlOH2!jBjgisWA?<0^P7=$VY3n_!*FbE{L<p>6$K8+A9xF{T~?*qmcr+PkCRnMbEyr&_95o|(JkYy7oK$()#lU#8;0;=u?f%GGmWhn~GPF@0jEJVupAWi=a<E`ur#7<Yy_>P-Ym`xr76JyUeF|7pe7z&<6VQuXgGqLLuh1rb4H7(z$-+n)I_TaW7?M*qESz2^&$UX@i1{f?P2Zf;agjRmSAO;o0xzJO;J%|B6eIq3N9+>8ThCn=Cqiz#PDDV)k@)yAn$^;-bN*r~9m?H%tL3JzOp$hm+qIEmq0|U6fE8w@rSuC=H5O*-*?gYd=fVhYEEiQ*42umHoTABnX=sr8CyDI4J2<WaK=;0vf?vX%W_e+|WDnWMybk`SjuOyDYOwdCC`bfmf_OwAnK@VqweixKASbYUnUxjtog&#Y>8UR@NN<5Fis^fSJxHYmxZ=sj%UbZd*Ja9;+<&of$A$n>;&xz=TtV>V0qPI$Wo{OH>4`q)E=2{U$!StDUK_oeo3#7&Nf}ICYb%#*ht{RUD@4~?ANIjs-qW{1dD;|P3THvi+>>dT}y~>hi8(z?!uV@ch(~|KT=>i#^b+qHxg?1o?awXbRf_5NzuYK>EZilwsK<+HGQG~7F)55xu6p&oVMQ$L0{G9_gp>+jj@V_vS(|Q$}MYymnD`?<o|8MshZt98n7&v|*{WAC#&$WITZOP7R&t!As44T56lcKtbZJZI|jugQ<UZ9hDEL2cqr8sUPf)i9QFE(iZ-D30$NxFq=6}cxRC$YXz069ffNc+I(_lkvd^o}GOguTR`0_<l@5R7rx0+pFizNj&$H?U~99$Ex!Yb@@O6cJ3MbZm|FQdHLX?t10xg-Up(s4Nv!T$jcmLEg)iLsh{*2Y5{JFh-Y5Ol)m+GZ2NOHE?hUBSSLm)qv&N!9wKfpp=ROus(v?1eTb@MAO%20liC7*Se5qhK>YJ?ueRy1k@Zk4ef<FD{2>ln%_{HEvSvhk{X>+iz;dnMQusm&`93UU9)~7@@^*7ViRhOSWQQ;0xoeSa&fC+T0@!3R>?#=cMn?yPKWt6eObuO1#&T|2sw@%Sf)f8tnv`v4Y*JMw~z?qya6{R%zAK%3&(&9j|p7Nf>H~)k5c+r30y-BOlROiBXEsSg{<AoLe$DelEhx2%7d!&iS3p^gbrX5tHEU&5Lif*e<b<o6cbOTn-!A>1R<vfU#=ifep<-hAzH3-X$2uZ3<#b9!HFQy3|zR@^_W25xwYpS>5N7OVq|PFvKor4nl0$lcLCv*79{23abvZo&zLdpV$$o!BAX}o#i_~Q@s$gZQ4>ipqyhW919pU);lz3!+!;otG3Ghbv7$z$ZM|uSAAkKFJWej9EL0ZsF%y@}L|Sb_mF}njt=JPspNziIM42Fn8hj}X4#eP?<qc>PAg3G5)p*n_PZW*1L4awc=zt6fAOiu!Yi)6GWv~(`HRw=N9=i*GA)}E*(m8zvFeEf|2*75gwIFv9dU`Z?qr9_FctZhiB%Qj-e8+ITbDslmI1I0UTzEav=%VntBk)Emyn3NlK+-8^;QXXV#+zXuH`pBmyXyzLzYXk*p?~Lb*kx^tm`N~k_)i7?Ly}u=#eX@9zX$O52>wW?x!ZZdUxUlL03P+kkSsvd69MytZ}WuzYCJJ!o>)i}n>KqJ$U){pL>tFV*zwEt1Ye4JbH_yDn2<RpGLDH>#{^wLj(5y*%rWkUj`3X_GgTe4-=0&)xXdxG&l}V3n1^)-=l~}=AQA^SA`3_}mJjBD@G2d!5aK9Zn)ZUMxCsI7G#K0gMdw_LCmiI7@i9E%L{BVcPb`FVJdkz`DIv+jZ8XpGL=ZiJ;(r6c0|DG!<@jkXdXEAR<ia)+Mb~oxkFOT+YC(+z|K3cBiapZye2(;aOyLJls|@_%Ht_FHdU!wVQm~~&Y#`F5bF%IX<koO`P(MVgA86kDPW~8)R>WASSH>ilLu&~Ja#^^*RbZX`@w$Qk!V1PB(7kO;{;E;s)JX|Xt>;&;f8ZOF*ky~iv}`BM&l_se?hQuyTrEpDv8iy{2hJz))l{tzFL)E0emy!Ev_0Gkh9g3iU<I0<I)((~bW=NlQ6ovrA{atfG^}Jz#N){XmA8N3j8KIFDqpmY8%dR=D+Esa75g<;w%r%VG3&cGWix3nBcVVJL<_Yikf9YwS7$0Uv~tvX<(vnktxH-fkj@Mw+!O66bV~*uZ7t_W9yf&!loPX88X7S44~St%FkH6uh9e4DRF2oyR1HkNw&c9C+A$>6-PCan;>OaX(USGUT1dkonmXdJ9nQzrcft0iXwC|nK5LK|dX|#~O)ghQQ&U;G5txBU9MDAbT3c3v>Ds`I4-96+qS3{-JfT_RND=}xYn-ASvVKkeyb8$11%PDBPKH~JAN2tLLe`5?KKHaDN>duL0{PSza!|a~?tqY0`=&>W%XU*AuHlK?0hcq1F<*lN;$a8mymIP*nQ_3F6|LXU0pXwnmWOlzEfT$uBrqk-UADm8X%4sn?lvGT$Sz8$DWxp>gamilf}ul_svHPCVrVZo{ZgRJd#bIO#Jt~JyxyY6On25_d7=l38NUoD%l33sjbS8;{gD)OO^H^&Z>a!oM^Mbi-UC5bAQ&?Q{T0DTguH2siQ_fYYCW}~=GNO0zUq2DoeT9BP`Rs*B{0d-s3uEA;(riIUR&}xXD3VZ?t`>*UjUs{uQh*YF!)Mg+M+N`o7&2sBSJDq63G}gK(Sd1QnQGZCw<rgQSw}wb+*(^18`nZIxv&VJHTqM>7CiCZhw^?a21gKb(-2hR{Pp{1#K|z(H;C~{RVf~7d{iJU40QYK33|B&^J#6xyDi>Y)0_uSartfE(?VyLg}(0bD1Y<!}oF7fimQV$M^N1Z}A|IW-R@gr)nMX=fL=LO^das!az~jSLDyw;?G78j)Dhi1zaQ^TwaF<r7FdP9*hs^!7|lPWvf>YM&iMx&4W!nGf(!Q>+8Wu^&nDygmulRd({_Sb%j^m&AqCvWk0*I>c*K#$j{q?ySi~NeX_U_QDA0&r=vgJ&HedgX@7Z=XD=11#k}1OOV9d^!-7`leBGWs&6SaHWvK!%Z&Ak7m6t7!-N}{VELVoF#g%Ipx=T?t9Sc{EL^puC(lxj;c6Q}09e8h#Il*H-5vuO#v2eD>dT<v+KTUV=Q>geUT>Z35Jzk3aZaD4Da=4!+EMxcT9OJ8wnMfa%k?dak4gQ{v0TiwMm*k;25s;uB@}%>!D`GE0i=F{mFWl&%D0}FUT{06*k16RBvAbj@TK6kadL-BGp`n)hXO{>r8Hx?xW$Epiv~(_A;#ikFIO4}hy3II;1m|4Ffa1KCuZ&x$qH^Fmx-axZ*4-M}S4q7IrpC5u%4Z@4`g+^dC^53sCbt#~BHQYgtDv7UI+1KaIMVhOY#Yeg6Igq=y6>IHF#)Y)gUKWHhMPUC%bVkRBJEvTH(yy#0oFzby63j^742d4p7(Z%(F3Vl-#Z|fny-q2+YK#w)#{x-czLqt=Q-wu)bn#Czzbmx+yyTzf`IfGHNf};G`Esay%1EXKz2+}_1lrygsKNnH8#XmLDreHlR?_6ALKskDI5sog95p`8RW4G<k158ub;nv`<u@fj^h$jc2{^(uQO%3rk-?~UF>a)y(Gol#}&@rD)9cU2!$(V(pYWE%9Ibd!gq6prN6?>d;)O6bQVd?CDXQ0#p@EayJThK&BP_{43`MKgaMaKM_saEUu&>-vTvyHW+dg$(-z_7e6zn&)Hm}(_{O*T=1gx)t=`z*jtjXkbKaP;j^!qAIJ2a`qCnrrEfe6D<OA2$NfC6?{+cYL7{V3H*}C)W>YcMi1;?31%sV;h)wpG5+%jeQelBTD;>ZfO3u<F-DR$-F{#jJvr`x$D0xxULEeqq8nPf&LB3ZWgi%H!QFzvU{+byBumfn8ogLj(v8?!!<BVnnmI%jdiI}p4_G`w+Zyu;(;y~~$SydA;YUGbg>-a^a~5Ew`DAr*-S0p-WS)w8(LVBIQ#F=c85<Ky9)fO;6<Hb|!mr0dCkB9P8RD?><T08-#ct~C1{4N?l=ov`(!HF8cnOR=TFhk;CE|8-(3L<}S}{grAtZClxj=Ca+1?uTaN(De5~^DAn&p5~56Q_j`iaNV_-A-7mB6UckA+#tAshzcM^mH%=?93T=+37U0{K)$s|t-`tq`dw2mH|`9^P7H7i7@;n#4k{(U(g+=}!CJ#wo7ksF?G4E$5*3bH`l^H6L94#OK?LI|2<~SQM-W`q5(k2ySx_CWct5O4U_|!G91S-EP0L_oA-FzmR0;~TBS0^=0s3I=xvlu$j62$F4|78(Ix$c;1j6E6h&c8c_2g%|AvO`zPjka4bU|MuebaWOsk^~FfE%>(;rqKG+T0LCH!R5=$?S$cRowS?LwyC6yIz?*;|tF?!iAbP0#3~{m-9Vi>H+X&`)DqF<U}8NgOB=@Sod<4d;QMh>fx!gB5~HmD2n{WIZN=(scuW#Z<Mv~o+P3CMpK-L+d@ybh4bAOz8tqrh1<O1Hn$0A#{+JQr@77IECt{;w@o*3n*-do7g1BUjR)Koj=60zmc6&VD39;9MRl9My3H4EyIqMj;I^rw+ivTp3GvgM`DrQq6q3damo3P9X<}6L_ES?){OfhtOJto^#?MLfFHiC;v?cnga@V0Ue(zM?*<ta^bl5J(?YEMk-C-^(c3XR<hbv9CXWjhka@dKE@gx<yHwBuKhL1y5DC-IBjCah>xNEqF4AZrfjg0%O;NEfK-yCVJGyP+dAjT7WSEQXPLh}2Ky$M`%GlE#B6(EhGWzGcc;t~?-hX<tsM#-4FSuOXc4}?ZRdryqltuUw@krAW1`1{)F6+69|C{m$6=ynE>3DVTgf!gUAJ6)Xvg13lo5gR`Vg}^pa@K=t)m}PEL6#BG#hjQhoAQnvwB3U)vlh}<XywT|d#6lm$oQ~KNDp+u=Te$_!!9o|ng$A@xqM*T9{U>V!hp7{sL4?zh5OG&H)vTrkSAPnwSiPF0t?#a<dy1snvLihR6i9w}I+nS=HKb*~cba&okop4Ba4$%2E0o==Q!+sbzB$2r*VJ7LN`@`v&_Hn*TN1Htct1AE3xo2+qU`M`$J?TO2-f95#g3evPGQ|^b*2PX-(&Jly<x4kyS*E}rSkni*vXOLJ0|#s1Neqx_~K23yP;Z-y9@9JR@*#<cdzP=Hh9CMz}pwkMGZRbc)BZ|V}U0XsTr=T@{REfz3}XVAm6%vxFR@hm;4k#znuo=qX@oE;L6VQ6gWrrpc1%v-IYRnPkI!oCs4rnmcZrB(=VhC{aS82vcQek?Is*(`u%Ew^9*qN=CRfW@xV=6Uv+E0`PYmW?J>U)ygcbHU*Z+E6Qdcg;}b2O58T($BYrCKY@zsk+<L@6RUkOrDZbXOTl|-{isUrA7KpOJROA=q8I9mO*&2Wj?^NzO5M^K5*CZHgu#fb4M<x6Z0KxYb4}~%|?Jd5x4*`_1JN0evQ+<307Ft8KulFS^erv_9z;d|LIw#=Pu}u32P#ywGQ1L=kvQO`aZUQ!T16J=^?g+3{r5pgZL5=*zP0VxHb)cW5?V{G4L)Z?bHshQFJaK?a+R2~efU~=fD-M`c2lRrR*4_<O$cHw_<E<fgj|X{xAa_~I=V@z03W;Mni%#$DAzzU0J&*%{jkfL%FSuhM?r<l#WBKPD8gkq4$C@Q|_QYK2a6b^?#>+KFzk6b^i}^;g;_?^n3AxBO5}h~M6X9o1boWH8cw!`;aHMi(AT{$AN`+ZDwr3Oa{+?KRc%p1M9g3FInkT%~6Y(rh^um9+A^uLq-@RJ=!`b-bDs@JWaIK;PDZ?BS0!;1^2YaNr3!4RkTRTTLy2cH6_f5S5eIe1-+&5F=n<n{yzP=IbWM6|vA_-9B-Jvhn#QZ{H{R8RWy=>&j;rjVW9+|!-kL)?Y;X3E3N2mtWNQe=;JiwVAiQPTIs481rBPdom-`_XBDA~__Lvy{WZ}zy<s$KI6d=p=rZ(LEGzsCkIiKgl9n~C(PT7Bd0=$m#Y+!pIsn8F`ny>ObskL35GsZ>@K)rQ6!0by|3Svq7Lr#mW}o5m}teA9$!AQ`}5q6*j=U|Yw#kix@2vO9FV-j?n+q_sh|jYlk7*jy|vsdPlFVQ=_+lDK%ijH`p)p<*`;)l$0yv3qH<8!RP_O@)!6p6j%tvaSndD!~^uPqbWbZD-x1zOfT39?byv#%L-qa!IG;Q))n`rW#O>W(>uXLqyQJ6lgi3ws{0CB=^??Hh*8(0y&{_unkG$VS6+xD9wgD)^mDBdgTltJvpnD^2s@nw6D3l7m&U$kWaQl{84~u+2(Q@z}}!A-JwkOMgZ?WBS<d=(k?-IFNPUzg|w;i^L1jr=WJ$z`9LuDSIjR)%%@{A(Z|8(e&^x6Fp)LpWuBK_7z~1@(=pX&$O~XTp%r_JTMS+ZB;b)}WY$dBoO!_!1@51{(8CLncws5L;7HDL_X6!^c%B!c!3$u~<lV4eRP1L$>D{qk`)@8p(tJOaW7r!Y4__7J6KT!lNP+*HDK4#$3yaRpr*%9TWB8vywAWVmp0ty7B>p;Y*HMbL6VZ-8qg_RNBq=6}_LPYi(&fanXamh=ziyCSp^!L{|Ay_<vM(t}a_I{K?F(=6TT9xN<3&b#EID?(<L{op;}UygQggb?yx>~C4LyJlS}0Z3mZ`uoDJG3uh;QtZa;qi`E7_+G_Ikx$N2)~QwrxzhDnO4ezk*D;H%I{-t+Za(<`ScYV6+z=Pm<d2t@``k9J`tA<6FaS)z=>i?3}fW^zAzPcEYp<wN-_9Av|t><#AJlFB!ti72)A_y^|02lD#wFd{yn*MzQ25Tu5RpY=v(y;1AHe*8+I#1NhhsxT^p@KTx-1t@mgTz~QyrD&~73@VlaxoWk#}9c(E4uc19}6aDZ+Kls8APW8i(_`wrDxcm6QpW}ykb3c^rbz|m-A<?ds{V>4EIe)N+YX_<38#^Sw*V%jNMv{7_p4k&~q43ONCRKk?o;jW~s^2{2O59L5YgC<e>FF$6m(QjgcX)8ONtwSiL@ZUr4a9$r_>V4w%VGb;)BI=m+M+sXy0h2#8q+25T3&m-9_Cz9^?S@~;dWko<-W>u>vPptdxhibtFU?Lf*$x9-!RwWtLa|8iYNIhZ=pL8C6ClsRAZI;YOfxiAHr8?Q(eeuPd1kA&D}R;#l#Z{M-GW3LLjAiHTU5?k;h&wcH=)AJBL1s`<8b1#iG6LNZd3qkx<EflkUC<xG#Ra?ptg}$+Q`)CqK`b?m4Y+i`UJtbYJM+miKG*POVihO^NPB%8syhRuV(*ozd0=vf?JKNpCN><E`L+m1Kud`OYy*`bR<-n34+R2)4M5(p6b5r8QbW6TTs%HiUu@kUjyGNe{MSV50>zDd-D9@Lb0@Zi#!XqB)p+&`M1}?Qs=*M$*JR$O6`hkf&mphs!nXxh~CU#~Qs9e2kTr8ahe#f`!8k2x;jp0V+?{kTMBAz)<-*t?oRipg{0FF!KdwmkMU4%3%*+7Ht1?CWJ@;yTsCODe5`FlFGU4mywYK-JC_}_8^wA7nboJSO$V+Bs8I;ST0J9Y&(_?=`+|J%TU466<E3g%UvpMFy)31V!8f#csNi44C-(Nbs+4k(?J!AVgXR6yMgM+`78%@BGoiBQ@dR6mwO87vZW;M52}AeP)jCi4(d!m4XvO$v(~htl-v#7sf+{kLwA>6i3z$RL3i57e<4{1LJxGq4bh#>M|ZBE8xnM<4c&>L>xri1pfk|9Bz<p~XN9bBV|14ay1qcyUD2Hhx{fG(jtx44$IuNGbbG^Trm{FfUl}uC9Z3pOU`JA#n*uvM8nEG1V1poZR{|T7>gBzI`LsbjULl<`VBPt^3Jf2AA7E)9yaae+0QRI-c_1y!rwz_{U5-nD=dT1{YmA}_zt7;G82Cp5|K2SjkWW^AL0|YI0DpYl@YD96xxjk~e<1Kj^2sXQ`)c677vN)(_Mw0;6~F@ld?ZQ72L;?e7~o%c<@8AEi_41Ylk240%A<Xf5#{xeZP~-_1D6Dlr)1zEtMQI-^IW?OGBEH(P(n^yi3ZZmbuE^(l{)fv_(nU@GTBQ-_jn?9?77Z0yRa&i+U(#;cdWw4Z0O2rs22=f7()j`h##!nYpD0-qjnY~0?|~>kr)cmo0Xv*6P49dkmy?`3XnHUQ1LA#SEw8d)d<yB8KCkH2o=30*Pxn73b%yH-w`TfEv(YYW-*nG1=4}E?2|cfaYfplak#EbX3QKIBJYRU(u|ozS4*P?WmW1fKTrp6mCZaIJpaJpxuip@44%un=T3&g(KgA|J_U&xiq2P{I|L(N_vx+$G%jnLH(alqAdKM=V08XCj*C)~=_)0e6vt4(aqfd-=!auChNJT>Ku!gaWo;w{av|*phHD<{Odz|JJ{CAmopE$z;_=mrbAlt){x#!xB6=uh2~HAdAOB73RavVW+|PiKpym?PTo2SBtfmLRs+?gHX`ix|r?{*q+ki^<9K{OhMR<GA*4HnumK&0)ksY)^K${GpO`>q+k=mRagXW9wn0t-dkWg~{_ErY6Cjgpp@rwg3WNj;HW!R8V=EJs;MgrPss{?yg=!`|<NLraS5TxQ&q|uQy%TTSifzi<<WraglgUP2SG_+vak*b_2lY5n9V1aRf1FMfJkWA*7$#{BF!522tkao>HHY#6?YGOx46{vm7sFJz-?Kkh<y|px8Ob0rP1D(l0)s;KQhskW9$^WkZkK%vVTAECSK`$Zqw4>xq)C_wXl!RSQw9F@#g=WjD$GP-SyN!>HD;bPM{zS7s7fHM%9W`enn}{DWg1kW*?4RnE0pLAV0McIHC98+HToIUvGzVDi)CZGz4@^RGPFS*jksK!OY)s<)F>wV+wm&9T<DYa)CKiSXfMF6i?>P(u(NkUdmlOtPx~J$cOsB#y+F_tA1ZM_@0fS+zUML(t)aj8x@uUp?l7TWk7AP|S$|O8p!{<p(QUnrEr$|K-bf=5SP;IHw4=FdC3)R#DRV<*QB{d@{wxilhhoGu#5toO6s#bYgyY<dV(M*oqdUu*huWbJ_a>;#s&a?wo<i<?xBe2Mw22o|tzByQF_0Zm}$S0bvV<zqrpdj4&VDWa|1G_XJMAbehi&bD&GLe=C!|vb<S@z3{Stq0%r+5q}GdkI$>Hs|i5_0hJ<M03dumAUN|Nhe-|NhgT{_zQ_{|}C6ft~")).decode("utf-8"))
_ACTIONS = _REFERENCE["actions"]
_TARGETS = _REFERENCE["targets"]
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_STATE = {
    0: {"last": -1, "calls": 0, "reassigned_calls": 0, "reassigned_pairs": 0, "experts": {}, "fallback": 0},
    1: {"last": -1, "calls": 0, "reassigned_calls": 0, "reassigned_pairs": 0, "experts": {}, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    explicit = _get(obs, "step", None)
    value = explicit if explicit is not None else int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(value or 0)))


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _positions(obs):
    farm = _farm(obs)
    return [tuple(map(int, _get(farm, "farmer", [4, 4]))), *[
        tuple(map(int, value)) for value in list(_get(farm, "hands", []) or [])
    ]]


def _inventories(obs, count):
    private = _get(obs, "private", {}) or {}
    values = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    values.extend({} for _ in range(max(0, count - len(values))))
    return values[:count]


def _tile(obs, position):
    try:
        x, y = map(int, position)
        rows = list(_get(_farm(obs), "tiles", []) or [])
        if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
            return rows[y][x]
    except (IndexError, TypeError, ValueError):
        pass
    return "LOCKED"


def _valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    position = positions[actor]
    tile = _tile(obs, position)
    inventory = _inventories(obs, len(positions))[actor]
    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    seeds = dict(_get(private, "seeds", {}) or {})
    op = str(order[0])
    if op in _MOVES:
        dx, dy = _MOVES[op]
        rows = list(_get(_farm(obs), "tiles", []) or [])
        x, y = position[0] + dx, position[1] + dy
        return 0 <= y < len(rows) and 0 <= x < len(rows[y])
    if op == "DIG":
        return tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("animal"))
    if op == "PLANT":
        return tile is None and len(order) > 1 and int(seeds.get(order[1], 0) or 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if op == "HARVEST":
        return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inventory.get("FERTILIZER", 0) or 0) > 0
    if op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return tile is None
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inventory.get("WHEAT", 0) or 0) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
    if op == "PICKUP":
        return position in _ACCESS and len(order) > 2 and int(shed.get(order[1], 0) or 0) > 0
    if op == "DROP":
        return position in _ACCESS and sum(max(0, int(value or 0)) for value in inventory.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inventory.get(order[1], 0) or 0) > 0
    return False


def _task_cost(obs, actor, slot, order, target):
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    position = positions[actor]
    target_positions = [tuple(value) for value in target.get("positions", [])]
    target_inventories = list(target.get("inventories", []) or [])
    target_position = target_positions[slot] if slot < len(target_positions) else position
    target_inventory = target_inventories[slot] if slot < len(target_inventories) else {}
    cost = 10 * (abs(position[0] - target_position[0]) + abs(position[1] - target_position[1]))
    cost += 2 * sum(abs(int(inventories[actor].get(item, 0) or 0) - int(target_inventory.get(item, 0) or 0)) for item in _ITEMS)
    cost += 1000 * int(not _valid(obs, actor, order))
    return cost


def _match(obs, planned, target):
    count = len(_positions(obs))
    hands = count - 1
    planned_hands = list(planned.get("hands", []) or [])[:hands]
    planned_hands.extend([["PASS"] for _ in range(max(0, hands - len(planned_hands)))])
    if not _FULL or hands <= 1:
        return planned_hands, 0
    pairs = []
    for actor in range(1, count):
        for slot, order in enumerate(planned_hands, 1):
            pairs.append((_task_cost(obs, actor, slot, order, target), actor, slot))
    pairs.sort()
    actor_used, slot_used, assignment = set(), set(), {}
    for _, actor, slot in pairs:
        if actor in actor_used or slot in slot_used:
            continue
        actor_used.add(actor)
        slot_used.add(slot)
        assignment[actor] = slot
    orders = [["PASS"] for _ in range(hands)]
    changed = 0
    for actor in range(1, count):
        slot = assignment.get(actor, actor)
        orders[actor - 1] = list(planned_hands[slot - 1])
        changed += int(slot != actor)
    return orders, changed


def _execute(obs, planned, target):
    seat = _seat(obs)
    hand_orders, changed = _match(obs, planned, target)
    orders = [list(planned.get("farmer") or ["PASS"]), *hand_orders]
    private = _get(obs, "private", {}) or {}
    seeds = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "seeds", {}) or {}).items()}
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    safe = []
    for actor, order in enumerate(orders):
        expert = "matched_task"
        if not _valid(obs, actor, order):
            order, expert = ["PASS"], "safe_idle"
        elif len(order) >= 2 and order[0] == "PLANT":
            item = str(order[1])
            if seeds.get(item, 0) <= 0:
                order, expert = ["PASS"], "safe_idle"
            else:
                seeds[item] -= 1
        elif len(order) >= 3 and order[0] == "PICKUP":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), shed.get(item, 0))
            shed[item] = max(0, shed.get(item, 0) - quantity)
            order = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]
            expert = "supply_task" if quantity > 0 else "safe_idle"
        stats = _STATE[seat]["experts"]
        stats[expert] = int(stats.get(expert, 0)) + 1
        safe.append(order)
    if changed:
        _STATE[seat]["reassigned_calls"] += 1
        _STATE[seat]["reassigned_pairs"] += changed
    return {
        "farmer": safe[0],
        "hands": safe[1:],
        "market": [list(order) for order in (planned.get("market", []) or []) if order][:10],
    }


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, reassigned_calls=0, reassigned_pairs=0, experts={}, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v91_permutation_invariant_labor_moe",
        "model_id": "v91_permutation_invariant_labor_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "worker-task-min-cost-matching",
        "experts": ["matched_task", "supply_task", "safe_idle"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        step = _step(obs)
        return _execute(obs, copy.deepcopy(_ACTIONS[step]), _TARGETS[step])
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)

