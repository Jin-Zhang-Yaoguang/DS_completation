"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%0RpQI8$RafSbi!Dl^axs)mAji%NSVOmR&R0Ky53<GfxAaEX>yaoC1A-TJEX1c$sbE<llgq}3w-g~FJtE#)|)T!#9|M$ti|Mee#|Jy&F{L^oKe)8tUyLV51`RX@M{^PIz^>6?E@t;2a&)@(0kN^DJ|9twt|NH7UhcEna`}Y0!**AWE^7|kE{FgUxZ@>HT<@+Ze{`AxLH!nUueDmRRcYl0$bMxK)FVCmH{ORWP?GGOwuAYAS)Az65-aIKief+T(KfL<Wi`O52?&a-IAO7<c{_^hoo0~VE{x;3@r<-^0j}!f{T(4gK@y9pYPhNfc$%jwwR%ic@^OwXL)0=m{y#3z8=&#0??;d~u<Ez)-{pEw4-~ae=am1_NyngY+`%MDFAco&M4(36c(_o_Uet6f*n|N7%e)8_-_3QbU1NFKB3BGuL^L7&9_|{N@(bQhPm=}@;YsvNQ$3ReDp)~eGy?a_(G*J6o19n>du#QKeUe+9pVQHw($V5rNyVq`uyNw%``GnDdwCAmr1^S1Nd)~NZ@ZyeN{~SZk1Ud}=?vtl0Bn>LxaYwm-DbemXlZQXw{p>97M6gvk;kLnIB#{**z`r~{HeS+LQ~JvIxkp{y`SGmPy?OC&R-8{?URm1R+HEgLS9bqz-PgC)vp?DUe+!m#`|}BJ*gb^{cKWNPMLK^n;gfp7<V9T{UN`Q|j)y<J<lztsgnlzi+S`;K4wBP<_xAPco0sqZ@`szZ?_a%s^{?Qjj=y+(P1&ozb0>E1yF2yxmE?*JvyP6`=?&qzdOeE~g3H<A)lRUd9)Wj{t_4bU_9MW1Ar0baBVFKz22G9`ZW-b=7zF34*_TMZop}S!EfxoCZDSRSZSR#2M-u;R`@nj4`{Qg@XKd}btvp?RQLvkA_zmnPzcm4zg~22N!DrEqT(uub=}uOT_{>>U4mV0WVPe0opPi1mXNQ-Ji%a<I9di4qj#=?Qcm1+*6k0LllRbs1!7v7rV=&5O&;i5av%IpT2^i*<1L#~Cwo_B!k!!lJFn-&|I>YN#BVM;Y9<V3L=89il^Zkpr|KiL*ctks-1#k)vMY31_GUl^1{xUg+ARb{OTu}bp``9GAiNuvL@2A(syKJEc8|(Ei502`Xf+Q~mQi`WXMgG1%8o}BR<B;$5(-ogumIMz|ulQUpSB`kizJcp*C5{&zDh`sebh^-w+2_{@a7yE?jg2q$f^ZleBXZL!XL(?=6FEHg5mPyp!x0#G&=i=oBJthv7^E2}Ro6bu!jqnk8~1DzKxs0Aal04io4M+!TDZ9B>Nj+Y{mx*`y_2Wu`Utnnn_|Z?oyTz2OR~jvk8jiaqL+%e<P7htBI})iIjCG%nApA9y_Ice4J5NeiM@K){2}2Z?td8Rb&rVDfA{wG&A1&u5-Qt%f$gR49p=`HCcpKY!)r$sI}H##!5c*>$PC|Ox`v4_+Od}{o0s{V-CcmBva`#A*V*>s4I*jX8I=M<DNVckI7QPd%44uVjtt-~_+gj_Zup$}Mn`^@b}-ixY2an?_fPV^c8j(#3=<VWGU0=B(v&87OtW9GBue&a12w78CM&`{aM1#XsR_@SmTLK?{l&<Ii{6$QzS!V!{=<(Y*@da)U@`vivYhgFZVu!r>G5yE7cHj8pI!Ey1%~ruK%-q3a}n?~H;T4P%W3yVb9K=>OmNX?`kBurO?)~N!|{->CuWVcGr?hh4k}Axl^|*LB^_aIZ@c@XdPPrglzQV0XYb9td;j*uPrtu;`}WVQMYNj=pDliD)0-mbnQ-XE9eo6LHsM};m))A>f9Qffqsw^^lFI_w)zoC^0eiXlC4nk%ELv3sMKA8m>x7j>T#;A-_C&ERj`_fmt{vX*y)><E46w`42HMj!c9R7aqTNJ5*Hy#7AT&W=Pg4-yz@Eh~P4y#mL{IQF&#ehM!LOZle_V`u3A^+=8CRE}Ckhb#^7*rc11A{tZePiVeQgYzp7J4k)`lgy@P6lW;{CyTP~|d>0A07@5Gp<yzGYu=-T0m|-iK}Jr`y|)%69d&wQtRB2y*HmQk7J=v>Q>U1Zt~j_;3#1Yf|31V)r8o(-MyFc52bnrrGi53Y$T3=!z3Zqr<6f=J6QQn8j#-y1YTN?e9Db%#7|Ps_ibH_nLoBE)cCaN9HUC8$nkw=TyxYSOio(!avcp5}IvepS#cBN=RT%_;L%8aC1y~S?gv21)hYdZ0a6H17z>%#IkN5_?F^qgLp662Fw(w5xS)9VpP|F5)^KBL?RcAOhk}0Jrkh;a9~Lkw+T*h2;cN?w1TJ+*P%w3IVf^4N${daOT8ooBWpr{#4f*$VL~|?vJMSoW<GX6H4B*N>O#p$!1YIC!qICOsb872x3>@?4!!K66T%7kkXl&5mPSQALH0q_vWdPhl_D$pSQoHzMxz<t2R?T?UC5oePp436><$m%EbqVeyKuB7%M|Ga!RV_0o@dp(Z=O)_v0HaVRii`g+|1{8Qf+_Uo|1Hz8bBeHwtHW2YHgq0J?S{^bWG>qfQLSH`0e1|O;o0UE1rge=&)IZ+lmTai=nz4@nnT@fJa(h_}%3hWeoh$2~rs|+B$c`qA6|sXDdX^YAU({6r)b<4A37$apW=92vpsaWdb%EBUiq-*xS&3;tpuSjAc%+AC@Yh9Gm$?>tge1&l0-7#3_qeJ{Csr#Rk|TY1$YRO<xee7nX~C4<q&{)TA%q4RMR9bZ}@<0(e?6YYK$2lC14ZVhofh&esHE;2aLtG?IRcUVD)i7*+K}LXIx(knI78HP~5T?5}>VZk;$R0@sS~hogGbvc)jm&fb4BoWDmF>|!#`Z;((;_j^@V$AKRZm?FM)Ihy|T>h&L=eC%Qug_DY08#!9j&l}}U4~u^Pt*f;0-u1BXx!Z5uyr6oPG3c>>6@rw)53?IZEq64<bk=l9!qa${%v=>?0>!kPdfRE^sw`|Je>OXS{yf}Anu(jBF4dI+T63o{@!=tft)62Z8vil_mJDK>XRyJl)+NwwW62D<5u2#GOn;^-jkD6sfeS5xWIx6aO{ZZUh;WHhTSus4R;4e59D_VYcC$sNsxLYo#mpMlUdblt%tZe+M*8D*FOh*vjSsAma??CKt`N!BxuMADezpd0kRJL8Sd=vnBib<p1G5^E;?8YQQ41Ryi^08<!|z{}H#if=dvK<ovBXA+Z<3c6fN`MiY<8^zSlB60xBa!&2|h(DGUrk589YWy25lxUqLyVmy^`dmGIAvzt8PROzESEymcG?r<H39P=k*$q?WtQWavf}partrt{+wKVo#P6N8R5L7gZ`R3W950SIg`X~pkeJ|M{$v5k(q&X14(MYAxegMISlWwYlYjO$5weXRi|I{p{O}BuUG8{Q&wfHSIvQtJi+Jn7!k$KDuJg-HUbamFK4M@!|+)|7N31KkK2o>K0)W>xKj2A7^=s<RmEK2=KJw{6m3^@y6KYLa`{RwxC3swVemrLDH733+dUgr!+XI@uVnY~3b?qWskMQ~V~s;;rRn+DmKRncYgCzn+_T9E7poYU4pk@ymQ&KuV##c7NLe7PO^bW3(n{7ic~yz`OvzVRPY<{PKr@>0<#{=1F%T5|BMPqd;;KdKk4(}JuUS5^@w+P*-Egpk(<JPXVQgWewcct6<Nn69uU-G2E<n-H2!k0CqZVhv65G>a1GnQ7SG~o59w)DBJC0fT4052I)~#M?%<Yljmus5m_J&gmbSjU8%T#F&t+1o=$Rw^nKsCg|k1k}kzrxdv&Z&d*GNA@S4ixvteb{&s@#mu^Zj`I+j~6}T=+)@Q<;^zM8X4OoR`CaZRFo(zUBV_t8MT?_M~UCvT{-_ij2q<;ZIs7vMFxv4SC!9zBMXSOJPEt<=lHeYpNXJ$1Vg5{Pp#V1v==R`31=>NylixO`Z?II;c0X3SCGRKiJ1*v8s?|vpZiQysyHv-k_~_`Z3gi?-(X4HdkQk~(OSUz>cyxgnGG@m&kwplu<jdGpRlmwOqT^b_OEz(3pcMwn+Af*4u#-aU|HfB^&mb&zJh4#bQ>8xGEh~?=w23I+6als9m)-@*kT3gq7IV-5B_SpqaKKN+x)1BkY50&eL8uW1QYUI9D>SH(vC{IMaWe(;<Hvx&S7znQ@7?KsE4|323{m0;Ot?o8p9@laJMOE^>@L}5UenzRH<|LjMD*>fi+GBxhZ-Qh!^%qc+pgpHo6v$uG$mf9D)&emEnGHmGq#ROM*Wv?b}<U%U;|OWfAbx@rH|mjf=K|SY{nMkIrb3izKsL2BF^RZzj<~!QMSivQVmb2D?dB_TsLOIn>fpS;=0(x5?RLc*ZbM#2jB`sa5S^M75CxFEVjBepmCuQYS0i9v|lAfz>5)LpT>!Q4Y;0n4cWbzJNtr3eGF6+fs&ymyf={nhZlWbXIY)tPU%ESzu7-=$O+dRGJhLSQi>KxDZ*m#-U*pdQL3M3BfoF=A4~STnUX_iR`o!g5kkqp^#5DB1W-aLHKx*$jhEElG78&zkiNE^4+u++KEmh!E&7_CEg3f#+Gb7k<(=J=Y&M0!|ha!={D8rF~qtlslZ+#1Ns~`q}aGpHQu`0l>=Uv8gp#8|M~PQF?@!9N!4RMX*kMUV<0Ii1}g}Ef$k8}**MLr^@hH7<6y;ErVW0S*SJT{O=8W=o~YZT^2lEIA`CA*2#OTNM(;XBcvbCa652YrmHX7}`WtmhidkIIXY-OYk<UG%HjqP+c|CD$rCmDLCb;PO1vr)Kb$rztdBb(7xH*fW&5DTcD`4F6VS+DqKcVrP41ox@+e;abwc8?kfFYJDeXG_u1@=NpIve!V`$@I`DqjJ=thBXKi<FnsTS-GLl}ru3p0}C`OQmg4r7cZr0R5Zd?v#L08nHzSmGIgWKs>h2R>B)q^C<SI)*TRf2CC{QFV305BC+744hUb+d3rXwCCVu(dVp2(2?X3&CZi;goZpInAMIX!tlfZaw^0YK6#>``JDkDU$8wr@M-11!iX)-3foFT(ItClB%y3F)kt!O9`A5a&GLJ@L?8pJtj3Xs!<k{*Ze5a9%vNH<VE&fYm5j$b_38iEleQL7GF~EHO>4l#sL|+Qb&ndZzzBMjZYv=?!+br-rK=-zv!X3uwJp`V28m;#$cWQXH>i5y;T+<kH8k=M<m&Ahtv!Z$kW|{Q(RAKgvNLf|8xQM({)NwXPl9w`2_Qg-b8C_uI+AUwi3{*Wf54n=5@$S?0*IZrlo)fK920aOM#JK$S?@>i0l607SZl|#wprF_-E00|S<*kM^c~C;7C9e$`7-g$jse~9Z^*CkB9S<@Q6?xH#7$SC?&KUrzUkE91b>)m}`}FS1w6?s^#}2$2+A2GYw_7w(5Oao#=1Gj;%oUwUt!*|}OST-FnnNk)&!?cg%Ltpx>rFfdO9aR4G#Nflh2<fZ`HUc6ZQTM7pr`)&O3Ph}{!Jv}62&GhhetVl@l-s918Fb!uMTsK675`?T5I@`mF*l$P@=*TN-q$^fwuvv&`VWc$le>#d=H~oxmeSvX~DfQ9y#_4xEt>E^Z`iTiYc4?aCD8lh)zT-RB}Dv5G4gyOoZ6YjpUjW;+0o4#w&kWJNwAZ!K{%AG4+=a)M_YhoY)Vv^ppZ%^oK{7%gG4j(@)eV)B%@j_8>C<mTMVn4{tN-f*Q^O;j~HN*V4=)M8sk?4n0i8u411Bh&JlVbcXs?b+y)<C~)m43L&*QOKo`=Va{0)`K$PCNpAy3u2PB@m}?)g&q*h^NQ(B}C<0m2+d^;|k*W%1CmkhiCqsl~Ww7d*n#-{p?ykatC?d~-*%REiqZ-F)Ry{$azXZNPCl(O=xx73;W%z8WU6r80sE0tPJPb8j+yoL~nqA=zp_;anI-gvy(B?vvW+TQ}B~EN3NSb$iL7oKkQ`X#M!3ZZxnA4miLPqX*=)Le8(ad1_1}c!(d1y)rJ6pJ3xPd-jm^C(%B<4tvLN^HRZK5SB5{?+jqG?O``W>=?OSSW43^UQxy$VxU+862zgyg#6@Bu+Q%(>>Cp(N9)o{m^b&?bVTrH+FqF-78q&0~&S`-R<y*AtEY1eK17Qci_d_N^gkN*Axwnid_Rx}%UJ{@^Qrnf;<~A@W%8k?I?m#z{f-u&Up^`sZ}R&NW^^ai!?Qz3E)WorekLRlQ5rkP-uX3Z?Li+7Uo(ft5iU`Xrn!^dzWX@O_ug>5h>Rc)xEE9^}b(VfPU%U)o}YRg<A8AC&FnJ|-FmiovCd5QzC$zSu5b0xRWp1>IExZeesr7r8njaga2S5ays7SD+jMpjDB&GeztSQv$oW`$O7p6ou9poriXr-^LS&ID_o}=qpu4#=yphhVhs6r&6%iYoi(~S(R&p=#k9^wZSFvLC+xOjeeBi7bn{&pv$?UrO-M+Ln;GQGcH&kUb=74Z-&q45Hi=HQeh;)sjKuSDJ)8=hsMR5y_Dm-zjhttlypF|&E1!z=(+B+h!Im_Jh{)P;LM;%B%Tw@LUwQwXh5m1LvcaNMF?iI;O5Ap9SKn%SyZ*u*FtW1N;qT=u|ryh69|OGd^Qg`bOI{A4LbAv;w1sI7z~~otP^33=lH~>tGx%nB*Llp-g6K$_p_sZEaEq8i3~wkKX^1~^z+BgNdX!qedC}O!Y~oz6pi-TA#rBywsucT#T=+&R{YbIm<DD@<txS*@sN)8j9|wOY-%zBp_WwXlCZ?a<;zK2s#L2Q+v}<qL6e&Bv~RQRBG37Stff5bad~l-$|&wo%(vAt_O*%%1RmwG!RQ_`sGcEclIIxaY!yUlWJ0o11a$JS+1%gILLq}F(PTp{>~nPGptigmLAxYgwEXBcuXOX?CasR(yh19kkq?@*>zjS@?l@=kbty5AB1@<cnW!J}8Rcq%U^M_Azl%RvN7ZWESe2Re#Su0N!SEOn^=ZJBBEPX&&~`wyPUdg{Z82YzM<HH?AGFC@#aRgEi5fwXo>k2$31omAFaviXe2Pxq>SzU-qtCozaK#AFMXgP#gEQc+CHj^`0M)nDl~xNv%IPS3YdM5fx`&EYDO9cq&^TWnnpCoCd20$0*Hl>rO9YhVZYx~6+Tp^-1+A!l1yt4#?4zBoPIc7kCP-XjY?bR-;;OZd-OF%3P%ybG3503M%=;(Ge#s+T*04s^7;5FZ8K0HHkWqxX1lg{5qv**dz-JRq*Vp6lT+S^^!S7&l4>Wzf`&v~(Ik#)jG12voS70b%8z&=j#ZaL@GqMipt}z%~)<sEfnq=lda>7+YW*a_fbSJAe&4m+F%z;}bc#VdSbBrQ~DsmwPocDCjJO4I%NG)UlE4%`l0pnnKjUsdd7ef#5(XW$jtJU=xhwI#A!cbLm*hIK17&xM2xFEkZrnrQV+56QntY1HPMo9~S@uY~EUEDV9T24o31k(nu;F+-)WrWRaDy4I>DN*fV;v@K|*=i&wcN0=!oqxUx98h&CnAv|){*8D~1aue~GL6ExA0p!*_8B^PdN#4KxE0N4qxGtQ!wdnDHVUuM$>9R9{-w{sP2S+|3(-h-JaF{F=rsq~MH|Z+A%EBGO47VpLb}b2wiJ1$9L|nN@#3yo1qrdjsag)FB{fkE8=7Sh<}!pAwWro6|CA!LnAs(w0>cLu{LfXXkgH@jHVRlCin3ZHf_ZY$qz)RlsEI~kBq#2qMt>G-N`Z2j(U51OkCn{xvkp%RmdM+TWVYt8iHk}+xu8#}$aOR>bs}});?DSM9qkD<K_i!Zs{Zz*0iw7x9}f(>3zOX<!6cpKJ4pzON9c;VwQ6IJ8nvGVl9V<$<u#+5CJ13UbF5r1p`!pSW{VGq@}6wCrO7gi>CrYFsNpkbgU)l|B5CJW6^$daOj5w6yow8fn+y-B@z@k50Fv{osv?~ljj8lVzc}<NKGG@#vT-p_hUTaZ!AV7xqHk6Xzb!Z#%9@e>Z}wu#^PZ;+Us6IuX{F)bRZ4!mnH(IU5+kfsTFD2UK-^sbWN#fhqIj5B5oOQ}OHnS<4_p;4k|$Q<_+L_KSO;9cTq_oiyup4us|k`v&LsshV$wb#F3fVD;h75M8nLPajyfi6L_wK?r)bK;_`zo@r4EQy9i!GcBOt)KiY%qjZrB=vyrV{FnUgIc#su%{*iEG6I_1H|q%wrn)^<)3q^4L_Wj;A*#YBjqToh(0YZbIo*GF5>BOJdh-!ck|h2L0I8`bzM*g~}1$EmZn7g-140=?oqimd%qDOoGA*ru<ch8;^ZgSvke92u-valuMHDOKD~+#@`y(f0iWmeGAgsF+jiRb^5cmVwRZ^AuO*^sIO|l5>?-TM`vf7E#cemEbI@B266D$C-L?Zw0Lg^5gWq7v-{mUmZVAL<Q~z0Q&O89P4fXZ}Y`_X9I5lrP_2tbGjmsa<9`30ZyT=1bZ_%g4|sGB;sJ=v~<F8ohgdbe&p*e^m%e_&l9t8YE&@s=-dSmIZ8!eGoMlf#evoM+42hbrpobFu+rJe%dN9C5lhr}m-$F!&8kot9ib|Gc<B%_za!F_EIlp_Jy_ad*p*wU$Z1J;fZnBwo*bQ;&Im?ePK#i57|_w~jiE^IkUHp&RAQUZNn<cm=%|ds&lBiyoXsIbo5n2?MD0Ra$$X2AylO4hS)y6?=d<8q+X%J|8RW{7s0hw!+Aii5(4g)6COHK+y{KUns@tEsNmhF#xFc1eD`^`JRg4Tt6euLVNwkw5nk4B&h|yZFx9};!jHO}$cJtyzD<Sz~qBt`527^5yC=^GLmQihCK`0-)e_Y<7Gw~X#`v4hJ*0g#sBYd+%kzyH5>b-oPxSY0jM5SsF9k#t^G_YX=4rbm_o~~i2)N(8ScC{>erXr5(@x{S4WJ?Cskd;dSiafUwbaLbRV;hRIE>3u;ICV4nVjIMaieTEqzvV}>YeAF_;jyY~>=n3C94~32&SylSL(Sdyry^4&N44^IwsR?LvR_R$V{dA8Pe%vKs)8rE#3Dxx9>rF2_Z#DYyrZtdrmQfnXfrj|x93do={gIpCzaaO2J%s~jL-2=PfWI5M1WU(+ksBvrweeNT?F1Pd(?;kW(3dO<D-~FK)BIKbZHC`ucvrAB0gypb%)o#g^`M=C-rN;1iY>;bd&AtjNGDiK<e4A9WE$3Jj>Y{LgN=mz5^Ysc#?uv=ttE~7o_yuT<I9d9K#3}s+~QmR?`QWV&YM|%OeNIBF7?7I##r3QlqQ<X&r{-8^vG&@-cSOAXrQk%pp@qAR=~w`8ZmON<{nwngj)w3Qrf#gD@r>ZQ+&z(bLV?t4XYO+cy}!<=j>-GT{AO(fMFjeTkgZoz22!8&deSanS_1D(%Zw;-ZO+O{G)YSr{2J(7<yeBqwGD813q0Pb3JG;<So)909zcm~}ZpKph_FHzb?6FfGBGBY;r`b2S34(JIWENR4YVRkNs814_A~m>lI*&@dwVgW>QQBH9iVq8P!k5yGJnM@T@ekq0}SIc8GEH*x}vk!|;L?D`_lPZYICbyPJ)rJ<Bzy9V8=1{~VV`!!OnqG__c;`lhg1{#(k88zX?r47W*v#WA<lMs33ar6a{M2DR0M2QIk--^@*EQPet7s0T`!ckl_BAOU4c1}l$CUK$H)-T=&O=wm;^U7`6&C92$nSW)^p+bQ$-AyGkMPw63m12>Pb~J_gsPyijs79N>1ajP>=^(RBfz=g$o9gzp$aE7MzX1ojD<w4;k#D7#*!CaciOZ&gbf2?nZ#b?TloLpgxNyQE>I#+{qBG*+2zK$(?|4I9qqO1rH}8|EpyTcxB$Co5ieyPrHd3ccM$0$B7NI$Dm(INq9}~c9a@&&YH7kTSj{NI$=`>#pR~>I>xB~y3_CCy?=x+Mn!iknC^i&`xnO;clV2J$YNi%3{lU1sLPx%v+U%?bBx28jMQ<F6cV^4W7mMWPQ)<KY7OC9sUO{I%z9Hta3wFHz&RBjNRI_g$XGPl!VA<ImRDr}qbE~h;w3&bQvCPnc@+HG7_#=noQ26m!o$I&uU2!Mg{nT8?3j{KgrW-;HFwv@_Mzn=O;vh-}D)LRdAqFBPixi~BEZWxLLI)v)0W46HAvkZk3o%!l$;;WH|C~vBUJ><2|3{eSsE7nDf-#LyP*ig&m1c5SXqcC$M5t-73dgH6FMRL?Fhud};7x{%gQeh${ZGSEig8aaYx=INasG#a-!YECucy`8DSBAa|@_Y&U5G+w|^z9>3UGOQWuRg3}%|mywXm(|*v&d@dbD5~(u1R$31j3sbD>xovH+%a0)2|cwb@!JqadE*&m#y3<Fi5!25bdjYK-c3*v4p7kIGW^rp>k4wKCj<Y-K28t$l^+&PfRIyM2FPn@DVGlJKC^QYq_OSR#Z&W51BoJ#ABz%6oiB-6+2P}j8u#D3!?Nw0)bS>M>LbTmN=eSMKDlK5$dGqghqc3v8Azh{kP-97fE@fTw)gxS1w=($pcPtf`%3?@odg$J8ckmk~p`!2gc}YuyuvJMUCjLMAPDML=#t7L9q5Ed^L}!?=xZMo#Ir4LrAgUS7YEW0wR~XP(4X05mYOVMaimOj<P09#>l8|RYvP>(trm<W>N(JmG%LTi0Evjb0Jw&sMBS(zQ`8PSh5?Y%@-0$G6g$Pi7Z`1IHqk?)*&RiDJphU$w|1xww66<*1kv&t9>HCILxM!GcXFCoS?i$^l!{=QkDWk1z!!<JWnjHMnuxqEam_gsGmS9u{}}a6jDhg!k%Vkc%)Km<*j<i1Uw;a5g{~_-)}Oz9<NNa&}_|u+NvZphIEd%^4*`lcW4tqa#v?zawieekSq~EYqGh+IRM(z!-_r-(Vidvbs&gY$qt(IKF6c4aKJ23e5FAGzgfBk0ff#a&^C@e;zVB!F^%qx3*2fZZ!k-HdK8+;$4Z&*LFKeVH>;encP|wEsCqO}h#9RxoFx@yzjl1KB*2|3BXq4|EU4rZ9Lek_QYYH@R383Q4CG|YFX#J*A9#B^3(bYpnmWJdILK%x4`d{NvER?Ps=4j^7WP8OXY0zPqWP}>r;LH7NYe2HB0_#uM`E!1sD6eeQNxwsy7H2lfS1yZT4Vrb=~8YQ9G5$#&5|utMk-6*5v^UPiW9W`tQ$}C<+kd=QWQI?d#$_H#xPh)vs7rGsj9FRHoIq;&Rq_P?ANyD2BHCE4oEaBzD6Orc*t*RpR94Lf$|4Tf@sgmF`tSk2?}6@jt@E3>v;Hp4V-8GcpyqnVNOZ(guv%>!OVNSFlA}k+Vu9|oQ+v|vc4<^c?xEAhieczb@!Lge&J@Zpa00^s#j7*-x`<i<Z8;}PJF}~%u=v@aC*qnNdg$|xPlUETspc^A}O6#;kT>8o@z<qGP)-HVk7d6P>+u<?rmWLUdvey$EWDC;Ivta;$D^+7ehs@BUL((Jp;Q`R7k?_<|j!(>aLG08`_mYUW0>XYv-E{z%vdL$qYQ-wosR2u%J}rEhuXvf@jGI(j3M5oElv-_=M6tZ7u%%RF4;hB~+*%czI=y`dKdP7V6RgBQ!5$ik_8OL9j0xA8373SHCF^p9q1Kg7s^26t|wk-ZZtK0r)AHtW#5zr=@%{)lb{ysV&y4#hvT!0`sHCEz8iFttzE-KD~X&WFP)fwz(3uZ_Yh=u`pNK(&Zk;Vf_PkSl{?G(rmDi)z-7XO~m~xzh=Vzpvc>=r0xo6vV4@qiN!txW(g>#qe&dPDmjBT)o?3)WqY?simDZL{fBjKoP~EWldhWHnKKJw_c_1*aeH!oasR%{-^NNefB5<EiKMnn98%ZeM9U;C@J4WZj0k2JVy0BJ0t!=zh>1KOh}XWwj~qU;(?J!+B1<k_+*hQSL!Cp`7etJ|7}XMgIvtP*vGU@qNP(zv>R6NE-Zu0sJ}Xvu8@wTlR&z2EIa<!KDWKxaVSG;}rF@Ja9MI5a(G3|Bf1{+dnb8`z)8iL4&oLZv0#G4T&;HB}4H-gt1Zr)3qE2{Ita+b6$1o3o7TiM`D5?EfHZG%{r5akP^9pm21>;=P+&~?UHPK@OBx18XjMuRQK_60#vj`YVQ%OQ#<O`rllo&?5@A!o4>Onvyl{)Y*+)^QM-Zix_&uk_iR;V<(6TM~7HR2&fq>2=t!}T3q;Vc;&QC3GcjZPqJ3+jTUcS$lYKU0$~@8>P8uD>An=3=sfV%2Z^tGkjSLX;<9_V$QhFJA&s+BLLvYu2fN8Ef?;kfRI^6<Tf8u}vK1FOf^|aQdH5e%hYmK;j-cxgJ*3?fMN?)+jrBNKHHqr%~oQ9qS^;AhF!d+g$}w%N8$dv^2+&1G)b*joe}s^sKkZ`B8^!N<I@K<*Z7EZaeQ*!yMhr_2u*l-nwuR+;2DRxj)K~nILd~xstUmx)x2Sx9+uy!aTN*CS|wR^)y;3tg*IvvM@o)PgrCnVxLv8(Ar`=Nk1K8r4oj~rGrgarHn;Sm~DiOgrQ=T7-?>vXo=&{=n5-W+R$>v4XPw})-G5xmRZ8K<qD=~V#h`VE}6DMIV}(!vsmNtB%}K9kI>=ObOE@UV%p+3npm+3Tx1QJq@anMGSmuWq%PfBl$M@afHrU-o6fM9#4_#ZqFNXC>Upe(oPFYWSkNwV%^L=DUT2YDvpBhLQ7%aDOsce33cN!fs1Wm6Ry~>w?_R47*2U$RUV&O+=?fSTJ=Lcx#_scrE-akSiW%ity-SpFkfm|nYwREi{^S#5r%|x`@^xu?j*uw#>7VLUXreG)Vw`|y9HrB^fk*01PYhH;Dg^+F;|HBLT&RHV5jf+l4k~=PVjjhBay4Y&qR^~zmL$*twG=trt5um?@Qw<|Ok`lwYJT~LI~q`^3c(SHf2@*X0=Y+~8$>%isqfz2zM1|}G;9^aCEQdCbQ_2>8KV%?3<e-^K@-R}nQ-eDMkprHSZ0BrsPoCwR$p;3I8-CsvsPIrSOQ9cB2C!k8D~HCc+2yF7_Pelis{=Fp->8<xYRI+Y0M9+DAQoua_9NgXqL$xevzautzxsAgghsD8+`zR=RO^6Te)4!Ig$5|&MBI!ZkiT-f+k?-)ns^bf^LR*pKIK7jO3*foTzQeojnyCCyxOYUrnXd>9kU4eyP3m`qAXz4w;44J5S(BzmgU*U|KU8GwzGO{6EQS=h^")).decode())
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
