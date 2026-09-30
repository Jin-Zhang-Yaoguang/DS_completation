"""Standalone Contractual Path Forest Hierarchical MoE for Kaggriculture."""

import base64
import copy
import json
import zlib


__version__ = "v115-contractual-path-forest-moe-rc1"
_MODE = "expert_dairy"
_FULL = _MODE == "full"
_PAYLOAD = json.loads(zlib.decompress(base64.b85decode("c-ri}Yp-kBaU}R(?q}NIe(>dQB^6sLxKt&Ss+#B#4g>*~$Hw?EknI5)M*sKO=RqEl85tRwYw^^rlDh5gTfFD;?7g0uk&zMq{ptVxmp}g7e|-A8|Nit3fBMHi{@1_!=cm8>{eOS@$3Oo0U;p&y<&U3!`^E2m_vvZ%>7V}iZ~w6T*zcD={_7wA{Qvyv`R9KB=@&ozuRr|uyKlez;g{ckT75eG`uN52|IbgW-+%h`SKl2!-TdMCXMcA*e!2YMZ;oGo`^~4-?(XBaf4@0@{KYq4{pO3Wm%sSkuaC#yK7aAk|5@EU+*iN+`yYOL{R8h0`uk6(<L|zI`OV*a``!1y{`7SH=-wB-zk>Kh?ik$thF|>f)z@GCVHwTue|Q;>tFM3iR_#H*{^FO%%M0Ip&GJ{@e192S?d$%>^T6M}>lfc2zkB)Dci%_8<(FUhuk`kP<X@kEw((WS09W3L4D@9=#P4Ru_xuE}>*VEIUcN3hy!M6OzAiV+zx(zFd6vlV+Sz*h;^OcYUJk5deUj|>+DVGv=scM4P2zw4_Pls@q7?#ucV$w3vRml*MKD13x7hUyy-t7eauBY94Zh`ur{G0zzuMlX=wkK0`~DRMdcR5MEjX1flY09H_9fqb{q^ye-~Zu%9KZYitFOQMzh0)K^~u0VS9mnL?#wfMKI2q-G;;I4@2$#N$ij-up$Jaq*NuGjhj8ylV`smzblBUk2@e)~=7TQ*Pv81r;gEqd*L=yB-+lXA`X#Twg@4KGA8t>&-yOexj`^=%`1!a($J`VhbCVa8o;M!){qPVU?|;?n>+`Mi{tNBz$t56ONTd(pbT@>*`~JHxPQN&Q_uc;j*9CaF^Nd|RiZgb~FW|4MtP}l-^)Jycdha&Y!_rjJr`_I(e3x8Gsk<$@zQL()?>cqMf$OSv?`hXlC2=UtMP(2xS#_5n=zIWOZSU)I>F(pw7}i3CU=-i8sSGwjle+gWs-$=C$5I{<V7Gi`(3E?=08dmRs(h3d&t5G8NyQXeNCVHe%&pt!4r_?O=5zR9USoRtJg?$JxFcQD;Xe4-96Rw~a+006w8Xo(aKWJCzt>2`w~?G@vw%jpitqk)F>JX?FdlpVHm|Yw>(^YwxqA+MQT&z+U48#kcq-9w;O({%zJ^@8>|xvkc%|Mj<f?`fD7*`~WAy<M@7TASB>@|Bxtg2{@nbID=`)QI9(7+|YQDex_9R`^m*4#M4^sIJzq7&L_Rq3AV!xRSljVn*8<Sm1oi6Z9Det4k>b_LAtl}@e`=5<ft(R)q^D@49>&q9rP}`-@6prcJudNkXqrrXqbyo*}DZ#$F0zE`Eb<@}I6YyZyGyMLLaC#~<fXa-p;H}@Tx&JDqgg}Gd++Lx%Mx{JuV-|ES#NR{T@v;d7aOmwH!A+3(p8NZ1<6gob(0D0RzkPmv-;w(|pL$O%2>D7(RqJI45m;XpFLFH`pdURV)i1tM3I?dY6eIUMYG(SsMFr+3;Yx9Ku1{WY3cH_HW+_)Hu-Cr(1HDj<OTc0deeqt8=JaxQU;f~v+4cv~Af&>c%QszOJ_LDW23163?7JkcFz`F>|8@AM0=+?c`pa@@uV%PIV__5cLiaays=9B(p9`?^{uJON<#{OlQiFNmCtwOP%#pc{s;o3d4SbrzQzBwZJ^~yOXG!#aeai*9U!day-@FN4l)<S=ovB9rv=2Pu*!LsJB&%*EtZZl%hB@yM3r9M5G}Ru#y@wMvenKA=sunmnJGt>%F>-UF6rP$j5ob&svSNiO<&uZ1;taB#zWsJNoVMP(+yhv_h4cDt7JiE;4Q~%)?km4K$myl-NwgKwbx_Pf5cuU0-k<8S_Ah_uz?M>+a5GE8=s`c0@<OXv0-N@3N{7*VwCm>&pAQ3v=1=57Mm&LY4$!!qi6qFCBCM;2s+HY9Q0W(Bg8<{QNZ`Zxfyc`TZlcGsV-_-fmdx$TPsw<PZZk4n;W22pw3lDhzMu3AkzeE=x<WtEYlVdVq8#*)__#{Xut!xd%BlD8(!Qz|(kb!{e)S#UJ{7dTopc`(vODMO_*Cl`28qXYaB(z;ule~3kI-&;5JuRiXzUz%|L2z@69tF&M?iBsB04$gIrI8>m2(D!JLnai9T~O*F)o}J*f_K=n-C=Xi0nCI7Yss8KV}g*uN}^;w4&ZaS^Qhj1I0b0!kTiDE<dNsPb*tu;A{x_g_RaQl+%!Ec%tS^4nCHWC*Wy%@A0e{bZ!}xCw~#M6@9!f0I&|V_Xn+?kM{dPg#{5N%^BYJl!PIW^Q^Tqk=7{6hcGLKgohzm=qQVFTCY|b8IclVUE0X)L<BL9!o6hT6f6!7YmQ-)tG^dO!(=#7Zd5ZB>BMNc<U4t9L-8@gDw*pP5~6Rg6Y(s7qm!h2qXp#~nPs4M%-DMiL_fBkTZ-I8h!0)T;?IS6J=v`^t_GJ$MLNlB)kNSG0ppoeUK5yTC|}gO0zmP^MiZr%w#)A_tJf$g$h1l=GvL?BGwA%JQ-Wy`Q1ZKqf+!iXc`94LqMRTTW3g<Z(aYpnDEg-dLKvyqmEB>l+hC?3^Z^1P@WmQ`DD{iMg`(iVl@4b>JOa@eWjsl+@O=XaT4V1ykPqx<sK30>;w&9oB)g{+<#<d~(ydYo!@Qq1@iM#2EEs%GJL&^S-=;k)(q+dbVG=J3$SDW{7Tf)bFV26ZPO~cQx$q74-AUzJHCxSfd(9rE1Ah>HD5nG)S3-t@q&8W(oN8{CfT}0)?*s`+kQu-aOLafH;XqIb0vDPuR1R027IPUc{hzc{S_unhMf$Rm4DUF4MALg6qasjWCiIX9Qjgv*|K!WBegy-}+&aX+1Pw!cF}JhcspgM>G7SNvOWLfqm&qPQmQoF}O1(i$Iv{X|1IRBjm;z_$$@Kp))yNEnoq(w6fYn66xmszkV@NrnC1pZ#<(Gm(kw&VOo(Rfsg{PrHEh=F)@@c4(n_{JNnI`Me=!G^Jg~0Mk3{y%LQL1!JE4m{lLcmylILj}zi<l-CfQ>jcKUAujgg0=9>CoU@-}>Wv(f^#F#jxZ^OQz~VqI%PAV;KeKQ*m`7Zcp$NAV3<4n-}zcn!VJ9F=6+K`MTlxWhqtZw2W0nU(=^tXpK$clvY54A!alvogu4!8l4mhrd_LHRLhHacckYk#!SK-T2oj#L1oX@6&sL)r3oK5f^SQza0E+^A_LU7sPni$pvX4l+eu=taTH{jSPSf*%hMAPRHsYIhN|E(HFm4q5X9<)hBP3vWHPdIq`M5D10F9|cskNFU#htV8&U?4z{sO9eP38dzF)}!__mC;!fgVwD>#Dhvt=L9U*th|idpWj4H>J_i$n`Q7*6p1<PQ|=X^_db$Gb@4Ws{L95ZMzYO7(08V<opj_A?n^VF7KQ5^an0HZj^>tjv!v!(=Ope7f)}-L7)9oWU8R-bG$qs}#Nn=!Zt|@^I{ELjRD}WBns1-lq9WmNkxu;BkWeSmSilyVLGqh)RRvsH|@5fmDa5s!|e{#JJnop+rRO61&w>urGsXxa91k?Guv9MAU27L_nPG>LnJ-S5zS^%owA&pBol4@AF{H#^tP{%ZdONm+vsga|xZ%>iWy9efRD6Z~vB9gJRRs;66G3=(-u_Vek$;0?8R34ZKPt@XUW|mui3u(KRK<XJk|oE{Fs&GA%G#2QZO^T&30fWHQKZE@Moz?unB0%6o&kVIYbBRx&6Rwe`?l$Xk!X0gz>Az$FY$j!YAXo>J1;&M59HdnnuSX2OiOS&a9NH8H*V$I4Ec+IJF9@zPTuw*8ykGd-21t^>l!``{uRlw5SzIivkDx4}FW8#0zI#W2u_pC9rq$cXlx{jo&oI7XX@D{q2l03X3+#pONqTd1C~8fO31Bcqq(ZNDsG1;b;6pv4U~=7PdRp8$JJe!B2u0}O)R1tiq5c$7z?iR+EydI~s|kc<|JigIa%TGj{;B2}A=qO=H({dSju&?&5CDGZE_3KgjmGNamqr#Nn?&&WI(m=VAta;#Bn6l0R4SP<Pj!}~QDU&EfWYFUtgLCW!AMIMJNwosMMZi4Mo#j?_tQ7PR>={YH=!+Ed3l!ZeEu%OhGosE*<GRXA&t{_DiHW>DNx7GY{xSZM`p>v`FxKqZ1<PLBjoD(dy?TTjCDtnEjY_0#)3XlbK(h5x~oGX-7#?_jXpl+!R2AB$fn4VJ5=9LQS!mZmeP5VuS1*}l53JAwR|29=T4{uS*SWpnT6fnc~AtmYI46()5>^&Gm`-$beu$?SU3zhg{t?jH}{m~|}h_@Gcc-^hWbsgim>1m0=i=Zz7Wf!s~RReX8C;wU&U22lDhYe?A;A!{r1Ep@WZ)XQ+w=u}1z|^x<YM+(pVzDHawHQUvf2{nV))s_~LkIL0&Gx-ksv&q{GfVAGMA_F{oZF{FrGuqqT!Kr@is<6pKIwupyceY)l%U8bhec}Y)4_-y%(3NkbhSP-!G|PQ>%OyMpR<B-iMn&#k|SmMmzS3HCP-l&@0x2u!f(F%`tJds(CVVw$+Q_Xnah;R@cE$(KVmcI=WiAiDDrbD!3S9}YdMFs(_?4FJ|XFOGb^f}EA)@ZT!IKmAD$BB9K@p5g49J<<`027yh=i)Qqw@vDGz8K*br=v7`1@w-l4*nq$%-0$_?jbw7d2^o>0TflB|^hM4VyGMdQn;ND4#2I`tj0ZYPy^Bvv{<gwMjCRIK@?`c)s!X`x&%x|GOZG!j;{-*11)Pw{%vP}p9|qnP?i9@^O@J*)X4IJX-*^Ft_#EmgkB)0em%jFQZrCxZ1_U33}5l^i=;M%L@qhX(G00T^>beA1v@3N9;;AA&KFz!#AcE%gl&;ZzcYfFuzNs*9IY6*sx$0pc6@@;i5*v_UZ<2`M$$<k@BM9!dQ&Lp|bi5dw_JxXQ9%bd^k{W(V3Q!`0A&9E3E-?Z+Vpo%BuTSfxMeWeODUEpUVWX4J(0)uGrrpzv6sXh^qw2IXitkvdW}a!d!URY!?l%bI5hEzksYl%zA9l&yOmSTq6byi}FBp1EssJl=E5i39~1NV32o2EBNqmr=EC%s~dF6`&fJM|+bdV-&-og=w*Gfs_CP^9kDhCelE1O$T}w%$s@wj|jZfZ)@3vFO-imh-3iG**&L;1iYqmS5(99tIC<>Hr)-Pwt~EoPY4XH{Jb?RL;@(*F}e;~OgVKjOM!EimKPSS;+!`wOAVs+3pl?Zoi0Gq*%^T~3CT6V$Wj1s@VC~rHt+Sqw8!Nmw6Cc3jAlcMqN|YSgtyO}QOB3CNd}3CB^sJ3&zTEQ$9Y)i1+6Ov<VU>Bb#RTw6guZHN8{1;tvD8hjt7x1rT6-66@5a+!lM%n9=CyQ2KXq_<8$bT7P-+2h^)JaSfd??gfn~jgB2vU$+lH00^MBTr@YAlri+2N$gNcL`{!p_m%+p$)6?hE>w{-&?kR{IH2*lbk_Kfp!c}+EqQX>@%Uv`Zd1x0{rd(XQ%N1BJJm*EMN_<{ca`mww@_4*=h=I>h>Zhnz3#>I)y=m&zPGtKwvT>p_6naA!Klaqm+>s$=nmE^&b+9GNB=7<{Hk|`Dyp)73)ufuUcX?6&1JVqoa)LC+>;fn-4=pWF*P2=Pum{Oy=-b@RowT4_z#8n8A%;2<6r(E@69a_|8QN3?E>gYJm)96mF;;?TcT>DaSD8(QEN(!7^iJfvO7h45#MJkdwwObF6tD)%@J0&p<zw7rVpos-#DAaK6%61TCdTx>jBXEyG?Ja7=~+8#+UUtw65A1yEi)zUfwVeUSJYsH>rDZWJdAQ)my~}}Z+1ckW$&1zR~j1z4BUE9uGlSe_1f+yD6sQ}(H*V8wlwsB64N4P(Z*Cb4U)GagXUgRab`6-N6OjBkyaUN+)wYSJx_GA%L-Wb{M-Ytc6)3l=PbgiHk-IBD#EOV_=(gj;uP(!Odg>c?kDfB+}Qqx3Nnz=V$nGYzM^;`^q#l#Whv^U$&kk=0Mw{lct2-7ABZ+hF{C$%s2{O)w##^B+^pDPeRKS+E3`APh^w?S0mFQ-22hr1BOxdD7`lGHjnHB3U#V$Qnq@P<NR!sK_*>&kX5EK-#%T8Gpgvy|ao?uENRuOc_=B1rRia5Gw4?ISQ>OJvef;t*(2Z=hqX1;xzFZ+K7hN7sf&dr@9eIgCRR|VKoA{2<FztPJ8Brm|^e0bXjT!4^M~0jy2=*XA{Yw;v(*YFit>T<_s-<sIFrWhCq%cv0kLPXsb%~zJ%f>{@3~gae;y&972TN+3Q91T-44kwr#_tHd2B2fyp(C)2wNO#6;MM0AMN90M;O8i}&MXy&EI!KpU}@m&DpXO!UAwO9p7S~%EFlKQllFpdNc5CU;fYrr-8?LXp8L4Qi1o%PoPY~4#~7aTFj>Mg$Wh6FYpQu8p}{q)Vm6N%?|Otu*yp7R&Wu45j{h*KjcV1g_VJPTqNMvH>Dl<nD=QIUt*rEPR%6MY+-is8>ss1)nZ?-59Ai*a(y~o5X!}qbHkoR2?2Fu#M4lv8f9^e$#@kK1c8+QaMH^2gSkT5kB+dt~)+(eEMyMQj%0mn#aVS^vOO}EO<ia1i=<(QKnc+NC6Q{sdQh_sAv~55=sWeurcLhkBVY_>*GJUA|&G>KLl;&*h5T7Ru7{Sm-R0@hGDp|HrR8LW1sF4$u^1{0cf2#MYluiPkKT8zQfL;{WxVK3)D|igBz>&pK`l!3al4P&3u$7s(pQhKAz_X$gDQra2@FA-oqq0MMcVSQLI3v!JkeOm{#iVmsmhIju9^EJNmb5H`BA3gvgEtgy2y$=f5TilP;W5i-Ee|}r#&Z#9ta;kT7`EQC=cTElUf&axwydBuBBIAuaWu+RK^%`PH3+Tu!5*4-y|_1%1lJP5EM7S%)FkX2S~+*=d9LrJyYC9O`azhB?B{9b$>+xJ5-~F$*7gPLMRaJyp@IWjMq>o#YagHRB4kE68##zjm2~3a#x3J!Qv}P<0SVh+M1}60GMcuv^laj~sOlEzRP$~UW+=egn1d05eg;XvJ2tV3mBZ|FXS(BXP9MusYb}}LjFeHolWch;GUy^X9D!w`OKYP?p?|6A@YBi$1_1WCGZrp*CLSX$oJ41oK?3&W^x2Y$aDx&6VYuGaRZ~Zh?I;@<jb<J4Q|0}c9eqDVGE3N%be`DSSG4g<_RfgsV0-SU$|6L}n2+4)n8gETrB_lheon0=+9`S73t)~srd6E2@Pmpp``Y6QY8YkQ8Y3+l#Tkw9t^ltpyr@;znI!n_DcK3tnj~LK=8}sSrbFJ-#JyIrNSRFG3QuuzD0&RUgajpd&#6qeB>L*H$Bxn&kYf1);@#UPCA)jxOu}^6go92F)r2gC?(b;k0&z(C-RkW$DdK3+Mgm8GMh;_&Z+^ET10C1#5@X~;3!_}aHMYA^a>x|*(W2Pld?MUO69<a3dXvrZ*Wu}B##!?P%tAI>RY7g)`Zr?;;RUT^FRNz&aswXLUPb#fk7(xoCQGc1S}CIHcj$G$(4K{a?pjR;6of4{f{rAuyjLTCQUKOnIrRq^Ucyt*>k+*7(#9_>p2i!R$SL9-{xIn{o8C?k^rfckEsDfCu;Q=yYqcdB^-i|6&q=#0Zc);fVB8xl$Y-Rnam`+>B=RSeg*DFIX48pt7w}8*P%%CcQQ21j#TFVJ-`XJpN~TUY`)ag0=m`NzWRbQcsX!$J)~3Y%w@C^xDDwsHy_d_ksJjoZ6YK(_oNC*O|Mf{w{HjI;=n&4JpuvluYT|D?*-q;vrA06JjJE);vh;@(pDv6t<lg^4n7*-lJQH*cHLjf`Dnrz!*!>?g3=?2*)0KXwS<s8oKx`f&_NRE$U1sf(u9DcRA+%dasOTON^gUV_Kvd7TwUOL$C6=rES}GGSx{UnfpFs>!Y!`QmPqDcGA?<-_f;>ECh!Vx>V%5a<LZ%!%=btdzH|5xOX;|(d2;msErz`m1Brq;-ShwqkLVoOW$@PoZWZ7^S4!}IlZHwQhA#{}JctUQ$v>U)bDXDwdOUr3M%YYA&TDAWxG9I6E-QyDj3Me&K<e?;Br6{o$HpO^Q91ZlinMD<dlW9rboFi=RsCB~ySh%t`#u_y#N^0}{d_LF{hjeQY($(!m3GcvJLLQL`*XiM*P|*0J>Pk09SlC&n5Zz?KcO6aPtR05H@q{M0T7ngZH_G~{{X(>P3?KPO*3K>7<+hBAJlK~8_KA9}D=eT<ooCu^ohSK?nB-@d8kONV0~5F9XU7~c+9?TCdz+F|w46T(W%F)q%AM7mo(%&|X$2Ww8sN0Aw)LQc+o?d)ydcK=D?FxYpKw-+N-uJKf@KFOjk+$KBr?~Gm&UcGtZ22`1a)8bJ78ce3y?$;Rb6d@>_WWTwz2&IZAm&Q;@JQ_^pYr*iUt6`X`62mobS#Oct`+R9b^*Rxcm4zdZJXG13+7idzm$7rxq4LcptJ49f4WCj6zWUlPNEM!9EMD=Ir7t@*rp`b=!(ZLe|n$Dsk}+<KZK16C%wpa6f0o3{p0zHXfvlh{7v4(8#-9Ps3wHtAb8jd18_d197%BDRo|OWyUH_lyI-)RU$YxR`$FQw{kQ|o-wU0$;0{l5IoxcVp~L@kw)QLMJesj5}EVNQB~h$&_*dd2is^o)H$j!A8hfzsjJ<E{YN&o3#%NNJ;!e#mjMSV{cnt)d{f{?=mv4#9hqpT88Zkt-Zg8?vbEjW1n?2l7tJVq+^PK!_85ju_o3hFQ83;J4SqG~`=+`(3Jbv#VR|2|X31M7(5=}l2?FUAubEL82db_DZvqbm^flcmR7x{qezAv}L{VrenqXHP9mgnLp|ped9zAokur;D#rsEC&?)de$-}viF=srT#mq2%p>0;7Am2j4sF#qd2PP#7JxapO;0+@rveSFvC&IjI4xlKg3G!9Zx8*)x&Row>VHn`plbG>=AZ{~>))Qk9?;`<tq#qYb3wdw<I5}yQS07G&?xr=FEp6(gqU|ZZdcyv`X-O7#x2?LVRkz=xIv@!QMnDLAegAzk2u@&7rY`I+aJUCqJ*r+y@xrO2#5e1v$zf2v+p$$*AMYUm|Hob2*`H(Q`9f}3wpm{EbuM49XHdBj0v@GlxW1l?#7x;a74I9fBwGnXARwLDEw9oNG^#)Z&oyb#lDJtf@N;j6M%2Jd>m5Th(2*FW>pAs#$@eY;c>A-Nnnnd6!NQuXZ*3y(X9U^zDjUMVX9>UvqYkk{cty^$Ve@2PxT3qRZpsI8&`M4!Jo5DrU37oXIFlR9#2{$GdeGkbs%jOJfJ^?BwwYIx2pffYU{iSm_SyIC2OE1f<ot_DTg&+{XdzN{!C_SIF35{_v9mb)%V}gV~R>o|A05<JTgYb2A-)<=@21AshzqxNqK(Wv?E{Hdnd5#GFDMv96DfI)QXdT&-9>{JuU@O~_qb=Bw4gywh=E<k$aCyD-cK&`_XJ~lDbxA9;w@VjV*1N0Ec0DpXp<3g8?hX~FYoevhxSB8qG5*0fU?=Vac>PD==<S6?<P@;%8Ua=-R1}iVzcpvE$i4WI!!}9%pXp|Eh&q22d{le2XAzwWwG1n!TRR!Wqoq6MsVtYjdo+umju}i)Lvwl<BZpFutU6ux>`lhUns!|vpJ)EYh5?Dj*v$tBLdM;EBvRJAlijzeapDr4q%A$nMbSnIe@BE_+TZ0+QIK+lzSz0*NnU=b$-aD^a`KF}OFHi9B3iTFf+%Y0gSV+A93j#1bWE9SXCxB(C@%WvV`NlBc~~`7MR0{uzYnTlRS+SaGeW8azjSt~Bi1K%eZ(|Ku*@60iz7p5u9wP|y^#H@cd1<^5op1j6BsJnMKuvL`0J`2APps8SEMtDdutAz#S|H|E#}vatgpG#=cpm)&|i3wQFzdfRNBcq$|y=rTo4to_;b8WTh$O5dkWxO3f1m()LHo{Fn!vUq!T51NBf4psAaMzt?W@8h1-CbWUvWl41CYBrEO`RPpmG97<=4vYh!zn5zvg2cL%>O=C5jqhQlUE9EzR7BPEz0f&q!}P!G6jGcZo-8=kT>lVi}`dz&1ORS+u>K%`A3ff$sxvGagjt3@$M@$U;;5<(ZoRDLCDH|M|rM>4VEWgL}+4Lv+YzjpJ7xf`3Oi!v$=;cKT`Cd3u>xd=L&dH!n{Aq_6bF~}Y8LD=Ajb}p1Kg7?>0G)rdqc<eNBy+D<|WxA=xGC*#jL*x(;VVsPKM0?Zgrpc15qRs&p5pp(p5v{7gN@e>uQ;!f^_wsBj_tIL|n5;RK{KTKyNEGf{73i%X{;+E)+CBo&uia!B0Db}-o7X7>6rpG<b#_&zJ)vINfxTS*8nTA>fg-EQ_@{A!qJt^+4B)hCvQ0zCxO`vd0O$J;G;3c)U?lhcG-Cl+4zF=#HBkiZMTsJh<UCaO=%9N7wnu?3Wpi92{08r`Z4q=2iJA<cCD9R!q3$rn99o!sQ>L1D0nVs2<VkXwj$dVD1T>`nx$;z%mGczr3Qo|oC?W+!d973=>$&LTlxA;!=BT92D<9ZN8#_5^wTBw-t$}x&c3~FKb=EMF>$dg&P!32nPLV2{Pnu~()h}hfWWHm;c1D34(mj?9;#b?DgC2hrtW#baWkuwa>&~6+I{$quDW1iYrb16)1nO#8ZxTso6$%h-M@g+4s&?Fs!mfj{Co^rvZ)0=WnnL78REX@nkrFwrq(HA6kM0{k#;n=tL+1>u1XEB8vlElUyX>SBpFA$n(_*GC5-nQn+g7&2F3}JOPZ!oStdZ&zbd+~bBqWgR3x`dGDhTfqzeFXp{+)!nmlbP}2+Mm>6bc|}(5PwIgn=oIhqm+XV7v`B0;~>sT49r{M*XF5lCB~;Q8xtlWevZNH#}2cH$ve8KcssPZ&|Bpz$3wwz$i7)iRetuD=@r`Rl5D&+Y~+B<}@f_Bcg2tb}Nw7H&fi>srN@)%t%%1);f&n3e2)_r$h_zlxqQgmsPdxySYjBS4ml%)9ZSrqMdeCU^?CTmFzMXmxNoq2vfT~eQV(M>u^8*qSg1Zm|^PmuF&meeSG)r_h(2C=<{vp6{;k~(}M;1m{6Rg(dT}7N<%U$ODF<zHqoa@WB}RZ+I$nO%2OGdJ71q~D={{ahOekHh_aI|N=b3mK%FW82IGqKekb2`^+P~3Q87cQ3Qx&&l+d4*(2TBLkN>5LxUiY75kG<yhtjI37mqLT)RQ1e3m%~EpYYxFA-}7clWB;eR8=1zYmO#aQh?0+RRSp+Fu5Vr<{@_1T-lIqKQKnIK}M#zt!Yy-#PjNHG;l{>&RS-B$xu_&tZZYonU;z=XE1{wDZQx8N+i2`Vw}6H?@5d70f~YJ2}ehTxR=elQjmdzYR?O{!iT4t1|;fAxUUc-rk9ZrGLkHrR)(ru_esIs?XASpBhV)+oKAbcF#jmg$Q&Cz^0KO$XS|Dw*#p~F=^rmCiLYqZKFm5m?yQK*vUNMX1Usc`PCE81d9v}|ab5?t+JL%4Q=c*xa}=X@J5&Et>%ermVEvVC&1w1+Izr2G0NRZwO(?M0w#Ng9LjkZoZ>!pt7UBkf2Y?-Th=>bBI5E7F;cWy4K7Ri3I;*~AL?YAr=ZFkkOJ1hMBhVA2udqoPj)8w<;8_6huGP}RUy_@;X8Fu@Hez9bUPN81uF0Y2huX3;8<VW$%KY>Yb9UMEl$Xe)_iFTJ$DxPG<Ym8#iZ14dxwG3^hwotl-_Cx4vf{w;8U(Npa&l)4wlr|5uql&Ra)YfqSA)zqM`{G#^I_l3(;b|HL5d;~UwNrb)a~qN>(1I`iAw>;5L4P(WjW6PO|UhxR1a!gQ%jvN-ui5Fa2L6;M@7myIi21Mwb-&#ny6%*%koI2k8^1DRaf2X3e?$<D+jifl#W_2xfbViQPxQEKJ`~bdtpU2KR3}AHAs@k&(h0$w3|6I-)5&uWL=!@e%woF!A57j&n}d`7bJ*e19aB33}hQwpVR%eO1T{cqX9nJuTx4)wi%10Qeq!7X|t$UJ&i);jo6>ltj{7vcD{2dkq#+`-YAF^QL`}D!liVZdQc+A_wuIEshnB-faxT3eo1q{Kee_p{&qSRJ;<pnuAMDF5Joc9;mb}XcW_b7*H=fd*sL}~uiVx(XWr1R(4AHw6aYPnZ2v{`qGL7Bf?z9{jSZhT;8bqvLMbqPkXs{JpEjlPx_5G+0eb)R0JHL(CXz0M+AbQPC?RnC#|`qLre-XAH$BR>T<s3h;BqP^Iemm*c>o|%JucxThNnkZnCq+$0l=XP>>-Bc%AkgvLz#@f8&WjjqiQY^S*0K}hb~9D8HVy^K;5StX;K<K;tu-9kaIcYL;sYZ_luH;)Ve&>ZRAI3BG)-|kiD_&*?<{G)z!F7R18AeSJJJ_!Q+%zumOv%LFROfQANgHjrs|gja@~DgEq1=A&ygi)n~Lgw!31`3`g7^j^d${<BCe&w;P&ddY=r*Ph5dUQUZ-a6jcP49Vi;-*0h*YUPwyZ|0tTGt4u<+R%Fq$vj3QmtIKmFfV8O!?$uhvJA2MBLK%v#B8$|5OPeCe&lv5$IY;dTI<ykAlUc7d%<GPGF#V4vsn9T1iJ*Hh8zq{tNCIVmF_@RTAEL#{xnzY7M&4b6$wZIW_kRRlXLvv>G(<%&G#>A<&Pri*U&iT|C??**DajTFBH>iJCqei+CKP4@Wtd(RMH;lOlwk;U7?X5up`XGgPpZu?>rhVt7_)R}x2P1mZyz=f1<V?XcqrM6z|#Mi#mRfOMJ-;|S)f-WBZyX%98%>+GO?z8>X5LKMxbJ9Rz~<&;nck=<sW5d5qFb_E8a%Igi)e*s!TbyRz#um|DYb#yzgRofbD#W09aXhVjnM)s*FyfQ?F&F<rw<5ibUo%nNh&+&e*4<^Db%BTTQyAE-C~x38#&5=*w%IE-{{E%o9{8kHuTi#g&c<+<iDDx*2ITN56c-1-MJXkJl5jZQqq+;=arTDy%g&tS}_kg4afGEvwx<KV}cXj!`M=dS#u%0HcZxT*q|(D-9ul;R|sa0&jEqyGZkvEr5&K;#%(?Pb~a~3xWRB<*@}dQlCv}JJrJ<rV9i_l;ei(Dn%n*(N6b14{%dyNZ&>P4QZD@&~-T~+Py*FR(Zuu>Gt-kgKT-N|NX~5|J(9XY%rDHx==FpjZ3)0{q&pj$6tK&)o;Fd8OL8AkG};qs|)aa`2lu8CF;-m7rA3__Zxok!&hH_`G;jRzyHB!c?b{s)@kzk!nce3ja&XYxYd?a+xGhQeQm^*oC`<gRmcEW-iZu!lVyk35tJHUNlmNZo>&`RJ6qraPYiG2<zkbx)cCsHXgNy?L$o3PoIz?8JB-St{A9OK%r7z_!M$Ew@p4e48y(e{h^{C%A_(8jX+Nim={q=;@@|4rzEpZLaMBeXO=Ed|CgW6lG;;GYWsLYBVPQq)Py{El)4tR&c5WkA^1wA;6CNz~%m-f*0DYAQ3x^Dxx#ml3da2_DN<t+FZ-ur9Q`ANvyHN|`XiR#>{+?U{5=!pro}h0-c$<LhphWECt^5N1y2?7ypIHBr_O?JhEKMbS+U=dlcgdyHvky%3c2l<;xUOpVo_0M|5{J@UR0gq<Rd)%3&Ii!d_P#!s?mjM!VJ%dU*}fTUf+ls;$0~8v=Me#R%V!2nx#tV;L?xoiM``iw)gq8oOreD|@O;bMx_$1jh6v1;dzqd-&#O2Q?nu{kxDP%y$4)$$oMb01E%7ccTrgrAacQKQU2%OTa`Gycn%NVG#DnkO<~2r?Y;yOUD0-7XSDCg+CLFkHc&J^wiH9NgE-kRvE=>LH#0&GTV6BMg_PJ>^zSD#5(aF6>Ki6>JQ5W;2xckd*Ptu)y`OR<tAeG4Q%NYu-^iHQcg1niVktKq?x}H1T)R~&yM~&5eO$_pHvl;YDS?qZkD@p)}AQ6r!kXz8Jsj@f%GxW+_<t}uZy3%Vv33#xeE2*{KUzrgWrS;o2uBlfwy3Oqsnp9NkP&S?+O5D|VWSYqLYxeCQ!A+3(p8NZ1BX*t+17k?m8c>}id)tDAr=`}+yHpDiBDB6L-tc;yKtFm!vR{0q6cA8-DMs&k)XemMiwe+B;+W#>BwC4*(Nk-&z{Uga54h4#w}FyiB!~tb*rVpc09j8w(l!RtFJNd=Q4%w{t$`~dN)sE-<$j0XIYL`vQwvyndL}I1yfB#TO87!H{$YX}K)*OG+%=_J8Pakp4jE*u<0mVPB;!ipR|1Vq{mImUV$U~s9<7iK)bafby4h@*_7Hq_S3!;X>6sxMBOT&L(n(g`idfmus%8mCl~!vGUb^Rc)qN(VNld@IjSv$FzriVNqRymMaB32zXY}n#9*0YQGnl}L?PN&}z&B<H9Zd+q)IEtN47&@K9@rhyc7DElz@7h&OA_$v%grneqlXDu(o57^DmTub_351_yF(oK<6%HC=y*o6buXVkx9WQqwIw0mvScP-eo6={Nv71SixqD=2Kw3L2YJ!l6q@G3@+HLjyOfqpgngd(-ogUA2tEJ@G(r10eT^LQ$=;Z<8CIq$lS+Z84Fss>Uzclmw-X&-zq8`*ExBXT>%z^AG`dD*4CeiL3;hfrrG#SG36$w}cTN%VZLZdITz}t%JVsr}qvkL)xgVaGq>a;KmP)rY<h=kd080|rh^1O@sn}IFwGV?B2Oxw=VD7dGj2jbE9%D@{l|<?@!`EV|9<sQr4jx?}R(L%_bI{g7VBA^h=qC#y{KamSv{qB;pWNAH<yl3vlkt7@z7jUsGfwtDsmu!L<i5X%soYlORi*atCK)Gn>Bpsl{F%WHy(lVbT>K2CDL5(*31ucKZJ!)LCIO*Eck$>keG}gzv_M~ci`9l)FaOkqCvkQx@*_-*BWW0s1h(0DU=sQ{&4tX!)8W;+eoC3WC>}zI3b+Vpp)0RBrX>EjV%fRU;}qUTiEyIwj@&b-7EzF+hxq`xe^<Gb`p=yVyF<;;C=Y119Mg2ZD;yMBnt>jEl@3eb;RPlv!C^fe`#Wsqh$RK#ZN)S|Cylr)%vFuYt*BCk&U=-`VWDua0xO(T<h^0m8qHRkj>9NE*BzT;?uQ?%u`9b1HOCst`ayL~A}TU^1w}AYwupaS<Q;!o_RBSkF^n?CO@Y?xu7h_?4qb)OBJ{jQLNDm&;D>qeRj`@ohRXmel|d19y9(pb2RtQrFSSN=w{G%$)y*q!{0!TpUkNQt0C^gqqo2d}mIGi!B}xXNtGVRtCE!P7sTegHJhalHKrOCdDo!ndsZ68v2w?2WhS(=Pl4j8bh*pj+A2##4WDy5LdCL{qXAG$`#E*it`VFp#SR=)y!N^kp97Cr&vSZe`I*Ke4t@VK2*(h50PCaszL6xI7lONd<JErBa+~_`f>=7&45Yg4V(>A5~#h{=spF9ba*8E<VE`Gy2gBA9)Fps5K?FET>7+@O6+8HeSdd<2#f-F88)T@c6ZzexyIU(uml<7(J<<g9eiWzU*5fn+#auzbszQ;*ynxJs556FW9pZ&W|Sxo@d%RqmPG+jmaX=;S;k&a1G21-r@IN+YGq>a@5>O@T%6%(o&LI{E@yYR!xv315_eo?Om83M9!SxvytI?l6KV$Xm0U?5u&c}nT!M{UgmKf(m#!8dx<ESuiLo~ksLlGk53FMahZC#_dIE1I(YkV65M<z>mnR<p<Sij-jkeB|cIJ)$D2zB(zLHu!c>-ePD4U93fr0(^UvDzLM@6N!%u3@^%9zh^yRBs*EI*F+1Fn^SY=Vx1a@kSEjh7A?;Ayo3E<<8HUVEn0>rErC}66YnvZ7#AofQTCP#?bS-W?~#n<a=EQ269)b&PegGYuLl~puSfHn87B+%MA!?EOhow~cy2<TYe=wLg!(!r*gyeWuE{Bdy6Yb^O&=_FV-&ZyeLQ#$k_Q)lnX%>F>^WJm9y(I|&bCt1=BI+vH^r8<-!J{CM^knHge#-webR$8#IiNcf9d6dP{ae=r6l%pr&b)BuX75-8@j!v*kg$i4v`BCT)tEpunM6nin_silgk;YxDq^@jU75IvP|0&BNxe`B0Y(5Qd=o~la&_a`Nx#|dUgjyvxZ9lB&h&lZiVG1XHVKwxkQF!*V55Zjv{U#LGHz0D<|59q-PRX92en=HdJiq=4X0-&1%92M@Df@=TFEIjH+-M(~t#Es5^Ap5=Qz#h!zdV(Mp~z0h$nAu%Kq`tN%Ah#)DQt+6{I2g*Nqe-CI*-bS9eTS}a2v0kVH{oaowB>F-wytdGlCI2iBr^KCvZcNS{2#Y}o~GihIg7#CShdaZVey%LEvbBAQo3;n%VLo+FIQCy{-1oO+XBq<9euEd1bo&coFgOtttM~zx0+*-_H*@!?B78hKTEJL}&Jovkk{ZK9$L6v4+u6@{YLUkQY>Od!~kd~>a>>y1KN&+fa0K?`eo1^B+ND9W5LLo1drUY6&a)@J<)Cbo?1z0Hc(bdxizL6SHSW4qF=%1arXx1(!dMdL?YqP?MR#kc16<omJh%-WPtTo*u+0B%#!Gpv%VBXw}CgLC+0;}v6ysczp9ICLzYnz;be2GaUV@7i{k4Pn4AO<sK$%n9<W4(tN5AcH?yw$non#DVkVfb;Yw!S*s9IM=ktmkt{_N%Y|{!MS>Zbh$>YiFBCIRVVZ2t<0|D5jIB&H&DBX(*dTt(mr8WeoJ1RiFY0^tUUD<<#m<h2C2wPb5z_nLXwQ8C_QfO$1A}g9XhEP}n5HP+6U9IZ*eUq-+H_kgDuyp3!wGNeUe;X?>UG<lmJiS*dP%l9vN1Lc-3Ko9@+3L?$Pk!}B*JD7u)gfIC$|zun#9ui*elK^|2g^%9~i@lM-XW#~X}>Sq^rM;CVhE>o{0{TWCK1!CliXizS9LQViy)xfr3U7tLmQVThRnapBTsY>S(LaO6BIKc-)nwn~l?2yp;Pd!WBXMB^Ba@;(e@rqmkl$zYeO_|uu(7#TX%0Rc-DyHJ;NXwC$KM@>^sTg?k!lPK#>v!by`kq#b;VjZ7);=iXWo(h!d(%>ZaVd@a2-8t*6SUeY=!WWSfzj4rRurfO9d?Bg<!Hq%s|X6TFDdD9ufXO;&NPZd=>n>$Ik)hpwFTr8;p&#}1V7;PIOsE^Oj*95RH!Ahza!UKQHMw;PP325nOg}`qxH!2dZ>~P*rB(DBV`q69=Ev%0_-=T@to5005uy1t7uKx2h@yL;q>mF6a(sew?C%C0Y)qCLCkoQaeFowd&$&J?Q`DH1%%=55rx|N8pzf2WKK5Z=fY5EY%7#9CvEDp#=#VD3LJ9L6J9pp<&_G}sbzoRjZWtL5ec<0HIKU<g0kim*E$J;YPI=Hst*5VCjW-)i7B1U&!Kfi&3963vLy63jmet_Vg~NF7v)@S&nL;M*r@b2*wA8^Hsj_HdFMqiT5q|1o5bir4m4Oy0;iYQpwVY<Pp_frK{VWP=P1|HsuW*+sZFFz!4%o!4%ouR!3*ykSY2^PK=em|lSGM-M<e+?<$6RX)Y&|JC9FHwzM6%OydlCrh?eW!dU5ET$qT_Qk)XGi9&7H_Y*;(wsZFfG7#UPw1_3I$LVX-t4S0U-4X2Ttr8dfZdChKBaH+_&4@`f)T_%0IA;5{Bxm;-f2;tMT(8?3~_zWS6$$G6+1zJYuN|Xf=qPzk=C=}At0v8YK*U(^jFV}QV$)-takf)kH_;h7F8On|sFpU@rtx`R?h}yG%(iLcV4<Ki5>k1sC{Ziv}-@M;g7ZtUH4mc<Fuiy^2$n{<2%3F!&^ts_2Jw>-Bj&AU%f&v~>u>5b7tk*L0dkR2|VK85{Ep;K=;8naSh*^UV?sV%%=3RcrNGR+h#krz5il=Uk_7bp<3I={bc0jsbe@u!4JOksD(IuJpV?2P5fb4|%<hGcL6R~1%y$uPj{t(3SA+XT78=CNNm<%|H?Y-Emhd-@wv#ZJXb<Rr>vMSp&Z6-rDlvb8kh%%<wsZl_PwL05mob5)in6O5QF%6M65?LvP$aBhhjhcoOboV%v!NCvFzbVtO053TT<<cY^;vO}mplli7hh98KuQY}G-DrU@ln;ISOr+GU3+YbwF`+;|yFBjKMi|bULLyeQ3D{64CM-Zk6Ts6Zfw(VgG~CD-QN0ZE?KuQ61JHs4dcWoN7gGujI&9}m1A<3HfStfJW+(IK&zg>1*_QzP5Zi{Y$0ZhPh*>OCJoxOk=PmEN8yjsQNab?J{{B{eWS9JB1*25D;AIG))(*IJu#vq(3E7%+V06Hfw&r=&hO2}*)LZJaNJvM~AEnJ+vMkFD)&qL)H5zYX=!jA|xDwOW%Cs@2k!YWRTu!_!e|i8kKp9V9P{I(U;%XEbFrg#_h0XZymCQM@3216WHRSxWrMC2=HP)g_;o%jv-N3{NHDWu1CVJ{vB+Suio+yr)EN;Q9&2^|**4Sp92-X8pDIU}0x7K_uTL&m^SV_qoUjzf^cudEUffEmt#R%m?>=QEu|HRlS8Uk#uMLQ&yZe7Q|^HV~)--^OX?aRRAi}VZJX6SkYHS+-n)DY6CA1}aIaBa%TAwX<|DH~V?2Pd`BGk>OL0Xipq7QbO0G-;#%EPT6Sc^eU3$Tvc4ovhbm5CF2lZD+(CXwzT9Jj?2@HXrp+HFpXweR?=rl+J0teni&nsHDe<1OYujv>d7=U_$9N3?q0|h`*W=D(BtGII*9j6#0-@0R!lQj51o1xApD72M)QMzd%@yJ@Kc|lgq9}4_Uw<hK{dDMrJfSJgGnicV#c>>_h{}&rMqP_ZtdYB?TodM{kaaqDA`3i4L2fRLW|*lm^hTAs}NV&CgD73c!(1<qxjQTGGoxS_UO1P=q)z@ly(l+vHWG#R|y{#3LldTxzA2(392q+!$M;#}VtzPt+Q2%c}cGcSsjmB}q2$s$wj9ryBtArl!~#fFI+r2D-&<63Ok9@(OUF9r&O`zCrC#ux0pNEH4o#_raW)OW0{b9x#edN}`W{8I|}z_(MP;(((*`?*!T7JIczjZ4rW&LpyYFQtUc-lA0ksI3wL&|0murD@vH9MD>RV@7t$BYRoB3$A_^5jt<LcAUO_>9oc_%(%C>W59F=&PW!kQ9KJ^lSZD=k*oqEbq>R+@aD%3vq`^XR7LbH&G8i5@EqG^m7|s^<<|&_}T8M{tB-ryhdJ%1@P-_MI80A_fO&o$g`6l1S0O(VCZh|ATrB+Q<ZjSW#GZTlxnUUFbk;U6p`Zi~pZ8Vj7BHQ5*bz2-v%zItYgW0>#V?5A$i9$nG6$iM25#g~~CE;05jSQ+1t0<OA#xx^S^S}e%r1(L$vevlE${%R=CVZ?~?OB*;RM37D9!v#N3OZ#hq99pZIC4ey5{|)Au=n7D1}czXtV6*fdeAq?0Zk#s2ue~uXDA{F6^tTb9~3~GRM8sy(2^I&XO7LJ{VvQ+AfN!DM@AA!7z9qqoMDlTT%h6##$nPF>jc}&IbS5B!uW@ZlwWtOL9&;_TBy`a5A9;_P$ZO%h&s|*5humZD*HRu0n9SMWqArOxD$ajNfn~9dO0E9F4s7-4<o`ZjvOF_BWpEaN1PghCaRWNU8r}O`lOejl~I%yMvEi{{9wO@Pb4%$ti<k%6Vyue<WxGhSTMs*1@uVLIRe)YlEdPolGn#G{rU32*?j!_3sTX{sVEJcjx=2prc`BpG<RTvtVmDm@-o7u70V(4?#Co{8H!~3{Zq;_BvS3toObZ3Al?124lWpoaQaiUO{oS-$%TsR>=XAZK|v(Yr>sO&v@(qR5X@XM&PPrjiR;AU<H;Iq_=Y+}TuEp>3M=vn?;>#QxJ>ye7StGO!{6?D@)<jW+#Eo%H%M#%92f`^HpulTZ*kko`IEP!<A8_7q7mB%xP3%D?mjLNE!IaHfkX=FytOBBoEB|CB)`Rw&)d-+1h&245lgd;n*|;11u3v90;Pe-HzaeVsxfOUNqCGM7FenX20vH5B4#4MB#dgFToI<f`c-W)$0}IIufP39QUrFWOny$QOhp)&)T}^dSqoi7g;y8dAM4S`5FNl^$iY&Jy;r*|9B}!_dNCrSF9swtl{*GRg8+sAPAm<LU1}Zyph(-3t7!D{Ol4X|@E7w)pT_51Bqcy3lra|Jdd)IJE`ASk;bfkdHr{G&uWIdZ5W4q5{RGjQgdq}$Se0nD_cB|Gy%6Y7^BOxUMkg%sYTp@Psk}RLG6t+euCT9kCqx;qsEV#9V|Z~DNl92Ij&7ulbK8?qQzZcd8}2VDR<p2`XKIzhf9>}Ms*)@cBQ0sU(Eg{_CA2BnyH3$bk`&~)-lqo?K(4}epvgI1H<f-K+aD~-VKymeVG0K5f<r$Sv5$+!r+N9rIt-Jl3J2~ap!*=#uij=DTL@MX4Ya4eY!!|EL5V18mAWQw1M2;D&jx|R!@Whoip%nj6KGgTx&~|AQ{kE#z(u=RLbXmie4=r3e_aqTI4O4)O4o0rx%;x5%%rB-)3ll0er4KiMX^a_mKir<<l$uMs<Li%*qEnc2w3yFP?$S~jXL|Miu315g$*Q`J28vf#5tP`^=b$JN0!p2GoIZ1P_J@p?-4HdbV5Bo=>j$Y20(*|*D{a?spkAj4;OG+MfnfITeQv#NHVIrhQ+e45e{@Gq)}`V64P-eCu+q<e{vllqB;j7PqgcEj0NS6sRiO3CZ4=s;cif%W5TS9eJ4#0In_%v`_&aTMCYjw7t~;#t4(9oOFDzbV7`b(TmH^!Q;D|ws0+DCT{C)&Xch9>YEO3oR-h);Q(YCM<~hL0wAv0){5U(i(0G7)m^!c=qIq{TOH{;tBz<-ZQ)6=26fUQ!FP2IGX>qD;8KVcN#OeIhTvuymDmrplP()WWP|Q4ArB5iuB2;W`;-7;AUJ#xNons?)lQ3CthLfBI|CGE*?1f6+NvOE83J5nq<swndtzIw&rF<}Q^{L#BO~$`Nl|B+NR~$QX);?92C1edgi$LHu^dhGO_$ot#bja`&o(^x-gZZa!`r+r_p&f|OdqT6qYSz9}JU_0g>`J4=xK8Bkj%)*OAK(U>`O2f1$t%(s@4ZrQob0&GpHj7ognp?<f>Kmrih3cM7sfavDM&GZkkboj6B4DrW9ik?%+L${k)sTnmY4s(=%W}&VwjoNtV6=?ipMyMN-S(VuIxo0!5Cms6~`nZ!~*(zJOZhUDmS@!ob<PpAQYH?a_a|5yrHCtmi4ZQ^HI@K%6ev9LQQ;xFwqv<m_%}XBcn)P&7pX0lp-_Ab`L!fTICDtkV4}d?~d2E<;mxD5v(=n&A0pT{6O*1Q`MWWa1P<%Naq97A5!Y@_ne4Lu2nBwF9@2X@G1C9(Vao-n0P1&Bsv@d4Nm4;QM6iuem-P_uuzw2;OX`yh5irQ<EmY!$?=T1O+>59JJy5BJVkeK2(J)XJo^=D)JqgQBL?H;2Z6$eWn|!pLz<Wr{_}Goas*yDQf-cOQ1~59UR#7!!5BUEMPHAUKtjK-8@bHJC<&50nu-yae@T5FUD7<Zyay*jkj-10+)6-!0JaP()t@5kp@ESR5;as}L8EJMc}KulsGTXog(SGV8=2{Z@`8-=F{RO<kH0E~($rqT5hI4hki@+e(TFu$1o4=xB67+@fKk^oNLHs!fzvlhw^3@x>#;LPR?oy6DSp+&6G7W9g5@<?&Qps=PGTEq?ug~?ioq(jk8x&w>&UW=e4OA>Z9O%$1{SZiqF5AnoI~**qjw-olroa1ao_$J`9hPuZ~NSd&u+gQlU{uGneOA0rs0~stHM6LO?RUgYiLLbcN`NxxU5Fb*#L)xeKpD}GTGwO&rSK@lv1&rbXiALg!lIJeH-Qpr}UJAv22^~zWrVk(V;k^U0sZ$l;tpJfKXN^!I!cabd?-MWvnmNm!%Pr?lZ;WOX);Z)T%ld_*EK4wC<{RhJO)7#ow;cw`~>4F81=<0Kb+-`ds)Cd>iM6Lo=SIsz4eQ1tZQJCyjj^kzP&;IjWS7`fMm-&T^iFz7z}qAd>1MT+LpJdAG`&orUex(*+HN^87^Tb&kJlClv)c0brKTPo%nRo*v*N60$H<wt^YXGRQ2$1q_!6)8SNhE*uz=@EbUe0}EYhtcy}N;iSj{Y>LdMCBPkp#t0o?yJL+ACf44-2v6N#&4gaf`Y}zxFM3YL+m5y9OYo-h2>@`SjYTvfF5f}v-a-5Z=@6HkSKn1Ycfoj`+Fj3@I>NIVJTQa4bU_Q|BN_+{Fuew(`EUy=Bm^5~p~r%A518%+_$iIF@bmNNIOS;y8q6U=U<azh>f<5r{-Mk*bZj-~pu8i9^yb(B8t9R?=YXAjN&k^d^-Qwl0Al*AW1f+d3)~M~m&)by3Osfi=yfn*Y6o37;krVPE$E_a+S)WS(bob?_er))wE?)5Tp=$G#7h_qXv1fpdfR2o=n$Yvx<TkdZUc4m#z?(MiaK9X%9M)uQkxY>MoUL)(uX;{pN<7TYaRFn5}v88RnvnY?iSo=N!>t^_-;pc3vjsP?jkCG%V_IO))tJw#xyA<_Fdi=w6J11DMrfBHHia7p;G9v2&y^OLy}5YI@Ece0VEnqT9))w7EfUNQgoUmvnSmsnhgX4G|}-4l|jYnYNNT(!mJ0#p%Dgs3@)>zDyG7WNkTnKg)aSbb)3*i776)anRao7CirZe>t-Lj!)|F9Sv_SYw!<}lstS?$jycYsP^~IOo<+Ytih%aPoeI=)daFML07R6Q!johU)+20w4A|iFQ;I<~<s8ML8REQ`O|`*p0mZrCiGm_o#||VSLqSic)*b=5MjRWSs2e!oJXE_cB2|f?KAc#wg{~>hnnxqz_sWVR{yl7g)7#<vvQ_`8u-!gdmPtv`O=cHC|DdQr2&*2-PGP1Oa^FR*0i(zr<euERq<G*re(Y7tC~yr34CQ5_B#gWfpSXoTRt~yQO|@wSL2O`jH)N4Xp;a{)C9u$c!O~Frs`Wvt1eSo&41ffiEe9Ax23(L!1ft?4V5kra$vdZQ)=e>Pg~kvs6HTI5giJCx>F*<O0-fMmQb`B^0RFzWN1R7b$ev_cHlOWAXRl<QKfpAGr<6p#7%I9fd$uDiY&$$|W{PClv|mDQX6$Rzmju@WT5*}g>2sa0$m=l@^l6-=slI(mrU%q6BNixcc>_5*Q{?eV*?0NTD;*RpyCvkWM?Ei3d4ea?R!HadkWs89CKVsC7*ri127w8UvJV(qn!$@;7=Pq21<HX|@$Dndc7wJjg`OGa&PplHbIGTs*uX;mlzJ}KNzO7-xgn=8R^XXHn#B?>ADvY9<!it)syh{E4ft{j1ZGJsvGUXY1PAzSQKBcdDuwzVXd8uzkvv+urI^1y8+zK7KftFwxAu=akUI=AWN=vCVfp@l_~SqS`F}58&)&xN1RLANSdrk(3v!29`<wH}Uwre`Z@zdz5`TR>{+52Rd5E3M{D1#4egxOuMq9qx9n-tt`HLUE`ufX1EdT!dACw|!;$_}6Z(fJ#UJmDlfAl(i)n5SYeGISh{Wsj7P0fAujf#kU#(>P8G#DW$OlFa_>s5eVqM)b`2=Gmk$gVNy3+51o&WRx)lV_)_;-}0ekBmy9agA7Pm4*bWfVsl)i3df+4MY{zztMs)NLNmtD-=$3Sp=;|gwVZMJ0l8(R7H6#-W4XULYAjpE^XmL-Z&kH5!X-VU<%*On;A6@WWv9$TN{1p$-p^Ycr>O*^4X13?a@fkBKUd~1GiKe)?OBl3SGn4x!mgHS#G}O_32X=4EPf8^sNt8V1U^#v6-<Bb|?v}vB|T?+!P&iQzUgPXH}zsG?3u4H8BihIn4;-Y6x$|C3P6({+f4{zvwRrL>z>5qCfE?F8Z>{Lg_*iZ|~Ew!REOZ14P%iTa&D8Im(~SJhpZ{RY<9&xu^_cr9Ze!5Oh9(uD18}xpen&X$)(jf?Nd4^bOFYGJ`F!tKLCHinn}b(3E?=z&Wi%RQV_^p1oQGl8Py`kOrP_nOnCP!d#BPW*0u6o<7g3I1%nh*K`b|erS%}QB=5cX^D4n;esK2x#p2-)~E4RD3VvPOVMg{GkVbd+q}kz>0Q-|gZexqpxk@NwHglG0hP6DmpzPo0I$>=hFsNNe|+>V3Z<df9edXf-#s0y84Y&2VW-bD9C*~ld@0%g^4pViCtrT^+doJpGW>Gp#sHtoJxyxV#Y8Z3HER0Yo$&C7T-2qpx-YIl)?zk;ekrCsFJnb%2hm<CPJ+4vmfZK9Xg1~QvL1Ar>s~DZCE&pV25Kwkp)w;ZO6#|4Dju6Oy3Oqsnp9NkP&PP0=R%1Y;<LNintl66a1$iHN0;sq9enF8dQOf#wLsx3F(<9p8$<+sRlLacaDaaFh@8IoN~wIm`cjN*^r)HX{}vTIKTt$DwrK_l9W_l#K)ITLz4qN7=mlR;!xQCR&-a5zGA>3A_IeOfVbA58s3TiuP(|2<bSjh>6jV{be}JO40D1a^dt`oL<jfCXZ-jd55x-5%*C1`ipaD1V6V@0aa6#ree6rFwGEOj+2+fj@07t}```)iFC{H}_&6@zj9@>@e4y#c)9Sh#78s#H{+qUKjErvR^N#dztQ+ue!#L7<<%~e$vqtQAoZ*B>vu!#yIiD9R7>ENn3qiL^gYum6lk*583O>kXYz=u$hfe=RBlV~f#=&`%?;OG-sqP(sIZu9S(S$fv~!WfSwvCz7dz>mF`v{-wOcH5~LJRe2~gC1);U31ZNh{Uc^JazU9FL%}Y{WLg`WZ}g7#!Xe<UIuUzJr%GykBB-;KKA9OWN<_GRM^^`LNJNzec}5_?-2P#B^~D5x(EG5IY1%tag|+R&!t|BQSafUZB;E{Q#>2|>O!~M?LM79CO#kWtvEi_+OV_s3-;$LG(gGNfSJfOvbTWrG$?j7HNRdhHgs~*bLRE&D(4J{ZJ2%f-Hr^qc^H)~u!Fs4Z5<`soSKOc)$aY6MdZA8IJ44<dXHQ2Z$S?f&aJYhbb)*RkBUo-$`o;=y|t7@&C2ykGCBApUE;<%E>D3$<CTGQ@)t2%(MF3~v+}B+kM{ei>85+_4V_O(7y>!Z+GwoCwbk2uF#!z0nY)o1u+}+6d8?XWT@>5Eo`HlM28(yYiecD`>aTgw*BDNS8@)_L)-PHX`G(uukbBH<LVAcbTU>l6f>Zz;k6fVQ;CqvBo7Ngzhyy*ie3^xE99)UG9lDIgp9?{FvRi5V3@(jSHN)Ggi2y6%ZqUSgRgG){+2AU9A5=ta)KGe9yZi!&3+CZnS?&4^RwTG<tDaiWvS>JK6y$CJi)Mn1i#l{SSevjYpB@NdL|U+uPUKy8w2m6LhFa}t?4Q&x1{aEg_f{H_0c{9GW0bFyqKcf`H_#e;&vkqNKSSK*^%Tz=$5g(2)6XJ9`pV*@P~XC=oi;%;;z9ye1F7evf#;)Zb_y0GQEo}REMS~KS5d7iulVBpSL)oU(w@`IoV$YaTh)ao*Q+&q*bV$a_@SH<Y%-=a%+Cop-BX^s`a3~F5@ZJO!%}^Z7^?gAgD7999IiUoB{E%f3oji5NE<^@Z^ecLiY|`p7!`r{4epVQMHOAaUw-u~7-07G1Vwf?xspwWUQMNW1e9rr?Q-MIYCDnaQDh0xAgeq!_)SuL8M+?V1fMwVPA2ci9z2P`uoDoq3`m}g8BroaE&+)TVIO5ea^;tTLy<<Rm5v5VT7{=!L5WtwY~<5WCo#pc@VYI!!;Kf3Toj_pEB{Mz_lQ!ZYx>X~+YkcA^1}_|Q^MNQe;%X9*z{1DP7vOG9cDv=b9?Jg>jnRFg8jmBBQ2Mz%YEt{w_PkRL(_^W-*VvRKg3{$62!$GnZ49nF=6MADn*u2r4*-3)eqEAy~PQvAOu59Q&4(4Dh8B#kRN&Vse}vVohZ4v3Nn*8C$dO`QDrHamir39xbx?ZfLx`Sr-m;_(E{p3)Hz%rc$7}6w{vEz1Ry33149J-ra9B@BsF2%=hdjLaw`xkCK_geOqr?l`LG5vfF*crUEwi#gM3S^HrT#0@C3#W4fFe=JM!JlGSqNOAgs;iXD9C9Y9Ezu1y*Od?$=nAo<7<N!Dvc$+;rmLG?eAA?X4iPec4?2J0}$&L`kE~g{<^exTwjPvxg7Y4r_0umyr?sV$1;qL(*4n2q0{f1A_#+70{Xo=aAH9d3~38@pREH+lECz@_?OQ=pO<Q3iWI{H+8(F^OrU2MiG(f9M!V95kc6RaPLE89296H_NLpKX{V=dYR=^~?#_fzg@VtOy0hH3LhN92kkalANzp=R^$X9pm>@ab)pKmEL6M@cFlY<^<j01MhC?1V+PLgmbO#c&<?<coj4uI68Ux|%d%F)DWU)7Ga4DTfb<+$|F>Hz+l;i@423{pRcy2<qn>hfr=$ew_KQby!K`bDurFxQy{NyUF5-8JF?5>x=Fj}ESNI~Vj!Q4=Q&wVQyG>aOI=q}{VP~iZ`DmdU?1}8_RT}97g>1<~t{FObF?ZGpV$J;E%d&jz<Uj1WbC+*sI63-mdQy>ZvnBB8`Dobhy)R_0dMd&QK=&mzR`(<v+dn!s~d}0cgKr86ChkOe%qJ3w7ED<`6(I(;wpWqq5M{rqjlvKZkHsy5J^dMY4GI~kgh|IEGFg(bYTG?R9pfJ(Vz+RJ|F8tU4gP>#JLcxtkc_f;+-Z-vzfm4^ssI#b;nO0?Ht@$8QwP~q`c-vfMoq_5pHfGrtj5iAfu@Z8o+JmRqc&H=FJQ<h~z;|-IR%>KvlB8I)-aNzmH5gyRo>gmEB7q^*@nJ<Chb*>G6wgv(4o?*iOk32Y%qXQhrXWt|y#iA(4!O#Lc2ssYO2W<{)ARe66kXb2*z>sD{BgLP+RCBRw*uf(#)ITubswA)Ji6_QX4fivjihR>|I`YQ1(e$g?KGU;lojUH+Nq#ystpF1UV)gN#;mNtuZ6AC1m#p%z$)UZesLW1kLyg8KD<RKGeSY+Qosz`hm?(nGsG7AwD({P?I)J=!p65aEmZQ?y|%N0^+(&?B7$M$6?T_`?&}!OP4`U{UIZN!D7%oYuNnx2Jo(qM=u$hEJ#0A115dk`A1G^e+fFUeZex&1fvKmfRAAfKp^$j5D9vMU-Gh)TY#chEw`jKS=~4~B6PsCT%pzLD-r}5}5|s{?mT|E#H7lZvQ)p1(mleopWl0A`&{+##8OMV;z?_b*`iLe$(MIgz{xUB0caD34r2PHzin87XDVO8DFveo*cA{(+Oy()&Nc@|xzW#ei8yb=#%6Rni^CTtwSwU<$>$8(#=fFN8X{a-+rJrB)kH|HGm_{FF5oHO)!q|e0Mpv#50Vh1{zfxOipw*NIG!I1xzDSG=z%}(yDNE9;@ZjUFrG3#bC~5O!@Zw!>3JfnKvVI2;BZgHHjp3qV9}KtZ)ZECLq*SVqSex{g>89s0<xeVBX;ba7cMEvaorOZ#S#&9h{W%4SiT3;LPx(n%PvQvMOL^Q;U&&KDAEamfJ%rPysWYR4;?7d7nmm1pjloF7?0F&}u3NVf)v%JD)fRsB3iHswRxprYZir7B7)#f$^7tWq5{ZWqnNq*?rzXluf)J1-f<bkWkE)s{*Hu6a0bknZ?vn;k#jUv=o>~T*Ji9CmBq?jUkDH#05E4Y@SC+S;D{v}RHqbs9u7(!mAVhMuABP-t(oUUY2Y{&iC{WY4zzzDFQ8N}$hvFKCyY)FMEHmkr&!8OrVBQvTMUI=GHP;A}xGU?aA+$i#?@^M@a8mqsWLqu<J1<oiu4nGjT63RUP9!MEK#~OxG3aFwz3{1RV-7MX<o#-39_>w<j8P1SmXgKlH!0c$#ul_+O(bsQs^5AR%-e7R{|UU*Z>!IQ;ggRth!g<L**zDF1iYrRO;m^Pt2&uwBi#+6wt~Eo*ZE2Q!LF!lIzHGz3n-^HW+`gULh^zjTcj+=A`YU73^=VI-7Ub)*@^H%k(?8k0wXg4c){OD*DAl)%g`Q<k5I#+CN`RJDT<{+9uj`~bw+1jLLwOeA{J!m6|&A;cRH%WIwNQmF(4=6Wv)YMG=k7MfjOFuu5ZPWA9Os3e5QmRox-qUEIB&S;Bgz+V2Eonr}T^YfTN@yynx7xi%2utfk-&5mp@o-W1CuAl_6iH#==W>a)5m!xOfLa6yz+sGCX}goi~ocNk<{&pcBV|j5L(05sC8V%f+Ey7xg5p0dFMJ#2U(rr8`;y><YT0vH&w`QzFIGlCm!E<6*FJl+-CQ*xG8sWrnd=Yme=r$i{@uQ0UE7=!naI=8g<0z{FX+ETf%MNOsS1f;#6Q3ord(OVtOx;7fRi7qv|wjY%roNAuaPr2B`KcBE_ls(V0#<Sq1VZs$%~P%9T*UjezN`^#x;AP-$BiWt~q$Pl6;*pMY~-lBAO93#x#6yeduWz!ss2q?1Ttt7fiTF3vy1p0-oB*>$&&c^Wi31Q-6+}&|r@hkF)`#QDj7Qix01nGSd-5vyKJUT_Tvxe8S!IG~dwjU(pW=g#S>2k2Fs4EHAc>+*(7}310DF0LzN)_NbNt&s#QNVbthtL+@ea55VenMiqZPL~>^oSA@AZFnvX`r9+IhG2#7gU@>jn08`c6y|h!Ww_m&Kr;V(%vgz)$>yiyxQ%dnboZi5Gbp&WILN8BwC1+NEISZ#_mep<UJ?4Hr-d|4Qr^V0!b(qVWR*l3JpRhdOJIoR8E=zc{l>Vipu5obJom(DAE)ob(09@5tHYYF|uNxoR@!r4+hq1l@BH$kPnvA$x>j_@YaT&IUeiHzbDgdF-tRm!6Pk0@wcvX-UU(^<G-il^nCroeVYPROb*)N4{Fj*iSCWiOUeU3nQSI?@yqunH`2(C0uFWia)m@2W7qqH*9?mXd4)g~+m#W{wK=Y~A|$=<uE;3_j{f8cbS~r9>?nHQWdq?sfEtS^uBKxm+FMbNww9bs3I<eMo75GG=<m2`zb?^Jc`26YKA|nFN!(`};b2K^GpcMJj)9Yl#gH6f!T`XFn_UEku@?Tx)vNm4qG*X76I2@I))}SRj)gqA^(zgWU9l%>vMZD{^}Q=ow-UNqJU1^`a70hZM3i{Z(9OeAfVdA|j99u`Fx}*_tSBUObv%j%P0IQLmZ#>8gwE5nAlM<}SdX9w`@B>PnGs-w@$WRGKHBkKOmu%FJ?KAqWg{YNl@)8wY8=@Ens*qslC~I(lyokWe9Au5jZ9{F9Q&d!CFLZEJfC|H$s(><k4CjdqRpHVqG!Vv5~BClrU_$9ju_>^fs)>mtD+^Vs|1?a4_)$jY_QgD9%PA=*C9tH(KZ3~WzyKB7$*|9!thve_E7ek(ayXH%{jY`F}utLdSK)uS_8!amF!p`lBHNF)XRu!W8po8Kh^6E+sZk>^InO088Cg~g7cJ&rQj*RB0&~I>7(wlJd(}3!d7N#d71!P0*8uDq_EdV!*#46i%Qk-4R*!K168|8=r*ypVp=pTJH9@EwtCNq^pdoig2I-|qk|U|h4@o1>D(6}+we$Uv;qg7T_d4{9WMffVhkJC+2hfiP%pv>Sh<yBMr7~U8jS|Dd88}oTlcnyWvsbFQKi955~NDhrZ~D^s2kWRw94nw^IYFSci$E6>!^IA^^xQnCqJhq$rixNhn{`)cM$~|aaiDBj?oywd9MLsltqz4^HlXC9!T7BU^Ybv44sCs(?k@r?js^b(;Si~T$efBl9}pEO(KYrI0l6Wf}R0M>N+-P5;V42n$2*o9_u%29ggCBl(D>%?B*jf+9D+xf%TzlP@_kof2j%9(-MS8LFXqdT<=VGMO-+E=A)QWE~mwo+=F|70Jy@1p{_b7f;2|iz-Tn<P@bxT&z#o#Nq1QStt64e*1jSlU$UM+yaU_TM&$@062>gjPRC@PKg>!uqJ24;a*NjzZALur1u#b*^C?bM_(4UwY3*?Z<$p3pgj~iYL3jd$rtn5qeOQv{HOjM0@Q-)SoFhufByRC$bXaqm0G8b<bD2989@pgb^QeCbQAYBfQ<>*T6vt!N8HJLc<G0m&Zzv5S5D{b^jP8l1#$=NqHc0n(G;@J~BK>al8k%}+Bya?1tSqLA=63^<;C=(vT!Qpxp^<9{#x@U1=8vL;Sk#DcJ`h%^eok+$lU=<(brP8``xVm5s=8xS*S{G<SPr#t)lfOjsF>NA$=YJ0Rv)NZ_<4OJl<l7o9IJ_4g1E!Rx{;QX_iE%%O0j4tC+PreOW5Rj-F5ed&iJLp^K?T~E=97!A0{0U(~0;&M`y~hp-5~4EB=Z<R$HP`*I`@ZnY6p&<{oVc#$C07QA8TV)*Qo1>UQy2EGoEw*Q~ML0)8hRD#qv`!to09*Ft3DTRX%m$<zsFUyaxXZ4N*wD-u;Cm7)aAb(7ftHp>8>TfVBh_j38>ZujAJid#TcQ=Lfhzdi}_SJkKh9l{yBGI;S*O$kk>yJ=mRv^)i$@fK=Tmj0Mxw1rWI+%+GluQ&ExCxR|%1ehWxlVc&`OYHs+T5SnBwgDOgbqbv3sxC$Yu|tN4`Z>v)N}MA-9I^dC=pc}|b;bmPj^g-;TN(ETk{hkUDot%CgsMb0kDuu?JRu6?V!(N-z{_AtE+0WE9JBa{0&}s(VRO@z1Lgb^2Ir<60WOWAJp|AjLvE`A*G*M|V-t+WE{t6FbWNlTht>d~<Gix?eHy|+i3%s=3rxuX{1d71D!iGTuC5H85Q#DSzaryAIhLso7$QK)wjz}zK_$&*@lmDO!<iDmL9Qulc&gjV<0(gI+fnN<3()PP=m<jugQYKb!ucSLQsyhKe80HwEDDbngp1*DmlqW5sCLlJnH2V4DYP+Jp<G8iI5mc$WIPQCu8LqaVPeAJsr`bp*#{r_NVLr@uvO&v06H)U(lUv9R9NJqV#Ty6IZv4zF=fs!H7Znb1`ljr2>1`tPAS@0PzD{um3ebArJQO`!iG<#G#wFAUA5{CPiUtcOauBDd@r$rb_su<s170*3s_j6l3MH1fFU!tc%547WQta+O(6GWEq;cKvZzP2?X0-?n9oHHo)v$mjXWns0~&yPUiu?45w?(a7b2%zgx@(M07(s2^>1uvd^I>x@Xeus%8WBRkFfl}`*M982TbYZorA)gO5S_=3$_4Y)m|3`kq3cq5=Fj0YnCb1ka%P5@R5rCkti0pbF(e{DT7TL<I%N3(GDCu=(-Jk)t7?KQhE53688~!12#9f*kb7+N-|f{9J$z0*u_G0$$=bscC=O;4@mO^<!D2TtpI_r7sW@@dpg($FpE<~AsL=f3Y8m(nlKM*u}`Ust|j_voYy9%>B27Jw}eXr0|oFm+KaZIJPR2&RmJa)JQ&nW6$AzEaw=wt+Gb*csEBC;1y=1T2^+pcH_fA9!Vr43YC!Rgn$IZA>aF}wvtBAwY}V{`1YvAZ>qrs)8r8BeJgq&{%+~~?7$Qv}`4yYeDxoi`TMX)!Dq|G*(`x#ALzp=L*n-dy#qkChIDY-@H&S0HDmDcAWK1lP27-h}tAhNX$ztx6*@0xA1yOwA=XN;n$lE4DMH+&r*abQ1TC~2d7xG;1GVGg~;iK=Oe5SZ<2At&ku2pT!#KtR7$YvNNsMs)>!_z$x8La+0i-oSzl|zFO#OTQISas2u$r?;-MpR#kU-GhsiB)mg!QiN{W24#yO6%dT5`2nrX&w5s#h#%`3k({fa>%Xl(gmHBHc`D8h~w$3!0^foi&(y(4Hc7C1t}5O98Xa1Ib;R+JX4e6Ige%usw_20=ccMF6u=Rx7EhvSvKcR@f_M-f5B$|A?=&7?#sEYFUX`=2UYI$IwXl3Gc%?s(L~JZBUO}Hyx@UY`jh!~(I_3;M+5nbQ;+J&r+M5)arX7>xkIFmfvv?irY&&qt=)61@zB8uE%L;0z+<^-{xUBIuWNs8nuO00NVzfJlT;^_qAOnuI1BFzn)kF=xlWr$0C5d1h@(d7y?u71F!8Ol(KtvQvIWBo1r|<Zp1782CzOUekKoUd=JI39ntUftXuW`?)uS}gHE-_l|wU<(xQU=j%3Om>W;HAlkbMW3bmZUfE9424C{-cUq>^7cvU;#me?dY6Z(+G<li*J*`h*w%A^sfqaYPaev0ym*_TcvYjOFvPd(jjtX9Y3;<_H@j^Wg61a!-X|ezGD^6vO{PxEY+mC0<|#nH}<kl^wS<bK>sdoj3TkC=G5xGO^yAOXv%A8@GNT7QDitGJJJpshrED#_w~ijEgAA^GfiH}<2I*8XB$rAt{Eb&=`Dz&1~_<|T3QfN+D^xmr*9jQQW2Q*&&S9?g)(<)B68pgrA7o)!l$6QIA-=IK?0p!>S&Wm9Q>Fg2bTF%SCWeyXt_KjTlPYZuHL0~l|;}2Q+j8}XBUw;&?~J=8i3@Iz)z8^8eabE&f0MdJ{GfPjb!BY<@Wj<QB&6aW#$;g1Z_yAU$>)ZoYYYR5de$&#;ded4UVyU08XVaz8WcS{>~eACFwXx-p;<EFX1QZ`MOW7_6kPPHelEoXo8uO-g7!d`Lydv+$S{QVoz;uuWIix5g=2#9i0927pw-y8!*R8*QO`!_DaJ(1OozQa936J>!b2^%F-=Zhl<UE$0}YG$iUGKgg`>a+r)Y7t<@xzWb^lxCJBrSkCB~!F|BiXzoQ&iu~Uuev4)Wx16}rQ9_FxWo-RtBG%&B7beIsC)8`^+K;@~f;aoI0vBr3Iz_?(89~xCqN(S6tyP{t!L&9ST{p<Cq^rEsowJRgx79&K;=Mk96m_D?%xNh4jNzv&<SP=?ma~IK;3fxS#dozUxvHvU2X7aAA`Kd(o%*lZ#{*>1@0;)fA2Rbu|J?u(~HjhA~Yd3iXxSoKz<^|sXUnkl~oy}fl!*ccI@>kH1b9a?V?=&P(gabv|JO=D0+YAd3@}cepn`hu_exr(BMDF!zt^yDnUdYNyTnG|&63rQ@GpLrfLH_`34+5R9=CHIVO$|Q}nUM@^CGii7lJ4-qM$sU!wwdWE)yz9dX13vDZy6I1sUogK)n#}-f@RJ*bQb)hI3}-fig2OQZrYtR`D1{IHbZ=1BWLVCBM7zxWVInpVp~<QD%Kv6>;LrrP!13^Dvv7tP1-v}S*5laYB$1Aa{qMSUqQA#FB=|3$dofi83$AZ?==t{sN85aToR~3g)X-UG1aol^42F9JAWEUfv)5B61EWx@0iysejA%C_E5>|yfqT3p`?gCsAZ_fxVAd&%ba_Z;LvH2Y+@pKN0@Xdr<#BzX9<ZgEcON~fI>#D2%Z<LWmTh_DR3h1D;RYukbU8>DNaSLT}qTFN!7m-PB+J4tpi~-ED96>s0$hmEzd4+zVP5_-mZ$b!6X3Dkirx;d1|CsioxjOixZ8O+?O@fH{P5}?Vt#|3H*?<_dTk`>kHcMql5Q)cUfE%z3UWhro<GOVX6_~l=J$wNe0TGh`JWD)6SE%Eihvn8})8pi^8Z{#9F6~SywG|R0XebM~OGMzDrcv=G5FI`>TZ9#+#V9W@i}_#m<ii+}yP(cJcafW9=m;s-G=K@5h1FQm=P~|1Rs}yKlcgx7Y&(wM|2-xg#~*S%ZyfgGsV%?w5y4eJ;XSHk+pSU4V<^dQua8wRNoPe8;^luh<M0zM{&4$<8FaQMWnuH@)5s#^Q>heJ9#<^+Q1WPBC536ymmJN=4|(NQg35Z^!>qg+SOm*T@S&&OwPm)bhg@0qRL`q(uTyy-v7o`gq&b%*i}D>{Ryj5Tja-?%2w<Oj}h#BP(ugKS?x5r!8)|m>t`EV2EPr|4bWJ)0Sia<kj0~Sc|@xwM5g?;pFV1YzMHJmWujfFoT*>Y8M$kZBioX)Dt6(U42hlgAKLPm+f>NA=zHW&PpW&j;TE@XiLFUO(765>hIzD#O#Wm<6$8nL&LAy_MQ|F++Im6+X4NY!r8QUImG)1i4Eqc)R7%e)oS2f`pWL+l^vu<s}thunKikx=7l>;((p{%J6ZgWBQ~@c8kT=_7+A81;vLSsBxz;obSs)Z6(#1AMDKN`N2iu#>2kri^QPuOdkVc`<)(G*zLO^O^=t<h`=;dE;*OCjt7!3O@OR7sTyo{b3tv!Ch{q&#xXuY}Mr$@A@=7fumlkk9+m61F2I;j2{*l1e&6PENZnnvq9V{1jh}+RM`c;`{+R<&9c||DV9X$Z;pxi54EApC@^j?jY%Q!qRnYL^p(A6@fX1Z*v4Ze8*d<Xjl%DMt4phpe%(#gC*Gi%AD;X;Kvn4I1Qw`MLBm~W`lIH}GxUAJlmCtHvhNG#802lk3vGi#(IV)7iD>tB)!l5$&QO0^=!MXA*J;H|heV`h==c~o?ZlT+utP>b6#Wj;!_oGc$ponL{Evg*}U;CzPC`4a+jRs|P&*(q6+s*$`E{W)$gH>hsMCg!2GG7>}g)K6Hl>|e}mc-gTK8J?!w-u6=7yg|n!A!lRMMkrLsR>-VZ6{zg7ZkqdDlyX3hc<J_|LrP1>cKncZMQmRs%>R=6vrvB`*2pxovQUbh?p#8W15hZ~ig*Dv-(xM@Np~j)Wn#>JI5gTDGnW-GorGa7b(;Gp)Fec3qH{47E48x%*sVxAIDDz8<S8s_toqIG7Npc>;)Q4#a7<{2VS-c*0`~1+xw|68l%ecYE)&en22DgS_HDBNo$^iHi!&D^y)EDeI3wo-Xmq{F_EvGF$(_R{ZXgylzV=|rRvLRb-&KQ+A47djm?H<M8<jp1-eGupgkQ2wP!KQ@y1X9Zo~#UNNR5;E;yJGBQT1wwoF@>HLRVud%8|DM>R40_*%d7;(ORVwgOnpM^iK%}x+pD2EtNxgJbsRLG*o8J9sy5_N?UPjoxD13VxyJlmjQvRK_7CAVLL{fj9Bc)CIflKe*}jElVdpL*Kx&m$q97fxY|QaJS=it#2a|W>yO>gw9flvkUr5Xdr=Uf3SzS3K;v(kW@1WUNNJoOMYCp=md4h_qx7a|wTE*Hk139EO5V+`L>yG@GxS1+M62)|bsahu8=gn01$v*O2?9+{i6zLqrW&So=7kCWqe;T*$11CEU-5v3z@5f4WS}dUm%AUT4D%R_vrkOToh7`Y{UcBa!_!zH$0@puaV>eQ^DtOll(E4jQiZp4O0>m59+~Q|BuGoggm6eC_|b`#Ph-xNG7Nz{UYY@HYr1os`=~CatgAT%D9p7oLcZcK%;~n1fMr4<2t^J~Abx+$;^ZB_qUI?htLwGB2r(6vXLKWYcefnkrw$n&X-FuhDGiCU?I4`b?~39_*-^pWB;ty<F|WUP_QHDNtfh!H=Kn!GlDWcayH|FK;#OHtqA(>>5sc25Q{Tmt*aoxSny65KsFWgnbw;8jjaa$9p{bfTO<h{jX&Ox%sL+?!s7+#!%7_`%WM1RHNVH2lF=d29tE%faYPbM5N%*j>IjSWToVJPRgLO)VsDE-TcwN>08kxjy!Q=(R`W#tHC;*INPsuUe@ksYFaIPSxDd24`e;4VBvZ=gi;;r?@;KXWgINIq?T^?J|jP&V&wgox-VY)!jUf58;RMDYU^r^ki19VLq(zg*nL)zsJ;Sn=}ryOT6u227G`L6%?*MI-_|NN(a{?qbp>@5V=!yGC~zR}orxOI7R{`iY;zWU7<FK_kh<MFrjixa+~?_U<U6Zykk!{nu}Ry`Yk@xxbNfBA>y-+%vuPj4u_%v)2$>oDD}-!~rg>-1HB0dUnYZIti7;r?)MCVFJZc&J6a%NUT^lLjNU3G!$0M3hY`4XVtuR2~pJcbbK2+$1DA%q50^OrD)GKs#^Qf>k+_im6r8)?<xei3dfQo9lHaeIvv43JVum7Iawztw%&W62&tjJbRQQ!q!ORU18!WprO|1(iSe{jU&4fu_fis2I0Fod+Ag$_6Fy0-lHx`KTA&r&hf&dX_U0jWSnY`MuHZmWl_2`e5uLYW#P0vHH@9x0G2$<&DXp>ed>Y%UlJgol?Mxl44lj6OKi5T!!JsHDkxWlCJ$58!yso>qX2`D;IlO`3}ZQsH+MCJw|It*@o=MD^%wBhRo03A#E-b>%Z-Ai3r)PePr893xs-agplNnw>Xrl7Rqfu>t|y_pLAcr<G>8?C_bx%u`2f1w-q+{S-N&Udtc40PkvY?sK$FT0w!p4>2Nfya@|i(X?)g)`YpN1a<)gHC_G%GGDyGmv8cd;h`sh2XAp)EI67<vOc@-zZ9qF2G^jq(pV<#R=PO=l1mUtHzE*P<gxinJE{fa*CI(ZdKee?-L;=%WC^BN;cH@SOG6vatExl9u!6As(~m9=Y^3$!=~@JhX5$W=`#4z)X09}w}5y`v0tPX{$x$%Ag#=`#%n9(6HaO7_3}_9WfOm*4#M4^oK?znr1QOYd~LBgmV%8CfFOt3|uhP0d6<eyp*&FRnpeayEm0DW*LyV@09>(O$wa1!@n(o~WwYz+A5~SGfzFrmplFPy!w-=)r2`JXB_cMQQzZjca{Xjc#*$g(el1I+P7gh^lt=9TS?z=YIq@LE?Mv@2gGJXB!B;4fSqYC&!*zpm1H}ty*so5%g8@BG<zK`q3kD`r<34^8M;dF|N_0W~TpJRPcOGKdj77qLV5aB(>HA?6vRyKri?Ln1bf+by+_=5;F!eHDC}@VGnb6t)V3%>=HYz<$j0XBSSlSQ%hBPdL|^^yfBzVOxz-qD&yPmhiQob>S0=BY)UtVq?KYEF34PmPgWX7#tEhpp;__~;D|VL-~082UYrNMc@tpRLlN5DVKpkJ=Y4RDB#j?Q4_S39N@ZiHn#~%OZLM`}=tkpJADNWCG5zv3f=i@P2dA)!3X|6GsVSbG(X=aZAFdwG(taZqlqD$uo0uUqFd>9d_axeiFghsDK*vSf7;B00TzY}mOm1dr7(I-~l31eFTUjCC?N_h8N4vB3;m?N=!l1X?PS^a@s5085dMS${FoiqnWg>+Wfhw0bLN5cjiJr<1SxD4b^06;JC4(Efr^sxDXC6`E>hk@hcZmEV|AZBqh+gX+^cUp-g~Z2Ib_Fn^>cklJ9$wm3)e<(vv%#+}bi3W|)A?iK^AX>QV^JEFYjy&^GV}8l8lc_su@!TB;}7sLL6Km>993&eL?<UbXI>w#a?XI*hS~Yv?Z~j3hf&#lTS3U$veAFC4alA|Oq3CEqaV45oYxL#R$5W-aV!2U(9$8ATV+i}&Hzx+J~ypwiBUx@j<mOyvNTKFLacLAMD7xxGrjkC3Je;r45X94h}nuZt_+$RdHsB}-w*00i0^35@V=)c41t_yt(}Rq@=!j6H8DWW++7)Cz)I&7<*lBGp%k;Q6M6;`au_V$4J(FWFRH)hL0@AyA#U_C6<NP%S>zjTZ$s`e!wKmjz;1Ezod{BKs~V7cE5Y|h<_M^bEyUj!T)xaqCl0Pe+zwsF;?IR3JlU-@eg>CDs+!?#)kJ_5I<h2Ec1;JOp(ar$?;}eu-^(fU(!}{03x%RcL8r{<K3iI56!~Y>Ry{RcV9_w-;#9VPMKh`WXrZ$dRF3ZRDHP??10jq^fl*ZZUbn$aL63tfSThDmE>g6=Sh7&B@NQ0iU6q3Rl&_Scik#aw&>DNsb$kFnL)_){6wl<{RK9>sVS<H3b>%AcEzH_!6EySus_<$M?S>@a+4!C_BX*+Pl6YCbIDrn`T3252#rdz)xl^S*r`eEo1?RV}S$tEk*6d+7@CV_Ca!Rnt_)9V4_RFc}W(lZD68}z+kOY|l{IFEtvl|Wsg&=UD`9kGz)wwRAf3jD2=@>xT7%FS$osJ&S^g<t4cL~=bNIiPL{F5)g`V|Z?bL%j2;#I9D`f%2%G>?EX4XTZBt`muPM>FGHy}e61AaH*I$S*RO0;k={<oz(!$P9*^fT(4F)joU|l^VGOBtC?FlnKd|UkVOI8mU$~8YpQMo`wY_S`D+2PeYx=6wAWP+*gkqFEqI*M3q<m*CdoIqEzXcK6J-6gn+U9aKjiw!8Ex56vL_cp)#Eyy!$%Lh6d;M)}K~(*d|3_mK$lgR9)^<@3`%2V=Jp}#VrSZ{-fC1YAJz`N_tCn!p<L6iY%i_(U<ah6k2PNIDr*}V2Ei7N^ghyr&^G&JD*BD2XYs#Avae+W)kPnqJn37S4yVkzCtkWihrQOk1BOP6MQ*}7EmXm&fx;VqjXZeoimD`rH#YD5WRb*`Z}ggTNF$3?el6>SGg646%!4!K&H%8`g~Y}8Nd=ewyyA)yg|ODRvT<z8F&KYhlbf2^@`Ne)RsV4o6XOdLoR$&x)r$Z<a@uys`T{HRtQEDyfpa(*&m(cu<flNvVGZH_&X;RAVf){&4sM=R=B9in6rlu*A8oMq?eHq`(n%i1VhqSZU`W3lmmkVyA{xy2j`H~W_f*=rED;DWD$+&yRRoXy+kv4)U)Z_)bW<iU)HP}MMSD|RLkZ@1Yv8!y$_LbP@s+2n{I2Sz18<mRn;XfuW@%Kgenw#uGF37z7_Ml25&^WHzY+1q17)u-(rH~bXU)@wFX6s!or{}{F5IWHX3$$+-T#nYpI<(3DC_MUjmXe2Ey6Sb{{y%VsBc_gL#;mK`Mq#(Swp)0MWp!ga^+}sCF|4pcY+Ia{Na|r74I7M72~;GLfHLrBwoTC!L`ThS3TwLJBJH4d#XdeC}Jxpjp&tM0X)?h6)EjR>1-HGB`Oh?J9Z}OJ_SH;jiqWY!9A^Jl<w8-aFO>_39rhJ89j%lX&Kso&r&b!0ev&Q(00wpvJrpE<$I?MR%Qn+Anik-cwN`;}cV`1X@AAJ>*-E5$!wsV~Nmlj5ZNh_yo@YK7z}NqondJG#tw5uIWLzdSvvHyb+mYyI^>bFSW42?CbKNFwxP#UX!0L{MZ14pkv@d!Hq|GB$~M1IIeerQ<ur8v#6MvR%K?b`5;oYX{m>J+pU#?>M1s6*%pj93k9(fa;8HAN*}U10gP{D&Mah3jQMn7RNzkFCn*-KH_z~X4aV27XVqGkNMJ~Hd{~jkA&V^(#j~4W^HlM`v_)OYj8eK|3gUF$D=-D)kgF_cM`dTDB<u__J->fR(WMQBJ&()HABW4StsFXiD*!%aJV@?U_rW>AquZ`%cCE74NUG-gPptr1K)J2ZPQ&R<Sz%tSoeIjP+F*d`6^Q9+%*q;kLgSPsD5t^#RuNbAi{qf*z6Gn&hqowYMkt6}3YcO0kh1Y`hS*}C_8yF({ls!!*!UKwg^C`?pzW++{n2)}h+r6bh25>jp^ov~bl*hbMbJTkvJ2Vzs)10*lYcFXF12&n!-kVQ@U(mRfs%|L+NlNFZ45FgF!dCPJUr=2T`Y-Z%}^2aA8S;owFP10&;h+gvwcsOY6za#%u-_((Hiy^=k6&{>0oIY7YkFfBDy$tPr5V?Z<{GdIw*q9TKLL19?Svebad56Gzp3}Vi)(9ajCy^+!G|_@0V8;^)4pH8NhpC6N|0eiLzNRnWvN^@o&ER`tKoaXxt=ykm2a(=SfQVvx3-i)@LWf&VhYG(oknsML)mjACYSWF^xXVBFYkog|P)0jjmiB0#10?f2Fq4K&vSaXda3Xe32L#fNScZQkJAwA*XjOrG3#bC~5Q4p5TQnd|F6k{SF{T467s>!$rkD7;e?6xsf$VsZ=4cHYsOzEz6WYsaT~=wa13JUn>iRva{$?68m!s6cg?D+n@52vYx~dwwLm_qrQ@N?R=1)_4g1?vk%<J=%Bc>RI4UWUt(i05;1$82#D*}twc4fq-V8-U%A3O?i<(&1`^B-@ks+?>H1Y3KZH*r@h~D&>bL&XL|I7?0+K{9s4ntRRrBP!3Wy=#OZ(h?(g3Qs;KTN*Ww6P!%fdjCvZnjE>A46YL1cbqc`LdCr&47D?UUhZXh9A_ahvVOAqSnbQ|H(LAnHB})buTIgZ^gJj0M!8xW?gbea;HYOuFSWC`Uh-w}o7h<0fd$HNqtB%6e)DEztCPl%zA96u%u=B4eiN!u8BuT5Ile%ZUU98A!6gAqKq+q8C23ZOlOig}h%4%%i<YlQD|n&{8s9$aA7-7Z_X6el?M}K^N~_&w_ayPT)U*m-=n>nJ|3vQ3jC$pgFteVv&H?bhe4=@O@P$vuvchLDW`|H}W!`;>Y=eQVw=}u!9y*PHoIm)SO^v<t#AUh&|+sP=jb915PVQcMEWHb|Sn`B<IAXz{pGhUhp^4waV}HGPH-|Bh;{{iH&AliejmdhlKn7*BPCC35jF?h**$eSBQOLcHQZy4(p7dRm6ath?ltzrO^mN=LF_xHoCqQM}E-pAo7{?Uc5=scwsC#I?>>98`xlgYa%^92YP5p8@+(Yii=1y+JQ(ot(QMoZDX5STa_VSrN+Wbc5;AyBe;+UK@{XHyD~g|CY?7O<&uMb8wVKDu&747>1IK4oJpI}R;~=Cy3$RmU~mN~QCU+NbsmxWXh|%Wx8^XUILgx$WowPjh)=Y2uWlXN7Lg6}oT1SBrO>IB|I8g3Qd5Z&b6FWXCwlB2&jd)$p%7k1!Ir9zV}(iL;GS%HuaQdN(X6uz8N3bTGaW|Pl2rE?1xZEd+uY8bw4hclV7>y0%j)jV8XNdPS0W(>$rv&mrw9pTIhnU8-5tj`a5r^zbaC0t#U}ZR(s(N`u9B(oKQYbyPHaxrtr*@vA@qBUJ2uWsenmbhGd*>A45n=KzKm{<f;7mSV$fL^YuYu*R}$M1k{dJS(}5f~SXb0)go`%;{5p(jUY8Uhf$W9c$lfSPi!?S27-jWv*TT!scsSfoNO)&QD{w0ft)Ijsh&i)K(&lH_ZH2PL=#q-_sL?r6&IXRO09d1CdROgvLYpmBz_RD(9(c9eV>2s99{@{sHQI)y2w)bXB~o076SBJsc7#{BpU4|<4r?WlTVjDTii@J?AT*e_vtzm9q_>YpBml6eTyH;TDIAC-O))e#iRc~iZeAIGD)z~F`4?zjV69eZUIOI!V3nLKvn362ZRnZfk=guvGED-r>;V`)(&`d_>$+H)!1ZFZ_H?A4FH0nJ)53g64%^`mYKl#Xri{=c$^$@|8YVU8%eNdivcrx77Iph_g<Kmi|1n`9!{R|+B~UeVWt7tbW?K=K9=i)|3W1|Pc>+tz*f2Xn-8|~I2Lb9AqS%^_ifC^|t=C#|GAS5Pv29XYC?ddz_S+IYl$T+No)X%+nzU_p5RR49CZlrY;Se~PSPaP#dJ6!&xPwLD0&CHqT*a!-9g0@iF~N@!?wo^E+_8u!w{xXYvn$|4jdSBwt#4eJjg^qf;(2+&RU>*zri;XjhHeg)g2R32V#I3Pf{!MTV?}MCtFuuoXi_2<a4|J+Bs7y|HNF)7B$t}9&r9`<839HZ|4u{dBOUL>ME6J1gZ`5jD<WD|S^ed#Y>_>mdDCDkX^TNfNi#CZdhA0D#$=Yqu`}XQ5kr#r@VWO;bPmRLjTzPMh&E^@xlF4#lo`kFf-_-k$?>8*G*A*za;33k$&^3{`=N^-j|~>k%|k44>I$r2DV;>y2GngyBa~v8XcR%A{bM!PLp5tgJ@ckCY1kGs%xtg+hCbpoP#jRnkA(_%ikCtyim2oj-c|Th{q~zGCjn1=CH7^&^@$74S#wu-46taB#ZmgGM-7r{Z=tZ2nFyYyYnDKwq7x}>;n9#CtFxj~HGJP(=Wj9^HVHK*_EJn?h9$_?=g(H?9Z9?+t)-x_<?`g<{X}*B)H^!21;{r%iWjZFfoIn!C}GcwK%f}IZglo|G%J*Egjr~muo}yV?j8G`(SSCOb-BbruWdcpFH*~~jz@%`Dv^-l=zgJYV5iW^nM==eeFNQnSGcdE>W$V(lIxxOY&stsAuk_%_9fj#9B9NrfrC0mV+7~D28B@$MGntXC5?C(am#?&6hSa_8p2)^QK34g3|87SBult1bGkJ%)oz+Z5S;)soJ`5;LmVC><T0wKIJPvL;aokIW!AbJ#ThB1c_-PVM`W}`0x<&XLzk9Dk3#=a)1jwj2+`G>pRsVkGdUG;;UwCRVyA97Ew<zy+yw-{6|VPm)j1I)GRg)<qgjXYRC#-5px#fB%MxfM<s-KC6>a#ED>vdE*v2-hG6<0{=6rTKCKLT(RvHo;L>KW|qV0(1y#VIO<37d73O}ewN3A`spsG*CUy!S_Bq&dS(iGmvs=Z1Qz4ow3q1-a%xKc8STf7+^-khduB_PN$e=0n#$?4~j{}Nh@<UOY{(~$^?$7V7LB|k@TtM}eeDny_S$gCCJ6HSiE)^R{X_jfdNfi5EbZuJ_P6m6AgBY`78V`ee2Grt>9Tyw80Z1a>L{#kJ38icXUgOaDCs0?<u?^kMT0`KSa<~rHc`%@>9`8r=A#jGkcHg)}*F$CsN3s()7)BJ~-OPQ=MHfj}usxzP0H$wUT3DL2dh9!tQY^)pUIeD)}{*?2Ej|8Xmz}L;jox9k3HF9cRA7>kySoz8nb&N}=*9SeCDQkrySq-e=D^6H#(M5fPZLMU|eu*1)wB;7}$u_GX>3c{^C(^5hR_W{p=`D^Fa5nK!F^&#Vcvrx@7HS&b+9CQ#rcOBLYE(7oM*zxGkyIk7{v_-P_lf;)^9Ep!<;$;oFPCrEF3J?al^YQOIZlfI^+}Mlszw0l5Y8Zw!Hb`2>Sj8DP3x?r1t<87x8P|npF^|`^x9uk9Z3PIDNP~iMv+E<>1;BA6(Xm^?*E{DmgMXkpc+u8wQ2U}Vl)t2S)?$P@u^6LBYhdMPe3U3pSX243053M<`G{q?)W1&T7@X;zLiRFi*6o2cV`Ge6v)MJ-c$jM!IWG+g7h}##SsPOV%5Utp((4#`6mpwO*v9q8W(#AL^p<fRRw^Xs-(pxV2)iFxt{2n>=+KM0p!NHV)6Slgo6^jO~@CRJ^}bArKr$eO-`d$22hA3mi=Fm@r;zRy9`Kx(rrclNCHcmechw#v4=Dzpo3ha)$mkzfX8!=@V2AYH5MS&%HG)3s6J7mn(uq_0i2w=nEPV-KJm-@&Jyy7LAV?a4~2q;9n}xIIl{sgEQL5GtCZ^q2`9%eRE?)C!POG1FuYObr}hicW-EN;BiS~$#8wgHLui8HN2}MW!U7nTE2eG9dD7g7Npp6oQMrmU*kJQWz<`K$O3}=Ma_Arq&D)bH=~S}_HjFZlQfEjLc=J`mdw4=S1!0;1#9)1e7c^#EexkaGTwGvjKuT||OACg~-QqQDt(z%Ytv2D@m(}<glFA|>(T}s@<)iJkK@jJsy*wvH1sZ^XUbZB%6t++(Bt%-d48L<m0Gb+P0o+*6_?mE{?3+UZl|97lJi>AX@6GjbA26ktcMb}5;uL@Oy{V5h0btc(7d4Rwfo~E;z&~r5Db<{KbM5evn*Nb67Pxb>ZTu;lO&jCUwL-BG96aPrksmC~6m*@+^O97*k258u><TWySg43n(v_4*E~FH8yby_UAV{7tt#QYL==`8M+WcbUKp+D~kyojmz9H1+si3Ma$v}xxysgOZ=!8+2-?bRC)aBd~9Xscd&|TJr9mj7UmyQMs@o)5-eAC=U4pAq?-9gQOL9p>I)nZnyZBr&lO+m%XSC<yfTG(VBns^=s<A=~AR)eN*6obZOdkoSyZC7q(;?bJRkD$>liY_SvWTRTkhNry;-TC5V6v(7`EWf+Mogj;*=uU^av&$G|ACv;{-j`-h3$`FUxbrv1ufP39>On<ijX({J2{Y0#k`R1lS)5M!B7hKBxW!j;Zp-pczilF@qydPEh>)X8Q4zadfwOQtb4|G6v1uJX%PyK~ii>B!jK1%N)zEs}o3a;5<_!4+bs#37c)F)UgVld$-_TPN)4p!PWMXvWeXMF}%%=?|HY3=t#3)MaLbnK86_*_hjtV<AstuvE9{wusrx>Ev0aaT<8miUHpe-wh2MaG<&~Isz>x)r5p3Dj?v%Fx5Wi8s+FKL3Hj4kIR>J5&pdY`9-R`>`-`k_jHlSFZ<B18egpbGaS`Z428C+moT;edd7;KxQ8t?~FW0wLlCtL*^lEf_$o?aSBVQThW(yvX9>6~rv1%fpAt*x3@UV@~#?y=6Jsen~X1z5kI3;4$s~sJeqbi`TJE%mY`7PT^xQIU}{ate|#w9=N508yIgxW?iAQ@zGWz#?W(kXznHm(%M*Pup!YM+6~#@>*}_|Qc?(pC`F2L-<BXep|@5L6)=wx5y?_cS03f*2Sm|fujO!+T|>ZDwuLKO5Fi9{R<s<ckGW?ADDv*63}1_w(`dEYc7Zs(?4da%#-Gd9Msvt=V+=kRRTziV8$=JYz+eASMY(nxuLa;oK{fX1JX;3~3pa~zGgo%RU&Zn=VtM}G%p%qks>r3PCR;^Z(L+~Fv5c9-$`y(p4Zx>k24T}EWIaq_LlHh!<t+P^CWBs0V=Rz4Gk;_6_8&!xFYd!4L2d#SEHa=H4Sy}IrbWFxiVsKRNZOs_a1xM?fWCgY;X_{eM%#8N{X5&T8u#50c}{QIH68Ijp?*kII~`Llz-?ekMZV5I#3IKPO0lU))PZ}B8W&K3po*g7Cb8oP80hRfNBK-*?8p2zP!-?Qb?PF=S}s1xmc5X7t5>02B@tY}l;Iip*+qg5bXMzf2_OR`FjFMjhL``?S(%O@$YN@%QM)|yP_NGs<z(zHV#lZ>XhSO9y&Wa#r2ZS2rd!}QUZt&CbBwhE049aWRcN9X$<~LGFr6fxXW!5l2+Z{p*{4=J3#0fMFlP*Y!0b%#xtgLl+w~;w6N+=O2RAolwfC5aVr>#85P#L0GaM^HKu+xO^q{C$D)k{45HMf6s%Bsx4Y^a6ad8ZqFmE&4u?i{$B6GA=AQ0T~HgO&xYqeD+`T2eINJ7lQV`S%tgxj3Py(3Fk@n4PVu7+vM+;zOSd6*-sdAcZh(y+L8GGRi%PM?dQ1(m0|hIY~5+!}+<0qKGberSV1Ss7x=B^takygF9szh0n9iz(ey^{zOJ2qI<m2%uziAKFD+H+q$%>vZm`2ye5=i?~Y#f+pL)naY9K#g(Tttz<1#jqaJ#8&CWxFNm~NRPzh8P!NCEwG?e1flb$L3=6P50eQ_!!~q^ow3Rv=#L6b;>dWP?A*-Pns9vh%cN!NcT7x2e9;0@X?P?tr0ZE-zo2TMyE~SbVMDG1*#sY8~Ue3zOR|v9q65kmqFQ`ViK_dZd{sDch=D0*y4c=wzBEBB7AsHA;q9YbV-QkBxWH9%pOtJ0)l2KK@lVq41zRH#ndXVm-%P3NgQ?MyGInDxx6#L{=Q4wOClH@2^N8xh=AZ=Fpz^2aF5l545VJx(<fy0`_w^&z2t{2q%Lph+-2tBH}IBE411(uW%mqk|!)*K34kZu=j&>0$r4w~gruuVy2l)#YF2zv`MGc0i>78BS<g<iS{l-07<@<~BpeEu|&%w5ObDC{~IJ2JCc{5Cchtx56io>Cf}o%T^8C6%<hmDACC;m26iIt|sF3YDPrX+d&gZg?Y_bl#`hk|kRViGD10D=QFtqGb*qEv$!DBflxoCht)g6U3yaY}cI%pu7AmQTM8UtDWxk!<r4k(p(gQ0(cp8GFsAKVA|m!<*a=+elp0K3VTI09xerZbgjlImLE0DI^N?;ova9X3jC1npt=>f9k0)S@LumOhK>S#odM1SoB}6LH5#09M&&jiLCF>o<zimoc`o?8j+-0x24D-=sG7!7*AriFS+?t>r!RJtc$4e9RHbcD%}uhuO33xPiH&9LEMp$p`4NE?y*9;eAwYy$E#L2YuJ%G;@E0wsmPO!FuXhC%FYDvGZ@)ix<pbe0u0yRgr9W1>jY*10YHseA3#y<s#LH&V6zU5wkz8MDqPKP`V_)Yx?rnL+PPXtBRf<h+CR3tudc_>P@)ghfPW|cXhk!DkV&2eKnJe^tB-EO#cj14j;uK9SosjGhBn^~GM2$jx?Vz5dNLnNSweEzUr;n3e&74TRdx#4zM_O#TTV}NCVa*hWWj%~>xvm}CP+&Y_t^Q0qR?{|P$lul5XfTJqK(&m}vrgayqiiRznU;zWV=#l5(=k3hLXuCLl}I%8#F%4O-;>s3n*rrxEZgup8nV3%p_RG>98`N=uoXT$)#L&ZxBea}PfV}qUmjxc8A5*5?)Ri1(Dnvmi3#ZJ6i%mof=k><Uogk1j$C!BZUXO8RrbIZ7|7k#2k{ln8eUl+!=0IFc&zQ61be4fBJ<T39kZ28pm?`4uLoKkIo&^|PeF&78_~O+3COASP`X@jZE>!-*PcR`S-F8-yYZw6eLdZ0<axIWJzHEZs2w9!2hoDX;P04sxa8-H7rvmV5RXafbe$7oiq=p><cnISEv>eI1|EGO4bp25{3C&dJFNeb4VN{)ST6Jsx28XsKibi!nHfbWLLNQP=b$z#TO{%VlJs7UX3aP}Fxj^3C=m3fYfh98vTL?A1K(r-zMTC6Wx;`?F^Dk-!I?5|?aUfEX=qWQ{Wbfy$Ue_pOfcVsrx8t^E4^;=3{JryiI5nYykhmyKF_QxlPJz}kWb^LKi1^gmY`Cdj&aE<b-Z}1v(3_3<ZvDp0psLsdN0)C(@Y7ClBFlh^Mrji49yPAssmVo<QXdNgI%>((#3sGk7ZFiM>28r7essAL-k2Effu#9kyyH?eoB{R=VRvW%g&I<SvB2Lx7TUb8+4%JpTbe?Hm;Y*{>rQo7Rdgw-kbYfl(MOb>}x>anp5|&4MHSo5}RWQ`@iDRqtwBO2{X;_ETCiOJD2_BU>pkhB056NVOa}~(!I|?!5VJUZKIDe^JW3FNjT|J8@qov35t87LoyXlwQ~aKut>`|e5a}8T`X$8`i=D#DAgw7g~>TlzAkS^Ot7#)aKHU4*;nMGGNhl%cY?X$TwZl*2Dzt>wf9njs(WpwLZtHoet-jWP6|iYzijU{R~qO!9OK4eQ8TQD$MiC3R{K&k=$c<wAK=#<pm|h;NqC3h=@AyrI!QvnQ|R(~h@rDGs3Ap9ZrK_#vVW(e>Kzd|VIXXUuEx|dlD7hCaa4`p6;&?L>ZKEtl>;#JPYHIrsB%YLo<pfVevWqZcxFx`0a=X7W^t>ZyjpK!qm@XY0g0?Zt8$D{J4W7&sPo4rPkY9~1cw9DV>sp4am5D833TDO+Cxn|EOLa%8*s;KsO7c`-Y0|fiC!^`f(TWclN|>diPUr-QxZi=bNwh9LaWp`wk~8XtFi->4^7K+B;cF{FwfWLQu^R&%|T=@(#GiQ6xmACsMMaa-RwXeRAMSJ@2ljr`lW{%k&`tpNs+<0muaHg8f{i&J2K1_%*)*m(Q4k@!i1d#RF<D5;S%_08e@1GD+E17^D(Y2k9E!lD~mElx<tV6mPv^^83;8~!IlIW>X=X(i3AQivG-`qxl)E9)Y40`kcD1AoBOD)s;px=1t`q5GD5!MFplZgmw<OdAqYheP9UFu%;Myo$D*DpBh2fyy$CTCrD}Bdc%1-YpE@LXq#>c0xRelYwXXoq=XbU8qwMbBZW3|D+nCp1JbPh1ane#mB=i5E9?4vewcWcrMS82OC-J^uLW0p5bLzWz65AliG@<}ulNkm4?u>Csy1{bIOH(zWn!0qx(>$7XaiK4-F`L9Fl`%7@>%GQ*k!Y8AVsIDdlxV%9MHBr>4Hw`hi66FgXtl(GQzrai?V2I%pIi%GYq!5fCb4BPc>}R#OV*bP5Tn@Sa!j{f(!C69F^D4zc$>@LMM|V>DlaN}YrQ);vDzDscKTD7#}-s3eR`nngARX~E)cXAHWV>cq^K2%YVY%)fm#~Uw-G=?+T{-g5AhK^_lw)u^5~!b^Ur_!)2F}t?@#~or+<9@%3(FGrq#Uqo8kF?cB}o{pN8ds#<xE||L1l!>{i46{gZKAjnneA=l|Tj{b5=!C-eEw=f9nHt7*TQ4y$?n{Gapro9E4H-k$$_c>nUvwA#$8&1SVZ|Lx}dx7%^Goz8zg|Lyj$+O1c+^FQBR-e<Sky+89Zlz;x`|NEbwUwc~KXS3R_Hs|+Sug<?<m{-Ge^`6WBtXIR;!;Oa}16!8v`9IIUV47Cb`NgL5-)_d$W_h=HHNU>(`J3ncYCaFyX8r!<+x=?0e6n9{&VRc-|Lt~p;PZ=Z&wsnyu6EOEcmBP*^Y7g+!*RHN^MCx)AOG{e{=7{6@5j}8`M=A9jL-kGexBIZKR*B8zZoz8vAg}x=N~=)lh^-$d->DVS3H0B?)s<Zt3O?R-SF~@&rdPTm!Fw0KXQ4%_rE@WI9<N<Z=Q?e|M^dU{?mW_)4%`AKP<2JH|xJ$24Nmw{@=s$|Gxb9__yn~|7YIY&!+kLzo*0Pr>}oCEFTW@%O5B3_v7nVz5KfI?hB^f&40iC<ODvu{;!u$b~n#>u>a)t-)-!J4V$;Gc>dp!{Lantzqijc3^)Jz_J(HEhW*WdZkPW8Be=}Y|M$m#`LE}N_xttVPM7~P9uC`SIYF*Jo7Tf_IV5g>Y;%})&)3BIZx4szuw9SiW?awXX8-&=>-9YEw!7W9JM4Gke%uc)A5NR?v|bN~!*2QWdf3cw|9*ei?8afUe*W8Kr#=7ZdOGZf?ekaer`>p1_S4I!+j-s&huyUN^yaYHKi^%$%h0|2Z}4BwziPYQ9}b7*A@=j|@=nVi=fm<k%kP_p<;|!0_0w@4cI)Mr9QN~O-mUlJ>lf_To5Ow_#%Vk6_J{HO?ZaVS25G<BPMdKUmIp__eEA)R<yY)>!)_RtgY@k$=k0pE-|oieaoWwB-FZ;P!@Sw=rp>h3jBii6JkdOi+j$v=!)CkRy?^)eyAShj+$=LSt+y|uwLIl|Gw$a7xZNJsyZLGqrsbn?T!wLZnE7?Ux640VChU3A#?3Mcm!Do%ls}&P?Km&fH_rQcdl+6PX}65gwA*f$U%4HIx0%}<mK8A#&wqQKxYsXQe(7$zjNiBn-8^oe7s~Qz<1!uV-7?6V-C=Y2+2!T7!)`w8Hp^n$Y{%!XUfyonkDFz_cF+I!{d@P*VfmtAn6}I6IXu7QcG#|$U$@^c>ug*`_wuvr!?Hq`M_uN8Gi-<X`Q?`p8}|GCxZCWPCAgo>SUkV|GHuhc8kd=0es=ddj{9YeEgwC9&GKvBHp8;5Hq&<b_1onu-?q*2e9Jp8%WJoumQP=&Y<^z!%a0Drs#}Kf`NL_yY_R>|`Ky;Lvuv=p8DBQT^2@i&*X(wi*G0I@>~_0ZR?gx1i(mfrdiiLaHp?h4lfI0{^!Be0&uehmMf+u=PA`u>toP5;w#?M9-7X)`um5~mYRkf0CU4oi%d>%Tc=^-wR87nCEt_@O3NPPyc$v}V1;^d<u6duw^|1V|WlJp!db?S6-}d?Om(g6_b68G{ahf;7<%gI5T5rc?cdqB<(U#@8e75|v<@i|-+r#rH4R5P@e%T%K@@o&<&FhJ?S*BpUdtNZl$IIK+ejd1GSxv*RU-t0&ZEly}zgzy{ykDMp8K}3nKP>BF8Rg~2mXTV&e(AD@56i;ZjL(m?+0Ex;Z279?OXqocwZrf_^XtPfZ}*$c@?z`VW;yb%cI<R`dDUe%FTd_}$1dA(d_G>6H(4*s{Poa$UaHeFR^!VO*j;|vxEq#ZY*~2o;qAQ+%UQb|o6B0>49mH(_fNrjTBdV33ztQ*oz7?T^QX)EE*ooleV*4j81~DWTh`w5F*Pj1^ZfJkVL6zWMY~>B;WQjJuOA(jQ|+)@mh&<z+wJSWo}PEaG6Bo!uq=+3{k`9>pWk_UUT(|qy!@*D^P?<h!~b80x#QLm13~aYHo)PZhjCyS&YUUM-Cael@hDgdC2^PJOn3FHMwF_xpN9cGtpXc7v9`)rgOV9p=B|A99qACp2_&0IkoxEW8gsU)|3~bNsbRr^ZTp|yU;La27lkNMJf0{Pm7fBqSE#WgF}-RJK;c+H^5tLchkZjj-1nj0r?m&TID$2)jVBj1Vx^mtTaj)Td!w5d%VSLM=yeyWk5Ga9W}F<68wrRhKI(K7NnCU&+B2M@I%U%mGt$gPQ?b+8o>LbknrGL4Yd<WL8x2=|)IvGS<hn48cJ|aC2!Q|4P*4?=4lR!V&=kJG<F(ePFXS${gL~<?x;mF=S(8V_!=rH7>)j>_!8Cy3h$DAOO$*fldS>(2Y9PjilX>91HbkK@fH63Rdc5E-%g#^YS@BW0z{GJhg9?=lC4w)b#y)+638XbYGYGu4*6^szYw7G(`#wFL1uk67RLmC#yRYH=I;I^8NIHAVVYp%3@6L#M*6fi6@wUZ4w^2DUN$wz?YjtFzye2ZW;li=bQ7{j2L4C!>jbtRw7*dgZdP)qQ=n*6dHNCEL^9qofIm+6TlZ)Am45sx;<628oksIyfuE9CBi6sFj!H&A@ItEhda+OLqqBq9rJ{N}f_=ZfqD`Lag)8BU)xmQyUZ_XP8{k0liA^l|-m6^(^ABu+($<%5e-c6A>OEP?b!#u00Cudov514zcF4eh$S`CDqk4U<+V4<dj&&NjMeP&uJ#Y3=bmeU%_Lg|v$&iA<!v~5P~gpOMI+o2FuGF$^DkGqqsW_>ZXp<h0&WN~wP9svGX4aA&PfVD_s+TD*k;)3s-#6jEFroeO0?O>Ch?5D{HTIBn{PCv6WJ=XqMn*DdhI_1M4$pZNJ-RX(X!+pZZ_{ft1wmFATl-lao6T^Q4LmHnr+CdgBQy?lHn=(OQ!TD~qOf0rPb%Y(NnM}b-=Il$jXXhUpNF;391-J*uRm!2n9rBECWLVkQ#e@AB?wCLv*uf{=+iB1Xf7eq(NX+%3CzG;61tqhY?0Om@YwNZtu-^Nl8HgS`C%E!W5_P~mX80Y_M}8O!(-jzkuk-Tc^xMKOp+XN@I-U&YC$qL&<XeA42!ktDt#CBgM}LJK0TnVJ3m;9G_qfa{3htCA`#MfyIg^<cWZ>fS^VgrBZ*RZ--`w}`zX?Cy-~R%#b~5e")).decode("utf-8"))
_PLANS = _PAYLOAD["plans"]
_TREE = _PAYLOAD["tree"]
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_PURCHASES = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}
_MARKET_OPS = _PURCHASES | {"SELL"}
_STATE = {0: {}, 1: {}}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _step(obs):
    raw = _get(obs, "step", None)
    if raw is None:
        raw = int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(raw or 0)))


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _shops(obs):
    town = _get(obs, "town", {}) or {}
    return tuple(str(value) for value in list(_get(town, "unlocked_shops", []) or []))


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(
            last=step,
            calls=0,
            first_shop=None,
            committed=None,
            dues={},
            previous_inventory=None,
            previous_prices=None,
            previous_market=[],
            previous_shops=(),
            previous_step=-1,
            stats={
                "route_calls": {},
                "commitments": {},
                "contract_failures": 0,
                "predict_buy": 0,
                "predict_neutral": 0,
                "predict_sell": 0,
                "preempt": 0,
                "wait": 0,
                "release": 0,
                "changed_calls": 0,
                "fallback": 0,
            },
        )
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    shops = _shops(obs)
    if state.get("first_shop") is None and shops:
        state["first_shop"] = shops[0]
    return state


def _record(state, key, name=None, amount=1):
    stats = state["stats"]
    if name is None:
        stats[key] = int(stats.get(key, 0)) + int(amount)
    else:
        bucket = stats.setdefault(key, {})
        bucket[name] = int(bucket.get(name, 0)) + int(amount)


def _plan_contract(obs, route):
    plan = _PLANS.get(route)
    if not isinstance(plan, list) or len(plan) != 719:
        return False
    action = plan[_step(obs)]
    if not isinstance(action, dict) or set(action) - {"farmer", "hands", "market"}:
        return False
    if not isinstance(action.get("market", []), list):
        return False
    return len(list(_get(_farm(obs), "hands", []) or [])) >= 0


def _desired_route(obs, state):
    step = _step(obs)
    if _MODE.startswith("expert_"):
        return _MODE.removeprefix("expert_")
    if _MODE == "ablation":
        return "default" if step < 216 else "dairy"
    if state.get("committed") is not None:
        return str(state["committed"])
    first = state.get("first_shop")
    shops = _shops(obs)
    if step >= 72 and first == "YARN_STORE":
        return "yarn"
    if step >= 216:
        smoothie_score = 2 * int("SMOOTHIE_SHOP" in shops) + int("ICE_CREAM_SHOP" in shops)
        return "smoothie" if smoothie_score >= 2 else "dairy"
    return "default"


def _route(obs, state):
    step = _step(obs)
    desired = _desired_route(obs, state)
    if _MODE.startswith("expert_"):
        state["committed"] = desired
    elif _MODE == "ablation" and step >= 216:
        state["committed"] = "dairy"
    elif _FULL and state.get("committed") is None and ((step >= 72 and desired == "yarn") or step >= 216):
        if _plan_contract(obs, desired):
            state["committed"] = desired
            _record(state, "commitments", desired)
        else:
            state["committed"] = "default" if step < 216 else "dairy"
            _record(state, "contract_failures")
    route = str(state.get("committed") or desired)
    if not _plan_contract(obs, route):
        route = "default" if step < 216 else "dairy"
        _record(state, "contract_failures")
    _record(state, "route_calls", route)
    return route


def _copy_planned_action(obs, route):
    action = copy.deepcopy(_PLANS[route][_step(obs)] or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in list(action.get("hands", []) or [])],
        "market": [list(order) for order in list(action.get("market", []) or []) if order],
    }


def _signed_market(market, item):
    signed, first_slot = 0, 10
    for index, order in enumerate(market or []):
        if len(order) < 3 or str(order[1]) != item:
            continue
        quantity = max(0, int(order[2] or 0))
        if order[0] == "SELL":
            signed += quantity
            first_slot = min(first_slot, index)
        elif order[0] == "BUY_PRODUCT":
            signed -= quantity
            first_slot = min(first_slot, index)
    return signed, first_slot


def _tree_predict(features):
    node = 0
    while int(_TREE["left"][node]) >= 0:
        feature = int(_TREE["feature"][node])
        node = int(_TREE["left"][node]) if features[feature] <= float(_TREE["threshold"][node]) else int(_TREE["right"][node])
    values = list(_TREE["value"][node])
    return int(_TREE["classes"][max(range(len(values)), key=lambda index: values[index])])


def _opponent_path(obs, state):
    if state.get("previous_inventory") is None:
        return {item: 0 for item in _ITEMS}
    market = _get(obs, "market", {}) or {}
    inventory = dict(_get(market, "inventory", {}) or {})
    prices = dict(_get(market, "prices", {}) or {})
    previous_step = int(state.get("previous_step", -1))
    previous_shops = set(state.get("previous_shops", ()))
    labels = {}
    for item_index, item in enumerate(_ITEMS):
        own, slot = _signed_market(state.get("previous_market", []), item)
        features = [
            int(inventory.get(item, 0) or 0) - int(state["previous_inventory"].get(item, 0) or 0),
            int(prices.get(item, 0) or 0) - int(state["previous_prices"].get(item, 0) or 0),
            own,
            slot,
            item_index,
            _seat(obs),
            previous_step % 4,
            previous_step % 24,
            int(previous_step % 4 == 0),
            int(previous_step % 24 == 0),
            *[int(shop in previous_shops) for shop in ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")],
        ]
        labels[item] = _tree_predict(features)
        _record(state, "predict_buy" if labels[item] < 0 else "predict_sell" if labels[item] > 0 else "predict_neutral")
    return labels


def _merge_sells(market):
    merged = []
    for raw in market:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL":
            prior = next((value for value in merged if len(value) >= 3 and value[0] == "SELL" and str(value[1]) == str(order[1])), None)
            if prior is not None:
                prior[2] = max(0, int(prior[2] or 0)) + max(0, int(order[2] or 0))
                continue
        merged.append(order)
    return merged


def _sell_controller(obs, action, labels, state):
    original = [list(order) for order in action["market"]]
    if not _FULL:
        return action
    step = _step(obs)
    has_purchase = any(order and str(order[0]) in _PURCHASES for order in original)
    front, body = [], []
    for raw in original:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in _ITEMS:
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            label = int(labels.get(item, 0))
            if label > 0 and not has_purchase and step < 712 and quantity >= 4:
                held = max(1, quantity // 4)
                order[2] = quantity - held
                state["dues"][item] = int(state["dues"].get(item, 0)) + held
                _record(state, "wait")
            elif label < 0:
                front.append(order)
                _record(state, "preempt")
                continue
        if len(order) < 3 or int(order[2] or 0) > 0:
            body.append(order)
    for item, quantity in list(state.get("dues", {}).items()):
        if int(quantity) > 0:
            front.append(["SELL", item, int(quantity)])
            _record(state, "release")
    state["dues"] = {}
    action["market"] = _merge_sells(front + body)
    _record(state, "changed_calls", amount=int(action["market"] != original))
    return action


def _safe_execute(obs, action, state):
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    hands = [list(order or ["PASS"]) for order in list(action.get("hands", []) or [])]
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    safe_market = []
    for raw in list(action.get("market", []) or []):
        order = list(raw)
        if not order or str(order[0]) not in _MARKET_OPS:
            continue
        if len(order) >= 3:
            try:
                order[2] = max(0, min(1000000, int(order[2] or 0)))
            except (TypeError, ValueError):
                continue
            if order[2] <= 0:
                continue
        safe_market.append(order)
        if len(safe_market) == 10:
            break
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": hands[:expected],
        "market": safe_market,
    }


def _remember(obs, action, state):
    market = _get(obs, "market", {}) or {}
    state["previous_inventory"] = dict(_get(market, "inventory", {}) or {})
    state["previous_prices"] = dict(_get(market, "prices", {}) or {})
    state["previous_market"] = copy.deepcopy(action.get("market", []))
    state["previous_shops"] = _shops(obs)
    state["previous_step"] = _step(obs)


def _fallback(obs, state):
    _record(state, "fallback")
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])],
        "market": [],
    }


def model_status():
    return {
        "kind": "v115_contractual_path_forest_moe",
        "model_id": "v115_contractual_path_forest_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "shop-demand-contractual-complete-route-router",
        "production_experts": ["default", "yarn", "dairy", "smoothie"],
        "opponent_predictor": "lagged-public-market-impact-depth6-tree",
        "sell_experts": ["preempt", "same_slot", "one_step_wait", "due_release"],
        "state_contract": "shared-prefix-one-way-commitment",
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    state = _reset(obs)
    try:
        route = _route(obs, state)
        labels = _opponent_path(obs, state)
        action = _copy_planned_action(obs, route)
        action = _sell_controller(obs, action, labels, state)
        action = _safe_execute(obs, action, state)
        _remember(obs, action, state)
        return action
    except Exception:
        return _fallback(obs, state)

