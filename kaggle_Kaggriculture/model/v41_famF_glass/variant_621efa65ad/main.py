"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)VGmOZkwlck<m7}+hf<QS8IFc=^c1PCUJNp?a0_ekpQ_wKFxBhMkLUMmK&(o?^WTOTBgJUnFm>A#=+>tFu<x4-`V$v=GYrzdZozkU1U{g+=n`M1CP$G`mN$3K1i&)@#?_kaKEe|`MlpPu~i%OC&z=Jw|0FE8Fb`S8}SKVCoo_~Pp6`}hCz<rljj`}yYf-H-XNy}f?@diyiqefYrLGu~cbzudm_?C{P{*ROAW{`lyxKfU$itJ~`*rB@$+?D@~HetQ0C2rq7a{qWD%@Xp&Gudm;HdhamBU$5W3+t2XB8oqk*hhN@2{N$(Kd-&L9O}2j=zM&TB${WY#QRfHT&1D?Q=H(B+yn6le&mZLA-7g>4$=&|rklwt0{`0%@J`IB#9<v|h-LH-#!%2L2%8Tp5%029^H-}%Jzq`IY?C<W8;r8NmUOcBoogOCa{@s&cN590q*-ql_)#^d!@~}~chvnVu@@XGHfgWYgH&6ZjNAokR7%cH+26z1&><w(@dH3^$9l!e+<IOg6Sm3))t{&9G;;{VTn8x*7t{jJRm-lsRUmo7xn3vsVCmU;7kj*}!z2I%6E%U_UY=7{Vk1xeT7Og3LW&GSlSNHgG)#^Tca3?sQR&8c!H*0r(K)SNqzd4Uzww`z6>rD3kZ^3e&-|jEx@DurhEq~N@IWIJs@RfSN(XomH3?~-w<m>vVE9Aj@76C$|z+=RN$uoct2kG`1=fjmv>)rd}hv@)K{msn-$OAq;;O6z~>lg3-{QK+McduT*`sbrV#-9*A8GWf?OHYne{P43#zrFe8xK(F|Ve=EhYk&az{<jTJ=Jd&6^z*~}20eaSCu<we=4UhX-1qXw3V}RXt+PmX!aC~_n-h3*K+PY<FK=(&jEB-$^%vOj?TV~CA1-z7kZS%P9`0{#c`xMp{Qq$A$3FYd4mR+k_0OEJ#6nlF+7S}|_Gre*<;guaI#Y^>f$yRnfdV*+wDW@yMcF+>A5{Ic7lG0?q@lb&YTAn9_*!wZUU&@l1R`lg7wiXACy+}&ZtV*3=Mh^!tXEtN-&z;+lec~)`CdOhzx^j?4z%d!?Zk~O!bi0HJo?j^R|@^+QTs6BfJJy3EHL321)zvyJe&eaI&W04@xd|n&FOd=Q;7ugj;TR8tiIHsd1tLHiVXj<K=nPSZAh)jp^G@%Ql;D>G6nCk9IdCjhl~>1%YhqyRUHv49x<-tcCkaO{)F|;9KSpaZJm0~IAXrDfd;+r?a8U^PC@fIl~a%>g!#CBz9u@<$qKrziZ~LI84N32Jc>|Ma1qm0ZpaFI>A~8XM~D;^^!bGAG~vh!XY)9QRS!Y9YQ|A}`aU#`^i&aT1P<HN)469jY(^sD1QKs{I1{_Z%EYFKUsf}mc|Irb{|7M5T6<Vw&V-F_-IwG%t3fn&^ZbKn1l`W+w7t##6AGE*fwMNwR6Xe6iGI6#?701N{^$74hlRYo36fx+8S<<C>@>JnN`iUnhKVlu$n6HbeRuo(*B`ELZ~w@TrA^wXcEJzzyzbPXu`963QAFE+_@j7?;PVFCv;v!D&%yOD^MxmGtKm*oP($*yMABJ2T_oK%i*}GW(jbo?DD>wnUPmvWv19B?Z2lTTWCapt!L!=Y$e4POi;!<0bD$&fLf7ssJ3vd_5C4bPZtIe%AuT8W;pu(KpLzBds~8`KLf?iDa=}E2SL3Wl&ue$EgZK4lz-R7mwlmD+e*%@MhJTKulY~Pw0hnaJm~V^3K!1uyr!1AE$pc{xP>N+Ufp4(pi7nr&`jF1<u6Kjk-G-C2pENYcgR5!u5z0)E^Ld($6Cm8blcTfIr~C~yamk=`HCV)!X&%6~UHp(h5;(-HvJ?uLRGgRR(%@6j$EPg6Eo@lcb||?@1**X^$SV{%-iQU-V%g9<4T~`$CuA@LIDg=Iibp6WOXm6756P=u!JFi#rYvUZoubh(iQBnXUR{oh7qlFeV_d6xUf=a~kAB(-Yh82zh^iJ881(*+pDmnYyb5YU8%vkF=1+}TVck$VBTxOQAeo-;d`>(+SP!f=h7oW<MQsQbM-ZQ~twm~lPZ^5`Gx_Vy%|}_h`pU4Q$&w^2En|3_xNI|=UdfCw%nxsWIJ94$6)kSBv3Z8V<b)$mM=Vvn#GfnJk>b!(!XFI{=S4{9x;bQ3QCX>FfY2VZw3~@&h0EtP7Y@)Uv054TLxgn|DDhC67>G91Fv6dZn-SA<8^$aZ-aRj9NHcTuk)V7sBX-Tpx0yRW3w0QPkm4Fep;;rA?IXmlV2(`(Hfe#bY7bDt&doka<PTxEG*xKRN%(L)O8hqtO~*sp=zSpeoJQ$3q7lUGGA_oEHNiZ>pq|HYfH@k=p)0~yKxf|Xn43xqiE^JbulV>X0)+b5%%SLdFm}0v>iQ=8=xO}x@63Ytm`iBxT0&!-*zUjtk#R)4<us~jcX1O+qTpM}QqPSc=IFNPQ%Sn<on1gu&f&46=e6V*7r<>cXdXv62>*{UuHt-WLG{L=y-2*?bf&FMX`T<N^V{cFN!CgYppX&UJTEx3&Y#`9(!tYm1ZC$8vws_YHTb&&fE3`pWr%`~Qq#~@vA-wXR3k?iF03Mog<qVWNQrANIFB^oGn-jQUs-WPcUQ!aW1Ruu1Tl~$wO@kJA%>uwV=*FhZn)V^rd~2bw}e-VXBKwJix#ENYE=v6(tqVkF%G}{=b(lDN}9VRmV^+}q7UD%uO?CIsuIe%fL~?=NIZ|%u-z<C1pgRd=I~`ZZ>tzq+47I#;%BwZhOZP~XB=5vlvT@f{<Vz{c>Y`L+&xx@N_vGTRPp(6gpQm1C=u*TI{Mq;K;1vmPa<`uH%#J_yqZcO(%UL{Btx>pLyEbj(*gI>tJi<{1V}{zonod&r@`Up<r#Ti%=>R0Za)aKAL&NXy$27T`thCQMg-LxOn7_<JR(A8fy?9K`KclFq%rX`Tubn<mWq6!a*S=@1%(lxwrpILg{`EojxMG@5BH^5;ZngSz$JW(0R!lgg;+|%%?Nc+vzG*>!%(4V#gr&_gD_FfnEuT4ayK)zK?sxMw0^+8QuYx~5=XL*Q*&~0We0MgZy)>}^);1y(J{#KFx=j8=-0+rdAzhG;)*HJS>uWDNXP9CI^C=iR=)@aGt-9QDQ-XdyCRb=vN<ZMwR@%{WDc~{ZgL`0EG0z?@<C#&%_0D4!lvakOK2y=+2L)J-2K6)%6<b(f1)HF{T`hTQ)HTIw?3;)q(LajVH#QB(yQNXNYtj8jo6E%1!DB}q8f)*lK+!TFDZ@)Ds!!ph6m-Wl<Y>JO}*q+Ry!Qy_7;~J+tj7i1@vz2O3enBG)Btq)3Z0h8{ITGy)j-QUZ(qT=#ubU2!UtUdnWNe_j2V%6c7=KOG4mzDG|p?P8*@f$eF^xGZ8;WNVn`{Nk9>ie1AbpB?N|t;x&L8+=71XuA;DU#HeEMv5x6GRatb#ms9XLI*W#1gBHX=@?*1xzU+(azMCBw98q=XMBL1FAA{LwUNE^UNxr-Yi!z&+EbrN@k&+K|ZZER15-X!x4diZB<DEcts7Nl*oRWkVD>`#U%7S67T3i}WD_NtpRd>9nO1{8OP<s^r7oVJ0Bo<>s!8oFLTd%BIvHr*e!S56dQvA%C@2*_RvNV7@IUR`Z^9r|9)Y@3>U^aC704djaon5%*OM5jK?2s79Scz1eUrjbE+rJWct;_@K(uaMPJi{Q!%(^ukjk#S2kx3on@>Lu2u`&TQRoX!-5UIRmB3H0MH59|=Rms$Rg?t;GQ#;S)fFy{0AS@v6OU9FkKc6=>+iz2UyyzB3k47hs946aAST$l5eBeh#9e~?)SvXL-iI}`mKw^4#SFJyg*v5T`4CVe?k-}ojQspz?$O5)4Pr@#n*?%qgGZDu2@W>(PQ>*rM+RGKzgp(OOURF9i{T%(*khMAYD{yZ`u7+_=z4^JrL{)vqwVP4^9}L4-ZaZ0847U$|wrjKsu(Em?s<~yH+-CATx%`TH!|o-yqH&JXn|hw?-LPNWz|AC5iGjVcStc%(m35G!@cm?{?v{1<D`c|8W()GC(`RG!%0O-<1ABT$(;hy|@KCO3MKL{JZKS7vBAVmDv9TrRX;8BpLDS{RE;+FhPu_(bs0t-*`?FbuTp}YHYUPj|7FX>g%tbH?b#Dp0SVO?p!&)_lO;{k+C)ryNtuSR&?_Nc6mZSr)q{*n1ie3qD3!4W#Zwg8qNDD_-?H90yUIY$gXb-NA#WJU0<k%I}ZJ7G~of56b_H=0B!d>H{%{Fa`nn6zSkYqN?pu#&1yd*Hl++cFC^C)<#g<TF%NQCNa-7ryFS|=-`E4Vf}jSLSMrihs1t1Pvu2aISovPeZ{2gmPfZdmGJg|_iwULGi2VlaerVG-qUjN*2wW`(pp%rYy2Tck@F?p;3j0&OxB*^pVq#u7CfvwMMon<HaRdrYZP$XuQ1%-}*{;TngEQD`zTy-x_bVI=2RLUBtn5+btGPHYSh9*ci`MiH@${i?sq?L=P6gkhYXK>qzT8<JboT3ja@iv-KHaF^H?2*Z|`p2%skNpfOGq_^!f(btWX(_@HbQ<8wa3I_B!Y}l}Izi4c_t=zj^(u$G0Lzg1^=hLjj@EPJIQIAQZ;V5&7f#jzctYGy8vO_Ru<1{<$-!kdO!HTm?EBv@$qm3MavhT~6!K?K~bg*@B9qRcyf?`8=o%*|~bTo-;9ni{s)oOklH#dseTG40oTC_@0>=h)lWI9jOquVueZ6b><Qh-yrUcgtadpBH{ikstZZH)Ka7p1rb!h}+6enP`E8PE_~)l;30WmFL)z(`6}w^fUn0<|DnJnHSCwUX+*RlW~>S~hEC6DiH6w~~ffsy#L6cg0Hk05T<Or&5z<mY@En*f=HplSXW@JSB>Dh!ZX?vy~`D6*USw)w&Ep&p=f$<%Kqf=tnF#i36e(bZo8$u|#!5MGmk)K0$gL%Vd-nl8;+)<0I?Uhtv&(HoC8a)={7fD=7F_9TQu`aNVnL5jq=qw&$H-u(iq&HR&u;MFKI+sAyT{(MYTuIiQ+yq(qE7DV;>=G;&czMv=M2acL}KCz@VR8OA}TCZz1+$Y-A(_&AaHRQ$cBf-3sfxLB>B6S{2ky7M^PGe3pva?yJTJnu9p?-%0KU~ARTqtTqEG3GQj$sR8G1qA{{^$^Sw=JBb*BpH#Js<vqn>7}R{Yz`PtC7Mc&1@pX2L}j&mx`-L5@@gJ(B_ZS8>gun#x=%dkQ>jFG66lC=`JLCJ0!QTHFu~l;Ry#mJu_0C-y9j1m4QcYA1UtJ}feef))U4`344K-IGPI5dnTU$K=tK+=8$suZe%1Sf1h~3##+`NA`Z9Yhui3E!uZFbB=HKmhOBBSc5YaqW5uCZA_o!uNbFpO2u^Bj&S$;eLWh*0eF0Uyu%ck<+n4KoW$ElDx#4@i4@|EcpcmTcXudmeHsp#KCB2H0k(o}fdhtHmI$8aD3Ftaj~F`v$br?vha2#}1clhuxx_t5h_JSy^1H5RgyMl{{sC}u9AG|E=cG{z&x>i@gpK0SN@a<^j2CJP)rBQKy60SnbrAMa+88&}MO*sY4>niJra7cIsse_A{H#Lcm+kqL3=79j}KP``K}KhV-s27tjI9$~&uMjW4hqCTMxwp7yxk@&Yf%UF8Y%&6OAI0=N)CV`*JGK&ZiOV&8@Fa^5`eHIYfsK?R@@vX{gt<_NA*-;QeVzWwYc^F~JS<v;X@NG$M^XqhCCkJInyD&v8NraCW9+%?z1T3AC+d^y^ajFW%B^@Dc=R$;LWvJ>($>q=ut*dY#iomlV_T<;+gu<%1^MsH#hALQcIoDt1@oYj}m4?CChQOgbq;x+p3;19%UEwaEnoyI}F0MXkGagE_5o7GqBX+S)(vjmc5+k4=vL+)73OI4VoQ@k276SDNqIR6%9%?(Ch5UJ`hNg?KCxuIcNXfH_S!2&fVub|haf7_xCQ-7?;E0h3ns#rmU)>t`OB*-E&<IV-tFVBptE^i9?@++q)M_pkZdh7>(^>rzJc$5jsU_edvPZnIdEAf-xlr%$3Zc<ipdv3(bg2->zR(A~<KlIilcHT@w%;U)A^5^yCa~yBfjlC6B>Dy}u_!PeR`unpe@yLiF7XOZ6W;MY+W_eX6c!mf?k1Sm-%e>m%I)h3l)@ltM*t=KX9jJ^lklm~VW3vN_suj9w|<P^`F+!FFV}Vda|8H2Wp0IrlhP=+v(Kngem@Zy%NNk)Q|}WP<1@KPuMuE>(%PXjY{i%hz){7+&V;QqObN#3?hZ+`QO8*$VeYzEeiu(5qWQ7Eqc1uYD8CK%?8d)u`?-6|?mnImEL!wl<I`CFs>~TgiEM7C4I+sTdb)D7^W)}zcIu1*w4D1>3XK3Xh%(-tv<y3P9YE$MREmNG=9K;(#Xw25Ph>3i+zNDvzj7VolrTWE&RvzHUfI_yF;YrqCpQWe92eY`RWJ>V0~M}Rf}v=e<!BYX*WNH9+k#MzEOwgeHz7@z+6j{N*y}8>IsvGdXyze@$9ctpLGQfplMC#`pw`r|ng}>t<M@{D)E-cf2xH#5$Uz|7&u97phu=sgQUqO<;L(%OnIAhE1rU?;a)TNLLq&`u@_lepA7&Dq*Cvc$cbin%{whYrKiw}ZF@}O?abz_Dn;mG?K@G$Vs0Jk=aE+^!^Q+{A_eD#l>rn)Q=>U^`ml=#aV;2&N@?^&SgNI9l@BRuG;Rx!XxWO>Dwq=ZK4iQ+dJ-XEk%4!Id<avZ+Mrv>MlAE7N%Ve1ci0#hi-d~|Y!Gox;WL++xICTA=R?ZwtJEdIouF|bqsTn^{T8N}5Z^{eYgGTE5>Yco`&5EWhB|=f89~FKQ^$cE7YbJP80|fGY{K-0qCKTlK$Z77?XUEnkWW)1C)R`Sh@z~F77N+f>qKi|rbot#BpDO&I&A}?pLNHC#2#Tz$YEDUj2IQF;kPP8eblz4+E65vtLKWjKM(i%?V@kc10dFnQwImX#zNIdkn%JbAezMh;UA(2+o><jA<#<y=fO*VPNuA~0Bt*bdWe!XcPNo~AaJgxR*d7<5qWBd6TR-BDEM1-2sKrf?w#3*f7pKIPW*xnkaeg3R(kcmrX-dueC(3roBgod!M%Bw{<{}uMmBLt31jhu~uGmoY_9lRC;{xmt$LcUVmt)Jj;5QvPJ-@myIcsZ>EYY5h=RFjgHN?m|cf0a!&{12PV`eyVzEr|H8$N0D1FN>FwYfVv)5~n_yPsp^_*dZuG2pz5a^7pV(Y0xbpj3J-i;h;JUJ&|ki=hXg=2waRY4usg;W~GRFus(W6%kkpmKLEcT#(-xQ=Ede?1Mv*^?q|O7v&!WM3Z7$cFEbnYB@ca(*{Mm`)wYxOi|@pGT3ZH1U0pcw#2nJDgg73Qi0g1J^)9ao*20f!$h2g0UHw^jGGohYG9vGljl+s#fe+GjEdK0<r_6l=%8?|RsSaB;CgFtx`pL1Z?Sh6`e7`YL*AkfWQ`ubX%{7#)x2rCQHxd(c|`1vf@p{0zEg!AVi{DG6;4lQ;slCq@>?fm%rf1Uxz=cYNr_iX!4gis;nE7C=IpMJ=VP}93iua_TUw-LdHbS?6*O*9k&J*vPNhkeeigY%L1dZIkoTfbn#{Y4Y?w?Qkw+Qr*_=}*Zu*#D>?;l&jZ2+KUGTOu{#r|T0zpv8C8ueE7$)(axG)|M47<UR-Jk%D?VMgI?vtRH;Ru$Prd2C@)aiT`=20?m%8^DlO^~v3_Ex#DK?ep{KNcSlWt(icrO7gi>5-WZ#PA!(K<AlhkwR0O6Nw=J8l;i}1?5$oh~;F&X!Z2^O;u?gx^$`3Mz{DfKD;W#t<ctQn-ebu+7{I?iY`<+mNwy0D78g8zS-F<PdqLezGPyE%0|PFs}$jQGYMOfws~V}ZXPi)oIxc@c$h*FInW$NQK@1FqYmpw!5?`#G!FA6e}yH$V=q<O(c__ysyofnDi?M+SpgI?BO2`!)53K13ZGQS+lW%_5Y#apBPzZWFhx_21n)G0xpV=sn`68>PwfXNSCK6g>J4i{kU-SfEOVn<7tecwhI$i8xz2xZQKt-EwYFKIjzo8Bf@KxYlgCy}ff&L?0hZEMLGN^(wh1}H@yp^Vqrg`<lDXJ8r9P_vSYTDOYsh)Dwx?M~<N{ISq>3!jRGC>T%h;x-q0sGXCWC5y6+jt;RB>NPKB-|q7Ox0TZ!`yfHp}Q4QWdc(CCX3(?C72+w<@P+#lw;0skGLSIEAv9f!3@9WKj)g;;>$3>cO24v?54!(|1Oc>G{7oqML{c+*bPf-oYH@ZUAw|OY4?mZZ-qZoR|oi+&gC(*A!AoxHhvN$eZO)BK{>#Kqu<fsh~KoM=tF|$0g^2IWZfjBm^^yPDlO7`6>F3`IHK{oSzP_AaSbtt${FRJXtt}$P|>DU1>&^D7#j~ByW0V2NG3hjQ&#<h&;9RI6fnqT9!|jh9lU5Vc3<6pvc!rElTemLl5$IN-`t#fk`le24Wyin<t9Vm$)c&Oc}ftI%K1GbOBk8Q$U1z)3`-esa^Ccd2z8uS5?D0h&0dM%1nGu){b)g6{<<BFo7+R(Xl-4ia?(x|6+~;wcNh<k@I_p2Q`#Ob?{R+x@xxv%~TbTkUHcL&Pd@zfkWZ|sS)e`c)bNp>1Vv!7J_$Nl*j-`cA2Pz%w5Sqw}YZ?+^QwLBNg4%?(mj((@b21s(zD_WDTYV^}r`P1S;O6gLqFXjLUdyhhwVX(Ba~HN(1L);7umo-|13>O4YWac2^6ak1WM;F+Mx`hD6Gs7_!o>zj!6Vh*i0Wz`kF_(rXOtihDjhb2u&kTk&KK6ot|tJXUoZyaGUq<0YBXsf{Q?sCo7NRNT_tVD;CM*kq%aY+jM_NI1<_0o`(pZEJFSL>}))Qz`;aJ<Z8|X>{uIMz=otR3q~hm8!-K_nZnoXpeh-F(s?K6m8yf@YI9IY?X>ouK4l-o!w6tVBH}Tc)jddBkY&)LpLwQkb5c-kaKjxT`EJw0V*D!h*KJ+-{F;QVZ<V;PW=io&#LVKv|*U_K6EN&X`QxuJxV84wL5D7%y7zPXAT6Q?|=$3&Zi(H`ti2Y3@JTaXZrpzLoou3YNwH^@l^2By2gwgB8$9=0P9$)A_K7ZM1z|Ph*8D>$k=X!&@oX}hom9_jM!D^<7h3`5pf)75)^nUxLo)SLhx|3h3f=FA2-7=)3&<2eslRPceip00o!v$284<BH)&CmHVd(B^x*rgG1&xRD{aqKVzP-GO`~M=@q4q4?uu?tCz~cgj1*^9yrT#}5k<?(IRfh7KnEc)<U)r8?~cGn8OPOlx<-4kHQB=~`>A^oDB+62aon#q3d(1KXg^ShN(6N#(g`4IH;HUC=?E^U^#ozpGzV7vBHHE(0OXhxc8sjOpR3pRe}3Y>nRA|MZ)F$?gUeL|DD7&1IR>!el=6PXQFnkiG`L}snG;$`tz&LpU)AKBY)i<`<?*_xt7Bg(AP_<h!`GsnKhf!(IMKYp(8j{K-|MyX9T`g~PNa3<y~)`!(VS0I-})UM#tHc#r*rK~g@-Q!LTCKLZ=038E*FR#UWp@-rlqi_GT!P~3UglRokCH~I3X6~Ax<AT`A$2X=uMuSFyjV_=vsHln?rP5Nfh1?fDp#XCLmvEHE9mVm1B7V4H9=#h!W&G7Zoxqf;NYsj<|M$eYo^HmTj8k$l;bWZ=<N-?CuRFk|QT7b7`k+fKS({mM?!TB6=gs>+1d1m!PD<B{9GzcP_bSvqGq2)T%z01x2WsP7#gwz3GZhEA*;BaWeZY=6--kY%ZEX!_ZY(2R=Peuz&^MtlZ)b(N4|VD2zR&#8{$a0y{w*UCSBs(MzR^Y3vitE2fm?%7NPy6(vMRiMr>LG|-JhlZmZSCZqP-=E}>JIHnlHyde}7DH+8uX*Y~jv;i+fDkzxZHb*N<0RhIhpiyo0k;p`TL0hxn&()_(DNp5!Ur&6Zz4Uz3QZGN0iDEerC-tl_yl(OGtV1v^p$+QDE>Hn2-Qgr^zF?Y9Yor~N>FuaUURuqllwi$bJ;wN*NOU$mZN}LYxz~X(X+1GhA`v6Am>d!5SGTn8Y-L=S7W!6&Nfv0dUH}L312gJkC3vHP+@mR`R`>Y)?2PZc41E`*1rzEac%|Ox+ef6j8B~yEeMHBahwg~c>;hNkoz=wWG*QKNlfc#jikuiLI3AJ4-=FVaKl}9SgmvA$^Eqx!7&*6<`wWI1E;L~KG9J*=@mQDw(5mD&5<tqY=Y^oEbyW^5Su`Z{dnsj((2=_MJ))3xM;o?!E%!Uh>X2#rAu~sia6~e!(eu3uCDp?A!j72}%0UPD615?&J&tGAr+Dq|RY5!u2o0gAiY{yPc8D~MZSubx7ivA@FK%pvqAN^^xE=xnOP*c|D9miSSHC_(%~{bZ+u-^nv9h&3SF}Eega?uz1I2-D4T+H&d@jWA$3!C}#l?w^21_9p!S0o?VCU4#8!nJD!o_K6STB&6a`kTgsHZemt;!d7QFWrM85s)HQMRg-+0CQ@l!(-%ib9G_BeEOGSI9gSqH~&=zdaN1FX;#q{tNjnnJhjqnJ%X&)+r=9J}M4Y$pbO3a*<;ed1|Hd0cK)0ygZ_+b-rsv6~~+^Wj!z~xrCJE_mqhaDZWH80k|(i<aiqAhRQ_|WOXEq+b4Iav{nz9@G9g!BJyTZ{!K2}<?2xjE#EAJZj!ckfB6uy*6u<MLh`OwL3xX4Yskb15INaJBB-8P0mhlk9GciR{iAP_zywiz=R$(oMQfwxrPB;#k+DaeXwo63(Yg|X+t}pIX~}3uk&%2^sRQ<e%CNu_)jX=uOw@Ub?GTm1b`UhRB^xIr+83u1b4pWC!YPK4SyALq_>tmMnw-h%67f3)HcpcLbliXVf!mv-K)AxzRGuv@LdG_E*dpnZ{SL!bt!Q8Ou-$}wwzd%{=!xqND%GJW((ZU0BI0;eh+=RAsV0Ya;v(7reoHr2k<ry0swH%T!*QqjSu%_i*67rumYgeE=uR;wXuzsVSoAf$>grXL5mbR%^RF{^VJg#7A(W=l!-6TAdsTxDVa{uwBuakfsHm+liveU;VrA!Lo~kVUO|`}RD<UJf)+6Y<%gH{ChYwi6I(^1dPtp%__M*25d<YlxwnrgTN|mim&#30a&B`n5%VLmSoN5>9-r*dN(@V_)#fvuyjI^(Mjb-$$arrJ@XSoeOcj+=o3qu1c$gsxsrZZKQ(gPK~wkqkVRv}J<XVR55qSXim`S{?TMG^p7P9xaAiarZYl_e;EU@`_6mO({rCRO5&4|==0G@9MIwrGA&K}r2lw~=J2&;CT8(nOQQhj|I8bsc@^wUkiTIKm`#^cZ9_SA`nP)1=HN-s#-G%hfrVtAfjmMMO1jYVZjq^c7vd7wPXylUD6(6rxd~mEf(OHu-g~xLt@>2mjDyltaKCZe5Hoi1rU!2-Tf<iuYHc;SPP#@zMk(k^RafRdv9Te40RMBo6#8acmNW6RP@;7uj%yiuIjh?BIj%V;!>STcW^K8oX+4o^vN)yaO{m?k?O&MWfUP7g-sM3AQ3yo&0VL`-6fXFq7#hz|QietdA_VIxwqHIZsa8p{t-X$aGq?5z(wHu&A~v-&sQTd=-wytUO@=jTA&=G4BuLt2=z@k?tG_{A&LS&)>yTcl_|P;S)*iTeM2ld=lfv1;j5jlM!hRW6hNQR)B@9qbb-+`!+)IvCKXS)uEE!7H=CYa?hcrA?rHQTWZ7kJ&hwBkO+hFvMn)oW*&YMoBA2f2HR87<*rr{vkz<b5e($RFsLRSQ7%H@e`|=e=tYbU{kT(FZ)lC%Y4DTW=4eW^bxHYWPoYc;h3ud_u(K?gC{I2M)=}}%uggP}3Ga>uN@BlC$7RssI{i66ar)-iND#O*+79Lq62EU`fASrOwem1tM-v21NU_Z#G%8I=i4CK}9aW;lBx1YcQ?siF0o6n5xV><Pg#cIQ#KJtYnRr-X*fe_8lS0?nh!jvNvU!e?cVvZAWvoP5<=kO(0t1^67c90*GJ5%$nskj{x3s!agWQ{w$_nOHzvHm(Yl;9*p7q%3BYxfI;w6OtiXqV(UQ<{Fwai4ib-1U{zpIW`;wYo-IynT73jds(oJ}5{dwk}g1}I*mU~QL@T0n|Iy;X@QcqMAu;zf!kdavdW&=JS3-+s0US?T_siZ(ez>QGI|Yht9F49P%g=h<qQqkB2OoIbT%mo|di-D>$0kbSB+zFgv37ha3^W6rNd^_3ftqX5xt8-07#Y*0Cr>>In0rwbE|+?oiS1w{t7a4!`RV4_jRcqCtaJq%e!>4CclhF)cp#hTAlKPke8kpSm;Hu(y%ZNfv>kQ;wY;rjO&mS1OHMQg7ryCMPPa?O-b7{QX$Jl6vIF$-j(y_sKsb#uT7RbCzLK37vrn=(feJ3p=39X*hTDsv`~OZ$Sc3+<7fP=IN0Y@E(Zrpj6z)004*0+na6^l^@hLu|p#Fr%htv3+Z`ISEX};zmjNMw+?XLO-X#v-GhKF`sGCqsg$%nr#FxuJrV(;|fb(fR*S~eY#@oJ_+f>)Ol1GD$fYGEE)%_8t1)$C6o`I9YR6#%ja%;g?j~rpvdQeD$C!*b-WZi;ng@wr~3ns)SI3ds0L{YkQT=VIs-XTV%=kM#`z%>_;N`;ZokR;kb#H7$5g(>l>xOBIj*clnVjp$ES&r(IFnH>WTG=rbT#Sx!yU0G)N<g6#2>4in?M*MeGY;fp47|Rn>U9)iVm=mMAU#;y~pRVIrB5>PtCvpjyRe?W{kokLMW@4gb<Wvqx4CZWm*qLinQlE#y}=`Zc2b6Nx;hCO$&zNoY2W=RkGRT8g&(YSSy)kJ1=UUq>av)<SM~%KOVZ#W+YwDrB?DK9BC5NTzlo5Txx|8$m(`&(I;p&hTI)=P0rTU9<-C^QTnN8lsx6=E``0xZ4mcqb~izMTA1d%88+fL==f?O)5P2Hv(liEslKw{qH$H;|1a_O$!7")).decode())
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
