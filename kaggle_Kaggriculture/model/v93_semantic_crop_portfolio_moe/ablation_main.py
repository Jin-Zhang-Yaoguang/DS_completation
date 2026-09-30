"""Standalone semantic crop portfolio Hierarchical MoE."""
import base64, copy, json, zlib

__version__='v93-semantic-crop-portfolio-moe-rc1'
_MODE='ablation'; _FULL=_MODE=='full'
_FRAMES=json.loads(zlib.decompress(base64.b85decode('c-rk<O^+K_lKd}y=Al_d_Q&32i8B^Pb{nnM5VHnh7&{&;u<$Nm@16$!@7q$d$zo+>WMsa_w(RjqM2TH|-!C&VGV-4n|M=<qAAk7y;@`gg=fyw1|LMmcetP_P@y)CE?=N<Xi~s!ozyJR6{~ka7`2A1+^~3)@e*X62iw}SM?wk9&Hy>U<Tr4iOUv6GK{=3>OzP<SJ?fvHB<ip4BzTa%#Jbv-3&AYp=FBaFc$NRruKR<r;_1mvry?gwR_g`){-_RGEMqKZ9zbsBV^7i##K74cXvO}l7z1VKvKYV)G*LU|1Uw-<u@A>nGX~(@+9|xfPYIjU$zxl<7x9{G3_xSe@A3hDk<Oh$xQ|ipSSFbmRVLEy7<9~hqaG1X85B%xlWS@@EtB1|~(;u5(IJ|fNQ{=_3U-=_({0TEU<c-hY?LG!%_N2jhT2r-IJgmpbFX@A9XYaY0Pb>A<y3~N!xwGSN{DI?;zrXvCpTqqhRfm8~o}IGeZ*|#%Y*Y?E5DyC2gH5Z#PM>Wa7>T%{&wm7mp!CLlNAYsVFI>>TK8v9Bh=@m`ct(V0k8(t8UZqERZi!4Aw_ks~E^XmLUSr#3xeEs4^wrjwLFSV8?s*rMk=;?*$j7B{`hmUV?%li1>xb|Dw7GwH`|j<(f10G$mVtA;&@{U?k+t-hj8m;?#Aun^72fe&G~CRgoVzSeckSVPXc#;D%F<<HU-Q)Z)CB`x0$ShNuyDx0xolqY=Kk&*`jY*@O<#h%n)jP`A3eEAhd&-y=$IR$V{Y_p{L|Z8IK+qfPd#;?Z=JclUv~^cTP_^JaW;hSAMRgmzu4U0{|#IhpmT>ieRj>;u~UA4cUM^_dW+9-(R;VCZainsY4P@+zq@uRrS7)q`Ua=Iz3bF12d=Byy{BDI`%jHm`<VtYY}>hvpyvZ<vc0G0((G|*3~Q!BFp5XV%0N9;r!s>ru&drdMT)n4X3&&-KDJE-BdvY@K*Pe>t63l^n?f^b;Q5xhb$cPqWeaTO!sp}e^Sp`^=8kkt$3W_f`q+tv$xe3S(h~3D!Ucnl|6U^%-$t^Z%?ujhDxUpy(QKJG80Wozo7dR!`ZX7E?w&(0ihIeR+&Sc0H3w!uW$oH!jd2g)g?ht~s~S$A&=+#Y>H{L)vHP3lZ0?|gJ-o~fJAS6-z_~8wL&*O1-B!Aj55K(sgOnq~FK6(-{oUz~AaCYoWR76wYGk)hr<-~nOZptfY93sBT*a^M|Ef0>deEPOX&;yINv{ttb}_X>L@6B8{m&BUuwifyF|@-8U-G0Ucbx~FrmplFPy!k@o#A66;q+8E50x2VR$9MZ1A@6>tbkg#xxGT2ib@>H8Yk#nC^18T-6x<x`#*x4An~60eYJKkVPI%{ibwCCPwzW&U*~=7u>}fWh(2jO-XJ3Ai{eGDn*;RGIehwJms0+IwNs31bgr4{--`;K&*_Ji*_oca;1qVBw($D2n1H?Z-7oZlFAfF^VuUI8dNikpv-|MD@u%$<(IBMEp2M3CHXp(^GJ`6@F19a;D-8U`{IA1L1s;Rc`onT*4_mlH1DS2ML-U(D6~?#b&jCR>wgNoTi6S-N20j5}o#BG4>hQ@z<H$J1RKhe%HUW-^Gxxo_Z`nQbl{lQS=S_g2j6zi+M>Q&^ZSa7N+?S+>EV>1yvNlv`&m2t?4r#PzZOA|eaE#HTLL35HVO!TQE1GDIIl_IgCMpa{o$y0T%4Gvr#WR|=y}NrnoUXjS%#o_#!g+pMmZY$6jJdD;cpoQ>x+l?<2&04W48pqS2^^3p@8FYC%;aR2mV<}!SP~13O9}kg*_19Xy{1juAGQx8gyxf-%G2pu<#39_2}o>L$)0)|i(vu;(b==Mgr84?4M}EB95-$%`u1r6*HNqNkcC8@M}O?iMbfyTdy33fc;?yt>v;{e_mkWq@<aX!D<ly;#XaZ`<p71m<0`wto=d$Lqh8~sZB-3nQ#>2|bRpaAbf2zX#y%hLtvKvzY1qKam|7AWbM~6=S7?BC%LALiwxTid=lJJ`BNJJI^CO@+EfJlZ^qhHWUgewtwhii{vm?W79!6#JtQd#2Wv%~Y8jw9_?1Dj9=*ui3r`zGoN-OGUx8h$x4GQO0SyPUO<vVcsX=O_coDCs8u#$m?92gSgPDGN)!N>gX1n5lfJ?;X7#47{o<S$~jqBnC`pCy<b8(Kdf?fXI81o0is8Q%AlgeH*F*4mj!BM;?6n1wjP!w@WV<V0ziQ<S&rl0HrcJg{wG&OkyAgW0=b#4yZ7_18SeYYZpEwO+;|>lZDHe8TOi$vtE^A*(t8gvbzFiy##M$BA>j){O79%n?u%TkQP=tQ;GSEm`OyZig;o@p~Z%Pj)M{pTVV(ie`9QHDO>yXm`eC*K{BnViI-oK8T1|tD)3syZjEbI)y%gM^(yf0Y4|tpz}>9t`hcKQcL4-zA;T87pJlXESd>CE@rb9^0ACRg{*vfAcPjFUD+M>x;17BdK|zI0x#CsKdB!E7m9-SRuYi`Z3tLnl&_Sciae)ppfz^%b$kFnL)_)@6ldw!$k&_@lw%=LUAanp3$u3G1kLO+v!L&sG}H%pK6P&vBpHq?w<J0X7$*qo6|?e+9p^u(bEissF6_ZgcS^Vy;v08Oxmqg^yMbSX4`r8N?JB)cFw{CLhf~e<5>S*R{!QSJ1fBtWSc>o24F`-uV7O3!p>nwDT$jUe>3`A^Q6<!x1<9&P^0Q;>5l!#ZMn&Mg%+etiq;9<*{^ZTuKSKjEw+``-pkatF=623HmF5vpre#3Wk~XW&M6ySbB}4<SQcv%a4hWo|0Q`##rod@;GI>9AH8O)?Cm>20V6hKyu2$0H7$Q#CM;Vh``B88vQcJax(LhP7@H8wa(Q25Dd>ZN`rdSqU=DvE|cp=F}A*wv_zeXWs5xGiJ`p}GR2mxccamyiwf~j)>D28KmqcWKwJo`HIhL+Clt+&=Q{#Ob13-gUMU#c$msb}0aMp49~6=Oc-!1sRuHzZC-&~s#Nq|}NLSN^C{WEoY8cFN~bXsJo!1Xd7&WlU30ay!&dH6tIjil&-|#;lfwYsk%2keS#yG^ns}tjdxzE$0=2ap&!hfLtY+r-m;_)&j~z)Hz(hc$7}6{W)``7$C+D14DG^1<^5e(xRA?Z`-R;UFB3D7ECnE0+}*X$@5_eW&lg@*t$Y9d4haPtTx!bGVlb(4-NBi(QWwdW*%y|B@otT{WCbK#~HLurCWi;S*H0Ki&E>Otq_bR=rs92_D3f<Y<nw+Y+p7P{?17m2$9oheIYBo6)tKr=B)AI+F|L9^fEGHUyM0`U`X2K1_Q!cInYS3TLG<ka1Kdnmeae;v!|8l8bKD(m>ycmPA~L_0E9w0o6b!gZ|VGH&9YHMq&i2nY)(WFwkF*B5E%yn+K9dBre@mdNnh)rZ`i0kITJz^3O-lr&T@N&*umr=rP&*jqJ@y^7oKl1L2{hMb8M_Zk)p6LXbb=3*M^Ojw|U%X?Xqjp9Z1lY!#m6wUjmXe2Eya~-QPXz|CUsc#kFaJOX+!3*Ucam!=~s#NiKkB;8ntdS52sPGY6m+T~o6CM@FT|hy_HoR8BIHpIoF>0%h8Y-SsjUMkBNcDX8=t%nb$j++N9`S(Io*cOg%P3I{+|!2$O&I5{%uD!La-XFDU|uk4|04xX_*_Olr89a{x;^2f?fx^CY|+;dD%fha^^cF*;$EU6t(V~&H1&{=ZPO+8TiGB@QtWhF8`F$GItDd>G8_eMsv@9ftSrsEK8BChZW+5jHGWyMia{T5o6-CdJ|FljRCBu_+U-Yys(RF_)WU`eAek<q}q$xj!4Y=A+~F>oQ^#;rVJO-whATf4xC%VgA9RLo3^GPBftV5wTS)I+?juX34z>M1s6*%pj93k9(fa;93tQ*1nx5oKBiW(4q^oLZ|jGBj~gELv~caJ&ZNYuGE*T9!y)NOgQzk>-%a7K-9oO3dx9QUlWlbtyAS$&M+A(|KKB3dSK<S<sHk&PGYt8F+er{*t0g8w`6Mms`CYE~ln)==7}s_>}P=Ial2W=Y$&Fc15#mm31Sjn(Mb(0kVK{TOpl>)0?uwyjnUHlufn90MjcF-P4$rwe(|QmuZ4>$}C_JaaF%KHu{IlOq4#nMJY2vLF7`v4BLm4jfXwNmhx#wV+`#l=JUeDx7aOI{MQ?8X9eqzrn^N1!>Cr+%muxvV>~C>H<5V}WKbaQLN0yPKq%zSzve}k(z)zm!$}@^+CBe3S*us=)B^1`2A&j{db&ylwv8PMiT8@!Jl5+Tgj`|c&;dO~v;CSbRTDh1nWe-mqBZO-&ebjv>0oXd7YkFpBDy$*1QmW+0gqOebWjAHHS?8mJXi&o?Z#Cf(IhC^h+VwCj7$Ap#W_Ke|9<GAtam}e<#;a)vDmtuDC-52c}i6z{_5?!zd+j1GAW{rM?XJLlEa@B#Fo82I~jHkYzs+3omnmY>P7#GTqB5S^kEiJmOw0wEy!qe<?0Y{!o&V6v6Ti|O?g1`P=rtyiID-grXC7qNqQ9?eB3p(FBS|+miaMw@pW$s3=br-d<S47hEWoY;i6(647ci(+{luoRH~2|oAj3Hy5}<GEfu4*sr1;{0$z7#p-^@fT}onpPJv>g{l5K{@09f<j<CIy#~t;RJht;eddA;FIBgs|Gdd{lEXArx>q~45Mj~eIiGa9n*-BKyN@}YO{OS?rWdmEmK!Uj;-fCbhUB626L--^T4<j<Ae(Fz6l$97Ez)1vy>LMRiHBYXqfEWV4w9o8G1E}K0+-`R*gH75l3j;~Ynr?H`a}h#<sQ8uTt>_AzN|X(xPll_Z1vv<joU4~Z4mxS4uHp&+QT9=wrf-28^gn}ESU??$DGqm9=d7^Iq+33Na`c0FTgVkTZi1FvBTV9TSx*h21)6@3;&g_S;-@3qa530<skm_6bC=ed+iuyBpdbTr7C6M9he7nfr?!nb$e@t-tA=^BH>op5F&r977Ng%JXcrW=p!sSdaU&P~*1ce!h7;7Ez)Sr!`b-!;c`JiR0Z^aat74IW*L1dtTH$*VC$ns%*&u2w$QyZ`pX49xin^v#2Rlds<<!P3Ma@}Ao)Kh&lm%JDrC3A;oK}$T7U1UWMEFFJTqQ0AMrH!=g1?cbD!<cZXb;D8sA16}Hd^6QWJ`rSB;5MTjLyD<L^1$G49L(c<T7*J>8K9NjG$4(fSibzxeldK3qt1v=4dv$z7<D)(D5MhnG$+*3d4%A<mg0$<~Fdw5Z7dt(l6!%j+}bX0g)9Kk!G|5k#JfMAFQ^qb*-(+kgrl>;UzmcpnM~^c$b1G$g}Lqa`*XU-Z%;;9fg#GOdJO?(om{KB+8pF7l(RU)T6Klypc>3YbY<4?q~(DE9j2O0?a5)i3C$i%DOy{hr!B`Q>VyaYpV%|8HQe|JvN6TYZE#{p(j_NBQF2U9T^gUiM@DPMmwjF?4IQWb<RN+p8LU;st<a>PI!kGEt^0RlT@~kR%g57?%%egBTe<I=70wATWD`i=T2Hs3m08q0J*36<uo*qhbD?52KHEH2vHGi$Q(FtQMx;h5#~;U@aW>QZjMC+6j}0C5?#fu<DZy7zp#}Ac{G;U7+yaiOuUJ+JDykkf;@4%Q@d^fEW<>Qj*IB@AV}lUDYBg{cuf;5`8s0zK`Pu#sdvC#4we<IO2T!X0Ms2?G*2taKb3`01-MR<#njj+U_91CXbXK`;n8rP5Zmr5S=KbH5hXf6tc07Sf&ProF;~#Npkg0ta1NB`N{=*BSmSTndE-`Jy7mfK_59QWT{}HAv%2*G0%diUY-Ur0L<^P@i9*EA*eujd`Z?0I>2{eXtf8O^B%xS@jRL61Gzcrv+u5<Ca*_nd%@F`rR4%vQvt|xNk;WLQ8$~dW6nS2lLRRd_^YSn7!N6Lr^1%cI^2~BNSqe-V-dfW$$78+u_hgzaW@!e{c%)${-s?K&T_A-q{(IU^&&My^-V~@}ve6E|s7X5|vNyt7QXcrpWHV_MzkF_TBaLh$;83TXD>&L1yS_=(nql@Jj}WM0yE4LgX^yKa5t6>?uE;4Ej{f8cbS_h`*-`YKc?01=fD(%+uBKxmTCZr0wicgEG6qy!o5U50=<l#@zb;X$JQqu>KA|nFQQT*1;b2K^GpcMJj)CKg#gH6f!T`XF7rO`w##;C%7q9Abi=rjANl<B&TW64BI~MZfrC+Jx?20|nBD+FJQ{THXbt|E(#eMTa367|hOhkzX4P8Gh1&I6b#ek)|g`%6>mKBABCdZ=~(4?#{Q1aCDNXR@*3xeHdD%K<D!M2x*Au|GuF#er})JHpx!9@2f=|TU^D;p7EtE^aaR^!MX&^*Jim9)iRq-5nXsZQC8RwI*H9-F?XOG!CNBG2dgA(e=0)}v8NBhh3|3DL7=3o+6AYtw|bB}a_%;6O=l$yL#k)l~w`?6WR;JT_QsHxIJJ&g(KqCebzlt;?jbNij|&ZiVG}#o0sIYeqZsCNx*sZHU=r*3bhZAJG~p4ybs?0+B4mN};uks5TbfQ~0SKZ@8+Q1KjVGn3n<5Ck{A|Nm~k@0?ZO*Hk3Z<F3TgCyen*Frk1A(pe1mq=tK&0eKcIh3bLqF4Zpyy7<r&-HwoP))+?q(!@T3^0d%G3j7XiN(G+C19GVU~C<^hXI_caOz}xUhUNiy++OCmM!i*PzLNSDi>#TXyC)9&*0#<J2m=W1KE{#SF+C0(~<gI(#!!p*~p{UYeMhQ|SYEvBDFT@S(6k6qTsXfy>X!fpfUq|5^EsrFZIQcmxNwxr9KJ@IXzl$i)fXxC2bBx9a&U+0Aqb!OXny0ECaYN#i1G6qdVCXc2nI@u`bsrHi>gEtXVH)OiLuP7aYGOf@#4#v55abL<QrB^TCP8DXCD{!7>al*amf<MQM;Xi8%GG>CMq8vLBd|Vn4QkXB`k$I$Jq<yK6m)*V!u8H{SHy*rNIr@w<+59B$vrp+2!JbG7;2I^5x6nR21cV<hw@Y%d{$|_pLCZc&`J_XZ0#!|@}<%fh<9Mq+Nc~MM8a5!wCyJ8=Py@EHlppEOu5Bti6$dH?*%YN9`h-7Rro<gvT5yc1?7J-g$TKfOM>tO2u<OQtkz*kqSwgJGR8mNIjbB|N+xlOH>1Ov(*&^WR#}y~Q{iz<PCt+Omk?zn{T$0YN1`|$SDjHP`8j@DJ@<yvAOaCVR)f(!(Nvpk6vPJU{*GoY5KyG=R<EJ4$3_B2fX2#Vs%U;TATjROV9g~+e-;{<LNGRYP%8c?N{B^?2+s$?B9+hS&2=)X_qR?W^JTw6dRbL>Z0!0!LkP>E6s{U7rxhw@<;-Mlu|bOuR7?1Ic_WnVpAa0YiCqG_!`ix$mXp^t@<|C6Ez3?i0NWB}^1ST2c|m8~Y4JQ=Q<qDTtni0PN5pg@evr|bs@PB@wt*Et;g8jpXq0u>mUt%Zt~j|zTY_;`txzZ;4Pt8*!%FIQ@mVY?xPWffSZ@Kp6Au+*^bp~A1^R0tvhl4QVwGg-gtM<kY=dPEKqxB`RV0z31kH7w*#Fkc05!LKRd=s*`Q&c5@jAsVpsJ~rNbz591^KJ0Re%oR3|<*@d|OjO)9G$n7A6f(!8V>kt;*6LQjE6H%8;|>1NHUByz7L~C5-@6<YaOzM0|<e|3RuPLC4lWW1vof)2gbA)<9e#Lqz=?=S?NfksOY={6JViAaUyq2?ia-@e#K&&J83tT7^}b+D-^niEbX>(`R@>WXQ#U^H_nG!IT^xK`I<8@evv3VvNK3rl|^)tKTp<H|7X%X%y`&fZh;tTNSu&tP&iXU_5qV<g%x0B4yaL1^^xBmBsyOFb5?noZv4oB?Is$QsPy3GdWpZ89X5pWA=X{Q;BjYQynlwfShebDoKJ$nv2Cpk!BBPN&pABq^#wxUREAYIYQeuT83GGZYM=Y7$O)feK`}(2WgZrUwP&G!F^{@c(foK42QeCpkPO}gHFz*F#k%SjmZk-I^w~pF$^W+Zb)!d1gi-X6K;3y7o7Dz_{c}1ZEk?ABF6{Nfl-i_NyMYVAQu%Yrb)?p%G`h{b9Sjwp^9hl!1{%N{}AnzVi^m{po6$FPfn(kQ>~J);gcyzM}$;Yjk?1V+6f0!gFXh|ORS*lM17wq4k8B&m|35aTI-U4Av3ploLb9didL(2AaBZA{0tdoR*zV=vr@&!JQq25R{WhN@@y3iXaMec?vKbsxPr915IN-{{LUExNNO;ue^PeFSA!D;-y904%s8|22*VFNFW1L$z?2^P90cA}^4{)WxC8);_PQvDJP3S~DDwT;VwqA5i6_=BUsBOO62$^{ZZ?HKRbbQFcyz5$v;!Ltx^6>X^`#)QR384M#C-(bfXxjqwpe<IlFSu1M-FxrcClbxav(>Z9W52d1JZm$Ioi--DnKCYMe)(}o(}c_^x{-eNQNhrOyvfmCiKHv%BR#t*AjU(PPa+XbYU0qTf(J*fdKfP_M+`4uY`>2s^Y$*8VstZ3XFoIoQheZHkp_pDx%v!fmM4-!i4Xzn&w6*!VuPK)qvs?HJ?G4)l>POX1!FV*sPV;5rnZtts_PFYf!_&@U-?&GhY*oVu;j*<X3D;tAut`FEOZ>R2d?}pGMP<31Q{{U<*P+6o(UFVDs+oYbh@j1sei=GA5Qt4M9SqRY87`WU=by*#T#t8Bu)U=XN;H$h%6Iiqr&Au?uq2wP<}!7xJo}W!Tp<!$;pi`An&{8E}&4S*zNZiHTPrkj*ek5V2u0hub+38La+UiG{AxmCJ@g5Q8JbW7S1tCTlRU8Bu-3e#y%kCRW8^2ZN)+j*VI_P+AXvNbo6zOY6|54fZUnw7?)CDu>((oi6CCw2A7)Kpb~x1%_8%Sj6%Lt*MwSRge;a&G7{FoI@6X&oebCo^x)NpvqE{bZ)A;LIE71YVjnJCY$kcDu@T+@u0pM<(<ak%NT%&z^iih)eAF+u@;uE1+Vl5NyNtD;uZ8MrF+K5)!1nhu4B&NqX}R+C4NZ<uRTeTY1%P4{wTbIp2h1}XWM~GM(5=*^PMqOKCPg3${o1SgUcFkLspGK$+e^TK#X?hkjvan5O~0`cA(%YwH8r>ebUPbOHLvfhdcv>pgUpptKgbvbwETEOF1sNA*b*7Vg<bZQGH**6M-a%61Iu6O<8<$ptZ)mLVacG6sZ!U#a??UwJBi`txREuvH*B#GU6P(_f1LC6L=1jub=*?A{ToV&pRjqL51z;oZ6xh7CRPulfj4=S|s!jg*r7`btM8fp>$g%bK{CWQJ~UgRF!pj$voQaCIgpgNJoz<tfBH9i*S}JgeJ{WO{yzU3p4*?FY81;?d=Qb-^Gbh#CFvxwYt5jv7Zu2c`XT^MU6U&3`b-~nnB}`7f|lLzSwz5hP>KLQ?2CTDyK$g6Heo-86vIeEr_B9IOt8yEeI)X+fAybZyS<Q5t#GO$Ebn|W$x5O<iHh53lUHWpMvJ%klCLE33PU;qfI7p@MDe~SmtA0NiM2D%jF^2vKM@G^)9umB!U*0(mO*wyNJYrTxng>063Qfeu`w(@bbUxtR2VTW6^8YNJd^>Zm;KvnsV7+W{y!z(1uj<bvug2Nf|W|0kEiVyh>Zu;266H;8Y6ZtC8~N@4V%8NjgrFx3fL;CHzD^U$@n2u3%(s1BQ)(CRlOOIj2*UPn%BSO+phcuBpw-tJ-@^1jv+Z2WLP13#-BL1k9n5wdqN_J<+glg8>0EcwJTX>!b3v&C)GchKlurhbmqb$iUGIgg`>a+r)Y7t+hxh@#g1|CJBrSkCAKtV!F)v{f=^6rJQOMk2Q?s80fOSIa`HQ)4Irc(!jiS(qTemPM?b)0hPPDhI7$Si8aQv1I7g#{IF03rDVYUbzQ92%8>9_LVvnGm0VP|r>@ILxWx#O@_7ViGNunrEv}bsm89r&BCH67v$>0CO9gHw+r62<gP8x7XES+M)@oNGdgkQ76QA<>MnLsv)q&0oY!ADVqRk`F=-P|C0$fi(UGsu(fUgs6q|U`&<$~pE=kiz3GFRPICcRUWKoJfUY4aGc8*MTyK**Q%TCjNrzE*Ek(Tm7+pZY2QvEhNNti**NVJFd?kvfA~(l*E+fayUX^VJ-d7Nx1-=OHtafvv>;VOG)%A8Zs20&ANUJ*Ap?TdA0B*z7CD1VpNc3sH3$o{wOea}J#a|0s^hBb*{!sHB^ACr$nuV50R9&zQ&=*PjstTLQA$GEHJzRIw_S9+Auc^gfggM2*U$N`I5|PEl5=ZHC$lVJN<TI`6L_+n$#Vk1S-$8KaB?DuVZ92rjAIXx3a3s6mA+w+J!Syvp*{Cm1_#jif-=aeE2d2%2}S)+_FfbryT5<aOQ}3D;0k#9pdlsPj~9b<&qP_b9=k(=6G<MDUC-=}=B30ZWx7B*L(m8>|2d8Mz{OUa*u^jc%sEi9D}h(5XPS!(mdKidwsrC{dECe<qw>9EYV2gwe3bPz0bZNHnxOyP)!g2T${KRlE&G0f>earZCA<BgIk-Mi*ZkskP*G)==MgaxN_gMc7T?OUmB&s1{EhwAn|uUiW5RTx7lL6m6!&6coc$Ey6KZ>)SdR$b%y4TCALQo~&(w8JpOsXY*PVM%5zLGHuMdYN4Ylc#S(sJi+xSQE8J?bCc|^5^@`_W8#{fWlR)%ZX&4Wu1&Fv*M}SHMyf>hyXENpI<Q)*dlUTkaedt1Jv^t_0|m8pL#nwWHQiZ*jcJ2PvTW|l!==6|!dTXurubcei{x@r6M40Dtn2xX+b^%U7%c3f%7V$xB)n0ta_Vn-yc>+ggrPkXZJK-uXx}MC7c_;qt1_h`tjb7;GLzo%|5PCmHqSNkLf~^yVh}C);fnzEBskI_0f=5Fs%`ps+hpcs9v!Y!wmVCqT8{46$hJ&dRZJr*Zf&0=5~R~5Zn>Bp+k9Y%V(I@(8dlSmWB}x(HyYNWFJ{fr^mI5myC|ChY^J56z8K7)rj*)6hEJQ6NIG@PNMn=tq&3)3Dt)<}t|KJdtFW^Y34vp3PYaq-u&XHqB1Ziju20OaSaUoK1Y~IV)v~=?1q8QO67zOIKBsUt-MAd$n=^?G=BU(BIi6~%fur=5-OUR-Nat23#Md)Ra%IU2vy!CYnRerN@z)%&p~28F{G-FbQi&*@;mkvlR+dgLMbjsu#Ofr`d!6agsUcaqTrlpuuGOI3hP7hlq;>7SlP2`(YzG(nx>UEt9V1m%(c;hG|5ycZsVXmC_=1W;JSM5bb(PR&w8ch5Ua4i|(f|%f+tC-&QtI}SKN8rwxv<9Xt!%PZ4wj2M#Odf7{i@6}?O1J@)rwHWJ9+@xLAX~gt;l0iQokBYE@Sh+c-nFafvzP}YDJfAw81YP0Q+EHpsXu!0(#V7&z;N{Xl5yy)Lf`g2b0s=P_3B@1?Cg#G)}5>P1j2`gOe?A3?!Cka|QNFwPuz`NyOwiHrGES7dYiM$dpP&jDu3C^TAtjZH1Xdy5~mGEly6I*P)hb%ar*jmE~mqSnB)=>L{zVx(b}nP&$7^V9ugYg<h_dEK1c#wH5t2ZVxx8)sBtLL(9rY4Bc%%Vaam+VpfKi9Sc#x({$R~jpR44(eX&g*%-AE0u^#8WR|N6RQ6al&3qT7Dj-L^bo=NwrKMvteu%pwrmqs_f2sPj5Pu@2k*Q~8p%gpaIfo<%pir<C@d9dfk2P~Aot+$ni81@(wz0f1tFi*7lQ7JsOmqK)8U+hZtXxdRO6{xwb}P~j4m&lLY6^=QtA6sk1u3<e_(Ze}I3_g1FhQyY2K&_?++C4k%20MHmkH)(jV7WO`!<>XPWh(p#hJ5__6zt7m63A-G`ikod#bpS<j!Fe*AR;mUwg1*D~Y|F@2bJZ=b^qPiX#W88<jp1`mo%cqh7L3P!KQ@y1dR(Jy{vlkQyiR#dBQMjasWAsyu;^6uKHyR*t+CP{yKKkX_Nj5=*OeVvuqKhJH#g&_!uET2eWb$K&T{$AZeNvPZzvqS98pv`$_fH?h%5^vi(2)u0bK#IPNsO-3yCO;Z7R#(xBd1CwLe=GSqh?2=>X!f~~Sns`{`xQHk4j+Y<1rf!}0WGOw-BYTk%p$cNM<3QtYnq*>1U`T14Z^UBFDlLtzi*xBs(P$6n7H(1;<CMIcU5VJJy2;QB84|6+bF}KvrkL<NNGZ@aIhr8Q<dj%~tkzV+w61ty!hbYMSp86C72Z^8Ktte8V;VBh70k=*OO;_Bf^qhVskyU+N3?$h3SoE}E95vumobhd4|N^}i;FTgxJ0V(mQIPb7|0`2{gni1X_F8Ri3C47vGS?Sxlo27kjG0ifNe~775hGF6;qbgoB|Y9wJ<_H;;>w$(@p}G356gOIXHp%{W6P_XZ(tqr;Mzw$Mzz`R8*eP3&Fd)<u-10$nZ!*LNQHgnK;{Sh4cBSD87*^D!7|OT=CZC^%u{Lu%0+;DWZ+}AJik6E3CHH%1%+-D(guUrerFD(HXPtyLb}YV5O%fDik0pr3kyuNR%WIE0;GkR{f^2OG-L*qiF&adU=i7BpRuVm_duoYy209c8MpZjBsdCb^S&S7vMSxAGRe&wU~nARl@pUnUW#upIi%GR<*xIMloA3c>%FJN0t%_0He63<dDvIq<a}ut{_EIKyMEJ7wL+!sXS=nUFwO!iPhe4w9{`Lnk{HX`t(4Xf*gLCE)cXA))X*Rbf^`5YVUb~u1Q0>9|1I^T|R_I%m7+BtiZVLetCS?&;Rp(KmErK-~If<_m3}J{__9ibJfu')).decode())['frames']
_CROPS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON')
_SHOP_CROPS={
 'BAKERY':{'WHEAT'},'BRUNCH_SPOT':{'WHEAT','STRAWBERRY'},
 'FARMERS_MARKET':{'WHEAT','CARROT','TOMATO','STRAWBERRY'},
 'ICE_CREAM_SHOP':{'WHEAT','STRAWBERRY'},'PET_CAFE':{'CARROT'},
 'PIZZA_SHOP':{'WHEAT','TOMATO'},'SMOOTHIE_SHOP':{'STRAWBERRY'},'YARN_STORE':set(),
}
_COST={'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}
_MATURITY={'WHEAT':4,'CARROT':3,'TOMATO':8,'STRAWBERRY':10,'MELON':12}
_YIELD={'WHEAT':6,'CARROT':4,'TOMATO':4,'STRAWBERRY':4,'MELON':6}
_STATE={0:{'last':-1,'calls':0,'mapping':{},'experts':{},'rerouted_plants':0,'fallback':0},1:{'last':-1,'calls':0,'mapping':{},'experts':{},'rerouted_plants':0,'fallback':0}}

def _get(v,k,d=None):
    if isinstance(v,dict): return v.get(k,d)
    g=getattr(v,'get',None); return g(k,d) if callable(g) else getattr(v,k,d)
def _seat(o): return 1 if int(_get(o,'player',0) or 0)==1 else 0
def _step(o):
    x=_get(o,'step',None); return min(718,max(0,int(x if x is not None else int(_get(o,'day',0) or 0)*24+int(_get(o,'hour',0) or 0))))
def _farm(o):
    fs=list(_get(o,'farms',[]) or []); s=_seat(o); return fs[s] if s<len(fs) else {}
def _private(o): return _get(o,'private',{}) or {}
def _record(o,e):
    d=_STATE[_seat(o)]['experts']; d[e]=int(d.get(e,0))+1

def _choose(o,source):
    if source=='WHEAT': return 'WHEAT','feed_grain'
    remaining=30-int(_get(o,'day',0) or 0)
    if remaining<5: return ('CARROT' if remaining>=3 else 'WHEAT'),'terminal_quick'
    shops=set(_get(_get(o,'town',{}) or {},'unlocked_shops',[]) or [])
    demanded=set()
    for shop in shops: demanded.update(_SHOP_CROPS.get(str(shop),set()))
    prices=dict(_get(_get(o,'market',{}) or {},'prices',{}) or {})
    candidates=[c for c in _CROPS if _MATURITY[c]<=remaining]
    scored=[]
    for crop in candidates:
        demand=1.8 if crop in demanded else 1.0
        value=max(1,int(prices.get(crop,1) or 1))*_YIELD[crop]*demand/(_COST[crop]+8*_MATURITY[crop])
        scored.append((value,crop))
    chosen=max(scored)[1]
    expert='demand_perennial' if chosen in demanded and chosen in {'TOMATO','STRAWBERRY'} else 'quick_root' if chosen=='CARROT' else 'premium_melon' if chosen=='MELON' else 'feed_grain'
    return chosen,expert

def _mapped(o,source):
    if not _FULL or source not in _CROPS: return source,'fixed_crop'
    state=_STATE[_seat(o)]; mapping=state['mapping']
    if source not in mapping or (_step(o)%24==0 and _step(o)>=72): mapping[source]=_choose(o,source)[0]
    chosen=mapping[source]; _,expert=_choose(o,source)
    return chosen,expert

def _cap_market(o,orders):
    shed={k:max(0,int(v or 0)) for k,v in dict(_get(_private(o),'shed',{}) or {}).items()}
    seeds={k:max(0,int(v or 0)) for k,v in dict(_get(_private(o),'seeds',{}) or {}).items()}
    out=[]
    for raw in orders[:10]:
        order=list(raw); op=str(order[0]) if order else ''
        if op in {'BUY_SEED','SELL'} and len(order)>=3 and str(order[1]) in _CROPS:
            source=str(order[1]); chosen,expert=_mapped(o,source); order[1]=chosen; _record(o,expert)
            if op=='SELL':
                qty=min(max(0,int(order[2] or 0)),shed.get(chosen,0)); shed[chosen]=max(0,shed.get(chosen,0)-qty)
                if qty<=0 and source!=chosen and shed.get(source,0)>0: chosen=source; qty=min(max(0,int(order[2] or 0)),shed[source]); shed[source]-=qty; order[1]=source
                if qty<=0: continue
                order[2]=qty
            else:
                order[2]=max(0,int(order[2] or 0)); seeds[chosen]=seeds.get(chosen,0)+order[2]
        out.append(order)
    return out

def _reset(o):
    s,step=_seat(o),_step(o); st=_STATE[s]
    if step==0 or step<int(st.get('last',-1)): st.clear(); st.update(last=step,calls=0,mapping={},experts={},rerouted_plants=0,fallback=0)
    st['last']=step; st['calls']=int(st.get('calls',0))+1
def _fallback(o): return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status(): return {'kind':'v93_semantic_crop_portfolio_moe','model_id':'v93_semantic_crop_portfolio_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'shop-price-maturity-crop-router','experts':['feed_grain','quick_root','demand_perennial','premium_melon','terminal_quick'],'stats':copy.deepcopy(_STATE)}

def agent(obs,configuration=None):
    del configuration
    try:
        _reset(obs); frame=copy.deepcopy(_FRAMES[_step(obs)]); expected=len(list(_get(_farm(obs),'hands',[]) or []))
        orders=[list(frame.get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in frame.get('hands',[])]]
        orders.extend([['PASS'] for _ in range(max(0,expected+1-len(orders)))]); orders=orders[:expected+1]
        seeds={k:max(0,int(v or 0)) for k,v in dict(_get(_private(obs),'seeds',{}) or {}).items()}
        if _FULL:
            for i,order in enumerate(orders):
                if len(order)>=2 and order[0]=='PLANT' and str(order[1]) in _CROPS:
                    source=str(order[1]); chosen,expert=_mapped(obs,source)
                    if seeds.get(chosen,0)<=0: chosen=source
                    if chosen!=source: _STATE[_seat(obs)]['rerouted_plants']+=1
                    if seeds.get(chosen,0)>0: seeds[chosen]-=1; order[1]=chosen
                    _record(obs,expert)
        market=_cap_market(obs,[list(x) for x in frame.get('market',[]) if x]) if _FULL else [list(x) for x in frame.get('market',[]) if x][:10]
        return {'farmer':orders[0],'hands':orders[1:],'market':market}
    except Exception:
        _STATE[_seat(obs)]['fallback']+=1; return _fallback(obs)
