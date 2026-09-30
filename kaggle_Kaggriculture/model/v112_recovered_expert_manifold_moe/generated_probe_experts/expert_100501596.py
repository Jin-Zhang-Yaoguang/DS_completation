"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqTaPBmai0InT=zwuGfQ_XvPCYu<Pf_{4`gB>5Eg9-hDe*DFAPEd-80j5h^&l^jL6FGRQ=s7n>{n#Up<w_h&SH&j}L$R?|=K(zx?^%Km6Sv{^P^{_~T#y?N5LG^5uu$efQH(A3nc)_?JKa`Jcc3*_SW>?T>%`Uw``Bm#_cu;qQO{kN@<$A3y%`_rLi0!^?+HzkdDh%m2F1FMs&(>+gSj{g8d}_3!@l`ufW+fAKf3KYaY{hnKkf_WbYt^6l?_`~7de`{BzU{PgSB*WZypxcCt9^XLD3$sXkUU;LNf|1SGs>qGtF!>8Aue*X5ue*5vqpMU-BtNF>7FW`gMe)I;Q`$t!q?tbUr|Ni?Qe)&&d{{7Ft|Aqnl!tM8TJ<Jc^{o-}Sl>Oi@fArg**Votk3;yBj%gzaX_w(zIZ~wUX4eQUHe--hAfAL+N#P%x+I>b+0{_b!F#M@)RcpFoFZ*d)u;5YFhmv3+Rm~SI>`*b28<-036Y`<Vb{?o_b%irPrk9rXhFRy%M+wU4O1t}`)FK9zS=HQ`GQNF(N;~^y4A9VRgD1xq^I6o*p9OMHR`G8{v!O<n6O`>y+Xs$h+CF1ovG3otD1b(=A{EgbQ85^?4&o26N14jO%%fk$IT&n%-{Uhksxua(yZ$lyfg8CsJfB50`7eD{gKfM0<^Y=e||KGm7q@$k<S;sp*S~)hc)6$)A>icNKp#|&}wdJ|<;8rZkvdto&wd?wDfL-|`yEdEh$Gm-d(FTM35aiPz{a{UG$hutokYE1z@pt48nHO&IhhVpwpI(3XdXobW{B^m)mO0y6=4|bZpYPs`McnLv)!XCKQ)hqP@4px}&vH$Kc8Bn%pMU)B)8D`T_~Sn!+XeD)>z=;b=1X>*UqC-DXPodq@g+9;+HTB0JWJMT=I*`!*?pUmXm4w6-^i+8?seQLhiq4U`yOw5n!h@@wO<Hg^Rr#*5VR~nV0y!KY4`0ehJ8nc2F2}SRfKwaFO`zm0=3mwq9UEUyaXC&pKqT{8Hcpv?+^K4&9~Qg0uh}lct;v^eUt3Eqaw`RCooqHpWDy(xfKhJJFIQG9Z0?E9b53h*q3a<rp4TgJ2n_>`5#59y&JLb+0=oCu@&$Bb?31KTre)X{~jJ=+xA;*#Ik)3`$6req(Zs-kZbR8U>B(D+jglBQ(b^xxH}B7RiiJE@hrq1%Ll^TW9OaaV%Nb+?BO~)ti99Yz@;|kHD&*ckDpk3^7@<Se;~TZ(3>;zr{k~F1B1Mhosqf-O14I7_ZhTP?{i7_z-pgd`!b5Z`|-c>KPY;G{+3MpI*hZYUVm^krnY93noQ?kON0&&z+H1_>k8j>lLmWTEp#f{()$7>$OnUOc>9p(>*>)v^t=)3ls0bGAj#Zju7Et<%H|4rsp!c=m4_2-UFcGVAm=_t6lnfO=p+#Qoc(^~tD7)#(D;^*p1%+GJ7T|<-?8nHQ1}b;PTHSuU`EhiIyZ9uae(~RCGPZ{k0iS9_dXP*HM-QB8UGYL@qAi-*z<Pa%8RVR)$bnB_3?57<+fk_3!}mp>wyJRgmL!u);nF-?)8hxeY*UM7zEL=XZ=a*nGcI?NT4#qF6FZbwlL&(?EiK1s}3Cl>(j5p<#^hniUw7-l@GMvsYPl0^7ykxP_|Eje2Xs>=?mPT-$7VQv>>iOeDcE6$W#tff}@%6BcMbo?|$^-m+GGVNHiCG@<Rbbb`+{7bJQp0EI+Wp54qQrhrA3+N=eU9&GXE5G@(NpN2@m2fez$ijD4#k4}qV;K2;B9okz6FafH5u9g@Oer4#kk5@)kPN5v9N`}FbSm&Ga6o@F1YYHT>mPm_ui<_}ZsSM_`!Ef}q?M1dJbN76G`tb1R;fePg-@kv(BBzsHR)M7lPh=t5cG4!#!SE^O*qruPL{Cs$Xu=uKcmHF#(vN*-M0upCe)_LlUg#m#e^6iypiF!Q^evqV&6WhcUW#7I5^sP@-B5MkDzTC%t`9XNNA?FnFwwh~RIe%-nhQ6Oq)D989sJ_DXFAZ<$5c2oS;tYas_lhpc<!Y3WwD#dyv#oi2Cga)2@93y@%jc=P&iUNnyQ2BrSB8z;GT=$#wOD(LzuzMRET=qjW+*?!!NQ;IpRY?Mb`sn#0f);Hv6YitXWl*@qgb(6P>{0?_K20K*R1BDq-?cQOhvU-p8kbpK;?o`4j3#JdYwU3dF<w!WsRuq+=~Ae>;pC5EoV$sZdmmTocy&?Lkw9Pn({z?%&jNGMWwz431(tFq^{+HSTwmE(l=wI9;=A-bdKoPeOR9=Fxx&+|N2<|d?asz=^cwTeC#TTo^>jpwQo%%GY{R1FqPtHE{4d6#x7C3$|+K}S`~fdz#C^9v}QnHhd~`|n;FAqEoyztBXy0<7g9aF*iO|iHZ0@?xA~FVNHig?UjRbb5JYB>3JH!Amut^Ee0#P=fLqv7ZbZl_r_9E7ozR(aJ8aiw{=H@po|vuV`5D<XMA?kmR23YsTG4LF-JItGaUdtrFWyHoBIT)}>!Hixx4u;v`b2J2U6n1!uVcT#%HOQyRhm!Ea!aGb`Nh!$)#CI_fijwj+_<R2X-7R)ai7AD^W=iiJdu_od%#>T4>KKp9LPZk`N2H(kLVX88ww}h+f#^)$cB*97^znhNkx|O4Qz~Ucb$3wUn1P4^C^{~Q)a&Qf*_d+iS(80$#3DRonwY(<uEIQzI)M-JZ?Z0qf{k9#D|i90*V15M8P7!%woMx9`vu|ORBo2V)F^oaHV)H^JhOFD&caq*bVv@(QmSE3chLpL&iwUJIuP+RWA=%@}&Jck$Xzx!hn90m-cH;IOME|oM*^uM9-Sbm%yyJ`2XZcqLonGyb#4!LfLlvP>H=>cyz^L`fTwIaj@hc>eqkr%kO`Mo;zjZ5dS3@hW37aT*^*5_Ar7^x}n};P1dqNsa%RmoiuXU<X3&M76`m-0l9WaLJhPUkFDu%-asTU$`{b8B%pF1$hz87HAe-?2~m>dq|W)J$f8IdV0#K3NG&V68g>}e@<KW6)sU}kYP-d=C9yThJfrr7V~y}83$u(&M(YLz<wH9WA{s|#e>iR05n}RkfhZ5{;SVJ#5TT2*o3|ld*}eInws!b;0#OWgH{#u;`dvWzg}4WkE6iRNR$hrvzyBbTk#?N|UkR946&Dt72-2&Zr4&@;L)GOKyox2}3+#yy=(bFOQ}V(6s_&4GeJZj7wRxE373UV3=ib;ean2!g4KI~bW!GhzU2ceQr$2WqzRRic=?gozP77FpB465t93ELK)x6FG&H<!2harg8ry%T2E7eleCBOW<JOwPfLWs&S7J>t|lBTEphpIb6VhJ@7FXLm<b@NA3xQ*${4m=_JFwEPad!=VLbwh1V2`tuD-p^2~+Z!xDDmfLX^b0KGc<K7|t*OwUi99s%1u;Jcxn!5S0#gJ`y^H$H5gia(m&WogR624s2Q|T*`tZ%MLsdPJn^EBbMhObAFeLfN2M!SBDF;0ylv4p4^T;~Hs=kDKS?xUCm+M20MTipuwR&Oy5D7wIrJR+Wx;>@kn>AIW!i-eQ6qtwW6Bttyo%?8H97)i&M4i=&&2m>ypL@-iXxEM1n$R?-px+gDW>udG6Acp!DOuFPGP+=t`Zd?Lwr<ky@;PO$f#Xn7hCz?WQf?hK(or5a@>S6-wg(c?mi1>8YkXHAiKjsL^8SAO`1Aa4iN>;c%i6}Kv{1E&gH%*(id-m(4WI>{D|o0i8S2}a8$m5{OtH^@1eHUFSVX@js!1kXDPP3qf&2zLx;q#~W@xcULC<p|?}iNURiBC-G;7r#k+YDlk!k{9o8ut+GO}_=s#y59Sn_R4oc%d-NLqteoIK{Y*q%FOb5!t;IWtKepGox1QTz&+Mg+y|QJ=e=wj0uz4K5a)B{n*E11*18wGv)*N~C1QWUvJ75Iuj$`H<0?cjaFb934$-64Az=$Y(&lg$^q^O3L1a^wfRbElLx>N5&qKE<~noy9gevT{UBZm5)mw3I&A@)ML`C3%zV05cn~0M#7Cg<q@X|IB}{i4JvsVi8~87X2#1hQx*HjNwvI|)*{~J)Dng2$=Fz_wxD#gs85!_<y0St(l=F|NEp9#KPyA#M87`1Un<hHpngdyqxHpS*tWs;HeBoA+HH|QMXKA274dP1!PfN3D<^^f+|wGfOzM)#C{EE#hi6^w5h!EhrdFBZ9VLAmU4GBVO|M?o#IdVwV3)_`-1Xve+)@s{e5(=oWXFTpCG7R!9HVu2Iijg;m3j=JnQr}4_Zi{zl+)1iCaGU9ubc{XQ!Nhzl#K!NdfHZH>AIlNiUrD|V*!;B=h_;#5B=p+P+9usE=npRI1xEfV1}B9q#6&uAs*?fwjIW>`9$4$(ZaX(wUA>IqIol`G5*MMx0b-L)k17H8g+k+C#$|`9WNRc6xi*8-4W}6ppd@&^KQ{y<y_@rLyJ7{*Iv6Ha4zH1acKc>H%4w!$g3wKk<(|sffsd&rHY|iq5rmZ1vj_Am^dWRJepl^_0oF;7ffbWVHROQTpOJ6vmnz!UCU?>G48F19Gvkp-!X?So9S?R;P^cAj<1x)gK7-(>9uM~!gHoLChVfy&Qztpu3Zzvy1%cF$h5(*lx6^*3%>2aUcRXE7EHV+QKRDDeE-9LL1jb63)>^3^yTk~b>Ww`U}oR?%9l~TgYpv+1$D)!7}rMnhFT*urZGlYM5+YZe%TBgjiFi{A~;ct{rBWn4#;Y{fyzS>jCM(s7=X6g!%|r+zY6yC?nr8%*+)p&{pa`vuc^W(6Nyy419C=eW=VJo7jEo>idzjTZlsE&xKbfzZjyboJ2Fh^Ps+^Fippb~cfX@56jGf<4kc!NPKU&V_xsDgRlk&t6pm1HNgj9PkK}k<4>B_U-VCReANZi6gN!?~a@EAA?^0t>B4X<Ev;uL%s+C9&E7oT%6Tj>Xvq=Zk3PngzhWHaN7)y>{&c|<tPg>?-gnMbd^rz3Ol{kbTmqY|=HS*DG@=5zDU<!e{wa@N52ZAcq;6wO)1UB*6*~UODXU*!z6~BvSND%9ZRq9sw4xF4U8&W>m91TYz2TgOEaJ|UEAn#PyZVb?>K5Cfkmw_AXPYkc$02c*}!{zPII))i*mzP92#)Wy0h%02;1YU6s<0Zy!KQ$~`!1M3nTsoUCrCyHA5@U+;!u>aQ)>x~4ZuUij3^EXx1v<nqu-jHyh)+&qI>^8g@An?eTXU1VjFB-MGL?)EWG6`4HTqqU^=eGv203_L|1Fp<!)dgoz=wLCeI^t>@>2$31wh`}Yt1bL;WfV6gxmNV<jG1k(heeT1l7p1<0<uXzUHKZEA6oxC7`slQ7TcZ9CltR1FS5>*778jX7-jrRx4EQ)`*)^E5bL4q!Vlkl$Z$#FVrUzboqtDuv{E3;f6)_w&C?N#m-Vq9THymuOvSEtVkpk0AVI%s4b-Y#ME}jkLpmB5o8vzAx^}HIX{#}o*?*|K$*;j?{7s%ez4_%sb}KX;#rQz3#F1HUo`S@52(QqtqJSn(}5l`rHwrRQx(?|&F~gPLesi_QF<GfSL@PcsP0lzhL_5hgLHL7He}5(1zBuY^yfRNycuYh+^Dyy1crFAsDtsQY(Ua+Cf*x8s+A$7uH+=;#NaxtMA@FoSmhCsAMG;BrAu?DNO9|)#&Ndh$r<q#O^vG7Da#_H$Gi#(e!Ud7YRSJ>B}3#?+81-SGq%k1xVk(Ofn-?}qIRR8hH5>I)x0F?>dMBiHR1|*cpbGnZt&$nUQ%HMEvfb~3gRk4K284aSOe;%8ZduBE-o*-J<A->0|AqeB9fsc8mCqykh+uA24!`|Q5v``ua0e8<;|tM<a3<HkLu!jZff*bl;{2+H78ZA*xY}bq2Jeb#l|w^Ux@E?D?R!47?iWoHjMJ6KpbQiDd@`P)@0QrJ(8#y!D`Y>>gkX>aARDNtww0`CM15{Jkz`lDMAF27<Z#`M-jG2qcGr6)>_=P<KZ2Sqxv1<cvsSDbSrJPeqvsNsLpIGYx5=S_JZ9KTboq-9%U*^%F@7*OaS)DGHYAy@<I={R6&M4z3w58mM@!9JNiaosT_@E!BQ*0%s4F($%XcXY?r}q#Ve}cVNXEU%$1<pk}_~c#znEyL9_3C`F2XJI8ob2pGc5^MbGwjW-A;tl4RSVIm?XR5xtvVivCp8cb4JbA@f4UYOl<T5puk+OO908A`WqRa?PoU+3NeGSOiw82higqnO&lvy5B5~q4lC<?c$TVJS`#cO>5qV*vEGCFY+9l1VtIm7E!eTDCLGpHs_O<93NDNy)t4^`NMVGwejI^1TAE!^B|oi;Ckq?qnu^HEHJ~;X1LKN<KS3-c?^|S(T2HV)J>oI%Y^`|7b0V8{HO@;smRuANA6^-!vHt7P2?6jBf!(~-4gpywHp?*rvz_YS>8087|V)il96`hO$3#jSUV&~$Xk$r7u~_4(FL}Q{>U;`WA;#NguM#%F^oNDVkLLVh$r37l{__94V=ivx$RNSpSWx_mcS~DzL$4&)o6W6$`^@F8dmRMqHuUUbYXBeZblzX`W(yj1_Em%GoeWexsWcV#S<}#Nu?fN9Q`D1HC29I(%+a8z%cj^LRyb>Y{|sxUlBupc(WqHt4iv>EVV5v*JrwD@Th2u3Ly!bk+E8jUA4g&TjlXOIO5V{hQ!jt%btVdb6}2p%y8Qskp-GUEz?W;C}YfU!<pvUl8zV2LjzqVN>yttwq;7g2>YUg9%q9a=*mMZ?W-%&3YL_U@TLLTZHXr+#lu8~85ByF^;~bdSyR%p+A9?{Y-=mb%EKOlzNKp*<A9v|F(bn*(xs3sib%^Vd{*J#<?nvBXC<JozAW`+L+jH{I7^$mqRRkv8l=uqeCn+NNp5W+V=7Z7csyS-K_sfRA~j2Rc#)mbXN4=(sQ1mS{E5WFM&QOoJrw0ILtT*J`V$znBZ6lnb1B%dW&PyH^D*7^MbB8-Es*<0P2xr7-;mGFlb|$fUKj!j)2v3PJ|1~1WbX)$Q7BP*EMs!-cE2<7Kr4@RRfU7Kvh~J%VU-;7;}OlEDq$f-NB2AO2IVU(?aW!92kt<-pVge#t?Ui2l0;TJcQ=)f2SZ-<;B(#5of!u*_@ST@b!;(0-+NyujMPxb;(1(4Bl;MTD`0$Q5DZ%l(OMIxL$%BqtZUK`w*;8xtme$P?WTzn#Grr~ewkvs57FT<LOez~Dw-n&XZT&cZOhE7a%8@d?r7d8c9R~aqOD~R!%%(jt);P#LjEDohn`GBFuQuwYb-k8DLWPBz!8)mwL5jQuf?Uf2d@G`f-AJ&6R4bMTx2*C7^B%A%H!JGQw`L|IdYW(T9)$>HTF5)@LgTGG3`NF*habxqLDDF^Vz3Y;YD9NPC?=U(?xtNk>!ZXTtMDYP5acotk4S;QBhkiSE#Fxq`x5T&LWUJA(E!%j?8VZB8*<wVv&q=i<N1m*dlJ`&REgS@qDcq5oET0s<~Vft6xq0C-7P%p3`<K9SI}xb~71{Bwr?R>#w~br4S8oK&rK3bwy*J$yED5L(cEkn``(Yl0Tcf4Ox!2N^2q^O8`%qMVXz|s{xr~?rntm&jR6J861H@n6h|~)zgvb47Qv1FWk}ux}LN4u7y>-k1iyu`+PMeX1zvZcIcm&W?&90;p&Ua@%j%_UCP-0VuqI?=<Uo`s~aKp{sPmnJ`YRe+)<u&TYgTpM<c$H^@eX5PVo=E)!TSwFRncrv1-EQ%##<Zx-&(8jEgU?Z`5dtS}Syl)sQg^G+}*%u2n~Ptdxv3U)lvbyy4calRfN$#GgaF>x6i;kXgENf{ZptYG^ibRFp=CaCqkg^NvW<=&9X|J`%5vvCj2L)zE$fNP4Pel}KcN1nmivVE&i)2BbMw-G06HaPo5PPMach<hF!>bet6b*Pj@cR=p<xY!Q}3AR7<<sn6YvFJR+UR+0%P^fTtc(@}j6v2no9{k5_qqJXN%Q;4;run15-o0P!{VW&jx|Bdol;?C|7*MNRm8?XI2^EA+IWg&{Gn9rSJIHE42-6x=F^)J|Uyg(I4M&>cSWV_;z*wK1~qSdG33fx*dPyOyrMF?64xpp|u_5_TPSF(N!mA6s7I9dmDX4ay-hl*N7x(5!oS(&I!92dJth|V<is+<6v?G-H^3d~U(hO8#K&vpzyS|cGhS}WFmo&(20mb{H|U!eR6kbly3DlE6AN}-k{pwO~duKx;2&q&toP7)-*uG<{@BUZ5Fa9{UU_P7>l5`+$9g;x4=e+PK{on!H~S6<avBVx^&8?jI7)4Hh2>)z@C9GSaV^}+b_q@Lcd456AZ2v3Kji$aHo9qAvGEn&?PERJxD?NZK<kkH~7Dyl|bTN+zSV}#)o#eF`$A(polntaQ)t(s!%G33Ld37mek{9IKt0Y=&tlV!<r(VW3WbLCJY?JAaFLwS!x6cDYM(%H;{)X<@EXu3R^6rJ)~1Q&|3nxw7}P2iKS_jr%4(3ONRc>!n#>w9!TM$+Y{l{aB07pQB1$Zu^(2?krcMdz@2)l99?T3$F)w;MkdNu^Fg%zm6by?l7HO*72-$y%OI92aOL7+AY4F;xlyH414)T4@{p${K;l)KC>b)_SJy3CFa3tB63^J;ciQh^8y(+T42F2YIFIGdB`-%vXH(wW*hE0zhSlt5Fj+1bUKi4E&`nGg&z&y0}(f)6>6YjD_sE(lUNgo6Yi!M~)RTHi91><V}$;Y|PZCI%U5Xq5FONro>6RBAZ~_sECxLbFM_}L`uhuXPiXoKoI+d@d|fpA-ejZx;6Qkg#!&6Ff#JWDyKhi)TXb3Tz^R_DA9G^=GgD>1*7Qw?nq;nemgfo#m+*4-({UK<LKR|Dn~;S@w5C!UNq;~M^ww{?!dhPBZrO6s-+mUWtlP&sp)VrtGi1x)>^d4yxGL_mC^X2*&~)0n$8@9jIcZg^EW;2+)9~8^Sb;nJi3{tOB@3-!_8%*t9>nWS2rgk1DWJKmfpLYGl6ZI!tZp*@9bh)w+~VRu+^m%s|7V6YT?e`y#Da<x2zgeEUnRSL!*ot$zvoT@MYWL47x8OAq48UMUQ0Jl%*^Eg5Xd|9zeJe5n}1$xQM|K=org0?FpwZd#%IQvei?K)5Wu)jNVtn@}l*4ZAxOK%&EvHk_Vy;6hH0d(8%cDwQm^diCI3bpvi=(*!z^OrENWJ<Hbr0`#EP6&e?^WBGjl@XE3r<lx(<d2wCIdY3|2qh}s`eEmKIkH+$JA%aX-|84umz-*U{ZuN}psFS87lncT3XR4tZgKVcID4qIB2$S-iDviEXXXpbJDQ+~*mzp+eldQFHL5eBYtkDwm2J?Yp!Vh9d2VBYA*Mk-p{d?^7TrVZwn18{f2Mu_$J@Gav}{13#^MRpEehM6U6^Qec)sI{dzj%l$USz9Kv?Pr<h9j||+4DcxL{#JGe`(Aq-^M!fHmcp0tQD<^W)becv9arZeyL4j*#-}0Gx`I>2N0u5<3cZRBtvU%B*V?wx;DL*-KHiWGeO!K9V%DV)K_n7IRiBoK@HBgCHBJRoj}c}hi?h1Yr#$`w(b-||$l}WG8iGvaGI3QV1PB2+m9#WuAM;uxK&I}_O7vPpa~fW*_P9YDKkdQmkl6k{yS0&Ps@y0AA9|`NI;3V1JzNF;_K$j;YeRc1ApIyvk3I4|mmMt1a5M91T+fVnn&nB%^6G!$n6aLwi<~HH5;*3HwdiV*ETfvlvNIGT3V=VoN+N7L3E7CIuuT&_D$Cj3uT*&G<#~)XY|e^5Dfjl9Sn;*%u!uvhAS&3YfD#n^9Vs>K^vfgT!!2<nS)EhSBw#)Q{P9aSe2_ce@TQ%}|E?@qZP(op_MElX&hrr;bJTAN)jqw7x&R*wru5j?)fcf=#}!gy(`QkK>~mz}0@5I;$I;OXW*iX=tjxQL^BGIA-`2MwS#jU*Q`hQPOPfzp!=7>P=5B@MC~1WYC}(&o_&LOa4yml>+a(}3KqAc4GHt_$zZvXIM@5jCS6iO6t0o>A^?gioV#b@;QPL4?LUO8m2U^mx>Tl3%dKvg_kJ6)FbChZa2{3V#TpdN!OtJOUWlYC1&nus>ZV)J|Cn`TRx3aKxenyltMf`wjXS&yFGR@iGOH2aCxpoh3x*==1k1?ZIUeE;M=`~kqtQZDz%o@*HDC$j0JvD$J?<@9t29EKN`y^Fdyf%t3^P8>d4JtKE=EzckhT%?a63YW*N873r_w#-Bh!rtwE+esiBn&c-`-&}HPyf|c-nCE~Q{8oHPjj)3ti`8mU7mQcxZ`3%fq@<WT{KEi>8oxbyExFfwH<VBh%PAj%{CaMDua3DVm5fC;?-@3emFomC8p%0>aU6`BZ8Q-dMiLl$$iKw;{HajEbBVH_LUjlre0o4yVN1jq~@<AbHJ?Pl1rLi*j}nUxu?u;T=13L5Gin6^E+gr$oZojORed{P}3c642#6}7?D@GMI55TX-%cU4Px0%&bbdK--b#L#fIx8SNu+%3piebO!+(>wX<batKk?(@>R8RDL$`DDaQ*!_Wb0H1&Q0x=`5*z1;h4^rFX`h7r2dZ8-)aD@efkhS}d1XtOlQDsx!XcR6|n1SmJa<ouPK|Lt$i4_N0_!-5Mk#UHLw-8s;`1B~XGM%y+S>DB>)q$fTgfab>`ejD6BsQD%tI3dK=uABB4hK$f@43l?>@JL2%HTPPKpIiO(`#<!@d3Rx{^?ThXMB~Q@9H5VsJJ(&he9O7)#m5$aNoN$4-T=0O;kk$h{%Ug$SQdC9?7-Sw{^C45B66c)780w>rTDn$HmUnCIUMYw$KK*G}Hg^MOBV*Q~XGf}8E&ep+U9``NFMbwzbPk$Ff-5P@yPLB*)*kpWEov(T)wC2!AnD^Bk_GREE<|Ik_oA|7R$B~~{Fqs-%n7jzO6Jg|g{q<DiQhP(O}a+G2!u(WrB!#_0D4uQ#q_-zUuwti^+OdKG*fe}6DSg1Mk*Og(O;u!M=erLmCv?68LFCU){63UxMaYG@6~AA_M?Tej;`?~J6RFpDdaElJE#VRw&U&dPqoL}ouOL?eZB&mGH_~i^5mWdt*lXbc^|<pTZAbW)eBs%1$U}l+{iBgE(11PPh(cq6FuIfYFEp@zLb>cBG=8TvMf-Qz2y2RA+}fFZY*2AWn720d_<%bJ?|A)69LRnYpM5x?<z442JhNdO&Wm{Jst=Ze;FS?e*Af<%14aXXdh}`QTk=A+bByhmYZAkhcjG3`yyWDO_~h#HDV&Nx>P}Jt?iC|EqmNNyxN^?(MRM;Y-DdzWE#iMm?Mu2blyAnC-9dLXFN{xhOy3E&AyL>v<5s2{fFE*#i5c;RP4~WG>}pvvQbFgJ7}aRl1vgHxo$x}&w88;yg8=y?jl`q=}1eN?q(}m`NtaDK9-GWj7$64Q4<Q`(e~<>lw%#5W>n-4JPj|*!5^T!8)2<=0xd9-Rst8VrN@Y|@dj~ChxvR7OFrIPX_=;eqLgFc=ZO8-93uHJ-EDX)9<rkvLUZyGDAaPjphmd<+-DbvY3uiqa>46m_AhV7;3b0m-gdvAI1%V_2cj+}NM$EubxHy)@gRRenWnncRj0R`z-CodF4znO@^JS-e2b<EUa2~UT{F|>vX&|r?8whV%Cj&0m@TUb6kY91=L1V0Ie!0`F$o>2xe>XyQwDO}d?-0w@Z6&7>t6e**=3epz|Pz8STFQ#b$3|LyO(CqmZ}!CWW@DBEQ7_!pHaQTS^a$RfzNPMXfqM5u1;X4ST+=4>P1VXEtzdW3V8SfNwXeX)8AsKaJ72R4VQWSVrip?c4_*B^`is(G*gWtI7S{LqR)-oEW1S_oj_te*TH7Z`0=2)ZL>QHG-}g%ohUEVuDQ$^)SC>T4_E#G&VWOf#>N>_GdfesTRT&QoaE7>NA`EPe+#?MGi@d)FT&#qO)Fb^f0Jiq6>MB0SPD%#V|DF5&s0?=;W$qR`FPs&%Qkr~Q&6Hx$9Bp}w7k?t=dqT~ObzEN$G}+lHfs-bq)#&`Xk@kYr0#i)d8YN@4$RyRU>zdQrsF;`s}kqBm`3(kW_stanmE=6#PPfbw@-3$@FH8?uvEIA#yMSfcRr?i`%-I2tFx-OrY`Yi)*f3>@xO(iYC}6;!tSq36~ZF6e^l+wein(^)U?{yAO}~OyH8mlL|mGf#j%9?zo$nJCl5w6VJ7c)Wk9EV-?H0}EQ~{jd@(sfUx#Jh;YeKj+(=lX(=;6HqfGT?LEa{zNoSR@*B2*-;~uj^GHIS#z7s?ai+LG0pUHOhE@pbZ)(h*)Kq>D<d{c5-Qm;#wBMMa5$l*Rb#lB2UDi!G`?K_coLu+}tuST<L>ZtNwQlMJhHbqCIWdL8G1GCHuhwp!Ryw;pkKu?Ebs^_p)F)S}0Gpb25w=RVjx~8|QEA(q_MDs`!CdM=9&zET7%oj;8;wj|tx=2H34%DVZk6p5*CANQ`Ub(#^TAeVk*a|rsMZ<_a6|fRVZsT{3D;KlX%OE8y9e^Rf5~$mmE_Y;?=cZL3y^ap-@l16ZX^6#0+bp`(kKC<SFwwe1pbZh(0k2Baj@nV;&6afj^-xcHN`;9m4wN6mC;2$;X#-U`=%QT9MUA;w$OMsDaHm#KOSfI9eMhst!_OGD4iQ{$PHH*eiAam;V^TyR@?3vqHiYI%<EU}L_Oj~k096l7v)>UT&e;*ntNU|t>fp(o15>?77Dh{7QJHBnoZOSNnjLWmWhoV@-dDocT2DPVOq|Tql5{E<6I&)4`ed_AwIdaCMc&KqFOk_icSH&67*SbzEolycYs(m$t1(BQ$MJk@XO~UCW`jzLQi^nz0HZccx}=j0qh`{uMIeTH6*!Hw3=RjW_sBEn3kO5fOHZgmX4C?fcOPz7RjOiI6i{$|X#{!3!5DGrOG9@;h9Ee8a18PJbp|J0dCc@vr3CZ*++HhU%CxHCcaP@_Aj(hO6nKb3LT%xaz`V751Y~{Q+{$0s-5sivggN5NGjDzHB*u86MN2IqS^W#{l1$sN9`D^P620||C+2=Z840%5m``H|k6;=!ZW^rvf|pRhpPf=%64hX`;w9UAp|V3N<H>t8S;d9@@IGY|^OQ;{Gsv#@JpBtxc8R|jyo%EbO7F;|34cp%4nQxAA0DgFI&v1YlH&(euGtLx3&%pOw7Wh=EVE=$xC2qemQ-CT5;1BwxisRkOL8tFZ83<BEXdQWf7Ws$rC#OgqNn)P$%4^-U}-1+*7~s-E|Yb6U|9#<{LAD3!RCS|Bc>cHYK}#9?fZ=aY8KL&0ETqP7acvs4f46absPKgv;OwSzy8lZ{q5@q{f`g-_Lo2Z>HmHBJFAphKmV7n{?GsY<3IoPkAMF9m-Ner|NWPL|JT3$>tFu-?b+Pdw93nefB(~;zW&|+SbqA~fAuC>`}!65C}02Y&mVvD-OnGtefh@q@6>;O`4Ru}r+?o4gkOC8^zDCNfAy<x{|nyE*Z=#gj~{<}-TkU>9KQX|U%$Toj``c?XwsLD@%2s45Mo#nxF&*^KlpF|b>9{N|LwnRG?DS){Ke2X#&6ep1RMC@$6%xS+2|x<V`nz@RBWa(XzVu}=82|;Mhnn{_lw3h(D?U)#sD;Ko?P!9jRk0w0F8UEXlxUWeIIBHf<`~lY-sFoH12F@?63)C9~+JNhQ=0X^b-w4qXlTp`$c00pfQh+Mqg;uoCu8>JZkjg?@$XG3((m2j>gVt+`8gC(X413K;r~x^!r6KB5-~JG^#*jo@gK%I~<L=Z#3u6IN=DcOW?Ni!=nV;O2Brc+@4JKskX--CvE@}n<d(wOt$@Y$(7i5&t!kJw@)VECb&c_&6CNuW7!)SGn08T`O4%iq@uqu(eIv#DVRLRNy+57#_pLs_Z^JM^UP+SOwe%blL;0!+L%1=J9orHUz$mjT>{5Lad$XSv=oY7|9b`~b|e%v3`&RWz>b3wQ7A^6>rv77msYO~m1|Nl_eUi@sdSB%!AXqA85t^FFOBgyBST2#P$J{BRO~Jz{ODB75GpX4;iZALhoR!afeg>%Lvcr;SdiRV>R_Hwo>1C}udf9jPbg0)wNUkz4zy1w1E8pP0YyKdm{sJsMDU+b=CsBe6g5nC@z79g0p-N`^dL-ZKq&SJWe-I^p<qzl6Uq}xHCFu|plJWDp_tP^apRx_6p9sROV2e_e3Q!g3s$B|##mi1*P|b0WJsyx|9w&^o#Do)3+{0jmQpdRIa7z=@3d4j@b?l+h)+qy?#wUDlL|`3JgI=99@`gOIx&^as!BhpWW@<)rlOxzW-7X$ih2)J)RW3?1}&P%CzWjvGBcqk6`1xh^Vd%*xi`$YsU*_{#hnC7dO{fv1%_zd6UyB|(U*?H={P+e6?^GOwhQT9PayxK(lu7zYvw21vsanE(RAs8V&^6uXEku^f?}9WUG5)>9RVdTX?a2csllzz=iNiuOsmgh;x-71$?ANbP}Vq`enQEi=qyF}?xC1>14Z{hQ3IibCzN|@1vL<genP45KI*;O4B01?TKs;2;+{}03B{ZRih4rHTdx=pn0-P4HONmWE0oO$ae?wY=Fd<RfMT9dbXMAPj_wIfD0iCW8CdycDn){7D~Jmnd7hWz`yx>G{>F;Nr3Nxgdv`b3o~0x0;ZBOlq7A@a)~N0YFvS6w_RVZy{J$d$a8^vPzfIW!)jTobEpK3}myX(yvtrtt8RepG{ltVf##t%?^!nc?rUH`!n7Rrl&WOn{FsUad)0}i-O#0nnGEYn}1hVaG28^Tg6zUwrWV7>;2H|;gs>+?in6|44JYJf$Z2uf3f`>6VM8~y#?M_l(ItbJL>T5Gh=B${s2$S1+slX7*IqLnjJA?@{;@SRdS9_70VA2=I<o!@iBdkXJJq{;l!az{&44^8;U}HH61HJxX2GpdUobo)BYH=Ezi+dafLESPH=kHIlS~(hZaoVb|@`Tfv@pNNOegr4CE6iH*PJV8OVIQB98^g(FwOV<~$v!z%%C|O7y63Qca!wj>(oat49oO!XybCAQBfLL3CzZ*F&686lW>Rvpa}U$ga?)1!k+Qq^_d@ElE7TECFzwU{N^2=8eX9VIQ>NpvxsXzKLu%xh!d0inMBQ;dcqgb#wxEkinS#_N-;qb-#H2h<%3Pe3R>^gsTBKkKm}~1UJN8kiMy^zq4j|KHy3Xeo%shKCRCoZPPRbCAIwa+;OG-T=sW&<v-1+<&NKFSpc@VsV7veCt!G8Ptw4lDM=vG8308$Gb^X==et9!f|DRp<G;#gAg#GvdGlpK@+t5g@L@Q|QXbKkox1b6w(AFp`|R<!pI&f6s^Cvz)KR(G6{-Z%x2w+pA?G#$fK78b^Dn9Pi+E4_I}OcqE8w*!CyOSd>S@E$NFkZOs2N#Hxgl*V8(0Fyn6DZU#_`Us|QQcPR7zYWvd+N66Tyl2E@KtlWtlR1jXzavbxACo&RCRJcE-!Q3DW74LN)7K$1fr7e)lO5pr(ZNaG8z&30C?zL9gp+@0P64zPG=S4vQD&MsxhE%3{`{6knLzRCNKWpioWc-J8sVe{bFwGqG!5irZpz7DfYY`<jpU?Hz{#v~!mn&LkBhT&s+Q8>+nudo>Rg`8AWQ@MZE3uk#Tv^71zS^Zp!5t%-xAco@f3%0dYfxoCbN^1zCTWb2h<=?>JbOj;GCSg!_`OQogueXIu6OnjcRL_ZY#9Z6-`_REekSpSl#O5(=x|k`NIA)0$6ru+3?O`g{(Q;mZgK0h+CZe(P62PuxtgE9@Zl4bg(SYU_N0Xur?2;2)uXnYN$V|rP#?}1prGuVL@0Cfn|2EY+s4u`CuggOFv=pU~M_PC39si0xO;cmYHE`6qdPo)4PX<We3CZXM?47u-p?C+zkUT5cP9F*Z?K@6BamU1yFnUh6dsbYqam3!}1v{2Viab&M@#$dSX~EgJmDSvFC+hZGY;Xu>3rB3<=8&3;x|@%UBiJab>$><5$_#M$4XrRz=V;IW{e`W8>Fs^7fsx(3%d?vNJ75(sHLBTS2R<<^($q1?lp2dd}RkP%qq}X)O-QdDoRa#lPO1Hy<7sekO2sOSmV-Hs^sgdnj<3ETQ^@mhE;HIVZSX+dzK;Xz3s`TQGxZ9AD&A!;@L&!?LgD+l)xIY+-ydTbUV@SwNV%C$o&10hL*HXX9dL!T*yPWTsin?7L@XGG?%3%N5K_4>Ny8W(t_&mCWpp*>nPCaUe5Tq6C>KkoJEv`@>vh(qd+^LX`K;Ocir;sxZ?}W(YF_nAyy>%B*Ei&$+qGO%Lo)r>vsh0>5xI*A_hY00r_HB{K(ljX#;e^VyOxQ)^`kWai!lGn1x)%>2oiRcbblLxV0);e9~UQSqmzA*jXqzwd)uP_n>d0L~$hTFBg1x~Pr1s9(MWO(&<=)L>Y9PtD&Cwae!PbPVaLmZBXLrc1QAa~TC6w_N2kuz(SM|KZtrl%3aGZ&Iy<?4Z%81L;c-5==|kM=SjAc9quCAcXn?=P_5SApY7#L6iW79;C2`H?+Eo9mTbmqN(nRrrnJ-XjN)KLp^Bq7C}~-JG&o%W<Y5=?fYn&3QY@C{g9@~M(%lNnqf54t|vG~GlB1Hr<^BExRbaw{qnMFooT@hM6YMSr7mC*n969TN1<tyHC&vwz&T|&-L6i+0edG8d_tlaXM7l(5%kz@;&kAgvpMzIDo(S8{9J}pUmB-*V4Nm9X4*_XpX1!DkWM=~f##5jbK9q(8?ehx>d=3>#Hk)1r^k09a|CAuIN_9sI3vKRI&p?a!D*wLYB((s%Yj88u)(w2HCE5#jB1|#=fxSK=i@XxoW2;HHgkvBA3=L@-gElo0M7Ep2yuGQ-p~LC|9y#gdg9!0rcBmtz!lSjtC2zak$%PLXO)o*r#mxF2X5d7O!Ez=29gE~WFTse;z@DZN5ScJP(3(9Hk~(|258!J6{kKc&ftCG;xrjfz1z(#h<m~o#LHy&-@bDioYMtxI#3wnGMo<Jd>g^x08afVIDMLo3}-A3>ZXCy7C5CLkUOk`H27>!N;?_Puq!>@>a%d3F5?-x;+^VIhNleYR)xD9JUs)a+u;-k<I_XZR3uC%&F_qYpv@&@6B&kRKwxcZVz@-=`vKq?i^KC_vt0OkY!K25yCk;-v(sf!Ob=$WCu--Dh^kg{tOKb!9IErG59+pf!Kjd(F$W;Th6)6iA-@gOOVs3aL$w*yx4k2-XTb=dzWvu^s$&lT2f{zN3N_v#)XHrpcryyB0Z`)_AzI|`eh1!2q53<7YN|t3kECicsuoZU>(_68YAT1FDpmI|LsbqnWKh$tde+RCH>gtv)vSL<OQG76LiM|pc^zs3Ve}Gen&WXIsQQ5x)oB3Kt(FvnYS#Nrn!)p+T9(lE9<SnGhN?M2by{0c#W|&0qZ-dhbsSWSLQQifGOpNE*4Z+y0tG!o)eWfnJwSB;ss~VY2K8-4n7W~c$A=oCRsB$H1F8kR`}R;(1*&@_sHS>TwU?vnKnpuabt0%55!G~uVufg9lrl9W(+RApZf#D6F~zf(TEsNoq1vm5sRk+bv@(r=sm?Zk2bNUTWU3yXX^3Gu!ZfaXf5@1^TdG@+uaK!e0aIgY12xG)e>v2!p8Y+5s%EH$fND-VP-RSQ!PKuzUB)!5m)9CoJA`R?aHhFJ4rbyu^+(QBlT0t&CFEucYElBGdzsvlET))7z%-qVsnNB8I`N_ERX>vpm$vVhP(ub)zk`9=!_*Y&rA;1IGWCFI%$S<@!1QP`{z4GGN@|B0_}7y0wpvU*E*n3pTkMS))*_uT7(PQ=VdZx@c@GNJM|%BFa)x1`CIp|2Nk@GI;g<Z36%E%`i*XZ#>h2NR0-@XWP~BRiJv>4@x)vszjv}-(Lc8-w$Pwy?N9fkIP-mmi7<Uw*$q;T1=L+=pI0M3M6dpimiXH=-ej|_w?Gs@Qp#ccDc6|ov`m4^0Fe;snBGehetvqTx!rSH*Ty+!<L#R=N_B05!9fr^r2m^?DLxg^fh>t-SA044B5C#OHEfDHq2*W)hjA{}f)IbO9z~tQ~vdS!mH-zQ{2%V{nLaUD>bj6OW*PVL#TAy_k$`M8cp#>^c3)a6ULZb3JM+i0PB|<Z-OYwcKg*pni6X+rqfPH@g4XYr+EmHmPYoV%*Ld!>Jfmb-}QKEO>Uv^<=@L*3ok*zGukcvAphR}e@96Kytcr}E0bwFiDwy=_n6ZwxtD?<&koG{JgvKEIo%AS~k2-kwnDKEyGtPEkOAPj|3*j*qbM_~{lv=K$9m6|#eP<w{Ha0j~!hGE<=+-gE~%prPjF9Fd##6XlmoN5e1(s!Q_9ypd#bu3AeAdi?4zQ%-f&`(ZxmTAMHn6NvU>{G>$j#5`qTA0_=oyFOHSDX#c$uMOc&VbTYM<qNp>&`mY0It7r1!ps1=5p3~__K3mR8D$wqevP+GGxs<mylOH0ZB&;%5Vf_0vY422H0e3VGBZE_Oyet10_~+9YJ+)T7&-@m~L-1?N5|w^{TC)R5MBqP%ieyr(G&dJWNv0Bo!!D3t1n~Gm!)-lwwe(BPh2TsvKnmeWwhtd)B9(-(r*&MVYeVvzT>SeWGNRPpbmu+mu&pH?*aV@^oU9ll6m0#-hUSoFr|!(4b7~{LYId11R=&Ac=5-L8%9#Gyr8>$Dq$pdf-LjK*`hzP^y6_%M#wWtBlk@3zk3uRX8!q$?8KS1GsKOl3Rn$crud2QVH6avI1-nrO9mhAj+-vQpix6GtX}cN(+`s3j%3=hjM9Dtk&4arqg?(TtyNQbX(C`{f`DHH=8b>wPmu8ANH*+l`d#L$xYnkik?dbRF5u2<ErSL`uKy=hH7q1u><HZ_GmNNyW17wn)x`ccDajl&u<Y*y*t{dtg_kemdZOqsjq=DnETIM_o;CL-4?nSQ<J%|v-qX(>2dgK0tl^@mK|PvCJ@<Mi06H^-Of(@3^{9CB`JyHlqC1Q;U=pub@w8qP?smEQanu3AS4YC$-2yX=+Q}5Z+XTZA{hb6?Su{cKAWtoS9o}mrkb%%NpQ<E1<C{x`+Jn8XtQljfHDmy=|FC9v#nPk(qll8i(h@2pCqwbQ;QgY`ZeZYK*g0`y_io+(wbo;VFmBjmRQe$3N_~#9)6+J^+9R4D18;>-avh^1J@@+8Lvt*0g`Iox5tt6Cn4#xM#OtlZ-tQ5gGt)^B<a)vk_I6OttZt=(%do0&{;;bzcAXA_$V!jQa4em$3kf&ySH{K93`m>lKJ#jAgS>9B)92pcVjXLNrtRV?gaF=8_5XHLE}m4I~kK1$thYV1!;F6E$G>!GM7$UfSev4q)XK?8I|-H1W~3nt+mwh$DO-`J{d}aBzsT>gk)UZkOOEW6*5Z`m8A?%LvlI*a&K&63y?Mg8Gy-?nYEGU1UV&RWE`Od$I@}rtnBP;S!6)#s4Z5hPq5v%P#KY$U%C*AB(=+0#BQdb3&{jJ-rIRmeRPsr!CX$#1ef?E?Jh^{vc#bU6`dyYEZ@`>@eWBU8A)FunNqlFiW+mXGlz22wgv)ibZS%uL<Cl1_nV@=H9lQg+ic|5UDi2yaP6yc9hX_{VQI&OZ~SPIZs)kYT>JJF>OON~ycNlTE--F1Nk}OI$??8GeaWfbc7B@+r2BUy-K0j6T#A6V`gEAD4mTrtky4@@rBhlTMQJmX`vP^CuO1_>!%*sYeGST<q>KGU)j3I9kko*r8CIW;k_<N|>G-LaI>`id6LEJ*4jD=FP$Z3jq)BS(BMH+mdy)!}jG5Qv2}ruypp4EPMQP^h)va@?0`)KuWx5<ne*mSEUGge-8#hf!iqeuO)6S+FW)Cii(j8EcR#EE9q4X%qw+TLFDBZ5F>d5ldcw3ZH<xCl-aD?RMj8Y?+&PLKz24zsj_Mo&`IdB4H=$kAhZ=gJ`JbgGyHDXZqlhnI%|Lc+T4^J|0(^QhQBuO=lq`OO!U+&&YO498}+L@#Q3#9>N{-a6S4w7mdNn44n#o+8wlx9Y$!I{#4<GBJxGZ#Z?uZA+#NT%3B(trweJ(E<xHp+l9e?55jMoF4W#CtW_?$qZbCzXznbOp(+-GR?8-{V|7u18Xl@!p(dGIo+$PtYVCI3%exLugi^%5jqBwj`~=QBLmbwN-*Lk|;GO2!<%_K$N-zWg3UFCg_o)OrWM8Luo<iO#_tnEGR7p<u#JkJsjw4YgPY{XfJT1a}p++$MFKcIYw8*IN1Z0)pXX{B3bKOjY;1n07xRY!DB1~s0$8RMex4mu^ZTOTaVs-$FMXi`FMmS-gVm-y^pu3<b_!3OWaeE#3j!tV-B;lfTgZ<@O5jyn1^R+LXBmd4is1iko!*=OM|kE7t;aU#klNdx#hZ+YC&6R!U#?C?2~22(l%MfqCfJxU};k5XX)p#cL2#koaJJRc><QE;tOt^R#E2ghOvww2)?mY2+NBlUa#0!Pz_<J*(~)1S;h{Q`YJ4)k+L+qJB_Zg)E8lirMaf7p{x`L8ylyopX9Rhz|?C=QUj8gN*Jc=4a!s-l!hND!%*4+r3Z%VTeizx7-hWqpp=j_6_Tb(a%&6h-vLRlWF(hhEW9L6>xE~T-Z;t2=>fv+7s?ckl%ys}TF?Vv+id*WdFIhc5(}mG{V12}Oo-C#jF2428=e8>HYoi-k_jQHLD{<ACA-p-BrsqOpcXR$51%-bRJ*S9evS!^6F%Q3N#mW+6+D2}-jHO-NLrAd-8QOl0+KG)2jwKQst=$XI0BR&$V!(m`lg)>18Z$MQ2K#;j;^5e0yTbK^#!Bo6WY`oMn1Ox-UMYBSJx0ZB(IUg?wOqAkn&a86YfIjYa{~nwZ8Wx_RTS>8pfpjn9^(L6IE+zeX}t+4P*%dV>V|wO}4-I8YZ!0R(u`Mp4K;G=?1c#swlncZy&tmu*>S}09?1AyY-n-D&@wYOdthoXY(Bcstw&OH{X#ct*+1T0mE{uh09rLkm|bZnb6;2Sn9(lErC+cwV4s9l_5%VW|Wdzb`MZO2RK*^2T?9bm?gY(3Y1_E-?20*U4mt*u)I{v)?JU~rZe5KOi{9l*H}(FE8(Smy#gMjO9=8ZEbS#&8qu(vw0GlC>W4yUWhhMzrHzxcWX5FO8MiVn=vR@}zywUdJ{U?ZLYb0LeJC|Jfo}z`3(5(gG%Lz@0+hz$D6P^u^`lJL1b1M9Z=DDOaA&?xl&aHYVUN;icLb$di-(uIOj=8bE%16(Yx(O<P?`(W4#x|Dj0H%Sm2#dNq?uxJ{pIWl+;sw&+-i=9>s?$to&cn-3`y<N)DvQ}a}IS2W<afJNpfVp>(xjq+66Z!X<c7sgPk35HxFSCWIhYYeX8p|NxG|(v{{XaU9W?%4om^_kA<WGWB5iS{pCsO5GJYOc?+OVGfAk}wY%93t6irPkn{#8=@b9HXb_T`BncH5cCIbH3CV$F!<#qp5t3R+(gKq1BqS?acYv40TcxgBb;E98-LR@~2r)i(;`)jZYqK(H*k|4dAch^RP^rBR8Qhx!ow|5>(l&fQH|+tO0c89047J~7uHEpq%v#-)XJxI63fdDIL7p(~{Ba>qoAHEguFd>+Zo@N;>!p_}<5Qc|$20AC!qQ=AAr9NljO@^SW1d!32k6uXbSi*a0MzXg*|6ocJ_FEn9iA%VsQ^zixLxy|^2{;|hOG{;8Beooe7(2?Y-!jB;Aw{}pc9Nh@-}$L(-u4(Xlq}lwbdM@e0ZKFRtKmZ1=IlRVF*;85$M%;`jw|fc<Nz1r?cQRB+gLaRGB1b6wY{;IJKU7aGE*$wfSX3oGP2`5T_l6Gu(Fdv^dYnD8=XLcRUkFj={$F3T*Eauy6OP#rys7)S}Q@ybMkUaM~SChv0NioO>(S8qV#und8(uoMT#-x@+MKq(^a%GnWDKaB32#12{GC(}t3QOX1W9YQSVTYdP@A`_RWT0TDl(?OPqUTOG4E0oz%4uEW#jI75hIa3)YvqChvbTn}i5;k5UGQ{^}(C5VK0Q1PC2M$j<Cslc&4f`$Y4j8hH4>4F&N)`%Edl*3N%dKG2tagIAF-4>_Dc{=5zm-5`&4U}yNEHKQE*=$$f<T*VOPs<;kPRA5wI6bgh@`YEq%R=(7ibsKy=Z$bq7su%WkhfhUN8UlfkdmseV?Z!XxBP?-ISKE=<7CNijS*DI?=TwInb^f~SrYH|uPzj()JN_zGNihSG)!qsuDooqofkUh0)*Qjr4Nk4J=qOFYAc<}VY(dl+BR8qGxtC~0aAM<q_FAsf>Z;`?Q!+WcZ)QHNskqEL=x$^#?ix(2AP<DBvD%sHANF{59|nZ;R|ohOmxy+=W#m|wL79qMII!ofIIvh6ZK<=dT-3NiKa6Ub+z3->eNXz?TEtO+!`c&bE4yHW>KQ*08uw)jE*2`GooqD0%>5C3i}wGoT#0qzKmMhwe?M)Z7R&GVMNtK5mmCCN!tTNV}q#KwUM{yA!?`E7<J0@5VgQH2PV;%^4yZB9!zw)?GV+2fjW>0f@$;|sNJ=tH3NaB+X7Wr13G~@U-mjUJ<yP~-Z1P!a+jsj;YL5LcY8I5MfO0a69BcT0yJ4;`ht0Tpb-J;ceWcNfyTi=)tC`FP2Tf?!m{!SWYD1sZdwC+mjxQ`1!(4G;+5hnIbn4<lpdN)1~;v-QI#c(70`uTstQ$IBE!}II^{DyNdlw$F3L+Xc;Ben&9_g#bMQB_==1S;T8r}Z+B$X&uk1<<4PZRzXXHSER>(RTnTuBLUva{l3Qxx`#Vi}9=T`G>y+1jSy$e~7EqhCz?gAauLymLu)6J{STTR<yUt~DZVYeNKq{CyEonMur!YP_05ev#FS|p$DhUL>c4&Z%VHgKS38V$6TP2V^Eh7GOlz#)2Tpy@I|@zQhH{X5UGk1OTBHPBdDID_g08cCoAv<kMs1$+^`K0HwGt0Odx$)iI<`lZIa1Zw7yd)g5?2B_J&(l0>mD#FZx+9%Lbmyk%HY6sK+<Ns3w)xp~%K=&zM4S*^H=#pA{{57<4n)k}4o{Vn^6juB>05m;1P|*POD#kGxbZGm(@N|G@x;;;IpFB;$Qx`n-#d(Ii<Y}kr0MCfzdgHnREIhX=tn={n8s{0}H1+YED!KExo=QueW>qHKBr>ALMcHcOQ^M0BJj)97xW+$np3@rNeDW+y&|zNEWHr-}rw1kIkf**-Da=K9HVR>OJgw0^MZPtjCi4)#Bu{fKo~XZ}TMN}p#xqX3i>Iydv@_4mOKvLGPxV+l(XKSc;XIQv@u){a&NF~!H6E;=+j;(6Jk@S|x&u68R@4u9nl;26S5L$3oPR5|;WdDMSwdw%BXCIwS$m2NXawf>i`dYEgZ^Uy#XT<!3N$D+DJf7@>^ypx;E40Cg#*<$1L_89xdsEZ8PI(xIt02%w*7i_(l-;q$G(a;MW>Q>L@j8seU03C4+y$VwyyWz!;4mQ1%>wMakA&P=V)V%BkbC4+44Y6yYW1596$-RyKD*dF|t-h)`ZKDb!hW(tcE)5v<f#Q>mGruMag1yzgq%03~Z)-2V^UU$|<@5WcRJf4e)v{$;Md}at^Z9!;sa($Zi=-osm_b;(BXI5H44{dW@_YGG>E{uwtM^)`0W*KCPKR%{o@Snn1SruF0xFWG55GkevWoXawytvSz)2-YeN@)R2{IU?o_y>uGKQSk(ZlPXRVnN9;5TtN~>%VdrmZKy&FdutWEBYp!-2S6gt6peJD1RkprQt~x^1h-K8iU|hqx5V&~>*tjlQrU<y|TXLPcuvXMfRjfYnu|h9S2TESU8obA_ZbKSkjdxi}SRbv9&e`QyL$vw`)@_7NAXb234Inr@4r{m;RwWs%lb#L@)@^_$AZOOa8nCRnn}_F^9>5(`eOE&R8C4U6R3kz)?CjQb)+R!OrD3y@z8O_}g|V9aB%_)Tsu3ih0&rm3ns4M(?J!TPK~!yfVHHq~O7XX=JO}D`jrBaxmMktzZl!7gRX^|s>#s!>KU?7$f@oDtN2qQ#4Unn^RP{_X0IK6+S)-|{F;p`<0XbEJQiU;>#YiCR>bm`{sH!fiRzlUpWcsOw3f1L!8UWP@+y}<x3f#4*;_r0AsrrxvW7UABxO=@>P8Hr=6&S;2Fjad~s<p8yp=z@j3r^L{O31M8Sqs&)-UvogH8-WIIb-!2sr?QN8goehI!qcB-4mVM%MELy_s~-5-ZT3*$7pI8^)y|!A$y+KALxqSvF>R-kZH}2?jTdTD|?yJ-((dxVyZ?mRl}K5)!YvF4ZxJM8<}jrHPh*8NH>LvMv&TZzUXH_O82|Zk#6nY0tnQ*HDfmbsW~;$?bNOT(#1Ma0i^ngwBDpWq4xcHmhbG5YJfC7ky1!)(GdY6wLle~fbaAZDO%b+q22?Fe9w?b^%E(L)RIV3b|-%#Z4@Mz1@lWllR`S(PMvfANMnIilSs`#r0JAIv8s7U)B&Q??d_-U@a{x+ZZ{wcXI6n;1Vrs^{im-()C705dAn&4)vJ%PyR89r8VEGjfU3!jDout!w^DBi)DHyeuLd;G`S%^sAh7gqHE`b(H8W9D5WSJPLnl#BcFi3IG!`w~_dsoCIzO$^sA<Tp>106PLUef(ci61QfH*Vks=XLzofc?PDf9sippCl$BXLtMJEX6+omG!F0qRMhbzw+D8|EO<q>a*j4mkldoiJI``$c2pG85rV=``Ic73%tkI=TyQ4%AIvNrBoOtfc`34K&^!XzT;p=roZ7^%i)x-D{5Bk|1Jrt{S@Pdq=`}ckUefSd0e8m^5scs|R7st>*3EHtvJuFTHcq3`e<7t;5b5Hj^uu!QKP6MyZdZq&tmUkWq*B@_s(%*kSsFTccE$Mrj%-%`jQQ=}<-jr9n{YadL$7pv1ehn>lmtcbUl?r8zUoAV5jkb{h~sGe8g=hNE=v7o{4UBfnRaz7M4(QECu4KQT%*9HpJD<t%Woh@e7M4VD?4043dm9ilV^N_&2kVS>Hiv@pvUGnAX-@lx-j))dZ2S;37_dRrZpt{-JWPzDsGxoy^FBubqwgVI${Zk19YLupQcGLA)A+V3kMZgl{q&rsU)qKqmiDN2hv#pfuuT4*;M<&E#)4lgoGQ;Mc9$hM)>GfH2egmyD(URxg?Wo1-OYD$)m5^t-nW|U#Qedj36x`W3j%34Eph*E<Mr$p)IE$Bul?G@I_DKnPS!d~hV=%v2YI(rnQpSPeB1lb(!(Kl%Y+qP<98}$inJ4*oyjxwyR!5<!FrM7u8)*C)bz3V(b0j-4rz36k4c0FC51EsH^4B@(E;(Cn38$-UMgTMoNGTuB;mH5pm;;zJ#vsU2nO3?~M0^1hf_iOj`m)ng_Y?gk_`X4J4-(l6J6DwXPo+q;{Fe(X!Mqo%b*4&t@I?mNHTB$?hcMFW2VY4PXunPayTr2ytRnGTe#ruET!u1{Y|6Y1FjVr{zB34u$<SLuB6S(QOxWcNu?L1U+HEX~10bKQMxlY%?YFJpunGhOvmsq{=QHr(QV_gHR&|iN%Ry~czYDZwT5q4VVodu{)>lju8u<ER({Q#`-wpc3-puP;(pvQ29#iXjrRh^7$8jIDku<Bi(@UZp`9_5>>!)dS@0;>X8^);~iyTocI{>in(8iBe4!>ZPTJ`J#{kyy=bvD!*>#k-{VT<N-U2YelAuJ#eRD#<Ev5UZ<T^#H2|ReTB<BRsK^z1eNio4tkAjKivKi#67QgWgE7>LylwHLU5jRBi3xnp787tW&!Mwb4EkDebZ9VOU2Uu+-4O+Do-=ijY8Pa8EU4RMnH}dcF#PQp~98m8u0))BN|-D*sgT_s>h!rC?;eAOkSu2pLsqA?1NyWV5F@9aU4o8kD@N9yF2IV};4)1?v_OSZsX8VRfUinh}FF8Rhs?b>Sqj#Z#utj&q|LKrgL@>bQlq=gevbVy)$}5-h>KN+#b7ven*5e044m)lqxgjbln0cE`Q@Z2ldP)HRYuv1Lo1ZTk*0`VRd4+wrtRaT+xYr(-z2!zS)_*WCTwIKB0KI4QGtm>0Dmb!Tt3ZmOX;H(i}}IZmb17@P?d0$Y$_f;i1daGEO4WK|!|geI0@U9|@OMq7{e`@uPN56(3xr|kinwn7ue<{?cBXr^~Sb5hC4Xf7K|nLsi{@g*!6Ub@_$i>A)UX7qk6%}~(PSp)VH(A?Sr?`Td&$3B`<K~n=4;)~K$_cJ!taGDlexG|b4>$U!*xzIG=##7q3?`bMPQxBv$-7QQNLqAMdww|sAGu?XC)HqD7lryQHW-4gvjOJE6s0PxEgJ~w2E<9a|<(8|AfTaQ~&CGHd#xk6qWdO7MZ4{O))syA!66Dcj?~=%kJC+)>6BxtN-z&>#o%DL{*F$^GQiH_##u7H3eK3{*7eg*AryQjfor)mJ2!zNR%B2Hx0-YJQGp4#H|Ctq~m!)x5ly;9Y={}SJGzHVZ(If6`&lZ%^Sy1{4N^L_IN;ji4pbNJKQQ)}Vh#*RRPgXviC^u82{iqDq_M!A3BMVW6opC9g;N}D<E0zjcxfs<El)5k|4dB0a-NLsie-o6BLaAhZR&)*J1dL0sk@L1=jOeF!*>ysvr>cQSE<H}Z`^FSqs8F;jf?i#IP>b_guDc{nGybL<6@<{zn5=CtW$SB{HQY-4fMWJQq`-YvbiKKG`P)%eBPqKJQKm}U%gngXYOviJ>8#lYJQ`(tCCa8jS%Zpfw;rr&W&&Ri7w?U-Wl@e5$_Y^3d<FvPra!%R$PsOyUW2@}TT%sN%4a{mU&y%AegY*hW-ft&kf$BwG(%QI!STC?j917n?SD(z%><I4cCDGEA%~Mdo}j|kA8_ZVA?pg{NLtO`7_z!C<kD<@0+4m#_y8g6xwRmKj7MYqIUqX)CAnVE^E#o8*=vwh2H60}R4tu-EXcJ;jhVdegIu<1cRR=`vt*_rs}n%>)sbvs>W7R~*_V*FM5`?zCla#0SIAB@lAVQ~asE)vy)7X7Cgf>kEmOQPWHk(OC?J>Bw+cYk05V)I(s;=JwvbJ#oi1z;L&gioQwDi&cCef-bXJc)7_z%9WLJai6>PdIfxH(P#46;i;(38=SG?1}N_}l_3t5{Q<dA$H<b8Yi0BmG($j~ktLf%UG<AXsCeAl@nh{LXOKY%ch$}BuADCeyq9-`IOcZt|3Z+j5CqJ_K%C>0VSq7aAsl*7vqyV?;s1WAeyTKo82Q+W?q!sZ6B=FQDZcFEY@p{!emxVGUXrNpO-T9<j4c-pG`H4y16f`>g}|5$|4d!DWnR@bfc@8FOq4%K$)22a@6t_d+gi`ly`^S?1hThl#6XNCST7%sodwmXoi4_S@B8{9X&2dp0m*7z#e<c@%aNld$wI@lsPpZ|ngfz^)y7UtAUVcfsB>~?FGeV7Npt-;pLN6}7dJXl=;>(|8k+ju_nhz(AU0;^H5sZfe6V(=kgN5^BOVAT+?25d%UdR?)>nqkt~;gPFhV3V0ff;9!$sRCA?0<5kcxBTRefHi9xJ!W8`Gun3l_aH*6?=wO*Zp2!939uG`bwI*&Hn6(3c_ppA6s)a))dg5xfZdEd)m`~a_kyiO{E}6c-y(&}Rn1%#kcnN0tG+GQ>R~G;L0>No&Y*j)0o2gJ6nL5=QCs?OTJu|v&$YUBrHQ|FVPH#@?H+6dVD0^bwKA~kLR>d5A(wIWfNNMKi#A&b>^+A2Z^kuNxY~?sSh)tk)c~(#H6%_jIsiS5!TRN(6=hgc1*<8r>KSVUST(S$_IK#vQpXwvJ!rL>wDK}<<OB-MAXg3Y+mNdVh4net@K9X6WVlW`uvY<(V6~a^z!D-@u)d|65-54lz_<RfusRV|6WLe;g4F;Q0<}iEm&H}DXE2LkjdzGOjlue5&oX?hW`{K(SUteH^{KJoJB#ckK9Z#qjy2RrYvN;tJ(2g#JxZ(=V0GX-i*x-$VYN!Q2qga6YIhyH1Mp$Quv&oC17X0~v1$eVHm;H5k7GK@Z?<;T6TEH2p7b7tgDI(dPx9ZKW6d5=>jb^h%^-IJ4=V0U*Mple#oR|!FH?oPUTLGDzmPfXWMDE41#a?xv)QgLLNtydO8NPRjHuoDM7SXlkh>+SV&|++gr$GpZQFu&=Szk1;}cysq_87u)x;&57s^i+SN{NrZW4(lp||)|pJ<F;gs35iCWNRuGf@YHk%nCYZ!1Jq;fS}C{J6{o{6s|ko~YJGh~f>m7or*^>Q6ybSBd(>Cki8RHKGwHNJ^sSG(^>KqPShaLR9a%Y^!-SeG;uzR2#$_VDoFK6J1QMpG5aWmyWI+q8iNlcR)00(?=Aq`qy*isowQ}R&!+Tj)|)46LknthdP3!Id_B;jZdOT*_|fq`61B+I{m0Q5C0@u7K`elt{fKc$BZa!5O98?E>5Y3sHs-!Z|6}5i0X{!UEb@fW%*G8)O)DHJ2FHAXo|Mf<LX@pXhpiNJtj~!2Iw-k_ciz`E5F@<S^zYh8K{lH_iRfFgh^n<y~;`-%sS;Q*p|XwhMScPsH+aq<g}EiU5S?U^(rfcvg=0g08xLJMD3U%8l9h{XHmPJoXT=~1>m~bNmzrtyBb!Nd#6BC1gfPw&8#PiLy~c*X}NVuVDXzSlvaOyd=<|jJ!x<Np9J-sVb>FY>J@N*_`DFGs^T+Bh|dCbmERem8{i3ISFQ0)@R{r26HH!H;0q`|*pA2C3ZEW`Z>lYQ#+fd9k)#&^y?Z>82<h4C;Pb#ZaANdx3<bWoR4kMfz_wbaz;_XPCZlJc^w{+F_Tm$uX8=8YW_rn)zJ)LCs&=QDRRFGt<4X5$Os`g-qo)8Y5hg~tF4R&P&@mmur|%Y@8#Hwzhz(4PqOrVC?2hT#ffo*fo)OUt1w94&CoI)Vke<H71M?tyDVf+!4>pvK2t9ST^rCR#t6p}KbE1WB@g<vf_`<#6BNx6fXzHdI*z_z&Awzl&q?zHur-t=Qz1I`pWRoaT0O`R(cn>@>pv~~3(F?K@U$UYoU(AZ$_w<$!!DfqR9_+*yB+X%r(!wBV0Jgx;N^HUBcXo~TR`_(^iBB^4j0%x|;&VI8Uk5xHmlhg+=OSuvby@49mqhT=WIEvG0cL0(2+OiATlf+V99hP|`*KyAx|16&bF_68c$bQg>YI-|8w62;`-1niCcJyoFx5))7QN5^`Tqfyt~QP")).decode("utf-8"))
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

