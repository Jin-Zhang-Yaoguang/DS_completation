"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "ablation"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlq%Z??<ai-s;*0u1vM`+g~QzD@ji|B4nK|>S>Lh2a_1CcWnXE6};?o(MA7jt)Wb2AS=x5%?;CbOzCPkiB5v)_LE&kuk6=fD2jpa1k9AO7a||M}s6{P8dU{_|hHe)-|I-~IUGhc6#L{Oce8^e?Y}_Vvqu|Knf&*Ux|b`t|QW{O#}l=?}mC;nOdF_luuCeEjhFS1;dv{a^Rx<L^KG>eoNKd`P}{{kuQDy!`U(U;M|H??3(K!^fC?d-?Z%{q}di`Sm}3_x;yD`0-aSFTW*!aPcAHmoNYIF?o<*|KcBh_uJ%$Z4dSP51(It{OQ{d`^~2xe)`q7ua+lYzkm;3`_Vgq?jK!cn*Gkd{oSv>|K%UP{`;SP_YDL1h5PU6dYJFO`^C$KDfz))|L8YAZLhEQ7yRAp%T5V>_tVP{Z~wUX4cpIMeiiY9fAL+N#QrM^I>b+0|L$-G#M@)RcpFoFZ*d!s;5YFhmv3+Vm~SI>|8ycC<-036?7v_~{^O_L$=~7fk9rXhFRy%M`|lbu1t}`qFK9zS=HQ`GQNF(N;~^y4A9VdkD1xq^xI8F69OMHR`G8{v!O<n6O`>y+Xs$h+CF12fG3opy0zcd`{zh%uj1Af2XBYjY0VDm<<zWUpF4cZ^{s_8t?&z7w`%p-~pnk}w@4tWf#ZQ0uyO$q+`t|p}{_o#j($P<btm7RYtsI-!Y3WWl^?fwr&;s^~+Vb3aa4QyN*=CW>+HHL}z^?p}U7Jn$W8OZ!XoEq12=eKVey}DoWL++P$S;5R^jq?WEDJaJL$F)Tk1yZ9-sHdozb;qUGG|-MoUNVl)7_h~h@1RZy*)lXb@KCm|HZI*mTMxk8Nwfb`r*6JfBW*o5C4R07s$hHdwRCbm+UydfPP%gIN^WdOKkMD-I#xPmaNmv-8=u;eVdYKZ)<Je$f{rNb=)b3Y*&5z9&dYEzB;(IUkGCJvt8;Cv@Sqkdc$=o`*s(@zN12e;(oCzLOs2gN=a;i+UhG&k<MLS0*$lJx6h`GL)!88hkUT++v_`lh|UzeBMrK~Np{^)5$5g_n5%}*?U(!9iUr3V);8S^q+a!oE%;#UOSWLsV(!Hq8w|Gmk0RCHjo9~W>OjNTinD*+d29g}jLYu7hsW5y{T3UsY@fq^Q2QyVP;MS_?L7`;fy%yZm-;Z(1^6R(hat9V^aV1Wh1g^HK$v^%va?+5I#`K4TxW;1cX}MS)W*D}?0@m;Giy)Ye)IAVL>C!)b4LDj{B?R@kXN!ZQWrtV)=2F>gLdjXmvj%T^5ojrQT*Kx|Be4a(Hr!)WZLU6PM&)E!PS`BmQiXlU4AVQIy?Y(%b{&6eAi7H>~*!!sc1{@3zQ%q48Gz0L!z&zNAuA0MyONTxLJcFbDOyW@^mYkE99l3Cl6H~POx>MOBsTk`xsH6<sYGwK=5<&{mNH2VdS9kEg!vnAMSU=el5Ra+asaykIXx1f4+ekLI2pfk@JrO<hL$yr|*0u(S5)7p(w4<rQXc=r|602)AGZfw*yyRWEHM{_lT~KmlG(r{pw#B6~5RGESMsUv#+<_>9%%nUsUeX<zK`gh>ktmPuk9WSZqTAl^J#^pGB~RA-^O4*UhgwbPTLdzYUk;X^ScvRM}QOP`*=(()i`^XN#chp91+7UntTSxIw>zu$E{+Tz~lFBTpk!IZO$TX2Oqv5~;lV(T`uMd-9QJF8Jh!0*34;R8QupPs&+-V1plWuPG1tI4mh8Jwr9mGyBnm4rv^%+F%Ddkc%<)t&ThdehT|sJ(zVK(JIFg`VMwT3WJqS)Kg2G%?2G6Yc%cir%zuOr%-#AJW|!zaMqtD6)7wqrr59Q`94}OT3v|(GmMU;XRugzUciA0<ty<?R?Z}OOWM?8Jf(<*%u6x!vDquts`k;~=Wl*KJVID}Rldsfbvap_Vp{=;vn%U7^~S=0KoI%%%Ckhho(4ZiQpbsX;)=3w-vIj7rz(*(g*spFW54_$Jlv3Tig;ViHLsk%wOd2q&nIe!h+kA+VHrh4Z+Q>$7s&z&f^YY#E6R0glw!2@;aStFH-$~cvyorjQSFw_Q+J*7xxsfu^QEs08@Xk`lf+B0_7;D?M+R6<dF0Gceu{&IKl?x5mQ3s<m@ff`%M!7blU!%sK3>l{gPd)!N36`qW;G8bWviWHDypsW^e-#}D%Y8Ez+kb^>kOjGV>jO{YeenmR{XbMAE^0mIb*7F!>V84<gb+)V#wOiln3@y;9(aSBF8PrBohlCb^jIwoymQVz5*kKS4Buiz7bO+`XvwRQw3)G2kl=U%b$<rO)$M<v4)RbCD9{L<+Jv!iDc%Xdl9Bm9L>cL8R*z0idQ*B>Q<|wj}&<0Y=hPe2<$MZ^KLU^*sMjZk9nl7vH3!(rx)9)`o)HYyx=xHavO;z#Pth62pfXP3{oM%apH3Ad53S$)(CJ5Tgv?jIpvhu*sc>gGj4}%#>~Ih48jw$l{`Nqn}#TxQJboQ16C{AExEGud>{_wB>KhsNJgYQHFQ06IsCS_3PYdBjjF4%1^IRCH(2?bmAp#x$ysh`bU42_nxI;oo+(g9Gm#q?b!P3T$13hq*eRb}5Sk~_a%2yf>*Zml!;b?w2q8b1r~VQBVq`<%#Cv-RkrCMtavCG`N+PMqTE2mevHh-758z9LyL3LKGIYw!S1t&WsgOutxt{zMuG%?fXjTrhGU%I&hQ<V*)9cMgq8N^LZV@~zqBy}qz09h-&IhM|C0{$$HRqa7Fb$W4*HV1;%b{8=SBu@Ce-ZsA`%2)ePA_CIw7jfrt6KGzfMrSAzZ1ETG;RjyH@otC<%B~Hg~-8$yf5@Du6(V_hKv7Cj$~8`Y0XEXs!FKOZl4~p*9*_6Sn!^$(jiWe{L}mPPk#C9zef+4vT=z25)4CoV?M4~C#`uHQ6}AxX|X12S&39GMWrAbxmEJZyI2bZUY~&6FC;MqT6V`4?>Da+5*XzRXq605xesJr?J19=BI1PlNOC0S{8D65Bu}b66%C|l6<rNGoM?G58}@3*7csSM;n~{Pnl_$M<iZiEyy?FzBW2OLDna>BrZz+a#_SKLO*<4!UM>)cp*{SeB$Xg^^>y<$q$|5O|I^kE|4yKOq3%Y!yHvm3C%@wMU>1ehw8F|u4(j(GL>tmBNZ{AVOsvuhi+BF$mB><3De|G}ItpHC67vQ2L<n?SrogG~;C|J2$j3evS!&um%<`&m3vqLAkeN8=kV%D)l~ZNcWtv@Ah;XMrcPo&~Ddy>mFSkw$SS2D~!-X6kSu54D&IHZ@q&SBmh_<I7d`v54QPd^B{JcD=E4vhkN+uS{0=8tPr_P5eFhgPqHMK6|W6}lkM{>1|>B|m0A^b4R`=EQFXE$|2ZB7X+)>hunP^$YIEI%qa6{tK5tk?M1_32wvp+OUQXyOZEehjk1E_Vf{+LwA4^_e3&Aha%x<z1+>-f9kNf;si!n`4J6ZzMOP!t9Gu4q#zO@{tc5Aj(q?dPpdz0ygH6b%<4F3HP$vd76`5BO;3!)9q7Is~7eUksuUSvsu}x+f!P;SyR<0%t*CNYI(R2fiX4FxsOK1kpyi^y;&{IEMJd!TSuM^Kh!2`LeqtUeplR?RedT<9ZW2wWc3Ei(SlLx*IeJ)0!f?YbIM!;$BLp1gC5bJ+&XNeXL;PnSJk!H9!Nx6wx3a~@m+x=o&w?P`}^V3Ps_h0I>_R^X&al;O4T0@Qc<xfa-k$PfEIYJ;Gxz{sBdR(1hvR9#XkQLR1O_t5uuu>CYi9G{3vz_WXo2{S<eoJkr`SnQqc3<$h#o}eATC72hCcAM&vA{i=mnT*e*E8zKpCKl5!RPEtY)S5(|IM9Fo@H6(^77Ew<-Q*##B+W6n&9$7d3Ka}>V<rV&9gd*YXFOYMd<W`~PKXNipt-ayMARxNoKof0WMF&QjDTR|@$ayewQ=3V*M1V=~Hnnbk2C-NDPZ=u7Aj*{|sA>V!7Eou<JN5&qKE<~noy9gevFEwX^2@i#WiU#U2>D7f^HV_E>7&s&0MxXMC(*&G2)!qe_yo|)1g&Q;DWtpkceB`8BUQ25c@A9sqB%yjTHdd-FDBUb-h$XNy<$Z9G8V{?8Dn1$VMi9MIrPpeo7@D}Gl+pU)Gwj=7dmFB`YVEd2pd!`n#ftbi#9(Wh;+2w^`Abg^%rdD<Dx)~nF&*Y~wMU>FjGJ0zhIf?oZFCtsBR9Qz{SwEQwt-z9mvh&P%W+FN`0}kr;FBE>V%MtIgL8}?-Q|d;wpHpegs!>uPt6HrA<k_b<utUsNovf?E2lzjQ_I5u<yXMGp0-t4x}FPDVu7;gSU_dOx&FoNL%&gyEPZnqC6y7Jh@2=eL(M}{jfdY5kF-zQ4`bMTqVBwC;amG!$hp5xyqVP)e`L8^OJLaQ6_#B=r~VjEQhn1pUNkBwu-gT@_0<7EA$|Gh-J-k7xyr?c7J1;Wy>>s~jMZ>lTEN?lk((6q>d8^cP}`I!Sh`p2nnykL2th7m;*dboXm-7)OYad}Fqv6}S%lYcZE(6Tf=mZ>Eu+oCxVIv5a54&1=*<eb(XuTaIEK!=<13}{pgO>OeyO^T@GK~f3A^b2GF9oXYu5y^?(f?pvi&ZIbU8j3OxtX|d{N~sn0Qa3j>P}?>+k;ol?`d3i84-K{+?JDeyJfg`_@;!jPf0npO7f1D@Mz>e$hA78lf?bG0GxRCD1m;X4q&9)#?zziCXNxC%1AyR?`hs9*SV}MWVz2w5J}H%3}Fd)WXL@Q~S(@LBcjaMZ7qUmcY=7M5^8aIU_c+Bs_%+H}*lrtp*i0Qbkf+sSq<aSsSK)<S?Z_DKkqeDv!+uuph2MA=O#rP-52SbVy8izrXxj^-I}E;RrRC<Z(y-NVdoIAS3hd&2XBvgB2ZQ+?kcDCO&<a8iNuMQ=g|5h#OX|M0!}UK5Loy<!6}n0kuLA5|knS%nQbn<CpXCo8gm|c^F|+S}*<SGi4<XA;={Wfm)4x^tyS{z6zK^pl<Dxedj<>rJ8e_zZ`*0e0H`m5X)J!`f<hYq8SpznqQT=6}|%}C(DMEPc}!xk;p+ak`t~MIT+-f>e?LuTGdAlH~lhjgZ+u&H5TBafN{9A&soPXW9{;iD95-k?-6l@Oq;+fu3@~y*zKo=MGJWTJ)BEt^QF|wk;`;3GV?@v;r^RDYphj2H~S(%1{sLU0v%%Dr$P9MPu?`9gA5$;e(%A&H8;u27#YJMQ_0NiH<7e!G`1k?)tJH!S@xTM3#Q9(8vQ5mp`K=+35AdRltEYlkazZ47YjjnjjuN0cK8N)vQmwdLFA2~8hO4xslKpt+%+qGup1?yw6swwQL7B3+99Y+Qg+xPYGxA|WVJ%&ZjHD(wIY0zNIJo$K#7@<@IrkeL6=`R49msw5^h*z6B}ORQtT|%)FI)YUP*lRS&>L80K!bjkXwk7Y<K*q4pkXJW)U0WM0}X@Luup*g0Bgb$!z%kR&?YCTOOEtCV?LvM`1;&<j5C|eB1+SFidOWME=DzaO_f#JOEP_*AmU}7DPhRx_wc48<$t>(q*XbQd5SP%9n$*Z$vg;%`gR7ZCCV{`>DLCIGhYLQf^e@R6<6)DAmD8RPB9L<4|vd+A_vKjigvuL+WD58O;gUb@-054VbYqB_f&H<*ZBB@lavq)}@YPgUuUFc$&eCD(xw2D5Ph?3JQL46}H65zgHzgBw*UNc(#qU%ptkDmJ?BDS;(Sx{h)?wJ?Mo#L~ZdR+a?f&NnEuLug`YRb$>omjs*Ry@_+_$Zy}#1eRr$@^|2aV|A^Q<<(rc^ARYpaB1PCkO9WA^upxDUs}0KPjH3i|NfI90xXNoz84=*vk{=b(^<3-duPB3l##Cb1qfwQO&F!ZdCVpvGcdR4+Bk`T;<MeH}NLYq4LD~mVx)6xt(IT;3+3=byu%yQkH6K`wn@Q;%a$Rl=E3zvI?em0$x|=7Ow-Hrel^LlDWIGWyQ==&0@z`2~w&U3yPNVuA;%pa$ZB3g!qL>#Ts)ZZN1AUFpQCGq02GzbpnaYB)c6uZ;g?;+X^1acgK5_3AWYp8E9`b1EqAB&QZ$zL<pQW<0sTGN4oRo+xMEf$9rMijdwB*>VJ~Cafh9y-{5lR_hBLk?|(V*FhzI;2SsGKMQq>m#=u%c&kJF{mF8bz}0NS$Q{^N1$TAB#p-)OXh5-=POX#%iw~j1hsnu$_)n0wWG@d2-FEsov`Qq*yIh$_&uMBbkPxpSoZ3&JcxB`gid;U7o+FK23*IjD2WF|02)YNl?Af>?KtTep0rXWEVeqZSp}G*$X2Ml|Ed@MH`P@Pl8@E)OnE35OB?Q*%3}vELVXUlAeY;axxB%^_Rzxa~1uXD~{gTZJ@ajV1-3wT#X+S;XM`EqwUC@jCB~`#<hvOLTB{X_~Y9p_Ni)DEN1r!-oUcVdFB}li)fmW&gM-9mAhCwBu6M=kboE6?4r>ywhaHs@>OGYQEZ642&6QeUB|F;J7vg|Zv9FgoU3L}WRqP+N|Qf#+0re6uNHkb?`Xl%`jnK35}h=x-or!z@p|~e;MU!YrknIxmT4pemPcknlT>{nEl-OlVpN`r4Z&tf$9gREP<~$044D$ZF!&EbT90<@$;9ek5kr4?XCuPcN@~_D^*AaQXu87isA!7{BMCc~vHFx<wHp~*<?%8$>eA($#1hZTo`cmQ?yw&Xw>1)3%*l%AmB$w1h(6w%rg^rcBS!MzK$qWA)kTZ#uF~+#zUYw0+2CHg@*qq5@~UNG65b>r`!ey=q<EZ&ITiF}&Doo_*Oct6_CjTy-Ar3uRvz>a@-0~d83*Ltju}ESkt&7kWkh;o;d2WAE<fK8de#B@-pf*6Hk3Z?gtHZ%rO;J?Itfx|C_eS7%0pPZ%b3cPTOQ8<O%R7_tw_yUA6{IiG-TmQHR=s^nVARD?MC3+L_HPdMMK?=;Q|!+H6yHtB(o{lv1R+{$OAHs_(cy{*)NdWMor{JX5f&|&J&?DD_$593ezlHr#>EeC*&vL7_suwju{hsw_Br;2U>Zgt5LUJn;xZNt%{;o24h(vRl;qGj_!Bl4a!$oI-j#X58Q*YpVge#t@I7Ajzm^Cc~3=>M*?2;&~x4Wof!o(__3f8b8Im}-+Nymj8sv`qIq2RBl;kbYG8b42n<^d(Ml7hne`YGG4h&2+!J7$vzjvFcBUpy5MAaNWO$%aGr+RCZZ~LRcx)XhHpB1gZU1Iog(LHQbjR{Ov%C2)6>Tji8HVbE??H`y6!H&whV^6$f+<0#S6FnsQ@$(Afg>nBYD>!5*Wyy#gVz8d!4=vV3RF%st}&bmjM3~5<#B!RsZQ(Tth-79Ez2T_8v7g*`L5OznC_q~Ya{Il(MTB8BJJ~w@Sd+7ry8+*IJV>#A4_C0;yM?QcT`h8wXZ7lLPb>5mdh1t|08KcNZYsw1W$;dsktL_`>+V3*VsL)IQ-)?$H|0JY!NqeXRN5^cm`PIRB_$fspfJ`tbR4=pTLxncuw1`b0i$c+g)ckl6;xIt-tn$ltDC11gRd3)fJ6<CbJB)L2`b#-dw{#k^I@*ZOD$8NXQbvQ)N-EX!UA9;&AVgF((lHm7x(Bf+>p!S<N4r7GkYJgmppqD5~eIy=!4r@1u*z>b74^d0DUTm>v2jrWuyQO1S!>a=b>xR68@ax0vDO2YOrh)#^q_wZFh{tk3KcId_z2-IkYA?a_#@ILRX2eMv`xZGtv=wd%UOp)>x_%=OfhS1yiaMI94ABE}cuH!3<s9UD4@ZODiR`mw$t+NwG{R(QsmUG3r?-Vkh8)iN4Ih=bU?j$vKycI~y8>EMDqW}oV<q3^^|QHmbIIGz*wJ0fJGr*<<|NxVA7+Sey+L)#o6sjQZ%B9SQ)$XvZ({+G85q~})M)xGv`^5X95hv!S&8d5cGCsO=he`eTU^_~i_MOYHAY&`hqJ|{H3+>KX-Nv5aJ&zOc<IYZxw6m88@2D@s$;l6&b?pko@ViBMmIVn39!hDI^{~M*YM0Cs}9s~UnI9^wE=4qhaA%hw9t6bi=!a1UbquqX>*+D?C>llH8j*R1D+RAoqAhDzMs7giC35%+<cAol8pNc264sz{)v+W5lBd=up7Al3KT70w)=FA*Nc{dexpmYx$oU<|koH&Yhk$|3QYFjzsI@>F7JQT*GHVj$ybe~BXezZmcbhNIl{X7SbgDfc=<Gw&S86f|JRe06hnJQIXl6XSPjJf_RB%LTtx6}a-5nz{Xj#UyXRC2gkd@Ivji!%uV2eP6p{iVOHJpRhDXxj^~!mJV97MhMw5y8gLXIH}2gEX8pU-!tbC-*CZq9zN%li}zr?{Kgqy@Qf9sab!;k&Uq(%J~rwS{g$|$>?iHW2<P4CR~^>e>uLvmA4O?e9N@0nqcd(<3pkYmSHU;$VWAkT%=hsS(Gf7%o$uVR}MAOsA3Hsl=nhJ|InH#ooy^g1sxh!ri+tF$tkasaG@vT6de(wy56iix<Xgd!Q_Fy9enRn1w}!BpH?1(oh+b^^&+daAq5z0<rbZ%=2bGaMr(P2oVvaEsmLgG>S4C+?CIiDe4nYoE6v}@LY~hY4`?K~SG)c&l?VZq-8Cbpv<ZJ@jX*?dXjVUIJ5zUqV;a6yB%o}?S@|B(^aEX&TaV))uXKCnM&gYt-uv>7TL4hm-f9$t4S}8{9Q%H0vrJYFi7u?w*L3u6nPMS(uC#<-)L^qb<B?;9jCSCM2flB^SoftyWhooK(Bi%oyg?>6vaz+The(k*=bFP#c67{Q#_5s{<gnikuN0>iNUI-|TN9dD3eYh2BIBdtIo+5C=q-+G3Q5Hix{k^Rgqr9*>`42Re$zEUT}|b&iKgj{Sw!y=RT&tP0AFM;y!ljXAyd7o;?IutVBp?Vkwd|5r&0{jvY42Ns4%Y$WMH*iCDDTKW;e|jMiYi+uU1~5IC1kajJKNF{~Y#9r5u}i?R6N&*i5e@j`5e_riIbfx)wF7dxDWMMDhwrZ?Ph;67oU$Ee825RZQ#PPiE8ig0Nx%paujlqG*!9z{~fae#5E@#gYvTe=^D}kvs?zGFonsA1ShMqi%M{WuH1k(F0#L!|95=AUG<LM-Xo8f>`N}czwZv?E0$=$KK5FrEhaS<8<3>Xp-})RUR{D;T4j|rec&x#)h&v{G1Dsk<p*ESQu(usSh-QFclk~(p|KzWNo}yiK#y4{35qC6pV^(1|v&F$%fl5kTo8j7JQt>rTwALGTEbhWr2-?C|Tr|@z5PUE5}Ur+JQLwI?GUa$&E!yy<mA%6t*f5nZU|)g8Z68DgiH7YLfAsOREIADm9kRO|P#|BOJl?;t>>09*&ojhInXrywP8c)Sb5ZQVKv!z{}O_b2m&`jJ0F<mcc9j2Vw~uI|nbrpOUrD)Z=Q@YSSFYw1ST;0FycKvwZN57b#Mnc9b1|E4_n#uRV_WYCB|;;p_6K<2$8P`8I-%OYV>jy|G#2(~#;$!Kt+)>wzfQT}510odk^=aN9eOaaB6nL=Al=emh~-B@y8uSAY=Foo4r|#x_s&0bxe5ILjq{kmJwz&JK9vv-))hPb^4+Ny1**)uvQ_(vZEzYmNH4rBg(g7+&smlv5ig4Z>?vIG`;6J~S!e9J=opElHE`94@|o`$s)?v7!Cmkroi7u^stN%cc=!?3np9k{IzvUMBSEP{*xSb<Ds`)4HvvawCx6;e<+ct1GLyW*zP47fHB`7wH($g|+E?M`bv>JA?|4r97*yhFe(iC*@`>sHdH;;D6UHj3UmiyiTpvr|DBa35xQL6nJ)e)RB?lme`T3ps9!#u-bk8V5eI$$lYcR^-4BD=0;Z*oVKfG2y4ySfavr9N1mqdTF{iVeSQ)3^gR|y=`onAuaB(`Dx`9!&qNN{Ldix1q=iq1=c19!Pa+annWYtPGL{Cvt&u~9x$Sq7YjvQd?IEdQ&$y#=_tJ8dv_cD%(>oRU9AXlO)JpR$4Uo$v5q@gfs^P<54fc+s!pF>8Gf!kxtIHkreN397#@ozM5)*7fa_V&ln#QpzYS0Kk8TD<C(xYy0l)49rQ*jhu2PJRynWtlybsWpyu6)9}g&)(;xB98MwSukFHlna8LK9ST(p=NYv`>RCaT0jKwR>vQ?N!Ttj2R%~R6A7W(>r#9qYE%iPt|74+U-q-JvV?LZ!q?{`i*gU`z)1PP!%fWJ=pZds~R?NWCcRQLZ>!~<*~P;O;U;5e4c4y1>>5_NUU#6N_OwBILGz0Q*GsA3q^7}&{aOo#X77OpRRRz;sx`Liw*@QbNqMFC_tsJx`pQAKquCAJiDQ|px`$fRgjVlbbiIoeyvm_yltTm$0w&2m6}trI}%>T2r=jLRxp!N`jDl?{cT%WR&;zJEHe~Ny}OodsY9Dd&0b03fm#10S2NYNEcc~L=qa-U7knl6H$q&0+yFT<a`q@kQfu-sWOT=yydrTuM$}bq_=f0pS`%q-vsZS*a_+;)w;(O+?#dRulScxMaUfGRj|c2*SqzIr$aQ}&Sh)h9*Kd^L7a@Cm@~(nJZ0JOm)Z&6+VaJj=W9|&xmbQ)h0kk{_seCOK%Q8yS7e8+*BdK63asHuBNm+dGplJ{?wyCD4q-Wk|Rx{h?#}1Sd5OYQR$aGys*GFWS(;B)m_(#Su=?o_`T*xUm9WI)@MKH0vAzrYMv)zA&Vc60Tt7)-_?PG7OiYkwg)qmE$=sqCwq&!^fZ=$@DX{&VX4IOWU!MXd3>;5`y+vT?5trIe-86y=3qzT^JK~R%+qtfFNLmJdk<<^Rr@@|#gQ=f>j)1QXrKsRuDF{TlEyrX)(;!jgv7Du?`4W1f;t0Bt~TXWM;m+9JCDPN|wM*<BU?<6aD5p+cuYf%;z0kb+wumr=*+F(vVL1I^gt`}6vDo<|42`AEZ1%@vLDj&F66vvHPS0zzQORDjeaQx;tROvu78`e4~B0*iG(6H3mH9B9^!qarQDn1P?BM^;Bn3_eNJW(tegW;PmTJp41eb_?!Mi=Lj?Vt#C6Y`fhbH66FczeLI`e?2_UUrLXo!<EpZOVzM(F~J&BDAtz-{mC(yFn4|T2wo2xmddl%#?+V{A%7Z3d8jx=2hAh<LZbUl@qV2Qlbl7cZ<rhI92wN>!XC&jeT3VR=#CiD7Jn?q?<eM6<6c+&51R!I#Hcgqj#IIn&|OB{P*kl_~Fw}Yl%JLpym&hnpdo*2Yawl-e4?Sw(1XW4t3WV#wu^qWc;oX7m?MZ3hHY6V_oYWw+yd#Gg$Nyxhfdxn?!fiAaj4?=erRWK%t$PHi5r{c;9iFF7O=ULbs%%*_DwH%7CY%|BxF3q26<!c%gCUAca9>%a6JV&`5zJnIu56*Me@F^>`b2b8H<Q-l^=%MH<!8(Va50&6cfljz*=qb@?4ZfwZ{AEp28;O+Exs+xlNphIMF4QUOTtG`v^~e=zednl&FzT3sZq04`ojkNaZd4f32)huHA(UP{Y4^)n?J13yRX!G@L6cem567|D)m?99o8piIlvf-EWc(&rF}DeCiZz2NOKdyY2~0TLO0Z`<C_oFI6)B~iB>q@I(pHceFx@pK`xL79}g)sCmP)xd6jRnF#*C8SHc6XM%5Rpd$)FJvuAn`_!sxy461VnZfFo9Q2Z7?{-}imq^`Q<9}E9lsULn2ZwDCyCtGDL*=HN|qchc--0d^`QOS>=nx{TIcO|tQY#Wwj&$6@9Nu9WyG~rEaT6}pHUsaSzUSYfzNPJXfqKlu1?_1ST-AB>PkyRE}6hV%69kzNwXeX)8AsKb!BOdv$aj;wS%S29opsSJo#0(&U9e6WvW*M$Gl@iK)aFdWw%zOb5gA5I@od<KOPh}ZFUQRp)FJTnl6{whI;b=^cl(@z!_J_3Rsf{*RGTD2F+ASCV5=wkq!!9?}2X3v{9hEppK_Wt!&f%t(uXQt#L76sXPyNVDIVHOchcRX7Y4wZhT6vaVam8Orlc6c2Y{TKGa6svBu0yx#tVVw^;b<Y7caz+cK$qWVPj_?qj0$tI<c9+pDWX^Vzh{w^%UeV@DTycBf>fRSm1RV*MQ-Pd9M89T#UFvaJkDq5FB9v1E7uVyX=<wJfw6o{G!fCf2>#W6L8U&c>rQj6?;y6*5(;in#1i)in7m5_Lds>C($@%_1+Ivf_uht}x423FUuR_h&}_iD->X-mJ<{O8L5F7ZO<jg$%Z0x`4jE$Gqc?xH`F!CdSnd^TGDURF@UxbrK45R;77;g|dtj9J6yVX;xak6-3>Nc?UNi%69b>W_qmFi{Hy2CGSmq6IwPjCS--7Kvaz!*uzu1%aoW>QFhWU6L~itdl945x5D~&Qg2$_IAv#~WdL8GGqTKphVM6dyi}Z1<W7f8st2)F;p+&MY)@e?t#{>xjV~j86*Na~MBPa1BgQl6FPG?-%oivyVkG47x=8nA4%DVJj;$A$X;ojiy&77bC$LBgIT}T$9QIVeDi*m7**RWV%+@M{6r^+nhWtvPKxbOZku8;*_IUI<I<TQK)!Cz=(;}^{=+-)NcU-|l>ylqK1Y8IFAx%4MN698zD)yH{4df~PBeFP9b_}28<G82oQstnFaxE7%=3*h!A|~OTT79f1uXVNWXx4Z5nZ4E_f@_FLEeAaPW>HK`3K&El=P%4=&0JX;H7+jYH$`T9Xl>z(NMkIrcPmFCeyExx@<J*S%?;0yU58#e3!V+D1bULm1QAb8mP(N7HFe;%Iyx~?|CVLN>P@ezaO&v+jRx*`N<%8>ioBQXFZEzH4bF98s%$NxGuk(h5H?q1jyR6v%h=8(n|>Vzl^3Pd;4D!^ZRm8#78~}+r2mRQwDck{4rv*F3{vHjXU>lt3=Mlcu>!cv>ALpahug)Js%jPm6kJ~#L7s8YPF!}<P??Y+2#y^bL->82!AV#AGCfZzu{uAu*NT`jooD!s;H$G`Zhz{g!b2PqYRi<gU~QWj>+|j?{=)94P@N>q5nrBp>w{-vj3-*P)RK+Wzu+#(w8QH0UfCjvThDl68dFj(f~_^?^Vq>7m<Entn#hp=kyeW6qf;VEq7X|~H)MP7O?F60I(dyI3#hOk-Y0Eh9#Sb`2H9kur+;C|F7X%B9pT_*)%iPWa{zi_`0!Y9)RCj04T94LRVmqw`U}TGt*W{{Ml7>hP`Ck6b&ga?C=xJg_mni^ibrxTBb_UVrYXqNY=74B6{TL~=832Hg~5W+eqd=Q|JL@g8J>}Kd0<(B-2BVr0Kw*hCj+J&A8L+2b?y6&=o$;@LI6WL<csDKV~|g29K!X>e|`N~fBoZM{^!qsef^;S`QhLH{HLG)--o}kN~!JhfBowJ{NF$R%U}NZr`NxvKYsY%fBuhu`|H2``A^@T&Anz-K7RO*pMQS+yZ^cVzSn>CrdfOa3VgWN|NGOYfBf#JPv5?L<N7!1zrOy6fBpGivY+saPoKa2@5|r+{kQ)GZ|C*@{{5#<KfYwY>f57z`<=gfdHF5#w=cn@uOH*}O)e0k-w?Paf{(xV-~Q{qEdu`Af7@sx<HPxjp>d4guJs5u@V}42M)kANQN+eBZ0xDn%wy2lZ#c{oO%06}pb766jcuUu?*)wkXxuWn-aQ%%&?o^K_g>N1CK~%b&=>@bexljY*x_j0+0fWw6Usg|8uJZ}EzsyE8i+;<(3tm&#tcAX9v_Xq(5N{P8Z&s*=*QooRx}o%vF{y?UC_8~#d)IH&^Um`3DD^Gi)KXN`~+xJfyO-1Ks0tZ8g<`j&Yy9@5nPwRZRdwa3D}K*?MS&jndGUq#~&wd027-e+MZ1I{dUcj*mut)Kib<T6L1q;BbMgL<lC|Ajf`2yJej;Qc?+rNZ%p*NXJQH_&v8;Rd9JZJljpvJF?pWZ?2`!^j(sx0!bUrj=Y8jnnCMG0iAHn@91q3a;Xu(+D0=(v8KBsaP}DFe9kK&E4oXC!7&TpwioU<JdS$3wlZv@ND)C9BYpe`TVm#2uaMw#?JkZE+*GpuamWs_X!jDeH450#(8D1J_dl)Lt9mw!JJ`{HpiUrA?wGQS9<q4&o_<AkyctUwXsfDWdbfA4g830AS3n=;t#cU$SHG=<yvZOWMpr~Q8i-(3{3n=H!rwgFC0*ZY?$)V^c6by=cLU}@|#;V@~6m8!%6muFVZXA?=OAW-io^uTq-=uQ>f|a?FF}`B1M?cEQFb8ry?nwo4h8v?UxW`@Cbme;75<_`XaiG4~E>!H3N@8QsB{qL2RLqkKDC)6&!KD*Z*{!PdlS)#YU=}L+NoAp;`>Ck+Kt(;NWHV^hL_VqPdyrWOJ*mL7k6FHcQc1mG&P`=fT~ORfpiECF!=b<st$RYbJ1F|naX1aSS3C?Ad+A8F3-5aZ`6rdGvGQIsKR(>CSDC)ibm@X(mnI!&HE`>KVwg=`?jMRB0VOSIc|rlH!M)Ds-9y<;tIuQNHVBGI>U^G1wm6%9LP??MBt`h{p_q3ArH6?c$Rs?O+*u>2aZL1+Np<H@C$$&~qAbsoNg26cnYbsD3o<b$VWOT)l8!3|#ABaK?2}2sWOqMYnLN+-W~*FL%r>~^XQGp8o^v!zXfe6dyw1Q{FM~@?<~_F+Iubh{i|>m#+4~zQdK$qg_j7{{SvnFOr{!ePo?jogK<)`R#SxtH1~xF}-x2vgEhpI2rtEuao}4O;ZeW9#j*5`ea>_l7QZ2WBa;h}MSt|kb_TML`l9K|Qx+*44$;mJ{sV66dQ$Fv`pvk*5C-dZ##6tGn&47_)o}7|6nn^f8a`wq7$#doBOtV$(pQA$XI46hbxc0BzN$N{Samw$(HsNH>%4rHBPA+p(ff1E+RQzjqj1%U?v;Ws_4kI_=q%Y1%+j%Ic5q2Z~9tV_HaUdvn22gXQjm20{!qBgOm=UF;eu7GKQ>qDSaDwh}AUJ)?1YNj4>1ySG)WvBp#!8b=;_-Bkocst*F00R4Q&E2DieVq0lN-ayCM8>G63RX~RjRmlPP*s7eR573aMDjs=tb9NY2THT>XG1|oRdmK#pcPW5;!S2*`<}~X*p?YLKi8U1;STSr(L0rfPxvQPEguNN$Fb!nVjy4#;v5(-H;kNrf?;yaawhp58eqXlSFvMq)b6-m-EO2a$-^*CuJ^9N}Fl!K(%Va6!6&AU9Rk-P>o!v@J1lUYu|M~w_xVklcA~@iq%mWVpWHz+;vf@heY*;$Aep+KLe`yC@Bx(ckoUemWJ4GUq4B$qyiwd(lOt@eqG?>lhj5kjwLmn7?gdVpaQThmV+{2mFfZ&@9&Px0HvB6-(?}V%Wwa9EtH>}X!jqSyPKt;%*{Y~-EmBM0~J8>E}RC`e2`OFa~QvIG7G1!B<CqPS)eD}4*>=&-{KI#yWli|luPVO2Hzp4X%Hs^IN76|ruV~1AK?_w%4zTaw{v=1pL9>K_mrFrNRGd8GDkUu_r%HebMoiqqzX>v8z=STgm8KtLo=wfTR92Wad%cu7UWb)PJRd{|InNQ=rw2nr?+a&Y2oBf$|+QfGD=PwaMIs6>5Fi3a!%^f9qOf=G{Q*@=44OIX&%VQ+?12Q0H=L@8p%nYfRow8g|BRO|BJJ8@=><m*$Su5^~nz6G_VVo#*14f%LfG;R_~zn0!rT!)W881hjMzGY<pI-laskWPJ;*3AW-@d2h`yFoW8@=M_2N5c7qUy<mWoNouRm<+X^pnTyD}GxGc!hVU?_pkINpU<qMb42x!^N$>F`z3Q60zJ!1!p6Zd%e!%xMbv}}cz9%kWiK3W#YGT#L)7lgESho=a9dGzMHKgvhtwzSM}S^>~fPg)7Bh|n?_E!$VRctTneprxO*n6&nM-kQZS7oinTL(43*G)l`1p%qR|%MPaHPe)5-wA_<cvL^=MGwPT4umK|TCoOp13ZOLajSb`%w&>q`r{xn`4$#_lpP}z`s@@wdm(a2g-vjj0wDv!BC!nPd)3VztRi|ZoqJeivtKzw76+6;wGd6zHQth<tNod8xv`ogvZyDzOJ2$1JFP<U{uNAB;Tz0|bNL=pJgA39coG2W1Fqkf0pBCIr3;Dtw?s7ON=S^2e75{p7=X`iv6>nFNg`XJvoChB6p}=L59P1NWvfWwapy0B0gZ>22ri09E!3-vKe34`gPiBczOJ3-=JC*Fo!}w&jF*7K$fG~4UW(hL`3bt(K^J14WfG0D^OtYBTchAfu%wQpxE0~!cX8w%K6fn>$nc0lld;(^1ATwCF1eqxy0eCX|{Ze|;VrG)^l=sd|6?1d0Fw;+F2r~ni*~Hh%Y{gK|xw+0w4=hvXq|n|1PjR&r96a{`1ri!1GY1-!KbgVv*_tv_Te%8k=H3M}GsS_-{K=SA>Nt)=gAP#PeL&Nb=TA>VP>aid-v_nmWr4>4{6rwNka)0kQ5$tpzkFSqo@YKa7}n0I`TL=E`MiLh^?a#R<tPgCCEDP*bjF!o4KNQZYJ}f^cy=CT7s8(A)k???`j9%1zVsl$wAO&M!v8MQ8_xG9uE0m1i~Hbv6%L3Jz|f%-cKe1Nc(J44_EI#}UD34JSc5*M7Bt<14sa1<mASL~0cZx4rVpl%rm4`hK-~{%nq=gjho%`ubIMwWV>Bo5o&A*aqzQKtx20b`X6-dCxPj>H47gSYtO`>Z&FN8S8XadYPFvud6Pzw97I47y$piC{D8?Bd2Ip)eAEyK7oZY|AR&kmw<mVEc`qDVf1LHKwG1Ddj`V{Bxk96A6sgxAwzE4A!V3(ZKp)+-fQ$0RTkK%Oh2+jy_!YL1NMu1aw;tY?1(@wLm;j~072UdZ=CeSWxzMjSz)iV80jMFGSPLtvE#ptw&T}*xi?ZtV|>5~IE%Nrxa=|Kxb1HAq7TJh<LbH_O)vTg&em>yh>4AQgo6{lZRMlzi4%s3smfg3Q*cbpnX8Z3~3s3nRg#c3Y}r?<-Y;0(!h-f<eBY137l`m8uZRGN#^Bsg`pn_Cd~gl&q~$?m^>=QKFy3*dC1FvcY~9l-fEg2Mrv`cZKDSy>s*SRB+%1E(!;N<$!bSOsZSrRlhzWIRJwd%V|Y;XGZ!Gjzo})uRkg8P2^5cRhG|22PjZ6bIv{hoq@Um`<AC83jR`OUNb?4AI(9NqyTZrM@2kp22U{G0b2_S~0zlCAlq_oi2%DdN7+kQ9D10sA?t0YA)bokwWz`^g-PhFBlcF3+4cX*ieDs66CjmdWo8xZm2ea`nGq(?JO7p)VKedM0M-|;6NA(SE0r`gj%`HOxBNrY5>%@MTl1UyU)NIDO7)lP)(=})oCPElTfvQYS_Mh`%_an>{O|`hZ(AJs3CzmW!1B0!MsDA6R2kUJ6a0Wo)oIjQs#B269}W1P^TpxCxWUUXHlKCKMr-TCB>kc?S3;Y;CWCjOK5xBMYVRQn$!`h^VXOuE-Bp_)p$m#aTrvKLY<aOWZbZ+q~B%S1PXeAsvA)Cdw}WyR1cu)1nS$0Fn2=@j}JA>v+sv$8&ECi=$AuP6{zl!pc+*hs^)T39q4NZsm=sdBceLpp;#e$<)lmv$#e#5s@po2VNCHXrWP@ccc}L2VX8rjecG5tz*HxjzXMCEYBE(1&(sT!sTk9^?foHP3U8@yJHA4u`UFf}b)ZIB=r4sDwzIznP}Ks}5Kzr&2da#zEtvX^sY{rK?ebb<YKJfl56(1I$iYn9uKq}wYLclQ;1?V2azXWi2z4%#Ta(2U(+HSOCu8brrzx%ZQ1zytNrg-M_e-cDfvVrZK<!~_3iZ-14=b5^z%(XI&3j;aG#P&(2(Rb8VS<@jGCoYTV(M|(_zt7vdt_)T@uO*)`3!A^mCthW9u%sNH2a_B48uT82tFGpGrJ=Q_vCM^Xt?%TjGG`-caP8(2wm1vb#IaO@Ca)u3-6C2v<pI;c_gF=^}{2y8$z8ntoQLKLX#le9nKZ#?QsT#dIUmK^cdLn8-YY<p9pIR4M4az?K4OVV0Bi6G1$Whb%Jm&j~b8gwt0p9Y@Lt7c@#p8BDAML_<E}ygwPfU1BiJ;gno;Nk3kq89ic4{1_Yrk5b9wF!#yI5Q40`ipaXVb^6nE^B^JXwLURIyX0D9FppPST#g44EoqGLRpLG<<5k>@|1u9hw*1so0qVhXM2sP;?LetZ#_<`2KNom=30$s!cu<xHh!zzeyk5oVWS{Q4i(DD&l;1v#gl<4gH>n;op9_)!HvXzAyrs9r_AvB;e#}11ZUJW5$9bj;TZjQ3Ze=J%VYLMlGX(pGnIJ{Bz#0*5Z9ctz@<f^?4VW=Psg;CgDAS6d&5Fy-E;t4{nbZ~tMsGOlM+`;aGVHh_I&Au4M6k;&?5)j=(3`7~kxyCTM>FyK41IN--9ZSleJ0pCJ3F$SE7U|A1ZCDf&vXe=kDt>g7x{A_S*M|~T1pBNw8=jM4$~c?>rK_Tx*`u;v=NiEEH*Vl;BFtRRIuCz#u8hiQc77B|14xFXS?3z^iYFlHRduO^PNs5{6UZ3vHNYlO3tJHSvZo!C9VoGq>j<iYr!Dxef$8>M)BZ$>R<GI$O0}TW0Oe|Ld{&gR0uA#zN$Q290>x?}=>vKul5VOGN_zz5UPG0ljG*t70d~*&)bm@6(xND*r1&f*omQVHndQ@}K>0T1)z%GdZKFJ&80D;W978e|6@KR=>0EtK`XeZ(ZGNZ4k^vO^I*>#-!JyOwQ5t|UZe!3VC_V6^aG+%B1Sr)&lw}ET%qk-_(1J~%fGV6A<!t1ePFc4bvf4cj8g#~!k#xlTj<Nt7L}?ORK8SK}y%Z9Z=G60BfYO4c(t<#m&rq(7iq#hT*mZhOl$%H*f^I81ssGUc<!;mEleSFu@x#8grP6xA1$-AbxuWNi0o9{x(YPvlr#}9mwACD;k8G4M_GlB?yUPl3&2k)9S?=QG^IL*aXGa^AR5sgesk|eU`Wh(1eE+4)eQKOQw}mc1fc~7faTdQ6K0OX!ZE@4uIoaXGCjyb&LOkuO?J_&@Gvusm5ixC)IYKh`4L3=Bsk;{;g}OXRHLK|;NrR9yKqTuD>!C*{S<M}2e`ribKyp7}!@kcZ>FO08p5$&8UJOdD_$W<*asr9{9HlARY?~9HoQ9KhAUC+%)+-R{F`&rBZ@$b=l31;&MGQdw7IQG5;>vGc%%>%3>@<obtl-_-66+;Up_UxO!!MNe-CMKw9A8D58>p{#;QE9p<5fvcfTUXX?QtaiNl5yn5pizntq_uWFiCr#B&~7%Bn?6mT2HEtq`6~~!Wx)b3P#&m^HEw7rEa2BkA>1mc5gk0!z6V<GM(NEBo!W?<UYM^MiQDHa7c!vP3{czw>!xQ&Ozfz>N^>e8A&&bN!pC01x<TYV$*30lJmop)K!$TQPOh|L^*AFt+kjxX7&>LWGHJSjSFm&0U;STJLCX5NrlAIL?t=H(~z7GfXtmuYyr|HAOmoDGK)C!q#*SajSM6-;aGcanhl;^Op6R?9<@g+^$9i{V=6<^XyM$3X=;}=iQR2MSCSLxd2g3h_2D<1N_DyoRxl=QmZf${>d=CkPLsHn@A`^(ha{DZq_2>iyuE6Y8uPO=hqBbR2Ex-FoH7vJs|QF@-yEOD@wqS`s;u^zYqYI$9hY0}VQB}JUXCW|GSBVx;+NN``^1a!RwM`dz_`&QA*BdJ$9akRnpM5+{5BUz_!qmxP?BpI@Lr(~GuGi|Bu8dnYSVkx_9#l5pv+6uVa9rlzz#$CS`u|_6-rLh&HZK7DM?$9)PSTJR-ulP47VofEnkFECpiJ-M9gl<At7lVilmW@$*(B;NWw%+PErAqF>$**0m<5J+4~TWqBKkW>fSq5fr=Q2a=IK!e*mSEUGge-8$T)WsI(-?DKqMZ`GX6hbO$t~Rh0U2C_ReuZGz7UN|$w39a+E{Z;NuSkaT)FLUQ*;sgaz{Mp9Qov>^u7gVH7i!4oJ%--Rh@3*~VI>cdg05reXyq|OTduSe29Jjt|CQ%Ta2B-JpI?mkH-?XP$wT}IL_Bn?<74Jh;<P11IdRO3kM%JF<M{OYzEO0%HU;7n=2@mv9`nTw&cS3?;qB<C>okTjr1T`wdRFpe^y&|eSUy-||p67gP5HaztS$yrBpgrqA-?hOxoa`_(T<8eKbij4QBB&SK@?&?9$;u=W@4oPau5SmS?a-5{OF-aVyQ9cT%cO+42P!bGL+JPu_2g+$2%8H_=1LXv&`Z1Iigx)kjY0rYva!_6)S>3~d&bC(d4-@SMZgfh**#~k1zd1%%!Kl5}{neLr*4iRj>syUU-z5N;Bqn(WSq4xU9Fm&gyy>wU*mPTu-hBtLG=jndj3wT8+ZWxB_o(EBSn5mMQznT|p3%z0qbx08sVhBv-PSSY;aNIU9hb)Smskgo`=1h)24xv9rUST#aoNvu&vmW!g0|9z5!&Y2C(DGTZL*9-hvfIbQmfhYv-C^YJAh;%&T=)zJON8vDSI>Ch9L8J!&pWT1m9UIgyqE&uUG6WsD`lAY?k_hEMo^teGQgQX(>yS-Dz}{rM?JDEX_4v4Q0ih%Q$O8Kgo6HfvMM$qy{7}l`x#HM$)?Kpp5PaN?V}xz;b=hcDW0qj5i;Y5|XAu(o{+Aje-67NqRNQNUp(HcuAbM3(q>eagvwQ1BBZzl-_A6NllWppbNmh+4!yZ%%hXEwG+CZl<P;iR%b$#CbL3vAa8gEl>4Cc14&K@Ne$}Ob(ZX!o+N<<a{#rN6L9f~3rUsrrT0rrXq@o*K1n)(vciJ8>XKwgNLrAd-8ZUm0+PTHvKW*?v-$wafg?cafvj{5qwm_uFtFC91En8$W7HLtQ9H5Yt1Y7FGuqY~Mn3lc-UMYBSJx0ZB(IUg?wOqAkn&a8Q=<|tC!rpxrS;7*sv1VG{g~2g=oD3JYJIaYIS*tB0%NJdBt~WXi?3l4J0``~0qtsiGnQ^3%ejU!__@D<@S4LetFHsF-GctsXGZDlAe0kG!P>=q$AD@>cgxLpBudb1J!Ls5HGt(_3zxFgAk}r*Goio5u+)c9S^}kBYBM8HD?^m#yeQ)wgk^;u6vG8jfxRYVAj&lfvxaw0ffDTDIZGcd!E&mwyj0BAU6G~6Sz6_-JI->>%!Jnl_6oR=t|7?Fu(X$8X(Yqas%cW=QR;_6X=Nx)1*KL~ke1Atq(9?c#s&Q<rY$f56R;14QcF;p*@aG&8l1rQg4Y%03{aX4Wjp~&7iyz2I@6DGN+!4i6MXMQ7=S<XeWFyICJPx#<K%Uk5T)CShu6H!w3QHBVD_rE^4FW7G#98Hju!$M3y>};<vck^HOsdgTY#KERwiyBeNr@c({*wn$X!I9lC)uVJs~!`<WTou2Gp9CBuCb}UX7%pV;Lz)iEWolnkv|B!+8r$dLZ*zN#?1p`y}bEPSPedB6hnD!a6Vo%s*C=28`hwk@S}*>5Pd|#q%COpBIu)v1_y04Xa(}6OgnKCmFpGHnmPkYLX;WVA!R$_$DL=mJRDLf}|Fbw1A{L3CYSKXtJO*<W{NcR^6~0SU0RH91L_GeZ<7|6(QDU<>X=e9V37kGFYKfdmR$EHw8L(@${r^cs@5_37iyX0NMUDL+!K7wHw};S*x4!tgUq(b}Tc3JYmfIaUoBe@Pv)7&GL6{!*d$fO>e64gyuXFo>RsXmJUM;aoBcdWRK<>^Q@0g)5mizcv`^IWqEAa^ID&Q=X4#OD&eUBPcyh*^L_H1^<<?yZ6;lIOUFmZ(<Wtw55d!p;2Ev6()}Isv;|KG`r4OSZM6g`AD*YH5700Qr~%Hy5U4&Q(0DDLe&eYTo_ZM1`7AgMi8B;9RiX$Qg)`nG&gdrBgVQX@uiY*i;#A3OhdAvpoZ+^sCm!c@DsiYX?8M?)!nx<hX3$bof$e<;?(Keac)vfMS`=A}m%-@(PMhI$2u}CJnLEMOaPF7Q6sOK`j_F+Lu7xv@7RA}!DCxAs!>LJ}4&c<lP8%u;E`?JcC;^k<ba?#OX#>6SB|Imf;fJ$*FXMKbVfL<HI}6Wkc-j<aoZ}dr6R0RrpqW}K2Q<TQ+WWw%5}YO}%QLJV7<$uB#zcIvM>rKYwnxx!;GS`+5jd4|T8eY;Lku0tVW)S!X)<!0<4#Jq#knt@+3@tUmGa!X4U}C7Ebz;Z$!u5P<T*bQPb(OnHdx{C^uTG!7gpsiiO9nu9tBRGH^Mnz9B0tRUo}PELBWuUs@E|fn5K5u@P>qhpC|J;N%C7`1V!>0#t=Kx<Tx%%;@$t%g~F8j$X!N;RM(IOW#=)e^0LErTIZPR4{n2$J}}DmWKdPxkJMHgmBVZ~Y_)BY=w@nxd;+AlHt|)oBay<M+bdEH9Jj}nE8iNat&P$cB{v(6rX!L_$MuaKjx==kQyW0k7DP?agWCf)0$td`n==!gV(dAO+l8pjh^_^Bkf;LY@OMnq4<f4Ed~KrB8HfS{%9QA&X5B}0%80_&+!`c&Q=;QsW>KQ*08uw)jE*2`6Qa|W1=7GN6}B-rIZ-opX4IyvtM3H5roy}$MpQi%Q6*bP{d|CEY!EeB7kPUgqQIZB7^AL-s0F4uFp0ia=axkEV50MFho~M5)PYP8OrxhjZPu063<Nse7O1)!&>776vem)qfyQW!6sXPI4APB$-tP8l35(=F=Mw-mrZz(7IrIhda-b0b>ND4kkwD{MplZkn^=gt762YqS8D!9*3U1y4dY1(n?geOKX5zJ$+&?YIs?8uSqLXCg8XHwf!dL-a$fb%<)g>})4WM&6K>aL;kmOC2*JN<sr`j#IPoEk1n?>~b_&iO8r?Hx?Mk<?9L;n{K+8H@epB0iuM&_c0`&XRsrouDw1qx-q^weqIZTBY!vUeeAv1M<`(_Nr}db%H3t>>E;ows_n#lFb!L`$wy5N3|yv8&FnN>NpYljCPBq!cZZPj|!e=^Y2~z9t(uP&1DPTFa*AeZOHpYddg=-Wuq18K8LOIc)x&=Gezo^4}V0tN^vz_5qC~Py;#zTVMjdieAq=<>Qz<I`pGoYs^caW*NEX9ic;jn#`1b1!^}DW(w3kftI?2i3F-Lpa%H<KY<cJ^OUa!KotUXO|6|4s5ksucWMVdq4oTF5h3nCr$+}W<k_q8$TR5B^?&8*0MF_6Jk@>jGzCvx@YEOQ8Sav&brS!hoM%LGy>VLsR-Stm)_Hh_fb$F?xIUh9C3haTQ)$W5Y|4b2L`KxWC~!Q^(;+;|3iP<eKT@9a7T<jGEKAT~UeY8r(~zeJCFqc+zECO5MR+y}VY2;bQo5(ex5m>X7UGxWX|BZ+wKoh~mck@FClx{uPg~(>7oNM9++3`m>alpDO=*m)@O0W7^+-s02GFa<gY|Pi&!3B@N_kp)fM-mK`XNuVg_z^!X}F*BZ>2W80???U(8MDGmxPdXr`Ul;;C;V}4LvyMKNe8@d@<ob=h-_cP*v<aI!kcGW!J)i>YD*|10C<pSfDlmnwO$OpsQrtZ&xRMGZB33t9Vm%Dk&ivlm=R^Yvj&*K+s*Xb-n!_-gZXU1{bUcxcBV&?K$pkDKd@$)~8vvJdo3EJPjNNP(tl4TS9$|td)^9;WA_$+It+Up$?f=;f7@0BapQyS*-4NPXLF3y|nLuth*%Hyfe80Ue6`jxQIedPBy~+1INhj8BCp!RiNT}??@0XSG#(QtQkahHkMD;fb)5t)|^1iI##_pfo$<zlT|~=2Bnl9Lv{vap%Ju8$eQf}daq>X`v7aQmgW|KRSmHE6kzS;!5UEJ5;A{N1A0qO0~>VDC*o=gt`W2Z3|VFCJLMXnE4*dYzF=I#wh*{w3D~)=TBZoN>RWQ1yRcToI5n(s7GQ;5oDP({hAnuHVcmx`#2W9il(0Tpodm1%@etO1gw7yVfME?FI6V$)xE59=q3UO^j!@kP=mg}<x>y6&HFx*$9Mb~0gR1XpXdt2*lrb`@5uq9~yEUD(iO^ta*sY{*M%7+nta>M00VafM1PQ1B9GLdz8!1&g%+qQRRoh-z(O7n@jMeFNd*e|}bD%!!tLK5XWOZS38&wOa`hhoCe=Vx`*$U4PgvmsIgz9e70I6y~RWDQnpgJy=HJYj#Lv@1ApmM4Pr3zy%tC2v+>bm`{sH!fiRzy|v<E|yuP@%dWPXnMDf&0L?T!Fh5Rs6T(3Ft6S+VH6w&=WV;o269Y-Bp1xYz9-cH>Fw|s}ia<iLu~R&7y=1+n%*jowggnNUG+hRQ1fDdX3b62L_Efq`wZ6Mn(55aZw9%2oKba{pJ`=4Wl*Tvi;c8#Qs26^p15;>w!#besl+!(oNaRl>RQOxDit|lBpWbl&a=-z;6JioZZM|^R1cAHKazOwdEk)6($-%YRCDa-+Y)7Q-2!M?>=R^_j?N<Qt!5u-2kTMUWe%rr2Da51Ei~Wq5??u6KTCm`-J-U>qWnlBh>)u^h8P_wM9z=h|~gE_ymlnpGeW#?in>7SoM2`M5>=iX{44!IwhC#C(=ema#=CIMl>m;^X=q0_m4CdNHvMn3`9Dek|<U-4~aTJbiTd+^xY9{wQe^c4QDomUIaw#Z4IceM05^EySJMLQN0-{yW2WYPXmF*YJ^mUQMJhs=w9m$f%<_!{nda58PI811NR)LS%8`X=#9)BI)Qq!Ywj?hv1s9*1GS0i{Jce@<{_7+lL37T(WOn?VY40s;>@tC_G+AUR-n;1qx*mc(8k?>k+>_D9nx3ZE~>|y0QDr$x-g{S<L?rp)=GSCp>837rV}P<dcSIHTw)@;E1l+Br9xdFQAc;-O@TTSq7<mjV66=(XrS@-Kw}?J(Fk?U+PlxOTM|U9&Q(KKedj}KR_D&KkHu&z7%g<T(1S3hR`Ygn8}~u-m)^N)hNH|=>#(ziP2>t@u=l{NQR?F;=}zMoWYnR(ykCwvc9=fl)+j4GhM9vIgVHomnqjhp8>4h{byUVal#xJb5R`hH9N|7kWe-ZcOS@ST=RQkJrYOysQ5peC%C_5p@R<RE;4mDeyHAuhF{HZ;N;Nn|eq)p_;3&PCrXG}*M5#gC{B$VyQK^Qbw2QTz1@09QRH&-KDuWZCq+75<l%_yw&yUj1lj}p7C&D#wJYMU4)Rw^+sVcbjTB&QJ61K6|;(Tq1GN35UZL>BbQR?Y3C|w2RUMUq4l;#8|<5-lX{k{U)RtHe}1f@MMN~f(DrA3|MQ<Qrxv>T4{#&>XA8<l4646^Mg^@7qDD52eqTGrNwM_HZVPDegUysf%gP=@XHouV|`4j!K<YYo*QN)0xg5~W+Vpc|pI*H|lq<hGOd{+>ZE^|jX7qbU8d1)U(sR&g(n-b0a<7Pe8J!M3y3pWrCN)*AfbQC4c3zoImXk5Xry=Vzd`FrXKGiqdYU%X6UgRg~8)6W3!L-Wc*79RwcG(cAbyRpK|NSXtykR06+eidHBR*tYn--@2!Nyxr);X6b9z|5&wXhSklTSn)dXG?{IIQAsE?0z<N~=EhvrajurpN*x-%TVU)An>E>iRrt5&TG^k20&PV^Sn>Yfws3ui{lC|qP2&pjuZY!1&OO1aIEpJQ%G=LFC0DccTOYtx-<Io@uo@QDaVCUD-6>Xyw<EX5x&~OGzy5fvdLE6{4#Ao<2Irjxs7~t`Rs*o=q^11;tns#3b*K*4c??%rORB0|)ycR{W3gHmR-N?;4_n{hQNFo4oCd2QuquF6UjwVZPppX&PKq@Gbq9u3Z3TTAU{xcrnj0^!wYY$vCq7rYtlR-#N1CgBM6OD-3LL}gDp)<hszDW>0=@`OtYmL?Tl8jcVKw8hs@r0XHLPAqvFavPeKoApeGb;y&plMJM(q}qM*BpglvCBisE#^csj*|VlWN@(VFHoCoN7p@swdU$cohJpm{8RlRST$2%io_i^`~0C|D?K0M*^_p2nkhaAmxEvWOt`{KU8ON8%Ss&kyC}K=9TIm4_G~X#!+>nshSZ~qm717RTn-Ido*QEyf}BN0d&$@sg7G$drquoAl6zYE4piUayNrawRaM)z6GKxYG3i<h~}Ysx!(avT_b5H&sExZw&^>}=R5HCZ^zRP#c9+qoQ~o54qLd}thM{OaZYaT!%11a!>p(Ui936<byE$+xo4NPyAaL^lmT0iUxGNzS#VAjoRcx359frYm0?x22JS|ChxYryIS-&|574v~nlLgCX<9&YdJi;%o@F%GjipQ<nWFR(mJ6>v?$1S2UzlbnXzHZ>`l)G7I`q+;3z`~O5MPw0x*wWqI86&K+!#%jbXtGXTxl9`<0(DdbD9d!)B|bGcMDUwsUIdRTA!{4bGk81>nbp3<#j*Iseq{yn0w`*8VEBEhB?VZ;nRgs?s>`xP%41ZEGXw;D8t!N1~A3n#$bt3of+li_|8(Wf}_myt~uP8q12#{z!;SNrYJ#FGaHrGi^Fh!JFllGHAtE7C}GFh2SXWX(d-OKPHIx7k7NV_<elW&`FH{i8TQkqx+mY6jii?)a5j=QBN?VXk^!^=)4<3hW^QLI$@wfKeTAf*x=6Z(qyfFRHHiMk?Ir|C>U%Qq=_F|^PEtE>`$&3_h=n9W=2i-4w>bgHijTrqlJO8pU6_&v@L#)a-uryN2}wthRH7ZH(k=e${Tq~QUL(<M$9T`r?Mmwj-S<_6gNLTf_nzavF+^9X`I#f!D*T|H=C$;837SUyO(-genoVO8wY`vS#bRQfoa={-6|V;(>Ftvu>)pM}-wv`G3E5o+GF8c5row$va_zRzX3Z_&(IDFjWbeaB$ff~VgZgW?ov3Qo0k6l3M}j<8M{?vswk*i80(k<EcT<5tTIbK_7|7j>Bibpw#&~V5qzcBAr+$35jB!)_2~@k7rP>8Do-@YN!dMZt#V27LmF;7U*TS!TeoKkX3=*AotB$1^hsR=EJ0s7MaqPPp>k8vYddlCJu^KdvI~kXz@-twp3ugz&ST8LEA!9rM<Ili&Qp#B=V^c8JO~xu=Yye}bX3jnqV?Ayh*ZQ%$jIm0Lmubf842)~zSckcvF;+@nGTu|FwqQJwjP<=Tc7ky{DWe5(A-b;K7L0w9@jS9(Dc+c|8pSvijLQmJ1sH3<7_Jr5c*g#=jLkHTF<u)!C5&@BgY{gYlZyMnjNP3wo}KPvoQnx!mGNHFyfU^M-FaXwzP7hzT(OUtv{jvq^Y-rn*u<oap&c}2yw~c-2V)%gu5t$mhpaL`fXI(Z96Bth*R2sABF5JDNLcx)i?Ayi#Ct$eAyFZUaJWyoyD&HGs=49NbEHTcoEz|U%sLmqk~X(2*Ck?mhpKHE;mTfTEcBlAhdRi^EYn`YuYnY26*lC6{bK<}Z+E%|7&M8vN*R9#hKa&Z?SyXd%zWi`V05q#RKkB_ij~;yq@$f=&M+7)pQY6uNXdt!eBTXjh~C5159Dfmjq9wAaE19wn@JjMk%dox!mYUK2jB|xXQuGu&z-p4mQEj5+<$AX_L^LEg{$8(=x?L>#9U{-#d(XXM!8OfAY_$#58*mG{wn3FMsPJ?A1d?cip|vwlg<v0RSn{5wB$U{=4uMAbA_uu1=osq{9&$U%a_N5D|9>C@BAJ_Wc7W<q@-N^b-7x=)d8K-yW#4Lczv}MuDal=3$D8}r@AZO=w7as5T6Np;&(jZVpR)P1*BjX!m4kJ)sMic!Pzs%8bE0r%ymyo>}k&w&RZ_)yjW*{2x}>#&9O#+)!si=E5oWTgLO9satT%su!c>OXp=?2-eYY4R#;;Nt4*+m4Ql{c4X`~{LqY?i!_D&;s!4?>hw4<JY6_})p&9{I4a}$g9on(fsYXe@+A14mF2@t7AA?vm$YVpS9u&%_Si?hM^@71_)x<uvdW5P?j0D!Gz)JNkvowKf1`Yh@AB(CJQJvZD@d2S~fT@7m;@a!Ns<*S3MX1I*q&f|us*Q<!swSfv5UL(f-J8u=@SRoL5+BK$38z{q4x6l2hL06CHqKjglvpjm>cDqa1Nw);YL#RO5K#3=+7D8lDpW0?>VW{@>{K0WD|?MxejL*je)p!Up4@FC+N3iQHaw75!ObyNY^x?e2QW>|Ah!Y!O6W@$gPS46tVC2VQiZ!$1q=0J=CCt?Nu(0EP5;fNy1EF^I0z_Z$R84*HnV+jL!usc3lus_OMp&<C4bs0+k$50YtixJ1Kl!pAqASWb~J*@_qk%q9{|u@39;txR=epFjnGQ~H3ZNJ0jf?6G|GWmVA!1lRfVnHTFc`S3-1#F^(oL0)DfU~tLzo1MuGZM0JRmM6RZ_6>}qvW1sZ`)qy%bC15}L$ikJVdKy}s~TP-W;6KJJI+90+5yZ1^R=xR{?1eyU|8?kbLYB1&B0nj-20mZBM^-@i$v#!l*3B}zpP<3^n4gu;=dyi>J6yZSQ6KGjXr^)(!2y_DNdDN0{e*!HEKy^_l4vX<)0u&nipB`wOCDEolRe@FB@8?hlfa(P3UEbxZW%g0Pb5_QV8K42QF<VP)b=I?4k=|*K$x{vCxlZi7rd}l#wL4D>c!m@6jK)qqJ5t)`ey^ZcNmYZ{=DP(uQn<_LvXb$%Q*D4c@s4D(7Wc4TUL_??cH80|0P61&s2wptXJy?aJ%i@W?O}Pm0&Lyl1FS)QT@5R=y-%JxsQKPA=o5uul3}Qn7k%XbLc;Tf(&vv)&s6A5K!-64YBWRU<xhG1-yc0Mq*t4R6DSqp(X&86<ueO&1N=SgCMCWJJ#!U$(Xi>6f?h!B!3H|!R`m2hdUFMyRekUx2`>V8_jnc&!ZVd+&lu2hXl8U?3<bTnoGVlgz%E#)pr<YX&m{2d6CM{{ZVWyHcm}}JCx)k;ja`f0l-1$R3#tHo4aZgD-x!{rYeR414n3P(uJ*c*Iz4^2^xU9%J8L#PUDSWwF+4l)no);mMesraPl2unYgH12r|<BbJO-Zjz@JD84>o*{2t0MS@Zy;8fU(Mp7QNM6Y|iL~d!t7#dST4Gg_f2rcow9JAv_1t$#BtA!`hnO=}FImUId)r0E7n%+dc5RfEK}z1}{jW#bI`$s9sEp*mHPmRA6_uGY@vs3xeFm*P%Ci5xoE`eW4%NO3!D0i}qIZbl*u&GW1Lg{KJaN?0OwARb1O%_{;><-s*<d2XB(Fo8#QUE)6F``#)H0b=iWJaNw*mgq<^X?oMR5#E#Zg*j*|ds&75+d^Gk!*}c|yckdUbS~=c=_xdn@{=a|u=b!)ZA3y)`uV3HMfBk<9%?Lv")).decode("utf-8"))
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
        if not _FULL:
            _record(obs, "trajectory")
            return action
        action = _unit_router(obs, action, _TARGETS[step])
        action = _market_router(obs, action, _TARGETS[step], _TARGETS[min(718, step + 1)])
        return _align(action, obs)
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)

