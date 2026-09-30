"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vElZN>i;L+e?%M>Ez;cCysY2$rXXmL>zo5DWux5Fl_CPIf{5_o&s~@7-JXN1j7gy;cUuN>BYhZhep}^6-%Lr~iKTuYdXb-~RgdXaDf4KRtW*^8Nc~AHVw5vw!=`fBegT-u>zBKY#nn-~auu|8@7jKRx^HPk;RLyW5-BKfU_!?9*F6|8V{C?#0#fk01Z%t6%MY?8lqi4?pC;_Wt_q+wISM_vr)o&v<`*{d)V(i^DsAxPE){<K3gb{`}StZ*H%jm0sQb*vlW^{Nd&2A-uZz`O`mN!#nSPxW0b(`Mtvwf4+YIVL!u9Yxw5X?|*vt_>-T1@9|@sHQD}g_=Z}fD{mZ|N1Y#VKbLVRo0q@+>CM~MfBqx~AAY)9CwKdgLwfi2<&PiE`!o!0c+7r~_rE%h3@7pFDX*>zEBCm&-W+~@`QiHZu)n)UhTDtNdG(SOb$Xbv`}a?R9sLUTW;==dSE~n^%fm()9+!8s%cp$+1$vS_-#qnqcjjkUF<9cu4DR|R*c;f)^X}&hJAU^m#+z;Cu)z19Ts^4A#bNowF^%iFTsaQsF7NBszC6CYF)zE#PBzxEAe((cd%@dCTjq(y+5X@!A76@xELv0g%J{j9uI};Ws?~k`;7)KpuiDJgZr1MnfOKWIe{&wcY(4MC*O~0Y--6{lzujNX;V1G1TmGo+a$aaM;Vbokqhl2Z7)~tU$=CH!SIC3+ECPf^fyamklV<=Q57O;3&W9_T*8BIx57Pmf`kR{vkOzExz|GsY*RMYO`FGd1AKtuu^Up_zj6WfKGWt@(mYy7`_~B=fet+}RajVV_!{#T1*8l<b!*3g&%;}TC=;w#`4SM{vPS!S_&Ch1&x$otV6#{v(T4#~&gmu;<HYf1rfSNyyU*F!m8xN(k>MyY4+Z9=PK3wYDA=UgpJltQ}@?OaG`TybKkA3l<9c<v8_0OEJ#6nlF+7S}|_Gre*<;guaI#Y^>f$yRnfdV*+wDW@yMcF+>A5{Ic7lG0?q@lb&YTAn9_*!wZUU&@l1R`lg7wiXACy+}&ZtV*3=Mh^!tXEtN-&z;+lec~)`CdP~y!|I<4z%d!?Zk~O!bi0HJo?j^R|@^+QTs6BfJJy3EHL321)zvyJe&eaI&W04@xd|n&FOd=Q;7ugj;TR8tiIHsd1tLHiVXj<K=nPSZAh)jp^G@%Ql;D>G6nCc9IfZOhl~>1%YhqyRUHv49x<-tW*=gnt5x^wsz+zVnd6s-VXRZn8Ar@_HqfB=y*)XV-6?23r*aDNgfJi1&(}nUI$1&2RS`!*GJ|1-i$@WP3NB*0$_-gzFFjaW^9Yfmf<B*cohBSv;cOnqu<9WQSIszT&p(Eyk)A4|jlf}hemeIIhs{VtoIv8u4rgN5See)q@k^263;~&9q9+Ip29&L1lMZg(SL8gGpQU&6{DWr%-OlQ?z0Lj;3Yp`9vo_9DJ?P+xe!F|@C}DH{=lIU2g}l89l3-sL^1Gxzm^h$ajYf6DM3;Qzc7xu3xPAHaZ?A7}|HzM}P1>k-!4GZw^*G78Ls~ff@%Zu{Blx_*Hm$&B*>i9`%zWX=+iJLz71WS?Es=B<PZvq|&7vJ7jx@;Q2MYZ;i`UT$XzUof5}Ut<5LtnQS@5iOG%}`M<RawT#~kQLywJ6K%MQ>|_rw3;wcEO6YDmk;e|UPI@@Jm?#VW>!q0qPCgIq9C;?+3o(ev6J?BIPp8St6Ao9zrU`JX^#s^OpG=p^9~O#mj@FXr1KG0>ml(J4zMY4Si=1C(OfOyC==d1A}=sy?K%yX)OxcDLaq?I#Tl^5AM3eS|U-<b0lH;{*uz@8sxg^eKNsO<Xc4T@4noWts=DZ5KZzkOU4ft1N{=CKc!9xit6`^zkXnZwniiw;f8ZQh{o)4Dt#^jyGa~wpcbaPs3tN$O#z?0nQ(Ip5hUT$&z`#_CxZjSMVnJsVR$DdZ%b~OyYL#l~<SJ;sq^7<rvqhp4WGM-J_p&!de#{0HUe|1qQwU<7W%!7_Wkw(8ki`uK9CgR#-Qb&d5`LDoCd1JD(HJ57q;#jbQ{_P*EE~#Sz4(Y-^Dk-&4lo(M<k)b8{z)SHCvwXtE>;OUoGECNA3yr&lr~4D;jLpAPNUXGM$KYiypOFgf9f(-BKmFY)IJcBDA;l<-GG!+8-Bx^50xRa91L86dRBEbV3@TH*3}&4mLrN~~7K{SaYY1xh^BCI+GnHH`2l<YvV5+=ekrg?G;j8q&<%d?YBJ%!pm{@@?jh&q5srAf&iPQE1kPW%~$os$TL<M?7ieuId|50@ck1O5`YE9M!16u?E2LDDmGoG#w9VqxV5$lx`y$LCh}WVjNi$%p(lyc?<`bqp=*iB76mO=KYSjskD$N-bwR{yH^n))W>EHMc0F|%N<nLH+i%R-<zfFF>BD=pM<bDv9W=LCToYt%4t;5KH_qhHr+o&O5HVv=%U+*Po?9=cXpviIa|jro!5M0TmZMNpvg4ALHK`+5ftY;3+glujYQ)0rqgR}^74Eno!>scO7c@`0EOJw=6S*KbpGt-l@61ZV<kJcmp$3=tHIwLsG|VnEyE6UJemfvisxMmSUTCjaA6fCEd1j1L`tlB!EU4hpLxqV&dSOly1OEV9P11~B#3q_sqzxk4KW1e28$7)bHi<IGWC+VxFrl)JhQMLUbHBE{;FCim*^{BigEabJ_jxISJK=qu_T0r7Jc}BB{hjsSCvrC1)ee^K;n74hV8b9BFx87G6yQ#8Cu1q%9ei=7e9Y(wsxgRI%C7)qO4k;^RI1u!1Lc?=kBR`QPL~Kn~KkeBh=jFyGJ}pa66Nee#n^zG*Um4)R~@|gh*to;E@c;4i712kxmEPAKtwE{ilC_GmMOaG<izH`MLRdc}AXv@8MgAdk(@pN4gty!@;Acetajn`#^O86CNKzjEK-#F!H!~ei8^hX-x497Z5zIrJ@<AY+@UDL1DzFEgM&5VJrElql@X!!+j}MxKx@6a0%a6z)-p58<z5FGeR9y=OuyZFjQzyF(t~~AWRf4rav>i+|AT$5W?g*tsk(jlzqgL#F4Dy)SO0K*?}DB+XsI~eNE+F^Z~Lw47W=h`n54u9xrW)qGC#P)?y+&(s8?ko;It5)h~C!9JFD0irbI=uE?2-Y>tX*?d~WEI|D7Xo1BOgOG(j!e2~~`lkP7~*tDEx3GIX;JG_mOyFd6;fp386PZYnS-=ouEiZ)a2%V#x&G^isvOe0HKdX>5jiQ2TS5qps|JB;35RL#&z@_&};C1nsn4X#zZ@Ti=X;@k+CsTbGEx`t!i-eN6dL%Ot%fZokrsq#$cTtQ0w)37#i9bGr*&csW_%Y;9UP?DPqLGbLd&ZPe5UYe5AFD6j56`7i=Hc2T<GFENc7)3_J6vE7;`y3<P5{@MWMa1&`1uc~e7(R;E>}hZe`gOXB#KtkBio(a5rSDV~(fO9%6n>`D$W3Q#mdh7&k;->d0fX16j**Cn*=|oT8@daEb|s^i*H%#)^O99Nn>AAMfu8I|7FGgdRB3@kt!i)+s1DV>1)5Wm&|;xxu1Hzrt5u6D-f1Ok9JcC?_f*Lj*a;qwBKzW#^FqU7ASmcX6kO|-RV&sXnPBssB0mb2S@YeMODUBGN++iSp?qGrb_!7&s~yaSE)^i<8gHo!*L-OU27?L`qZTV+iSw(;9%TDh0-TjeUtQ<0Pl;!M1DRR3V52d&3&AhXX`byHH0Hx%LS?EPgI3H@dC9D;V1sIag&$hTJbZ;|8=X@-&*cCbh<%{2KW;b1lZZc`_bS_OQ-8eZ7DtapCypE@+d)`0VikPgM+NEMZKf<7DBT-OUKAkVyZal|9~o=oK17Cc|E)-2u@kBC8E|9)wU#Gg*U0R@7W|pmVS6Ox5cH{4`#NpW3Twid3mz{kot}OU^=ow6ock5Hw<0makfz@J++m^;zT?_WDFE!G$?ZK%mKMWpub=H2tpcp9UWRHS87H@yJWnpadET&lN%m))<MgJUCwo8aS2u9sh*V;rs%(~t>tbcmqo{K4Z>!*RI*l?${|h8k604{8E^WfY#0}+iR#edQ%0|}tXZ|=I5gV&<o(6TR5$szo*pd?~(cfKgfr?AgzCD{o$R#pjmsXC$VR6+?!dwJVP`8Z0n=u4HJ*-t@*o68~*^#{k(F#+V^!`;OX9@6+l}bhdRP;)~SlAQbWm8bvkXbmoY8!wxtRZj}Lwj&_tbsX&9mlq&ZpYK_@0Dmhil>7J7uXsXZMGLn)Xi~<UL^BY2E*Oyz$GC-ru>pKoyWV&*-ENF7fn8<L`&;r<!%LmCTEA?0mHlxb9|MhR%Lz>cShEp$UNZqT}}8(J*?0+KF-U7pG#bYa4syO9C%TLF4e4%podvzwQY-ZDMPr+=U$*qh9Vm>t0-2Y6k~QTFmQ8Z%xPmORSF5I6Ac$!&?{WyP%#R<Bc}HW;Wdop97`y!IY#P3cG`)J;lX1~kIx+<hOl4Ece$O&E0i#d(-X+Qzh*;nYg&uzM8A+=xfbpc+X7+O64MhoO*S1)?1=QXoi6yg6LNYCv203auUD9WK8Fn(HZBN_O?SH#z-vKcjt%XfPpA^ZXNZ?XJ*J0-qs%1+(wt(jg1;BY4#Av_)9kQ+%cL6zE6y^l@Z)}sHqvO@%egwjy+nCquK^K;mmdB^f?`8=owB;BbTlby9ni{s)#_;*HztaCS<z?n60=IJ>lIX6%EX;0Gq+3O+LRStjsT}}y)Lg>&ThCa6*tG-+8FP7s9SOCehH=6{Dg*SGN2)}s;A-`%cvqqfRU6cS*uni1!_UEc+}fN$0XHIt9+sPv~1Q2BvL|6ZzT<}RC{U=?TQ8T0c1+nPNgQzEI<8C@oq}^Cym(Rb4nEL5GPz(W-C#Qs#Fwqs&&VKo`I@W%1dev(T`Yg5(h*n=-6BhVu?D4iX32ZdxG>fmdPk2Bp<ip#z)qx52+gnZFCI>t)oB}R*>zn4kosU;ksAhB6K$JY|k6KV8@grYSLMxiUeYsQPHx@qmfuSazHiZNQoGEQaXv!Y2>0_j3RT3<I-5fPBgus28@HuYH#2dpC9-%k@!^ny{1+w`qsEut)UaTY%{p?INUQoh5K&Ndk8%5G$`+v+|*!e)up4+ai%fmG&ac|F8Kuo0!8%@%o67Dslp@~k(sLYUJ>b~sK;v#7*8ddO8o-!yi7!8wHvjF8K^>P9&#li<6X<@uerJqJm*uXM0pbEh;jK1)uU2I<l->F+|E`zKtZv~RUW$tW?Kzu@}LAeyI6q?jC#|o>Ol;dx{NZkjt7~DioEDV3=#V~=ZSvR<%0ycx^l)<blUnddo8cou>-G$w91~|?Z!$J#H<j}JXaB%xuT`0WoC1+WX-V|IFwm_Iss)XBXlmWDKX2Y^5B@ACd0?6kU7LMuL$y$=@xhZz3Q*8)ZD4)-$Wu#QEbvHc-)6Co^i);AOJA4GLtc%&LyU`P8|r4jH{E?j+pnw^YuC^@=`SxvS&s#-Q6f=?w2&mR?sxYBgZ=b`{6!6d;oH{V#+2996cj1pc4TLRZbtTT#_4C%!AlXiR79S;FT9G#w&kXJNv}Vv8<5^ap(&n2-Hx&cpyK}(o+V2!5<!BzE4IRpMIh~p$@iG(+83Gw>-;Odf3dUOJO((gwrO0pUX0f2oX!xIPx$By9#|45Zb7l(hBjd%4)5tP~h275JF<JN^E%;Vai$1^{eo0NpAC7a$+Y3Wk|a)MJ!2#j~E`8;`szDos-)_Y#DK?3dJQIA#LYEgl1)^>PpGw&<(Ata3G4nvmo~5x8j7ts=4!okT!-YSaLbnU*+*^LS2=H!Pthtp**B?KQIgUU@~3dil3TLlhiJ*K4>!@O0yAT?9wB4u};#F;|mfap!2aNBMS;Ralo988xa-)^$DVOoZud6Fr9_`d8vk`i?An!OM^(si-}odcSmA{1nF^uyxt~JvdrL!kqDahX|LbN8u&{aH^tBhP0OpWfUB#loBi%kz}?hpE*5TBT7T17{SrKh0B5QB-y*U{ys&xPkPEp`@9<ur(OIA(FHv-<5XZjI2fgFsb()i+U1YZ3B#9yT!e1t^=<9zxB6}qI1}?EEFdkO*^_zc8?Q$;h3QiN=@jlxC=>`-Q89VMKnAhJ<X+z5G>j{*?AZkYdCH!XwZOD`GsnB7dro9i%G!OTCjNti0du}h+_3(28_&sHAg@%*TD7UlEs8fDF5g5z2%H>n<6By$&xk#@OV1Lrup)+j7m<zyB#ly~otusss#^&x0NwiVNStDWYx>$Y}PavZCvA?5lFBK@i4fYJ<FUwD*#;n)fG#0WdJqDp5o4{!!MdE{=LL80xxPxDuAEQt!=Q@-^wZBG6#;cH)0Yt8s$0USG<&OZC(%+*%Cn@QPEW(~ZfnM*gU9UG~1<<T>e<UeN_BBh4lrq-I1wjSx1b1Z>76aozg)7xrC~jssBt;jsH;l-(AYLOYnx>jcNYkZuf@D2*Ez7G;C@E%>dC1{$Uhz`U1@AlF0w6K?Gc`aaLI>A)x24;#2dE<glDB?v5bgGpmVQ*>cT0&BL6;tQ9Axy^$F@ZQjwHR@pb)`O5#xyb7@X9HnFQyxi51u_B~?nl3PkZw_p3*Yq2O5@S&hJE2U>Md12F?CG)Y)m<0|DODtT3X(UR$+6G2ltU}4{71|v_)g{+}GV{v+Ll}ae?9?T7E8MB&;@YgGfZry@n83G@9Uf`Hv0=_S)jx5jsS=<@Yhs#eWA`q34te^$_g|6t+8keJBr(}uVKe`Vqwaw>AtHU=hOv+2sgBIxe(ww|0&5Cv^B`Q#)2^D4$b^BdWB_<e81FrFX{K+~pCKTlK$Z6Kp7YEEJ4#Sf~REQml=-7E|mXz)ApNo^Kbm80-6Ds_m&7LaGLU2UX2#S2EYBoq90pxBOI17PKblz4+D`*#eDinh$MnEnqTS{G#0Yohktt7mszNM~-n%JbAII`82T@a-kmRNN;<seeydU+sH$%o~AAVd^X&G}DJMW$PuaG_|2k{*|jqWBe1SU-%9EM1+HsKrgtt;E<WSDwT*VjaDg!FwQJ(kcnqXiCldC(3roBOKPyM%9IB<_Z^|Pr?9Egs}uEtk_WW_9nn%<I?F*$LcUVmmSNy;I|7oJ-@myIp1oKEYVnw=RK5(HN?m|cf0a!5J_8`W2P-~rc=Tg8$M}t@~SqNtzQGr{RO<Hy!$yuj(-(y5ChKpALm_i8~v7+2uh_(vgk!6D*d2ywitQ<YW_O0KdlbQI9%t}55||0vmydZ!O|kMg$wc<V~SI-mVIyx!}{gJT$E`L5KW40*~MZ9tL1c0PFoA@Zl-z40z;Km$zZb)5!8G!+7j2^r~u4AN(Ex4D)^7&J27${hKV=}12$$e7<VLue7`<RCQpziiW4_u85OV1r#GsT&_UrUss0_t!Nt_zbPLO2-aqef>%&+whrC4x#~QJH)96XkrFqkIixsUP@`%_S1<?-09is|6#4@OABAjl_MD!Ee<TpLa=wiB|a;-)DlH#nGS0$W$!=)AM%h_Ea&&O`+6EH0lVYJA#^7cg&D`?!JmKXtxoHUav{VK+ig2*zZA@4<>G?{l7*)W+rB9AiKvpJ_s+|e;X!&k&M8kahey5MbR{IzE81cIQFOHR`S1x(^SaY;KK7<OwSyS0Ex{K_p!2vSF2iD_E3vPV72S79C{1E(BmbkhVWD`#(&s}*!$fJI^P0a3QehFh8}qnI9<=|Bv>aSU{xnHDKDwK<U(0-!-EDNs;e#fex>MvPWBu3uE?<)OcpN^Nv2D&xbeLfi^%{kE;}QlM>7VWQ|Cm1AiW9)(g{<k*`%$@0YGlHp4xhA3Aw{J2VGjW?69iD;WQrsn1m6T=x)qJ+mO6p;hXVHD*jb};I&eiZzXr$gf~U-DO20zCForI9=y`l!0oEUj|2mXj4gF*BmkJ~1s!SFi9%g}jX@)eb=&(=noqO94|f<w)>OBbZAU5W6|XtMk-;fN~YtLZRNUHUtSojm<JQx^-o|CupcQk(BHF2Ulv!;8kmz73xTIw<cItMLc<I#T1AkTohm_Z58xR*J+!OBOJdho-(R-g(I1ZjZ^BQI)?>TMZ1QaM{9eUbwn-@HBPF?Voa5pwX%$DY8ndNzGgBg!B+v4K}Z!hjpUOW24wMy@bpG=;AgXpMj%xYt5Tv2HNal%d2*|AdR9CfNuEk;9f?yYiy3ImN<bFXa3&7xWu_k7)<7$QL^plgLz$lcizB*;sK9N4uWt;@QSJs1cf4+HDduJ~0L_VskjcF*mT^rXm4s_E`+>Y!{v_gG;skV}Zk-B>^LpgcPP9>Su7(q{aY{lkv*`4~kDQ;P|CmpyfXn&m@Cp*As^1z2W5$z(Q;1AKxr3EvWQnqCMNIOhN8LHVI;c8h^q;Cg<f*O4@fp$7vV6KU9KjY0!>(R(zXGQe*=Y~*cS<rN^npn*f(BwBPMar+(U-U=bW9n%6*^?2cys|-j#EH{degW?R;gX|DtU3SMpsqCI*2sS-pWjTPu7ld{1vK6tT2Hsk<qa{?utO4CjVlN0=3+}v61t8hX*y3N44cscd=@>2hCI!kdQj$5Y9;9M1e!%0I3n{rgyysP3dR6+7^O$T$IQFNOqa1gv?#ZK(~XUZrrLR4IvfX)$Z_?x5!LfgsOg%l4M<@2lc=wI|M4;ql0))D~!u{Ylma1;LzdXdrAZ6WZ+FEE#2v+gG$x5qIOpcppPuYaWTF)`i4Zxpct~!g1>mrz=&13h`_#I#nQV8?23CnJaafL|6B274HSjaAUsxekGlduisL1j)2WRpLa2H5{#4x3-C*_ClGtRUm~38=@<=$%Rsr2|jBRUjB}5+YM^h>SPd&}aeQ9*+^G3Hm`cxzH6_u*S4fmW1K4_17elaDhycE6LbMVxI$ZVC0P_Fn!0-fDY7hv5X6L`JsStIP1@k2K+#gKa{5s-6q!d)su!~rTEpNLZ$rQhLYYhlD9s!sh1G0&>)0W@`|n(RZTQkK?ftJkA+QdPUN2EYubY<A{A0QwH7Fynj*QlcMkJI#>N!*!<bA2Spqz^HZ_sTxlOKdo!b$RV=Gs|c`;r7AK2drx$K3CoFXL5wm6K*n|(gpP@-IwTbdV8pIMA4hAkj)>zxlc2y;!R5kt5Q2xJEnFuc`nVZ}nYPvC^_$CYxx1B12-u!0G9XN}ze$Ulv{{I4qX*wFjmahmTWNc?5|d5jXc{G>Pv4tubXRnHI@vS{Vx%~;;vGc*iYQuM&Jj=t2RaCeAs0F%cy|Oo$~dmZ(>2<Qt;rr{*-zbzKnYhAj^lo{QBXb;MEik4R3fM|kxl?vyGdlDNk?!&ttSY(ra7?U7tuCX03gSluw!KH{an4i)blg{&7AX8dn?0G7+kIzKxtP4%rSr!r<C_Aj=BTHp}`H4%$(3lY8`X)`l=@1WLrXhE|1qmT^;*U0f7*57`_(m{E1HQ#EIq&hBg+?{a&x7@5op}aU!h)?@i8@iROHw`quC8FiyxvIh|`?Dm;7<5IW-@e%q|%b-6&~@JbwsG%bZamGM@`Qke5f?-Yt^#tE??4{`d)$#>f6L~rusgc&zbMAy1Y-W;OiN}}+F0E943HUarUt4VV>t{lq~Xpp#@LX;riyQq*^5wtl3b;Pw3?8Bwsv24>MM-I27c^gFqXLoNfksLWunM*rm1AMwpwS4(&5z!l2URNKtz62!=E{Op)xpT=qn-xMGqgM5~EGR<7bc$%a?@d>9TA^13ij&!IG4}&RVsp_98iuaQI`HX%f(0!2X5|)lh<0k;Mq%tJCB_mZ6W9sj=vvO0k6tQWOk<yDUNNOCR}S2!s3;*iO4L1{q=9Z6noMksG8whsHdkJ*#4*Jn<_)2!NXaOMNxNaJq78T<QbEBKw>er_3J5U11&wN}k3=T&3)-3mf37}VN_i?*{CeUO?WO0NmU{W2Occw3IH_la;dP6bXB~oZ32jhEc7Y0L=?*7R^99p<S|jbCOm9a;^3rNXr37mh>oLafM543lX*15I$h{7PN$ZK35{Vd@#pH-czq+M$XDj2vw9vOIOtL_u^#VAMADB@WE5RET<Q`2iwYtaWXJ>rpW$3#gEtpUb!7KGf-##MM&7guT>mxeWJak8lW*4|R@2n<1r->@In*_ENP~^l|!SRSR{^5N8`o-s8C#>uKoiA}~!pOO;+-ETCaG?R)SMh+JkH^9kfL0~HkpNPDJud`Rt*dfi$)X{l-%BZTgpSn3?-7NpJKC_-Yq{T1R)<W}51BcFgd>t+jh^pSD5(~<7k12?P!2lCm#7VK?QuM_KE-QyuL|OUKxha>RdiXSw?m|9Y?J@pxKQgEe{o|Y6kTCT#PtvuSn~8zKw)Onz54YTYR-yQ*#_4qiIuJOxuW$!Bs`G(7$^>GYe<aL;Bz5<KPDO>DK1WQG*}9;2zIZ81v{r^-f)4O5iU+k!+L?ll&g2^M?IynYE{0ti>ec4&B#!oj<Qvy%x)$PphTo5RTNTe8j;;dzCz}y5S`P^{Oy^5e@RD}@L$Mp$z<_?$#gkIu}&e;@lkQGN*;)Lm5Us+$Wtqo4=@w6;pGukt@B+YsyOCUDeHk@$t9#Lzo$%eNbx0#3BY|BBFED>H&iZ)Agd!;+&;NWrL}s<gjXT=5s^2O@^5m%E?19QX!&L#bd$8Ths%eMwRRtJ5R!Mb3d&nVTSF#BfXK-%5<&IU3NX%O=Fr5p=^uTY1SW{$I~NkvE?OHkFP&x}i;O+$M3W9Njn<VA+{PwvPD@5Rij3sTN*%B#RE7nfsOC|HW}?nhY=@{6wu7LlE!j93(Y`p9m{Xd95>7FU%!(p^!jBZ6)8tH6mx$jfuyK;?r{n(958U1y1;Q1!rt)lQ5i+*P!xl-O>~|QhYDN3HhwUchv$c&tK~G$FP^k`0k#@)15D~|#LKK4|NHsaU6Bp42@LRgEij1!2P%WVw9F9BH&yr!JutujIwd7pULU)QeK?7D@!lJL~RadW~jGzkCntz?S3saev3ZXQW9u`c|+^ZUN2y<TZBvJA+M@4OgSqvb%5-U3|^HgQ&Z>lZkUlAF>wH`s=T~79SJbb_k*6A~zdXj#avlqQh;6u2ew>=7(QmSlidPX%TZdP7dUlxPx;#9j(_a5hXnqF!aC|<ltV5EK3Yb>L0jmvlOI?HYNxl5NxS{NEoL54N1H=U`flpd(?wN*(^wF+?>Jd>`h5v@ij$lZf`7D)hTIgMcdD*7xqRhFOtg2@<QSOyifnN*28KIrZ0(r9+;+M@YA1ts-I-A0n7KKm1WP7_TMALb>X)^+ru*HS`V;|P<~(PNO!Tor0CPm?mAc&Bs!E?4Jdt_m(M77^9Bslg|d&{uT*L8QMgO<J|DQHVx`R)V*B+T_={;&vfk9sEO+Q4RrnxOFkUAlg4@AyjwbDc)a&hCB2{$4e8GMD{C_RMi1T@@WF4kvQ<X#IZ>fPN?cXUSz`+D%N+3v4ao3k9EkRZ;1j|Y4EDGdCr}H@ea)NxVvy86^&9GTx4Z1CfJH-b@ID0><<clz)Ys206WW<vOcod>cFf*<vclUhpvLoAk%5lMnto+z@plwd}j&S^Hn$+v+{%iG*S?e#e6uBukP`sC%SVW@T>hRJbx2Q-SNXOhEF85Z_z4I^GS>w7ZAVDOh%+Nj5SmGTLBibj;3HQ?b`^+$1?jUREJ7>TfA+s$UTRehOFyIZ>bIE_cV@lKq3sv%eKVWnR)n4Z0ct?8*EQSm%Ca;%s#ByM=+2N!=RdUM7aoo|E(d?q8Bkb^y5xxy`eR3r@>Eho1-bw)+ObiJ%utY6taWzz|OK{qCEL5SVzT2zb+3^CcHZuD2e?l9hX6i>-6XR#Oa%3BSGNOXgiocNc_H${mFMA*2?2}9Ze84A;mU}(5N&eB{qx>cT|ZIlZfq(PtC3#1XK^H<MzTG76M$I6ASaqX5wLmVbkbUPYPXQBT_)A$mTgl-jNkfm9Y|Km2-#D2@GsPT(H<K$>`;0YSJ}+-O}nx4RUWzDl3>*{f@)BuPFjNdDdgAkN9<;i<c1oD~3dGcuipy)G`z4*5RH)|E@Y(iKC3R>*NqTDg1MCayEH*?(vy}8lZTMg0)>rY5^$<^;RXK;FYLpix(-H=!2R+LPs3Ce*48HWTpFiD%#`>sY5j-uZfXzG9&|~ooB0Ij_&3Ba{AP6UD^n4cdO-3K=!HP_;QJBU3e|tk2${<)mLsnjsirpZS?I`vq9xhvTy80o-Rx<a%&=R78DuS!o5^PfQd#K<B@#z^)O@^r3daJ7<!dW7Hd9J{iFyVMgpAY+2kw4wh0eiLvH*rh3nsASbm*(6|KFh?1}`C%QaI%VFXJ~^IQw;$1ISE_GW(l)y)ATRC#r{`&>;iZOR-??EJK9cl1CWs?3={F6|4(F0@B_LII}1v2i*tnJQ~>Oiu!J3RGUi(#JV24zUF{!;G3<#P+S#<|Hr?iyI~78)@cl3;mn|&(g;}#C)bjk0!%5Yqk-*xYE<Bjw>vE0al_{_34VS`y`|jQ|C!xs5~R!vS=KzYMl21mQX%;b_fN{FQ2>Z748)ff+C*>sw{sK*YQ&9gjeGzo$e1jQg3=<pc<qpKw2Cd=nUjUiFJ?38Rv&k;L9cXxcw&ULk1oSA5-}jR|eEl<hZgHWpb_~vvBgG;7mrjkcrMf(bc5$4|l|(P|JZM5`V06ZUSM5^f?G_cv7!#Z{8jLC_2DK5>W$Y^&X$c=FHEiKQ#jbIO1pmnK25F2%)TE5<*axjnXGsmT5g0Dbk+v7z3H$xhVmPBmpajH!T>7b3!MhRmo<TYt&Wrajj&U?YyXYk~TVHlB)#6{dnv~n~`)qms-h}aHL64bM2LLa;X(YAgkN8MW3MA7;<;eH91>Xd(cjvN9m`YQSy|dyA<{&w?W*e+1&*3X<?f4X4r`1pyR8BOcQU%&q{+vruxc)i^f&?_`jk?s+R")).decode())
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
    _priv = obs.get("private") or {}
    _invs = list(_priv.get("inventories") or [])  # [0]=农夫, [1..]=雇工，与 units 对齐
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
                elif (crop in ("STRAWBERRY", "TOMATO")
                      and int(t.get("fertilized_until_day", -1)) < day
                      and day <= 27 and (ongoing or age <= maxd) and k < len(_invs)
                      and int((_invs[k] or {}).get("FERTILIZER", 0) or 0) > 0):
                    new = ["FERTILIZE"]
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
