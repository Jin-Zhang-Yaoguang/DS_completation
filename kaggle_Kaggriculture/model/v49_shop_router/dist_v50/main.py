"""v50 market-fingerprint router: fam_F prefix + t=72 two-level latch (market fp > shop table) + v41 weapon layers."""
import json, zlib, base64

_TAPES = {
    "F": json.loads(zlib.decompress(base64.b85decode("c-rM%(QX_`a{L!Q^I<tdQlj6q(wrrnb}3NO4bBT<v4GDoV4NS;elz^<rk0$U?#{@F$gHNMgP%lD!=CD@tg6h&$jD#*=j`8p`~B~K`~B>nemVQ_>f^_=`}4DZ|Ls5j^}il|@$lo{fBXGE{`TJwKmT&}<LAHr`r+>O&F9yj&d$&FZ+EXA{=L}V-~aFV^dUdr-hFzTKjq`@{rl6Ozq~(xeDKHJ?#=1fFBZT4Y4`s2=Z7!beEI#`cXzup_lGYJdG+(VpI&|W($}~9v-3^(^~bln-G?v#v3QgH?&GKFi#$xwyVrmI{Nd?IU!L>yk<(jGel`Cvn}rMg&8O!dANx4$`In!5`tkF-_iuiESkX_Pzf6U*l*>_kc>n6>PsiDx4QKK6>98K3HXjTa^TWem@4U%5cL%(G^=WsvSh4BX-~|ICfBh=XS$|YvF&`g)4ySQ3=aUgX{;<-Z$l9I^_-XD=i*}gcXz$Orf~Rl#)0e|wHYIWXRvpdmRX6~`@*LNaOxxnGo^5pb^2}!M@lz{};_3a7{eVF%W@{~DUff$~ohJMJ>HkjKeY$knLdi{intZT_(Za-K&<lJ#3%~=zPvp^~GZsI+_{=j*UHEBq>YhF{UH?C(r8RG-xj8;IpSH<w)HjaL*5i0;FZK8vI9bR4>rB@CZ^?|T_58_Xtvl}I2lm*dpOJXT(yi4NvRfK<bV~I;4URl?mB4AQkDsTzX!7La?S#&=$NwbHi<b~_u};s8Zr<{_x9{KYUVr-aPrJKM@7}-rm!)q4|DXCN=r2m=*ulHVzVc{~A8$V|SK)ZYPX3tOvmvy5dZf7Q51+zg9T?9gaAM<J7|U}!6HY@V{)jiYjdn_oHd%~4<bzKa+3ENnxYFL--F}##`N!Qka&}JMdX1xa<&!;bpzmmK-}lt5>l*xj8eGSVSodl3^XK7+6}VkE3|$az4)9&wOOJp!G4ZhWgHq35Sq7uwbXT4Mh<z&#67ap~6LmxsCzwQz))?a?hw&7nHZ`dr8euq;^pnxOSr{&{S+H0`MvKNLpQmP%4OYH9@C7H{RP;mMzPkI18gZP^;|hVL@)3tPvuLQt5w2pZr*D|~!;4^7?=pt+^~@G{&9ieK8pLt_;X1<W;S%RxB6>GZs_=1imLD9ZXlMCrj~>XNSB=2TvJ`xrEWnd?PkaT#aGurm*!BUDqOVZ`O#JiPabc``K|3EM_oi?I*-j1mY5CRT8>r`(c-JyGIy){8ANKT0F`jN;DQNT{t<izW@pTxFA?H442X8uDmU*bHI+!Ffg{5Uj{wJI{<B%4s4m=;`QM5ca=4OSj9ep%FHF{3VHaVQ)H!-gn`Yv13caZ?`0rER7S#CPD*O%TVvi0bRB$2%jutP_8j=mI=3=0S69Pn=ZFHkFVe9{s1w4n5cr`36`nL?XUTo!LsaKWyITrlK$&42wcOLw;@vGDcLpXYFjQs1k--@vv2*#rJPlZpTM>F(A3$KBoCU%_|9$v<s8(*tXGtl)J@o|t=Uf@?uPo$>GB^bf&r=&p6#D>A9T1*st>E_M_h5T10aIS;_^T-r^C*vKsYXeHtL90r(9ze_+AlX2zx98)3+${7=L@J=ZbNT)v7I_rgegjH^9?|Ex2)!1tQasYYW!2FXhI(kh7;0L(!SAAHCV~^nF&eN-Ld;e7tud6kaZPEL>?Bib4`O}*-CKcCq=m1^FdzYo3a_;*{_PIL<jsd<nzETIjr|Oav9$j3p75zTsR)#yNlXa0?qP2*s7(E0?VkNPVP1lLo^W+Omb^!S`eM3&1a&{Vveh6^u93|+{cx6!#RLH)XNhk0Q`r-%A1`aI9XF4VWN-&nC1G!<;a;T&-2KmpKG4ASbBzJRb&EsZf!0M9J)lIhNzMjP|&ugZFLxsL6=NWRx44ea-g8LQy&cZuC6Ty3F&I4IY$G_Vo=-TK}%Shf}-J??*K2~&Y-Lanz8{&L!#rOe5J|Dc^ma#@Hex>{j`AYcCpav~`DIy=+-)g%<;NcUxef4h)$7X+f`(R8LKR6tD^yVr3Lk#B>NgM}ICXBO_@ag{^ZoD_Dj`{Rt3f3@BGhS1X`kj5I!<nZ8&G|raEZ`L){I$Y>Q<8sL(*tq1Wg6==Xtg!SJG4FAI4)4c2Bw<DA1<V{tc-zX8OvwlZ$N%IW7(AsmfZMe?1Wk74VH7mYMq=lvSz(bjPQ>(nfTIihpBp_yo7!F=v6Y#%4a7vU$pwu21Yj>L=A)hH7>gRP82Ie3Jr{!1cPX#sMo62XROHzjDkYEh#0U#Z6DKRI#hO%x{xkw!Yuj;#!AJh0+yN95vRaHC){7w-&y1x^G1K#vo}T&V?r)+rak2{wU!DVjT=Yi<S-7rHefF8Mf8qqx43!cHE-4ohZ(X^NrfOk$EbT&!M;Hz+pAzU843;9YabsWIRl}VyqJ6a{Lk^cKmOnGhcqd$Mxx>LE%@v|e(>~za`xAY$EW@ta^tc;!@rhswF&o(hpsAc$|EgG#PogeVxA?LIZ8W8{$^m<+x9`ks{4<;LlG(D+~PHuCow9^wgLkW#%dT?GMarWcmHa>9FhP?Hv`XijPd05J7b!YH}6o^=v-Lzy>=4UqrES-i#Joo8nE|{s93>K?bO<lB3s|^fqk-Qy=MsQOVA`WWRzH#2?8F1TQyQzl){lutjMI9*I_;t2IXxv!3z)oogAX$Z&F|9S%s<M4*;<6ztU4(ZK*djW3FDh?h54;FMT+__#Sk?EWJlV98xu1g7Obn#!v6w|M~3v8pj`$c81T~`9t|_bF`hu&o3l+6CB#eY%N_-SCp42mN1_OKurL=(Fmad6K{<qI{@0}8o7@%Mf0gNHPeXXfhB>j7$1l`ZFUM^=~{WC9@amx3xh%wjudqf-pT1mcHW|Akg%8}jg-!L?QqW!8vz3?rYXf*tD7lbP6o@Fk>a|QQ;-0;a|(q$Q4M!~3HmdOP?kGuSIN8iS{;r^4RGZ$*wYqm?VDp>2#oJVrruNJfeTynSm7Wwr_KX^If0YMGKUOUr*W25f}Z7>!4c_U$Z#J}dsthqYG*-Be8Pssn9>AaN`^}mP2q+pORkoLRjG%dk`FYwUr_#$l2J18O~QUo`Yu;~6>Z~G_s=G}pe#L36|N>X&xhH?u(C^YgC94MS?>iy{ZiEyrwlJc$BW@C6JhMe{~~V2u(+_{6UAg_9LFgRiTzj_WqBYADN>wZNP?PZ3lMbYt()p>|5Qg)E#@vwwezG$r5e3riJ)xAiivYlR+08fAhHQ-P-M<+b%uf9yOxHh2@CM63Zo6=P8cx;#Wyq{ob&cyGEV(V4KT(d-@%+u^Wj-2OJF(}?#%C^M>Zy9wMtL>0VLy6+Q|}9Q4mu>&%tR&vK!P!$!G><j-x4&x(pa01wS2{do1OE*6tgbUpGXIKMl#mW<Yh1skB@@5@SnPH-69HS_A{i;sf7C%3}Pmg%KTMsHY~5PD*Dilmqk>tHkgP?M!EGa*CBebNI+ZFv&_Wo`R^_M8bhz-52V>JJIl(>FgvxUL^=#rOlF-;gvZuK_Q-I3G*O#+af;KUSr+3ew%uISA!&O_oo=_SDFkI9ccF_L=HjoKA?&Qod=$bbSZSn1u(tgm$7OIcgU1d(3rE&GKCePJLe~?fCL;3)p#XtTWZf5A$6s}#~8uZkuzk@g^)Ml^0xxwd1@|w4dxgVVJ4r)JL{4k%2yeC{PbkVoCD*v2;|d0K)=iCfEWHa%Wgb9Zgc6M-UwX=gF}0RzaqhC73^rd;>D%{lOs@zuOsm#V#x^=4e|~4szcS29lk9USp$HZYE;c9j=ycIc_Da7^d79Mq&#?17~Z(Gy`@@|+`hgI($;jR5p`EocqK}3Se;{Mu^79{X}Jqx;#62-wG|=41zeWIhicN}!Dg6#A$Nk~__U>uV+K|Kj9`Zf62wcmR8%LFjeP7}=U~#cJvS;$Ewitg#q5=s<cwM*%6x%VGlL!H6H+7I2P`P^?yc!fCNQR$VvFD<470s&^zwGV3<iCG;?H_}*ABLVM^mfz93wFVw<!@w+TzlJi;IT5+0Dub5BH26C}a%{xLgRT$#mdp0!22Jf+7?cLL9#6I}R%~Ram4P#W)@@Adh5Eh0JiV96w>7fCC&Qu8r}y^T=vaaCV>bwM9~8@pp<>Vm4=3coNqJvgl`HlcAFe+pP30@xNNBNvop;$RIV$KSwQ_rNs7rQ)Wj=9bD0)JIx^4kfx%QuEaJ-1$~;xwUkJvWNoQMmDi)M#IFJIhdh{AlQodnZMF4cBGJ5q2pB;m{<(E1tIska>Vx1zjhFoC;AE3Ctq_f{!foDqaO9+6Rqj>=1FKCj*)?q{ik5;E`h@wBj|{BTR*5ymOgmHJomlOTM60fP`5ej((8P>*8o6YSVy7n}(ifQ!d)eCx=A)d|r}B8IcDpbQc3%{9%RS2kV`I04+LMcAC~57n?v8Xa0f1D#8<v$OMG<@l=PA~Q6qdS7fVuew1Q<)a;i>=*kQxfNw(8=tmLXv!h*oV!BiSy9zq>S{-YC*w^^NkDx7`6}xu}BsWl>#z`NuZRhF2sn2<R2bFD6b-3o#1xd}zwinwEQOBZ=*>*0FPs+qP9;9uo>cxl@8NEV@#Pv*Q<1BJ?aCJ2cm0WIE$-C{4h{!s7T0eiw&c#(Ip~MrZruw4TOQEp&u?)rcu)pD@o0U5oZkflR!M*1|v-&)8mAQ1ob3-un%yXp*dl65!*c)iz7vb66kRk$|tv9zhTRbv!$q@T?Y~2c~Wl^Uy4hj?loCBBO0aAdf>?A;y&xDFk8+1)I)u%?)MtI8s&?5ko|sqhBrUzH+(4SZCN5ID>xkjRV2KN`ZPhz0s1w;$4z>P#*?n!!B^;QvH#XY`tz%Q*azn`4-dbZzjSKgf1O8mxelaujFY&N$1O5yk@yOL-?_l8$kt|NWZU7M8I-PV>7GbyQPC@h&D`a^q%TQ*38sW{6&@MuOmT<OKt#jpd?IP2~sP%9>fc0+?fJkp@Udg)6R=lRmoG%FfQrbA*dAG6wI+Vob8h07)x~0;_GOCg{hIfLHvI0@zC}Wvck+od*h0ky>92bx?%ybGJ-C{TZ~DJ$#agF7F9c8msU)_J->}nArnM{$qCv<^#BRjkaHn@0y{&^CUPjwq=zO8N8=Bj`4i$fz3|freh-0GCh+&|vyZ^xg;-Wf*}hVZ|NMGt5QN_lS#*vG$6z`Nw9~MG@|Z=1Gxf2~yS;b>@f(~>*)Tz+=O2UHF8(tlyvU1fD?mXh0%6W~EWKOm?~f&Ai0mIO?8|2}!X%`+CYjUY)YST8VnW^|)q9-;xPVL;3T+nY-D@K~!}?xL21F)*?-~vI|H|l#=tRMWcO!~&nIWK^PZh@z77t!9nrb@<#{wBplfgunh*cKwFB6x;A`_$bS1`AN2m@<z3zV%^G(6QPz^jTVbxX4?kIAh|Y6RR`L#ib#$N}M+A5W%m*)R%AqaV!ZFbUd4GizbiY%k=n+A5}(%KRz4_B6_DQV*EIx@h0#!(_dV=A=%TnxX|5YcR)ab{->pT92QjWux7-ZE5&|MKa;cA+~R`*4iBUnknFk>z-9lf92$F&?OZ7!d<azlqiwL0rzF45;B4ZQQI*MI<IQK)Y^Iyba>HvH`e+k3M<TxVa_XU(5q;tIz~eya;Bx`Q_!0@-RR1O6|cvp_Z4PQ==4nyqUnni+z%#yH#)mES_P0UUwmjZeVt7mafykIvQ3ys$<MFZSk%BufhZ2uv{<Nflg&ocBBnvbZ2EU@)u5r<*tZGZDJ#x?G+P-Bk49|sd3*EjpYxNEm@9>0?3V2prHWy+pQi6Z>b&}fOh`iQ%GQ<;s?mwQI7nq1%=-ZMZq(p=l;FBz-5nlvFbyHEtEp)A;ZHjU9@~Y{&i5MXsZn&OZyO0u#jYRZB|D6#?24<<0T^(b7VCBkgTb6aoQzT_z1EZ!zL-~-5qA=}n3x2y!O@y3VZBU7i>X4$Jy5NjyqW=WTg-=Bu>`l2qN8`F2nj8i*CKaW(1SrrFWd^>KCRDS52?v*mVEM<d?A-VjyPOYl#Wjzj!BNE5Jmc&=(4BGcLg>fU+;(eg0KzwA+9VbKx-Z4Y+x~`m+H#9ce&9_xg6>5^2mnKTMDjc4qey8De7O1H#{xRMKjy14tAR{unO;q3NQAr#wz_l;?1vA_V0AyY<7H17KN+Ce<9dU8qbgUb$;``d036X!-@X~!>~>s$n%!XqIFSs-mE<Yp6O+J!;}14b`VDcvpbJE*IsC|>ogpW2cacRMN^w4FoS50m6+J_>qT1=@J1;(y{p%)lm6qhEe4}=@Gh4A$)ecXj6bmeQC_CInIuCJUIPJ|4_{WGBe8}rO!u$Z?6eqXu4vw(XkN63cNIqGkbmI!MRVu;=P2YpIm{mAxTELGs(8>=GQ<1WG(~L?f}k8=ZLun`9Rk;4)G!NS>ysizs3@uw*-7pHP))l}Silx+Gao?r!jZZN#=)3{(l=%5hBvc|NciTyP2c!Fq}yoU@K_SDs0*=+`!)E#HN@}R%nn`*(xhd0)Ri6|A`$~=n8!5hByppF%UiP6jCU$BA@R~0>-;Xe%-GGN3k|CnIowt+{NcXK_HZPtd_GI1nAyVAqMtjD07MPB!DO!lI|BY8p0%5WAceimAunV-`+4t?T60joRHTk3B~4UZk(#*~O2U(;L}wCK!w4U2Ft+@5Rv1y+n>>VscEXPeL-1s6p>T!rWH6lEJyffrrylMl$5lBBks@OoxjOL>k4tLt9xki2b(meWU>9>AzOpdigz_;r5T=BK-fvzR(QZ{-Gj3{{l3G@s_(DTQukKZVg;Wk)i^-KbNTMoJLu5~*>V+7WjgP1m68XEDCdJs2+j@pfl!FzmM8V2pn&Hdggb#(Xl%X$6K?Nf6gBfFHKUfV5!;4?9&?vCTGJ)g2{>OqyB0kIjfE*aHY9vH>e&y;iOytj>zc_{h-YL>@sX-#r-_F_nG;r{)BnIrzO3o#Zryo490D)=+o-PY10-P|0I+=ZzV3PSNMq%l&TNPcO$}g%=!*51Abt|HGSy9j6ZX@(#l6c4AA*a1}?CuTMitUINLln6yyXI%{MyA=YiiSD!yaFH9DJiW)Ko%NSiO7j5LiDg8sybGbknuX03oBhYM$hU`d2|pgeFT_9rUbGI)kDv@NE<Wlet^moWfM>opKi=?0tE$Ca$C1s+wi2ZSDqU^_&vp2_;KlYElgK>utDOUn9QC4%US`3Vs?FKlczjb|0kGqNZ+x>IpO$0R`&=_XiL<=DlRpcCYHW&^op19xYsB~Y)GvAIUHR32M%>2fg{5xA%r)wV!bLTg~*QN(upWtv~;FQxn^iim+EvRIXsrS@MNeLLy;SZ;bBm;sM`UWhC1a2liyK&&_Y~<;?RxKpNb}^3D->Y0oMU%MvH2gum-_kS~v0Ds^Tc=t&nWa*jRa*nU&c{=f-BEw}r-9R2BLv2B)bYj0>D#CbOxuKzR8FF=rYx)!PerW%F6I$y4xVtx!{fl{a@T@m<zXUg&fcQ$bUY0+Xclh8#0yI19WZ?PtnL7%0La+Mb6jLKpRoq{R%Fbjmsj3{*cIkr|@|jezHT`5cW26&vV5^Hi8MswLX_;)toXVjJ7@O+=SXMt{bKt(BR?5P|M1#{F_!nwCj`!HOyZRVKzfD`EkP6HgUV;C@%`l3&)Wo>W3{pv@o%oL3CdB$v+RG)OSOdZLbbC~_pRfa0bxS!^=?`4A-Sf%U`VMf{Fz8>fcV%2qOdhBRLwYf6#~en)rHCE!GkygbJib<JnSM?+$bQR=p>`jSwYn6x9sn}#Amg_bSfC7Xu%y^dZiZ{9*s%o1?3c@}|Li%Dd>f~C_+l0gvWDrE}uh7Z0J2RWGiLMa8#XBiYOUs_O|kPSXYc-Fpxd6MD8F=bH+p@HOh2}2jWp*0>g04ih3UF*GC67vw;5LU!Tc@y$QHag`%i`jsGQ9-B<CD^o4g3dFFT@7b<KFm@>%uxV~CGwiGp<1k&wyG8#El|ih`JOd$>+w2JIrw;W;izeZkb?mFh-?zg03-=tFTUd3n{4ZqY}z>R1sT?;bw5{7p`Sd@%pC4@9=Y+`#K(jL<qzP?U@KZJa%f8-U1u8&o@xfs7FB+0Ye4tW>@8~elI6l`-dMJGv9(9^dFoS^lU~qdYPcu7e1p`&N_dECCG`(kdTmT|iZb6UnHnOtr6rF$J*cT%x+$fme0An%4w$*atZ9W5w01_aWgC<m=v}1}sidK=C3!bqPq}0{eUBP3u$0G?sr5B?H|3yoT7A5ZLa$YfNgGfyE^JQ3>0t*EvW5*8Sz|~VYx~0^ZD<WIRwnHGBX{b?;M}f7nBhhG`AalV7|VEtyb3zkQt@LJb&jDJWpgLaqt&!02T8{0L6vP#Aay!-u~oIc`nGU?Vp6EO%4)Qp9>XM=Hm}Hak{2C6(Ye~V+3Tq%$WpiFg1$<NkJ5?o0D>h832`5d#0_UfQC^vZK53@V3vHJndJ^qK&j5adiMO`zgMw}wjQkO<&U-`&W!7==C&p{?VnD4VkzZOpJtD+$!VpB^)Ti}G6v|jb4hltYR*yEJ?84oenOioM2S22jBb5ck+t*1i>zq(Pg|)rTUZ&{zg~5x68QwVJ7$;FIlwQ3h297PT%T#I9p%|CSA>0~MYxsM%A}=~fDZ3~ms;nm5>&VV%$gZXo^be~+lPk`+tQm%(mr9zxlHSbXa_71_Tyw&v%{0PqO7|goQhGdBME0AM9#S!BOI|1^pL*N_xOJXQQYER>PVD|U4PcD+;-$GP>S)u%zrlJuuXAREh(V{0+fqk0<L&l~Zti`8fl6U|nM=_X=?|7oow@2Ne#mXCs3Zm8$|B~rNq>}ThL$1=0%4?EW2JC5L2_7$P2nUtY1O8|&bqkw14mXll6MJF$g^kq)62N1-qfwuRolnBK+75xFT<gAQ&GQVLM@_E&4J%n)S*@qzK@pHRXbyjEDK-cU_nGZ%vp&3-rhS(X}WQgd6T3aa;bXWYmL^<uED;c(kXo!4m&+1!sMK(oRvd$94OU*h0KRN3pfpHQF6dQ2<F4U1*W^q>fHWt)Lz~fI5|kXm#8YUlHd4od06xbIDWGz3m>%qw#~p{RbftNYq|!oaH`S?%f@}?9FvQz<MHJI=vWyeDwA@qD#|w=&89T$p~5Htc2kX7`ChE>JyXV!Zl<B{M6OVlA{rfT@w6$WT0NGLAra$@oT~Bw<V$6w&7qQHzO;%>!MqbVsl(Tgr8mTduaH=XQG*4*Y+!s|(>_W2mX=@k4&xg@6%bl9R{qLEsy+-c=S`hEig7e$>S$J3TY{1n@ytbU7sOs+4>U|(gu-UeY7eh*w!r!p@Afe>OaU%YtJ6rLFK<`Ma>|a;IH|`3B#<#22s2}P0h)XwY49i=MW#eB=@epIk<OBqO=|TJw!tWKOzC<r1#~?cYejcSS+|2<bJ^>9g@TffS=Nmlx4(nY1tkyGez*~wl8Xq-dN3*(BOwUJnN(mUS5nqV=$yBckCSYqWvrq0t{&P}i819oq(BZ^lr}e{Y)TXt+Y*3w6X}k%e$S`MeNC>&%?pf_y!fh$!Pgo?;lP5aCqs4LhC!DKu_js%X~kRAnv|-;HD50#5vx5_F=3@XxJ2r$C=-!Zxy2Vvcm#|zP>>83(y1j>q7Xist6_|v#JXm0VCv%;u4;){GEw{nfYFU9(92X~;{PRh#avMKrNeXTkcJXH2w-?@lQRiq+Jl(+FBO5i2Ir|yAsAJxRCENZ7clml9ZnRq*$fzjr(43J5-4L;75gcJ^RjX?!d^loKz2ln2b8b#>e_gPqXG<4cuZpaO08J&!i<@OLPeR^n98k5<?$lbs4tZ^hcFmhcLka%vCpEVBpftm2#1&OCcXvuMbk#STQkAHGi)WvotAwY$Gz1&&L=7N#KlK+J!lss6qp<OSxaQC#COB=PLQ065H)LPyMnopwiK*x-Ls6AK$GR5>DFy5B@iKxK=5=fLBFI+jWI$VtX((jYuJ$XU%xWSRIHI;PLmq5&6qLQ81K1w@r|i5x>fZ?*94;?f-&UApb_jz<6j|^3~>5HWH?24>O=?y498QDHKbx^vni}x)d?U%bn%q*`xG(PAMYh?8}if}Zc*jFlT&`l>d`!3zB%EE>Zx5T)U|NdaMY}n04ZWGs@aD3Fvuh<jEpY2%r_pc%7;I_yR}*nj9a`cONu0qc%yTgRYxYUV$3aB<H;P87qhmhYu=7;MD0B<J*l|eES#i_ZpAW+6m~Sp>)NqfNa;#lWK}?`^fl##6j@Hk$qzM=;<gh)ddL=qeq%V<)PoZ3$Y@V0qI)(mUSH+pn6K?Z;x4}|Hw3OJv#;;Hy>*Hfe5<r$nyS8OG~?#dg7k3Z>4J*cHntbYVu1i$G-jOVwYIXj_32|PY&vkGaM}{#JGJEO?Cn)2tk7+cPr*7(PgVm$)`vPmhoa|Hg^^IFuc^D$+!d0TS7I>FRSlH%_~29&sHmQE;6w+gUiFWsHO3_gfKOVepBaH%xDQuQs#_lLZLbFmlBG~Hj5%qG^vAc<Q7vCkGSjT0=@HS#o7Fo#kIajwYsBdZR5ClyAT?fS8(t^_sEyW1x{IX<1WK)_W45ZsSZQ`wQXI6D3U4!r_r{jX-ipGY6@I->P=o(Xt<~O)j~033z8@6`Ftup8C(8P~KSu#1Gm~PFt@7#1sIe5(vdUghol@QXUb;2|WX_2|Fg2+rS)X!#Q7}oA_DZ;~Cv3xX!zl1Krc7m)HSTfHdSldybQHPh$x|pZk?mQE1P}gS&sEeeP)Nlwq`SFAa6%dlxwNzOA(kWUfzl?jDAeF+6^~!qYLr5;PN7JkOG@Le*IQ|zw-95fSG2U_Av%n@<jsy&XnQof+Agl1U2m5+jbdGot~1AF@wpdXS%)Jc1>>6`rU^KtASFh2ZiXi7wCq{4^AT}9oD$i>(8k)mRJfsmJe*g8uinw+@ZI?sm@D5@&qRc!%Tyn_lZEEw+Gxf;i~KV4#kWR$7cHCKtg>AyVn*3F@7!O#ESb99;Dx6J4_4<kK9m(n^$p;h8l>Dk#g3W<Z$}GRZp=cj;;yf=H%{W=UC5np$DggYqw~6DWo;~%6?RrE8N>`@-;fthJ)PKoV4W$OMfJEE>mUWp*rqn1qrf9o7LMImup`38YCq~$wQgN>i1CzM9zadZHEz10=F*f9$}rE`!lTRtGJD!DKxF&J)*cj%u#%hXhDrri$7fDZpra>n*jkM2(UA&N8fO45AjtG&>wrJ>*gP5E*52Y`2@5-m2JyWxtb`qy5+$QODycxz^Fs*-Z{V1Xq<#3v4;kItDMz^(CS_0^PG|V6TBFo-=V=!{A`mF5y85bP*LlwBCaSX-=>0?}F-4p@hZ@!Q(P1q-tbytB_?MyrC%BhYv4m?~UcvBJK7YQDp5`OeJIF}#UbV-sXg5()-J?SX22D*?O*F~Aq>!h96!qDX%)g?!&sIV6{93!%6o|;sWnv8bRG@K9+CNQNt5l%u16e3oa6mz20p=(aCBY<JZ8mF>4eSZ$7-6YUpcYZMv^J9)m3!m$8c;R4R4sQ7T3u`kYR^O@k?HSj?hCr2xZO-8!M~?5@YkGuHGUX9vqr`ww5q=cu=#^+96awA5}_e|Z<S_&cKl!1{7tbWa0{;|BC#LpOX8|qKtIb1vDx4UEGP~g9V7#qsjTghF7<FHwymIAe6vwf#DP%o{7?n~be+7vL_1V5NrAyYhKjr-#u3s&m43sRSUKzQ!RTRI#|w12kw`)bnKD(6VZ2En0WcvE#n^2PjUpx{tt-Rofu&YzG7ECAei1fBRw|9<;F{7m-W#J*NEyH24!*{Pv0r({XkT7W_QBdBo6KmYiAx(%^_CXzIq0jyK1X-A9~AXbuCI;DiB&reM!t%weli^2%R(n!QN`yV+jPXGB!6{O9s#RDJOEKmTtnEa1}!jp4Q>ghUfQXy)*t?USMmr7ZN4qzOm@=Kbnvvsan49?E78Hpy0_3y)|W0$72QW_B+P4!X2v!c9lnz_)*44bT_*YeIQl}ny2n4J@8+01IINDt@=|obfa?AIF8a{&-f5oInPI>5aHu&e>Z2s=MG@^5AEakYI4Cb9_%MI<`~L&YSjT+")).decode()),
    "rb": json.loads(zlib.decompress(base64.b85decode("c-rM%U2h~ua{Mp*JP$h`<dS})cITwUtwe##_24WJ!T~<RfN_41{bu;Tn=8&ocV}coWOh@M?WZMX$)4(}tg6h&$jG1m>&?IX^_Rc@?Uy(I@Y9<g?>>Ki^R#;NuYdjbfBui>51xPg`(J<gx4-@8^UpuM`R2=Ce*W>{{==8|k8f6Q4&UwXp8s8MpPv4EHGIeq_YaTX<xly%|Mcnd=QmHQmj{2|?>}5VemD8}`~9c;AD+K#^Y!!ZK0fT<xIcV-$lVVgzrXwXrSI<#Z&sV|@#pXM`yapl$K*{8`_GTV7kQqbkMIBd<;UZbzCP#pE0?z(d^G-LHVbS0&6nq&ANw-w@t0qI`sT~WPal4MUeU)dU#G%Z%IPS6{B-xj<9YT+!<jsNIINeajRyn9{QU6udv9`9?tl+>kNbzoiVeR8FBlm4`@1-2{ZWO*e0lr|PUB?G2P1y@VWB~hwY?bdaqcdQcADU5@2|Ilmv8#h*TY~mC2{^19nJnO8~|Z?&TC1gZSq&IHoAOyMzi<wTMLci`2NU#z#t~GwUjYW?k%)VgZ+N|zsq(XE?u@za#LR>AM9bYFmW050-w(U@WAjBdGy>Fi@!bjomZH;@YCF>JO0ve{ePX7*1TQj=KR=v+6JGfZ=63{FXO4b)XOJuvd;h4nXK{Ok{Ma*`Gd(?cHGGi?6FfnBk_=>TdOT(KQ-*=l<IvN9C_#}fzw_eKgYXh@Z|IDgwC^<|0K_gmk@EWF3*i_-t@WmpFZv1KmPou{lnwOPapqj>YKp-r~V20i_$rE@-DKkJlo^v`!CZ~IA5`YKPLBV2<?uK6qo(!xA0hJjAsX&*f<x)@|@3v%TS3w;tg)2oszRn7Gn?j;LAmJIsRu{X&)Z$e;l9r=iNEy>>RxH5=ZgECwtsLf1ttrv8QfX*Wmxt;5uH!vQHbIKhH<3!0p0e=z?%#fbZ%_dIZFYiHEfxlzRTkG#Cx1yYdV`>|1e=fbT`0s3W2{!6b6D#uz6#jHej2sYwOV2*aVIpN#I!!f=Vrg2kF;v}k<td1^M<VCBmLUvS_}ML*=byN7>NBaRb#ULmklKH?B(77g`0!bNQL@(m+@coOXDUB*zpp4kGgd35eWgE-GWTt|34>~Q`iqIct@3Li&j`N3g|c9y^P=z$D+)d<WeOTov<0z7H=#8)s3=T%*gEloU5-G@>ha1LPNpWluPv-G_%>$$cIgMONR_5AJ9^Fq8!7#x%x2Zs-Pc!3yCw=WPhdXU7>X`O8)g*3Vj<1ysi=j`B3Uw~yEN=bBJ8DJvGH1|$cWOc*2G>&ay86X;EK1R!zi}5p=yt$9g=dS3+Y~3$nZZvdewx%;<uia(EP%P7W`?dNeWb5&sPGWt32SC@?_6tzjAwGHJG`=7a{#V$GbeiR1O4<Pm<=NzTX3HXy;hj1YH}%=Bsy^G`<L4=OxPKh%tmEgOA0O@x-|QbA{^BA`%R)&J`dNYt(E+jC_}zOe?-kgUZ8@1dZ35T0<IxH9uDf2))2+CSvwUj(d`1lHjo9;&3c+!l)S>qSd}Py^l!vy#w&<V-DCz0=kv*IXUC|OgV1Wv{jP(P>T+akf8K))sYI3w>Ist6bv0&(E+vDp*dWGS#ATD12+GUT=%W`OKPxZ=4(>s_F2Oa^VA-{(z3H<iZa`5xwV%i?nZfVbH4wL9>N>6!Fb3KF7_#|nl<R@yXP{sEvvVa<yoQhKsH#~P!<jk@MB9uo{USzb3v6jJCh#7wk;~b9U<ZlcfQT5bNV62`x9D-aniqi&G>*PD-8d7RMxUh?Rgn7m(<+tghpiR+&!l)l5*9*)jOT0RZ<c%>if#QnA;ZON^MX=FZvk9xMHbS~$4eB0n)y`j0oKM0FO!?e%#~M(jv6m-L*sD1wtn!aG3F5S#?Kk-@l_pVVs3LK+;;+rT%Cga4&JHsEtr$OW9rMBK^C(t<#jljVL%tHeGpO<kUyA6x_P0itDT#`}!?~A3|HkmS4)^!Z#<YH`Sm-Zigx)<xk;H&5F~oTYWl}ba_m2Pfe3^YvwZfMt(`b%4zLCll>DAfqba?4r*m=qVpbZ8RQ<uBxWb8{0Ii=E*AQ=q>B!}pwx+3dT^OuvS$B_-s{y2rm!9>&Q!Q9g-6lk8YR3&~A2bwb4N=FPc!Vwo>lDLB9)A(E>&ij%TG7(d_U`E(!j=L>?hrFx^J$#9ruB@OTbyl?E5|LHB!@vQ70By9!|CZm0FxyC5na1Uk#W=H&)~b+aOvMt4AETp-n-rHkrEJ$y6F^Nt6yYU{A+Zw~?-o{y1(J;99cj0-Q!OCI*8CXren0NnTcdC=q3<};&X`v9rGiJ}#*r2|jRUU@m`i&Rm(CrG{OAoX$zj=q-7>*2Il7U@!vke_dpiO^>w?bD@SFV))6m`clQ}eFAeEBi_cJ-j;2X}T|M~yUKY-YHHvc7lU2+qgfAR8z3Idjk*N6TecI&b~OtPXn@-`u%`N6FUs#qLG`H#M5UZ+K7^9Ke*E7>RSQy=`ceLS&R`vI*_#t}J~U7vX>S(ci92;EUiXjY{`N?H@&%H6}+SsAu9h+5EWk{GxvfD8_P_mpJboefc8GPBN&<+4JseOU%?u8dV+Zys^9f-~D;v613e-}r%rvWUKC3hYbrlx{CCW*rU;<7zOn9eSmzyJ)kGj1(bYxLrP4Mu-9gNs(HW`#-NL7!`j2pvH`9hSw)`4S#Tq!b<X8p~z+DCjgeDsj;LW4SYy7a|!rAT^iqi{PgEHt7{yUfRjCk^;h7b{I)r-?aS}4H$*l`B*AE`?26?wB@yoT06+>rJQ_zdz~rrwo(F*ZSiSaT(r6x*CUP1PKCmV574rw;PMe)5i0+j)?%CQTb{$5D&yS0|mS`S#)BOxb&nVC1hDR8!fsU2EJ!5PH4rum#n&hjRDql_x+L=+~BBl$_33kJYC~99$$ZZR_&?r)gyK7&`()nr{j*JX&>M~f=mR0SWWM1{N5~N5-^E@o4LIC_JHVSl?i(IH&PT=mbJR=9+Y0PC+g=cwba8P<EGu#Q(B9_*a+FQUApRn12NohhbrPC#<qi{=<Wl>Awr_@hS=?O{(m{(`Dt0l?_1aRJQv{=n9&??%-S&@`ZbV2?3wFQc<Uz1|&r&oEv&KbtNqWN4O(uyJ>76I;{NS!1s<FpUSS1e=^hlj;ykvbel7=3t~n7gZ8IVxpG25F%Y=RvuX35-@}I2}PM3SicuQ>)0BCg9OwG+j#IC@(Y3B!Q1=uN)p%p*GUZ<ip}X=|$C~_hv-lirs4^?#y7aDdh?ljGAJa1zIMsq2JA{>~&xt@Qs(FAz58a+9C<d&dk+WjifRYG-sGL|1mW;ymG+H6oRi|*aT(ebqUurT&AFWiv>$;9;JH=*i*(*Sj7JKWEB&dVrO=2niS)(krq23UUux-Y7ayYDuEXIvW1(cvaTKDuc#}EG2>0@&(><crO3Tpfsw<Pu4JE|{zXD{Shs|$p%9VBr2ch*-UIgkHI$8ut%+WnCS3Y~pYgzmM662bk~fPesktphoj~0uAckx9%AmhHq9fvUV(?yZ_8?YZj*9<8;}NBM<4ve1>u!m=N!5&06h#Uk0RJx&b3?<z|BuIl?y@_xbM4hr!EaT54(Eo@sJW=ua3XxXG&jCh!{q}5zZVm=LZSM?DLD_xopEs5v7s>sPDW&L;;5)ce5=CP(RZPtChZ>baY7Y^!K>#Th)2z^lhs*y-Ug<AfnkFLAAe5}g~ijJue5l1qr@zry{Jtu9yR=1^e3$R#e*H4_3TjgGBz`M3tp%+oC6tZfJ{+iPqJ(qDK$2;z$k54IBfLhyq>w19($2GJ1leGy{XPr!>r6hi2)=yefYz;mpDG@av=>rj8#mtH)M@QrGFM#qYaTg#Id2cEBXUR^+91cG9eJhPLV^<hZ2mO<OFR=E!i=Hbea|JWHjmcUx?CW%BdLgrEJ4tr#xyKDI1t{3Uv(G>8b5)LH2(UwE-mui|Ds;#@);QdVil28k8LFOkqUrgP?Ti78i}L*By<u&BE|d>QrC3e1|1qu3SrMe7@QRw|-%U!=!}XoW~(;s>`hUgo;?t0Rly!@`kyF20ylz!yq*tR3255?UHruWX5QbN~z?$;Kv}xnuA!jZJpjj2MVH?6#AdRn<&V`G*peYGi#cZn3R`VFEkTnBwU&v16zcb1MrtzXl~mZVDHMv$)m_CzApfql?r07MIK82&N+`p&Y5@Gi$-mGr`|=`Q9;*=5=iX($Vwx>DviX|%mNWPPvIh~-fKc*W*M$RK=M8Sg{0Z$1qdm?dZKwV3ud8C;ezf+gGDnZ+#<ldWrT@}QaUk+qCI<L4yJ|C5?gTO-at=C$B=c2U8g%dlZgYHn=o<&!z1;6OL}s|K)`VfB6H-7_#`cvM#FI{IT<1r0njX|zmJe8#DcHuBq-&qA!{ZpVWAiJtWMH#xNb)wub$*wellm2WhIE)-+^dj$v#}U4S_fy;c}$byQdQKgC#zIgSj_&a6Vpv(cm0LZS;ktp_pQ*i}+=M<w^;St$GzuAyFkB(Z<-nKGxxGfy5e!yr}$0LFJa$L0xW($(GwB8EHP6R@iBqoJ<(=TUmRHxM71bEV@!S8&a7uhQ7tqh*hIIeJ$fBY_}#z+QBe5gI-1h#hI<cZKG?1PF@@Cwpy?nF-?Ga{&u~k6>yg06~*cqN->7x|Eg(XIQp!qusvJ}I@rn8PJ}MQLnun^U<;MmBW&Opb)|<BYfRN+tJ8=Iovo~8eM{oeHlr!k&&(jdb{JIb#oCjDr__YJsKOEJ>rB%;1%X+b0#_<AKMI82;UxU+?;IbRq2P>OvejWSs;N^slDhcw`-Xulmx`FA63L5H-JvpArbuhYkMp|DBB*F)#<_CuvU`Oll6hh$ckzl%ric%8{the)7g6xSb=wQHq9rrmV-!g!qwPpXQK&$t5%zxLt8QfNWr<imEA`mtYMNq-BjCH2l&&j5s(rL^FB}D_`#NBugIHG_&x=-lErNnW6ieu-YD205uZ)pNaQQ4-CU8N?IjNgHr=DINeyFCfUcFtIxoB^kZBs~`vaHQ4D<hyYyv116wmj#EX(4MTFdPUC(v;)!HU_0~$R;7QXQNRg3E0d+NF{}2!Y+%&ne@<P;b{D!Gk<)8HN#IM_&o($nM&aApOgd+FT}D;(zjbhZwrHM1L+&nxi`Mj*+BB0#toF}mlbAf?f7fAQ-FyFpg;_|keC89o|SD<mwAy-$zN<+K?+JC2=l&Uq2*N3e_mFG2nw=lPc)kmCt;<Ucuvn#Q`7lDJe^Ul_gZqx@^Z6De)rnQ&#<0ag8`ArKe$HY7op+N7vYJ54YQo5Axno10quNRcY?rp@Pe|i%+JEHNQUtoYgSnRz)WBcYgx>-zk<0HR2x`hU7%REpy8>e15^R71={(R$7I_jHv(?04)V$*1mjFluBW}jTF@uWl2c|cK7A^Ss?4kfTC=^7<7$hT9tt-s*}pW*Y;q5nPP=Fb=i_8cbhKogoB#osV)_<!r`35qM*N;ktk(>*(CXXPoi7+_G{z|yRGYt9315Hcg;QBY;_LORhvE<|xGE%snQEGG`DFq7#@Nl9yhuBX*H;tAd)<@tgR{03Kqr&vY6+N^q6R9pVXiQIg9@95WjY}a%tT@+gV<#IOw3{H!X&kb*iQq1a~xaC_?0)+7u__&<>7nR6x^*>FiVE;D-g;)qL@dgm&aye8)ypp?x`Bol(qvJsnl0q#>=#8+_0F!6oC2g@moPNu0SbF2>JqvmCV}m@zi9QqCZy^837jDdL85vVQ?e&=SEJ%m{}hzB8|Cls5CYPWywORQzsXjnO-ftS`E`x0O+W$CuTrq!C~iT`Sx0cJBxANJ+<O5u+6+oPNyWz54$Kifr1$X@|JlGH*G+Vm{qm@8}7g1hoG@ouaP~8UMTgH)kwos*+LaPOc1)D$)DeFg=+ac!^Mb;xyovmU$7j7m#KXB)Fs#Z2^f(W;m2FQ8Z&P&z%UTMDrQ~-f+`Af^Xec7aS>s-Nyr5SXe0p<UK#fos`T9yCIXIjoxU6mP+(0f?Q3jyBYaz`@&!ejK9*19;-}|)m2b_6)u}drUU1q{q4Flquej`9@7AQMKpTq*(8CwrqKwzs6X=N>PTbm7VZh*rVJPG44`ib8sqe08;#k#-Q%ziRi(5Sg3%R{A+C|)u+p6*fMk;8!UI88l&jqc*5;RVV3e|&)X_vTJ1`QmJeEe)@!WmxCVA~K(PhuEeADKcY@<lpu5|h5MW*7!;MBrPq3dcrm!r@7awu5o}F{`$!h^RR`aLa+*YOof@Z#fCh_N=u_NnM?E{;FfBytj}~QZnd1duJ1ptdpv<;5dd+)issh7D8`KdX{x|VcUR3tdrrjrq^^CNCj9$bOyM<B{E(Gu(Fw)-ef0$97=8zauP5Dttp|Tn#TE_ufkusBfqZR)n-3WQ^$Y$w1!B`z6N#tVf5fw|Cv~oF{w1^l>f)3=g{e#(^%4Cort;;DkECIt*zu7-%b>K@yEuP84NKIBwOMbwc*W5jk@R0@VmzI_Uq(B3bFXW3CG3@86x%~S(=QC*ui{E_OtNbsi)Fw?Jy#x68SBbtYZ3ZEtE~FHUio@&3{#d-5h_D;}fu2U>fQVxE|wGZ)m!e(o%sdvhvzWGh$sy<eA!%6BxGDY22(6<1l2}rc3D52r-l4+~9LU*?C2iqU?9Fq9+~zmSiA$jqknkCaRY$$ZyV;dzo3IJD<eL2wNxON3#ex4W>J1RS?aJytIW(r_&=<<(`2V+x-AF+~30Qr@`V7Jh)aw1?Iow0G`9%<1a6;@o3{?8ZCpf*J)tkAVY6`VGRBgOHT22NeB^oJGhDy^uphaQDHx7WFRddJBbx5J=&tN2A2Z==b6`}CSf9Nzle0<9~ipmRHh)LD+M=f8HreKqNpr|&Vf;Ehut!v**Owhr-ze+cbG6vq-jLO9unN7Wh)zr2pe5seq$M*IF8~fG*v69Ua`^pwVumhXlex+QI#>4b_VbfDs@bjo*KF!{gl+$uT>>uPGDfkVnO6UchXR3n)YO4PH6Uavl|(6_Xf{>O@GHog92|ggUST0G>edp4$JaV+dcVPfkwr4bwWYfp#YXx@`Gb|GM7f+DZO6yakeg@sVc(w32K^K4IY%RRg0*V5#7k$#BlDbf|YX~3#E=$RZDvI%w<x+AxJ9&IA~tzFfjXgk9mGN+1!9;Db|vtqo3gyC3xwfo;f!q_l2TX*)`;e!_rO=9i3QI!2%`bjEf}1MX`xJP>l5PqJ~!k#4ggYp~itk=!G6UCVg@g)%rXWU-u)5m*#dObUa%!D|H1BE!W9^=>?!M(4>{5E&i`Xa01Q4g>e{D#cXxhL2}ktRRm|(3ITYj4Euv1O%hWgb;*%;t(S<<4f`clsp^h%(;8<4vgtURDG?h#w6f5Na6vU0DqCvIlzEv+I?stBtn+pg8v`yQj|7>o5v^IMh8XEwyyl>R8WqbgnQtcJ*tG)0pivu#v#WbJ05<^KPl5&Z(l{&C-lKb`N>E|0umZ$PW*iWtvxxw=CY5Xy*OS-}$IVS^w}pL@A_rEogQ|lHoG-lhMO5D6bb<8sIhE)ZIv5tk?Emdk@ib&LW7tB#otXld%_1${Cz_)XN?2fKr6i^LRG3;x20^jl<O#U52p5n7gogxC4PZ8;r%JaNm327f2?nR5T$5rG<0nQJBMP=HlSI(Q4Gzbxs!A$l<cX9@1ms2oAjfkOq6*-RH$|fN0^%L=Ei0-b6Nbr3yzVvrRj3h6`fhpztv@y*5|LOTGJ0KsMDi!h?$7CB9sxHouJnxSOC(h(9!|PY@waZN`Nwlqz7OMt1W%<qz}y27H=%S0z*uGDhG_VCi0}K!p2QLf?<6R*)zl?VS4|VzA?9F;uo&9G0ZhKGrYc-*XC?Rs;!}dZN!poLFgCy>8;TkQu@FWlC>0Az-8{6P3u(hVCYr4iq{49Cz>s$8;PbzThBi5wcz)a`@}%cO=?HbHDT(dNQmR$G=Tj-On>Gu}O7ql~Fa$UG(Vryz)ybIQftJ86^I*JARBgd2dRtO~Hqs@jzzJc3w^jvYc9<U;?4p)JM1EGV=%1RdXlg9mxjC)TXoXUm5rEYtsYtP<pGx-P<ckW88$`NbZ=QzC@Ob5Cje)@3j1HMNk}JS&TB`FfE<VnS`fLoNaJL{{2eQ|lx@t=0nHJl_x_2gn^r0AafH0`0*#l>hf+Cdv-krdO*Ft5ad2{v!7vac>7|Ve#1&^@U3X-81e)TsY?^WS#LHI0;$tB>Wx0B8-6jV2w90lWCDu{qE-_sm)sC29ON*u9qiea3tY$a_IvYWW_E@x6R_pevR!;-A=!cSvS-)8+R{|x?XWn*P-zt`)c!u{SFh_+9EHN^sGX5EUjrp6uz%`y?WWDgVi0mo*%`Kag+hV$YEz<lluQ{;?=(!pvREA<^fYe%dNkYrWytDm|piBrf-g+{{?;@fbW(|zGJ*C{oDIW~VQggdm%lhuHsG`Y_P1XbUnZiEzZ)|nbTpD*H$&Nn+9NDfpAzagKZ_9mWfUSY*4iUV@hX(LwDxM+bL40*2$*A1w-r?2|!E9ijs`l*x+tg1uP&32k)Uq&SwG+$BjrMAqgC03-Ql`8o=pEBu{j`EC7k3uf%(GZhF0U{|t^M6Pug*Qzy%WB%1uBwveZPJ})y`5cR!<^ayScgy^j|+XsU17J(<Myd=-jHe;w-#uPp_G#5xH?&Az*2)$>nxOZvmhyy0wNmG{*gP3h5Bwv@Go?Mz_U#A3?A&0#ry56ozpI;{Tord@3b<lSEp3F+$4F%z7xi3^QX8VN+o4P>+a^7tyf@3tYLB<tW+ZtZp^?sT}PFAkDVfUV7?>)?FKLlNeIs*migMcEQiag_Zm@`<?t%1y3y!}B4xTjoLewOHBwZGv23D$;Wi1msW2^h9JV)-U~V>jA+zpKQ+%38tw*-gG9g5;h3Xnj<*FfGpwOQvk+_02q_l;JWXv?u{KC?p#`M0KVVY==@xE{uRm-4HR7@+)9KqQOajtDi!^1@`+J!0W?b9snkr|8=GSs<zjpN1hHdFe%dL;@+Pa2jfT{}p(H^KrwLA2W0Sh?<P_4kSJPjT?5rZt~v;pIiwxh<SwHzDYj5i#}A_NYDZ>M+9IS1N(-d(j%BHQ7D1(8I1MQUb6c_0Z)V@L0$f2tBRG90m7Yt0O{~N5@OC4yU15LYt6MyKR95v-EqRa9zDE4VTraNx%?oM@6BcofK{=PN_=>SVra1>NChFFoqb;Y;h8WrGi@_p~lM^vI@Eq_a6iJ&f8BzJIv9Cc@>9xktnFV42y42cWm6F&yPf|TQK@ME~;&n5^z{NrH#}`@P%_Lel^7u=PG?%SJ*dVuCysrPpV=Fxt*$jULD=)|7FbY*eL!I;0D7PCy)v20Mj;8#+VgVIZVDvchX&7=@JadN{B@`BCBC)dN32n3q_WYIjt&oC?x0i=T2mb8L&AOjjAo}(M_7AHy-BZxi|AwJ3u1rlHx>jLkd=zW(WB*^KEwq$_D&05akbkz+x0moZZZf%4?c-LNCi@w5ckI83;{*k`&*8rWOdQR8z7}D8Q&x)?i5FHTHc%2-Ak7AsAPZNGpn!+=A5tn#SPJc3LHvOfneoAjl%r{1g=B+b>{I`J0VG3w`&bwE!}M=zJoYS&Vy--RgwpWS8D1mcJ_>Pb5VQTc=5H*GX`Cx@FYb<o%$vr&xhNsUA&q9Q7NS$3hgDN6fS-mN<4qrK$%waHhEC)7{q0BFC`7-pvdG*p91*o3QJEII2y%VC9kw9jUdr%IPxP&+S$J9&F&RxhJWWnB8baiPmYiG7`d+>0NAA3~l!KQQ)Jn{mAgQ=5&%=33N=nb~GvDq{-t^=H=@<dGI#1o}#@5V1bgt3$4}jUiU_hb`^?llHvso7%}d~OidBD&zbB=!gljIZ|@38A2*YapNINz|9G6#*WiE*4giFo7~NJ9&_;T5+gKO7DZgb7(8Lx@*QJI4OihvyHcI@HdW#l1WLD-vx-3vR$L>I>WRrjS6Ky2jCR0@Q)L#l_I9;@&3F%NZE*+4Q1P8rRbwgLretM8W&Ww(Mwx_h`=@HP?r@HkbUW;Bh(+rZ#t7gneSi#4OrrTKI^qy9?jc#uMu3oeEGn?S0GbFp$9EW#^UZ7EuFEs!JyIhAhH(s>W3WVn7ta4TZv|vzfRMov+D2NxxALUlD(yao4B=f_stb2};Jk37JqBeA9>yYy^W7ypyw0AgkT0=;m7d#9dm^tQp2=yj}%4m%3U1B<pgX*=w1%UU#E5Zc`jjjW`jdft_03;$p;5&6WSyz3r2a^n@-aS<`PxAW7mF)3;kiFj8`?sPh#cP)ao223wG~FsE4dRcNl41}0W%$u8^$*lQnG1?9s1lO(XGj<@07Kcnx)f?fRKo1L`?|$8n?jd%rY%O3;BkB8x+<GR+SV4iZLIMK7_(UmWRw-t3$BP4FyOb-e8y5(QFuX3DzzZ@oHhL{i<NP?F;h8JXkEEIH>gieJH>JhbeCAqC<}|4d#!bmw0J4onx%RxLWfLIlWsmHOyqPEscWIX?Qa66=)w|jbS~@-aLVVeKp17xSy+P4mEY&gd4eA-u}NGe#oX4^f`4N19?uR}(cZj7FSSbVqnQy2W8aorUzzO7<oJn(!b4$3eif8@t2n73=}@ZTvPn#yChm-4SE`UxQ{(j{wj1OHj%5NzeR3-f5SR7F^xs*!J0@Lkp9<={mYx_{4OYX~Db@Bnw<s57v05tMYKisv4a)Fs)TOW>aPW*IP)T=B?;V-Ge}*xw5ej`=Op_M<<oacWJztOh=K~!OL7GPHJH?fl{=s$nA>mm-ZzRVz)~JK$Dk+NTx4c=)ZY-supF)Aa_zd5vDofd<KnM)59tK8bOy<L{R67GAqY`t_5r7x@P4IptrB_g~R_j8;y>pp|a@9B*te(cocqQE^wX&0ti|C<Y3NRSXH3BpV{>eJG@x`fk3K0F3d`Z*nFeryC?KU=2`0ThrOS>T>T@Q?IKugWl__JO%*)dk@+D_~v(6-IS0;$9#)x%$P+TKvSpA=T$8iZjKvQA?=N88iiJdBqi-THKsqr9V0IsZ1U!d1Uv(t%}5X|Gs@1L=~MO{uIHT}#j<5jB)~T`3*v$`l}kzAwOjg3K1gU?^9qnL#B4&k(2D%ovp*K(o#a{gi{P@q`ano?OMK9Hf>L3^pD;{&?Rzr=q#rR~dK)j0sLFQixeLxxBVyYf0!_{#>F)63IZ8B&MO?yaomoIC3TE>7UN7mCKfZXGK9i1?%VJ(y`;Fu_7qDmK8fk_h<X+cna&=Q)ne~U1+omag&Z3D;xW1tK?h8EURqxdv)q_z||c@C@TYDEPD~Ro)5flzI^=j;pg}F$F9??h41n+Q&cA_fZY}1G)=>KRH9fK&-zK!C?=yaJnr;Lx*hibfPFGyQd2o0#&qLQ_@>ahjnYVEey`LQ)Igi4l~kHH0*kVy`DFrk!7z;40DW<$kT8a!yvaRPL*fwVwt`}C`=D;}Fedud62~-63OJp9wb{$8*xi}PpI7^7T~}B|*d%xsjt2VrTy8<}f=ME>(7fWdj`^5Aw17;_o|O(Rx_Rn4(+8TVC$Qf+<yeS4_`0&hUS5B}lnKnE>G;Z9W0?&Wldg3=kC%yadYWRCv8jaTQ64TGTT|%P?#l-|Vury~^v^vii%G;~Lut|y(o(~heK<&YgTn)eP>la@jmFO__e#>L=kI;#9MjS*J^yKZaGS0$$;7|?UE91m-CJjOKB?$atbg;-yFTuSQc){4qtF;vsYJWK(9VfwA1JKGyl&+|$YF`fW^qI0hpndc%ApCVDOHFkDx7(T`xaA|URtUPNgPk}`rs)Hv9gSN!UiVq`$7dhURZaOqs-UC2*cvBeH2h$H2?sYtWP78Su^dqqTIhxIV>3UE#}uqL47tfBZ4Lk>>|sek}8yK74ccKx2jfHK8i%7H<{$u(^5z+mwOh(c(NA7{$LcsKM!_tB*6DL|BiEh#0<WTRPcz#^FR*8?xd_Q#>?Bn0iI`q!^P$ZtpdwaaFWXP?Oe-_j;r}P{Kd`>=}2jboL}Kgr-xkfI+=w-eIWn9ISzjZj?Z16Ktwhu5JI-D3%v#zFZ(9zo0&G$+`Y{oRUlE6l`)g0SD`nx>XO>#sT}Y27TCl1)5rVo?;h``pMJmpbpONj!~M74hTnTB?HPS`Bu9=u8?nFB|Jl4XP;oDN7U_Kvl!>1>64MLL@+jN#o6f%gk;Yfm)BgZh|0Nj")).decode()),
    "c0": json.loads(zlib.decompress(base64.b85decode("c-rM%U5^|`a{Mp*ybs#hPx_4_=PcqVEwLnTa25uF0H0yNI6ugKGyLDZ)b7l5cSc4;X7!3Z_=$tzY<G2aR#j$XWaQ8PbM|k){`U93{dV?GKc9Vg{qf`3{`~CUfBnyY{jbL_9zXv5*Wdo*Z~y)H`RB9mKmYZY4-fZmKfn2Oc7C?|Vf*^=-;2xr{(sM>7y0S_;nNTKRX%Rtzd!x?-TwUP!XLNWx2Laf7hnIleSiPc<IOf-zW?Ff!}iSm@Z}<}e|q=h>n}HbbH6(~--NF}{;=JC`0^i%C)sU3ewseW;{?5X^XJbWp0D)fI?q2jJ@w?P`H$HwT<ANWu7AAj)3E0^KYjZC^Sk$Ne|dbPpFV$?3g=ZWNAcnP>z_UyXMZ-F#nq?7db-+tFksA&7k{($Cg<E8@b2}e?Ze`YO>cu=7#R7R*KyAJqY5wc>GJ1r8W(du8S&GHl?FxL?a6?j=kD~<4ig;h{pH@^=}v$8vKh>#B+lQequIU=8$ftH$9GAlZShwxHoE-v%x3TDS1XO;`T3FkfI%!~Yb|45oLlHUP1gJK|DBfm^wniAN-pZt<bySgUQB!q`UM~N0&v0biClVg#^SFRzj=YF3!g@(?)gX4_y7B}wC3$JH^<B7(>D1=-En-jp2kyqsHbn>WF7ynGg<S$B{Q<t^(T|H?zoc=?6ONgBk_=>TdOT(yEN?Rl<IXF9C_#}f!$tjKhI~;<jTj>3GHW3|4FVF4<X`Wovs_*yybQ8-@o6!`Si=5why1)y?^&FOWy?kKlM-0UzGN-gLjeL@@S7A?>{f!!tscm{4qIaLumJWNpaX8euc+6FrF*m#KyTWUe9q)I1QEfBi`UP+9^5OWHI)T7d{<ir|o~>NPGKm|6#u8A6Mtd-Z^>dHMZiFclNk|zM;W=+f%o$Yw-VRa2+pV-K)*_pT{j$;C5j%bV0Z|z<0fu9szM;;%4m!rJldC3`WE5t~>(}`&Jwz;Cs<4>WC;#Fo_(kF~&&_<0(dMYEnTo!f+_*C!=$-FkE7@;AIUNEgGM^o|;WISo!e47o2!g(GU6I^}}D(h~tDF-w=3JKH?B(77g_{!c}bbbcdNgya;ynDq|>L&uoF$Jlpr7K^*5FzDIaGT;cpnMDONF6+Vv6>j#@DT3P<PM;Bz!t43gESqeT*7T`&{C%%GVI4|mYT=oHxqOVZ`O#J=Zabc`;K|3EM_oi?H*-j1mw7m8B0_yoC-mwg}&W_8&hdn(~jH}y63K~5~Yjj|8d>qDY$T`p1#+we8Wgcp89ZV9L!qRI;{wJI{W0Mwd9e6&>qiA_<%*_h79lbO_HF{3VWwJTNJ29^r`YxBI?;-)>1LSvlWx46p9$$K!$kwALl0^1Czz!YVIr>seGAtaNbHKatZ=l}L@k&S3vj(O6XEboRoICZBYBSQy;u#B0+4Yc9hJ3O4*N?OGaF0?Ae>@)a5^hrJjn!8mSSTQ$!0$7e_>Z3+Uhlr&K0N#t+$&E0X(_IS6@kH*JTdpw1jmBDI^*BL$sU5=&{^xaS7cIw3sOT&T<j=1AUx?-a~^=-xwM-Ov60#L(MrPcISeqJzDqz9lX2zx98)3+${7=L@b)AUNT)v7I`0el2&>>C-u2dcRpr|XrvuOh$Q=gW2)WVGk19Yxz`4Kf15F%_1P^zf9*vj#KNJJIUNij`y|1f25=Nary<B6OaczeV5Qw~Iah)Q2+a1Kl09_oPsDt;ZdL)HQ7vIi`ZXfb0!;#cUx=1R~T0B(@9s(e-l2^#4>%{AMb_FIYfP77#kn^UTmBvCHg4;U#2D&tUvnb*zBwx*(6L<#gzJO~3{}rS&9g_hS7|Y6m+%Re>R8km&+~>>~xAiBItGV^g<6>sG>XOsd&9&!_okcItOQwSNgzl8n47nEu_JK{o*NRSN;hA5E-@P>Ffh4Bm%xw}VZFH+;9B=U6qX!#)R`g`uv7a^@;%Q!r@dJi@K6t$>V~JY4rTh)KC46R3f);LyxX1QgZFdM<e8RS`{*B?-?C$R$jp^b$ha!)jJY|1~;hZAz;{eKhakdja|KH<@_g0lLpRP=?8s=%nV=6Mgv)^<m^K_s&9Vm_kJVHdjRv2)~@lQ*7APl$6Vx0!9mIir-wuc+X1!~y9RI~WQ#gCSSG0-ey^-TN*q?a?2U1?*<jc-Oyn5EfZH8(8Q$w?z?mg~d_|7eqmFCAByDmTh2*r%8Fo@x$mzA|#q%8e&gV6-0821Yj>L=8j*HFmnZCkme;sRjm8f>Sh7=4;jOGah9HSwT@>1QFOiw~Glh9X-3?T}Yrckr#ah<4wh>0+yLp7N=N42LV`C<XLo{(g6v)_JmyIOmfO)YP}e^H*Or6lfyXhn*cLszcMcs=oUB6+~&=i@i2oHDv1x|=ood+D%v;5WIGkjCPSeSd+p~VBxfMhk{5HYpY1vB?#KT-en_(dYh)TucfmXT@rS1m%G+NrAfGyX$dAkZ41X;HYZLDok6l&dl!scBi0M1w#Y9UobCh<H{LR3yFWVattL{It3`MArbBottp2V;$TM7(47^`7msb_Xq?(Ee(HzWa&E(V_P7~{$9w#GCkPu`)d(Ydhbd+jW)M|)o^7jLGFcfg)I!eRwSwNq<Hifnzu2lmNg^PVBFo1jT*$SAR(5`;GdxN79ID2F4TSdmIIkHdT_49eSTf)^kFIypqgZ&F|9MTM#22LMm_xAat3Tj~wXn5&nsyGBXHD<97<J_j8z%kR+;hg40Mpo+th@#DMqe?B|E!SM&>o#8!qeo=nf9Bt?6_X`Q$1c)|LTT2(z73F1$CCujmz!Cs&G#+Sx!k0#t9U$#<johc1q6t-+n`uPyz>>f%#s}g~n+^CcT`O<Y!}=$78BmDAk)kd_H#r~4&QkOY5*CxBk<vM@9WK$>iD@=M2wGlKioRAiT>gR?P-n)D>()|1PUO}p9rk24-1#MV&@5(IuC;9?@8+v_II=asxyyi1TgJ6-j(KS?J}H@=PmvlfY|SHzgVdbb5B%2&+&-2$WKcVeyb8=xupxRFGPHX7_Se>{+FDQ(pPpecrZmBqvf&a%Q)vEW$<>muD)kUl@`0xE3(7xIGD@boN!ZU>-{m^5qHUb&{@Fwql%>bH!qw#F`7pg0)^TZa@Y5nPtGi&R@6~8ooZ)5Ycrl!1B9z_uU&N^x78f==pqT88<2c13u^&sL2oGc-MT!#)NpKU*(5ydi-Bf4$QyopUsJk@P&XXRMYV?XFg1R9qCeA5XMcylc$R->?kvX^383uyyS{j}vEWlS4{u;=gFk%dfW@z{~C+^=dQvIC<7~_`jV9uxc@GO)iFdYnc=6BI88<VnHwWs}XkufLjWC<xLh^Zh#%+DaA2F)D_aZszJ<7>|)M^hqo8E`}jo;zFsvAP4=zi)PaDG^x?X^<wC2P%b3#pdd<8GD8G<=`1yi*i7Dec*1SQpOKt81*3re`@0Bq;$qYSwYXyOAP4H%5>(Y9qgy+Zc&Qy97EM+4UY19U#J7`1jB1)vy=FEl^A%HE=yX4SEk4WgLs-G%wyck7Vo+C80&`hm#NctJ;>p9KgC$T(qo|LKf9k0Hw4Z5fG8UD6nHMuWzZ$N{q#6rhN>mlAyZ00W6pld6jp@noS&Tn3UD-1<CVB=r9Eqe)NckqWBgi2&5(H#Lf(X{-wK51xwrHUm}AU?nfxBFtSi1LUuWd;)0H7{4vg30k5B&qeV5e%FPv|d+<3m+<|-+JzxH=^1UiF3qcy`Hoj|t=jWizpVpBoS5!S`uFYz&AB?=W2@(uaA!{C#Rzbz?Q1DBg>SIs9*KJ6S^Xtp^7&y609^`De`R0`M|2fX+87Nxjv?t=(6U3^3b7L{m;VjWfyd3wA4%VIn*r#UZ(l~WChPSI28O%d$_u598%JLyhhb5y_3L&45{TK&f{1K|Kh(L*H-;vp<Dt7LBHk_eOj?zvH6%9(xgEM}?1IcJn3Q4kDNof#ZCpO6|wKVU?Wp>IuZGJ!D}C7TI5J-!{3gJB||D74=8wFA1~(bTFy$H)!AZ%UMtE^x^~_}<Yyd$lt3!(C<vBUwWnE?0<ZG9Y-eKv7PmtO!Mn5R)%DkHZp96)q`<H;x+$$R^oSA=8H}_fJ?UV7o>MZDTy{JhEC9ob~6dZIN18{GH;Pm`xiN{=tm_Ir>@JWay;wHY<rsysB1$(&}^p@<<Ky&*98wiLt%jl-W_T2Uq&&PBVxtq^W4VE3phxS)V4PEwz&=Wm_sz<#p;S@oqp=AvY%0d<|rGTkXD>dNl7W0!9!Cfo?U*>a$Gf`XJO$<0XIU?edw@92M9On@%AbVI|(YN#V%e!|LI!$_7@mVzO@96cw!+E2IqbLjajvsR0vfpPBZs#A~zKM~PNr)g{HOiYio2FL@ks+j6-d#a2;7(=T!<cCtAZ%xF1ALDlq9^><-0>|iM<pL+%i#>S2nwNw|cq1g<QP8~pz%16esFr_G(@4!FBa+1P}EfZ#5eFegdrS))Kzzj&qg<FahAz+>+VfBetDM%wZFL=V+Gy&hJ>0rf=@~F3cg7)j$?5Pm^RZ*mV`NuX}hgUH#XzUf?Fs5-%%Q*@pe`w*+$d*fPBkA$5VzP6X+a_0FD-*^*x#5B`Ec&Jt^~W#AL|9wgjc6Xo$b!aiD67Cl&f@qCnivOa#yXYTMrZr#v?`}3VJ(J63H^kYZZ$~H!sVS)VG~cMwZIa_RJPwKsG95)>XVjMG@I4~5AaUnifS6#^%CF1y3>x3d}UGz0tq<j*>;5|y8u)$)ts2MW?6THCbpCwZR-MgAj%an4xvam5MwBqdY-Fp$S|_%iWoWSjQ(m#`jx9D#=6N~<9z$8uN)r^797-*?~OJV7EP0ciF)aqeZRoDOI1u#&i1;!QNiXzMPN*?znL~i@Va#1T-NH?DUv50C8aO-{F+7c4E@K7a0D7`W&wPaBLbvjikn$m-z_&pL$tASqlHyBvSy~1!ZNDRe;pxHT)6{y1|@mxN|0Jn2O+LFW7-q|3mwF|I(S~Rsw$^)mNAPKZ?w20!c@W8!5n+T*)A!Wv9u^H;f@wr@E&E)5x)_9+{S&(tT1!Y0=e#HuZ{ZF&^_=%Tw;6#orcF9Q#6wsBC$9suEI{Yn5=tw)1$g6h+UJjyp2)=64@ayL^=<4KD)BvUG59Rrn@VPTjPh${0Xg|UYu$~$%lw6(-Zvq*-PLVLx?M7f?unyf`0ur*w}7~3VRXb1A6c@zM%AIQBh5uvGZ>0AHgRFJ5x4HP(k|p;4T;c88Tz!!7eL^LMc>XUV5zGTgv^9Wp9YeAg&I~XEWj{u|!AB>2Ydm%{MWtZ;}(fNg`puQ4IAvi#+g+!OLT9wk882lfQF~2K|3!^hFq>V8h!H0lUl)(8{NB<_Mw(4=Ah2{3ITWZ$POBQ*<I$SpdpR01t~=jM`tp+zO%(tbZ<$&05j$R2KrT*rL>&&9*$I<t{lCaA^&xq_7|dglm47nc`~0a4n5~F!jS^c^A#B1#YvokmGNwm|m(OsN~_(DAVwr3;YG9^Ddgm`7m3ri#n-FrWR@e&Kmmh8mz~FpVsu}*jkB^g4jK-Kz+ebnONr#iMUzWZ4Q0S6!OHQ&uX>*;N)@89TNP+ZLxQiD9FZf_*JFuGGYorAuo?buWMgwiN9uTW~{;ha~{<hX8SECpbiZW43v@9h*qlE>uQE+d}l>dr;}b8v7!Olw86sc3cbK7ax{IAf?L95`1q{r*|kwDfPneRMx*)fZ0d-sOl+4e&P36Ee$HN8?F$7(6rXBZEELhnW}|5l(_mvZ{ad#r(a?|V+XQdV6=y%1t&EaKBf0s!y?yu3`Ho4<mBKUa&hfN987-&jqmc5kz8w>iQM+okrN_$p9P|dMOoMqJ;5d$we@`-A*R03HlN_fZ26jD_20Z*}XTM{MFq-*JBS1BZ5A|&$VXD}Bggj)2F_oQg74iVXbJL37I(L8;9fPTcs2XKxdR;OrG&HXaBrY&;Trq)UgZed<<GM>miy27BX;6Kpyut%=hRlasu>`kFqa(Ve=nE}S*y4;?h=jp)FB}$Mp9H|r5UCh$R+92ieIe#Q4n$m3^p;Q9j>);F$VGac=*XvpdWAuOecY+Pb!hwX#gf{#)=tg_788J}=)HTw8*QEIha|6__d3k`ffg0k=#<(wZjHAAS__OOyjhCuHjrTD<P+In?2MJFF$pHrD2w(_df=IM98wmsEAl`A7{FlDpttAu3!I1G7-*b$g)nC8B#k^D+N_WlMefbAM&PerrRP3L#%23+G%&kas&g2I&cHqSCrcxX=0Quy2N6FjwMCb=7p+*p6Qw}*_G7t{nY2u&tvnbdgg4&wcNWC}XB><L;&PX+W|B}zxDf=DKHRK8X<|)km?UAdKWj1iT+zHmJ-+B@?~0#_QlDt<oI@QI<tLljlTvteh*^OUT1sZnABCaR0wK7{0Rk6qCH7z7qL7VRcuRT^ik&L4cp@t>Ubh1@`EAkzHf)<c0U9xmlw2?#$1LuCRi=LwC;V`mHU;F{P?e({&||g5qU6LD7|;oXOGB=|%?{ypCQWLGM}O&2Eh4voMt@9BPjW&EZQ?B<ZboSp*_3#ejrFjX-EQor*M%NijCby)Pww_zzKElm<uhU`_0$#s7rozkTp-HW4UT*z1QMVS@weTK1*s%vZh9ec+E1O2l)Hn%s3Q9`DVC!8j?~P}026LJB|?<28b%pmgR#}YvyzM2+T?*Hv=hEn7@8|<>zFI-Cj;l?>Y;KOJ#lj{zpe^hi1ry<$kmC5C|y$Jckx}`*~~77u*<{`w=B#zVU5fUgo*K>=bP7Dw3{y1jGLOKB&Ss;zR)kytEd$aA{8npB`O(+!Ul}$R}ED^jkOm-TsA%;k4O~wYHAl_uiO?;WO5&@?j<T@7LyNOHYdC(l(iFm!3!!qk#EcxN&9Z^bXW`zezQVn!y+REj{oK#3n7W9F^m6mT*Rur5YhRytN1WcV1N1g8VZA_K+BcJh)6>|XZ6#-!8?)|u0v}?mz<w|@W28DDpz<qETrmi!Y=CM`&rsaX0aHtr9+Tagnz04sX`6ESMJoUh~DKI94zimLjNX-gB*%;+8f9?ijT4zoH2=Bk|?WJ_Rja{jZDg6-41i+dCfnnfKoD!fLb)HOOex9gdSr-?{%!+A!C6s*H*fCjLg-a^5{5NiVQI2OzCD7Vu+q|kz{7Q1pru2v{XR7eY!Bm=@t}h$!*<k#=}$0P4?%G!Z3WdbetKcc-`XHQi@F+2;KNwP+lML<e3oGunOiP(r2s@R5+}V6;y%^+LDW~s#XnJilw|9o#kbi?zONH>k*5M4#(X7enWjr;Kwlj2qBrQSO^QMDY6~8v>{3lEuE=)dNdbioW0j8wP})!A4_z2y4i6kT$V4cG=`@^Ii+sPYZ@w*8)be&wMYwn6N+Ou%8V*%r6$}nQ7&8u+!?LlVUiyN!)YDaJF7ONB>6(JL1Sa(X=+xyBfTJ-<KC7)YcXBuqZpK^f@JTer2nbJNO(;Nv1S@tsr{Tr<s>PU1*JTLZx$dmwPAUW>JnXM4ebY`zERtcine-`nj}Ry<k2xpTHqvUi&j=BL6H&B<vnC2x+rqwKxTlZQ&URdqxx=%>>4F}1gz%^`e-bv*Z~llr^3Kd#nRT-YfR-H+nAtlBDy#;`Zqq@t;{3_5p-QKE}7%vv`hjFR@5q}Vl?JyIkKY(Ly(HL!1b=&C%<@FU8w~BK$}6(Ij>8iNi&@TYLIGx^+d(>P)bQ+1I2Y?0^Vf&^C3tY1#9ug6$Bh1IZidJRl#I@4{5$YX_X`={NDAZOArQZ$vcuVAX|VopE4gdiM33rKi8ne<PQl|lu7GVyqYLvROmYMP11IlL+ohV^8Paf7cC(?n->wowJ1x*BUn<iB)tUjuu|$V?^)q1fsh^BFUV4Gf0mQsN~;CY3)!P&gwXA)ttTl{9BdYa7-&`Hxr!paY^00$(7KWuX!SH+qjg?ML`1MmSd}1UU=RjU@*r{5(rP*2aa2I8L+Lkd@}N_eVmZUvoe#6r^>Y;CVmZO4wy74Brv11@Hx3lUPVTctnm(QbDxDwCEF4FTP<s%BAHh$eRe*Hs>*ZaX#gi?)l1&>sy`b9~#q@I9_w(?XnZvctV>y0y_$ZMe4+6v)EJdrm4{e8}D|w^AQ>`M}Ud!*_4VXik2SyEF5@uLc9m@wVmiCA)P<_gB{tTK-4FH9QZ}4MSkq~jDq#Ps5z>R5LQ4*ack3&Shv@Ua}tu~c(HznMZlg=E?MrRH~^+&RFS}_K#+L3%*hrZ)@U8#^OX;N%S@Qqh;E*VqbqBspKA~MBveP!THIZB<@J+Gr9Y?Xo1rkadyn^SmtU_u19VG~K#?2<;@{_sd^UBkPTsr~-Qor*O$w`);txI94q5EZd2%W8$93);|9ab^~VR?wKTRTJOQ>MN9EBx3}kinSM5pU#nMmBp`a{q85Gz^co&Mho^aN|H$ei{vMHQ0<XjHBFyuqML21dP*>LD=!GUw1_L6zz+ahvQiN@`$)WVR(0hSV(1-cipbEO9-^PpRx~!?2bg$j`&20C#X&#-!R@@il@N*@SDj)6C@(bB5*GPk))PWPWGIYG6ix$L@k9}hHFT&@@Mg7_6OuAkh1SLvDu>bbP12n^=NC|!Z?7qtDZzeW&?I8QH;y<)NfaTaCvu6YW6S+AH5|1k##iMy#m3YcZlEm$jP_B=Ldtk6tLX(hayJ^tt0@%y!)o8;N;fWvh9T>vQm8*j=Vo!Xb3GrfX<@Ty>V=P#{6mtbba$>O{x=Cer1a8O)KD%y^|$3zUyZN`mgI9@2}`ZV?(t*LYNYwoX2UcQM%{7B8YnSEle0@mCv>XEEveROY@R)qO}`;r1eNXdlANM()9-|wI=j`C8Ig-yu}%sgmqp%f69Xv+4ZVsiFoe->jljZ*2gzO~7KM`!r6r&Sk?Ugb2a~MqByVJ*Flo>9i`}70DTvZKV6D?}#86enxC@)stBMpalZO$#bPiO&qA0e~6MnL^%cjs5^KMy8BL@q@>|uIC^a6L@R!TFF?XEQZOh_^pxtu=l5=ZNC*Wm9^9hW|lhi$47jB>VG&g-FC5tNj`!t29Q2JDBmNIhU61Rr8R1k;9QwR6AwZ+H6ws|N`T6Xj=CMjU@G_mDnS$8U3GVTtzNwz)d2pv>viP2T~mxhfEIe2i$$M!Cr9={5&YWMw?5Oy9Y#sOxxyoYJs|YN`M*PIYwUbFpIjOns*TT7><E9HA_mG&<bkZd1z2dVC~9hQ=8=RsI1mnMz)pLnV9w!}U5>MfJqs6WFO!0}#u3h_7El78y{93B`EBrp=soEoH%E##dMYs`$`iyz)mL(hg$qI`2o_k)@;QRYw@hS^<>bh-WUkyC5c8!{kMXY_{9>a2#g|tZ(sdvo*sM;45miLrFyN?J8SN?=iYNSzMl*0+b8~!pxYSfF}1y8azr~ktq>uJcT4z^thyDlX5=<ZZLWslil8FvdDgbh6&9=S+|30a}Dl#F@w^hS(ca_m%oGE1r-q1BDoQrl7k3Kf-u?{V=M@Env{7ZM^e`A2p{)=C>SGb#z@mc?HxU|_Y-5)c~F5Iwy2J7$l#RtFu5hPH9ARWul4&?RgQ6Ta&B%hf^z$Zsuka8Y=r|3rbG?Zm~;3lv)%0luo+-gq`h!a?@}ru*IdJxi>&sE#cY`R;1apHqA*2TKNlY~p(8NvK|#h?$hVd-i$b(%z70F!QVN;PKFHKnG(29VLJoHRTT?Zd>D0vkOW=*UsO_D@meL(%on3}4W~RSP`zJHE#uwAO>QJQmjDt~iOvPTX`WWX2j-pUO+syDnxQivED*--MCApt7J9m{65cWGFakC?kT#()N>vQ8#jcPbZ=`soZE9GXzgE3|p3PovN^DMWxm4}g3Aiq=`9in4w-4(>DL{^KIl2F!|AsimUoA?$E7)=|obj`d2&%7}m5qLtoy8ac-=eAaPiRs+aHy;rUp&gu17;gx6EpfOKYYvk{K`JW(+N?)!O%lp<=&VY4&oWwyP?q1O+s?5BLIg+xP1HFX{c15a#)yQl4&<yQW23vk`bAf!6pqArnoOFk4e!MzhJh|_zcQ0Xci-OVYGc%1d<?iTY8Q5-XR(lE2B>}_XPkmN4a%y3k>f7NdStP^*_3duDi9FmySPjGy_2j)JX8QF+J@ZqhP!6D&*XdIxBEf~oagyB-$SClI!a1m^@Gt(=XofQPxfYcqgyAExRYt;LB<DdDf;-Q5BF9RgmHtHwM~%`5)X7v!Rp8oR*beKqdb{o@?g%S+ve@KM%3Q(`jv{;&4NtI|5lWwNO(t+ysjO))tIh^MpjDHz)F}=tFD3&K;uk_nkaJH2O)iKi^9S&nrzCDi-u^lD;5!2n;36dKIPU`Pq6`Xm!y^(2p6&0)z{?C+Fc7SSK7<Xt_}11i*qSMy6N)dLdBdL%MRqWKwK_bM$WTcmtLOka=*f21SbvWJ`vJXOIOccUUk+BT?Y9StkZR6HGE`!1SAkXUQ&lfBA~v8@1<tCkaWE%KQj+t&vQ|Sm#RTZdXsQM3si#7iFcx9Rj=mA6GP+r2*9_sv}-BsFaqds7qOtQw>&3Gh3b4~2g7EW+ziuB8b1Agm-bS*+qWe%Gg&U0rV%a9S(%msN;&hw(`e!>399{_XRJ!So>Jg@?^E+@vdGOY+c67PBgiC6$!75@Qixf8Li{DNw5%SQBP@TP_Xhu)TBW_Xo-Fc}`+QWVz*NuWt}N?m@7H1aRDWhB#pqq->6c+AkCqDs#-5<2at6FKaEA1p6G`JC*Fe*LED<{<4p;(|J=q<mYDN*oG2JY)xN?W1-d9GoN=Gk@?mUHJ7uipyNF3q+^-{I<0^U@VM!K3?d@3Xrk&97VKVrGp9@=d}mO`tJ))M&zwnjk~YjBF>!=#$8|B8L_ymB)nMsWA~n-w+OhS8k7Y10brn`S58#r2CT2lM7vtb5Z<=FcpCck30AI1*Pd>=`1qfV~ScaAZqrXvt3Np*1@=5s$>F-z^Mnte;JViW(@)d6_z`p1$3$(#7U5oP1c!>2IolBFfZNDt_HbgmZdtwCrAe%gk$cBEe|v^bD3AVi7mXKBMQJ?N!P8?dCN+19`Bza<9j%RI0uJoQ;H(=cg!BsT2j6`*L9x+B0{(qMflh53fS*raPW*z0;o8AuQ|Axh(OsqE4m0h{)k$seyM&$up{l*H|YkV6rxo0xf%w!dcj2W7UudCadkXTcyEuK_o_ta_I#^X;w<J#3eV>O`9@L88%uo1(c~k3xPI05VV3a@_O465ulYo*|C+%#Ews>U}i`6;IIZ6*`y<QsD#=8+CYHq$r=NH=&^}19<aR^h*wxxa5UKOg=-~@!4y;(ZPrP*vdb5T91bqRF_}pl50VcV4c+Uga-N4PL*x&tGU_}QD=sOuA9`M$GuAzAN%W#a*V)tR+NyIP=xIinH%0V22QbzB=&%+ZTARLc;WYu}Oe9(Z!yUon*=9?yURGdTKCixbpk_aekP53!kVTITOHxpqE;UXybtHR}Vx#NuGMOhulccSR>iGfoMWx-QJVWP*ar{#~N%L$QN|e*Ax5_2T-j{_^ipzaXUa!!Blc%X1XdG9%l`Bx~iRBPssU)EmJGeYIlSGyK-2<6Os^U8br!F=H6>1{h$OM2kk-WCKs5JA#y>TiufE^8W+0?JIiTHg&V35ojG?NHQKF5u*r5x<#;7H#}e1<giRf-APkH4)>JzS^jNmcBInx(iJ8qhuRB4##ttLbkTBibzn1Y23tC0!!o&R|=owfJPCq=!Qd$JL8N5Corf^7;~`P_1qX3<WY&<l8W6ke0nH)MGeQ3Xc*>drj`DM1`dS@V+29CDhSW{e|&pbbr4nhUF%%p~$@6Xe+RX$@t1}cwo(yde4HutY7#|;f_+-tf%8o=U``yQvqPk`3GJy&k^m)uao_-?u&v~Z&In51}|-()kA{tN`!7Z?8fwP|3Psjr8oQxUv#_Po)}t(!N^BZWl@F?d{t;HEDHV{(3+08l>e`e%Hv^GI0+!YiSH1$*g-ECJqEV~Q@Aaw@nXZ@ZA-pHp=-HioS>dC+3TNYh$k_Q(?}9riAYb@hlcj*HhfNMAI#N^7RJ^V9j22a)<R1{;wJh3IQl|Ay{A8>&vw19unD52c!@V)DD{?v7lxVp!1B)N0M?mwzjAS?#Vl$DB}_=M?-oBSY0)kRKYz~s{{d^hQf&")).decode()),
}
_SHOP_TABLE = {"BAKERY": "rb", "BRUNCH_SPOT": "c0", "FARMERS_MARKET": "rb", "ICE_CREAM_SHOP": "c0", "PET_CAFE": "rb", "PIZZA_SHOP": "rb", "SMOOTHIE_SHOP": "rb", "YARN_STORE": "rb"}
_DEFAULT = "rb"
_SEL = {}
_MKT = {}
_ACTIONS = _TAPES[_DEFAULT]
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = _ACTIONS
_selected_route = "v50_mkt_router"


def _mkt_route(m):
    dw0 = m.get(1, 0) - m.get(0, 0) if 0 in m and 1 in m else None
    dw1 = m.get(2, 0) - m.get(1, 0) if 1 in m and 2 in m else None
    if dw0 is None or dw1 is None:
        return None
    if -30 <= dw0 <= -24 and 12 <= dw1 <= 20:
        return "F"
    if dw0 <= -31:
        return "rb"
    d28 = m[29] - m[28] if 28 in m and 29 in m else 0
    if abs(dw0 + 14) <= 3 and abs(dw1 - 3) <= 3 and d28 <= -2:
        return "F"
    return None


def agent(obs, configuration=None):
    global _ACTIONS
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    t = day * 24 + hour
    seat = obs.get("player", 0)
    if t == 0:
        _SEL.pop(seat, None)
        _MKT[seat] = {}
    try:
        if t <= 33 and seat in _MKT:
            _MKT[seat][t] = int(((obs.get("market") or {}).get("inventory") or {}).get("WHEAT", 0))
    except Exception:
        pass
    if seat not in _SEL and t >= 72:
        sel = None
        try:
            sel = _mkt_route(_MKT.get(seat) or {})
        except Exception:
            sel = None
        if sel is None:
            try:
                shops = (obs.get("town") or {}).get("unlocked_shops") or []
                first = shops[0] if shops else None
                if isinstance(first, dict):
                    first = first.get("name")
                sel = _SHOP_TABLE.get(str(first), _DEFAULT) if first else _DEFAULT
            except Exception:
                sel = _DEFAULT
        _SEL[seat] = sel
    _ACTIONS = _TAPES[_SEL.get(seat, _DEFAULT)]
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
