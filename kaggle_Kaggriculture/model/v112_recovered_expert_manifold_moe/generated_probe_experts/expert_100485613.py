"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqO^+nWk)HocpX=b?9<jGsvX&$?WD_$(HC9ApL1-!MLReDbQU`(He^+-`MufS$xw)B#XGUgJUWUc$?y8I@{L}2U*Z%h55C8qI|NiGc{pW{&`2F8L{Et8U<v;%TmoHy_`0aN;{`leZ%ZGpa!=L{3>z{r3@<0CYm;d$0zkd1p_aFZ8cmMn^zy0Ck&wux`pFX^N`1H%y@4o!6`~33z55N4?53e7RFTVcWA75X8{^c+J`t|#dzxnVIvu|Jiy<fil-EV&N>+in*@&`Zu^7Zw%<PR=BMEv~u?=Q)N{OV`_<#)eLe%Sg@zyI**^~ayS{jlGB{Nblxe*5b3<jWWE!D~Ny1JM1Wt4y=s`H#Q*)%QRDmoNYRr{8_U0Dj^2d%7Ox`|p1Cx?)Ox@RvXO%}?v=>-`1)^z~(@gueUf^@q2AT>OUh=U#pl@q>T%U7f`CD+)TqPh9@)a0bNNW5IYEQ+;o79gpBQ@gbLQZ~2&SBX#?9A|U0vD>-bxU_<`n$KT1{;pHFoA|PH~`O3E6HDn4>RMub6hJwt&U8ACWedWhPNVGrb@{dpiT|e>ip!jf*4_xE}ju`}dmxwlr&NZUB_HdSn*YCun^OFetaF_8nYSU(H$R0nt=+6xp>5ncCGuUyd_OtUx(5-Vv&qUsaLiz>uLq2~0{p-(u`j>xt{o$uyegCWf_U$F@{ba~G-tp1Ov5B3Q?u1j{M<Wg`V6Uhx&z%RiVo{cD7U`^A*M}YK${*Ra*_1!#?bC}k803c_pMLKLYa&C|<>H6@{D+UfC4b0e;U<3wcB}dE_4}_kIq<+=mn&?Uv#n*$*3S6p?#)=lP5!Ii9-p2%`FX$pV%R*(H4)kj;g3K4@ZG0>eEs2ve@3<o<l)vmJ=^9>cAQ^8KQ3pS@IUc2Hu~Cb%s)I!)@kPMo&W5<O-Z!3wYG0$)i3ut?vz8etG<1Yw>@3H+PSq~31aiJUF#6EEI?p-!*wb9b{E6Gqe6q?cCji#J-wGoNo;}I>MK!^&Rt#tjkC|U&!&t++Wz;4e6Z%*>pOvn&J?^O4Z6NbcHL1C=I#@itA@|*=lk4>1;-uMHr)=S-t>+w_+acywqVm@?!_G&47U7_BGulF*!OJeK*QLIvwz)rYylUH>+Zk1$Jn<078|i_pTmAo`zfhVZXR;&Jq~1n%D!!v`Y_c6_=UT}5L-3+0vXRj?6G_x%suw9vs~>uScyH{W{0(RdK|dc#=NHNfA;YcYfoN(^W`6iE;97yjQr{N>-4}NuViPWE`pM+k=lI*?bLZL=^j|+$+a(|_`4teEB}L{H|TH4w6DWBdFu5CS7T~xMybj4@@t9E;SRWK4sBiGyKd58ud9VlMO%7bpal6~@C|Pt5`8^Anune@LY>ma%^D<`+sqY^r(4-vAukm@d8qPmf~^Z($`It-$A|)5{t-F}1V1O=uY7eAMh+U^^3j*?!~KrfujO}ayC)R>!n~9A=Np(2^q0<!oPQi3zjci}edi;I?)$wDMQM$$^=8IDMNd4RmLK-K9k}u$t8n$ZdvtxgoIttlSO3DO@Wpyy!4zSfeZBQg*R^~7qH>=u{~`uKbnIDw(t75@VjB{u%&<%OEP^cz`5pPcZhqCFV_<#yb-3(LTU61Y%C_=>@|{|g#xIXQYXoKc6v(&uLXp0}4f-8~wL}Zz`okwLJdI4{FeNye2|of#r1I`ZKYpq1$w#8O;*;+R7_y^KJ(;6EDQEeC4SvYIr99+iSW-%QhH9Q?wxbCh(%4(I!47mF7h~*O9eD`+6!xilFzY;`RgNR{9c-5r1}mMYr<ORI4LT~8XxgWbAHOV4q4q3!q^hyuEI&;uQn-AWV!x{A`)I*vbtMYSFglW+!D8Kc0S79Suf!)=Ig{iqX;X{wlp+=~FU8QuX0KGM+DC(*zxny_2x0M6`6|=b<z#V+bp<5OuB`La8w&#hLFC&j&l2@|8vGzh9VfPlE6Too1L#|yszlZl>U_D6{rrRQa6`^1;%zn8ymJ25ZVi1upQs%oeo=je?Oz(+(jnyUm&F+b-|iJ%l*`p9A!+Tyvu0cK_)NyLk>Al#?Uv3{cboIM!FNUTxvvZxxn;nU#A~tk7Jt7-23Ssc<jhchik*c&+dp5IOzb3>F9EyD60wz&TxZ@s9-~;XSWu9&4fcqYsn@LLp`>iJQ%ps*Ri6HZWkBVEQVtj_7J8dORC(;?n`Mot?c9q07VHBx-z{fMRc=`I3!MD5QbP<`8=CS!e$1^W!$qaO1qo(iJ*2MXf><=U9nv>rq#mn?^mLBs*F3CG6_{<GsDFJde?F2o!Ss&B8a{TFM9(^v&)T;pl9`9@MVLx)G#5i;L}QmIUgZ?2Tdj&dQs9lV4O%lGu*0AZw#|%Tvlg{J=8?L_<_oEwUTml87aJDxg4^`SZ6uly*DnAeYzQJVNQDH)iOaR;9lkwVBfu?eDK{eIlv8G7yH4oLxE;3ZGXGvP2v5vb^8Ac!8lr4QZK?_mSgmNc<ZjOMf!L9g=ojxJ8IkhT(Dl&e@LS(141FRus;<fw<kzv^VC8RC@+!?IXSt=(;r!xgf@*Pkra&3ZL~dNv;k2V3tGG{L$9Zx=Xr4&Rkv(9pmxq}SKMv#|g#2Kh`bYGOkqw0t@9il>Mr1?CX^hk>iKHS+`35$|w!2O}fG-j5()pCi&?z%txgbcULLz<Tdh%PiYG<FJSvkzgpl>c3lE)3GVw9>Ri1<+QPe3t1geX`9m|3jX$%Fotd`VT;RBS%MG+ZfO%lz5TyGpoREp~(cMf98On}V+zz>qQ0@(!~ucGb%RmON?yPUN1_xG<pK<fZ+Z6An2mBIg<M8qu@n@+B}UF8)8+lV~LrH!no7l~A_bK2&0_7am=)m_A#)LmVvmhx+xO{QOtHK+m1BaftsC3`2Xr-Y;b*9eWtTC*4qQu_kL-pj0kJrA`{TZ1StVSPKMRwt!qaB%uacjmOsXH*X*k808CSRT5CS4`f~KshXn#<%B3na#H8~Qe;si53oIj4y2Y9T@5=7YI&g?_G-x2HnrX2*^=0rWS&v`!m&nplZ9DECZlzOg7TqEgowtG*&j}uc7&L`Tp-FryZb{)3Pk9l?B;DqS9Wjyr>!0Soj?>r-Hmv6seTtwej)D8<O;Kwg_Tz#)bBrtWTaiEz*hoJtcnYZHw5Wb&Qc00@}cVT3SPw$^9A-q2y|Pfz$y9Qe${u#$37KVf!aLG@``f{&2w+;nK<W=xrUd@sj}-b%`P`YxYM7z72oC5`1FOHTc-uAK#?!)LJp6tmFlw21kM4ZIENvK)~6usO)J$>)Fr?CygUUgyF!S{F&2UYwvwi&{D-PLLt+Uv5ijFo(slEDQn-!j%MLst{4mVhpnIifH+4g8P6;g5R^HE0s@oeZKPovDsPqdg<9O-%^sTATpou&*@dYtI2DxOHy8=@LOudWx%n=<BT9?N1E>t>lH3v1poci$1u|riolABTC0Y(W5urMU~$U6=Y<tYa}B$QJD8}rCI#Hzl8ds*!~-Iwb_jzx$Q0=0T!{}2g6VWpgvow_}x<(oBCq{56;%M_Tq>k}AL6P^2LWE@G*wnUxPip}!%h_`j*+3-VcvL-amDd=~_omthV!bHQwLP{2Ou#7GkrGCxzt*x81Sw5%CHE<j%$}s32S<2C2BR$LGM!qV##r8lV+OqzPVvX+#B=HmoU*6vjAAh?1TcWWn-m<o_DJ@j}?jRKvn<5uVVgqP_=L#NbO@{h*=0;G998>J`A3<f;Ar{fEiE5GwSIQT$c_3T1QqFpIFpSL5Vv&NL=SJQQ8Q`lv6+39wsy`xUAzdTY1i&`OLH1>2<&add@Nco?+m<-{bLNn=2Cq1IT;5`P?v%|@!9V8Aq_}@3(Kko&D_|NC6tgFO?snR4NMkm*Sag=y=->^s{9)Bfc+n}5k{Of160}3~<wIT$8LfF&{x!kT(X=KJZTyLR2IO1lu%e@+{9VX*Uw4br1n`luholRUsoO4s2WwZ&nP9?0p`g%#dQ5tCp_dH=0zU@MNVw6bJmNF~Cr-7cK_xFEacAMi%y?O5s$w5Gsg~E$TEx4&t0+mRo{Wu^Y70s?i~3{<Tuyl(T%^Xs3Z;rqhP)9(?^J2Q+9!r4E-7WSzW5B=HrU>VYaLv>EfT0mb$hWQJ`OS1nqGOOBxe5H(;Bl(>XOPRPSH$<XI<?PC}ZQMR+-@)C4C!Re$U8FuU^)~v8!!hm&fJY?c#FWQVza+s}cBQ$Aj1<?DgOrqjh&VqN#0_dJLhNZv9jD8R7Jl)6nuJsb4RzoC<YQEe`{fjREs|+E!)hdM-?f1<Imh0hJNw+8VbH{YFW$^vzwAR7P+ja-zTtH4jNO9)3gI(^YLdjA8SMy7QuiZ|!R#=l(kJW>#bTk>zeJfnlqKSat=S`eQsv^-b$|(Ws!nZWrv1SUUuT^yQy-i|#7tDi<4C<bl8T+WmktR>OX20dF@(Zc@mrCr2qmZBwFP>0YsG9`)2C1i6ffLjp~s+4WX0y+?4tWM&m+5f;R?!RbB=G9A>ljP?-Y-ipY<$tX~vH!I{u%XWI;_&oEDuaw4vY7Fz~wQ5SjbEeoQ?4sMwRHeVJT@%E*zpszTw!t9M<@j7MZ4dVHMU}T;;ysBP761BI-~Sg>Hl&5#$~b-bdtzPqr7f7*x4!aal<%PYghWAIF<Qp8kv>psgvK<+D2qsyK-({yVWTlrt3w1QYO(*G+{zAFO*c?^D1y;0i4p_QR(n_~i{)2Q3m*?n?KArb3A_Ik@!~jI0z)Sfsd@+GjM&VQ@DwiG*asE28dTg!6-jZWLd@J`ZJ7Fz!<7D{%q*>_JT@D^ez*#SRA-SxiCLf1Au-|o{_=0tFJ&WzBh*}y#~t}2+3weajLg3`!)ewIR&<bYXI8G7`1D<B3`#^yeV$ezZdkPv>0!nCtYzYtpJCQJ)CxsNP=@#uFBnUXU(UyGhEH1NVT5~Wz4WKgtCcu}AeTf0YBloFYw}6^DqsqMy0uUCogG1yYR+x`yazV%+1bWGEN9K?#}&VeW=Ih0iB;-W_zs+$EE`fj*&GdfA_vV#PPkp<V32pJYc~dHRUb7>_RGKx_9uqdZ-9#e#^KWTXC1?gwaZJQ9OJ^gd&CtoZ33^jhVc?(x1SmoE#Ue0a4wzAmr^fBF4M)x%oF8>`)}^7u~z-u?27~$WFRgJbckVKx2>`epPa^YkbxuK?>(5e<|cU=BV#yZDw&!6CX#lIeivlD8dJC-%YO53!E_l;qb&tK)YI%Uq41HPG6*XG^3GmsZXpP-@zo~W#@`@MR;rOQh`bS0BhS|-)faY-yJn?5cB2H8mNrTyYL$UhI|P+U$_`sZ&Fn3MtX8Pptr0h;R)lX7NhjD8C@~WfUZ_tb=<*APVYxV7!wrk<ZNuwlik+pJIwbtlD~ZoOD-uZsK$r;`atl$C?T#PSp(-QDEMh~Ph!1mqD2+Tp@HK%lnGN6HijMqX%L7x-B=Do-D6A-z9QmS=kGn$+hG|Wl$iJ8dj$P`J2Vkn=TA~@=f=Fmu*Dp$M<ML`<x(wA_YRd3Z`Ero1j>yKV8KxkM?TY?<Kb1EXhm(Ou%8g2#O2~*8rP>*Zs=cpj9O`XQTgDiukrWGSNL?&Bqd5V)4&PC>0W(&nL?lzYoOS6s9xANdy3}!Ouz8~iPcxWNr9EX0h4f5VLBTJs!j?Gs_o`%w1WfxD&$iK)IV4xtaw6(13t7~zAJkB-2ffgTs4ZS(+XSL8iL3VEwcqZ!?$3M5k)VH79?&4}E#%Xr?~XN~UaHac7sT!<-<-@2@eptnDZ(CFB8X~*4XF!UZBSNc93_}blJMBZRbF$-hycfye6NVE=UPX9MH%!nrV_&*jjC*HZa>X1@oT%fV;S);#CNKX)3@CsVHwH<X&Xf8LLiPui^O(iA8fL~k{(CYd|>r+CZ%`Cb-6LD$gU)`&l3{rZk}k~MpS)OW~3^R?L^p2jiP|ZV`~xGj%Rl`jp}!Zvt1CjHEs5YVqSo#7H%vL^d&w=T?MNfRQnEPDhtZe>5<G7_USjv_eP)k#JyLLQBSXW$fKo;rqs8-5rHawmdeVeRwSBnQX;Yt?aNq}>L#Akl4G;_$aKLPmQ+DSC}o6=44`61gJy&J^6iwOa-s;3K8_&4ik{8w%$_-D6v?(Db(R^-Bbq$F6pgH??<~W=Ll1_G)m}XqBLaD4I~}P6MjYPq<eF1cz18<gv0AK@8K8$pG7UvPb-(7FAqu1P@8Wa1JbzJrnhvQL`_PX5MV_^jpn9X(OR5(9q--<EE`IXb<ef6IS4JEveYlQ`HXgg41ifac^B|oe;F|5SBb=&Ot^zY8Jq>r{WE>ppFOMPTD*8279KEyKKyx9$3X90N8b2n&dn&R=+nzfa>oCBLYZG~e&gif4`?pK%Q`N3m%<dDsfn}NV%rh1i(KI8S&6^A=cd>Rzj!?oN0WZ4QMWbPC8UB&wtH$i2*bsXaNNG5`j$!3?%8)1B`jtF5SIwTtCcBK3CV%d-rCS1DE&6WW(SoD(DJc^rI%!zFhlv8>_3(wkt-BdbH|eu1(?|#`kIaN7sro`%o)%BUs5})Lg3XeS^;qbk{Jf+YG9`dv@E?S<9_`qYiPgU%hW_x*Muf4I)T~+Raa1nQbcNww(H0d(5_T?Q^(nh)H!`-$<8^G*rOP>qC7zc(2dhQgZa*4sYb3ImlNHe`k1fOzeY`hK^K3~+jO4+AF2AL!ix%5mrQw-<)gh0w!M%3nL6-LARm;RAyh%XzW#Xwx@i-B4D(LH)vo~$8DcM==g~~d+nYOyDJm?|hTe1c+4#>G3GlXO!RSMb5i1fz7=M?^3e!d~}tONADm!-UHD1F)qXDd8Qp{oFO5~R*heCkz|hp>2;F_kH|Je~oXAP&`9k(#wWytqzj$ikIs)En$FGY_QOjlj2wdMe6`hPoZY1t{=qMpzF?W>c_Z%lgrg2V@%YiypGFUm&-Qn#haHz#*TVCqijfyf7pbrdha7eLV6`$WOvCV&$bBGbZ+Kw?-omwDL$-qi(%6Jxaw|6-BQM#<D`HgxeGy-S5a7l&`RKK4*O%xCdoFt2wV*=^I`hiL7w)o{A**1ib2@=eqklGYVwzV?ib6*kXjf_r5?FsiKfY^SJIu^g$xk!1&G(7`7Usl_pFx>oF!`<TZ!5C%`mkHD$)_Oii31y38@i@Ia$xfMs>vZqUT=*xFNUhTqlO{>{7!N9OzJj^%w~ck^K?+FDLB4AlqUgBtrN<R9`3>&X-ZQ-V&fu;_TFd{>wQM^Jp!mXx!v#ih6huK_}WE3`2bsGMkAV>lBSquC$I<NDxJoz}-$ca;KKmPHaZ_Bkf<U9BfD-9cH_M%odgkua)7+NW3HJzqOcHDdX2Y{@M?mdIknWiBA^sHS{sUsdRZim0Y7mn+o%N79Ipws8>%o)AG(b4TX(VG%~Jv3pi=_{V3ClL@8RB5vl+SW(UK46w?n;<~j{&E=X{{c6%bfhi;LoVHu%NH~tSyUuVV`7(W5f9(w^gJ_rtQau=}D;oDqW*KIK<os^ExrTuv`Lns(kR36RkR^bp%A#D+>eYb6;oc)-P9XX#LnAN*Qx*@hnm;lv#9D<2%YyJCs^_e|YhhLIql?JuwqH$oS+DPy9r`Dx8J5FJxcZ`Uyhg=TJ2SSonBnCIdRzF_>PASlzrb*;&+HO8ca&${mX}lQ(TJ}&$s*l-Nk@Whf;M@z>bkt4Gyc%b_0*GBE{<hI9TPty#uwr@Dmq0S8#;w;$cP8}vA!YNsyf_Pc*dGt?cyHZ5Nub~G8#pQgV?-|VO{Qa?X{Tc;DS76pX#ll@5E72iXOr^o)h}pBV?neb~9E<ygJ6(*C%X4+Z-UNtd^-Fktq_$T)klam$wY0=T_a-z4mbO;_m8)=S$ogQZ;TTQv6?kV%T5xo(ix<SQ4*nJou+RCp5m?jaP+9rl-))n1)(8L*IxLZOu~#yK27SzP_{WT5#xM5uhA7DLWRze2Los8>O~Hbj%|j1N{;>URQPIX`tO9gBkU!T;90CIiiN6-F~3iK|rwU7=eP0jN@b4%64rav7_~<N=4HNi>kDCp88FniYK%Va_xY#?Fla<uVnoeDutt3e6$Yc%p6B~Hx+fDbPpVyvoZmkIEr?afSze;TRGu6+beL~6~?1B3|aMbpGg^hv_=ASw63iEJUfnqEGZo0zCbw{Ape9_c-7pQDpg&QctXpJx&A98ohVJW)Bz6>V3%!<RT3*yvb$M)E7M$yGYJ9*vZ5^gxxcME{>rgv+bgfatP$N7nvPHr!N$;MSHjhUG@LYF_sFj&_bY><CJVxo;pi;yaIho2gOW9=S%1Zmjj<id`4JCV8bd|N=xa!0t7wcST$nI_-oL?>w-1_p%e1YUVC%8tL!twgVJ#!bM>UgNq**aplq{Fb8C)_~4mHxKVhJ9U_d-Pf(3&ZoZ7fIy9U51ri<3#oDX)`op(o=M9TB3s-mE*iLRZqk<bl2&eD6{PML~a`Rvv_%ETE3{BCE9_1sH7Q7M-W&RWh|kYk7g3y1n?R$S8H{VYcn;>Ecs-pQ*ts&ELsFo=+SPXe78-yZ$hh2mzJdH6y3A34djcKtyV2RzGPwQ+I=78opH|plroi`5w{q16`L}kK-V(bbaPV;*Bfb`}~eu08rW9Y7~SGfu1BB`+jM&OjZtwF09qJbo6hTVj+93w1i*OV6!~qkz<97cHoBxzHh@=_oYT<DI34g;=UEUK_)k{v9+y-NRc_`n!`?Zbj)JL>5>lQu-^`^6sHzQs~?nG6Pj5H&@lEQ<D=p^-IxdHEskpnNyQVoj><cPn&>@jPy3X9(=|a|P35tPrs<4XMDG$+85oiPzsO#A^QqQCrg~MypB?MLz`dy=hl0&cr5K`RF)<NQVO|@^z-qZlq6Od0Zkn%*CJfD9t-L^S;^t!*Z#A|5+3lA~IX3g!>oAP5nO;X6<1fQa3!|%bEoxTx1S4aJ<Q0<MVntph<b(2C4Dws5nAX9c%%*PzVZ{PK4G3OD(IkO^*Y7|6hE*4eB^w(4WRzJVc@QLIwA>&+Qe@#q-RzLdK6Qwq2fl2E(-nC^a8x9ZAl%pmvC{4F`ho-5^;a2=y_w-l-|BqE>9*O>B<EGDJZ8+oD<qLk#VC=C4P|rqDHkFmqd#l0Fx0wI?`Q;JDmFZ&yJ%a<+IX=NQ+>|)MQ&>-7!~UbMwW__4Yyq&YdkzH_&AMA`$L~)vPbvI0viQUvdAstp*wt5_L=In199|qmZ9*H8;g{B!SbjmY*ipKftBe5`89`B0$#4vB;z^PRta)dYAm0dUSFX`ID+fNBPg2O9WN&h@zC&iqrV!dJ8ko&6o8n3m#f+5ZkVzdYsc^{gID|y#1b}k4qk>oC2OCl$JMCSra6vj1s_=eCUfFv`QYs@QlvcXC_DaEdI$SndmQuCcE~2f*X2>icS@=9Z3OL?+#wr!W3$GmA=Qn7Q)@@o15vWOiny#g2^u%xws#=os<gL>8v0E9cEYSnBEmtg03o6~&F)u?ZJz1_!i-{ZmP`5|$Di??9q`6y_3I9vSdavhguS+_O{x5(A$yJ28ufKcr-&{wyxi+3r#4O+gx98UKwAKOXi~yCbl)#pk|yCfTzviZk9zE4L;JlWEg(o^JMx{DO(V+KG4p98G2$0qCiLl0$E{X%%)m|4x~->jBaq+Wgi3X*E33I>9qp%ANw|y`=@`+4wds6EWjMP#gbI(PJgcsTTUhZY<z_9Yr=4%$f7dRIBF?V7POa6a=~F)mit_dpcy@Z!k&)q+*paNDsfZV_+I{|Dr&}_}-DY<6N;W~}MpqV`wyS0cYt7n#==1<bo~G|w(3G@&dKLBb-4{veF_^2bkF5?Wq;jXvL=M?P$wmaEg-?g)qLIu`A`)1cr4?^7mIlAAkwb>L?RS!Eb)co~A*o@{xTACT(sGovLJO4BI~DmHViJecO7krZkjo_zernmO;lp1I_Ku^%$IM$ZPh?c9%N_N7Oq!y`+ssiC6Kq0q>U9U2#<41D&<H>o^=*&Ry>4)nx(A6<aTH%WC2#ear(>6O9LwIWe8RegAJfmb`l-3Kg00gwqOd7K6I653T+_+4PlGRU5_rP3dur3|Rm**h86e|SJ5=V=J9dMk3ouPj)n?7w?M;R~H-I2-F!s9ojd6MVB$ZoG6)NRD*!0G$8a8lb1wz9@r#6Y@vA4ZVQi<Dqo@rtQ<C@DztZz(8cJHq^$Mv*RZRKMNMRGgPRX)wtI;<9-u623h1@rcc4h1H2{CCkPK&7v`h2~;MC)Rd6yP>$C;5Qppkdh2^e#OpytyCnuZJ`gxC#M#bnp3em5?;m#G3WDEFq2aHkfp`_ZChDZbbKK!GZap}yOwOJLz_v>UP<DCS^p(hGu5^%_qj{xDYF9?d?oicLR^2`068;q_9#bEYw|E;bo-mUB5^%N)KzZyhUj%#6KQa>S9Zg4?!(EqAT8_e$`-woM*@y<AX7Gv2kdNF42wj_b$>5dxdNZpZ<ON~A$xrCu7X5t=tP#(;(}pe$C5c??hM?PwvGA$v^)r@d@UBsGD_1IKW{1{sbDK{{-I7uS$uG(X%I5Dsivo-XWl1PGu!6J4wMoQb47e%x-O&ZBQnfs4P6=hBjcEKhLagC<dmBZ7fl`!Oe}ARS1jag_n%=Hwlu_QS}bCF>5WxU<q@*_&)OH=2SlEfhim;!ly@?1mG-@%{f#g<cYkr+Ux#hG+%~**LMAn1q~d@y!FxLhYSM00dR$^igF33*S`ky;t+IRS6ESxB)36-q22L-=G(wMeRIgY3Y0Asu2$#IUQ$uhyWI1AMZW`)3U0W;V%e3}LprPZPWCbsRt_Wi-%Az7*R%Z#8V3=7O%n2w+?26F!f+|_%$;~+7M7plP@TEZI12>D}xKZn>B#LQCHNFy#-yDZ39cX65S_efWsEZUDmO8se=Zji+nl4wxr-5YzqEQJ`v&fStiX~$(eDg(1o|dW)TS(vN;#{&F6rpZH{t{>I*Q6G24_H<o&9%qNZgH*CJ71zrIWaYwVRBD|R@UpgykuZED8gNfYNst1YnOqUvapd~&09ucxL(A(N}FO_?UAE$;x$!Dbb;$;QCSwJ%3gAPln}eIZwuGTw~PzLmXC;ZbLYL{YP`NVu_jh0s?%!pjtQ%Y9uLHSzl@I`KK`_n*dq>Ven+W!#cF!62OH%L#<FFr{_y5dcb#FZ@-|Jz?;3FtSxu^-uC_ncwd`@1;ni*ii#{S(1tWcv=#Cm>?r;2jH^Krav@_Et@RtzpJ5JLDo<m&dmQ*ymG7>@=@O1Paazh~0d+rl2H0~UvFo<mVQ8xh^DR3l{1W5K;&~39GZv$_Rt)s&`m3_WSqgpz;Q)af=vQ^H}s5G}OzauD+7Pq*i&FrYjhahTO|4YiSc1=kt012Lk7i-}UX5K}!=EF&=i=-96#cSztUu?WVo>S@&8$RAkX<4U!qC{ih=ZHPnuu}T&cDfZK*-?$1IhhcYX}MaEB?X`R90D;#eIBkCyj^C`@n#}GBE#=(+xv+V1TVKF>b8T_b28SZsj4BKu4FbSlTx?Z@$|MD*sQP0+5A#My0$wZzCBY#u2k_t){?ZjrcISwe54~bWHPjw{^5s#SuLXI3THYcS=!R^ThWZkC{cZq$bFsiqvNJz$>D;>oqb;q+E2}1vFxIC-hRh=p>JzDva$QFzAaToTwBF5{*3$?)d8H<l@}lQ3>Sqq6Vc-81m28gvk|7Qv{dAh2^^$shd+=s>#;TcErwcGmex31+hkrlSlZm7U5?I^Uv=wD2X<SgdPQ)|J4OVw8|hwlYehOI#d@xtEtm1*L2=V&w-6ZGGNrHSa+z(YHxEFcq5J`yafPgaHED3|Iw^0^OqFDk$Aup0pz!tX=+;ad1<DKRc$(D8Hr?N<8ClsH7Xy~cb9V>!o^H)lAthlZPsirQr{o%!@-oRJDn)E3r9|sPZN%+s%*>Q~zH)qvg|DvmKzq6^lgdX{TTbdeCR)E5eU!Pqx;iwUP3wG%1#@0Hy3n&bB{QvRSiKeN?|6T@f!po4IP;KgWmpQ`PveXwyZaYYZFs3=q1EtIT=q7x?#&)s9tm+a9<^a4D%h=%sajRUWsj<+$!C$M19D53UVdv9dFhlDKg4x~S-wgr|GT<BGxASFYh?0fRfbZ^*Dbq{$O0&2uocq<^z}XF9e2dl$&EBIu6~$zwl}7_tRSzGP?)nS&Fd?aWt`xcor_7c((<h!>Q>A<xcN}FtEVv2W3^uVUIr<7Z{nNKvY{~{D+~pqYUIEkp4wfe#FUD%lXjWNyYbkI7^S`y*1wZ_)9S`4J0o2N@D(~E%M57vev|u4#W_Xpbl9YN5Nj2_j!?<=6!y}3S6<loI?`7`bL2+UjkG>uJcIsxjef~|fdV5&LJqI1bWi3$ZA#<VdU2Un^_APJq1AZ;i=>dFQFO{-PX(-Ek=u}+<Aud+tujbKN=IPGuLKHornMZ|Qn_i5N3Wv;8!A(sJsLVK(%On{ts{5G6-=})`DH`EwZk9Mw8M6kY_g?df8EtUp3*-eivwlH@JT+7d)h8l4!S7Ua#3S07BVej65grR$9nQwSNo1;eTSdfYaJrEhM3fHz|(IQ#l)n5LF94%%52umm8DVR;#z)FWVVOa7QTu!#v*&SawOu1s!1X*q$1JW@EqB7=(V%p*|18WCz(tT@#JKw1gTzAJ6@}!6BG4sSyrsx^r{M{o*vL>;Ety>q=K%<d&&M%4`$QgTo<Ow))G3SeSn0pxf*lCaU5U9b}rfU>oBOiD5VBxi7IMCr%Sfjutz5SR|KM^SAlUz%kX26DxW-azHl%!?D513;4-J{+IJsr7gMULSrkxkeQ5-F#z8xA*-1lXLWUqXc5n>g_iY9zUGdBGJf+0y{M=qEV#;)$;WvV>&X&3TshbK9aY(2wQ__O9ZDy>`o1^$EyQ4yNk}yYndFHJTo{2G@Xw_0nHdg<FyCl;NtNVLpizIG6<B4fZNx2BN)|gLY2ajMHIDTm&M*>7zDWZ=~i71IeELq)<?Y%eIAtmYLHJU7-!hU$4w2660rGyz|lX;&0g(bVhUrcv|gO^q3@2JfI=!N0KeZ^6Gj)FD_P9IdIWHah791FFo>iQV5%xXd521M04QYE2Cz^L6*(ugY_$+?Vlt{|GGAWyUYS<6?HdX=jup5hk<3r72nrJej+>&IqzM%LwlWeIZgFOvfVn+u){m~womIsVkO?>C}rETk6#7}6nMG?y5Id`jaGuAl$@<!Al%4}bZefBfs$5Bj$c|MBNP{qg^O_y?<$T0j4nul~>f{lmZh<qv=Q`j_;}hyVTO|NQsA{`;T*^zGT)*R0CRhyVQJAHV+Hzb(J->%V%_tbP3oe7LXw_ot7){_dxb-@bg~`VZ>wUw*{D{qbM3pYXGfpT7O?>o0!s?SH}B`TBo<@$uu2ui3Bq_GsUJ=PzGhf6M&smtfMDkMZ?QULeG<B5+LvFTeNS{_DOi0{+{7+h`)=!}+VBag5)t^$0fbzmLI2^|R5Fh>g9lv8Q4)k3nO<;V@4$H8fg)CcIxXwt>dK7c>T-ahJ*U?$KC)MhVck_lm|g(b)Ha#vo|)6U~Ok4oBn8hQ<z?Q1-FWm~Uuofkr>kKr~u_#=KuNW&j%V_-OQ%M$L)Pn8Bk)KmHE2ps@greeY=O1&v!*oF|$UjRR<$0F8dXXhsCiPk=@hXv`B0L}Q1eQTL7J{23=4!EFf~J3l;1z^w#qN6PKVBu}+H{y1?1nAjxI_GGf{w@a?XzI!J5(cV6pfSceFu{2L6-;QN(WXy%klgU>mZy^=^jfsBuOiaP#IZjF@&owq@^4xbYCeJgQeKJAAu}>yg*l1(&yzkr*6MbzaQFaL&55?W#K+#etdj0PipxBX6)G#O=vI9E~N<^U;ZEi<J-(On2GE{C!#oQm2_@vS`Rt6_A9%p2z>2_(1#~B$yD!URHr=?=EjPRpVF+-@pWQLap+8&0A3p+AAj}OJ|g<?T+XQ_jELU}@IC%(QGcs!vzq0~avTRPA_p$vec-USr>gkn~a;}XGtLb;?h-k_*qvWtg?VhboI&Zh@qVgo|4PbfJQ{e*%+aZe~uDAic?dw`<-yM|&;1I3Ml5>O~soGm@qQ1MMF=Py{9D;Z;TyIhZcl#wB&lK%HerF4cHqb|6|U06!RtmaG|g1^&J(ZJtJEFnH66`Pq~m?ssKig{82MLo7JxO8GFn^l#5Qb~#v%!P`6Qn^sk{Z!O@prW2svKh2!BA-;YJ;+=LJ*mL7kGXvPq>_5WoSVvIx}dm|K$)IUhC_iNTK9x<cTn`T<8V68k4ME`JCg0f^sXn6e^TihEAKV)6YkloOdm8|x}exgla8|*xOG7>%%(2)55<mvl9seQp@7ujR_F8Xp=_qr=P_{`1jQtEK2IoXoJ~KWq)>E{B7FBy%)5c2d!VR+P{I?+y|scG2t_}k)OR2C-ff2L6G|<9zd&(MDA$By&H_a}p`@)>3<%6Vp@16XCzKV+W`wvvc^>mGP!xb-o=|jB+H;QX2~8+>n&lZ-`DH3af@&*>3mti$m*V>(Q1<@DipHe|GEBL<8*I<gk@j#W#bnV2U@vP__XL>Y08Du^8yNrZ$O4=d6YOtOwm>ycOnA#1*y^RDHsq|Bax<e;)UBVG@WwbxMSx!a`@~dWQUFs|;lvp+83rcx#AKS2PK-&vJ51(@35Gznea(Pzbe=+;otSKLKGGmOZ%$RYvm4WPHG#)VvzG0jqeO5wCWq*_wy)hu>PrV<%CEjQ!DP;gNsBPK%u5A^P|i{BuiY+8m=VwRU%T3i9D+$-9h3J%IgPLy@%K2KoCyO#xif&O7=w-FBn<TWhZ#__dU8thP^!gga4zm~7zA}>D$d`ZWVLcM>f*FjVWkPDG2`iAPJRR@mlb9$c_)8qhhZO|lN-ayCbe2=%E>-CRm!(EPP*r?eR573aMDjs=pEN)N#2E%>Ji?boRdmq#OBGV5;G||*-H=8({j>Q_mQ$${CgpF+7)UKD42HY1f{i<ls+oJ<do?+Y%ZkK-H;kNrf}7%F;RD%58eqXlPu_BQl=oa$#>+@I58=YlQLH)rPbs*P%Tn01<bW|mmT{kR3lfaN(Yd6HeKg)3uc}@87e%0P$y-GMIDlIw<V<>k<=R<5AJ;a45a3rpgaiP!3%M?w84J+`m~_FtmsxmDgaUo9rNw$ud91JjFh@NQgJM)cw$iY2}%yifK{psRCq{Gs=4o77lOO~=8xAr1uNS72j}f3DJOFjC#yToNN=11$lHa}aGLjFDhmtaH%#V&sVlvCMobn+2)6@(0ZX?yHt-%WO(4}0`;x$Sh-n&w$pB1tFQ)izFzG#*!bvf0-TpRAZ)=n8iSV8glK~0wH%w+PCjX8w*?vs!w3t+Z$$Z14PK`;MK2BeU&<qOd7EX46<3|T4b#I(3$fA^-{18t5p*aQ6R?q-WZ$+8Yg_C=70_D$dX_Ofhua4y84&@YvaMB1THJFn<F{gPTCvzw#e+5q4`ZSW0J^?4Q$_c-+**q@J&Z$~Thi`Ybf~j+PGJ`M;?6;-yY8GoO8x(9!y@ApfQ2Izv1IJSw%IR&cZJEqYPWt{h4IWT~K&eL@P=j-F>JC>QjdzCJR_Qn-CpW6C*>tSXQdcx_9keXS%wct_k59|&gXIhR&j?`I%(CH~!wN}rxGhTuD-pLi`J=;9BVpMJEIq76*y&(dpuv2?LSStkP7!$T=+#hvR7<gw!3qGDdcuORA_B`~uxww6;`v}r0G58j;=$T-cuVHWTm@D<3oLVirBPVs>P_z+9+n*p%byLF%3!%CEVvs6U?A!*0bv7_<WE@OoE1Rr-5VN+FRanNcMi)ZupEH3={v)~L+OcOxdfJd_{N@BhPC~vd&2UUv13SBW?1m=E?dT`$c`)9jE!GqQyVRN5?U2O$L!d&Ovc8q+2rjzXQ4Ikq-8I(97)TadTa%4ZkiM9I226RuhVnx$U?nvho-eSDCbRA_7wkmbKZP-T=<#50p<C`*ycR2W)B4}lO$B1(30KGBIg8`wGH$qfHv)9W(#I8jpK`)YIrhBd|2{ozRiea%NE8bvz3`anFWNIdooLy8Bm#JGaDCs5&S=yL1vo8%)WbOCSe9kwp_u?^f2>hWTt>QUdha6%;pm?ivyX#5+%q?fwcdV+3zn!CM{+rDMWei%v3Qq=L$3ZWQH&^fSFBftIS&V^qiZ^-1NW>bxtbkE$|Chm)e5o9-u%zqh#hlukj}{cs^SaW@@cWfy~^yU}mN`keNRjvr5gzerV9;DZCG8dh-0~X$WfZ^56GCEqYntF#zWfNG&98D_zt^UDWLjimGNlH5k^;srmb%cKy77o`J;T7M7wN6y|HRxO3@@Gh648d0+t}{QkqU^C-IzwluF+LUzz-)PeM+2MMO7?4uR_cUh(NJP4t_!g(wq=;Ai`z6u9K31H|!3VV1%tGn1yTzf5=>aJ+oY^*`6QVSaDL94e2vdY}q{QxurO4A3^N7GbjTA=EOG)*#c&qLD;qd8?g!7-W>_|A69dD4VCiCfbzFInqM3vM8KJp(Rv0gJ#?Mss=;nnuT&i_;c3=LDzA>I59Hck;j|B#Lpyhrv19$j9lxIcIa~vsIjC4f(kQr@l5$^T0Swa?G@ed_KjwSs|TvbSfpqx$V=?4cH|ob?84`;#7~1)1x?@+k-O#oN&rRoDtwuojAjz;Iz~1Yd9?t%Yj88u)(v-8mp&qMs=C~C&p<MAE(K1`eJn2#2qF-g7)IP=k&=AoaK!X;`E@sp#cv5d5QS+#JS;|5?QwaS4<DCMh59e`W2_YsElMd-I;MZa054Bnr}EYkTh5z15uYKo)o8j6rA2F--9zG(|N;bfTm4Xaq6?;3{hz=PLtr&*=}w@+!MASUM9Q$_MOw<oUee>fx;M<;B)}z+XxOjaOy|F>1SnSIAd{8Hw~P&z$p!Z++#hmLU~TwPcoh%D?Q%ovv8g+;TgK(o$67Brwr#-g}WR)Jp-r9aEgQR(?il!BuppG?~H<=%{62b35IBGsHDE_jZ)ta0MFnz>lkJ*BdwTT$dcR^%ubg?F+G^go~WIlL{znsV;xA<;ZS`HeNeZ>3r2<P1#<vGY^XqR3G!p0UZW<b8>&s9zU>`xJqtzv_3ghVQ5|~#I1v89RjBa}p;m4)ll7yZ8UQt}5u!!@?lbU43f12sR1<1Lbs9<4BvdV+8rHAh{?t?sJ5{RgVTP(4YDl0?S@o>BVBVn42~@NG9W8}wPYTs%Df2qi353y0sM94LCxWUUXHlKC-w$=GCB>kc^?oy5!1JJ5meBUtMYVRQn$#Yu^V)(cUQ)U>s_~3e<1nZeg*sg_k#WVQlFpWK6)5NnRNa88-vd+!pn3pRCs5y3gt;4Pczmc~o_#-5+kk38@4g(Wsz7y*1l6e8P&L=1>Oc!SNOdNt8WGj$4#f)5D<@@YNTxGbQ{CE}3}cFCF|~+kyhF8D4^s_N?9<9L0;W3I{2f?QRg<ZDc&1)(OvRYSb?*-eQ+P{t>+uyb)hA%;sslC3LVqdLu%7)rfT}J~4FT1hcA(0b+JdQHnYx5&STC<NrgjL^@Zd~Sg&fSpZR(GdsV13TyGzJ%3#u1HsB@Xzk}Rf}M!<AB8B<p~O=-=Cs#pC?DqPyWUqTHDRQ(PHY7bLWsFyZ*Sjp4_rZHh^-UHLU$@nWl_<G(OCYY%u<HJ-drXH7#AJr}PV1}j=KboeQ&(Ky_`79^zL81Ccum4%jFbvd$;InZuv)hAkOa8`+hHI<EI0T`(dxW+?=&~NFTWhq3M_5Z)c)u5+y&$xiM?#8FKRiOaBGkz!v_9@dXcB~*!?^;zJ<fnok3eXO9s`?xBajH~6JZUZ0SLEteFo|JtImor2D=-fP7rS8QR5LFn^)M**7+!$M<LWGLVFs7+73f#3xom0ydgrrM#RS;jE|1c76=1^&=v^wFofYA5yq$m2sO|FJ1}{-iL4Tf;SHfV0YWoZMq$wV5xQbW*6U8ae67zq3grkRg3tn$ss-!c6CqLgog##q^b(;N)}{D9*TP9@*>(b5!~(GIpFqPZh;WNkKm1x4YopNe5nA9C4ttd7?EA|u3=JOai6^p^g&C&ej*KBRpfbk}ix=JuAzmF|aD;A-vdDidS{Z7P<%DS_m$W!MD0^ZCB3utOa~g8hUWPDK5Qf4i>@E<JqcDgNZYuFP?I5j#>q|i841M7ab{7o8xM66v#W1E2gVEQ3=pJGq${@})hS5!TpAa56mZs`hQvTc-;af~duYt5kca~|xqL`4KO!8FmqodSSl+L<7l&~V$XT{m@oD5UO;S4BU73ItxmGwH;0It7r1!ogs=5p3~__K3mR8F(=qevP+G9=A9mylOH0ZFf_OC@wNm7|<M#(1j%Hi=r;g3y;e?V#*HiIrSOP#rw2!G8@*x3`-1CrY$>)mBid3rY=8F80P}ML8?bFt3xOzK~R)SS=)dK+i<dP4z)(_n_Qrs8W;>^qn%m?pdFDev46B6y=l@pT(rp>Jufid|DMK-=@4;yP+*@l;;zpoVAW)NXDYV@0=u^s}D-Q2j#TR@3dGlfMQ<<k_aallzJda15n0w4EhA62VN8oluVrfr5cE`Ea8n=WuyjLun81Ug%hKkjeOH7>vls{yQe{e&UiACj+oz37GQ%YO=8OjQEsi5LW0tqdVUK~TCh}F5J>YG%B4}UT4NuZPVb3w6-h+UZAB;bKN_IiY`T2XmdQST*tfP+S}(YOZ{j9b^jtEadUPooS4HpC#~+lonj`d)jS|KlZ6bSjSs|{u9LH6byEys$mY~$x(MBbe%{E&q?+B&71<Ekre<^dH8Yj?gp$ib8Kj$&d;@85b$Kk6jZdyAhJG}TrAd*{%r+u|uW+#4zoOLZCrj0UtNanubCaEuV_adZF*C(lFHSHy75RwLnWL;uC^ynn3xdZKYjmZc|ZYONm_t_*}y~4wj+|0s@L8%oVr72KOAhDmLG)0?ja{`ppaFPz>1~=P!1tL8L6uJ1-m-$H&t2MQV0jOVN4hB?Q`PGa0v?Pt4Mv;USyjxpheF;>kOOD~;7s~qXt=W5yucFKi)E7H&eL|G+rX(joQeF1#aU}goNcyA^ac=6Z5R!T@Nqe6pt#SP%4MGxHPpXxqxnq*T8kkxNM%!8QQCbqEZlY9=h0;iNZ#{?IBy~YDo!$y06&|1DHoa{|5}F=xNQR_M?hN#|8_5XHLE}m4I~kK1NjHm0+Ki+HO?y;g(`gHm^TU(WRg|+)(sK|*IjwoErI<fv_7eJJC~G8*3v7}BAsJUY<N!KJg~ZcDB{{>>keqjb%$-ea0n#QQ18{jV7jfiCLFy?Q8AxctvGm+DD?EEKEi#~a)E2GOC)jX|sSHV@g>xIGsa?_}cC!UtNKT;Vy}hie55M75s?%+-f-z~cEVWBghZfXyn#8qy(^tehB&lR1eTC%Y?M;)^n4g{5m8G^d5T5Sfl!5SGJwTHBaC{oa=fb?Jvf5{^(YDHUTyC|8r5#v$Ihv%)JhzvNUtXi`6EDW2NDlOYaid8>N)d>T^AhzXt9tDGHdjda7rVqzl1mxzR-q0v*5NRcBeO5H={;+^7o|;5<|XPdV?9P-hoSsh5_M}8N>0+v{bkiDNn4QAfTS5#p^lOaN0aoHFG8u4oPcs7X1C;!kTefP(n!YS7nFS@VIn3csQ}5CxLuxrWbL->eTaKenoIra);m>!iWrD;x*kfu1ErH)@+x;5KPmC3v?R(YGwO!<gDawRJ2a$Kl=^xoJ&N*eg3k#`mvvShS-={PMLAbUIz8<nxp|}1NKR)XsVgDc5QFMLX_JEB2^6Al!j!ay^0)%^;V9LJLD^4IX9fSaBk3QWWZI~yBxy;KY8Xj(pCps^S3Hs~BWW)r4Ol1*DD)pq(sqzk<4Eet@q9A;>b4q6b3v)WnbLscxdK)*S3_xUhB8)2&SB~yX+Vv-zK~SFILd%Re?55jMoF4$#CtW_@YE+HXC2KRlCB`RH9YXi<$Iiu$L&ZeGTxh#oF<98s|P)cYa|^wB&jt+XjY}lev;;3k~m7Ed=yUaNTSrBBp9N!15xS@l+!qr6-7@6$_Z5UV<;^My=j2bo&}}lpu9!0x`zXuZLR7bCfW_$=#+%B599`ZI7U~&sJ+$w)t7YE+9Fx&qsFA~5&%pRlf0cQ1E>rRNlkFx^w<q-x~)g=zJpjALE!<$67Re1i|)r;RPstJ^)>D(lf);_Xl3GFmKLzol^(us?HKd$ES;&2OXK=WtOLmXPYFwdvW!>L0o=p5>}R><x|VuDTWP}xZS(AtWx~=nS;nG6@_S&Z)ol7%`b*e5fMg-gaxum{0ZUscdo$jKAoF;`SVj;8-&iVy<<%0eH|#8^hOpFZmime;V+Tup3zkl4DNB>xX>^sPz6wh$%{AW)WyPJ#IBP>c$z|t(sn?RE1|+YQFr02i(z@!PjBXD~TcGs7a(&BoxhtcLhYv~#NmC(dswB6@!2bLsy_#htmtZWsB+l!FXPMqO$?NF>!to2GcUnqPlO!$Z0<dj1e(gQ;=p=3JgzhKh`cW>`nGmJPtdJbY8=e8>HYoi-k`qEwgSvH{CA+34NnpVoKrQA3Tzuk%q{{lz`%6q{obdTRNjibD!h*W$l4M9oT9BUIHmYy}lE4wN7?eV@`T)v-BS7hataJ&ZZ`#Q)u-2vnr5|`>)D@IbJF(-dEu!c%+SVFIKDPfJf-;P&Yls|@w@705Oipr0`Ks)xQ3;omP><Bo`f!Y@hS6(3rt}&*Mb(;GA2ufEfh<8_ELE7qsBC}nHB4g1r1(0ZU9Ase=?1c#Ybb-C`x^)^Iqb6fIsn@(=x=>yl+F%9Ie`?cy_oM9P;Kar+<Zr(1kKh{mXlHgSZ=j&DN7AfUDrJm`Xh#=-i^`{DD|Z_GXk|TL}|{8GR{F*R_H-7TmTi=OF{;sT#_(Lc;^%-!5*Ho^x+yTrwYq!#cbUTS!$f6Ro=S&Ea%Kjcxhm-fD7pog1in(dkvOGGAyl{CN&<VekhbyhSF3}YBdFE$&5+*Gj3&E(63@z0~0U-`(P-w1f`i>=tQZ(34AMfT~N*drCCwN6QFdVHY%et{V1nof;%w5w_bz+_%q)pO4VtykfAhAUZ)9By0v(C$;(V@39$ucuWBuSJp`q>LhW$863AG9bV(`a$w8`FzU9~g<OH%ZaRup<qPauY$$=m@5qV0|hS~Lm*z6^Tx&<?!*0dx!vflM(Bo!UYNJ&a;yIj&#!LA$5TWHb)na@HpPj%fVNq2LSHmMP@>va&;fhl1Av5+)i3?D?&U!SBiCQ230TL68&kc5g|o6T-m?K+=;q>VVq=#{XkbxKl`B%uPsUTTXEAvv&YScefLwUDF*B;83!Rt`av1*IWJrLJ3b!){>Ru&Qt{(0TL`6W2F{SeuoThwXQa0Ak2sg-Y#pNZ=j{bnfEmN!##zZo(2cDb4`0{b`2UXPIj^yfL#@hw`kgbslysGlD!}%=~d7Pn+<Bjjqk*?;OK(8rMy4s_}&8JQAK$#uJtfLkn@(c4lOc=7V|G$EWGzITt)F;OVkFHtcz=&%krK4NsNuRDh=$+^_jQdCq#WQl2)GF1t&|N66DAWrYvH(~jU7t+Ueo9rCmVPY3$imsxFf2~s{hPgftHVH8jUoQEM$eMX@1Ry_U6QzJa}FrM>Sa2gV4C~&Go5i|;CyhohTO|A#0xg@_fyKIP4C9@skw8L<QV^>c+&g)d-P-WPO#ifLE%Z<&TrKSSg`wZOM{p#?3e>}A)vKFs{(*c||!|4#5?uj#Zg011)E}JP%o#7nQxzybXXCN(#v%68!X^DqZlQ<o~sezp~R1{nbr`}NlCd29Q__5OldgDuYPC&yCXZu#h?N-C=O}};)p6l?mDb6^@F*qksQKCRIwNwshhT*jLfm0<oO;VO;SUoWGs-KLB_+pE2DsXI%px?kf<5VMXD(AEm=hlZ9I+Vjs?|Ri_<T%Hjl#a!@EuPu%^s|-n+`0{vT?j1j%a6%ySK#D1KN3$X7@js*;qdgpX~`E><t~ZH!y+C9PM!zhoUe{EXyb31BJZGJNJZ7xF(8<xcGK{NgoK|b^EgTJqcMUa`3z%-ooR9$mnHFT|LRI%O1<YUBSWfdNQ1KTm{fV$VLPpJO!WuHAf*qCvOO78)%GK`l}6<-TMk=on<ToKS|FbQsjW?X741l*u;=!IR0GHDaplTKBek_r8l&W9!_jm^66v_U(Zi93&VFhGh}wdvDSB{w;6|VeTX=J3qEn1L=W%->YBQosK^`QkfI0jf6ZM0LDmUMn=yV36z<@F(I;mOr5uGxkur;>^3E!0HIG0(JsM<l)jTxgOh}wkcv}S=ca7u-33{FneOr06EDeLMxfv%}AuZ9s-4@FeT)=@w2AQ~G)P1Z%;o`)##r!2;(>mh1^X%0-HFV(pvQ9YRGeC!a_gMm7b34&?#6sXO*(wc!lr(=Ptn*p7{oG)7)oE~V5)<}Wc%*`O(=;!rruP$Mc9O!%kpvKfj=sbtMU|tS1B0zoSx-k-H91K(q8KGWHl0qU_RX&3ZI#j{UYe4V1K*PNNP0UQZ){^_D1zEKj#6@(Hj9g-)DoGeCpbNQH5vsaIhOGf~P6w!;1rd_GiSm*R&ihom%k9%=2L9$E`h0wzroz)$%~m6oO{t;(iwEtD9H`F<Nh2e3)x!N7PIyz{8TkT*vR``YH1F2?lLOhikhIvcNAh%6XrP|%M^@|k@S^ip&$ieX8J=j#bqd1FF+6tF`AsRR%5ZZ0jD?h<Me^xxSU$bu0N&SR0|#p6(Lih2^t|sk>}PEU4$-55PS*j7SDwS>-)WA0TqXa}Kw|}{)wU04B!L>xDcAxN@I~}`<|!Y?<k6uY{ZeCI0yUSBd)^T`1gObO=@+1O6=9}8?GtFJOPENYDg$bO@Bb4h0W?qfY5-IrK$q0oX@Ppfzjdc};1gQUuP-9R4e0dfK!rSeRUUZ;9lHK6JRRUU9nVwUCr?xG)CEs{b)Mlad0Hp&KgxMVB-b0)6=31HRbicnX9zgY5Q6LDIahM$aXpomJk6?1I3zNn21bG7ex45DSyrIOHU5$EoY(l~lV@3i4)c;GshNg6Jt#qkJoS}IVXnfnQ3#XmN0ZV$MZPtjCb1B|CQoxKo~XTHShEx+;W?=gdU)CjPkZ6HdCASi`l%j^C)$+8xC&3F&0dd$lxG0FYCKp!xAXkDc&e1AwL5smq^KYAG;4@CuAYY5IsYiN;SGRB6@?}q5x69Tq&vk1Gy?DYMQrH7LI1IU;^&JA2RhH*Nr9?j=h0b$BVKkb9H>4Fs2k{bZ^i<(3DCS09Rgh>+kU+|>BB_uv9IDy(W#__Xiyqxxo(j=?*Tz~$=3DudwAO!T^n4m9^l@y=f`v0+EQd31FTQ8Y<VE3+jtr{4xohEUAKgKA6Y9SYr=KNI<)sVRzn>!t-^t1-6N2-C|RuTcS`_=fxWcvfULVF*}OBk0bb7~*?19!oSbZg{Rj4u-7=UuA*(>e_12LfT(5R@A6YYq>})KbtO4iqJgqr_nsuytbpqMqyC$oKkPS*HJ%;QI$U-A%myk8<1@vCY&i4V<WG&4t0IM2c^(nyG>w`6*%q3+0rUvwuo(4APo=?Qp7F;7}2^g}<)_2M^Kv#InsC~h>hIJuumnC51x@egq;Hr=0I(K2Mh;eFI<1D}my*M2xc@1mu9>cl~X^1u6Whr5Ov^oh^=i@G{+X$UOtN_CrKyZ2-)^IDVN<!7oUhSc}4bTb5nRT%SENkxO;W?%Sa0gZ2)zCmhH7H|bR3kz)WOi#hX%nHr(y&=cA4b*QV61v4TmdG8Y6J<W034XM<{K$hJIvE+5LMe=SkYK^tc=y^>-NT@n&v=#)>qF1ZOP)o<W{N{Q1t_Eu>Mw5@v{}4AqbO+eh<~nrU6pbfU3Sw4S?#nSk`E&Y7Es0I)loo8k8!GxhzHkA*<{5M^RN>RIP}r=Eq%2s-Z%4Ii3bUH3Ij6ak&C_E2{W!#}m+Dp0wdpHJ~SMt~X1m!n>;iW7rI)Y7eDa8><qkHi@y|RLw;R8P+{(p*pQMf{|3sp;YzEpn8kceg_7PIi!CbCXI^jS>mD=<`5pJ8~foHO%0<p;ky0U)5QKjSM-i`PwRn9YkqV)nbJ+!%ar~mt2l_M8p%`*XG&FbJK#3}Q_gN=viWGHa}BAHXl*%2H-(8tklJy+=!XweV(L$0`rW5Yw|;K{MC#p|vKzqE-0LtMf^<8!Yk+j|PE-J?ej=@RX`fL4etpsJ<VZC@Iz5q6NNv#)0V1_P7Cr&v=_gXOwtGg+2NwOFA(84QQW~ixkxt2_{E4(tkz7{HFA+@&>3p0#=l+q#0;wjEnt@2CQxe6><{?oBh|b6RPv0HUR_k^H(r{)~=tV%(9&12-BcgNI+r8a1i0aiy*&XXZJq-jJs}WKaM%5-mpj)js1nLI@^)~|=WI(534cv2}<^t3dKo2r^=mhG?uDQd2#-fFL4%8;5^Ya>wnulDPP6qTXM3**khs}Bnh%>{k+KX}4S%F65jP3&(KpS@hM&hPic1T}sdr>_e0@Ra0>%x$RkH1TZS}XCng}Q|RnogLc>HVUyafylWrgWN*N`<;UqK@vun*wzvL@7|4!CD$n&_LtyKw}?J(Fk?U+PlxOTM|U9&Q(KKedj}KR_D&KkHu&z7%g<T(1S3hR`Ygn8}~u-m)^N)hNH|=>#(ziP2>t@u=l{xDD{4nbf<9(GV0J?-d~P6c9=flXq1&5!_2{qL1`K&%`jQQ!6@Ba9hI>UWh77<1f?D)N4U>X*@F`A(rzw^bDt$9Q<Ub+D2)ImW!r5)_{;!7a2Sr#-6u+$7}8w_r5c<fKNzJ8I7+XksRyMcQECu3KOM?#RI1@9?ZsNo0{4mtDpb{AmB9&6(k<8_N>iY;=SOMh$@QVk6X6;-9xwGiYR%w`R23Y(R_fZQgl+7#IA2?$3@A!-Y}RHZN<Cc%rK_OaDy2e#(wqQg9E-BF-&a7}>HtcgptR>j>9iH2w5U^jigK%kcEeE~d<VC+QEBGRAlrsgUr_o2CA6DSm$mibQC26o(~*x7Z>z2@D8qXDPEne52aivbwT9{tr3M>LiPBxRpo37_Tdb8qa@)y!f6t(o`cmucQI!6&1)U(sR&g(n-b0a<7Pe8J!M3y1pWrCN+8X@fQC4c3zo0aVk5Xry=Vzd`FrXKGiqfv9%X6UgRg||a6W3!L-Wc*79RwcG(cAbyRpN(JtSoXNDuLfKMJp5uY+HQauievMjvJlWEd84G-&ZY~VRdsSR=iF;O=eqQR1yk}z>sXLIhd>3&($(osYBy;3yhs%vnD&R3jb)XmHjy=&{jl*74QFT3)gqp|9k1#G_DZ;hFFc{+!MTtqqxGNyzM+xay4te^#NS<v0QJ2)v&ORGa)qUPO(b79l1T$HNXn}^~Yn?^JuJg2-c)AIPWY#by~-;8h}+NE$s(jjmKiup*mdWF<fCSsj6~SC*wMe#cEktb=D_5tbKz=`R3|y8mxxEssL7f3#|S=u_j75Db@(o9T--%7W8R=RgJ`I4qjYqaREP1e6Dm^xdXnAG*|nGT$N}Q*oW0suzG-1gDO4+d=Z{l$=>X?=*`~3YQ|wz$6}2&tX@g6>LylwGpy5n4%XSvJyfwq?G}_q`$VIZQ`N($jyhkdv17H9YTXiH0+GR-YDlQ6C)M?M6#%7}P}M6{3#d+)zdx<&Pj&hJlj<fN3BZmcBvhe+lm~K=&7I=?P@TnXAfbgsP8Ft_7phx4VDa!7N7ap{YDQ3vHX1%vUHC|B(Udvy;@qeP&`E2dI&NL<IkB37SZkTA=x*J~-3&6--bj4)Ef7^v`-&GwG!NCw{SHX#8c92OuF}S{P2XWY-+{k>98WtGr%}UjI)>jnY~gOR*6!!VIk~wHCuQ{xv!WIx?(AXfrW%TK%PwnoC7cr|1GXT)1aX?P;G8NrCu2e%&IwH`!>Vcx+>N#l?e~Lo9zfIXplK^KVPqcCw1DRH9%u$V%V;heOPM}0Md>9h7hZbYpNpoxGR;uX)JgmGQ`4Mu=%YCoG&QgwzA8<1KQz^FnigERF`6prwEm>I&@|x2Q+l}PG!>w!2hyDH7N&AjKTKG(KHUuFbTCZoDlli|bwA9hfT<IhTjih{2r~|bImtxf)0I$edCCY-DuB{lP|m|phO?s#V2Zzu!4jo9Gs?;Fouyy}N15kca=0-=sX-rsF)00^C_z*+8<p0J!*G5*ucs(ANSSXaVaM4ALm6n%><mdxYEq_;WCQ}_jpWk#cmfR>w$r7$C*PTsq?aXdR+2U&8Kypx0ki_sz{n$JZf6V0`79)Tg`}OjNV*G21A1?35dDqoO$d_I_hjJHNzz!Hq;}r+k@O%D3rU8|trX5~a{`hTAB8U@<1UiAFeMG(zjoccxA}euNk@@Xq8+EwE&j{>8<cF`BGGNfc+b!6O6v*T_f>_1ho;Q;p5s0kqN~*W%n@!Ceo#;IT6((#O(Xs$6ct3xrZI`yUdXm$F)>fh^+U#r*8`FC_DPZT=HBIxgRDkEcGrPSRkD|<aG#W1yEU{~a|?Jh$hHF6`!Eu+X+YMX{@Sf4s+x7c*JH&aL7uB4IdUOe7UWogJORj?sX!pD^XGF6<Zi|h?UY_)ytGzQ1!KxnKfYVWxT*dGs$I;b+66M6Gse?}u_9`VPr^7V+s7EMg<tyomJ*v8Bs%R{9ZNF~kHxrlMxG_(*mpD56~>YDls}lU8Z?eO8JDK=GhnO>X9vhwUs?!4#&`h6pMmkDl(SOCreLg_j8($e0LE0!oP8|DdfYg!^<#G#W0e>$(~Q*_7}v(J4s$<atdzcFyrooa!FVDW>w9JF1mk#8MhoIXbX~nI82cvUd1S>>JeaW>#W)m<%L-cs7;C^7t`*aG#{O8wW*WyBuMM9P#<`ura<0%x#r<H$?oJucPWLg+#RRd+c&lk%7~7TZJg^pD+hZA5>|-WvRVU-T{d)j5F)3qc2Mrl-wfgbF7ze(q+z!GatIQ7|@}m-m4h!maYlMf0vGqL?R(|Rt?1~2Q9*|T>REQ!R?o;kA%niG0ZaDNDDbfb#27Dc}&IPcf&0Uu360yBQ)wYaqWv??9dQbXY9pqt_X{+JaK#H>n8*;$@u>hmDJ6!_|nnc{BjK2fJL}93QLN|D3zH&P-I@kv);XjySC3ZXMXeXI73`WamX>|uu@*yeTcY_<E_i*(Cxf);NI;%ZgVZPF4k_KC3;nSaR6j%KKTw(sq6n^}<6SrH_>BEZqkLGG`$yHal`Za_8Hkwb&b>>@~x43GQ>r@Cr7OD3TuA}3xQm$$QR|EE;GLNp<T+J})?C@CCAg)GB&I4_(rr<hPxaw1It$4@p=4#e_c}%!Mx3lfe??FUX-)Brp%GKYNs|8#g&?&teuFi<pS6kt#3$D80x;b;IyYh|h<yr~xnV=_r#}h7Ab-}8D6zob^^|4s}2&@{MJ#(x9l*Yka_jHLpZJEM(&1Ibz>+E-7Ek(3B)(EiL`^Rc!Sk-l~ZpJ_^!Ri6luxb)*vIy9FjO`zVHCC|N1Z!Ba27uK7+ha8(G%z~cJddH8RCsczP8F)ApsFuaBcQ5*`Lw@7JC-`tD9Kk_WuwgHcmnlf5UU1xY>3r^LirSHcqpu1Fj%dc*r!&HP_>DXz!DW$sJ>;ECQ!|wf&cttQFS7!Guu5rAXE)76;Nwjds$fZdiJsi)p&<gry*3eF_BNzWK;t})dQ+qvl$D%vuIo5BUv-yR4c_{lhw-bvBJj2d5ew`s|8pc_|9TL|4>-1k}LrNsy<2kL8?=Qss&U%5CEK=s)KE1Z;{K7W17Nm-gMQIyKO|9bVkC42l6U79Am|{YVvac)6@)dEAXI%zH~7-3@K(MqI!`k+`TGTs24N4oe4}LmB4NK51Z=hDnR2Ppp+qhNPybR_Q4H_dfY8g=qxP(IuVxqX|HSxnw2j_$Bz$m&D4byXwurz2rA#_iYb2pKsP1ClDk{%rcX3NuL0B$KqmyKIx)~F2Wo*~cMen)wsuP`k4r4PPXyGbKtoV_fa0yP7oZvi>Q4dGR)9{hR>ZKY)lC&>1Uiuts5uQ#H5w>h{=Wd#S$Ax8SxKKjD>c#vsrBEySL#3)gX$;H4CvB`l>=0RDgO?D#<>qDUd693)ucM>+N>_2xH|@_ZVuETKpkrDF<lZxIMDb6S{Bo3vOXUIoj`jYbxF8Cfffazx+oNf#rQD+3XT0w4>Zn_Xj7i5z$)*zbEpGAbprG*@AB0$`zYW!D`UqD&;Z()EhV-(>)EVG@3hC{sfO@eCU#y^uab(|ji&`X!-;uDW2c@SDeZH=RnV)Xs==)D-GUt{++}oG$#~kSHb9+tN3vOqdsr{8k`gDoZt)HP^>+!>ju@b`vTl-|LG$MJusmJ?w(jBstU-QV4J)+0Po6rc`Q9_=6NO=tVW^ZBec=E?!t<5V=Z{a%ROn4WhcOFkG(+a)PkH>`A3ZOmSDS+qC>7$-vp_)QGYfMA{5|X{B|e0nxe2{!*z`<6FQD{b108b|Jw1@#T!Cj*AG}DyivZp|o<)T4Ol8?K2DBWS8J!nHLGLZ+3Y7z}3)U&<sVl%U2|W9R$Ay<0gU<k-0r2#R;b~`M*P=INb-42dRRF$*<0|nFhNtJ+(3`kJ&nB0vt?r{vPv0#)H)!6@nhj4E^<Q@k&knq1)ZtkXyimYXpzFa>l?37GJ3J?kfu}w2Cz8U04c{XIPu(rNI3_$`tn#8oZ!s5}GkW3P=#h(F7&C97rDY4A1*u{P&w+F@T=dkiwx)M_(zBo!0Vg;B;laXo5Bx5mMew7+3zBGYn4Ku97n36P9NrQY*qrUmgPrt(Ab0U)=*?b4F91tl=m)mY^O@hGJ&K<0JLyS=o{52fSaF$MuLGuvOWO;dnSk1(ZfJe*CJDPa&K>O1a5A+2gT+?YEoccl&MHILIb-MUM21W3XkCTfwZftL=yB(xu@B1bYmImJeqpMW<1Kif|Nj30Fy;R>")).decode("utf-8"))
_ACTIONS = _REFERENCE["actions"]
_TARGETS = _REFERENCE["targets"]

_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_STATE = {
    0: {"last": -1, "calls": 0, "experts": {}, "fallback": 0, "divergence": 0},
    1: {"last": -1, "calls": 0, "experts": {}, "fallback": 0, "divergence": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    return min(718, max(0, int(_get(obs, "step", 0) or 0)))


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


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or []) if order],
    }


def _align(action, obs):
    action = _copy_action(action)
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    action["hands"].extend([["PASS"] for _ in range(max(0, expected - len(action["hands"])))])
    action["hands"] = action["hands"][:expected]
    action["market"] = action["market"][:10]
    return action


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
    return min(_ACCESS, key=lambda value: abs(position[0] - value[0]) + abs(position[1] - value[1]))


def _valid_unit(obs, actor, order):
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


def _record(obs, expert):
    stats = _STATE[_seat(obs)]["experts"]
    stats[expert] = int(stats.get(expert, 0)) + 1


def _unit_router(obs, action, target):
    action = _align(action, obs)
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    private = _get(obs, "private", {}) or {}
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    target_positions = [tuple(value) for value in target.get("positions", [])]
    orders = [action["farmer"], *action["hands"]]
    expert = "trajectory"
    for actor, order in enumerate(list(orders)):
        if _valid_unit(obs, actor, order):
            continue
        op = str(order[0]) if order else "PASS"
        position = positions[actor]
        tile = _tile(obs, position)
        replacement = None
        if op in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"} and isinstance(tile, dict) and tile.get("kind") == "WEED":
            replacement, expert = ["DIG"], "spatial_rejoin"
        elif op in {"PICKUP", "DROP"} and position not in _ACCESS:
            replacement, expert = _toward(position, _nearest_access(position)), "inventory_rejoin"
        elif op in {"FEED", "PLACE"}:
            item = "WHEAT" if op == "FEED" else str(order[1]) if len(order) > 1 else ""
            if item and int(inventories[actor].get(item, 0) or 0) <= 0:
                if position in _ACCESS and int(shed.get(item, 0) or 0) > 0:
                    quantity = min(6, shed[item])
                    replacement = ["PICKUP", item, quantity]
                    shed[item] -= quantity
                else:
                    replacement = _toward(position, _nearest_access(position))
                expert = "inventory_rejoin"
        if replacement is None and actor < len(target_positions) and position != target_positions[actor]:
            replacement, expert = _toward(position, target_positions[actor]), "spatial_rejoin"
        orders[actor] = replacement or ["PASS"]
        _STATE[_seat(obs)]["divergence"] += 1

    remaining = dict(shed)
    for actor, order in enumerate(list(orders)):
        if len(order) >= 3 and order[0] == "PICKUP":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - quantity)
            orders[actor] = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]

    action["farmer"], action["hands"] = orders[0], orders[1:]
    _record(obs, expert)
    return action


def _fib(index):
    a, b = 0, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _projected_shed(obs, action):
    private = _get(obs, "private", {}) or {}
    projected = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    orders = [action["farmer"], *action["hands"]]
    for actor, order in enumerate(orders):
        if actor >= len(positions) or positions[actor] not in _ACCESS:
            continue
        if order and order[0] == "DROP":
            deposits = list(inventories[actor].items())
        elif order and order[0] == "PLACE" and len(order) > 1:
            deposits = [(str(order[1]), int(order[2] or 1) if len(order) > 2 else 1)]
        else:
            continue
        for item, requested in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(requested or 0)), max(0, int(inventories[actor].get(item, 0) or 0)), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def _market_router(obs, action, target, next_target):
    action = _align(action, obs)
    market = [list(order) for order in action["market"]]
    farm = _farm(obs)
    private = _get(obs, "private", {}) or {}
    seeds = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "seeds", {}) or {}).items()}
    projected = _projected_shed(obs, action)
    expert = None

    target_quads = int(target.get("quadrants", 1))
    current_quads = len(list(_get(farm, "unlocked_quadrants", []) or []))
    has_land = any(order and order[0] == "BUY_LAND" for order in market)
    money = max(0, int(_get(farm, "money", 0) or 0))
    land_costs = (1000, 2000, 4000)
    if target_quads > current_quads and not has_land and current_quads - 1 < len(land_costs) and money >= land_costs[current_quads - 1] and len(market) < 10:
        market.insert(0, ["BUY_LAND"])
        expert = "capital_rejoin"

    planned_seed = {}
    for order in market:
        if len(order) >= 3 and order[0] == "BUY_SEED":
            planned_seed[str(order[1])] = planned_seed.get(str(order[1]), 0) + max(0, int(order[2] or 0))
    next_action = _ACTIONS[min(718, _step(obs) + 1)]
    needed = {}
    for order in [next_action.get("farmer") or ["PASS"], *(next_action.get("hands") or [])]:
        if len(order) >= 2 and order[0] == "PLANT":
            needed[str(order[1])] = needed.get(str(order[1]), 0) + 1
    for item, demand in needed.items():
        shortage = max(0, demand - seeds.get(item, 0) - planned_seed.get(item, 0))
        if shortage > 0 and item in _SEED_COST and len(market) < 10:
            market.append(["BUY_SEED", item, shortage])
            expert = "inventory_rejoin"

    available = dict(projected)
    for order in market:
        if len(order) >= 3 and order[0] == "SELL":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), available.get(item, 0))
            available[item] = max(0, available.get(item, 0) - quantity)
            order[2] = quantity

    if _step(obs) >= 715:
        planned = {str(order[1]): max(0, int(order[2] or 0)) for order in market if len(order) >= 3 and order[0] == "SELL"}
        for item in _PRODUCTS:
            extra = max(0, projected.get(item, 0) - planned.get(item, 0))
            if extra > 0 and len(market) < 10:
                market.append(["SELL", item, extra])
                expert = "inventory_rejoin"

    # Preserve the reference order but cap fixed-price purchases so an early
    # over-request cannot starve every later fixed commitment in the same turn.
    hires = int(_get(farm, "hires_today", 0) or 0)
    quads = current_quads
    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    safe_market = []
    for order in market[:10]:
        order = list(order)
        op = str(order[0]) if order else ""
        if op == "SELL" and len(order) >= 3:
            item, quantity = str(order[1]), max(0, int(order[2] or 0))
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
            order[2] = quantity
            money -= quantity * _SEED_COST[item]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and str(order[1]) in _ANIMAL_COST:
            item = str(order[1])
            room = max(0, 100 - sum(projected.values()))
            quantity = min(max(0, int(order[2] or 0)), money // _ANIMAL_COST[item], room)
            order[2] = quantity
            money -= quantity * _ANIMAL_COST[item]
            projected[item] = projected.get(item, 0) + quantity
        safe_market.append(order)
    action["market"] = safe_market[:10]
    if expert:
        _record(obs, expert)
    return action


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, experts={}, fallback=0, divergence=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v88_reference_trajectory_state_tube_moe",
        "model_id": "v88_reference_trajectory_state_tube_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "reference-state-divergence-router",
        "experts": ["trajectory", "spatial_rejoin", "inventory_rejoin", "capital_rejoin"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        step = _step(obs)
        action = _align(_ACTIONS[step], obs)
        if not _FULL or step < 216:
            _record(obs, "trajectory")
            return action
        action = _unit_router(obs, action, _TARGETS[step])
        action = _market_router(obs, action, _TARGETS[step], _TARGETS[min(718, step + 1)])
        return _align(action, obs)
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)

