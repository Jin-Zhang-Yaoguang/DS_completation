"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%0>(OOG8#a)tkj!1XNDBqdSaQDj>phEfY;)52IFgaJH;0b{%vduRB+n`HOBw<_yIeCK3UQy6>2%f64wM?_@Ai4&2({`aGQ{qx`c`j@{w`iC!mef0D5w{IW4|HBuL{_W5I@h|`R@lPNB^VdKB?ce|MUmySX>!a`9{pq)#-`u=>_u}@^hqr$D;rjW<7gtZ-zyF^<e6jkmpKjjV{?Py0+w0e_mp}9D!w2r3@%H-q<?@|xHt+m+{rcvokB@%*>8&4Ly}5oAz54iL&wqOL<MU5LcyaT~hkqW6ci#SRef{&N_cl{}d-HCb;)g|i_2Q53em?!?ryo46>ta!Uee}!q+uQrM*WXyL(&nL;Pv4Dfc>LlC@YwI(y?Xufw+|n>efM!q?8n~i$?(|W$I8bqhxhvVi)(k*r(v&Fdi4X&BVRl>W-0`imv#C6xIyr|&C=m>KTQ0m+lvy^e;fCV_V~1*QnKU|&SU!J`R(<a?aNQw29N#6k19PpZ1Ee5XPjksR*LTgV0hF;5!)43qU-H&A-vvdst?|+81Lrr#bkjmZ(B-p{=B`iXEU<h*NNpkn_^nU&0}}1BJ84C&haZ#3#&E{R`%{IG~0~_pm*_*l@-tG*VEFEnHkFEl&9yRtJv?|{bTp6;^NobRWwhEd=)p3otaqsyW=Z*K<Ck{zuWnemU+7D{>Bx9QA%$_488c{^Z~pW=jm<p*VGw%`H9oJu6)0^dHwqO#qDqZc>U(~)$3RPyfucGU(}yXeT3`h+x@G4`RoXcZ>W{J1U!pRe~4h-pMnk%S&6_(Mjeau4<xJ(;<k?}rYD{7aRs){v9%f^%<3({%U9nwW+j?!`y3JB?6A=1pIvO+15aS_q&pGcXMmNpDK`43864rwTz;)LYsZbcvK>dvA+@INp?d5QeT2CE{~Owr6Z3~Jp0<7roIoS)_C&fomK&s;iawN|_Ab=V`p3^{uHxij=VRv4rjOVEvL|c(CTRT1^vn8v&}fh~=48=NzFO{AOHAgF@!M;DtmMz*Z^?q|;alsX(Q-L~^DqDK{LMejMlecB<|AHv_0L0o7>Qp3UDKd}3UQ7ReiaUkXOgyUmrW`*y*Rv{o)51vo1;9nF*##8niB#;MqT2s)*8bv%anoV=L`vzVC45=Ne_rIorlGW=w~<1)sxjjM)_18)K~9a4{91xa$Zf?PxWKRo?Zt(0j+53@5o`yXyQUY@PXcA`rX+&g~Q8vhYqK*I_!=D^tO-)SmM%9Y@K|8r>VoRJkQm^;5sQ<S}u8kdRC)ZZ%?A_q{Tr9IoHL@b~h$us>`cv*4sN)qA*R)%$BIstCg<jb__>7WKYscdTvjmheG60cyM<hgXzId`pP;`+_5lM&QrDSDBq(*W<s6P4-fqwa4?rYyz-|{NK*K?WJ}MRaj|V{yWBt9vW@);t0*D$D_wVW>5oq??$(F>YW3uCeQF<e`Ob$WdUJET(%sWrZ*Si`|K+>uH*fxQ9`a%MVeaWFnC~=V58QVh*TcQlnaTRo0%yc_!)-`;kc)XImyz9ln_Gkiu|K^(9Pu8cg2RL6;CqQF7^oJ0<@u?|B5}5jLq)M<dLKN5fTY{zdf5|Ob8&LC<6(h75C>`p!~13267rV4rIBdKxC-l|)Ea-k<U0U8f62oU&&Jy61R#V~zKs|7s2^7Q7XyaUr~hhrQpx%;0YyZtCE=$%I8A!Yg%_}MtSyGV^uaTa@@YTI9d2U|l`0RpTAQ^Kd64Im582{>=MJ>R^v?ZZrAE6A*OY5$*%x%ntks8K*1(>%0UjPvA!^H~;l4bmh_8lq_N*4aR4f!Mj|MM{pI?o~+GB$M7bjKq{Q2UF#YRdeWJ2p8l8`f-CR<=`VFxryex$X#RCys-3igirqpl@qVt>_)mL8zWZg|_^@9<@o^SeO%>)BDahT-zGi8WVG0qA_1lSma9h0|-<{4EBU+x+oC$}@btdCnPY#AC;G8bg=TD#7TG=-$^<pFQRnZsxQwS^cb@7_*XIbvq-^AdU>}>iN#+;Q7URT;iyH1REaq#1N9Y6DmiZ`5qaZbLQpd=A$fLeL2cb>6cck(!htt2p3V=Vnj1VHd~uB#N4O1Kb*z)g4TBrSUiKGX^0apM}>NI5&Zgdp(zQ5u9AOReP#A_ajc%T=OL!i@Vg1h&_mNn&)!QY=WZSL@&u|LqXxP@qtq&EA6&1!pI>o%8;Ig6@h3Izh6Fod+enbB_7xY=+qS`I%wih@?U#5#c2c0w0xYb84W-KM#Lo6yugLZ(=4>rE3M#JFCPxfVo<^IP!_*34c3i+u$vbc+=Tn9{6QEdU8w|x^ORK+4j8eIJY6s;E<Uq}wk_tl?-l39{ra0x3pAx3e)N+)P&cK=ji8(k#x~UM)H(Rt`Q&ndX>?de|&_QrqU5Djl7ru4-NtL`jbANzuIk~ZZ`L^8g%c!b-w2NyRll)LAts(H(#t&wm>+bEtfC{_wgzQ#T;TVNG;`UTCvjNpO(!Y0Di~G$3N+x9cj4qutF@nC)#wM+_epb_w!yiD<n`803;>=p~@xYEA=|~f7W#tZ+9&Y*Vpi_uIM*{foFt~vuSBiLvXq`ngvkdHJh2;R({QvU1yJr;f+aU+1#=K$&TR~ZuKbhSm7<j8o0%XzY%_Hiw8fvRC1ag~UM1E3{bgl?-(sViHeAS7jHl$parpjjLT5&mFM<Vq143f115n1k-znJER!Kx@&HT3-F8Lvv3W)(_`I-oFnWC)(u5g}j@eGb^RM*wwBm!6o6ZaO%sF$CwlnJbrsSlt2bfXW;hlPZE`<N9Gc#))w`1@7yiHv9m1zBow7O@2_C=lYc^Pj-^~J_#>-DJ4m%haj{<W}KqSw!sF^srJQxeD(T|AO8J%7@3OV@Sqk)=;G(`jJ!z1{kN{#A}^52v7x+n+_&#EjpC_G7yEq@o0QO=g+D97^%6+ZrIzWTp$+<JVTrmxDamPYM#`gn+F|2L7B)#_Nk`M4%0Y!^QH7g8RZeoT$%RrYqSnR#45EFROJPZ=Ifv*eu}h$512Vn55i$Go2s~~+gSvhQf20OTv<Z%94qN+T%VZOJJa8QdO08|BAL@w@sJc^1xgmO2gX&U@$I5kAk69k?%r#H(FqT*8PQsA1Z^CQ=Yx|}93yF8m0a2X0d4CiKqj{(_*=|0g(k&9C15!w^+k6hwf_gQvPW^V77;jj(!`o7L*C$|Kvs!}wW;wW>`{oQ9(QghZk{u%#gM!inHy355V&tgCc0!_FzPb6?+l!|1xO)4ubsW44nIF7N;__-TzdwR2TqV(09K@9qRfyjN@&%$KPfbPB?kgoEE#u;Esm-7F@*o^ml@DsnA_8*F$~}9=H7I(RXnoY6Z9Hi)#ALmt0(b-fLh<Cuwv8=JHJI;lK?E0V4aL^W(Bk0z=$SIQeAeZ5jzvHq{RwBLC=xe(NT9#&4RI#x5!{ruJ_B^X3Cj&v8_B&Td2SM#^Gj-zxqKOYSZq%|d|`+xai}PqZ3=&WUFTTSay|PC_7;b{fYM;O{d(}l3d<(~wnU`feU&5xV^B(H2SLBrAI*=*z{Z*(bfhk+6<925Nr0YTxr7@D1XraY>daIVniwS^4bnt0lpJ<fR{1`wmo9M5_&kOBpn%UO^jlI6yjlb;x&e(O2<6<7_ZURo4@@&q6sVM-Ltn*LpY6gPVw+&_J&r^W)T;y9Wc9D`2$Dj`puy?Aik1EB$Y!kNl=h%0rs9c-E;^`fwofwgU^gfPmhM;cn;`ZDyc3KPUs81EbffbZU7nhB7IGlDIAR?yf8#5_Hb`%{?hdO5S$(7$nLdL>NS~}f`1OWkhpa8aF(z6TojF*aZq(j#yrA%-7^wWL;xO=~A`8OTVu;DcNQ(<&1y9z9edWq-H<Kru&Zl^=9({3#0FAxs9kg5*sZQhcdiLJk;pKW&6$MmJM&`764P@A>4kQo}V`0piVUax;oC2Il^&7=E<q>yT10SJwrC^@z+tg(gljBm-^%@yboXmPot3RZc+a4DQZ$c-|Lv!a@fz+ZG+wZfY$;$(3%&voWL0hit=Zro#<vi5am7XG^9Wkv<kF;;#0W+`fWj9?_#aN$i@mtX32){4BX7)g0w9ZORsreAbto+boGJQV0pG_r&DZNw^ccFT&rvPhSXRkceGDBfOpv+ZRGs=J`Ig8CagGiQ66sTcxsfJ;>bm>T6oONhRSfuFQY3_@gmQcj^3mnqKnNHfPuABY#K7zAHu<bu;w`v`0Yz_kiyKrQLb9;zvT(v!jX4gA%wD?gwhp@uUWouV{t<PcK)8nmiC`@jXDvy&fyX+iWF_%5s{=^{*HFMBBe%M4idAYY>2`d4^4k?+}rXvwVF(bJ=Pt1$A@ZptbuDqqNJsXH&vad4*r$*yQpR59jz_dhwvcOX3ut<s~fAIS6QKmLTbvIJFTyb6z@bExqOMObJr}kUG!8P>{A<U6eelN0VX+KLMcSYx>OTL)jh=k-7w9J%P3Gy7YdN_uxmnY7U@~J72YT{@d#~G7Sr}PB$0HVjt!|*JZ6fvPMJzY>%0svuYdn)Y`qgXF|YLz}CoL!r-R_YPz@_17pta|Cj5>Loacb8@*K}4M*3MLgi)ZJ-&v66>_1WdG-711)C3~>b-^d?9_M-sR++>-)r)b&2IU4Xb(=8EOk6a|tS;`AGunLu#KreBtKDdjt0*ajO;0c79a?fvh^j`JHG)r_zNMw{b8UWr;wBw|4_PI}z6BLVy0Lrhgtp#|Pu@?9M4auE)OgU4-cM~$AZ{?k=tQ&d9WNZ&ueWo*i1v5ao1Ygc+V0M?~0&b5s~Z~8J(nMQnB`EH>#2o>mIc+PWm5g3al?P-;vi&v9?S7ipFJBo8#NA))_2sMbRjx04|i(^Uw`qo8$XqlaiOgl7e*63=q2WLRZe?LBPPBw^;lw`nA{iU1_6L=LNOLN3BB|(6J5=H!idGy4H$%|V;Tp%c3+rCCY1-6YvEZ05F8A@lPk6E>qSFs*3Gh^r&C2&IsE{7hYbO#2Q$=61#pt92)x&oA+w)D(x1w6lq`|8gQ?1%H!YGBrZc=gSv2Y#LqeOF+f1mJxo*bJj3bkKAHp&eBppzo^DQm3r+9tzL9jn=)9MTOK7v89gvN$fs9W=w-0!O4hS2si|ZW`Rk_&e@$A8n}Iz$5lOKRk9`Z9Ok20r4Zm^t>ZBk{Q3Tm1nW4ttTx@dM^Nc1b4YDMTDA#vU|fFZ_KF-W%Xxr2?FX?nP>>i_j9oNPpiG8uyC;mSRP+Qg$olA{KA`IELhXo}n|>U5hCZ7i!C#7{*1}$Z)0H#2y|DGw1>@qBFvK-oS0$}Ths)RlkY7APMEfL0apppo5X;Q=VyQK!2V!M#)g;*;OhC1j0iEm1GCT(hf@8bzz21SOD1(wl(?LF&ZomW7tNHas&D|CKn@GetifvjDkNfbur{ZNePym=oy^5|_F1`jlA64YDu2-q5P|W-6^+i4udJz@4ZURD8<;zj*xze&)ZyoR!K6OP?8y9WUKtUyMVag_5wr^k99`O*dsOtLd<xaS9VIstDk3?&(5HBdyFIWD&cJ`6mgIOaLVr*lf8Jj~aR32of-}F)d8vW5D?DxqC<l9f=6Pf{+GJSx|zuC;Tk{)els9aBHf#kHU;@>FE3?U*gr6&YC#XbXww(8?_g!rbinsp>9T)Vc@?E{Fd9tPL66EL<XqiNwT05xkFDb#fyv4<YTYLSRXo~Z2(l$<CgRA*4xyI2McA)QW!fM#{D>XDMGV>fAC?cx;6006V6zip=!R<0OO5b68EH<*b9fIla&8ZE?jTEYYHfS{pK4?w6q47FO^1`>&?T@_fENxKr~4c0faz6Wq2qS?f!#JD$2OOMZllN9LASL4be0b+@Z6(2TE?FLe*gY320sN0(Kh{`7^Tn8z_1jz#wRzbAv?UC`m4d<XP3CNU3T@vA4*xW=eifP5<H%Rptc?IaShP4d=U2h{uPgc^!_y2?dMU;w?r%WYh<5E1Ho4-qk))Ky24{MInq~Ns3Uv;L{mnjuhGb%Q~Aea@49D>srrh>&>!}Qpliz~n$WDdBpJCUwvH0|Z9@5k>1zF7&1$>!mb%a`hi?eOwS295UI{@egPLFu84Rmy8y%uII@oAyefY3OwPKY%VQ7jz{*tPtE_+)Aj!bbtq8^_QPOQHGzBD(zmHQwmPMK4vvi?ZxChR!Zx1@7jIi7BvB+*f-^&m^>{Uj)GgF{}2$>XHu*zTavK?lh$gogVz+6NZ!%A11y7Bkf`m_Jt}xch1TvbmFzFus3oSU)vHWH+PJ07(E{1I>mFbK)%Sevms^;Yq>L!a4RWFmZR_6p`}UeCK(V6g!b2{in!~Z4-7WFwfw6iwxd`)n*3Md(jPI3zk0mCD;8v>!zoKJ8zf8ph#%mVVv!+n5YIOk4x+)c|R_@EZHH0kBkCI3V4U=xLRrJaiC#YJG<~k-dzuxA1w!mN5sLXzc!(uPGgM3syZ|FcM`~YB!2PdYb%It&K1yRdatH>~Hl~dpS(?vX7$qZ$KW+w_5yuQ&z=g6aSydC1+olcd!-#b|%^JnyUs&FM@yBH{y@X;-c?}A7aeyY1amM7>2o>gX5Kco-!hNrmO0szw_8LkI)E!0W+6;U`!%%TwVw~_pN)eyc?u?Izb++VC>5swGu2$C%ICCCLU+@mKc!2rWeYT<%rYTPBh7bpM`oYaPT?IcW!_g<)-V8M)IXj1d~&CvLZ3k)=hBG4xosW#)AE4_$w>o+Q}i^c#k7{|L~4+1Ah9Rb~D!s^S|Af@GoxMV^F_qU^lVm1Gx=N3xIv05b!BG}hXoJcEADeeiHeHK0|2v%@M)8<#JvFG(q<1hX0HEBsHlag?0`<wDS?SngAX*PlKCo$Hp`1I5#7+~eG2a6O2tv%8Y8E4d21k%FM0v!raFXs364&hEHJZz5Q`)_zSy1|k)GnXki3w~kpB}-_+)S84ZHn}ZQhV_3i>>-Z~)T6)bYt4J_duc+Z6&k(nz*mhX(P|jTC<)uUx?VVfN=13p7L8dktOh}uZ0(vSR0U0|JPuutv9P~Ru^3398H~?uA<-YSwE=ce-I{$yv%~PASh&h0vBqqJ-AbD7gN!+6T#1aES+Es;0=Vh<uYvGNtdlvft}5RzzIi#e1Cegb@JfahK6nH{ZnAU-*-I+X3CMznv<e?k&cWbjNPSS-l41?V^wt+4`U>Xx`h6)p5Ld{3%xF%-NK#U+H0e}oU$OhQKN>Qe3fS+<Qi~ap^v_niF=U1IeffUrPSns-r0VMCB-IZ}Zd8<hRi$tNY@_&q9&4$5|3XjX)fw+7B1sE-A^%-rPV>cl8sY4asibP{N*3oi{Ic*SZ`I8X&cv0?YH!3L>*%6Y2|A~!QK~myA2W94ew)fE!myio8g%dBdgiGy&1{#KPID5=MIAyhKgzmdehpCg7~3)`3+*mZ(gTWXM(tjz`izgVs)Orq)bP5|mEG5}fO-0|V`QbLzP?Ii9-_tU+LKBc5<1b^&LjaySH4C_nXq017Lb}uj$v6S+G!Pm6iHzg&`D~WX`U@^AL9YKZaev4%6d<-{g4*NK~F6p{un#q&5L@?mn@)J0%px`Z4b~&Wfn=*Ok0pxMm+RTMfRUJ*yddtVJd^dj0{u>Jj{usxH7aMD0(qgY*wYo+6pGh6hc$$isvK4_9(3&c(Oh#{igS_yLfD_`e=#}d;g>papsoeR`jXPz`#kTO?GnXhN|!J?t7w<u?tw&1E>%(zM_U#s^@wqa>MqiFYRbTHrM;g>Lkt|yo1}S4eB~F)g0&lW0;(vS4F@aFvpVn$gO?S=-ibihJAe1fpQ|oumdQrG=#5-K3ytVH`#kjbx&}orm#5pAoMIqMsCuPZSok6d_G$jp~^N@qwK6RK?WH9irFy_-6B@<boETf)Ka<;*A^6DsC1$+_6B!KsRTF7GARy~kSL8L7cbR-x>fW}xzX%4)<diV*@M-f$W&L20q)|6w~qr{AkgLMI7JqNfPo><fE6n{)MlI-zsz)mUixsmLNey{ChC?~*Lgwpqb|D4D4mscVX$NeVN;SkE(!Cb*vpee(j}42G>ownD<;6pgT4W`Cr*tLaS_sw2okrui7l<fVu_d+GBC@e74u&$`zs=fg4<N^^{N3DXq1$;0?*pPE$jJtkW#JFNYgBPV8E%M6lkG+m;N16tx>6G!`NjH{Jv<uNZJP_Cq0*HGhPS2I@#+20+MU7A$9mf$;&Ld?={GgHTk%w)=2XjUN!to_4(qmgz=R%6#?o0-2qw(!k3WK%KiO%R2oLK+FzP2cATe>t(jLR<jeF@>Usk;k*3Shu!{ZltGpoT;K99erU|61ty8vh#I2*nr@7(m$iZ9pcPU-!P?#vB0EdLjD}owraTcj$ncqj%D$pq~BDwp?wROVYjFF+R<eWE4?!+*<y-Iwb2VO0Xsb9IfgsNv-M`fL|dUg(|n*y?(uDaS>g!%C<+Jtcv12X~E+vsF?NxZrpI_1r=wS~wh$>?^C6`HW(2}i8dBBy+{RhByLgDENFT?LYTA+@1ja1;Pv+2PHwX|ADR%}8j2U0s%|9FhDoN^Av5N4y+5*u91)H!)lZDrvJ*DZhQh4<A0J%~5BT0HGlTsEpINI=K!=eh3wT);XxE2CsI|z~R}@Q>!VC&omQV>On=4s@hw-nVz0iuIzHp(07_GWl$t0si5;9xE^rTr=l&yPJpNM_|se}E%ciU!;%x)@$y|VR-!cmDDN>f!&(9Cw&OlV*sT;o(+rWjef&J|nx!jDaq5wt_1^{G>39q+b&VxNp^gdY$JjVJAUi#!cP4i-_#`SGPsbP#a+~vX7(|tXjCxD$;{8}gF>8AT-gqzxQGz_-93u2)mJga28kbY3dwlg8iuVj)tp|9)dx{}}XP}&z1_+4cK4i)4rP+tNS_e!1HE40U%KF;VCO;B!?1SDlL`JcL*sb2EX+R#V>wyRD^Q7fghc$KfE8$$FO;!C#12H2LD7EmW8JkllDy}oNsb&;Z3v#|Kl<i)U|5rlESDF;2g!D{0KQ#v}v61I%lhX)No8~?xs!yiIvcS0{yNGaYU0<a?#f_@0nWg*+jP^#MmadnJ9u$I8W=iv`4Z)gLBrz|!l4mX7&J=cp%AgD6;p_BRlwDqE4L;4wvQk$9b;Jy}PJ_U$8l=VNy$E}YDb+w3=tp3b;`VxDIbWgxJxoVO9BaQ-0Hz!F)Vvt^y@JPOz*!C227~>(qjW)mS5c`NlqAj~O-T*ny0hNeFg+<(B&<&ar+*3C7U-Q{sG-8`jSp+Bm?+W!OV<|}CZ&~EqZRC;ax%|o(kKRuad>4PUG9}9&Au1UL1J;TCKXzny`8bl8K<WNB?(*VdV0ZusY1w|z6#QtNR>>OC3NVu9v}m<sf2ZJb=$4YEbs{pvh_c-yul2pF!~VD_Y1>&`5CRw^0cfk#zUQu@|`&F<VnxBW|2D3^D~l&@X%`%jv$Xlw+H~20qU%$qgpo}C?^RH5)}vubabf*P3IBR1cIYF;1DQq%4q`dmu?3KdNzi-fFVY}krh?V$Fos#Gh=88_h918kb*7{gs?i%;%LHf`!30lS*n;|V0-#vz>SfbI2nQxX8k^+QJZsdw|MJ8tMe?80wce^gtgk1PW4sm@+>G|&AVVd=~tEDO*<?2u2k1o$rfu_PP=(u{ooIyNSzMJwY#`>CGTLLhXk>9HM*Clk^@qWYvPVMgp_nsgSM%ls*$X^`_Fx=@2xj8CEeVh-4OP8Rh*FkW1=mT9J@hI=!XZqq^7`pb{;-bd3og7<v`|16m@tIf560}8n~oRQ@^AP*e*5?2AMh>s@&W2t{rf>PRP`QjR2I4w$TR3cGLumj2$;2%7C5uA~K@cP2P&A#S5UQ3GHQvv|<mGadP6VC-j;F`$*e&eFHPi>m^ssFK*9eAn)?PDyw~1M{=Ts(rbWvFKX?;br2yHsXmwJRCg7-A0;Y(GFS|SI-?95v3)e&QeqcRValZ;Zo#l+q?TDsH4FlpkLhkD*fl_q<CS!Dg1p99cv@jM@D}4VF+O6UGOnCg&yx{Cu`NC9wUMzSMZKrySBDi5{x^pN2>6v?F{!FFhwY<k89Bpdx3D6yX=~|@Ysx;=o5}&_#+~}zDN0Q<C=E?B#^E<de?0tsH3au(6HdtEa(UtoRWhf$NbT#@>)RGUf2#h=!8)i0@ye`8$5i4l%U4xrB@_D~``dE^45tGc^|IA!KqqVYMetCH4k9XPyIv(a#leYjM1|!`BB2ZLn>?iTQ0tySQ*10nYg$f;qFg1UZU>4%(;>p>bF-jJrPNKA+QWqjl55m%7Fh$3Ac&Jv<*8fPOg19$^hr<|m4r#2P~mrSA0<^Maj(kXR=-zGXZ1ZfN686ho7fX4RA}Z#18!!&n2+5kCW1Vzj*w6dg|%{Cl9{EcnvW{mGqUA%r==sU9QP>j(IKpG@hG*zT|iN4b0X3@)KVmcj-hOaVJrK&Cln{Bf(LAC;xgBk$cFC!d~XO{X_?%A;A%U`7NIZ>v1gkZ1zOLxEXCx)RA7q|Z@~-$We4na*OK?CyTa@8??P;dU$$kHoI4iJsMVsMF#*Aw5_<sxQ58!;!A^Rt0IVnKfHq}|rK2SjN1<v!n3|zhNwbZS<;mb$m)eohSTB}h?khm<+2)-O<9~B=dtUtq<zFq$O#y*H-5A4g)w-=DXWfWo9T?{;&;f4pR#CUNEwz*C1BE?gFiT&B<3Q7Z0>S={Eg3y*4({2ZORJf+mQn~ITnthkEL<u%JJBM$p8!qsNL>e9E&d26T%U6z*Py}%5;Ea-we}s#D!x@9h~JRc@0mjaLpKg#bgW_*=*(yEDR;&EeSyOLp=gVJ+uos)u#k60yMX=QFh<j(TdqZ&8?kbp4zCDXvhBL)vp?s&o|}Qo-)ewX;H=nU*SaHVs89o0&pC60NM(>_Q5Hsmi7pBCvnh?M30?$|q1Yy1i<5UnIg1G<CmsmrA6KBrbcxO^k#@T;vmF%>23TrL#j--0Z2_`*5bHO!$hrPHAVq7`QDjpjz^8ve!fxQM$PCPRX9dKp*}~sAN2%?(0DU*v$YGRmE3mFazI?xeb8Ap~uZ;-%K4PKhQuRV#XO}1GX6CX95dXf$bzu%6x4ZNa>KhyDUx*!-L)y0A^}ws?X%Y>q+d(}*8+V0twH=atK+J=8jzPM@LUzd#^@$@&@0PAwfDP`OhtF|UbC(|S=8v-@?`!k3up{d4Nz<CXVu})p+~EPyt<70lt$s%pqn(*;RHk7%3jQ&FpWM?%ag1~-(G^skr;N&>o)z>kdQ%fa=T*mPKwmQ;s(IFgMd<HMN-Z_3cYrLA##1#BzD4>3t<NB#Ov{w$(wP{uv>l5ub@^vvnL!S_(iC-4VOdZM_Z+Ep33n+~KdiFWd+r8u7dLZ4T7CKh$+iE-V<I~s{LfwX8W6Z^o2TRpaS7nqbHz}@(t?$SzC>v;Z9+#Z@PN3GFY3JBH-#sUyQeyJrJ67YpfYGxlrhbCny<jKdk4~sc0l;AB=100YqXaW*gZn~t%CyW`R*S^X(x9AEl^k`Sr04!y#z;B_*Tc}K4zJQi!Z28v$@v$q)DOu)MP{(xmrj!l~d|uqa`6s{d$=C$;&GjBiuqNPn#WXz^bp?zxS-B!sqIcsWnw@{jj2_uvr|L6W&bas*z$fLARPRt&18DnWw|ZnGs*)Pq_t75z!`$(6-8EwW;MjR(+!}#n(_dA58GedFSoxbz!knpN~L+mB@r5GpF}@!cCjsLceQ>&i-vI7sUK!w}^JS1L<_WqZ44|a1Ao<q$8Sr`=-izL@n8CyE7LF?z>viXmxth{#3W>T9K8+t|;*BB}?4}i;WRgKpJRUFIJ-NB)CUPhtJLyuZcG4os5)f>MPHxdaQMDcU7rf=_xv<u~$l9Mj4S&XH9g%-R$G?rQ9$#nGl6Sbkhc+V(vE8_s_{d1oJzE=fxHCU5f!6d~Gbm0aio`664!8%p8Pp3nml<#9fqvo;ogIgM`CoWU2J#fZCjS2@{120#zueCI)DLSrBUzq*9X=E^H@t){xPuTyE3$D4z$aS*WtFm2DWL+<s1tN9TYQ8%|NGBppWCUg23#ViIe5ry(zb2~qPYg*buDX*no%-#9tsvB;eR`$qYz_)nZC8WS?AB2OOQQM@hn$|O1{|1N;Vyw9$xCC62nZZr=QI_qGoj6qes2mDv%3oTHl%<y73q9b-ZE+{Nw9N}VkzkB!U^~>L0+<d$`V?FxrxOs?m%X^ZxpS8IGb<GFmn|)58YS&VwJbPEaV}1=4)f^o-lw9;}q?AK<^`Hrm3Z+M!;#qx4qT54dQO^Ae5JcDQPRI#iMGoTUu8<0pV~u%dRZ`aR-{cvF@%oLSHv?WLURF{j64U@kp<q!|v5GqH#Carv6U=!2{I1)8>kW!-uq=<lYV-qFJ|zlPqJ%kTf@Qq(Vow@~sa{Otz!nX&$X*b4FyLNrep@~hEW8UuZ~$NNV0u{il6y}hIur%SXLmJg>yd2+9$CiIatH%2g~KB&mNv0qHb7JH!jOwbqQna4?h8fAxf!c16H;^w`+(5$GB+v4M%G~m|12mDfRXKD1eH>C*7OyBM4BwwfNA{xm7Y~;ZR<1xHj%%K;_iaO_1}_??3eG02gIU4bN%`*)AE@R5hbb`J#MiP=X2x459!P#T8e$fDM??b+Tb<CX`)V;kkZOMf(!vnAkK{u)(SC;;U`(c<Q^J)mUU-9x8fmRnY%|CMb_L)qvbjIryCSiV`V^<n^42sb<|;=jYR=iVlYt4lL>phRFaSkd!5*Qv&Jy#e3B%vXX`&^$W2naL{Z-nJK{U*=+qer+9K{g+?O-#DxDM-$kAUXEqPCIvb-?Yg&_4Dp7NaPv#h0>D1{i<%|`?O>T?Y>PwjHQYczhP)s#xQ41csh)#NUpb8VL7$YhukMvT6r)#S82DccPAv<}69FUy44h+xE<0H02btF9&R8V@8vQ@(vLOPuiKx8^!#;!@<;P;Y1J3D(-OHg5fsa6;?->yY(`7})E-yj;RQ(Y&o{%1xeqS-<zVdGBfS-ZPP}13J@8U+-F87#r!8!#q1ymiSa}{q46}ipDo?Z+?7!dn4ZX@%r`6PvY;_-+!+@eP3NU{P{$`9{#*8aOvKBtlAu?Y>b~JR@`8Pxv9T-2^rnVVE>k^^Mt?Wei_)|c+S56U$<;<cm")).decode())
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
