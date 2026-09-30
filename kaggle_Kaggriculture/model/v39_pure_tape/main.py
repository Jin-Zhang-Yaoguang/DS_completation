"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%0>(OOIX0ZiWAfp|J;+CBHIj%YAL(%5I}2#kes9!$58jAh;PgnFaapk<{Ji>|OPdYmvK-1S6jKsLx|pvB)ZNagp`w|2+D)-~af>-~V{@PoMny=;y1KFCV@6^pi*b{`-Ia>wmrb)4PBC<M%)Q<M03d?q9z?`u6qTe*5|M=DXL=UOjsI)-OL?U%h+r#gjL0{`b>Qc0cyh&F!ln@?U#-{o=*;XP$oj_7isxx%%n(k5}*Ce0KB8+y8wI@4Wos`ugY7dp|tCy?#`B_3qbRUSEH=9l}@BJ3n5(xcTYri^reOb9{O8dYt21DL#Mp*VjKk4E_D@JqUIqm0utIa{cnv{oDI*?8P)a^!({N0Su4dJV8A6+t<%ueD~Yi550Q*P9*kY?_@PRcKEUI@!R3OxO#T&&iY~4J4x?;z<K1eD`Tdhxmv8-_s0bi&znRipZj*=KfO9DXZ*Ku&D0t{2oyC7pKuz}FITUwZ|9fqmrXqOFYiokc-ZDQHqSWeZdZ%%6kvGN*$`6+lj?da94N0RP5R)S#Pn(oU#tlD{I+E@r_bAxJ#8cNx;Dgl+KQDFr^g<WqF6-|=lGSDU}^D$WbeMBW;?k6yoyUC3(v~sY1v0-hA2)vJ(o%`U%UIq9+Bea*IX%@Cq-R~(_=dmOMiEKr5=!ZH2d#nuB5d+omYQy#l$Gl8-bw*e{3JXn{ht8ZT=davFD$7c-PhMXE!fiTt9pD+h4A4Up;^E{9oqH@cfJX*{Y9leKoIN^vfqlV0?olb&hy8pMD!zym^Q@Ahd$W3ZstA`6o0ieAMIlQNi@k2_GdeJI9tZAk4~l0*E|tgDK5Bec~+ZLtEMA=Po>O+#&AN{m=}i-R)8n*z80L&XCBc4_i(C)T>lY+vng4RlL+0y+FtQ9}cbM#eDk7)6|g>N6-j}Jwczx@`K2$$Yc4ody#BK#`*IwS2%jK_tAN@>Ez|V?CDy*2n=AEj#<7A3<p_bt_c0XS*ttN2+AxOzb*5%n%@WDDgx)>TXJEz94B!4<sYtY|G68&ke2jAUR(O7Azw!0w@6nTHJ})0jq+1GFrG=gx1AR$SoGlVdU`s%#;g(fW@C0no=$CrQJXpfu$GL)FJsQY^K*ubN@3*pYN;Mj26ZkA7O9_|oU13hhm8739@H0aTo0;^DLJni`zQUFeR|FA6<A}Qj%hr#v9qQ=kP+Q_*1546`9SY6`HIbs;_$NX<jJY*4!~6?-;9!o-8tMmX3YeUjSk50jHkoGbzE3m&dGv!R^wJ*JDo(*b@MWnd_#Y-#L6UF?^r2?X*e@md#YY7x}NhGRz2iM)(SnhC#8pq$RqIJ?m!09gKPTA94NL0<2;fLha8U(mMIz(KfLJl2=8+H!x`1ddRApIPs@P$?fk)QZv<UZ^Pzn&H6b=N{njsbj~#^*`>oq|-pc3p=GD$#AKrTT>h|iFZ?A7}|8_zXmtltF5RQvM6Y{`%T6AXVrH?%3c($K{wi@L%FfLq`s07i{VovE_Jhav>C+9}1nUj)>dYQ?kBuH<ybB9<Y1qLgxBK`y$xNdU3H}71=m{qg(FiI#ktMO2&Lvt!4F;&QOxbSIpiZ*E4(1^-v@gZALjyzq^N3L?o(<?J1GM$<7?;aGp_mmu;?n}G=yPm&=q0<+KA0!cP+?mT1nuYji-Om)0Ip9pzK~tK~h0aPETmo}``iaT<7F<4j1Tnm`GsT^w@U3|)u)iGMl2QoNcL9B7=lLPlqAAFj2i>n`K`YoW{_ATXXV51{AOl|F+m_rnexn2Qp8X(8^d}EvV<*Ft_Kqume)rt^%AokdM;%}hC>20N%5w*B4xH3K{j#M1XwkvypMSbv5wr26qZQaZroPx1QUv*u6>Gq-U~LU@-vmeOnP1uGX$ZXjkfnq}zzhc$G&<EMPxYw#GCqiWz1f90VT!_o>K6G*C(*C3h(Wr@b)?UZVhV;8oJ>qeP-CkjsNTjh7KTL6cRtrUsW)WmbOZu+w1!Zr3sL35o$skF<CGq`xp`;dk3XN!{5nz?`iMRxwHZziST;6>cW=KvQ17*jGKo*<8LIMxmV6_v^Jz}6&RQRT&f1+Rp3i7(^k5wI*(&@I7Rn&<jsf&=NGRsMZ#XsUlr3dXXp~bKO(^tfkbSwj{Q{sc3jRdnPI#q_{V3JYupdM)+_>P*kLy23dMotr$vQ<DVJwUJ5$04atR^gw8k++I1H^-43fuaY-~xQ4<AP?`2ZWgQK}4-7_I60e^tZJVByTM)vK%IdbMUZv3^1o^Ib*Lqk745ftd&$=K$xy|5rEOZV`i}gkdmz4UffjVa50<SniLqda9WE_0cT}HZk)MHg7es1-;hsNMQ@_zMA4SkzUCH^-spsp3nKW%jQOj6VgTDjA;z$zoXu_%p#YCV{U+vA(%fb(&G}_fo9URLV9^at8eixMcDyVc#rfPjzfDavmX|}&gQIh9(|JSo;3y8X0=Dd&ZuX<YuU7kdtm|q)Gt|Lu8X+sXb1`shH2uI4>}mG=MNH;YBwXT<i=-$G_)Nt$RKu6PzjesAgrV-A&4auUpBTSztSOgT4$e9c{k~~t!_K7Ers0WWfl)3DPKx<~L}x?^;2SL@#tVJg7Z)-l4Ebu*-49Na+~odmM%s6hnivq87{x^S-+W-EoZxl~g*YPWD@<JoWX`H9lL=o$$GC0ZN2<msi%jZigsozCUR$Nj+jPpku98){gh*qc?Hd05H(G4TRcZ3`tA1wsKL3sVi6nC8!Z*wKm?FU~a%x$oC-nX5Np8xSEg!|{Z2j^1i@#DLxf)CbluxrFK3ebX=t6+;OQi>UmCqW?7eNTsmn(7Dod_dOZX_SH%*X5J&j`_8YP{fCwC4=kZ<a||kg(-NqV+Ot#7im2EMwUAg=U~c3O6}*kk?F-sB^@Uz8eUs1&_(QL{;OfOK52=br|9FA}dx@T-lhTJN&~^U984LFcX$IK}tf>0uxNhZW!GWq;(N(CEAm4<3-xBt(x?^QGuwNIW(&syCuSv_)BEp{Qc7QcpKpu;=uiaND5kW8(_iY;do~ol<~a~9(U{*=X+T11b5jMpj)n(lp2@w>$WTj<Z0Dc!k$-cYj_AjXcmPoBIyf=;qL8=LJSrs|D+xPz~I(*MxQM=#!z7-@(WcMnWqWj1oi&ioc6Y=1&G;3%}HYqo8WxqnLiURwOr0$XP-5}88XJcSQn(Sn=ehx>9gw<J443KVMEzfnvBj8#-0>fWZXre%uHbiz>o!_DHZGoED&gkd~Yz3MXkf;kJb2>bAN)~HI*XA!rY?`yCR;iRawpX%1o4cb{e_x^G000nsb(@2AIu(g*rx}*vL?y47=znx!^P>d-fDk<;6yEg0r=O$b*gHB&F&3*bWO8DM!J^NBC90&rx7H0u?a|0+k%SWM^tfS?r}vivw7aWR1;LUGbhN`3mdlfw&PkyO}Xm(A>x^fB=U@`!WU7UDfQ5Ot9KgV1O;(m0Z;I##K@|ogB6Z+ejV7W5%WcmT{epqm5iNG~y63VkInbezl;pR6^_*Z;z9Yt}^fBt!bNeOBot-yAb?>rQMqbUhOG1UlJ;_hQ7LRkQm`b3seIv{LmszU&PK^4cy;(E)!@V)`7zQ-48~7QIyq=|AEI<^}5tNgSa^yqer6?mp3&K4#KJttKb7aDi~94vr*wd;iKsugZQO{@9wU*exNjs>kw^}`)@@C`;^{QJ_C*{Y<5MHu&YJ(Ukm;mH)xon83fm6seO)uNsboIT=00===Ah+s9&Sg=G-4c?oK3T7}C^>pF2!ckv7ZjkO9C-nl#sGvLp<SNrH1(BC;E|e3q;hgV{5V&IX)3PYxOeu)Z5beWOUnIUZirvCqM?o12;RBaIlU{x@RcDo<JEC(6G2%ZkTgPU;Z6d(u$BJzlVOX-k_zaYfSv7g4GyD|DU)^?nf*YM2<&6Dx79U2uVFEz&MH8zI<LAAy&zkHbN@Y9-T>8ch1=9tt!y1yB#NY7CoDKdcUNmmrcbrAetX=nTFQ5r+zQ(#seQ5pb}?z1w}X4Vi_btCqDp0GwtGfvXtq2ao5=f=*$_T%}{T1MRf(uz(;PMYzb;D77OvWY*vC5Wh$!t_=3JL+h3pAch0zO}EOx`XrC6K0e&@F(+D*la;&`44RxCh9?XYKg{t}L_NAhBX|&zXIO$Bkiy^9jIY$i3OC1xd3pGAiL4OLMb_7a1oXiD>@P6QG7u!;r(IjhAnx+P7g&>F$cD};j@80~E~Rmp3n<%*p~6&JF|NK^r93ktP_IzN#mbCIznX)bxLPSy2qh+ngksUPE7}7A7sx|I5jGU?;w!=KN*c%M3FO~jvmp6yS_|w%pWr}T3s;Hv0<p1)y0Z#)P_1o}-nP>hUN;s_k0I7gN$st+3!)J#+z`j8jXfaybtj<;t#$aV4j7+NC5ErAdvW-o;V5&Bfjp-etRV0Ox`T~!>ZjSXe#^8Q2P@7pZSdoIjeF#XlzrnS>r|Vpv^=nPa7`V&I*L+lzq9{i^*dsOO^(_(clPq}IBI^Ao|u>weKxN#6It3lY6GQ=GINLdwMH#mo3o<p5#Us=7v_0qfG#nhCs#gOEmRsSTgK8^&-0mnLc=r}&=Bsbr|KJPQ$>&fBPmt0RxM2m%z|`rw%e&gkLpHK?umC;H)|CVDWj$*Nkc8wni@<yPnrrcrQJ^DCe1W|(&Hhrp&I^4Ben>g5=EQhgiGseC5lm{iejHqJ*K(*OwK?RE9EscQ}iPQPU?Ut1s$8KK`c=SQPBgeZcmWjhM0^>Lh^AdZhW+R^&xcwp^duTkQ`TZ0~MGu7Q*CRZ&2=4xCosMJlpAMG-^hNJrYy5mX#hZhF%6jkd`9{R5Om0iIFFzlPH}=E(*r-#y!dO8ba(u(+i5gILOqDlzkjIUo&#KNc>Rzy{1?y`qn6{*3b!Ewkh0s9PVvDg&Sbedk8%5G$`-a+|*!e)uyA-a;7onG&ac|F8Kuo0!8%@%o67Dslp@~k(sJCUlHl0ooj>cGvY)?5>3Vey1Ao>%W8LO5i?Mg)I8)$LdLu0)R(!sB0J|(sYH1a=!kJC*g*GqKrRk5%<XKo0~8e7T;;KgV7AqerWNg6MGRx1ABB{Zr^I<DVwv3cZqnH6)D$3yA?EFfQ7u)Q4^rT&<oex)Wr22Hv||Te4Q-Xpo!gz2D2Q31qIs?&ICC*ZEjCiJ+q>I9ECyFeUCG51ly@0nb9qsTSvQpj$Lus2K2C+qA;i2Q$X8ppzys)2U%t|E4@Lhb5^;)RlXkn~I(+nuJB9=Dt^u7-=Ni*ms}2N6M(Jd=Ba~ergae#S9eJr53)wUyn(l5CZeP+0a>Ma%;8I5&Ax5D+nLYryTQOym1&*GP7to1-g-WNlt0DSUl(L6;BjKn<JC`{DUU}7GEcuh{>=QS~vPLGv)EGh#sG)#yB0rGmDFeXZ505ZkCnJteKT)4h2V1JygGl^ao@J~(yv<~M*x`LezbA!1mSq+ZB9^Ri<Y6jy75Xe7v{5^y73y2n)mm4fz_X(ugw$r0+VU{Ml(V4gSK-@|-sV?R#ZC_Dkal5;Sds`IF+48C^9fjbOm7RZWyGl}6qj_Aw4DnPmX)EZD>auxH{4x?15pH?1+gc%lSy@a)7*JNNE<^HEV-QPukv^{p{`29U~EI+P##jcAD9JvFquvskEIeDW^r7q`k>8tD9uKUu}hEG#X3n#j*m!;fY!&Fj4UYN!~t_UZbVp!b=6XUR0cCOLjJr|L(@grlS0uTQu5V-Sz~)gVub|haf7_xCQ-7^;E0h3nl@?&w^0l+@Rv4jieV9&mRDf`SEa1G{q9h}-PCF>7A{y?f76kE37$lNv()`>5!oXaY#uk{N-oShyclS77O2Qe6kRIBv9I(&^SD?}$Fyh{ne7)zVhFzSmkBKT{vVIX9;v>8ODqbE2dRGd{QGoY&NW`aX~H|+XB!~hfXX6c$K3?;`rAX+kaGKa3Z*cJ+7Unr|09Do^hx+s=rB;%-urHv(*++Rcz)lX+sk#`|J(q6AKGq(g_F@Jx3kZvQ+_`Y7|Ykn<x}qy7~?a!NUsrKf705aGi=3}3&2su!_JhgGfWA_=I#z@v{A=dBVq2^SbiN(z_{icdy^KL#{~sb`EfRkzpOu%8na$|(^$!>^caMKYyzi^6p0Ud1~G5u;|hLsevCq`ocmA;)&3eO8Sg?`1`xSk9+MC%l|KSlN`H?6ous5E+7b2y3iNtEbG_b_6+pAj{gI?7*|#h)Qp#8-Hv|>D6I_*5SPYB<4X#vYp}3jlkQ80i-Y}xQ1@RhL(R8S(gxtE+N|3I{u4P&3gpy)5nTH%6=M^snUGTo+EdUaOKT`u_B6M(#cU!s+dw@D3AbINt2hnanY3WB5ez%m!5OnE*$3aGqeQaA4;7HQT4GIwq6ETj+H^E7*l329c+I=Hc-oA=9@lRKx6PO{@ju>OalQ`Nlf*m`ssmTb0T2h%w!qFPVms6<ZP4&fnOqZMplG22PeVuI=c~UOq4CVQX(}Sx-LUHwAzO9xKt7Gx~dPC8TTTm@S*dxyh%=sl?`;zI%@(j?$-6nH?_X))VqArpRw6MR?4Sm|;at!R0D$(ml*I}ib_Ic9k=*`QL^1}3>0lL03CvQo!qM1sG2ozaDg;zwqepl3p3BJ>SYJ3xavW|-h135kNFlXwc!(|kO;YlLu!=@5Cb{(4qWjple;*=^~Hg|{z6@Jj>P8DY%7$Rx}MYdEm7bI{1a<>eWg`g)oZ>ysfq>DZgilG!E92a#hrJl$Dp_XV?65LbYQkO&>SfrdbvbC075T)CdSXDV?_Ps{+@<61L4a>Vgh$yC-@jpZqIo#NU%S1bb^tgBw)vtiT`eA&u)72@7THOTMN{p>?;YnN}*0FmTyax&<cO`)*9WwL&iLw=Wgu)uusCqCRxxmF|lQ2LOVJtxcE8Zx2YZIWcapCmaV|5sw%Z=q#@SBC4o?l&;oNYB|mS`)-^B#)C8fs*nyIuV@Xr!&hF_RWK&ne-H4WBgncvaiW)^CC5?gCy*-u)aS$G-|Uhymx_kMkb6jc!Xz6s6K5S#+Wjb$-w{TMRt_H9t%CpH_cl9IkWc2jff0SrLJyu+t*6g#!7~nBpN=%RV@UVg31GF3L0rh$h9h>{795*K&F%r;UYn_tJdG@<NqW$zZb)5!7rkS`v4^Q305LlnTU7)$h;LJ27${hKV=}12*O|7&jz@Y`;E7CQpzih7-4984a(^rZ;Mn&_UrEss0Vd!L`)jbc+c|w>faq!oV@dw?(tY8i#$;(@8R;d4+U06>SajJlO5~(MBFOhbpWPE1W8Sa2hWYr>~(|1~V-KS5bRv-QbthVZ{_G;n5rZs~}n)T@`Y3?EXCgtwM1_i;OF8T{Me=#x2T*5uL~xGO5w8q9-XlEHfH%RrIlvxpL7SCNo9kK1OSH%mWkGaU5XWD;67#OPxqvq_#8uTHkg;JkZD`f$0F>OM*Lb^*SCHb{8VMi-5`U%6F0wk&ciNb8FSc9<?K11#px$IOR2?n<f}oIaRA%n4qHotpAD+i1MCnxTT30#q?;K4%G0evq9%+Xpt{dixa6KpciD40`g=j9thlIcxW}=`cqX|POY?59-~`486RF1mR7jeZ#xJtMb#G7Ac|H|IdFEsqflmxgnG06Se|8EGJHw95S59BA6F@&@n#bC3vH9c)Z9E4VmO0Jl<+WxB66S!i=x(~AB-xjBTsb3F}-A_@N&Dpw$>pWd4o*0s`rn_btMHd;><q3EX+Eu@HT~Vjrh|J8y&MMq8dv<PBi7n&QBvahWZmpIYy%M41IuK6-hs#-LN$Tc|eW2GR3)d@4KgHXg86T>of*eV#=^oTicq%MoqD-vUc*tipdQ_xhQl})+$(<t~+)>k8u352Fj?)6)s|~HcrKkYX24ND%$De3|ZTUtYd9~s&TqR)>NtltCc@&Gt5xw_N9+O9lZ*T3|^_YE+n6nDi$Yt5T4$+9r$@Fqnk%n#j4CE!wj&YdY-nboSqdAM{=Ojl0~8h%9;d{SqY+|Qq06*z0A~uD;G#2$XC->Hk4WRe>%RJhzi_J_WIht9KUWrZ1bIQOVKo&$Y)MWgiP+0uZ&m<tt7;nc@5;v@+T455+|S&b?YQgoUtR9_CPNr=YBUa8>g}ZbB0bs`^fnz`j7dP3W%GZ=&oRFs)+3f`Z=3;xxJL;P>HJOGL?v|S(W#qzf(mCPu(=;XGA)aWwxcE2cjK@UA<X;1+FOa#NIkOm5>oyz;qNr$S@G1%@f7wORNw&RtyFS9g0!>xPZ3C$rwVZY1|^e)2=m@47J#ztEOQc9Gc#q=ht^_R5Z$4B7MXL6YM22nw7^>5t!37T+At;mD|@Oa;9y1P{Vjsn>=*^s&-Rwo2mi`(uN%B7a5$WD@Ys`HDcXst|!ox2*%R35Vu(<(FP!SUZMaocl`p}4r-}!sme&Tunb%uyRll{vNCZIs`gDrlC^3c%mbh7P?>m*CiOmSFfRA39X_c#KZh0X84aA1fj61-QK#z#D#g-@WL>R0p80~KFg`k3hLpyj2C>rjzS!J<#FpF$e%~fy>4gAxp*tU*IsBFXt$4BqhC*oz9;>=MT>%!w@siHzR74aZ)Vz9sDsIJWApNy;GTEOcn^$B!68^GHKzI7$y*0UqA&>VjViCEIjLv%AH&&raRxDMtj2hM2^9=a3oEPq5mQr~s8lvaOrngMCT|`h-+{<65)KdYhvx~rWW%n4dyNrRkd3h0&2pBOs%Pox|BHk3wKm;3&O6u^MvM}rrMVx-Yl>o+JM4Cb*d$_4Qp><?xc^o@#a53?8XZr}Z1A)pr$iNW~QZNDipxJ38l%AwVdgd`LFhYH5r;#d|R2b5_riL8nisXnu+*qrk4Pft1KHcpACyE2nxERG4yH^mzC5qIL$s^DWyQq5{twr@AVgXHpqDO^!3*SK~9*(xqieL0VGd5;gR+mg~ir;c~D-Ha4KUWMqm}q~I7Bx7tVAn?fx<4CzOt7TV)@CL8m`JoVDlk8MU$fC&(XHKN4<d+>;`E4j6aliKxNv!*UmYCiAS4^PupvQqBLq>#aW!(R(VA;b3NTAy>e7CtTv0fV>(z!b`AiVi{Dr7Q@Lw7uj$-{<e+>33b5x{^VB~xkBkAp@y7fhr@9AR=<28`ZD%MxbP~tO-<$fhzt71y>vczF+5YjgcLh@I_ZAjaJoBdWb<R&K(vRHXQEULxWSqW%%fb=V42@dQ|ufGG$1`KN~9IS4k2$IJ3F{OE>A+Jr&DT(HMBE;4&m<TOy*3&14nmGy=T0~sV_=n#%>r-9E40)6is3A*BamAy@QkYaqFT9B=p$QTo7wqtnldrVXCf#I{iEZ3~>D=92vda*DRvLxv>k%V3?Fq=LSxqg&apho{fLp}H38Jv}F0_WNSdhyQH4%3run(7h$J(0?GRbgBnpY)MfNb}A4ap=E^`^8^HiD+BFUvQR79q2d3-$QT)}<g+{*oYDlVO%z0$HJ*F)UP{%YxEM%vXr6@ZNMq{}6grAOe~F0dqe<WDXb2ps~?a)A~M%PH<%fE34d+4dFyhj3|sf<(ycm1ovO(mJ*_J-O3#*@JnMKrC_Ng;F?4{{pj3KH%^kdEk|xFGcjtFZLYYS_KePpNs82kVq&!Wl&bW4ALk70L=kx-F_K@8Vd_f5kN`t|30Skb?PFU?<r-N}eWJDWY@^g@4t1hf`@+dDE1Hf@n)njgJVy|WOIU+Cc?*;|%XT=~m<vqvPL1qAd7m{*B(Ec8a7nOBvG`#8PNX`UhAZQ2iX7!YnY5jlnT?3KxFG2#TY$}VWanMRMO&e%QkW}&{@#TcKR+;|7E6L(DM&DyifJ`1&(F^IUd7ONLHaC#7lME3jlO+Es@o?8sniE%ta<4656u>3b$(V&eNGcqtT2gBEufN#v4Z0fS^WL^{`pt$f1Mz!yLUcDv;L8rT4|#{tZ<<_*r)M;o{Y!BAsnnq5+enqG<jb2sQN19_>e`{LBE$W--rOI%f%zARd=*uAJTGjpRDMXrXTWX1Z76#v>FY`tB6o7Y%i>sIiVbMkT201;zHYaW)+wY>T*KW6Rp4K?GPp!d$NB$PW&L#jg(6mySPdKLq8sH8uB-^=n$)AMek&TCX>Xc-K{PLQiB~TBm-)2wh#r+SvSZKi*pgpUd8>vdX(VPwhBV=3W2_Yn~VXwh;3YILG{3-oKCH#6jxC-FO+31GTcSos`5uSlZMbfGLtHnCl-yEU!-3l4O6JjX=eWN8~{<tMwnh+$p6U9=|t<foS|6fif9t32uT+>_cg0sByE++2grljBXPzi!6_5u&xkjTIY-JJpmTo-Ez2*N63sV!jbb+JTHnz)H&jN4fS;K;ZJ*qwLQXwoLVb`3i1?Mse>aIym#cm(bP2O?t}cgb&(^xT$6)X@@1P#S!yc~!#1?V5kf{*hTC!&WB>pNB%OEY2ra}|jCQ<Z-0hnfq+v+FSm!&^2FAdhyj*M;1L`w)UjaJuxZkm$!Go?*Cij3sTO4X^SRK^Z`ptMC*U5Tnfu^gf<)eeFVEy>2oP{S?gKI$w*B{Exxyn^EqI1Z444=0^`I+EZ1!0pYvXs$vu6?{toknu+zT1dWMzj16;bK70~w~LU^);83F=DRMNG6tF=t&X=KBGy)w69yZOib!}RE@BPfTXf?I837$bo`h|1$n2EsN-mAU1D%FrB?pKE-KjnV3s`lxhQ2LT-GGTYf+kRF2X)TUAIfi3sFSJouwsgKPu0LcZ09v^4>dn?J=9Xroi%=o^h9W}O35EsRrsk;F7)k)pOyf#yKLo?c=!;rud`=7^(4_Q=jnNiz=v?bZhK@YWmK7LdYfuaQLMbOzAOg01WUTZB0fxaEep6VHi#byPW7U|=v$-sE?yY84JdahElGgF4OGxRjaw#<lmSW)RQTGec%@o4cNpN3uB;KQMo7iG2lsX)0dnQ3{{5@yv*1)&iUKGj<8)!cPt<r&CD-_%x62{LO870}BwI$^5Rv5;yK9gam7v+$Sz7~<j3YZT1J6}06q*?HAQeUnF4u^<S?dI#aIxT|#$yaVp)^lhOE|yx>allzAqrO=OB5zhAy43ShdrWXxt>|*PzOQKl#40kRkj8Zx~TZqN~kUiQ|vYo(I#4FG}dZe%IMI-avQXh3JvJpZw$u!o^az-Pv<h-)2?pb8OAOE|0cE}i=-rqAw#PPcQsMR<y@8)ufUPEW*6?Ap>bY=ajQ0r1DrhEb@KZL><@}8_>o*e0l1YfWi4H?EZ(eG<ZLi4hpw2-K*z(XjhJ9Xz@jpvd=CWe=c|w?=AMZS&;aqH9rOM~etd_}e4sw=fnV+4ZTMxZb@PY68a|QKNr`ji4(N({|3yM5(wlIbjHp={HKru50<dBoO~G2)*SV38W!BtRhe~!^yuq!=um<LS)}f*&YQy<GjUye92!rx+BQbX7*FBB5`Xj6d-cLniGnq8q$2G}b03i$p)np^eMF{+F4KfzJh|!@RS4!Ir$+(?JKIv_arilI9yhOt=D07EGeoY?OSv#31Wj!m_Z20Kc<sr%e?~VpaYQM_HWzce{%v0*T3gu-@Gnd`k!ThB0`@8;5z60?-9>(iff*{%`zE*@rrAZyJV05^nNtC!ayzlq~<my2{Rew5eFI-z7z|~`FVV>Dc-K%g^8tuu+plf_S3Mdt&I>*R6y2AM?HlnOPY#N=wzz(PjmXsxFwfsy?8ilVDt*%EP_vU1>g1gjjGOK%FBEXYpJ+}6UU-#K;_izGms!AJ)Uhta1DyZd1q+5r33ca4{XeEv^TCS5r@Im39laq7Omc2yXw$osEjk2s=PHF+I2<=uSqTrRN+=_)1O>`f>-mUn<d-q#_&lp)hAuFffGtnmNMjfgt{Y#9LlOY)>?L1ozb966{i_<4Z>jFM-yBGAUkj|u$08=8i>!zKP(jmS|VdfEiG*7!<tEbOOT@7*P8NLM8?y0uXb4Z*{Dg#yBD8|F`@#n*kW&9jCa<B!fJTH!TO=XXwVi>7uo@a?k&}cj=1#Kv~V&N3nhI_uvzL>pLb6#2kiQ|@we>&?^;d~aDhFLseu1!P!s@eO97(Sk^byibM`{+g!J3p=3&^pkEDuE@?OZ#f43$2l!Pyj7(h?>r;n6WZF`;$VQVuG(??c-DvN4kO{k?Y$qm~}lhf-PckSDt(!%@k^(c~IaK`VfSe&tcW0$?%?aw0F0-OwlXzDu}*-?$E3Hbj8?xF3^cE^Fh&|9GG{>EDmNg&U*n_Cm%dJgo16C&%Nmt0#4=AG1boBgjc*wH^Ig@N~ethkJOu<7^ucd3dj=2209UVpjNm?sEpGzsPN_5a$J6sd?5o51yiZChpPih6gj-BRhgXYXj?e>QE(=sUdVi7VCZVn`G-4dQ7Eav5s5!msV{*tMD`p6H$18DZf|~`{wUgwMj8<Vk%Xq|H9n8cnV(UMX$A&x#L)z@%_uw~gt3ZA2t`>oN}ubv1_z@x=P?F4!E;jz6lub~*?{iyA?AcmMysIAu9^^w@E{nO+B!=xPmD$fN^;ek68^)r<YpL1{<Bgh;Wd+1=B6s=<kA_8s8u%^i#|cKF_dgFEIHdROjE&4@jOaD-HV#1yxNuc9r_63zQgV!h);_xAaApbpbdJtTFErob^NSSto_cg;eJ@DjQv}meYSh^?A3nu{=eOuuWo+4dUX@LITZ2CANcY5#m!H_d)ME8AH4GbkKey#tmC-wZ~hPEKhC`")).decode())
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
