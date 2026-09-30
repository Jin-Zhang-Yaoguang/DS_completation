"""Standalone event-option resource-Petri Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v92-event-option-resource-petri-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_GRAPH = json.loads(zlib.decompress(base64.b85decode("c-rlKU9V-gapiyM=lifp?vHckO|fobA&O*3@-#9=!!TwXOfYafurp6V{`<80?vEm?YH=0Mkt{iWkuFYm-$Sm=O%|(at@R)8{^d`<`@`@5{O-T~=0D#3%kTd5hu{C{<B#ut_1U-IzWea<?tlO8-~QM4fA;amKm6`b|L6Dr{_*GEy!*Rf|MPEu_089x|N0l-y?c50{+F+xef<CY;pI2)e)+{WukWfKzW=-5zP^6`@h|?<>z7}D_3mYBKHmTRa(w*RS6}?oXJ3B&gKvNN`uZ#Qi`5{u4<ASRfB*RBfBpA={o}uVKk(noAOHP_|9q(?_r)*%@z=kqzTlkbZ{EFs{r0<0U+~q}-+cGWPe1Kw96v}ftgn0d&GPBL^QSp2pZ<%6aRE3y4ELGX<CFh&$M<)?{^HBefBW&fzWenj$i?8UF+BiM*#}V|NMC;Ti`Vl}RfG8WM_+w+E~|$JQ$7tKqrv?B_Y1auN}qlA`pw%HsnMKc*oVarBB4S2;xqqgT*FaMXzbfd`|Zc?{o$TN7K51gXTq;c>VdqyTX--<3}!-u0W0);hsCHui^3j6(Sy({^O*kIPH@dS`cS?fLN<nw`s-3Zi)%2~68ZM)UvogbjiTUD80&NYf(IW%{q4nm3}9jE<#>%N^g!~b!4x%^6j_+y$()0s9*i7KLZdPE&PU%4@4It<Y3gYkPlE;^F#sH2U_ORte0xR^>|ook#qh>(e033DU5JT4>18PUAm(!+xPy4~$RM7^TRd}&W=5kKJTv;|mOqAh<j8paEWR?{hA^oiWFxq1ZW(gY`#U@Q)ur>*AowN%>&3pqB<A|j0$+cfzUWw2smS-WQ%${l1|2cB*PMPta4zophyGX9Hx?ZffBof`ufO>2w}1co&39jX`NjYEw1}QG%TnD|W+LJkpJuKi@zQ^1t(zDf)5x9E*rlHJ{H~MY2%>WI`8_nvX&*t}N5EfcL{#Jj49wTRozm&k*Qdy(QUwV8XrTT!CKRgo*K^m8epQJ+Q~kw5lO!V!^<{5JM89k92Uf;c8A!y|jq%0QB>RuDFyCdw3hJvq|K{soamVxZRmOI@haB*$to+xvuU~$jGZYYi`Ud0BEFXpj)*hq9%fZyqG!aZ>Crj5E&>P@*+iEj0{S#>V^mP-9!W_I;b{|@49@@9xee>D-zkB`Wn}7Dgoomb!4b&M?H$k?3TF)B>hK^a~&z}9Wzlsm4y(o7eeEva0STc5QNAP$&>xW(sMzBl#ptj->9rpz{HyP<JR8Te?1M0v!j|E}-PfW6~RJrVdz&ena#NRdYaM^jLCO!N^U5$wE^3xe&>y{@|^D#B&+}tLL9tTQ;4~6si+d5D8N~@_NQS`fG3C&=BKc9J<BL+>8K-;NxFfsPqcTV=T6vfz~hgsCOWvYmyPHHv<SbtR+xdzfHPx)Qx8TUY9g<9YIq`Sn>SK-?McZD&}Pe0g%<9Tk>7n=I~oZH*%HhGkvH6$bH-u~@lBuHkHlFx~e2ZFZxzspdN%uZ5vqs$K^nB!N0e0CO?xfe1LX6Knin?+$V%vSgk$S_}((HzP!2jdm}We?<-(KQF9n2UF^TY+%%9kGP=)r*jrI6|a>9*%zBvgp$ustrZI466A|H~3#h2fr!|j(zt;1;5tUg>gOdD}nNTTRLY~Yu>+j3I+B}Ntg|K^ZxS`2zt@P+|b~Kj-%>ou`@gnD4WY~tW0fuF^FA5kAV0pGIrhLr)ZEgdtW;ik2#tCp%MH*k!$(zBjWKFn)uVdHWU`0E#klU`u%W3e2!-SB_s9vheBiHPe<a%qZe}d5u)T}-^`b>C>eArv$uhK?qz{wV=$P!ZUR@@I1pnE#L1;f<&Je?uwink8YlCQ_6)C>BYEF#Jj1qe@8eGJ**E_^Jn6T{D)HT^M~mL~n?r^3`SotC@az%uT2|pu^t0Xv2g<8VpKKD>lyE40cH^C~2OZgVz8MD6Zb6&<S{G#<P(N7kk?Wd?sO2iYCTuP)JFf10CB+CBSx;r(hO<Z}#Ht{HmzVo8IyckYV%Tq<yl;m0`rtlwwC-jRM@^w*&`^(B5k(&NYxQNsIt8e2yINX~Z%ZLm&kZQhA3uq2)1C4AuQoTJ*texBCv0|bwlUx0hQP+f;#1f0{<(}9L9`stFPCRGVZ4yp(Qv<w&9aoAKc}1H<)M(d?evhX#3aElGN4ELLato2!x<RPf<Fdf+Z8P%Wiwt5<;))hQ8rO)LQbYq?9YeI>baIZ&}4J)4}w}TdJF0dXo_D;K$*h(jLz-X{o6-wIGz9PuRa+I7;%C7X|N=anxyr0_@!s}%jh88{R_b)xIc-(W}EZ!V)5;$h}#-oyAY;$V0uOu=MPR!S^q@~^haip*}B6yg7a2tRU!r+eiHA07Pv;r6xIMVc9Ed2R6Ax8mywLB8phb#Z|(lX_U>o3&F8baOTPLPTIXv-HwG1TR_8Oa7^>*GkI>{QY5?2lIo51ms-UTeKuJz2_b*RpCFL5u@llAxAtTDt{Cr(ypHlcSKQY!sgp<JtmB{}VPY8i8qP%c?8RsH4Hr&v4FgSGc2{>ze3~u8(`ykw!Gt|DJd2poj4~R5d4SRTuWu!hf(oyz2GP9mUwi5u)ByIe-7yseHTz%CJO8ap4uUJwd3+xW6ezsrq>w1C<6Hn42s;h791-rzXjITR@zGPV+jg|?ofhJan!@l{wcQ1o+9FrJc!o$<=vvVcE`MwB{MU6C9Bc0efnI-h&x1WUqE7{0&h5zo@%(vyJD8B#t>yHQA>S5Pb*gC=0@!L>Hs7GFQ3ST$^KPI7KI=`P0ldj!UX=R%|>Y0}2qIS%b2+PfWj8>A!lqPX%!c?b{9=^PvyTh+nQ_5aVNYhnd-x|SIZ<bz~V2E~1Y2v3O@#@aYuA{1-^pdNWl^+q8;3QzEah{mqo=x4U-muT2AjI^;)x54ryd;T@?|r2z`|^rH{A(i&&*8{zPokN<M_K>$pqJik^dst$cE0@VtIywkz$b7KOQ%r7wJ$1gj{>WT5%sv<S~=bsk5})bUMA*g<C02imsBLL_yq>&pU7y4i-`ASfVJ-Q=C_|+anrXRBRIfVaz5~Je_E@U)-jbgt-0@CzKyvP!t-db@#bxCTXb-~7GMh&wY?2DC?CTwvEjqs2xG`2+J4s1vRKW|(CU45{&8{_*^UzPh%lNXz-(k?WR(7@&TsYiAE0@LQyqFcHsWzT`Ulu~%crGrr8ib@Xs{}O9=p~pvfZBht5-(V+o!?heQ+hLb}e2o>-2?Z$J?~<c#EhfTzgs;Z{h4qNUF2LxTjc<I=fz96-$rzCNAxpmq0?qLhnZ6aMg5XBr34ARGJxYb13~e=(9t=NLGzG^m2J)OL%PKFP8%|yK*n$>NV20m75+=@4oKX_UNpMFl#r9<k#DXbAQClyXIuc{N&xxvh{{v(D2c#XPgOLvM5piU8?+;9BKYEQs?qawZ5S~=17NcJ;v`5yo>gTV~izmz@pr8r0HN0nX9*rK#y#pwg9~Tpj?|O;|v73t6&RfF_E{fliMlf9@rsX+x8PAdUs8*zniV1?da{|dlwxt?pWQuL66JmL$Y|aD#qxKIvJy$(5MGaWAhs1%yE3gcW=bt?1h~*<3WNo&};F!14XSr-9y*dIIIL3skA1SblFFJH48>&0P9i){=GYpsrO><9>p2{$nF8}^xclezQXBR$v|8qPWy;cbPq9fD!U8Ey{(kM*xwe&m0NMg4*2`lvLBF*9UNGlj>r+7#XL@`0AlUi1MFp^sRAU07cMce(Ea5>A*O!P!emS9$jZ34=>F4ZwP>tjq#flUvUX?%ujJqBH*zeBQL>2%bmWY{9tpDsMhFu^eXUsJSF(drLUOmsz~!sg%@9gK*Rv_kY*L&--XSh<*wdLtYZ^tAT;Mb)y0VVi9|Qbqc-}-GZaV3UW^0RnY0uRxi^xX)Y)q?34|WxUox+2qSFZCnoj#*J>YFi<+)Si+tuT~}AZ{K}mkg6lgJy6OGf2@HxZ94d6dM^gbjN;A5B$oV99fIpAGp!W)n?VK911)D`uAu#<h&0#nM2M@Q`Zyrc70Ll-%@+CC}<XdHDg^&5$7U!XSIesHN&3yVH;r=Q`09>T-#oa$-=s85=;I1gc_(pMl$YtkUd4^4A*_wNobc(%|upD1yBhNS#Rc**YX=uLX`WZ8uBcLeARJQ?-;_}OwJ3Z`{P>bP>|<@r!ZGjC?QA4kzP2Pt@H4cn8lwOX=kJWs9#Q9_HU_1LoEyCT<ZS#bKEA&r4xZE^(nD(Sc|aAoN*x-0c~(WtmXhx!H{fv%gxA_%8wQj3M^|YIAEUh)hA8XBh+J_nRdMt$=lqXE{5SXCzi*J_l)in$5`9?i{^)P;%32)D+6sOu>7o3QRkWFW^t^ZAv{+5XIB@`7_pIV>SS)r565~4=gPoTHquzad*+n%)@58_jmrwm>acEbOBGKPHS*f*z5g(H-pTpc_<zDMKiWyjRKue3RjZy<^y;f`U`E6j(uR<YvTbk6)vtQxcQ%7M*S-B(%U#~kt>%*m11E_aO*@6vn8F;m2lLsJ^PhbF#Xp$WWPTD^G;5Tm!M5zxW+E(c25LQye!%+#4G%fVL`|}U41<UYSL)Evs1=v1dB|RnS<NHc^Ds2U^g*YE6^!g?KtL{wo4z&f(v17gTryzKf_%%3tWl^kkgGh!)p8+6FLleQ(aQnSVk_M=Qski|YFfE!G3YO*o=gntKQhjL;_f=B#dUY)k-T{TqKJ_m15Bw<`a=#pi-DJ_$^Fs^yfYnNXiP?~!?>TbD`yehrhC=+CpAE)y(r#q<bZ^7^VA;kfX^Z+HXCD~g(8_VcCM~OpV~Z`OI?<9V@lqc8tKfY-qiHw&h%Kmx~EY>h($3Zl{XGv8Jgk}UVXiEo1{B6>{hd(fu3N>^bBQB`-*3%HwKt0GU%=4;faM5jE?G^J?CxzZ}h1~@?*(~y7?J<DVh0$eT7>^o3EVhTD2w9PuL?=RT(la$M%3hbbZZkr?xOt<CSP1?1ZwDZDcc1SZ>D8ju~8yz8DR!33a2Sc3Q=;e|r7$>#uzJIonAEtb|EIIwFTbczgx{Ck93?4~8HoS!lD!{w*T;baZ7b1G)0lZ=`3GgV>*VA*7b&riFdy{X$N(;em9CHDf4T+P#i*8nR0Ez)PN9&v{eI!L`CsI-~!kNmh=wB!C+WY`uAL?x~NZk>}>2Yl)(xp+O>%AMpv-2@PX!Ffr*B<{25R7$`TT<)}fqiBGNrm+wXB#pjmhBhPj-uAbDHwVyca2d`=>L29KWj}8Y3QWmWmM}e5Q3aFcz@n}zkfQPmtgoe`O8Viy{UKB+43Zl7b0+|JEWDyPQ+XKQ|sJ&A4ywl{E2h_1vv9I364r0NP&s4x%!I2_Tct-Z#<LVO-U|H@*`f5FRauuMIs_UbM=i-e7w_>^^W;}Omd0a2zE8eM5ZnVDz6_HI`_PJ+K;E`dR<VS1780QotQ)jM*YvpMe;MRkBoTPHl%Lp=CWr{N!9XMA3W~x|I!?jmkpXk?(Ui+6Wupd2qIhH+3sZwsP<u2>2$h5zS3|2boA+-R|8uE9le$84=d{K*}R2+*o<Z&mikEdQ5QfIZam0Ncc0c!;T!@N)W0wAGUgiu!&dJJtR^NlejFrU7`{B14gP*=QF+=X!VOSiYG10{<~!y=;OY^cV4kH)eW97j(od@;~lkG01b=M^QQDdRvdPeF<~rY1dJL_{Qkly(P2l+va>lQ9Kqv({QT5kRM$^$(4*m8IJ0M9|dsoSFo?6gw$<8sn-~Cl{mico2<roXDPt7>PLA(Vr`{QgeV6k@S(Wj>oIHeEP&e3#e_tNLlaWW^abk1l!{-yJDSsS)~tsq@?}9Tp=|Jq~6xv3Xx)cudty*v%hzJ2=E$Xcd{O0n+h9q2eG0MV{ZKDFozmMl<xr{me@ZB^QqKW_b_Im;jRIhD?nB|Pt>Ojm!?xociu4O1iEk>YM02Ob^C~m76O5}L11~r`tZjoIHmh@Do%^bt+(PnP+d8Hhl)LhN>E(4`^WY2&DY=U|JE`wesS9(`oYqH^zsubZ=tFdJoZ4S(0hbzOTNi8h{+?@(5+3~OPW#4ReEX>ul>R@V>$&gxc=$8AHY3wIo1`kxBW_H3(5}IDjLLOd2z15<LhQhtcug?1tz;MVOLO^9AfN?rNZv*RM^hoX%pDJ{Wn*AUW>qSb&N&XA{*>SwKC!($QtVl7A1#q%L2FU%sw2weM^IFj<=EZk~HL<5DS)dA?Dp_7{GD`SP_7&=g)6{YM8GYaj9`eL`0VO3@BW&aH*ln!U5B*;TGf_xC^Fx1yer%PGZDKj3)J<wxEjb_m$Y+!;atZcDZT(F|(s>#+$h`l{_E8n@Egm1aFRCZFon+S;Fu#B4yRpE*8P+A{kg%<?}Xh+wr`OdHZ%H9`pjS>f|8slQ~EI%Uro^{ElkW?x!5zwpXh>)V4lqKrRar0dUqzzqb1Yp|}6(zs7)5OmJ>{5oSB5KUFHI+gT<}J2)vOn1&cPW>bzaOXDN+<-_%5J}R^BP)k!2d;>96Ailk+_Yn~3bgI&o5ujKwV(DI#O*J0C^~)e#jk=V!fR+xRMW}+dfKL5YnMT#55s>&C!3Tr^Gv5J`p8)7AR6Zr3cN<XDCPJR4)&^!=qY!^O=o`2Qn-33@yV&~XQ}WWnWW3_W_5LEMaN~}yla*fYgU%>T?gC1pFnK${+5}jsIz(r&#Z3q-)D{BkYnlgunCYfnS-_~8gl0RB(6xd_UX|uET9eSENBTm#Ok|^RMBD1=MhcbC7xLu1IkptmS*q)FI@|K5eSK`Ag~$dfGnHA8#L`_NYL-{v*$;dTfnZ=C=e2xFXcl4oC81f*+mQ!Nq1F)WW#}J#V8Y;)>>5yNI?CPYD_TTpaTaJ51FZznN+J5YB3fIr+kRaLDMAfcKLU{2Mwz38hCtc`NH+|U4oa<fF(P6g0nLT6-(FKr&)utfe|@eoSu0Eu!UU4?P`^2a0wvECfFY|UhN}rg!>|Y#whD$EG4%R@D~!HCQJiKp)2dI!$y*a8MNT!_FEi>=VR>Sa&y+XPZ$1iT5iCI$dLIR{Fjt)EE=^%>8FPsrk*30AEQZF`MW|3nTy>$%>9vTN((CXYDaDfs);=dK`5kZ*g+oy|%#8;3;u$=3#RNiOJL+R5R|t`Q37}GTR7%5dtWimkUhQtg3H$n)+9OX#TZBZHoam)IHVF;InTd$dz6iOOcD6Faw987l?y6?4aB79pgFY{Z*8Ya_xu&RJKOxEFW^W%D9J0VcdRS{Y_=(%;I`1!(_3Kem-$Q|Ql}zOkNEHHCH+csEzD883QuVF@9Tgla-%~G{=*y6+K2r;V;z95L)fA`Mxok3(+ssP+F^jIqNvK`rvynS{6Gq87k`iGrb1xgiyzA=+M7x<Q-55FRqGp}!S;w2$x#-u(v>8hszU3Z|X0239Q?taUN~`LcduF&Z`cYBrax1NfQ0(7ZtvSwWFHh$lfBc+=dv=J83_kF>!@`irr|;~WG4~=Ga*BA1;oM=OBCuIg0&LA+VqWg~1ENON0La!i4M4U%08sxCO6Xz3IyTz{Uv5u8NlGQGLgMcx^l;_euXGM?z=LI?2ITlXcZvZ8_96-=wU%aTK0mf}NggZ_W`so=@iUJ^Vvm#H31l&DDzdj=$f8fy^Doz_EK_BRPJ_iV-6v$U8v<z0w)c|k<ij>4>zzanT&6_l#*wapaGwKQNIG{5))6OBb})^;`0^i3qLDlC)tUIJ^bk4|M|oavb;Q>ZmG)+k8qFHog7!&d#pkL6G`Lvw8qqTbf`01l7{;VLH1|2aUY4I=UEn!9BiO_4>fk%~pT`U$$fW*L`8y!N@Aa$<_BDA_8`<-@Hm6{l>3<%*X85tkllsg?b<jMPhFBvbBbn@9Ln3rg2bgVnqr3>b)_^TQ^jO6$VLNABsz!?AaC~A5ITHARA8{*U9EmKDSSt<v<3hbXpXP#_BavE-ald4Bu@-}#v5HIcg+Z<`IJ`!Nm@90x0#(97LX<ugWfMe-+nEkaLN@JU?>zSQN2yC>=cf1iF9buPI3P?r2-+L|sSFZ4f3h<+B;(p_3_M0@$7m8=z-#3rfG~QLIRcq&@MR)Zs~8xr{?!_WP3SjgA>oxqs36>|^xyK+Z!v<0oaU`+%H1mS1u)GpsRQkN@wzU*Lll~;F)2LW-iPUw?LK@%?$6+7JhRigTNDh#u&JhH3Wf(+6|kp)>Qe@oFaX@n_oD9FUIi;)7MZp|76g(lK(p+X7U?-l`|9m{#7i~jMUcQ|(H@$f$#MujXWe?scM+#R-~QJ0TqjWuzKMp>mFjh&yL)2G;XPMchx-Bt$|~*%5|qpHU<-rNEt&Mp?125XFP;@+C*(><LC!o2%UwD1955gUR~#d~X)FM@M!^sba?=o0#0!6rp7Oa7E+QAc2A!R;!oJn}?pp;lpFB`haeD+kwt+M|OjT!O5|CXy?4?o_E)OjXfCz0pL^&WM5VCOIY^8v+Xc^DKT&?zdczoS-%d5t84Sq_%L0M)5O4S}UH?8v0(`;#KlmmT&hJ<GKeRw4IpP`Ij5&a{wJ|wpaYU*u>xc+z*06K^IB%;6)(iC$9H~b=x^(UDMg=lzWO;MWX<R4B&jCnPvNIFudczSVusfuB(##ilyGdFr)MnU2cqCu>$o)fVm7THE2)5?40s@Z(*7p-XbJ}WcNc?B`)&F%v7WqHkpT^p%vAeBXj%UqF1`@2}EKX*KzO}%X~G&X_86_81Tm|Q78ufqu&n9v7F8Jy1Nn}R%xcZtSLRBT!_va;048V%6w$!)qgq0fk|;Cap>Nqq^kP2#SaMFZq=3L%ZADtbF9OwhsF4s7ye`<!(<doffymh<|SMQ7}C>K*Y-f#(ml83$DEBZ&^dZs#5Xvblc}#==?nlibF$xLEw^>fV=A?li#HJ;HzoG!V%zE?TWV*rA4%`e*^sa+t|BI1XH3;)?E|eT1L-O-y~-&kb+toqgoc7Z;s*nh(`HaPA%QRte9L@&l3Lted4WEot?uCIh^Lz%$C{mLYHMii~0kZIl}5yh`2$NH<$D@MQx&DMvA#@MV6JG7l?fi!v=e91BTQcO(VAJ`r+f1DFDVNnKzjW<Rp>scQ2vlJ5Qnb^W6HMbro6kWZP1OH#Ph@7pBukhk&5ypelC#Yx=c&}B5)m`n~RYvr<W7ri<cD4RIyJD?c1p^L)D)M!z$foy_;A&-wkX>ce)D0QmDIf}yJ9tryRx(rgnfgO<@N~^nlWQD}-%u64vpsk^YC5!}LxPvi2&;N{3WLgYX1B30<`&or-?po3PrYc*{dyC=PjdetjjH!UHqh1NCA_NwNLa9(#1+O>ntseaV1+f|7Qa3<&fE8zPJUmb&A?{Gq&%)?w6`*WF0;$kZ8!pwrwr2|#l5^Ojz>r7ns_Hs(<<W47fE*y*8l$zWK?1z+^M|YU<firw?;_trMi+?mLaOC~HYcb}gz?2;QepvGnrhKpW%`Tg%FmUA)>TB@enL7@jyK3t2qeS0Qclr_t1~@VOY&BRTS<C*DGRaMAi94Ua~jC!hI<=RykoU8J*lciNmW_gkI_03i2`cn9Ce4c*=EN^Jd3mJV)HDO%Ec1Xrb31HUP=ykwvaSupSPNOWmY-)O>|+k44*|fUoLS@2d{1uy(2mR^Ri~v!4&`OF}x4v$i*g-b*PnbZ!(1@pbdH;B}T1C|6KPVC=~=PjYt-sVhu2{l)IOZK`*Ocwlbmd4z2q0J{zZotti-%fGyk1BOt=XGHzg5&dv5bVpe5ga1*u4t+|)26$bec0WRtG)h6UYCI@0vuQTeEdU1OsUJUE1Hh{_<TxE{A#dQ+6Zk1ZfBLp7dF`?4-DMEGXl@n2-%zG{Uoy>zR@63<O>tGTszY?}vOh%?^SGEEzo%qqYXV`!+L=Y@+{<lUAOeR&0`2&LBNcs%_WS*1!7Ipv7Cr8OQ>0UuHH*N<35(v_8?1oF-0{UxTSLfJCUce_IkS=<u2hyzr(pb=G6f2Nr()AkE+jh88&ob;v#jUvs%GA9v2EU1#)}0{|io$VQsEF4@(LQ4)<?*Cb!y+4;G^Q0ADb&u3<zLIX{!&J3LH7>w_D=cd{pzr778k_=QJh#Zq7nYY!fc4GT~qd|%mawdHpcEJ;Ev}%g1LDFWq$-&>~2{ZqfH}3NGonCPAw54uj2>bHyKvgP|^-v4Q=T14qXxfRTgpRBxuGdo}<dn_W$`8|IqKw8{^UHHHL405}7O*Wobud66E?USaj);Bh#?$(eFJz`3%77gEP3kdUYAsO{s=%R?uD2j!SiEbU3P7bE{XQC+;?&m!zNUY8q?-dIi3neOoFF<Sc@g=`7CVvyvVXe6t#EOrnCWX2HU$6(DQouMNNk0Z4+&BmpQM0D2{9fd?S<heLfM$xa1hZ!^6KDxNjdBGNEP%(TQG^?wBq7qfa(`n9$~mgCHvV_QReJD@ZC<k%E`0;Vs<yF1FvB5IN`dzZzvcbSo7;j>L%qNIs%L1}^Kg~w_`QC^GcDmY1N#YSrFQfAjWC(PT@4b<l44>l}eEP34s4T$ZXvnZ#OE6MZ}dKS`<2<HUi-6L^~iohs2P9*cGMf*5ui%t-jf046X>Ql5<Q7F7sbI<17H)b0$Qej<bEst{m-x?!PGNdG%6+3(u<cs3y_)C$I@?=8SD^dBWAsa}++O_?g3sC6-v?<FL7ohiqE0=Lg#N8gOr8-?zoz#)Fk|lcv#$``NuA<6e!+0qCl&3rJ64yz8p%E0Q=3j{41@jrU%7+EsCi0ONc#{DhQ6jQrpJ08A&+Kzpp<HAn16D+Cr-xT!@zPs86=<_{f6yZ`SjWzb3rudp?BoKI2w=iNqcvAAp@seGt$bK``RM(NLGCyPWHm`6mjrT&I0i!7mtJ?)%JPtPGGA0_O@mPs7>iIWyi)YD2L@m{7$qi{ig%cE=BGp5SJ?p|y8v7!FpCGkb7D#BC3_9fB$z146D2xQSMmaJKZEPz^{@dkY7S;kkuJ09B0}$!_Lw~sZ!%LYin*e?cz~3~^{woH9Lm1KJ1tFj3ixK>TyQrVsu4N3FcOj6Xamfmj&P^?e0p<7)<L*k&&{62rhPM}odhc`HA(Lq;}qqm_UpPFm;1ImdS2Oz+-m2#*apQc2!k?*{s!5$LpC*bTg!e&cN*y+Q|c@Y07H91$1-dwc6YrJvpM&*ntKrylxzE4ndO50qcjS>gI0%tL97*9*l`uqq)kAuh-Rim7$-{h=}Nf+P><iQC0xyc?q3Nn5HDX>RKD(Rdj80Z;`QIZO1B?iP=yOfK+u!){n6n7R_ptzIRv3{kl#sQi!#`Cv`{xu#67329!dQH&q`=!xE=$HtFX@6K%Ike6OwhGts-NsrkfD;x=~ClbR;t95CANMfzDCq(PXPt2r)?cxhGf&88=au1QevD>1zi_T}1J^i5f`R8RuEh6=wSkdDvH^dymDHpLmL!hvjO!uVG0dIn75IoV<R}Z9=WIp{=A;9B><gv~w;t(Z?kr$WPiz?B{6vl*h{&{bXr!`s)|bU%v{P)R8Nd=p6ac<L<gLN#v@WOl>aa9vfr$+VviCi+K#Hn*-Ies0f6@R+xb2Ej~Bt?ARnS95N5dd!tQuc!o_vZRtp!bgzHLD(SVD!`dU0jV0(}<7gxv4a{ah;WGBNviB<cQ@+o|?~Kot^~2TPE$N##VV;~sqG=l0wQ-)6;;nYrEd7SsE*?q5dKcy8z~e6P$R{3Kf03mAo{esp=q|;t5SJZ*WkxkXx9TmL#anbaCaglQ%>alFnCt!0_a@}b)*@9ZYu@w8;yE&}x0B0Lglg4v(n*4+Qdc>NtIudF3AV-GxkbH1I$jWNo5F3bm=q3f&{HJfI)t!7-W(_!D-WTS*Tn(Q6$RZ*WN)_<x~1xWclIKyn;P{7Sr?5H5Cb-x<-i-Y2b~w+$n1sm_?>sFv#TXY1LV?3jBJia<$@h`1|l3Kg3%2sjrq_`XqhddV0_HG&2Mj%f0tSOfzrij(l9^BH`OgpieFy7Z=&L{h;nfaM;6P5SO({+H<tg^XQv;r0f2uAkJrIE%EjKcquFi<;I^&vz5^_~p-S_fN$SacXubJa`EJP>cqQTfkA5VO4Kxx&Llz**PS)v$%zC+<r<LX&p;^k9srg;qUAWic#Odb5qzL^686NQ>5T9+te-6|qvT)^>>x)~JC95yl4w#)PWe+!Vh5a-NTCh((R^?+|ad2>5GctOziE9JL>JXvU3O)xivY=(1XQnO=yr6}xs5&I49%)-E4qk=6y0Eo01+N*KFM+IwY?E{w&d}Pjd(b*wL&3!T6*)^aF9}JhAd!AldH*}11a(L21MA$u0*Fo}!N!>mB)0|<$?lPofKrXwwPA`#o7p+z?q7b-DGHM72xD_s*c5@y+?2YcMO88^s^~gkFVV~h0rnW1UHz#JHJ1Tus(_jVP&sDfWSnEr^C9Hn)oWp4Wglwyx_cwkcCQdA6-l6r2tMV_{RMeJkS|j}P>K?B(C`!m&nyhzbm42-b3&sDR!yU^b(oAo1-2~`+AW=QP!yIdM9Cy9sSk^}8C$DhygZ0|Sde3uYiRR0Sj!1kGQdjC8e(~vsKd)+X?5t$pjgJ#y*Bq<%Mhnk;WSnCcoQe9i(HGiK@&-{CZ;Q9tmU8;8PAMPU<bIo=kPC4JPF)Xy^RvMVgpB0zwP%6iUl5fkFmBqMpLjTbZ{}QY`rv|o5X>37pjTNsjL_}(14bxKGsa*7VsjP`1$q|3@Ebzr8J<-1}HOY|7C909pVa(g4l)_aKu}gGL=-ZcdFTyc=F)9?jkjuse#k*d%=__T3~^UDjkL(XAh;fCLgH;k(vckNl4hqvg2)-E7c7dz$xibC<8{D0K?M3>n8d)<%@bTspeC(?&|$;@S?e>I_W{loxofh9f?1ryM(a2iT>b8Xyw;^GnqAigl+U4J4ct4h)zECj%U1tMF5j_t#Vm!y|PA=2sbw&wdn$*cYnB7_f}lTCKLW{Hq0v2##NMMl2r7Q{%=Y60M?k5F=I$$JLlM0$o<S$_X7!(#dr^qAaN3`B`LpIgl^<ky>*j_x9$-Vq%M2N@`{!OG!WDbK+@W)C#7<1?k^!lNpFotHBe<w<=fl7D1pMcN|DN@?@7dZ_x}pSGT)S|OF0{L1uIYeliV%wSz=;8jS3%ZT<Nn;BmQ5R>*&Zs$P|d!^{>W?dY;k_R0j!IgAEv?wN*Op5ms|g>Ix@crIUeCdx!2h4|%YGpO|K+UTJDIt98;HELVxHT9|D#No*AEx>s#CPwYga9-!nIxxn-mBQXEiBant+$0JBW0nnj*1u9^?=tf5y67@_Ec+d0-$s5GQF~veuIAezq+_16Nwx<jj6kMAdQ#o1os%^p+!IMl%F)}}CH|q;Kaj#`xS5)^O++YxS7&(^)pM!HD@tK5nq=Qem0immPGw#;cj|WJ9iysie5ka;g?ydb85PPM0!Mm>|hUnHnB%Q&MsE^eUIa*tfP~z}5-L0vDB}bf*EJmfm=yoRXlhB-!BBi&e?GI|hGh51f#+jh2DnN2xKH%cUt+7YC2`3p@;;;~ku;z5uMgNge(RuASj>hGGBfxAOU~*$TS3F>N`do(whimb@ZRkB=ABEXZH?u%^u%9$4386wq>sBBTsjGHCeLv`^CZU-{23?j3YiLSipOYV_)p1&ouuaUIe_d{7wi?W|^Z~kyH%beJj_~KYHw#)D8ao|6s@NO2!~t|m!{Mxty8C&RoAz6Ci|&1tVn<nJ0Q(^nmv@9pK{aeKRJw6?riE@Zpj#RWunS#)d`Bgn*eKo7bEGS)j1)sn*}IDxp=^n{pUIm5W-M_J=-#0EjuCwWJ?gQoPBQppQ&FyZWbS8DYpM!nlc-rw0UjUh@31(oef2&Nv5jzs5n`<a)KL{{J+S8eHnTLMpm}fDnnsCvy~xVXjHCQ}?_$_5=og}VuMM;$<9rcf+_Px&Un?2z%sO)#OX>W`B<C5t(w>zakkcT|g0bv__ExK<GcS+nSrjSOO7XpLKAQ7iS)s3d2odwb6}cazIGDRkWTy1@3}ME<d`S=m7%{clM`vA(a^Gy1`$$VOI~`yY`!FZ1kJaPlzSezA8gdnHA<&I`h@wa2Pmt!f@lPm$F9s%?s3$$i>XM+tUDQ#Mqf8dbmG|uJ{jZ=1pd?Nk#3>8Ir6S}Rk2bZ@7Ii!QZ6$jdOCYMmFkYIIvYiJxPeYRTB^Bt&?n?1^g*td`bCTjQIj{&1Ha8lc2S(-WWvVe6w=nZw1FLfP%IT(cIun>xQxpwWBQiCJWTA7Kse&%7Tz0k^T071!oG@*73_xv7DG7ik1E8ZaFuc?FjnmGH;?Za9W?*y29`FXN<ri-zyD{xOJr`Ct1}p4!Q=MI1MKFeP=KQ3Sb%9C&F1<<B(^<HB-$cE|g$L6-P{j?Wd^({}=MA$P%J1&F$qJaHfJrf627*JK>A@?eXJzL$(Tx}?8kuhj(9NhxZRe|b0D5)wyMXFKc%Uz=+iV6+<Dq;k<wCYJgwUIdN-<H%XDu^S`qr5n-PvTO*Y?D?&K(+k>%E<cHNDjsX=dMcUQ26??q|9v1^pv6v(M}az>>0%dQ1fanv2HBSpl-&2FZT1w2~_dn?!gKWIu^;8r4Cvq6DW67A8&lO&LS%nGI60Jj`;X2uWjR)Yw&!6_N;d<sN&+F$9eb;Zhu2%8tt=+HzMr+C+Nk@zvs9B#V20IrXjH8?2L+H=0mdBe)9D>_zN%SI9cW_2?1D|2=clfecBmoI;EEMXAh5l=&oSQsS9~v0qYG168!zYbWOUK|yHXWfTg%^cC5azM6DErh0q<k;O$kolf!xaGOv*J=%yC5gUhO5Z(RWAh?-b*zz9(4?NQ5&Y|l@#NRGh>JuR~`Q%O51!@=*v;NGM7p!IK*JzBTc;eY<fMZF85Uo<7)pGkJT1Ttna^4@(&$Hw=s!uyV<{IZ$5@=waz%dJy+H~Zuoq4R2C&;)1J2qh(huU!%AGkWvw+fmWZ2@MM-#SKd)(xeT>Lk5(soS2$Xg0m!ET-Aolq(I4>?l&X7NKe_+2~~l<AaLpb?0D<g+*<;N=oaf1zJpitfQw%FCl^g8!EB*Ft+Y-S;zot7`M|Uy}xN2fnDEH2Z}#1sV2GsCkoM3b4e9MlOT~@`mB_tn%=L8J1s7~&?}4+RPxtT7J*w^i@6DAoyF<7iIP=e9o8<T|IXG;%8Yaj!eAX4?^p<$yMRW@0nQaP`Mgl9WL2TJADMYO))*CK)rS%R+=9xD_goREO&!$IIKkJ<zmd|ld;~!m&;|68MuE+u^LcF)y0UN{yLm=z@BIoFv76zj$t9i{ZNoe9gWK0+z`79fEIo9KLU$8p9cx1~3ZQG8t8^yR2=p%l3-uyvkyud0AX6~C!n6n8dcO1X{<dG>9i0uE0FSoAGi8W-E6+G7Fd|Tmk9T6qnOK>%{fvfK3R%s9*0i39R14y34NHh0F_1G#y4qg_DbJy7G?&NHZa$1<Sf*QPEwHaOd>40H3+%Nqc{IQ_PkyiF<~xhQ>LyGq;*c}s77>T?TB|qFNto2uaO}62;MMj(8Niq8R_v(UORB)G=S##)ZNz9%a~02ACA(k0{Q4_<Lr%(IqD?#;S0E`goWw42DJ)VJZ&rIt$Ndc1al-2(AZoL%ABIfL?7(<4VBACjVHL^{mtJ!XV`0TdxXhoC%tjX@ygkHrTC9Y(I<%LY>Oh}`)?M1~1KZg*oA;dg(g@4OE|@UrXS4s{Onbx&Oup{(1Nwm$z852RsqA(yeAABaD)61h1eIcWHT#e|z1MuQZZFH^s%dghg%uC8;Lax8GHY`1PuGTDxKM4qsKRRWB_WH<_bt8N*dxwg@V304YSGF7x;lU!VeBdZ-2}ze$&u@hI?d>k=abRasoj73Z0FA6Bq}bU8$;a4(k66nB07@|LG^=>_uxsa_>3L|TG{7LYHZmW{f-=)mG1J_w0D_BIOM&7Y!&{&lW6XQIQ-2vk+DrokCk$Db5i=LP$oOVT(QbF0pf^QC}V_J*K(JKs<^ZfV!s@R6OmNjKW1>KtF~7S{BaWm&85`W%J+<tP*($Vh(n3EfwQ2R$_nJ{g_@W{$!iUwM&&sB7FIzXL+L8<Cj+HoD|tSRLCG@VD4!CZJ9&d(T$UND$PdqFO(^1L(@CqdJ}m(u#{ORGV{wIFNnmlPCQSkhPpXr)7c(BC+3;ZA)}Z9~(7KR}tyyVqu4hGFVvz(EhUO+>M_NR6RuhB`J%hDo3yGoxZY2^$^i|%3C}MuXcA*PX{A4LYDNp0On~cz-Q7A(wQe?9r{9&mW&9BFyQ;FF(Y*-3}<yKuw99S^B5elfO4F#?k%DZrgX{HH{N3sQBagUc1kPo4iZp4gX%#fw_jTVVbA(0>w*+YV7A{qf2&sjui6U5H=^j1AiN0iXa0-8J0izDfXMiAc#(CsbN0K}{46P2Z?*<co_`OEus6F3zQCqzkf$Z_tb)5-eweJY968fzSwJJ6(4Y;R_lP>MJR8k<m$B~2wP4UC6b4?gEhqIR+7Bx;L?8mRS%NS2@zqE`>KM#HLE)E%$|BJV(C1q63w;|ndnd&2;qqa0x<Hf8qLLQyL5&ii>azCTS}-*^7C$|M%0?X|D!i8?2<p%eS!G+ez5yn1h0gxWe#N{DBXsFH4Qhge2{o~0KXwcQvg{s$fKn3f<9*|GkX8u3*a4@!sYt3Ply?B2@WR21SBTCXc26`JvQT@`5yi?%qz+dmqy$6h;R{Z;7u=E{=sC|J*xgx%FZV4$bht1dQSGeWo)uR@-xPF=sALn>1Je<3?E<%=yrJ7j_}up0vQZ?1xUS3&<zX0mA0wZ|J#w^`vQOgTAOG)dh$_cPTiMfw1UYJn;Q&jO(qD=j~UPa*1i#QuC_Cpjn3dDY&eFmkCXkr^>bM=icO4rc04bg&rED!m6y@`@<5Nomq$4>QV-=1|y|;{vx-YR!ydlsg#ZM=b<HN#iF8PmYU}N;t9sM~XWK!n%ErE($e|oMv=OAv@+4nD-Lf(v(zc6e2!>CKtsKd}3Ti*d5j0NY<ckWEM%7Ec&=sj0g4w)RLNgZ6jcY>%9_;AIogCAwCbI36<UkQxjdX+<S@`>{D;XP5vYhNn}1dKs?9Z&p&z5{?TQ)#B@Z{es_`xq%$G@sCl0eo*I8<<SH@mm)|`~(63Lzkrf<n$r0?Ppx)^0sgA1}rT5Y2?it%hA&Mwl1=6LOcXTmNXU^NLMe?qFR)V@$VS?A5_V=-xmRS|rj=8Vq+}-LU9jEH|q?hP6bOUi@Hi*IOU~sifuN4M)+=S22)a7N&jbtGx4fU+$>}_TG5K}^(L?6^F5L+t5%9CCBP=TJzt#U*lPXYB=pIg+6i8k=d#v{0hSabLh1g-lJZNl2<7){iu5ntLNSQG@3xjyZC-4iVMD19X}@2u<H{r8mh)|+-1*7L4Z!*H3-Zrn<Mu6l@FW7LWm*4Tr@Jby<^8)3mGK}=%z*C5XOc~FMT_bBs0jhk=YNII+|ELwNCyD--~Xhe&N#j@}8WmHeFmv=B&D=I~=(X#$MV905EIJw|%grDABY{p0DuZ`GxTFCKEdZ1=&9D1PKb@l9U<t|30#Wx*Hjk(}mR9myK8>~SpXR!6x&BuC%dma{r%p*#Yo)zAke8If~lCf4c+I8_~;fnV@+FFkkdvu00N9#_jsyh|+`EuIky;uvDtU-0m^PrkZ$2`T`;2y5h*^IEdDpdrPc2yO-NQDZy>N!r<X1+tS#-f!>^#a;~(G)DwXz9-)6a}R?d~s=YFc<B3@AWuQ7CgN!OU0`17qz;0*;aE!X?#knxkLQj;n|Iu4-myJHUC}`iYpC1!JbdjBd&-+W0p_bzTu)^w+)_OPaO$Noa$5^^4;)?0Wnh`I(j#{4$$@Ovp6Q^bkPFB-k7~MdUK!KK8$<)C4rulSnZ&PgAb~w0g=m92R)^RiT1Y5JxP(>pM_Bt7}d^^qj_Upp;Ye<QJ_Wa6)4ck5YYQRf0GN+gg`R)|DfR?PrW9a9nkvgl6_{#pR^!Ljm6!1`f3fy%po(tASVvp6ac(&CXg4x&F*WP0lbrdH$~y)=(@1l$$Csu{*)s=Gz@H;<48FPRj&J9XTD&YJlF=fy~ce)zi+)wjG*X6UGO9|Zx*sT7?)z>f=^1|7synh<Cb^^i=@AyVWU6^(IOy9g2^F0U_)GJg9#pJ-{~}Cu<*r0vP7E!7G(z5Lots~r)gOY80It9lcX?*T`VkGQq<^rNVILBMmLS2%agI=N*}0ZLau5yS(3^iok(*hi{QyERsTc_X|f?TYACqHEGnE&7z=VFe~w0a6Ir7cinW4*Qe^Mk6*{>`eV&-u)*N<&k=2iMS24}4f+d}>6akBL+1*YDKo%A##@js^j8Y`HHKDszQ_CDM&RGS^c&%`g+7OE<YhUEuM{q;Fe`iSz`X-_>UHiL8hNL1LS&p7B9=XVKP>__}7GPPSI{?0Jt%s(71F(748ruzK_2~j8tnlK#O0wk1h<1+BPm?0>UMYclr5bgCz6x7_?R4%nLH{`vM|D>52NbIWKd|cVrAMMmVRGGHh;*m#pGdMLrg7>0fDXrn7P6FO%~|~YXViSj<Ta4|v3?zCDD>DmvH_h5EllZPSQ=-;F-=fRtI<m+tlc-@bW`Jj#4lyBsfY?mc|aAE=j1`w8SDXvri5>o!vqb4BMZu|Z6*O=QUGSkXqKSX45+;IYQ|h1F@n&|EW%0lS`vy0mwjPiqXzvKc#f1W-xIej3#;N_B@?U?t0J(v*;wiA$-K@Pgy9ZGIt>_9iChHp*Gj`@Ma7ZKt;4J_<RSZ{EhmuZ>y;MahLb;xVYVvFQsqbZ9AaOGlH|zHV(w0a+gD?8S6Cz=iAQ6>-FpLz2J4bh$NdNhMO>LI5T?rMk2mr$0%1d8fz!xDEf7qCd^KK=EMj6UrP-n(?K+c(29Rkp&kQ80$r09=;wM%-$vl;Yf>HASZeuWZMc&x%1DB{o+C|~lsh#;v%{)~zzeppKyMP|uUuiPnd+cKE)6=7vT!oQMU@{3z@{Y;f#>6O*8zO(2|A$Czpq&8AXWH9K`4B^574OB{TF^*L6cQ$}s4EG{QLABXgEs*!@YaMNEFxdg)<KSP&(=Vggg&bQp`zqr@liu29_9B9=t6?EUaS8bY+A+Y?p~snGwQ2BOQMc;fhJ9S0BB7vub0Q*r4EqOk=cF_zi*ZfRGVnSyP!J!oo+(v_KJt5sN8{0;#hev;JO7WNduw>MlquXWfdCyNwAQ&Mh@fv#d+zpBq6U&s;d>O=R2pcq~5GY=*LW5gTwwXEX~4REQws&b_VVe`_x~Mv(1V#gfL?Z(qGXaCS3^Xo7RF`E6!vR8CU5ZGKo|Nu_A3+*)ehb;*!hJ?Y8J{SU0GSDGN9Q04Ak@wTl0i^Blci^1pexJ-0j-nzE=*e_V;*eEr=aqindnEe}Zk9^u)~%P$W3fl(H6?l14Yr1OVyOF6F+r{Q#gBnwJ9{|f7KoveRM3p1b+S_b)tE2zRP6@l)O{V>!+>1xywd+o2HofGe-?pUTpbd{Qs-bz7>xQV);w^Ura`OKg#3@O&0HS2FDkQbT+jopy=ONMhGq&sr0jt^m*JJ=?{$(zrhXQe2#Jz>+XE1t@e2rTg*vMGJEhDT_$N1&qNya_ljy6Ea^pmOcuoxBR9z##E5VCV8AT4?TKb_mQ*3bQmu5rwTHMxU(}KGRN)#;T-QeCFO6)mgn&Ug%3x%g>@&Ig85ndUgc{7(#)(FRZ2Leq5T!%v@`PN}Br#3AW9gJRH4rTfkkEu*ylza>3?#MSkKL8v&wC(|91D%>Xv6II>?@?G=NW956Rm1@@7x6ctDXc3jPZ-xj#UqU(N(B~<SM-=xUC65q6Yqey&%9Gs}4s#<a*j-Q>?Njfdp4t6)w=FmfNs!+@V#q=oG1{fc53$ACz{2o!o#P10^yjfDvAEK6ubA$R+X(nRSr(u&t#|S&niUXr8ra#Agf_j&SVkaM>E{(G&6HBzO0%1{T-`Hk$$G6c^<!Bo=0xK7_L`U2bf{KoqKUx&7OBdI>hb!`VG;XyTP1MMsgEExyGISz|6YS=4;ct*rS|BfN638ZjtlS@N7}+P;M8*UNtm{d~ezWD!Ag~u}7k<%?B*u-rRlv8D-Xo|;72Om7|8%EGI~+z5o=Aq}THIXo!Oh8fZ@8AiIL96jq%E><?gL4}sXLv`Q1|MA#G9e`GP|{YeXb!#O|+jX^;$$gZk;n%p@~p~ECn$o$QMa=ds^R>PV>N>8Sdo9(TLH8uYz6gUkDq=twOnoW(P@VFM?m^p`0UDnkeB-$^6pPMXf5pEY`Pp!w96kdfUv@Z#z$9R>qo(Kz=e(Oz4TMu`;gK`?YDjM(conI%X{oFMeXD$JE}=!}5>dxud7CG=80n0AETxOFqvmZ0PHUQUVU1mmG1B>#KR#um#BwVB%krM1h>}M+8SZO=0^_S=GA8!AZ2-9NiD?b24PPe-1qmtaLc_Vd?7f5`w-oG9iN0Plg99bR8M#71X<+UqY9nH`J(5oEa}o-Fy}`_qC!7&&Yj}Y)<I3j`r?k(4Q1r?!ETqx->+x2w9r;gQ9BZ^>3JC6f~VTu!C)tx$R|X$4ZJ88nObGm6~xYk~*I?>@hlUNRaVFPj|oQ5YTGIQ1{W;+h?479u*x3O|g(C2l7Q2iWkaR!dM)v+AIvRM~INmUZTmw>!unnj-KZ-vfmFGKE~zbIKHtT&}Oll>vHx)BbDt2QIJQXcYO2qU_~7a?-sSAji8eiI(G-1L<-UNHZt-Uz-3KJEp(_=PeYc^D)UxBCWU&g>+B-ZnFG|gPAXWpfQ7^a`z>RklOXh7dN39N<1G4iAdK(*iZPMZB}uxkjKh3z`E?;H4rEC|mK0={RNO>K2hswJkY#GUi{_ttnG@Ur#=<h~uuP(PiGW3)g{Ddby5YoaOW_J4n~w~MH%~mTh%{(XAg+QACF`@dJ*#llyzXZKW>mJ_5T+pQPEef-)nkc@R;B>ceV8p^n*gj}z|51=lPGT87u8J(VZ(98-@is)Ne#{=&oNivECQVMY-KCeD;aLY?5R>%M9<veOTz=eUaZEJz}AUwR8DuXj#?mdU{_1L)x9|nuv8ClJs;pI9$*&gniHew2i^NBH%XwFX*eGu^`myL=?nb^G$iy#cL(R2gL76mryb`_;GBf&=@Rl|(Hc-7*+hzH0v(VLy6(n1?~q;mA_-X%WmE~-BKXZUWGm6Jr4m(S=1rF;^pcGwdtyb2o^X;zvQ(V!%glN`v0Ziyw+6|ik+eFxL$jq=;Nc|-;!>tdUcbew0b~|D@kw}GuP1EtzL#nsHv&k+mNIIK+UFBVI2c)bAcX6mMP)Xy$_-Ylfz=|gx}^P!_~ht|*!uUrD+scV6Jr}R42bp0GI-IJ&w3ZOVn8I#1zU}D4N(yg&Ek_oG&r=JjJh`kjNbEf0hU`$pQyPV4h2*f42TmLsfyLnXIYKsadVzW5zk{0RaxhG{EcHCpe~~>31~NKtcb;W{6AHecu;Q{GL_vxFLp24U&C=~_#$}Bnle641P@C!Lp3_mM|FhMovR|WEx9~DMNpU#SjHs>_e#~1@f>1mBkAR}!mBid_*v%*FfV&V0u?i?xx)P;Wa}FcR<2zpi*WNi$eWM5jPcZJJNF5#cnEw_$J_Mo$SSV_pR0y^lxhw&)Cj?kbtdAQ#))bIeC2p#GC<~LATvF|HPOfwFpHr}&!aUWF!i=L08L7$>L4V{m4<AD)vT4Kd2_!mD+#`#u^WknkL?b5;FC;z7KT~W-Fh{CJ?RC;smf!xA?9m#vDidWTw{@KES|(8##ImaQ%tR*O&P6*_vLnGfu+aewC^nr5TxmzA-CK)f4XLusM3a*joD!DUg`)w0EbBG<MEy5>UJ1i&}K@%T0x)j3z}5<qGD)LV=%iuK&Z8*HAJWF5W6D2s5LG&88+=itJJvvO?!&L!G)y0nx$*ju@V-(2E6}jAZC;Ke%tfVHV|8kt7;q~NUHsPeBYqX5XrJgkYOrke-rZk(_UU1<&&E0K_9H-p%P<>RwW-#k#vCxK<|@8eS(-sNzoi7?{upkhZJUZ9tY?S>|GpKOIftFbF5t@4clv|Z*!m)EA)zhW&u~K;7X6Q3mQ(QJvJzH<lFV+Q9miXwpQUza*(c4<Lfth8a}-s0d`nn{^o0le;=~N({HDJNyGH;<8^E)oKwY%x}Yoq$~8vVMEwSAc@Yun$)%;cxH2W2i}ej^qtuIdIaSTT`FwwiIDOU_Q_S?orC656-+IP!oN@Dv|52g3J@P0kQ$Ohy^8ch4tK?};6-l6+5yUK>;li*o%~Bx8%S5GU<C!;qY2*>+&NK8W%C5vp>%A&TmXiQ{-eoM4C<smtXAJJ$xG(r8La*$ewhYma@c`|2xaKF8=!U!TQO_jOPoP@sy+uDt4lPY(N@_GC?dF)-Jan=MP=#Itwgx>r0vC)T+9#Gqlr{_EbUC~Ao<r+{x5yU;(2mJqn0>B0L_IP>joNCWCfy1$(+S$+gMr<|FB){W)Of>4ytkx_;|6iu1db&vpVMI*z=SwsNJj`E*yd5In*3YQsrHK9gxG2MkzPHla7y|OBN>Q3Ah`mhuz-LrxLysHboXEzM!>Fe@65lIXT4X}xSJ4cCFbAl&<~eL`ed9GIG667t>M<NyYBncS0MwHX#>wQ;_fU9=4W<i(6?6q)wnTlOQ~Y-TjTI*0h9tPRrVMHKd=Wgj@HWFcP)tlL(?4GC5LHhBX0|9YkE+OT2Lk-*nG6DOHe|ti@o#V{c~T9z;-e7vVH*~%33igE;u&>&S}8J(gYFFKY^@POqZ#QW^szM>ukbaSVFb(Pz^}~!_*^`y0U)x7$xV0-nfb=>`A0%QT&q|*JQhxp@wy<yR|RhZ$&rZa5j{?ZlRF;$3>8orPv^4=*D&Y^08j`^;&{ux5tF79=U=QuZwc4*o^IiIBu+$l#ikN0U~Uq57_NR2(C|01J+-+g;cGxkz0iXpwvw{kXsr_s1grDka8cAR5S_($Pm+=dX5P8p<c@(%m#BM*S$2_VuoUoJ{=6k5#rdKf7bJ&Ma%1S;hT6t(7?O=z_ASf);a7CeUGJCwAxE6=2;|$XQoU7$aY#*wELIgqP5=i1r`Y9J`w$#VLf-MGTg(_+4;GW>YJU1qmqg{me#|0$`9SGI2-fLv+;zU3BkwT_2)nSzd!xY-~aZ{zyICGp{4))|M^~Ok^")).decode("utf-8"))
_FRAMES = _GRAPH["frames"]
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_STATE = {
    0: {"last": -1, "calls": 0, "pending": {}, "experts": {}, "deferred_completed": 0, "fallback": 0},
    1: {"last": -1, "calls": 0, "pending": {}, "experts": {}, "deferred_completed": 0, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    return getter(key, default) if callable(getter) else getattr(value, key, default)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _step(obs):
    explicit = _get(obs, "step", None)
    value = explicit if explicit is not None else int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(value or 0)))


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _positions(obs):
    farm = _farm(obs)
    return [tuple(map(int, _get(farm, "farmer", [4, 4]))), *[tuple(map(int, p)) for p in list(_get(farm, "hands", []) or [])]]


def _inventories(obs, count):
    private = _get(obs, "private", {}) or {}
    values = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    values.extend({} for _ in range(max(0, count - len(values))))
    return values[:count]


def _tile(obs, position):
    try:
        x, y = map(int, position)
        rows = list(_get(_farm(obs), "tiles", []) or [])
        return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else "LOCKED"
    except (IndexError, TypeError, ValueError):
        return "LOCKED"


def _valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    position, tile = positions[actor], _tile(obs, positions[actor])
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
        return position in _ACCESS and sum(max(0, int(v or 0)) for v in inventory.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inventory.get(order[1], 0) or 0) > 0
    return False


def _toward(source, target):
    sx, sy = source
    tx, ty = target
    if sx < tx:
        return ["EAST"]
    if sx > tx:
        return ["WEST"]
    if sy < ty:
        return ["SOUTH"]
    if sy > ty:
        return ["NORTH"]
    return ["PASS"]


def _nearest_access(position):
    return min(_ACCESS, key=lambda p: abs(position[0] - p[0]) + abs(position[1] - p[1]))


def _record(obs, expert):
    stats = _STATE[_seat(obs)]["experts"]
    stats[expert] = int(stats.get(expert, 0)) + 1


def _repair(obs, actor, order, target_position):
    position = _positions(obs)[actor]
    tile = _tile(obs, position)
    op = str(order[0]) if order else "PASS"
    inventories = _inventories(obs, len(_positions(obs)))
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    if op in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"} and isinstance(tile, dict) and tile.get("kind") == "WEED":
        return ["DIG"]
    if op in {"PICKUP", "DROP"} and position not in _ACCESS:
        return _toward(position, _nearest_access(position))
    if op in {"FEED", "PLACE"}:
        item = "WHEAT" if op == "FEED" else str(order[1]) if len(order) > 1 else ""
        if item and int(inventories[actor].get(item, 0) or 0) <= 0:
            if position in _ACCESS and int(shed.get(item, 0) or 0) > 0:
                return ["PICKUP", item, min(6, int(shed[item]))]
            return _toward(position, _nearest_access(position))
    if position != target_position:
        return _toward(position, target_position)
    return ["PASS"]


def _unit_router(obs, frame):
    seat, step = _seat(obs), _step(obs)
    positions = _positions(obs)
    count = len(positions)
    planned = [list(frame.get("farmer") or ["PASS"]), *[list(x or ["PASS"]) for x in frame.get("hands", [])]]
    planned.extend([["PASS"] for _ in range(max(0, count - len(planned)))])
    targets = [tuple(p) for p in frame.get("positions", [])]
    targets.extend(positions[len(targets):])
    pending = _STATE[seat]["pending"]
    output = []
    for actor in range(count):
        order = planned[actor]
        token = pending.get(str(actor))
        if token and (step > int(token["expiry"]) or token["order"] == order):
            pending.pop(str(actor), None)
            token = None
        if _valid(obs, actor, order):
            chosen, expert = order, "scheduled_task"
        elif token and _valid(obs, actor, token["order"]):
            chosen, expert = list(token["order"]), "deferred_task"
            pending.pop(str(actor), None)
            _STATE[seat]["deferred_completed"] += 1
        else:
            if order and order[0] not in {"PASS", *list(_MOVES)}:
                pending[str(actor)] = {"order": list(order), "expiry": step + 6}
            chosen = _repair(obs, actor, order, targets[actor])
            expert = "prerequisite_task" if chosen[0] != "PASS" else "safe_idle"
        _record(obs, expert)
        output.append(chosen)
    return output[0], output[1:]


def _projected_shed(obs, farmer, hands):
    private = _get(obs, "private", {}) or {}
    projected = {k: max(0, int(v or 0)) for k, v in dict(_get(private, "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    for actor, order in enumerate([farmer, *hands]):
        if actor >= len(positions) or positions[actor] not in _ACCESS:
            continue
        deposits = list(inventories[actor].items()) if order and order[0] == "DROP" else []
        if order and order[0] == "PLACE" and len(order) > 1:
            deposits = [(str(order[1]), int(order[2] or 1) if len(order) > 2 else 1)]
        for item, requested in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(requested or 0)), int(inventories[actor].get(item, 0) or 0), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def _fib(index):
    a, b = 0, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _market_router(obs, planned, farmer, hands):
    farm = _farm(obs)
    projected = _projected_shed(obs, farmer, hands)
    available = dict(projected)
    market = [list(order) for order in planned if order][:10]
    money = max(0, int(_get(farm, "money", 0) or 0))
    hires = int(_get(farm, "hires_today", 0) or 0)
    quads = len(list(_get(farm, "unlocked_quadrants", []) or []))
    land_costs = (1000, 2000, 4000)
    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    safe = []
    for order in market:
        op = str(order[0]) if order else ""
        if op == "SELL" and len(order) >= 3:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), available.get(item, 0))
            if quantity <= 0:
                continue
            available[item] = max(0, available.get(item, 0) - quantity)
            order[2] = quantity
            money += quantity * max(1, int(prices.get(item, 1) or 1))
        elif op == "HIRE":
            cost = _fib(hires)
            if money < cost:
                continue
            money -= cost
            hires += 1
        elif op == "BUY_LAND":
            cost = land_costs[quads - 1] if 0 <= quads - 1 < len(land_costs) else 10 ** 18
            if money < cost:
                continue
            money -= cost
            quads += 1
        elif op == "BUY_SEED" and len(order) >= 3 and str(order[1]) in _SEED_COST:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), money // _SEED_COST[item])
            if quantity <= 0:
                continue
            order[2] = quantity
            money -= quantity * _SEED_COST[item]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and str(order[1]) in _ANIMAL_COST:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), money // _ANIMAL_COST[item], max(0, 100 - sum(projected.values())))
            if quantity <= 0:
                continue
            order[2] = quantity
            money -= quantity * _ANIMAL_COST[item]
        safe.append(order)
    if _step(obs) >= 715:
        sold = {str(o[1]): int(o[2]) for o in safe if len(o) >= 3 and o[0] == "SELL"}
        for item in _PRODUCTS:
            quantity = max(0, available.get(item, 0) - sold.get(item, 0))
            if quantity and len(safe) < 10:
                safe.append(["SELL", item, quantity])
    _record(obs, "market_budget")
    return safe[:10]


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, pending={}, experts={}, deferred_completed=0, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v92_event_option_resource_petri_moe",
        "model_id": "v92_event_option_resource_petri_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "event-precondition-petri-router",
        "experts": ["scheduled_task", "deferred_task", "prerequisite_task", "market_budget", "safe_idle"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        frame = _FRAMES[_step(obs)]
        expected = len(list(_get(_farm(obs), "hands", []) or []))
        if not _FULL:
            hands = [list(x or ["PASS"]) for x in frame.get("hands", [])][:expected]
            hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
            _record(obs, "scheduled_task")
            return {"farmer": list(frame.get("farmer") or ["PASS"]), "hands": hands, "market": [list(x) for x in frame.get("market", []) if x][:10]}
        farmer, hands = _unit_router(obs, frame)
        market = _market_router(obs, frame.get("market", []), farmer, hands)
        return {"farmer": farmer, "hands": hands, "market": market}
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)
