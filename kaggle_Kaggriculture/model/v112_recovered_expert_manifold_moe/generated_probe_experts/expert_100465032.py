"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqO_L<aai0InoaYeVk;&T<XaZ|mU|_oojZv^M8cc*lnv8%1LI)X*|6SA5m6;w99v<$IQI%EMby+leX1Xh%j8FI1U;mE}fBf%%``5qx`QJbM-5>tr!~gi>U;ph-fBpL9hu?ko(@!71eEje)fBf@5zy8_RFaPb2fBj#7`rFs9|M21OfB%pF^t&HF{qpy}`1!-f51)Vi^4-_}bzeUI;lr=L|MBHR^2O`l{psc9mtX(lZ(e@*^xF>~WA^RKzxT_xzx(a?zxnQmuYd5<uU}q%NB-dAL&Ps%{_|t<Am9Juzx@7p$q!o}>JJ}2zx?#`w;%S~Pe1<r>u+COo_zTNK6vd%ZveV~bd_oLJOBRo-~aH-fBO3GfByY94B!`Tzo+YAe)#SeFDs_x2Y>ye-~PP5zTRK(53esfCG_3TFF(Hh<Kj20Klk#hh#&lm@9HGBUs2E@e&X_Xhch7F9t+0XnCg3r>v#mei4VDad&|ds8>!o;69FmTUCCkl1sn38KK)+)4ln<x7Xk6|%2&4it|3#9qO$&iHWXwI?iv;4>nlGVLZbaamw$vJ==zD52gQejeBdG<aLgdsyF|1}bgmK2wTH7rynH7nou5SDhr5iwQJXenL-zRDMSp3)NPl#Bn8A)qwV$0of^MBVdM5HV6w)uKAM)vkA6|a(^FRH=%a1>Q|HJqH?b}P*`^k`XyyK&lV-q_q-3h0@k479?z+O>Xo;we2#iA_REYexKt`9rdl|Qm;vnhYf+ou<8Fvt%<KK<Sg)<lM^%f%1*<&U3!NB)q@!cG1V>{j#B%MY(NIq<-*%N4fF+14^=YiIm)_hu~OCjV7$k55mX{Jh_PF>IdYnh0%%@TZ@D{O<GLzx?>)KO)-&@^I^(o^A6bJI*hlAD1&u_@DS18+~mz<{zFV>ojxs&VP2_rX<?iTH80W>X&;Rcgi8#Ro}kH+nz38?cCb01hM(qu5}1n79cRa;kuN4yNhApQK3O`yI2*Wp59BPB(^|p^_8ed=PoaS#@XlFXH&)@ZU6g2K3MbZ^_@UOXA0ht23_AIyY8q6bN30%Rm11@%YAOeg5wTrn{EeEZ+gcTd@%MUTd-*{_u`HX23!6|k!tTo?0YtKpkZvq*}v{Qwtx%9b@$)hV{F@gi;Y;e&tX5P{ghNFHxIe?9tW~OW#6_-eVFP3{E@rE5L-3+0vXRj?6G_x%suw9vs~>uScyH{W{0(RdK|dc#=NHNfAQ%vYfoN(^W`6iE;97yjQr{N>-4}NuViPWE`pM+k=lI*?bLZL=^j|+$+fSe_`4tfEB}L{H|TH4wAW#rJoWm6t1-1Tqts-2`L#soa0lEqhqkWpT{mg4*VRI&qAk5IP=b6g_=dL+iN2m5%|p){p-ySzW(|_eZRQHd)2(c-ke7;{JXCo&!PbQ?We9TaV?=>2{|KD~f}fM`SH8LlBL|Id`RL2{;eJQ#*YZ2I-4hD`$h?#G=Np(2^pBkzIsZ67e(M@{`p!oZ-S>MRiqaZg>&=XRik^5rEkEpeJ8<PiR^jS*_vrd~Ie~K9ul|Km;fwXaf+@l{`+Do0u50)DMddzS{zVLe=-9LVr1i{)#Wo~RnPHdmSp-`c@;mZ>-TbOU$H4mZ>u}khwy2^(m2Kq%<vX<~jb9#r)(Fb>DUfgRg(7`{8}vH}Yl#-b^@mSB@-#A)!<67?Cj1B}k;=Ot{rIK2Cm)ICich{PV91U_^<<9vq@3jkHuxd;mhzB~!;(_cGgR|DvmH(7kjCDs4R)Xdxfo;L>c~Ujr?Ah}gIVVht#TZp?_j&6Fj(nCJ+;KyY|v4$MAJTh`t)^i3bkj+BUOzJXZdMTk;3J}6#G>@-$x5Zt1D4phS8Dq3>NFo3ph}rd?h}~%9$i@Nt;@XrxdY}c`1fIHhZO7)jk^h{LRmYM+l3r%2%1bE+>mqtScaKc4eKX-dGqA2qNEJd6uZx)8Ge5>Nv4YTv7Jz8$jRsR3);eQ0MD??3W*ehZ}NE5pS!x=9Tlec5CSS`9$py@r&v!Z2!{mmJT6*zbwum_;#=8qFk;<2}x@oo;BN=$7eF0jr@*|YPWQry4#%34ZbUyFMVa$$Snh&BwmWOxA^-#GQe`mBWH&4Q|v7K+5Y*uWMU`5d<ocHmWZvK<T~^A@fgL5#e#yIZLmkIOuc3`4<%)*onk7gt@89QECVVRlybmevC!KLqRL}8-z;lHZRb|}w_qQr`EEI5s&d1sU*P1gl^SBm+R&5-@?&m287?aIEl4mE>mhY57sR5;?U241BlTECq^EO4zvN+ks=#dfME&by`SX#y38r@}*6^{bBzo4VeAd1-k<2`FFTzxcqq!I&BO1Fz@hYcC-D*|zkpgd=ZP1zlfgJ{Qux(}xo3*I*F^|+WHeX2f^kO?zzu2&l7u=>tZX?lzxPAc$VM7p^K`JCTPF$`%@9^!}8Ub!$OSustr<^hy+jT-`#_h0Om-+XaL3m=elILe+(-37dYExBkz-mRiC3kb455$g~M89|+$%vGvhOUP$hu`{EVdxXNQFT?eAis|N1}lHFl2>UyIm<1L4(As~6I6@SGX=_MCUWDV4yPUUSjBw`JI<2}Li0pgj_d(*y*$ix_;DZyA>;@1)IXwMjBF^JcyCW3G9nv7PGh8ANhB3n$~Ukvw%v8=0ep#Ym(HhDhEAFJ$^}6(6%y$y*OTAERXh6(&B|d`27PnUkUVZc6{A!oLBxlWe*%gDB1FL=z|3O3P9F5H<V&i$regC6rr}EQTISDw*;T^jYOx#iFQVUM-xPe+0EUc_mUozSv8!Glu;fYmcOv(c#)Sd>CNJ&RoN&ll5joG0*NC1qmoI@?aq<7jo<u95xcNvFTM1>`?L#H@dg0L(i|Mn)JH)|~f2d#o$uGbE6?*QJjYIsGU>Mr_^?oTk>Da>vKIw*fi#1ux0;O^(Ds|GxWs_g^#abZnvIXSYAqh3mYCN{4zj*_Zz$jlptCE1qeIV;<Pt_b1C?`Zol9M{;mm-TId4TOHbRe~?=xW$uP|FMDuvbIAwyEtF&z8j2B=d~g7mhW;n=H&SG8wHK6qFBTB1ANf%>HoNv?Iji<pNP2+T9;YQXoPXWjAj_y0UxoKW**s?*yV4>TbllOZB^e@(XcyCRdofEUdf|p??2CBqQxQ1-=q+VpUvNydg-ha+Xq1kq=duSMVy9m@lv=LZI6+1y0Ea_p81`KK7}|3e@IdmRFoxXr6mx&%`;0%r$(hoGQC6)9i9XgggDYTk%~^jZa_Lxpi8=3KaR$F68jYTB$DUOyC?qigOr(XnhL8-n3FJMP2gC&&yN5vMYqB9AhCkU@K{Q%73W3GbEN!6Y(-WCS5nbCxzRXzU;sg!Vkl|4Z0V4c2hUh=9Iu<ZRPz8rMkVr@}rVdfl9x?GLDa3pT0E}8Z?oICcYr%#~_#Na#vuAfT?#;pE;rfLhI64-i1m>uI8X7m{T9VId-V3M{+YNJisVH0TzZNA9=?CqCDlGhlFw}U}GLxhgj8@a4)N!r~7h!$gv1<LZDVJ>>naQD6EvTvQxLGw0yIsid2}9YMBCacYOk5YNB%=jf^7++LoxZTCrK)v8OM+W=yo}Mz$t2%_-=2#hqEzr@}<T#6n6Ib+C*s7^QyA^{uU&v{^o<%r$TvD#|eE9$CuKVIwok<3_$Jy2bWDBHFV4jAD)N3MBCq2w&gdkDq?N{9B^2EZ(xVu_-N7_3j`Q6`LX#N@4?Of#(VyYE6dvcIHM<iyTwz^B+NF*C7_suZe1s30KOGV)H=0z<urxhLIUsEK<<(+{n8j1ANt|Vh7Dy^+)6^q-&&_0NCa@$i9rM9Fi&){w<b#+Y)Dg&K#1~;1ws2%Uf*Eow7M9_{W?}_<)&2-yFrSfN4Zf>{;U3(^O)YaIxqtvC+XBX!*mcmGGidA|*2>gC%H(=*x$^95Pz-uKa6)qoZj}BHH*9`3%Un&|yVKN%?KwV)u2oC`|w#8GA^&5ShB|B6zTN)tm_yWrspRp#$}p^y)${8wdn`44jd0qfdFnX#!51YD<GkUPj{1!i|~nvdmP)K5|kmucft!cbR|il2APv8!Ocolx`OF$r8An@;<mojfWLV6`u@wBZ%Iq(t@>53{6~8%4mJ@8MbY(y$#noxOQ74P?75PVnuu$Vz4#6^2$kIzx1@mER(vVGKy0))8ScHdj!hZxT#fUct=U!Mwj0+a?`7qHF4}}8`$M>Id{9b9JiE%FW+heKH2dgb_shuILBz+U5;pKTcsXDXr^2L)O|)cJ>@jCyh-ZU%PXfs-BioN0A*vqyq>mIS-LK06yHZ>#{w!N&b2jeANtFuptAJMU6fQta3XS|zzj7HNi`mRL)_C<Z99x%^NG6iqJ?kmYhl;@6`xs+@kf@swFHK(7GkX{C_l!NRNu6Y7mW%E>~_KKh_ypdNMHVWx9F~Nu5z)VMIQKTuiXzgW7X}K7Vvgs<R*o@dUBMyFMI<p>Jm#8L$yNxZR-kdZh<jzNT6vnyWZ-h_XsYS%&fvJ!h*OqI637hWt^62MJ>M-k%N=r+DdO$$c>im^uY0X<{e)tjR(~j=JQL{l!WI@u}|1Vx1Fg<e_gvKh;@HoACYZ?L8Qy^pvBboU@u=(c?%}qlc-VgZ@&NGzo4?A@`E-y4x{wt?}>Hcm$qPL-}=gzQNDxn6A}e=#b_DVM*2Xl5gOANqbwp-0&Tx+hK<Hhtqu{KsKx$!aw|JzHQhkvp$JC1BuWfGTkT<~ES6tIZ6$UiQ~S(5Lc;Dp#iHy+OJL|kB318zoDrK@5}v|^8~dQ*R)dNgsUj(^REU|Iti{RV$YDx<Qf8J`R34kf%i?eq3aQQ_hZ3_sr$b`G`~BtLs$a@R3P-59B#%4tN3z?m2N{`vZ-&#X8?5Lc<Ib#HHSy`Y)EJbAnEE`eK-{ouCDOx+^;yfrFFV6*^$xW{5fYRk{>%%;lH-^2@tfh3mU$TAURp2x>GNtO4k5@T5rJBbeDs=p(!L6qLZEK#lYM7LP^DT8GJV+toA~T(V<48ZX7%HW-$gSdi1oxObt`-aPEM8$DW7bPhCPvkrnybHUF2YpcdBbQ2540uHB9!)zzy~%hSzU^ivq^siuPw|rJpuELJQW;FNu7N3;pg9T*&kayn-9Xi;dkLYghz<=jp?_h&EqJy+m1aYzIWS;{Mw_Yphj2H~Vry1|EnD1RZu5*nz7o&L^ia9eCgf`g;%St+`2F(8#zBnO<hbO^8HZqX!0A!^RYIkO%c0l@fGmPNP)?KGf5UG@<&DpF9YA0P-GRYj`0Dx$zY!+-Be)cUCHtGKjnpR3p!hu@HJYj^k#fWp<-1l$JY6Wowmz)IJz(4_X|SI@}XAvjq*ZfT60mMtGfCB)%yrC88Nh^Mphp>T?U40mG45u9w#^%_3Xi@Y<eY$E&7XiCGCs+3~XimQ<XCnYWQud{R3gKlnoxP>{*ShK3Oz=KP2od8pt^2W4s;z6}-~Ai|ahrtC>jvd1w!q{MXOi$*@~4$&AQNnw3_Ivzx3zOe^jisxF|8s36PNMF}4N(<!jwq2SL)y-_mC{+1!kmirbUJP&giwleH?E&KsHqOyuq~UU-Vy6;X;zhG|My!&t%8yi8#vrJo6f1B@0WCSFIgz~%gHpCrGgi+;WL>)~c<F*4D*oKM>2dtB8N#*dBpX%(R2ExEPlXi}{3<MZ@#B84N`}bPw6FGTzipY7^7a7yP_!(LQM-UpL$w|WLm#5HdXfDVhzcgIEQr^qyCVj$t85AST;)Ly;^IO+O#13r<LP7d*@~$GzxDQE%?^zbFdiu)AzGrFYDE&M3tanDCD7F+xq58dDz7<ZM1bR7zE^A4bFHJlqI~?j1WV<#rz#+uyH7K8{L-!hS%&;a;yd-{>Dz9RzzpS<v<;(lB@hRxMXJ2AVK!NbNslCIMz9(`lNvqb!rT~FWcw1@5DJNZH%~NgLy8D4E5>c9+)#vV*C-5lNVXQFC1#StAG`V;$sw>xtI+|q*-nai1){pW@$AyKTO#$C+<-OO!2wxPmZp$o0<ll(S=(xt7rnbp3o`8Kbq{&8blL2BXF-q{DvO|6(P+kLiO58>uVYyToH;hj?^GX|u5H5-E2uW5jIxnIRP1!n>}6lRol<{J)C<xl5+q#Fv%Q_!UI&dM*><qbGUItfKj@D|&nxOX%kb}zi6LXPS0=^?LSET<N2-hw2e>@B=G4S+)yte*L{_Q~(BmVSilU#IxpVYs#VDz~_@pk+VN{={LqWzqwxfTM=K>`t^k}x7s)au(hfT8KpS+BDr@HKg5sFG5uH&xFy!3o#*lr=`K{`jk_2p&9I90J+h2DG1Zu3sY!Lk1G7%H!#wR6S%n?CiI3jtPxM8?+mQ4!u#wJ)-kwb#`9Ra1unZe*LtEOZ8dOAUa0yTm?K?TW>0RKXiq%=ke0jGx)AW9;@($lIzhsNBWcK{-MVgM_^3z8H<(vSs{7ma!VMi(*6UMIfi)Xm|`Oy;BA~=`OM4!MW-SMfT$@$F=F7yKMQEz=Dgun|E~UXnjh`Z;4JDR_|e=ka#_OVQ`mkMt@HFEX(v90?Q-QHHlPyA>C1nCt?(-O1;C%Pf0bm$3hR~=OulUDG3aN{~)CGXvdaNto{`-^oKV=B0R99zRprRq*^6dExNQ<wnc@JgiX#^EzNG)xQwmyco`dY=`vYj3Fu|d!T6}te(M@;7bUXBQz&No*gnck!)<JuXG=O_Bo7XBSu<4)x7bE34SVgY4tbmnZp$kVva~O+Qb7rC7LYxhc!E+qP-K{4A$MIT_ohcSr9G>?Qehjow#KYH>LKV`$_6qL$hjXga@-<i3fcIGG}6Ln75-g*$hB)Fpl`k`^<_it!$>&`TgIZx0Cg6mPEma7jnYfDvV$>|DQi8RTbdve)mo976+gVlPU+sl6>HSH@%HyV5_n|uo{BQAq3*|U0Sbb`5za%B`4sHnvVL^r0hzA-qKB;P7s!31Ci5b5aL8xp$xxbAFANcdX;!pTACJ5h^1X5yX}Hq68Iyds`>2seT6wIiQPAGfrj-F!HA)C$SwU68nu?C^cVrIAS6JGlvpx^pgR-C1oY$PHH|h7q`jC4QTQNgk_26^eDxMh!GWfBe5_N1bLf?B|D2&um$l`fiTO|4*k*Z*PXAlfq4bgfNrt`JTU5q!8`1b^u=&UBqxNWS76GWGx7#SaE)D5tFvD@98+U8rkD$ek`dfV)oSLMijAKlTs&+OJeOif$MPlloU;2TzBABFrwp1VDngupNM!WwaOyi@Kg%z+~)Kq_wdq5E1~%6srSASAd#J4S)piN-aCGl4Oh{h>UrX+G7KeVnIPDWPQ<B~fFa<2cWm8itXmMM~R9pF%VeM)gzs{35*PYsV@{?6+;i#}ZkPxXcCQ9o4i??W+pCP!Tn?<#L6Z07<$Q(q=9K$rB=JYVOF~rY*wgbuAXzlWw7<QfwJFb7!pR=6E((BhoD8qR`R@mdjX8{3md0B%afDD;)`Y@^*_FjwoLwu&vkQboF<q>o_QfGRBJb(p}zBt{CL}ZoRpNjUxH8x!Vw{`mZ&SkR^bp%c8u|>h*xcnDgxsM#=ul&<G5{l;wl0PLWI_F<vQxWk*Ua84<0f7Vu@~(Pd<H@2{r7tk-<Z4*e6;49j6fTzyeFURPtP_Ziz?%<%F9z5V`bl_R9yUtl`cXL*U7JIb?e%g?FyXvA07ZTg1<+XOxJYV~z__h<Z}nd_-1uUs5Ai|#&yg4h6EN!Z)Up;Ow1jCi0R>l>o2y2E{?XRO)PF7M$D!FFA3ImPtuAU3bPSeL_HdoAWV^yxvWw}!$KM@1=m2uFEN=x>jZjh@=gSS9i57;9gjunp~hfTXfo#)?Fyh#%`Sg6UsgGLZgUb!+$9v&pNwYoDDjaBB$FxJ^s(fBl(ZfYo~@z?NW1w6gKwpZmPf_+mF+6(*USLO){~Xk`q1r$l<T<{5)sHQ#Vx-&uDpIC8NFP^O%e9SdQ;MD6~KQd_3r>FvtxcL?Bk4cM7yfp(V+rq5y}{=${b5j7m`76i>M0{lJ4N%V7M6dzMowrc~44XsC0Dw<AMOr^E+)bIIJG@*5j>j^hA3~P{AvVIE{!clELTE}u`hNGNGqGpxufkSgvCVvyh(5@2BGtGsb6RcwwVh#=BQ5%M=db-b~3_n>T;W=7W)_$HH$3d15j&WU}oD7hEB5DC$DczC;4O+I#^<N=i%~mhqw|?yY%<(^BML%{oi*F^5YoQ}SEI?LgrN8vImB(K&7C?L96^%6l)?L;vJf%<T?kO*Ot4CyHIlbzG@#jfByI&bXHC+&%4M$gi4ih`lJ}6nQngv)K-5A@ZoFDX{wJ}tfjJ}C9c8kUcW7@%V>~ZA<geKqeZL4P3deY!nz?tDLBS=U!vs|QKF<F%?*UTAQGgl5Z(yL;LACy-^L;%s6DV^OcNC_PpSf;C!NzEy*$8aGi<1|*StLn<!Ah#F>TcIoYVDe1gj=uNEf>^2HViOX17O-6F>rYI&tqrNbU`w~?L^ZFJsWn>5JLJ@D$4>=Esgn@1duLBGALeYE+V1>hCC_J$4Kxzpt6hzlQiOnRV9ly%+K0cgMj$FRG_9ZXo~awcF+JZZicfY6vGP5l83?*Cw;swtUg`SGjoceoz4zrEcLAW%z12Vn8v;E^I1c{Oj+v}95?xuVZ)xh^^2I{-TxkuzsLN(~#v{iH85_Y54}9Z>vGz-i(o!~lq04<M)PqcJWMgZ450NT!&NYXf@93DtjMF6@++n{RUM)^7>{dT0w<a{R7NFtmMMhIO0fk-XXZn7}b&RAU4PA$5EQYY7H70s%+tY8Q-=j^?1ZP3P@3hXCbM&54RgEDT^NUVKUJ2(JRS}hE$C@^9@3qJgVsl?9hHY7UOvGP0tjQP&aI`+W*@5$g(Y2x3;FT9vPRxG{<E^G{LAwoBDT`-bKOTmYHd86Y@d-2BJTkh1*J5mS3o$a{NM1PU4Y@hE+14ifo`n1!ET(l$Ak*(#{aCR8Py?d)0C-tq((w7^hflv{m62kpiH4mS<*i5_8wuHMhp)}{+=K3cNN9jMa?t}{HpA(Xz92YQl1C73q=Q)LIM!frz`CJjinVb)_G*W(hO2iPr(<VB*PPeA@&fZrog$JQr-GbF%7-#a{G5xKkqMEtX&7mKSw60ynS`kr`IP>oZ8dD;#Y&9%IY%0~F`{5ptdkm9JxVs*mV>PE@HFw`G(YW+otD`m-776@lvK$=zl?|OaBA6S%h!(N(KlR%piFK}Qfdy%)1$E60f#NEHRKm3Qi*!GsIy0U(5W=!D&1K2H@$X4jj#jPqDN3mxjTwZ`sATO^G4$}QmNYJOKAl$WiMCE&)o%O65o#DTL!84ABZJ^>>Rud+e+5vQIDTdYfEz+)4D#gGE8RB&$7o8i2T$5zpGN@*T_9IqCBj!<mv<P1$)T;!<Y6^2Y5>C@@=^7SM4ENdSkoB=PcFHf>W_aRuxgoy^21qI%67l;I{wZj$1Jj4Ac7?x1j|1EsR;0N`zWZSPTIm2_rT8ay8BwRDTj?xQw%2)8|J1D$?1TZ@k!`?ktLhUNEKFOS=x18I-K`3%umdIwZ12BK9I0+wgM2qs-+vsTf{w#rF5Bq-X^oHj*j%A9_wHdaEWeLR>=r_K$j8Z$o=5Ae}5oe?Ia(m%T5_m^SliTvzOx%+NlK_PAxYju|~_I?#zyGt~&SV#I5U1YRy^tgQwjS!qu}@aGpv%#J5a8_`a-Y2Zg?Ub|bJ3Qxv7$FYX#S@9?3-Y%$=yn%~fySj@w53^oF^<nxnS%SjCJteK3Mtfv%x+T~otAHw!3e19lKh){I5^~d=T`ixjurEwmG~2HHA^bsW1ESZ+JPyigH-&beUqr2mB^C2yT=MFxW2+4esVC}l!b3JtvYP_wMATs%DQfOY#4Rhcv|_Qwsv~GC_r`X7ZMD&*JuazX&$!TYx6*QywBityT|E_z9pZI|)O+(y9FVIe5z%V7I5GRY?6kn6LfXtbGf%8mlRl05zUK6e+3%J|sa&uL$*DQ6gaCTH?^snq=>5M8JGV#aUQ;_tV1z`jIHI$T((ZyLKJ)q<@K`Q=<rCJO2$`nD)lbc>cWj-u5s^<3n4mhW=1Nnh3mkljlfc@p-58wi5nJwK%<z~O^s0E8+7)szhEpB0^0XG?dP@h*4Is$-ioNE9W6bJ4OT{5n-As88HoeiRhMOH(7tyc*s!d{f<ZW-KSK>CGr=?h-xaKkvs~eLMTIpAu@p^i~wo<%>D4G%H(l=`pTYS3K<%t)|+pl{R*y{1$MWcw8zUmgDj~(q~+tKWX<b#6W?6yH_LhwAT@9a8D1;X2n0N?=Sl*p1IBi|hgFQbH*g?lTUNr{cfGU)#9vn)eBzD$=H45waROF7k{C8g%CB=f+mOOp$#YMa*lrAwG9^EDTIC3k5;yo=^9`}M2H>7yJ;t;xes^6l?ci$wMqaaXx*9U|{(O{Bp+YuSC*xeq7bgsiMdEnB2d9tt@2hfJA29<sBgEDwv3_e*@`6$8AssT>~*+2fP96(nXur?RBh8w?{pmI5Agjo^0XZPYuUHA+ZDZn0QmaT=apfEikEDlDluEO9WRj!#+WP!<%FJt*a%w}!_^m%z`g{=Lm736w?%^MS02lsIcCG9_reT^TAQqn>m=lo?#KLcJB+F5=!okL7*xij}ABraKJN8G*2^X0_Y(=E^fCRm~wQSgn20eVF74f4FAnL_I3g8fxDg+TZ<y6DSbZG<F!(%Z<`or)g4QM(Ptt+rLXO3r9=N_ql2di8?CyTJcrh4YYge6A^j()37}EL_S5WY1f=a=uwbrZ;L-od9m#C1vLJP$OUxJq!C;&1%rzADy}~9b=uli3b|=rlR%%xJNF7+4qd>;TEa!;(5%iIEG;s#O1i5-4N+N#t}axGE>FtF@6{N@PBM(fHO=ZgZalmyw_=)bjW5aLHx#0Z5}KK|*0B-^7b6vqrG~H38Kf5YrfYGTX(Qw_qw=U`wJA?<OGbD2c9WK~As{)jTvkWd5|hof2;~&=mpF63CgXVfv~%&uq4s#$ov(G)=gYq-qp3!}Q0`W5WzEpbD+zYrBFw|6hU0P}_}s3T<X07!AsenCGpmMYkFM1sgOOc1JIe}ZH%rd4=vDTL>tlr2i!rHO^CjaFwB;ir-R^mBxS9uGhFVLhAAD64Bg^rw&EKRUIML&QSn=2K@#CkTm->Cg9?p~7AFt5;x(0KU@fpi=uKL3ncBXwHukz+i#`+pD6j`mSpkB8>F1GA&m*Lg!mWw_jS6w4}lOk(7e!3iaWFYa*JgUH7Lj3zUohQcnhcz2f5~>>TEc738qZ)#j$5c8rt`Ve)i0pDwH!T{eha|HENUB@VV6+}q18<J0y1PnSUOFyQX1m#9R{pWZwvS~aI`z`-d(?zNc(i*GNGh>*O*1M^2%d%)65$U}-hHs92%zOf(jwsEwe;9UHr^n!XlsZ)An&cTtX)4-vN7;;#71zAQwPSj8LT+nj_Od&Nn@Z;%k_ekK!54;Da2&;d0buadYKK?n-P177QeUu@Mli6y4-=NiwRQH$ylAHD_IrFG}EnqK)sC(Hjk^e=gVk|LVVAqidU(cgsfd^bDf$hH|B^%N0_yC&D0A&1j}kjMOQA<>A=!#j^FrZOg4w=%0zC~l*=499ZC$Bt}eKro84;JCFi`2iuKyw7G>Hb4_N}pFbmiIu#D#-e@68iXY~Nahcd(O;A68#PJL~3jOCK>P%Jx>Fg2Z}8kS6lAmuguL4!(n%iJ6NErwFIRK&igCe6I&v$PFEyKr1;eJT`s4eaeqb)4YXY>WsHH<G99){JzHhxJ@L8$9D1esLjYw<hQ@Le$fj+cbYJ<NEb>1?bb2KR`O-O!t~O?Qb4U6<U%9i5@B6?p84DPSUgipu9|ur5;^Z@L_GFk#(?fF<_}K>9i7aLXPVsO%+ZOUh{M)j#ux{nov92NSB!+Q8{8ev-Hw7Vg1+~pZl6dGliKi9PeV`>#RM{o=(uDMv>Jrl)Be(#Hf0A_h)W9u@2p4(`?^zu8k9G?(OLL%(S;*wS=sXi2eBqZr|qO^hNf<VJUAvk29m}?!-(r6s8uDR-aaJ@!Le-;9EUSv47o6Ua&hiQ)Q`${T@{~lTQ^<XPO2DEppT;D|v{k5VI_m(CGKH;4zE@6w$VsytS2Kn)2Pst~9dX3>limbO3z~n0dz?an*4nQ;hGcVP~IZs?!ScIteW}tAd<JvM_w^m@Sk^%hK|#AWBrsLAd!)wyU`@(`mI{)LsTa1-1N^(^&~QbbnJ|B7Z5cD?rUtXUmj>QW1R8G!uCbo>N5<I`h23x^_|<THQEhryhK$jcCy<Goj(TPVO%O=M=BgL6+*NizweG8m##*S8C(TEeYYpq-D;1*J$b7h|-Y;NSufGa*Zy}d_e;vN<t2>tMq*4KyB*d*ws=|;<xwth1;{C)qw(wn2@898b+~uDqz)x+}`jUM=WNGl|eF6I;ui`C6Jag4d%#3&`py(dLb1Q+YWFrDP^7wbr<PoMfctzPQ(2BzhF{!sWltoupN$)rX9AURF*A`JJlMj$7O*mQ>JVdKFh~^PphWNu^8oAE`ZF1MJ8%Yf<b|-i=>+(crpTB{|-NE*g9}<Ei|bWLM-re?Gkj6FZv6!8#Gr8M~#bXxlWO}AzHWiB9bJFOy1~mM=2MnNHjNMN46v4y@#oI3e$crT7ihza<T-7RKuwq@5!-}431VE*OeoNC0I0c;*Q-08jaiWM2u9-6?re&UlL)i3mAFig$Fu1p?!clvAMi*bax!P#r8>ZN9R~7(Md_iS(=L4(CJb{HXM>kqZEO{sny6-V9lWiY4XTJ<VOyMrt6(hT+B!om6sWAD^sdgnHNovDsk)Ux8cdsgSbYeAtfQ>4;<e%hCcE(gOjfLWm=h1I(U9+uN5w3n#AyX!B=O?)c({>$%Z%{)Yc+N<_bqkyBUSQu$wAWCkb=Jm*?C1;F%cXiIyR?v|;rxxJxo^oVveZwn)d;GoF|Zl9b(FYmNClcJK(Mf#cUPvOM)j(?j&xDG?=6<R$De+Iw-bLu%5=J2P3Fh5hh8X%q95N(nQ_R`Wdl3rk3ezZg8KJ_{=9$czbpOKlE7X+Usa;g#TBmtdpd_(4@+Hskohu~4hQu8$GRtf~?2KvWGSRc?wzj2N9I#g#$iTt+%l5Y14Kr&<53<p3%)59l1&J63V>Z><h{*!L8}-?1(aEX$jlf0-O06Y6wMMMrBfjHbA^Z90u{;~7-vq1rbB7}6nMG?y6csmyDc$=84Rw?F>%fBxxjuOI6_KK$EX{`{x^_u=oXQfmFQU%&c4|M!po{MSGJ`Sma9k01W`U;h1H|Mstc`SZ6Yaj(@XA3yy2pZ@gvcmHGg>97ClO`-Ps75FHx|M%xlzxnRxPv5?LdmDeJ{`2dP_?JKZbM_N{@#*uo|9$z@ufF{+c-OE0_g9}j{q&Oks&512+wc7K%ggVWzx@(B`uZ_m-`fR33@ZZHMDXzs{@Z`uw{^gO`)?afWPCV(H8hU#+qE9S2LAUk*r<LsdJ?g*7dG}(Z00d&>^B_diKd1|3($o3i^ew4`1gXw05tA0x!ye*3(zP58uwn&*d`kLKF}Bhjeerp(AeQ<+}Y6BVH3(eHX8E{jV;jVCmM)G3(%PNi^dE<V;&!kzS5{U5gIdi)ab|Gp%ye2pt0{AjlH08>x%P4v!ZbTjT4~J?-$L8!1)Q#r~-|7qJe1aa5U<^(VRcygd?~ufn(=~M+vx<fbB@RJ(=XGw#OeQZU7UTB-)-#w*7X=mDqRBBtP2QClhcJTq2g{$>iIy?2U}Mka;qBW%3qM(chTpchAHWOrGPUWb#~Nb0*Jy2V?R)v)LyTG#vY6f`yGXCeQoM9Wl|@W)fwW!0}Mr9S#&Ng`(I0o&ky-2}KQq(jhyr<Df(oiqYnFRP_C&)hk2gmQ>9BQHf6~U1Mc%660}3hMI1d#(12OA*8Y^k#SloHp>V<Iu$d73QT5rX`t<4sJO5r!}Iu1++HXaBzKlNm?xAcly>6lwZP*E<q4%0s@~Fp_6cPG6!k8k=qD7jiX4{+{u9b2t?>p$4U=6wG!$DvIdMKc2ooC+ihV-Kq39<R42pX~c|xhis^0???cX&Na~dda9F%}UvEpp$xrT~wQaOLY%3R49tJ~#z^rMUnDV6lUPb#G|+!%GiJ?_F%DrPlj>Ja>$mWl@cUSbLHDXG}Z{K7n`pj6D03MlHaeZi#@Q`xMl^pi?boM0|g^pnbkiteYP-UAi&q>{~`MHBg?vh6|ULg+~arhUxi>nD}e8|K_pCesDQodnACgfbio4AHtLl)HnXuN{Zeaeh21_S%tb7p8YTf&7z7*I0S4nV)daUS;~A>Cy$oUYc~A)xfO_ieWZ&xqm2j1eCO-<p~9(2Ddt&cMoMVtv-*5+aM?=sq=Y4S>tT_2_=Q1lN8~*hhp9h6x{<w4TKV&Q0}c2)Iccu38lXKsP}F&WS>xK@%sgedqTM;6mu3R>Io%ny<$LM_6Y^lAU~n3P&OmP1<Lc7e}SR^6!V0llhU4ZbWdnPxzjAqz{)REDH2p$L0ss_^L#A6F9K!nZ>(rsY9PauySu^mEFEbNcT!9iZ2<Ohjq08NQyhRPZ)OAI{~cL?vtok%ZORs?=7|Y!c>`O$bkv5N6;p0zl#06b6BFJTXQ>F#>wlk^3QP)M>MEQ#BPPSZq@I{ebJB@1>34_8JTbu#$hNN;FpkbssIwE3P0mLegy+qvDtC5c+O8(>cxl$M{d1HE?#AR09oP1?J4t=%AWZqy*Cv?ESutr5CYO1sz!1tg>ixCbg$Xm_+5T%+dyzvh>8oS%eki9ARwMo%hm$j5ASibRP!(gav7Cf~UjHxyYF1B9X&y?oI1SFlJr0AQj!eb*`;)9zjz(RawkoVN;WTDE9n8s(;N-HxtR?T{FYPew<8yLjIN79DD@{4sC#OpJ*2YQq9JWu+Ndr#$$qBvV+APVta8f<O`;&80iHz7hIaOjNB`167VR~9l+Uh=1Hj95Rq)xj+?EwYTPMx5%mXgv(1(=*N9f!?@l)4*IBgYi3IyENhj`P7gL1mH!T};Xpq&E4EJQ^n^<#AHx>ZG)qTnDN}3Z{U$w(hcHABAe<N>%9qGS8;#d~U(avnNA^2N3F{46&#~Qtq~-)FYC5qvOGy&!2(Ryc3iM!8>>%4wp9AZ(pAl)Ylc=ibw@OYN2Dkef_$+$HPdeyCW6Hl8Pq=WuKtrpbS{0x<G}81f`n$-gP0k>u>&e%~P<Vy?=1tZjy2`M{%;c<BasiDS*6PI1Q(HAEvUfFn+^iE||K~n`gvifrM~702r`zi(>=t0n-FhEwL{Ne218(F_;X%WcOl<?*^0JgDIR8)7I^8!}PW`>7EGh88I1<5P!pD_G0qy2$Su{<W7r86`0I7OzPB_wCUsYI)r9WP`7Zh0~|j(IH`N%WI-0C<m88N@(;}^fVP4LaC$4soGzT)lM^U^eoLdwpm=p8CwC~PFocsvIH|#$?1?$e138&PIr%Ga+SaF$ob(AenN?2s%4YMpI6J3mDILDu*$Sr4<;e`fG_c>6#;aMZv20MVHT4EcUqI<2K@A*FaVV#^xwd68J2~n5<1~0c4FaVeaX<~u$*DVBeKg(~a$BY2keuA8wr10@LQ7rI#C6cJATx*6tv)_2vk#Up>^~!bWi!i$cMdBg&Ed8z9jrv$;^dDGOO1qOE3ovi7GbA@Wq}6s2@8R>c{oMjy`xt{{ZTE&P6jIgSn3H2!ioqilfklmC5q>RH33-q35y47%i%4VD{~cC@hq^+1(rr(nX5Owdw5uOFf4yISSo|%p0MC<7=VGOzXXI0P?A4kfpb;>wRdl5Ail6h``$S$pTKee)~4?a0}rJqhUF4i_Td|QUK!T*r|t>MU&f9hVVPmUzq@Q1t0FtDY%?}~l}&B5>`7=<1Rb+u(=r(wzh;xS@0^9!ypxu_&~hX#ckZzj<4tpd9fyMH>h)*F&PNvNg*!B@#X-5yl|042-i$XNo)&&2Fk7m5Vr+6A7_*0hmPyj7PiAndv&bRAWjzD^37Ad$kl6wmOyT$<pBkRXpan}_$hUcrY>C47M7AI^D6)Vcb5CSC3y?-&k`xL{py`PWBGW8n_PrxB2{Krz<qBk`2bn)1G6gL0N@O-eHlF}l9ES|nB|&5g<och;E`=p6WF{#-dFRMfF)`-~GW|qWA~OJ)O^m9{TIlqgm=_Qp_@B;63B3gd;p$RM@Lc{u{-Q+YKyUFUGH@<i@?&Z(M1jcM6PXm5e<I@`gN{z&T_DpI7=pB*83J0o{P$fzGi+!!k)`I)LgK5^1#Q&T++H1;n-m)w3}NTc{QW??en!%%a8v8h4hZu#eEVHG-+)A79$2UdzyI*;G|q0?&}k)P2Mt9X$WwZdOIpf1TCskYRaDP|5b7)Fa}t7fJ5{_kOAsY`q17mC)eRl(Vn+?_wP0SO(y<$+%|;qDB(<Pz9yD}|AbZT6+YbP<GPi-cM?}+9Xj-7%hcrzxaL+^245K+^oxd@f6Zp<{#Cg($`-oe!Eg!Q6nHF3=^m+hX)c=c&R7P`p7@CvTT%5MRIVU(>Rt?~QiIWFzAW@7nJ_=6b!_3F&z$s_*<Fi$qW)1YY1gE|>PV>MxO>)SziAX-hxfvdvc63@T#kuX%(DT<N=XB^YUE)+{#p%=@oDtxJQy$`s0H^B286E|v^(NGCS|X4GOFdv4XP324PeY9AGX2ks(|N_mX)>I?7@aopfXR=by*T|H7t`#(S>6~SP7j(G8sO8P7lKbuoEy$5k#8Gt#q{86WRR|-uQ>fhRV2gd&WzK68@K_}e8Z`MjKKoshq}b@q&V%P;B?a*dT@qhI&U})(6H$$PJLFKK~IK@(<C@`wwqfJ_Joawm&xwGedjbd{S|OJPypi+oDSf88^K`*PW>o2UDQg3GZqJR)4*v9oYD};9o9NJe6~lcw2WuS3XHcpES#rHc!sWcr+Sp(DZ{zd+AarA&%o(2oZ?{o^pG?a3DZgQJEI_Ia|Ovnx`V*Rp>vbMHS*pMz|P_q>ktjtFRYke$THj(Oiq^sF+G^fo+yx?L{znsV;xA<;ZTDzeNeZx3kHSk1#<w}YbZZ(3G!p0UZVo18>&s9zHJ?GJqktu_3ghVks5mdI1nbmRjBa}q2g<&S6+{TY5>%@28b5PyU)NIDO7)lP+h1E)i9E(NvK*tHLPF1{i&&(b*fa|!wgk9)Q~`(vPxNV!Ms786R2kWJ6a0Wo)oIjGUj!t6NsXhP^U{cP6Smy&Z6qv0H|B(C<fK6*PH1Ao(I*kd^U~^yHyv}X%E$T?K2fG8QmJyct)ym7*vZwoi2&UxMEXD`^vcL6Z8eDZa~%V0jdK~J%FkcsBbI6+zmB6K2-0`4yd*P)q)0nIaF1F>K+NIHI<>N)%B=4(5DVkoe8Q&M0L8yjE1*jriNrXgEiHy9mp`IcoI{Kn8y34@Y&5&gADt$GL3+#PBwoBmQ>Ybsve%HpZ771>)sy{rtp^P*5fN=s!zbw=-NOPhW=8hVLkhM099R}8Um_0?Ld_=wFOhZGIa^luwGtkOzjY+;lY`v0y&t7+r%F!Q%y3xb}Nv>m?}vyC0EHUxnhcG1Wc!sG1YTrpn3sRy~<}&-O~2`5^6}G>h~~EJD8e6ytJvqN~Rt#jR{lp9+>XU#a{`+tD^SW`DCYUt&)0NHhxq~*n=6GO8jVsk~qaU?_jKamXr6ON`0iE|14)12JRa8Y>dv>JqWktZ>&hTwo;5k5URUJXbXfcYm~b6KYMtDxDLcmFc92_&|VPQ%poB~s2?7oU-g$d9fi|wgeF0_S(z))z~c-Ew^6tQp($DkZ2FBrBD7D0HG~Er+<NjEq_wX)E5cwWy%(WQ5N_2`;}IU4S8%E_3g=-6HHy%l2BEgY5ZVG^05NZf(615kF$m+MBeVs=fFQI5LOl#&xJQJ+&7O}?10ApflXsiQDzO#b5SkMpv=JYL-cI`wx?)Gx>rTCVt<O3N<p?8!&;pgJ1?%4vAyN39B7~as5}_H^iugX)!VsfuJAo!*0T}jApfeRjxJ9ZTel4urPP`NB$QC$+!<HmE`~I>ELw^T*-ihqAEX*(!cVrBq0hKv+SiEo$Lfy;I;0(hg4E@KVWuXRXPMBwMNh`yH(kEsl!!_GECk(asGKQhTFceN<cfpVzhe5U+DwN@DpsAt~R^LH}zOV<o3x;9fI5gXO7!!yw&ewqG9%CSOc9qT;&f4F7N_ga0nyO>ToI59ciwT+RuDY{O8<xd{>}--Jiyt1PuA+n{6uPrK+h^t3@T3fr#^DqwT@7WJxG3wDt^r(t;|k6u(#++o^Z2Ld+Ne~p2f;p+2A~W{cg`j170-Zj)6e7^j#7J2P9SN#l>wVXFl<5e%bs{ticw-!*AWy5Piy>N1KaJbto?}+Enu}3l<I;~1C)!w@o7;`+Rb}W>I+H*3f4l>{qs~Py{eANum|N<N0p+Cpzo9cj?enk6I_haq9~`N04*jBR-Y)DCDf`w`8MU%+6`^#ojjiz<z#{$gEAInekVogd~H<vX%EV2o#1K3WB?Vv4rCI}Fe>#plm?)T>lpM2N)HSv9H^T*14=axWm(4?v+_s{1Yr}Xq6%k5IXNHppbX%~4N-0_I^)?;y6OZE!XO(&X%cfjh;r+{6cUu?%oALK(t@?pf?%4@P%e#%)f)cT)Ot^pt5hO_mMc1`0@48GX4d7C-c0rcq2JnC>7yWCxoMnS(Rs;$BGRRHTowIOPcSNNEkQPEb~ppZA8n$3cUe8Ixg5w<mcTgo1Q(&y+2KYd1<p2GEAI&9EhhLpgCN_zrms;=j_(9fyY|h-A8aswEqr<)zKRM$>u7|>7oW&Pax3w)xwgw}#qTO}ZFe@FDM(5*042%XKinjBrtV(k6zT>f-8AndX%LbIh-F=3LG<V(D@PZtX1{B8M?i8rW5f2(CTZ>!9-gF8^+73!K9~aK1hV@%N>g;(HYY$i4JYY9esHs|S0L77K(UKo{h6O6v6@qh7=ijV>R>?Sm0vxXPfBu5y727-2@83*=EV9EsZf_J!=r<At~w@XwvfVCQRY7Ciz~Q3A<B4Dk`o}QF5C7vlKvzlebSCN_x4r@Nj;dPy+@Ms%+F?(APoW%8c?bgq`6~|VMqo>>xmzs_26iZq0~*3>Yh+`RuolFLDS^-lGFvsbapF{RCs)n+w8U(NoQmvL((gE1`^zjWCX{c@g((~jLDRw^0Swcv>8bYTKA~LtkV`G=Z7b0i9zY5#~_GuTGLufNq@{tCiKZrPIZ#(xLQC+#?=%#fPPXTaW+v&%J4KK=N%w(e-m4Pv<b)nyq?TO9(hubD(XoF5?XOAoj1)2&t9yH3}_*>#VYj)Hk{36A{&xE2<JA;QoE#8>}C$Skeoo{dwW?`ADyJGkTkOukhEEn+9jDo3+g&e;$6PUE8-oJ>`l$)BtyJujv8~dGd)?>6@=|f9%LXiaAmvS9QD!owl-KPJ{#1$r@Go_-qE(obzEk(ho!kf^Q%!LUFN*KT>SDnb)Psg9z{}Lp^5k?l8{maqT{?weaWdFJiiATWK|Z&I8P%<E|tJrl{(B<hr>vYY;RRtD5JG|QQ8D$UZoE6)noK^7)l*)=h{{y8Fy4xrzCAbQUj7^SdltPGMt0t1auQIyCsK&q&Y817v?^aFcFiJRDfhmJTFf`QdbV-c9v8c;3&<df_3Ylsz5~yL^)j#rQd<l4MI6jQk0fNIc0X;Fn@4Gly1jC=m?Y^Mfo<t=LDt8`m2ttV2#J3oGWKaugo5jn>|X6<a9QYuCnX6S$CndNk#AkD$zGxO4>+yT!s2@lxoDF>?f(SivQb@^bb!mZP!$iv?NJ2jHJ6uk~VlHCFwGf_CnHth0=gZ|Is9E2g$4SJV;Rn8|J+z%>|_fXG#N(=L(q3Tn(kY8Oj<-r@IEF0X6FSLQ(<iC<6-p_2AtbC244q_6luJ{ZNvwAi1?Y@X6(SoRP=DBwdB1;R|}8lWU!%1BWEFW(duyRM}6`97}RrC{vU%O81;dqST-w7^1WTQR)tq(>RnhMUNci1d94Gloo{EG(c(3g3@wO-XdAu!{POq)1iNuXhU$LQxZYN$8iKd9HXmXob)vH*Iv?DYl~#9j~bJ)O8_uQT=I6Z44^JJBo)DV>ti>t^>z<Se*>1Yc5V+#y!*B<dLVC6$t$tc*SM!l5}&-UOJxjuSz5qSS33E+wQJ17v#b^l&PrmWWl)ypQkdnkezYaacr_isJ&enKmRqiCDHpVrW{l7_&pufuENzozEcztB2bM9K(9hCe!rlQS3vrf<Gv*0cx{4u%F~&|Zi#LpA1VQkPr9xO<E%B-jkOS;uso5;`6<Nj(mii_vW00~m*_}pLS?a5>#L`^z?Q=63Nv&1vC%NoAF!frJ)PUr*5{A?5B&NPPC}*<=r7ci;;JLnKyWEvg#={4tgrupEG*yyYdtiTllGX^_FqdE~yd=)+g=d-GILYhj0mAVMrR5*dO;UGRBWXb!fNit!YxkK)CuwzcP+H%Qa;eUQC{5;s<Uro=3@Eoj=?9XW5Rw|yt?Mk=H9biJ2j&23F(+W+6E7rH)}7v8VnXAD&-Y1EduL^L#sE5eLy{pOX+e5++o-|`NE%-sl(WpNK7exI2vB+;D_z3qn|3k`thMPt=?C5zbp@pjLG1Txizxbxwzh_mkL|yQpbT9o4Q=2<ki10_yJvEe9DI#~mQ7FVVWjcilh}u2R5gqufeBT54V|KDjjfLxlWHJL5E-*6%()k)%d*%pslE<qYwN>c`hhIxDoRN=M_2SKah3Ax0DQNgz4e(<dauTyoInoNUfg#KC^vLR?!F^Y>R26?ZoshIis4e08sxgJdnoir3`@Nmr6o}6OL1lda%G6poEfFkvce+|s^J1C!Co>l5ap7ES>ijVKneEnl%;WMz6Q&w!tz={TX#E_K=G5Z3|86wEa%Kkcxhs<fDP#qgS-w)dkvPdVHtuC<5B8|LMbzw(q;fkmvojfSu$Zx3@fHJG66HNr$*_;-K`gt8l1qliq{3@3{aXCWjp~&U>BaEjMlh*lv6Un9hl%-FTwx}n(q^(8naeLXTlzoZmk|(5;N0ULu`TDt6J+{4?$_KkWPqK0vQXCE~(`_Imi%n=&xs=z+ESR$*nFSah(Om;|V~Th?AVWq>+!y(gYI-W<arNNpfVt>#-y^8{CAXRnBykiP(!J?q(wFfzD?kndiFhlcc*jNt+aj*!4OH3&9j{|5!*GFoq8z8Lm#!%w9q=FKd`DB%x&2X0scXyUr&dxmoI_WAf|W+sY&rDM?L|gc1yUDK0*Q<UDYl3?oQtAxR5Jx|5K^4?)%`P~&-2?z&Yt?7Iqw1D$hCIoKKYJ9)&+^$j7`W~H-GrECNcLk25UimyWg_gJ8PT@fs49G>yiI`;DnAm5*+sC|~YcEcMpYjrHp+G=NEk82~y6voUV7Xq~jP}u3(T>j26K<6%=hO|P-caNz1cupBlSUn6~#9`-|kxiNp=BaBl-l^CJbS{8e0MuovY}oZ$p8@D}8=flRsQ^zixMTBu^7P6WDNmcpm))i7Bjjn5(!z(}X-Dw1HU#Mo4|&>xrvshs%fz<2#3>)1r*qW-It-`*?!yqMJ|ob0E1rJksS%!f7|;1EI1Pz26gX8P3L1qo-Xl)yz3ahgF8Qy`G8^Jl$!v!>?J%6-P@J}MKk~Dh`8<8ba{}qH8MM_@V0)i|gS%f{-tUj6?z7Y#i_-y|HpA%<obHJ;cZ03r+-{pGPMzT#)4kN)3TGf~iu1cs^irIf#OVM|4J@^xsNh;S^$x#88BSLTAqVALAI}NM_~C5dO1a%?n!QQb&cbsYo;JrB$KaemQHcT#)lx;E8HUr|2TqmZG=AdW+&w6IpE56K7~)jm*d9U8fqTZOM&NYODJjma7cq1xhuz-wD$B@mjyowGi*q}9X2Ww1VxC*afwB{U1)ljane7UkJm*K^X$8Y`Qbx;gdf>L?3%hccgydlzj{+ypgK%nfZJw`L^4t29cVIANC*#*aAh{uKI^K|yi1vYe%8$kfD&;eb&bq$TE{@BRc(;Fbr8uSD(MdpvR9BHsPLIi!mu<GwTE|p_a12sXuBK(i7Mt>K2U1(<Ru1#!u-~>x!keiN@(GaI8d5#Skw{_V?FFd@w%g-MmXAidsn0W{Mr$`#)e%Xg<C;egM;c`6N;{CKEr^<;5w{191iJ8sH)kelb?iBi+Y3>f5nYP%AW;Pz;_sNKA4616THl)JbOxfPw%Z#Y=02iRMilnv)*$1X5*=qXixO40tDLY`Bx)0))0zg-z%CW`GI$cjQ)*Mz+IIr2Q(<BaBdX3!)Wz6OG&YEutd+cd4@7;`Jwz=q&VgC<r9!tPss|IDj|Hj+19c!31oP-AP@A=;H3NZ8#{yM113H5_U-mmVJx~>9F;JU18l)Tjyx#5AB`lHyolgMN*MM3l(R$><Z3r|XKz-)CF%oDT3{;I7p)N?$>9DeV1}StXgPYfY-gSY7djYC*pn|i#1!=Vz#6@(Hja*`*D#;itAPl)yA*#AvNv}ft&pQ((ccr|O@{$eCn^n8Z?bBy2{^p|ke0-j6!g&S-OQa3E*j$4mXqeu8OAR|vp%s#DM&_!;`!}5Mrphz$dFq0v%Xpd#PX}6}z&=~{NS^KrUDVV4D0q+nJ*x1$)wnHoMTT{w1#1Sv!lUCOR-WIKqQWUgt>=;XbXV>B4gaP;<^bN;X#)pp=FvcF+4Q{mH*9Kc2M*Drflk)}ir1dQ4&Z5yeOxjB(Lm#9ppgV>K)YZIjKCMw>l0`*j}ATQmm>2LsJV>XCr}co$&Be2pmtSZra<izXsJt>NT4bMYJm6useuL+-5#KM%2xxR3IV#L)*c?Hs~nqVr$SH0w*(4H{u}^0Jvva)0G*wi#$?c;^Z&xr0iM(GJk@>jGzCvx@YGl58Sawj6qM=b8IfFXTvvdF=T?Sw9-hvlJiRtC_VJu6x%0T5N=u$*RVEw~8By1;X71<d5T0cTdR*flDbIP0Z$5dJHRv!eX_BI8$kT%wbjVX*sTAfaJOf<_lk!xP?<$(E@id8z_%(T&Tk-UC9i>Tl8a>ZFJZ*)iz3|-3<mO`iRFB2e(4yFkr%`&ZNkYmqfPOU|te@L?{#-m&Ha^V`o-wKFhdj+1Vveh+;dahHN^N)ppgJ1igpa@`AtW6tHlPvs-!EcA4-Wc|1r*Pl8yu*!#!7*zV&~CWf+JpbEgYym45+(?>-`v@HUXN~qC=pIWZSP-Cw-U*KK50-DLR#u5%r);=Ph#QJs@bqab2xhdEFnV7F`(%2fG>Gd-nWzjyBdNDQt#h+44Y6%keaD96$-RyKV{fKC)Iu)`aVjb!h)_tcE&dT7?72x<?>uQL<Rw@0I`#1N&*;0a<rVvUzuM1I(UFvhgAcIXPJmb?y7eZW&CSkX4}Kdh1CLu2;LdkE|I)cA6ERtO4iqJgqr_nsuytbpqMqyC$o~ko79gW5~{cEOdf)30bpVK<}08JZdq}eh*lawKcZ@tZIPOX8>z`ZNx%N?LM#ul(~e=;M9Qr($l~u-Sg1{){f(93$78g1q@kb>pSH-2lhf>t6amn5V*?{uyI|qOc8L^M{=FJuvXMf6|6x`0<6%C(}9xLum<ljtlN-=SmRxm64pnn6JQP6M!g5?HbQ3*E5NV@5S$)|HQWlTl2El%2z#h*19Sp%W?ifS%bL5Hc#dfU+(FfMbu^GsP5L@=s78cp$n4g1(kDWLrD5}uK8&ip{#Z3hF)@eggiwtj0TqA))7E_>rD}(HS`DIV+Y2lD+Z9grwG@m?HO+zgth1g6+LFbE$*oi^py~(SVEwJA;%6&7Ll9zsEz9IoH=71XRRgN}LNx%Y<6>E(sj4AVr^K&YPSv1PVa#PQ5(rscw?B&NK$q$ISmmDqN~)nkbvd2}Ks5sQfpNJ4cW6dG;8dfUU;}&0sDzK;GzIl$DOGrPRbUL8!Bp+BO2`3JZ4zU_shW!tGOT;nLUmei1S6@ML#gVSLG>1?{SFKob4Y)^nYSvs8`-_ou_mf8Jy2o%@f=N!qqWm@yRxUL{eiyd9V?&KBcawT>2^Y;TeFv0{Y_bM5L7i3su~WJs_1sWa{#8D-N=OV;ZWzBG2LV)8ewY3nWLYADc$xyWx92J3m{zY*1X*SrsmvCx5K*zOcw`51(@n5Q=(h@gxdJ)i;O2{ssYpK$&_Sji`EE`sRi=z2^dg6nc_v>GwMRH2>A@jR6m(Em|BwQlw8lBOk2gtW%2wH+@zS!$0>Dg!8FX1-@!B%Of|{W3}iYTevhh;Q>Vuk(L<&VFrANgqrTPDcY0JScLTC=W)<v3fYcuAM|~rtPW!#>+)V?iUX7LAv5wT!NTQWSXwfL^M-?kWqFeDdB<cqe^<#*JCeTUJ|1esS#US0%JqKzoKurPkAh(C9%ceDwU37=>j73lPoTp7p=;t*sH4nKwor~vNur6)t4tw_)5OaoIwih3*)AF3X?&BFiS9b%(;ihADNSkeY(Lf%;)A!lo89Mpo5};A>?eJ2&oB%pdz^)V1D!6fpqwpqsnvcqhx^Z?n+m4j*oK%$C57~^>(u{)U8IR`~$GK;0DW{aD4l&$)x}6ksM%hH&>c2A(-r92~+lNxbm%GVD*yU9ZqL_Nl+rj<ZkJZ7L;Ux3?I_$7v6VZYh>_K4eM5onHl5RL|K~f#M%=^pv#tzdc989vZS-1ebtM-sI4U%S<FyU@z_uNM^5+n^mQje1(+~=6=Ac=QsH<z@z&ytcUNpoJ3VG@v}oVyJOm>Hl64#P>hyCi8QaHzf#Ni{e*ek@5JYh!YbJtQqjQiDMG*+?3^wrU7Td$E?Yz`Y`Z3RN{&T=4iL=??6Wq$x<+)04D1PJJZv)VBtH$4j-3TGKTng#^cvbo1yjnJ2s#k^v=Yj?K`FtUsBqL()}9ZdFntA!#0;WE@Mfblz7$(CPq5pOCbtC26&pr6eut5ucLWs-WF)lIAYg$zY7{i>hrT^@XG_NJ5_(by-&*zD}<)Ccj?09iJrLPF-C{hV{msk~Hhy9iJpCebgaI4fdLnq`T}s2a&YbC+R1n_$2d=-!tf-zEn7Sl%&7xK93(&bG|Yr&CFgW4MK9;ah7ruoMc%0fj>IQN<H&5#o+iPb=GZu28s#;`p>5%?Ru&_1<A^ooHek~zlrJlU{klc$T0|9pQmY_)B`!b9}Lk{2Gis$-^h`I6^cZ)Exzy9cIh9F8=I;N>r7XLXH<jjq>2}Xr%7uIj7dTv1sIZcHOFFA`>|R^=XB`vZh?<8?9F5cR@@(qwX!qMQQ|k)?)Gg9k9XMZd+E?LuH^o9RB;IqK3HcpDLo1+th?I|LM2wSHdh~jRUe9Vz718wqB_oS(5QQ)s`aF#RNL*;HJ}Qu^v6@x^I)oW$XIo-N|bjBpn9rfR1Ki2ljijUsK!I7R?PChUVoGwgB2Evsw!4>F09j7s+L7nXZ^s#+8=n7KdugEp=t=K3Q*Ozpz80Ds*29_Q;k5wfl*a!m7WGv)kv!5P^y)%@vLDt!6sI^THFEiMjESqK&(o#1ni{hDpWn7szGU<0)7Wis#N=RTeM$qQ8nYJsza&PRscKCQmVR1Ro{&2bSTtH*y?qxc2UJzv0G5=>=PkUPE`-18t!tac0#RN984e<m_rQ-RP}`Vhc)WIL5c}fy+XAB>eA$XTIHSU^8NEdbzaLlJqBQ|5fZ4-6v_it$mTV1HmJ3TRa8;hfD9T!<WON!d4akG0TxT1aZpFgXU&L_>Z}z&)rBj>7D1U4i_Hyc0By1ssN>euo};Q6N42*9J3HSvVQ&W6Wp5osov<$2<Hj1ZGyaj1_Q!+NHISCCr}1nvcbK?$;O`%Y(~hKR)G(Tk;o=T^v)im^`>AO<XZmPT_U$kMYC)3D9=2wxku-scqq`E#2~_r4kW7L!%}HoZb(*%1=7c7YVV$%FHbq<C^>fj*J80SpO&E!XG%cVxy$_mRMswL!%50G-Dk@<O@Y1>dTr_n;)9QIJ%}~(PNmKO`&~&y!^Xu3QeKhBSrUq8RSEZ@$XKbqBG%dJkV>DILKmAE_p=rQvr?g|wX(~Wd52QKYD@<$mz=Xx<)6HN`N3WWy0@Kfa>W4WMFm(cRs|!>EVUCt3O)~BGbS0EqZZZOt3ZOI>l=Co@;p`{_nBs3^utcd&jnb$|dI9oiZg<Js#tfwf?EuE0^oOFfwt_NvC62-Q^}L><)F4g1p@e;89}FdK4!l;z%?ZhA^1hE`1Y+Zj<kHW00&Nwx)1|sgKN&Ae-K-?j8~HSw&_^<W#$FnDbi~ZTY#}+Hg`}^Lbg_%1yO1=XqqYXI-?-j{AW40f&OE-;GczBP*7lL~AOj0YhRl5w&Tex8k~P8WJWp{CNnN;%2Jm0IZr<B`KZN8!JNilwc&(HH);zb!aofQ*^7VRZv{Q^%H4thFkCWg&n4-f=`{&6*gJnOcQ+X}9U4o_&zs3M0akFV~o>mCi`Wj^DI_L)!sRttG?UQQi&6~>~2U(4T?5+cuDp@a6;XWy@c5866<_hp=knL?Cn+9YJO0C^`rmA@aydEsx8Dz_X94n9~0C}?y2&5VQ{LUFiwD)<9@zNzp6^tpH{P=De<3{-tsBtlu8W+fT&KOS@#)>E<e(#L&%J-#bZz-~wL8{ZP<*+p4a0<q=g6&-V4s(5)v92(Vq*eUEjMcG>OSAYHFxG{S17xf(%>W@|JOty<!8mDM=><KiC$yJ(jj>7?8^D;Vl(Ub;7!S|P(NCR>%iiiPW2_QeWty=%0pn0%JWrGEXN*<PmyEZhsx25#Bx8NAjGbg0&$BiBiymD|Zwto0$#@=FtP~GstVS^o1>>@?RsqHuFotWzG@h|Pma&;?QDW<q6f#~CJ|&QI6NBYop_4-U!I0g-kgK8ir163TaxN%{RmfX4^8(qfc;|sN_}U%|S(^%EW1)Mb7j_<pkOMG>Ng+emX9#(#(vJ@YIq*xJ_aF{gRek``AC-7>SWvE8Lp(&1txtv675&~lK&g<>5QRA0r|NwSVrxJZwBTHkb}TpG>zFktfQ4=DvSOEr?H!7@WrS;o3g_J<C0y$X4|7dh5x)kKoJHV}6ZVfq7`@|Z4&j?r@^^5Uy84@&i59l!B%JaORL6fXMjL92;ygK-Hw=c$XZdvpa`Pdn;&+2Po%ewC1Hl?!8=uOlJz!zx(q`fYTjb-@pKugd{Rm)TD$Nug{J8<QTQlp!>imxeYimn^z6Mxb0qfUn`rCMZe6X&%X&W_<0;^H5Q=tx7l;1<Zjt<63N30qG)_~2Z%&IFkSTjsYJ3MeT46GXq))Zjp3Rry#u)2EO^83J=HGduxu+aEyyZ(C+pw;&oppu?r?UhDs4Xg!V9S|;^4Xmynx1t=Zt$@`9SY3eKJUZ2Vx<?Da)}m2v=5w`duIj>70d?4wxawoM*2b%yynw3)XV9E$00na}|2<tIQCs$KUejBT&(+knE+3rT1Gbdb=3pZLYwsVdm4Q`P;<`BoxrD0+T*E3=w8=tXAIeDn+FWCWt4+9um1_W84e&u$L*fLZ1JLsztdpc!p9XiR9IGj?>I>EguxemO?eEa3rH(a9um%&X%=vf%g=G+{2H9<h)q@)P6l-`WtX_oG@lOLD!D<tefh9t)V13IrO`y&}14sJD!s<j={lp%v0l{j3<A7QN-OJjl*CUuku*N&YI*q~VjRdR7um%LH2Uxf6GZuVj5xvAmGH$}LR*$YBQ6IOs!tTa-+m4c}1za8Y&SFgeP+YANt^$I^)n=`@18`f!uv&oC17X1Fu|{k4O>_KlaA$a3J;7T%_Ea%s`ieqN)8i!hkLEa6F)G-r#0+vX@Sw!LbU8Q-sT+w@q5f8{MB(Mq?6xj2iG%{T@jq;`tE&)=qli+L{UIT0Gh+xhBmi=+M894sT_4eju<cKKXIs#_e5p%*e4<-2Bou>`jWjKfpDW(|0U+HZ5=%mFaiu=dAiWAvLlB)1qUzj4y_Bd0&fYmuRrud66+bTV`aTg+pDm<eHhYNTJ+v318YSvaK{Qr~M&$#aC=A8bh(@3wDT$iX5LLs8;zj`rQJuBUR+rWENwii@Z4g_4&8DSJbaAsjGf~w=bZOSgA*#WwKMzq|BWfqrM-(sl*O$Umoi%n=m&n{56IFx8sDP+Lh&t2^WV$4eaH8=^6e+vYWH~=1I)Q#Z>XL_l5-n>*bx~FhYxiS96t)65JyC7EHa$d5wNQUMk2*k9Cq(b^USF-sk3yhv%n%Kr_1RL7tFs2riga6hOrUBE&}DAtCHN{SzukaZ05qH$XwY5Tk^*58Sa7eB(g(9nc?-6saF_9BH3(>8+hf?p-wO0@hvoGusf4oYKJNfff0sb*7@%%~>2=;w)UF4ovYK82xb9*etU=mc4J*pMQ=q|y`Q8)jQ<uO1=TNIc(!s?I#C)Z!`s3p>HGC1+I?aM|&XDy0pn3z`A3iU{SDl8F@j`qSh^u_&eQtmyh+U<|hu|}}!58_X&lLCqiVrs5F-PIk1MyYLuCx!Pk6t9{ML_Q!k0e5Rm1YuJM-#Yn*C$155tLWEOi}=QXq^I|x&}Ry(6di^Y<jt^_zdV7Ku@2Uo}WO0iDcoMvZCGj!YTky#Br7T2h*$hrRr#vV&b#OJ!`8DspHdki_Z<3x(*bL&5W9{v`*}f>Dhr7jyk=lMD#*IPl3J(OZ5_@r|<B<JcwR!z%oxt4|a`@2t9ST^rCR#t6g?uP*$|?Ew*HHhA-S3zRn&gvZ))U$fjpO1{u<GAj=FFJ~ga6>b;)$CSjlj(t~yI9#~{Rli^3B7eou+?2IVN7n7RzoZb>5*j(|<gPr*B7Us1`!Q_G$;S0bO7&?h9_<ZKpXph22##zje!Dp2A{1czc9Dg0KWL)}Z_{>Dq9(7skqc@4**?H=Kmj;-jcOWdwx^Cf1*l}bT15fj}+%k#b5<^>8fp@L=s6Kq;IcLp-!h5X=AD;s^EqY)6^Zx^L>NQ~")).decode("utf-8"))
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

