"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rl~U5_NmajyAa`noRs+aq*0BI}668M29);c1*D8UnH6?hzKEb}8<~LePKTuC9y-b9ZxdGY`*<%&5E>7OT6fBA@V2v)5kx&rg5;-~axv|Nhti`1B8d`p-}Q$DjZ9Z-4pQw=X~a;fJ4p{`B?b)BpPOU;pLp&%S;6Z-4&V|Mi!@fBX7RpZ@WW|MQ>!@YCmC|M6G9e0urx<u|WCeEVPb_2o~We)HR(UOy#Yy#3vuUtfRy?JxfB^~cY@|MU{GZ(shsU%vgr?|=KdAAbDy2S5Mj_4N<r4=x@ee*OAiFUbe_?XUj(AODd2u=PXz>C>0jpMUxO!+!tyr(b^a{j19-U%r4Jy!N9v0Np>j$~60(|M<t>{`l*E{`T*G`QvvC;1_Pcr|ZM~_`|PWS4_zd{`N<||7CrBy}#hUy}j&|&=0@7{`CHji{G&R+{>>be(<k;sFT=!ML~!7iOb&|&VYD(EEw-&s_!kX;}QHOKIHQ4Esyy=Qn#lQ0V&^I$zl5i8}gq&|55%9FaM|)0rB$6SGN7GAybf|vi^cL6l4zW8WrX1D<2Ob(SFe7AE5}ke&XeW;=@5caFGWbGYIxB5p5EkYeaMH;VcoaKZr@^ClUB?m+?1h(`IbQ9zVP2uMHUKk1h{0*m0@$v-6LjTj!3RiM$Pk^b6{TeE#vr*I)he&;RZ9r(b^i<8S}B?=NZZlOgMP$D@^F6FV*438%hCBMvQKuc$50od>sKQI>5M>8xGXhaK$7AKA6plt1SE=|vk1@<WiP-}_)qWXQT){E%P&^!X3u54kMd<PX7aH9x=p_;!;6ANXy#!j?JPTIOu+jGyk_j78k!zv}(t(^Dru@AqE}n`gNuLYpD{`In!5`0|ghKmGJSk?jKcaO<9)ZSy5N&M%-pE@zzZpZFRZeQh`9AD$)aG;{aPe|F!dB--0r+c&c6mwO#|$|2iT-@eD&o-SYQ+}f`MvH5J*Is`2X5SZR@UCO@Q#jx+F(4e?otcp-i@1;@_TcEc3N>rqCmzO}}?DOrjDdUi~|NS8k)_i+?ClJw@f_J1r*Eh+oJ1WB5eFAgU@VWhZpIfouxWn3}+kw=Z-mwJ_#=c|=HZA5}+_Ax6%l{}+?cIod&!!GEjIB8P*PX`}aKX6l{=0jOZQF0L5zF>D><6_!B^AoeL$1BYfh<tjx9w67Q(b^xxH}B7RiiJE@mYvHmJfuv$6j`pt6c{xv4`92u=Y-m1J~M^*OdLQK7V2D$?I>v`~%TNhTfc!KOKLa9vI}6?2Ob!P_i{ryU(DVI?pBD1FJl__H7jZ@YDa`KPY;G{+>*G8^+0}UVm^krnY93noKXhmIxj0fV<|<))l_%CJpwwTIf`?rS}C&kOzZrcza0n_4H^Sdfo_iN*gz8kYsK%S3sU_WpjnRRP^Mb%EJk^E_5kFkaHg+3Uv8L=p+#QoP59X)lC>VXnfB{U%n6bJ7T|<-?8nUQ1}b;PTHSuU`EhiIyZ9uae(~RHSYACA4zoI@BL7e*63PqX8fn<iRaVu!=ASTS6*Zlu6}oqu8)@!D7XFUUl<j>SPv|iB8;=Ix8CWxcCTMl?$hO8#2|={J?l?e&wN;HLjsi<b}2uLU<*TjNB*yyUv=mhSWmwWm;GsrDjHPTR(_y-rxvC0%j3@)LD`-H`4(R&(igZvzk{%rXhB?m_~eDBk*OS}1V=OBBcMbo?|$^hFV#KyNHkac<huff>?l-E=BQ7~Sw67A54pFLhrA3+N=eU9&GXE5G@(Npd#g6sfez$ijD4#k4}qV;zElrpokz6FafH5u?UKS^r4#kk5@)kPN5v9N`||nox5X*cK1&{{YHT>mPm_uiE)P@eSM_`!Ef}q?M1dJbN76G`tUE8@K!x&^_#`W5lDs8tYB8Qt#6sq!82Z@km1<RcH2D0@=ffj}#aHF4OkbCi#VOVmkT|=t&QtF!3<v~~Z?8N{)az;RgCupF*e0$h`}Q56Z#`9stSQv_b|3roC*k3SoKwWxYOZ<Z{H@&@`hGr9J4F1V`U=~>G`y!n$louEGYG!jE4nC`t5HJI+QYMETl4r##<P*%(NXP|&Qo`r^SQxyMf0_<3>&#+z>~ylvGx{!zefgGPI=_aP(H=Z!k_J*uS+I&63mx?-DQc`%1N#>?~lhQRxB12<ZOd|#LCobR`XC&w%RGCqS`7?|H3k$azQBv3>FK$%^<3L?B<(gji~M1ivJeuftv4@Go~sxtoj8`{#vOahO7-uc_2UL)|26)Qs06EGqE00*K$EDn%oZQn=w+4RYZC^NAznR)~5>0wkPUeAIqPQ<V`TWW3h&hT_w@8PUTtq)<iP%(7gy#DURl1h>U3L62+^WB6X`((MJlrakfEg1_X8()WNoyF>KbN*2g?j*Vud^)zgdZRQ+PZLSAs29=VM~6XN;>AcPG;WCp2_;5c!)_PoQlXKMtwg)QYqgq(89Y;4yFof)^oc3tM*YX;$o*-D<DkxfIC&8SUP!2zok?Uvllc|H(3auWUGeIz4No*KG7bUFOiw+cg_$c?J2vIY5d>^E5Xo0Ysu^OLjO(&%u0aWp}-I6YIKjAkM?F6waFQIA#Jr?BHZxga!8q~*vSFxSh&Ootx_au7m(Fi-s>`o+kG!io3x6e1(CA>=eh>Xk%Nk)?bC8)MsDryjtU2zTjxN@eJjnXg<BBvT=gzH&YJEnKy;&(N$KW@XSf7Y)hd22?RhRT4xzl>7-O28a*^ivTl=^*VXbzmhMh>Y9qpPcRKviq|rK_Uo<^E?0})pnnnlCi|w~s|GM+jI_MNtczXs@_;2z+P@RIr!+1M=r?(3zvhHP&Wgx+hP+1fthsy%%!-TuPxd5Q3B}C|QEVlYZMP4V*z1KyS1hK_7Vi)TOa7sL{U^Wv?LVRCPT4rbe+h=6y<hK_vXhQIjNp@QsJB>?wJcC7m!eW9ja)YQRbQ+H0xw%Yt{sw41FgnmYx<iv5DAR(1+*#&sN4s#uJ%;TQGs$olq5N+bABnZD3S-*o<avw%Zjds9R{_$P!4-F<ZGMSZt-kMY)vxHsD0sBBfQJPEF+WAx<NttP$oh|<H+oX)21CECNCF=^3d*nC`o|`U6kFt4e846&41e3;ok{FG1T3NcbDpS0p%Cs?o6&Qds$d{B|`oFgGff&bqahX;KZu9uy{j|Uga#Mpdvq1U0%VfSYp1wo(O?%%M>^zAKb6{4*A$qkrk-T!z`~jx6nNI#-53D4w-9sshldiF4OFCLxem1+^zU7r^cr*?A$snU<HbNX%}*MWUW+}btZ5QAjLThL9~7f!rrt}Ek#}O%je}OVA&NyRF1I_9I%x%J>@@C-5C-~sEK$Pk4e|f?@8e{rY}42gz&>KZ-efYp54?9wK*lQSX+5NL#b|WuzXZ<Dp2VcSjO?v_4KW&(4dKYXyOZEehhNSE_Vf{2$*^o^_e3&Aha%x<z1+B<Z2FTf;si@&9OsOJ(8PI;Q>Yo3a~IF`H^=VAj(q?dPpdz0ygH6b%<4c3HP$vdAcvxha8I#Cj@Hs!u}x=gu+TWD?4?2O3OEEsz`+ysg@})ch@H{rY1V~(a1QGplyjds}-B&>k-Gykk5u6YLhjgX-+}EEAGsyekx2fOe~~iQ3uQDf>G+%T;JNdNt@+!%3K4-p`r|f?vbS&9X2vX9yjt;(Ji(I6493RXB2CES0IU}K=}6le){~&<=+yGW$~7^jZLXaRUD+EVpHToNo)Wu@La)zU}v`Now*UzBF7Z_{6|pPb%;guYoeND!j<wxY#zuLxKG`|Ffv1nMGAU8H}Y=C0AKY}v4du<`Xh1{(lt^|0Bmy{WM4*B4oMXY{}xNWZHco#XAVhg@QRbi<t?`7PT3q4{A12c()(u;eRCAQ0;Ul`F?+-@tELjWgo{OIiH#24K+7Lit%Mhy5-FK687x6NL|-2Aa>!`SyYjCIj*g}^iD=_b<Qb4}p~H%flJeWU#qR5FQJMfA8T*iQAu@H_Metzlsu>fk{J8X?P*CVVeN1|Fp_dH=0zU@MNVw6bJmNF~Cr-7cK_xFEacAMi%y?O5s$w5Gsg~E$TEx3#ZzZ96GB#GKEhybA>XRjKIpsaLNR5XTN)=Cryb(n2RB6H5Cx#|2DP^?2c!q5oY;VK04zAr62~?!Iy;u>CLkza2S6(>@L`5iH3TY`;3tx{5QAINyo^`d4Kp7i1waN_dDCyhi@_R;ZdiAm<j$Lg7yF4!EZWov1mU8grTaCacJ08R?VXp`07_Ga@5lwBY)W;B->DHgR&j_cdoQ9S+N&R|xAvn}cwLA<^HU`Y=X<L=0>yc?M7AT931yn|yYirCn^m|E`zPXE%$_P$GP867-<{_!Z!*7Utx~gr5F>F3jcV4vct$i)zh<qY%W;MniS?<;n7`9r7W!-*ae~c%ozG)pV8Wj}S?SkDAYlonazWnoU(Ou<S<zhpNJn+|EyB~1Is@pFu;O)l9O$vGS<S2Dt`37FpC6+3NYK8vW))m~`0%PKkK+|Y;z12(a5nM2tS%q1I1#vC2s=f*`9n`gq_7LOVim1U^J}cpvLzm5TI6ZKDo_WVtO5;H_hWYYZH6`IWQ|uFV(QRj{(qGrE31Z#f*N@1y!KkIhU)ZVH(u2KxQROX|cu%56#lQRQkN+K&4V4et=s1khm%k_0g<sl&nSJXkUq<;3$|ocW>Wa}au8s78S|c>3F-BQLss!48*$f+vp;{dxI8lrJ_vBV~$ZEQQ%0m&1XeK2Fpsn_>R2Ivxf}KOzliFwY5fXO)X{S&2N?_<jB318zoDrK@5}v|^8~dQ*R)dNgsUj(^REU|ItljMV$YDx9DKkqeDv!<Xetx(Lg;ZyeLy1|R(;+e8{r>WA)h}fug(K8llE)p{Be^_L%Jm>4^Y6`YTKfnrRCJJWXI8G7c=|3i1|=e<o~IRv8&<7EdRVcZwM_i7Gt736TA>ID$`F6y1!Kwa%X$1}_@reXM!1*OOMm*jT8Tpla!Ev>RwEz1CZDvg0;UkCTl-|+*%4H!=G^A5dtejK&Nc>OIcruQSNtxTAwjGsR;gRzJ8*KcY)JWJb2RLU95ky{!tEjlgS=B+yD>nk`lw;DUj}ZlKQX+116&j^4p+24ODp}#ewUn~$J+TNk&khq-#vm0nO=ccaKm`9vD;$}iy-hkeK;4<=1ZxUC~J<OL6j@*zs<A8TJ^cvmkToRKwKc`u*1L(TxD@SIgRPS14q!`dsuJHP4a?9#&yW_GQQ}}f<#`U2L@Tg#uRgq2lcuCW=xmnG+I^QLp{w%6RIEi$%C*5An)<Dh8Kd68()FKZ3Yf<XQe_ZgUA~}HS+vuVLkE4NfB3CW;e=0X}P0Rw$?lV6%W@cbZaN3G_&6fvRa`MxJE3US`og>CM60PO5lWq9O@GZI{(69ST2s&aL6M2-SB#xVrQwQHi;=trM&l9(Mc*O!c5Z0gs9YZ$B*<-)e>Z8u_0K*hdDpIMxG$}IzgHAhVOYrM}x5CfvIs4)aP*)d`dY-zG&oecPPX#+ZvgtF%2BM=p!G1sg!F8X?P1Fp>tioDE*Ght99u-RClf^Lr&$(K{`Fw6i&!S4X^u)6^s6QKh-$+yHO+El^f+bl{gYFbhR@)m5fz>Sc>zqt0={C8&WMx&S_2<ufvU$ZOe=mFA*u$F27y6x`zrjx2|;@b8Lo6?S*|I?=AQ#D=Va@!U_t0$rZN9$-h@6L!@Qe_jtCsw#+xVx|$PlXIapqb^)P=YCY`Lyi@Axs>Ux@;%b0+O}RTR{N-&|Qltc3t@4ltadRO*P5SOw1L~z3U&n6uFWEk3c1VhV&qxvY&=Q$cD{x3%;l$@BN=BEY=CO^dyy%oM0ghSuUTIy=#g6`pvhDA>FqIRZDtK(}Kg~$-YrE)U8S*d0cj}*~Z^K1GGn6^fHjL7xKpc}6iSWw)*ks`)J(8#y!Rqr&O7f5^b7NeQ-AZWxCnVh6Jkz`nsrtIC8A?86M-g^eqcGq>*;<&k<HI`~NA)|z@lFe6gzfH8%u5i}+>PaqzC`I>u$yCRlWO0iOl3(~dO(u-!aikZ`Qqr4pSUXvGVJMf5BX^6vMF`6Z^fZpyXL7Ck7k^fh+IVbLY5`GTQQ94cd8$mE@i_~E2tEujI)tpRP1!nY+YZzol<U2ln2r$5+q>Jv%Q_!O$Uu6*><?jG9!9K`)6`!Uz%RMwAx^CRAI<i?Nx;_!jM-s+K~!j#33$EzL=W!t-eo+HDjgN06jjE$te0$<2y$fBMqaJ@#2%ZJd08NG#!F5_OTuPi#*dOL0w0)%Tz4@N*QXB{r%)s%R9wnuZ&n!`r$h6+UW3~1WjnD;~<?R;JWa#gPf{Ztpe}bG7Wd?WE>mouZ|(<D*8BAoW8TWKyw+u3XaIg8b2n&`&4A_wmmm8)=_{P*(Ndzo$+5gKwynMRqcYs>`K8KSeBXmiHvncG|foI^CpAJO{^V~Bh)ZRz>98z(P$)FMt@`(t1){hHpE^9avDx{$FZ_IWyq6m2}>TEt0qun^WAb>_cx&D%eMr6TlCGmqcunCDJgR$I&E0Jg^2><_27lUExj4dIO&rt(_jcJkNrwzM9@Uo88a$UrAA@pQ&OGmvA{$5yrfAoC4ph^AB40X>)6tX)xRQ!{_u`RgyEIc#98WnR4&kT<>6l078OJib~I!4FKeW6g#AN1G+yE=ww{<vkE0SxKrj0ooJSqdDv8@OiLB@ps+nHeXBj=dcT)3oNk@$2(Sa@}rmDXd+jphmrhU~xkF&vDc;!(R#`QJG1SPy_K(=h+NlNiZkzrm~!*z|@o0iy=_^kFyWnJG)TVqxp_7L<fWdj)s<lK-Max#%Jh3s=g`exy?3jZ$OqHpe53Fx~oOMlr=`?OQe<&)FrDRdd2PJ`4rich^&QOPYvWK3nsNsniaCWu9~R-|Ul4==V;nzeAn8ujM8{jH7!me{;cMfucFH)OZ~1%BxW>qC+W73|=$K05LNnI`?B4_VnSkQ+x$=0)b<kZ0$~P?~iw3=xHC7O+!~N8SthHzGzJuC!{#B;W0}Y2=Ys9_?z>wb!OcsadO{=oP|PR#=sAqM{@G9l3+@6_&2(tmlDyQ1-K$^O{rlCjGuxA98PED`wEE9)7Mn!!sj620s>5;*Kpw=zH%AhLJi7SwxTPf<zxAQWcEv41-~-AzE+3G`b#RCPrR!h<gG|bym}6+^*Hc34-ySW?6ioQ8&P{!EQHiYI|+XdrHpmyL#K(nOEn?d>`G>yf5rdKTJ(q%Tb1*{NVdjV~;}qA<xX7OhYiOpy?GB9q*L?3UlBH3Xt07(Clk*De%GTfRNw{Z4d=&CmPon&IHD2_J{Jg9{E%k_Hh<orG%Dcl|+qwj=_9aK`*8~C`;Q&TS7DvMzv4-@+!RNYsV=`<al$5#u8bOxXcCQ9o5uN?W+pCP!Tn?<#L7E07;q@(snKa(GwzSYVOF~9xcM?HI{iO4*z(NEXu@EY#BFmXRIjact%)dG^}6y*j%oO)vqT16PPm+pVM}09SJw`c1IeHC|{;=E51`XjPcsJ({&t_M;T*9dmY#hiJaf9H`g#yB!4z{8^TgC;t~X83E(NSD0j4aJs@+;y^k=4%^&90hJ|3t@<CQ(NT!uoHt%1!)d`jzJGEqtRFnmMG$C2t{i`W4>$M-VL;u7y!*W;=S6@_)*Tk4=b;foWGrasjZ+pL5?Fgy(7ub&VnO-92j`FPAa&)SFG~%o4Hcvx>ZGskhwfefe*)#s3iS-mNYo5Gvaa=0~bY&BW@f$UrqRtJS(l%to0|i;%5N*{R?khfH&8~KV4{r#z>uMQ2Fr+bTUNf;Si#xV{uQfyBAkAAt--(l=^gM)pJSXtCN5)1^>}I5rcyo-EuTR#7HakEPSuJBlB2OfU^a&<^dBs4Qan-HeYoASC+g*EhzPzm=Q{#3h#sBpehW%CVi2z%GC9%rJ2mjLNgvOV;@v1P%)D-%RX_%EU@SPH=*_tN|cF}ypfqiG)wcx<TB0za^Qf4fK^%AxBH%e`Z+r39D2Kwc1yl(5vqd>b$hA8@CzIKY{hzgE&3xZ}B0l}UV1?o96hL7ng+qHqjhSsAft$r%55U#cJ)NlDzETMIbYX|;pPiPr=CF{3P864H-qjf50<~PcFsi-rhd*HyFm5JZP5wxoW^Gs9M$_dr63o(a=@Td(#Rz2NkQHGzak>DJyDQkb89mheI432SKpqvble<JGlTq)d=#0*-d%k^I&V9nMp;J1G4{><?|Vg)~TcZP4Jj%$G<K`cO4Wu?FN_mIb5Fcv<0<&}&z!qq}25h}#j80hTMwtC!!;~~~P^6T09%Aly}eDLfxI;T5K=}1GMWCdy#RB?1*Y};{u7=zZjP=PP{ZqZo(8>5NYU9V%;Dz6kY`IZw~HDlIev4>T+aT@gT6HLvl73n`rRvF7Ra0b`Fl|zkmpI9OS<z){MG_+<)XLkxx5{HJ0>1tzAL&|FrTnNNCl|_U~uD3xKx<Xg-yW}ao9Z&C)`6xl#o>ppu9sj4!>LUNNAr%#DDHff0=9MP3Mr(O1oVxAxsc<KC>S6Zd>}k$Ze4i;mDE-{Y%A7A8TW2I<SG(*mr3C>M2{gl@w6A_;jX+dqXqrChB~!O}W4gFiG@Wb-S@|B(oB~~FTMy14uXO#)jcgk872kcK=`~&bsRV8{w84fzPZEwJzqAJ?D=|b@%IaI1^tXJjkUdvglP~I<S)TF8u|h^W@WTV&h+(XqQlnIqjbG?m-wNI!lN;IC+FnAWYMgV;VP`NpW-;S*Ne6P+Z--Y~QwyZk56Z0x&D8ccoVv*PXqWY%<orzE@3<b2RHUKn5Ut1h5TduXJ^fSqJ=X+fH46%U?{vnTqxY1m4h+eGUz9Jr*;nf!LmxaXrws%5UW*(dHaC@G*p{`#MEs@0YOHPn?b@p?S_$6lwfV~E(9mq<$_qFrHa~_@!&37Fsxgt<t5Ocnyk<NMBkc~itiYf^rjgO*z7~+H`-hR?N%D3|@7^L`6Y_)d8xrzcu$b1Jg3P{e#bd>4K@EtS<>2pLfBgJ=R-q`CtY{dPQSOQ4L6VTxa+3t3Zh=T(fI4u|Bbj<bQY*6{I98Ge5N@1<Si1HYeZi5*3A-b*&&n7cd$Gfpx77)a(|@y}Q_ibcc^H|xLnIGQg*cIf4`qA!B^M_n6C!K7Fw)Ah{J4VV5T;_wQ@V||)vb*eD>2&V99!fzhk{YDPHJTJDA{lu2(re*(~^(V%CtXnTIPy$uT-#6A|(s_GCp*N@5(-ty>=XrzTYwgVsfLAQbSlC2ZhZGIBaR{Aivg-O4G|lnmxjUPURq1xyCZH=`{~(1Rc1BJA&HC-7$31^$rc0HyWvt%F{MqN)?DHb-Chv?k*^k>~;*_GDO9HAePv%bMP`uC|R3FJ$gp1EzNOEtNO@FFPYsw%j|A{H6mqPM|tkIQa;%C+T)n7z(ckazE+PqlT+%I?;~ix3=i3*8#^#Q4XKtBoT56i@Q0G(RRm|%Nzk~~whaPzTy(W90|DCXZmxzR;I|oOT@(>)B1IHIKoT2jw$5rC9;g-~%orGF5vC7={B@+Wf!=uiK;8Tki>F}Xv)6X9DwXdvWL}`w=Z~kun<VlrqV)_f%e&wHjh`>!^*?NXzXpny^kL(e((|E5kD~o)686J2;qU*b$Cfs<hXT@Sf;7-0Uvt@<q6||rKaJ~|5485<>4e9vjCIU_P}3q#R!~Aa9`bXky43;J+_Gl(%c~>|$5Wb(==j=n*rT$e-OWgaCu5!^Si_a9_>*#H=L@i$x`EGLyIzYp53}Aw{nPZxtOT`!d+JU*z3|A0b4!Cs7WPzx513B?f3VZ7ALPz9yZSO)E3>^T>tNf(JcNa3Z9sH-joVSF>ZW$?%d4n+@V;P9kCk10eQb4VAyq$pc6G=WN;W(o?SeYI9Yy_DiC|=9mR5YwSfv4N$=%qdtgTMBv=1dU>=_q&?p|7sl2#moa+IfnuR{#!kP>db(*kn2Btlv(3pZw+`c9uZDuT_tHS_dLHQmyv@3ZRL_gmUg(iLn%a>|GY8q~20eb5L%8F+4w(!I`elxheGU2&9TJJoeo(C?UKQ^&H>D?ee~E|9FE>1<$(g)>^GZA7_KgeIsasJVQUY1IZ_;w12&YxnM^+qjnd7&AcT*?|-Lbe=0UUJN@qW-)2aM(#ZwG&g`CZ!q>c2##@-`yy3*P^B>CJ=pZds~VPbWc5PB*{3#%<*~QD%~*-se4dtK1>>5_NUZCajqKiEv9IfC+uF+U7E0%Kpv#(@b#g79u623h1@rcc83o>V{CCl)i>0r+h3sQT$Jcf|yCM3Z;5Qp$kg5>om5bRJmI{Tp-TL7G<y5^=lgjk>oGGJ(n9q7EoJq-z$java2C*!UJihjp84RahUQ0XGArPhJuO#)rEG&~ts`!>)Jh`dNeO&O>J`F_mQ+3Evk@H76mRi$?q2}A)P!@^pF(R*WFFHiv)0#?y8_TkrqjNu;d>bllyBhYIT=6}5F5s9NGUfYt)DBVRnGxN<*!}}Ne<RYgmX{l9e}3}Dg2Zj;be7angW<2o(pzI@5Zng3jY0;r_y{SrEtX3xR#Vf;_QltmGD|8LOPr3VGgKBoltl)GpOmu3TZ3ez{ofZ>quu6536yXUGkAPq8c3tdDKaT&-CY?lBx9d+R+JfH<dnX4Sv%ZY0J6MQUa_dO-5-bNCetTy+xh0ob0<~RA*)5LebIfO<jH@yF6Kn3Dbw?bL!2#5>}b@%2^WaV6+0a0<qqhr6E&$bBUK7AbF!t%Wyj%)At&l6&TB<kdDqbHsZYe^>8D|t=?$D-jA?`(2B|)@_@^l^mwkqR#(fppdk&g3f=edL_M5ZbRX_1{I?z^Xv}tvdK&8h!_X=JPUB|{+!bO$Ntd<%qNiwqlnsbqw1@(34>O$4!@&s+1a3$aEtyN<<f0fqgaiii@(G}BQYkXlIzbg<`oY2g-wT_iY%owSAER}qXmLIk7H(is9PXot@bE6`uX3Z&2c1y;0_->JwGzYDI*g{-KmlTtIun7GW@|XB6RRcrb@&5dC?c-&4zSdcvF9N4Lq#CU~x#veK>swx4NwE7C;R{Cf2A9jh=XT{JzqYsx*>Ihfd8It$aFgm?Ex&+vmKD%$_L*hztLzom#|W_(`?fHye95>FZFxkbF+J}MS2F?4X*Dsra3d{)&Y}T4CIlz?cpz5%ZG8On`In{MA8~%8y|FnLT6<;hILgzEWhYnt;mx7$IzwLN&6|w%HDV~TnpZ*HZhu^C+2Jn3tKHZZ{fJzRjr2`2bs4mu9Y2|lzyK2P%$N%NCB(Fk(`=#@GTbfLXttvyggD^i(SOJdfe8EwnbL^Hor4q}k-bjpPDdjplw?W)$&3ryjMigt;LWjxdibqTq>d6?#>wzbnKoxDV>zdz^2}2`1zo4RFYVb!O+SQDyETEN)N9wIq(YG3)9|7#{Nc>IYOa?^k$6d3Wn8?L9+Sz&8$@Sn{CW+yLEcMg`N4jnL}}pXh^^+3a{budNx0&UJF2HOCqIHREmsR_eCw}$Mu?bdKM&Xo-Y&D<dNUOuk^1*`EdIg?gO_^}b>l&5Mj30<RCi9)S8_>|skK`zgnIiVZ2ns1a?NS<HQF!{-=L{dTB<@K>&Mz$)uzhLJ@PZ6R-6Ljhk{uhujo2zIxSh6-|?H}jL9ldot(&>opQb7re(?Dg0BvtuL19uW}{qoX*_So>s<_LZD-y$0!KzTtBknjjb#)X`7^5hIjbcxKJXb{4Q)!I)zt|cAj?)MOeJcm;U$weNNEsfAl1DHkl{gpi=po=uZkb3XEd)DE^Q&vE_%PRGIe09X{rSV$0B4zSi6z(W%q-mGgGY3wX@$eemp4d+U#BlLmR&Ib(}794)rbx=w~Q@0B2kwD`4X&IiNc=RrX097kVUxySvS>TUFC`gz}O-o{E*<@RZr78d=#I7Xz01lTL5pIiKlzt*WUaPQv+~j@$9-F0!dN4enE2=A}fHk?lN|Xf>&g&wX8~nF7&Qj+e6Vb=E%6o>tSOR+80~l)AljS+t6qNOL=ub?8T#k+McQ2Wvg4M)rwjn(eT<PS!`n{$vKX*K={6B75_&6u@7`Sz~s0Z>IVaQ;SHe6|A@jZ{lmXJ+`9ae+!@A?JNkpMKo17i`WEGr9Js161C82$=*fIKV_{EaqVFi&JtAwJ-vbqBa=n+j3#erWk{xcx3Y_kED%EmZ83>KU-xI;K}cK|-AFj&XWOu|$urdx26>%?TAfwnP6Q1ZetgXS&7`$z`Bo6EEar6F{7|;5vog~WwqAB$20M9g;=9bVta~uz8K`v&DZdpSwHW`VO5nB`WQVyYLfv!fTta77SXg;as#mKUr|3Mi4CyQMhn5-T@ZB-@7pZf~>*?@I_0&Zc)?TSmG`BK^7i7M1hv-H`j<j83=zI0oYc!4Kix(IX5y_Al(?Xg9wJDtAE6S}%%lgV~7tv~dfrUrN;Yi;2ZMPs5t7+smo98%jG26QgQkc>)6!I&9MxE(wM|PHO+Vj!tra-Jc4KPkAHJ}ZF7ipqJH~wMhucvM~C-yj9V$OybY=@hrX@}`35oSviPc<g%ad#lgqbYlbFY-|@a(L)1X+w#Ziz9Q<kx3qt;7_d-*E7Q0mQmlSSqdp5$SJmtC|s{kYC++t#fn;HQaT~>aDQcXuI38jsIhV_Z!9u%M5`KKMf&Fc0ARh<O_b;wsW>$^o<}xSdhM*YHk{cPW%5MCYm}u<q&jH{Uur!sfpt-2N$yOqYH?zVMLVUkOobyAq($CK_Ls<mzvC-Cd4gEkO41wxx0Wt8*J6$+kK-WOKBby|MF*8LrBvuFc}8uRbjc+fw$G&Zi$E;(DsU}nxQ*yR)d1xA^o4_=Y2+tV9y98L%6k&GM=MoP&5Knu-izVCLc`iz%1_@ccWJ0n$lwO&qQVfI-)3;qwZ=?$R!St#&jq%ku}t3^ew+Ijb_av<shjE#aj=P+G4ughbNUb<>+|M){>ttZQJo~r5nmp8>w{-vj3-*r)RLLizu+#(v={9DPT(R*T+evw_jSMu9hmLCcMTrFG-%v38voi#AmAUJl4BADV6-}+^Y(;Af<_d>lecKHa0~n4eNrgqA(awxV7cqIg9x@8iMRUNG@Jy*c4RV!zo9mLQM@pExUVK_&*3l#&K^{KW-~t^90|2r?)nI^%o;`E_Cr-yQiZ5UxTw8s8F8H@Ig^nN8$@##<kPHw)^aqZUghe?r@(Ws-=w2eofBZl@?RS<h+k!0Ojs5^H~%s@K(M*sg?`tDjIP!K9!=>m{c_WPp2un531CQve9_U4+#sLlyGQ=FpY``Y|Ly<$%irG~^gloS+rR(yFaO`Cf3Qla_4&Vj_5b|8fBu)h{rRtNe@VZ5`oI7EKmPUa|N8HL{r=h9TSn#O(|`QsFK>VMKbN2W_OIR*Zf{?KM|u0dzkL4P55Ii={^dLGe^CGR?MM8tzx+$~6Mpsi%lH3%{ilEW{=eXDzWv{S`uzFl*X&n)=kWb^{^s@d56s_w2_=1djJG#=fe^!rz%>!P{K<d+ulqjX{rCU2(L~0>`KzIEjNh*H2sZG)kHJRuv(b}?jlHn3r(!dYL1Vw;Fi$i!G+KZrd|WiPfyRFnGzOq?m&x_v(O7^+3DCHYipDn4*pGq6AZYXx&4$JfN8`?h#txfM_Oa2J?`Uj+MnBO&G+Kbhd|WhU02=f7X!Mmv&56*M!J|e${tmUEu>g(z=xFQ(jayfoCz=(F18AH8jsCc3Mg-1JfJPN)%o7bnV~3+r_l@TK87CaUZ3!GZKRimntpsdG%I(P{PqjV%IB^4**d)>RWU}qIORmIzcqaML-aeUto8S_$G*2eqk7e&<%!SO8$s3dRkc$4!M1OcDreN|MCnb~T8k;kD?mHNh=b6nunV{j=Clf4ev@v<!ckYOZzBZF6y9ADh;_h&uXekuE{`U+}>_{kT7?cj#fgJ}WqEL)Bx1*x(FRfk~Dz~I!?vF}*Qt28igOeDKGcwe4yEMk*j0_=_U5Sj-Qn6V^_|d7DAyi;8!%G8g4@1R;9T}d-hvN1^u^_p#)WJNVJfXA`UvC8-Pbg0)wNUkz4zy1w1E8o60YyKdm{sJsMDU+bE@_Q-C~BDO;-R6~0?LW==|Py-fKcocN)AOop<qzl6Uq}xHCFu*plJW0p_tP^apRx_6p9sROV2e_e3Q!g3s&Yz##r4h*P|b0WJsx`|9w&^o#Do)3+{0jmQpdRIa7z=@3d4j@b?l+h)+qyX66^>Nd={1o>V|lkL?RCotVmIRi&R)lHvq&p`xEuE>v_s74;FQs3(<d1}&P%CzWjvG8aNmDlqM1E?+;Xq~0*+rZSl>DDEUsrYDr)P+*AGJ)ztk6n*VDoR0J3QL)#KWV<kZ=n3SXRJz8>N6q|%d-f{R2ThkQDE88%<E#d5T~G|OsmuLCu_K_QB`r@VAT_wv`FwaNn`!lVOxy-RF-e`z6UrKA(@!WV6rH39KRgukVW8+9C~6>-@Pu-2t)K=%(N8G#-A8?Nn<4vzQj6a&P}~#BHKCZZKv7R9Y3mgO0<%vjpa%H~WreaCAudp!$NUQv1)!KG6rGgzoTGa}6Uv=tc?MQ~nM#qM+6v-AN1o@U_`V2~y}z-dajAg}Q||5t+p~0}J={q#S+oJz%No@^0j4+rQ{K!5#{WCA0B6Mn``eT)P|Xt)-tq>vdg-VQIV+~z%qSIg>nA3>G0svEpx6ICF%_5;z|>VZaYjsrfk{0vndYPuW6~cElX+r-A&_lfGhiH@r%-1nCYzj(Gzia|Q&sNl#<X2c;PKL|W&7tS5!{W*Av&(@Yj=|R(m|N=tFKKknX_WjB1|sxQh_0qbJY85w+j<y#Iya^uJ$5_VA5B|<o!@iBdkXJJq{;l!az{&44^8;U}HH61HJxX2Gp#coYFj$YH=Ezi+dafK^>Wj^Y<rNtsITIIBiu}X~JpDcsiJqAHm6Gg;`79$zR%G*vIGO#&EJptyY?HvQJKx@~w@N?m29qoRbEe^pg{M$F*6Kcj2UZg!d=sq!Jmid2*`6OiE7n(!=z$oV3+_q-+-dUPzsGh1vrOrky%LX)PtCj|wn3WjYR<3n_Isq(+V@Ty<(p)E(!84}!`h3%Zz;DM)Sd9eFfPOv>Y=%+*P0HMtH{ixf-&b8X#a$36<x$d#(n0c4&{*ZJInnP*Ri3J)OENf}~MhoszXNvTI9^-jlwJD)!Tsd*<T4}y2_LL4q_u;0HvEvRoRx)qTMfYd_AeE<4wb&rRUQg=rxjwKaO49Y%1$w3*gN_Bw>4+%;&_r2>vaM$1b@tUV#MSK6?yxk<_WRBuwb;lX$ol^jLyKov#^FB;vVPX7^$y_jXr8m!r$pQ)Cb^tJ7=@!QZJ_4o*q*`KM68H`=O=B<_fXVK~6h90my$4e`DW<L4--hXZZPGmv-ZNq{AR+#a$?V1CKM*F{kI9`DlPWNo@0ir7F=^As>1_zjprCHyWCu8YbZ}Dl#>s*#O3BF&;p88hQvhuR4dC=%lsR2ExhE%3{`{UsnL+XDNKWohPGJZqjc`(fIoT6)ng?<+hjQ{);IyqzBRT04a5Af$@QuypadCD|)lxcqyR#Kcoy(IMglS;EEsa;RSYz3sU~B3Pl)iw{M}itSp5jnW?{jU-WOj1W_s41QfEol!J>q~GoRd>`xcX?kGvu~P$00enQEknpV}+KwqKWIEWkF^Rt6P11T4o<CU)X;}0Lx~U4Idm<NSecKSvpvWxW&mI9hMpi%T{3NVJ*T=2g?Et<`WhIYx8i5z<WophWevgik%Er0I<{(7K9ZMSSEvI`$`ng2WtYb^b-~j)|SItGFRp*u;N)@nF}n9!ZKHHdiU_K>|j{_Y_L=Y%ROPi-7o+HQGW>t8=xeA!UE^40BY~v(Lj7*jrM(TSU!Q}0IW^l83rCoPYlZ?u<XM(_PjEz?N8kkmcNW0L&7q{f`50}GFC-)T-j!9{3@H;XxWp{st7t}$EIa6Hh#?}Z{Il!t$8Ocd!gk>TJF?iE2!J%1fBd)Fbzya;LA}6;mAV0aDT0eE1+DQy0WME*PHX^qvNWWKRCZ_a}#5m^T3)t6u3;1P<=v6b~}rl6I|9d(4PUC-3iSW&|n_N7fIFdg!ZSzi6yV++pI{od|`Y-+n^Z~T0o$=C$tor0o7SHvvRQ)(f<=#0!_1^*(WrUK!b%_u7GBGp!rimQ@|sygl02n^BJI-fzV*75`?Be`u_>-8#K*=W|E4O4-ZWh({rvs(@$s^Gy|a7#KFp}6;RLVxlT_HtWoEry50isaCNCOcy0tBIqMK;4m2KrLQBqROZrT$bt({=`xwxywgaL0vq1}2f(A{W!pDH7r^uh5hM*QN|NR)$Vw8m;127VS)Iwsu(nW35mEB&Qno)*N4Mw?hYW{wxT|Z5rXHai_3y0AT3iH5(+`1#WbjJBjcQOyGXN2E>cy<b97u~ioY9(X`eMcS0W_plsTB<-=xd4|HUeALNUZrJ%ODzvJt;O445haA7Cn@ad4Xy8DN3rd-aH{*lX|vG=y-O|Vum`>0B1kiH=l3Jv)F{pnRUb}M!D)fcAL2C0*gX+WGYsdHwF$>?PT)J+N#}_(*-qS=jCsl0X<Bd%(d$8QsTEj6r!t(=!{9V#id>$y;5jEeT~<8cfajA3<{?qcGd>JYtDNWabl|wN`S;l>PqW7UT*6ado2PkXo+deN+C){K^4uJf&O1KUB;~p7*3c!`B}aDXOI`9*C*Y}2p3d*#839i?>mknwc&bjG;bC~%dA2p4mI&*>@(|ei*<~%)(~zUOtN>@`2`X%wJWa;a7vs|=#xeO(w3p{y=Tdg?EH96crw6SM4RH6*%g3iDPr!3ZG~Wi?Ha)l`8Khb18&7}H9?5vRQ}cA-Hg3R7-*{@Ea<D)eqAo!_DNp+_JiU#shi6D;^v2Twt(&g$)TiYcqBUHeCgG{GJ>7yhC~Q%@%y<9&JLlo)uE5iQ${CmNbb#mk7!Esl>WAU!C!=IMV{u|P4W72(DUFAy`{QXRl;@<imhlW(aq?Edh4XX?&(IbAR1Y&gWjwb+-R1o089ZIaQyiV29uub`X*y}jXA}i(uA!w!FhmWaz;hGBHS*yP0MA++-V{Ix-HPdjEc0!_^mIu`(}U^kiTe6UM0J)^HCJc~kTQ)v^fBEQFBl%O7s>$$w4o}&CBzS5dJTt%Zl*S2`o49<^)MI#)A#?HM2hSI-#|DFSDD89V~QVdf&r!dJDD25G_GNyMHBBc?ncVg-yc&~*^OdwBcYlEss&KP`t|#tn#xJ13e`QzK$SBM3DYSntTh+P8`C*qYSzD_rA+NPnffeuUS~RiNP5Y1y2Rr|O!dPos2=E3yP0kkrWjMR-fX4|cOFyA*?Nz?gx7ZdFztalukESgC9PY78czsy8phP3Os7jKGOpBA()2Q}A_aY6svAu82Vm*|QxBNxgz5WoFn2Qz56?72?faS922%@~`sGYjg{gZWrnM`7get_*P#tJ(2cgacR3m~K@553rWg2E9Wok&KGgwgF+O!N~isvu2h-o;KX&lB>gY5dWGL3+#PBwlA7F5+_sve$ch_m0rG_D(eNSMOgsasF3kf}ZaQ>$tN)yd+0Db%nY`#pfFE>H~t)tq*q%9z@Msb878glSl>tu>~02vh&yOjCIrOuucikCdq<nd*o4(yc70QxshJbBWxNBBq!|z;rqpQ!~{Dsvy{}SKUmiSlYf{LJbL2{Q(AQ4^va9mNs2j$<za;F=1*x0@J+-_$xtpyFd>+|KPH?=zX=SdRzv6R2SKU8Je2Z$SOWVTVdt1JiG@L>;6W~Wh)HBKphA^8z&E(NIDR1Dc@L8Zf%tqhagmUkI)tfUDjK5Ynk@&2rJ@`5cFPz_JYu6UI{5e{qP9gdY{(GC=AZ-MQ9R)oAJ2<JwMKXa2tg?5SpU*z$V)WBtrW{SVL$4!mW*;LAn8}vm%T$6d3g()Ct0^GHN`+WAh4D*G8cmg;1ji?P(BhGU?q2ZGkX=m^Vb|*NFHSgyGQ<+5%xf5ZVHv9){50B|<e%e1sZ^e;t^-+eB80-SCFcoB-i=N6trK+>g)|JF;GP>g8*F+EFM*7!iaPs8cOi|DFhmqVE(TRHBy%%}u%&ABHe0KgqTeXeAbang0a(SV4qar25ej`r0V;hL6w!*KpXhL}%Y$c427lV9z^|`3PNs&{q)}P>y5ot^cv!-9;y5I4LCy{l}ump$2JAm}hcH@56)ACuShS&69Rc(<ds*7={YNP<Vyi1w(oq2HA3`QHEOi==yR{IYeI=gxv+iFmfPnlQ||7wVKp5D7wcOik*duIYeX3-DibIj;5(Pn&N!!yznjNq?%_iCv|6qHmr*Y*#RZb7(YBqU1zCHA4^yd?6b;jcwUC7<8TU=uF7)KT$c4h*8uLpaV2LHh30bPInyCJW2wfmG=ODDI(aV9uXqNQHq^&u*u!!H+2gGc*d)qf3&LRb%;Qqb5-Yrpph$RHGXWZyaBqd}PnLKctF5q97nT~ZT+EJ7%+k*DUY7d8Qi0;NkaP(>70c=={oDCc?_s$WRi!K==tyON{j)yx9GA1SD9b4+M~g`#)+bADJ+&%WzR!BKc1l|sEzf6WIlDNIK^cpxzmuYLbA4FGJuIhnil-Hn0aO4xkXbmxu+#%t8o)BHqtGWTJ+P;6ppfbeEY(1kWo2*73MMs>h)tlbDx8_+9455~WdL_?h;r-T8PA5&)iVmp$|7!%rAb`+Aj_>SQ%G2v6Hjp&OAD4u3nFViW4ZJ)R%;|=Q}8`mZu*G`+OX)PG)M!Mn|YT{S~l4eM1pI}<*Wslo=y1VihfK6RF*CU<*I0~dV*nT=X%P_b6LV*q)jyOF00Ztmvgzw5*lZp;u4lRJK?CL?%8I`<sGrqH(_b?{pYkhwK}Fz(UOtSART**+xWHk>4E%e3!I&Gkey+Cq8`b8#nTSlF7p__t88}fUQs0}xuujOb2o956rj3$(O9S(kc?_KNrR9yKt<~kZ=y#hS<5BZq{u~1G6Is@IU9C|Hc7*;@c5-J#Gn)`l%_yAfpmY4(iF|O%?VIW!$~@jEZpqu6$tqlPzB>x&*mpdtQgfI4xxSxJs41u<yWKTvywDgyHO-ziSO38SYN^w>XL7GbdoMq2POYR>8mJnbM?h5T%QnSyeY{EkW`m_dmKr35|Tb?Q=EH#D}<yTOw!yXN#m63CutCp(3?`NB+VU@3}a%8c2a^tX-Sm2iBg>aW%V318Ml|DE=Z=+TY=QV<CEN`x6KyH$;wEEq<`)VM7bNu2+l#{Nvb;;lPO6P{Ujx6Gm;kc^HGV9r!7d%4^MJyk5CRu@i_>hoYv&lQtclz{|S9Elv9-?zji4gB;)Fr96*z)keHsRByo5elJgFbx%G)HK-vUk05(wOB9%NTNHd#B1`@h-ES)&b3eR3#jST24wM8rS2{s%vSB9i_Q8u?>s@f%;V>jQ>h2*r7T+BTlpX63bmy-0Fe=rZgh+^U6GgAteSmw>(Z@OUtN_8iGgE>iiTSIQl@Xqw)SyvEtgr$Ub!A=j5r9K>AsEng&a(im7eP%0dt6azBR(n`pqZRfjk}fmlUM_xl^}0{Y8jm75FyZe;lZ2EaP#@>D>q}Pk;Q4)pgnza;S~ZO%xzq-4mFqBL9S$QoGW%k1ltBfx7o|;5=7sApV?9P=hoOA)!@so(B_}!WD78*W+JdA8B+an0b(CZ{2gwO2Ct`L>4hczfT9Pi#u8$;4#N;FuAQ=-o%rlUz?B2mfwHKwiRI_f)RTZd=fheczq4YaYx=t~2hSDkV{I(>@DRc6M`GYH>bUO}0N1*g5%J&IACn#OkdUa$mYd98VB^u_vaeGK^eknDQ)7ePc%Akxc#2%D3sSTb$Rr)4ONqa1ht5zS5QjHjt{Umi({eL@>?%_$Mot#RNmL#c$k+gS7GQ_B)Bwa?*UPv0SP#RG4KboZJAURSaUWu*E+UUI~%>|_fXG#N(=L$H_Tn(kYz052p8GH{(18UXvg`@&bQU+A~>%qG>O486I?KqNa<lGM>=?aotM+Bc-zQ<X598A)oB#qJ%uTl@18rMiVa7a>XhS01^mHj03u_X0WK^Y~+2_8fvag-WV1w)i}AWGGNa=J$0g58O70;T;JN((}78lbdiL1{TCZ;`C-;qZ3M>CivuR_|k-qVPdIj#K#Y99@N@HqQ6gU($JNi{!138kMn20-!~vc{^bSP#heRvf#WivK!c#y9cJf1x#a|-2)SE&h3j9$y;RdN-*^`?kZa3n`d+g^In)1z|@sazi#a+^Y}1Ltc^?~F~>A0OmnHva#_RL5@x)b8sIKQW<Sg=<+YRz+Df}dXrpJJFjJVe2{RV0ls^PaJxewqQwYl(D8t-Zc$Y92ugp`xtQ5eRpwuk0e8XTy5Dwp9Dg@@$Qm{9aEUO_bHJhcrBFoUhQs0E73sROQyW8k0OMMlVSi)<*eU>I8>D+AlNiKU2Ov08VH6VGd)ZuhH*>0!}N-dEFlqhY1(gP><E$`*7j4~cRC?zCKg`}yH+<FN64?r?#8ObFq3vY_^dg)oFH%{_;%7AeELK*n2XiQRpStDsdZ-8yH@oQU}M<-eH3V$1vp&#W^rwLJ-%oNFi4B{D3ZiCVfBsn1@HK<_MS=wuQk_3j#0aRs9z|SXMNUE%by}!hT#z~;>lcbxhmE9QwXaf#OhJ>UAiP~+W3MU|Gr~06rW#;t(6b46t(gT6%5=`Gzlwn}iO$SOp@W!YsC}Y&(yo4=6=`-5>8b&_0{~m%ebfGk~l@CGk7U}Gs$w>|=FU%<T8VMgCD4TsaMpeTo*f8iKZ0H$PYkYm!n4AZ)1c9+sYch4$X}T<z9g{NbfHuB9jHMgMa;~D(Q-6QqC6is&VFzHq1)Z)>j52!f#-N-)8rEKHcnqjJbVqK!?mDYwF~iM%mRnU^%2I<|*LBZ?{)l0zccZifN`0x)j6k;xQJOQOG)h*1<Uv_n0JYdlLI$E-k}ykn=M*Tx9-gucUh8YHoGL7@6|;4>V+nFH2}`TKoi6vYoHJYDrM<lZexyqX@;WT-HCT#<rBzYI@hJ5}p_I8!X)^$&OPb7>ESE4R&K1)dn1Bh`Gov)K^Pvx=1}E^X^mRcw1C(Y(8Bc)HR`zhK-K6?aPRRs!V1jR*2?KCyzE6~D%v!1a9QL4eYZ>v9mzmaLVhe0v)mjL92ugE>Y(l&e$XI}MNm1v?K`Iw_6t+*`t`orIR+osl&f?<n1R$-)Nt!T)o)DY8<WRR@1{9l?Bu7@h9!qlb!%ay#H+A)hv=?vO%}v+?na@HpPj%fVNq2LSHYpUb>va&;gDGGGvXC@j3?D?&U!SCn+DH}8TL68&kc5g|o6T-m_d1_|<Yw=al8nk~nW7>ksY#MhfnhII#)ps`SU{}92$EVz(gKq1BqS?`pvi%I_fe_q>l6@AbP^%sV1j$>#Ptm!)@J1tJV;v`0mP8O3Y8k{kib0@=-kEAlLq1$PCHHgI0MM`rx|LWWv<=u7R~daIBQE?aBQ4unlNTYxe%vKaKet)=JIzA!8vu|bfh0jv0~~zoKuDq77s%!aoB!lWUuC9aq3uIJbfR}x!`F5PnTt}Vee~w0-n=taH<5S0yxd!w#|2mb9P#c(`K?|cj@~GaoVJ$@DXs@5jbOX;*%1@X$zbVG`BAk+UgRYd~}>H)P^S%TkPX$fcr4ysZYo=-U_E*acTso9)@!|3r<7g3<XY=NP$M-4EKn0QZT{I$7wEEugx(V;#A3GhdAvpoc>Up7T=7Via~JC^cl|yB*kXXRa1ezeFg^Zel>Z&Kc2eJQFkm(2XNX9r$cbMC(hgqwuW=NXQnuHhI35wQhO_$fpjU(_M&Kv6sIO}I)GCHM{Ou2xE4;mqxMUNb8DHM4o|I}>*F~A@jjgGTm80MJ+n9A+F5w6!_%fX4gcCs<D5V#i30u9QXQZfhSS^!PL<;HTJf*#9#pzdnH4mQZ7OhVkD%qiJ>yg(a4I)PDbB4GF*GTM&EEAY#>jDwJ1HHDb8DoX@-&(s27#_28k8NwMg$gE=Er2VD{%6hABm?G3{UH{5T^$gOTKU`cS$fFR_`cq@;nIVe07|`0`>1La^oEo3~9RXHU<Rs?VD~zhm?e|@o}=_M`Hxl@hL_>Ti2J+#c^2@@Aj{*6Q$HUjLL;Xb&Y6n){jY%mp!)A`o>gua0pRSp{8Y47Ms{_2T@z;R1UM`u-CRpVw<V?@#7P<wOJpd8A%lO++K)k;I%!jNcmu*ThEM)Xq<X;yEP?8B#Dk|8$Ft6kf|x{K%lk&YKjir9yk!_!Vcb?7wDvw>p6+r3s9Q@U25<kPz5aE?-!^aG(zL-Zw+)h0Z>yr(oc2{eL$xSDD29uL83PWI?h%W1FCLUC1I}!)FwcuHTk1~Gb(Ic@C1tH(Wb1O?*!VV!fYA_RGk=TqH&i3jSZkC>mF~<1Ju<==-dO;0*4%!IA2O}OQ3o%(CJv9dN5E2vOh3&o&vR5Gg>ncXgn6Ex*5<JO!=~}!RdhpKa0g3HnT2Bclmj}(yL1_BnLX50I074ot^3|a>;>41gOs}Hbw#sgMq3cBh+g>3B-o5gnR~BbEtfq*D&67f%<y^s#BmwQa5BlCT#`*5uGF;mx!oJlEeyVL9SJCs%}@itI&?~ZuXNPOPTjhUJ}50dun&NdHT$)-&};AkI&P2l&3ddv*XKUFKTG^;z92s2g<QR(zVE3wMzen6W&yK27c_WY?Gea%DeUY<UqzQB>lAPkv#1c`lhG*k=5V`dQ^pZt3g}niU}M1_qz&+M7I8jCFVD!sBntT>M$~g?y7yh;otPf9KidUFycTr4b~{2wG?{Z>l?PPwgZRg(Lkr`0LAOfVZZM*vp%kD|7f6bG|)%_HJ~xD1&-f~(DezlnLmf-^Giv23DjIh?h_~p)MO6y3sAcXFH@lQ3A7X>Oe9d10X4wn{|S@;nx}g;0ICq6OJeP`K!f#DPrA1R3ak7a06IN7P<<1iW&Rv`{4YQq06IN^)_|G<s4jr&s{{4-3Dg^F`+-Iz-5b|MU;(-nU!4f3H#pGAM&Ac?uH?_-dNM76npK=|NOVMvi?r1SsD!6Oc$SstagBkbJm)pW`Q%xap2OUvNou7bPY+7ZAy0j!5}2#-40HiZ$}`R;_7wNlc$&mB{F*%Vt$2Dm^J5a8v$Lv)r>*d`7oMAa++3`m>alp@g$1s{)4Q<O8zJQxKyw-o*3a!se=eRX8=qkZ&zKbRL!M?0Gso4&a69TBBsjbUPdy3O&j`#BLeh<5;~9b1{h~MY;H3XhJRALe5}rYOucbUyvG3?C#St%i7S2;2#nTP+w>M*X+Jt9be-3#rifzAMob*u=_}EwJ)<`8~K%={@J9`HQx+Au(maDv#Tq8#vT_KT(GVVQjemF)OYZzg5uVsq^IgQ2BuyFuY)9$KO)BC_$8CVmp1J<Ek#<8;LkO>uz1M40EtVO|MwZ2>OHw<i=eLPrqO|W?faszywOR({x2RS#`X>y~$Zn;aHfK{N#dh0w8u2!(R53Csj*4Rn&!5VNZ&-0lRs8YvDRws}qzGtv%5ZGYmF<@r^7Mec01gu$aop%a$9>i6{gpr)9$=a4%z*RN4>JxCa)$uxxs{zF=A#*Y{pndc-um|^a^mw)7xY~ki1YQ3^R?qq|x!R<Sv}IJhU|hqx4!Fw-uyI`!Oc8L^M{=FJu<A*M6+}mxSfT5t1BI?(4cB8>w;>I&#-j=dL*Hn1bk;M)I$1sM!Mcsm8N>)MtO3NM$6@ui!m0#=HL4jlbCXlu2IvGt%(_?umNj>C>m1YNcXV;49YR$r{$0x!KE`F(Ww~p?h7cMo4V!87VN~t)$Epsql~J7#suARz0<c`#+H9m$?Jy6kK~!yfVHHuG_}AAo>*=%Rc^;@q7T+beQni4pA9#Irx1x%lt?<M^^m?B5P~FTKAXN>h>I>BXsE!L`ji#!GPz^rpqH0j8FyOM-2ZXGe+aE<$jq{VPj#a03tN@`xbvd2}Ks5r-fpJL!duSHl<4Mvu85Q_c4QP9tE6h@=@b0R>7&e2cnq#$(dOua0#8_~u=AwNJ>z=hxoz@${NUHi!s(NNny+uO51H)UmzToh7GjG&!>qcHL^{I)I3ifd_`p0uL6^=2=n+wXCuBR#eaTe&hW98F&B-EM_-A<@<>-937zbPsXf~tl>Rl}iDb=(d(4Zw`E8+b@R9_oBErklP*BTVfuEA(?Pr90cFOt<!K0fg(_nzkFjRG*vac6ir->EfHH08{;BO7vu(P}hEaQSjtUHDEeDnUYLx(Fp-EwLlU+0n_OxQ@pZ!M!g3X37;XE>L=3%Q%f?PlI!`CX{#K$ESO({n-tUeFrm%^AdLl5O(Hb|k;Zc(#fs)3QU{RE$2(Bp<0Xpj*ls{h&a7&^2$0%iJ*aPlbkb^X*LKrDs#h~*cdQHbG?Hkn5S_h`ql%Lu(XH4U67>U#4zf)SO`wyc1Jb0mokn$T&w-i?P*VUs$lYP;vSy8Bx7=YoW6`=j=V=q;`FRaX%|otE=i>Pus!Myf!*)FeM4VwW?ZrCltUPU)eIL&NnztJ;4mTCEL%M0(ivscxo_#*)8t-hnCf;2FG{i~u+2aJzb;2Z_?iaa@OI(CE(bIfXR@9BN$JzQxB|K;4<UDQ0YH2`0^Nh#yjN|MwwuDp4QyZ=BKG{ynIiqZ%ZdKnI2o>VFQ|&`38l0jt3h3hXAd0EaydB)P{a6)@8BQ|KuEVYxHjylt!OjEvPE=a`B<bGb7Npdnv%J5YZ|pdQ!m%VPn}xAv8bi`FNSbl7ghNRNRU4Dq_K}PPNrRBo!^8;cF2`gKNxUt)xg^bfmXb_Kn)8y>lYk`U)@?w*%m77j7*5jO=Q<gzxi(2PI5mE-ZrxVKq=#;PdPfI#NK%79`PoQrV^R$#X)kVa7C2W#P@k#>OA8*KB;9izk~9TLdwP=A7}rNK&wOj(Z@kp{s5M<PQbuqrNf&Ela@PGMCxm1`Nt$CbG$X4|rt6S&6_Q(xR7gmg$0s>>OqNdj3dmU<An6m5_Ov9egN=!FS3`A!klbpZ-Efk}-n$*{zB~H}B^SD@le)f;^aV-iGNUf*>cdy*RmNo0K`<uq7V7FkGORc5l%!er?)W5G>75QqYOvRoB;95AIf$gaKFMHa!5t^>@;!sD=}UdHM@jn2?(_IjH5)2p(oF0~uR%y|JI+#Uf|Cqu5Aa7PS*d28C(Dmdrk&C!K+=F7=_N_Ko+?j4(pN}&d)p@IYOtkSUE~-9ZqMIF)cim_(vOB%IS5X{N4||C1uGPZYFm8YuPxGFjvJe*3+qhRglAL*ZiAeX@HA;{fh|cWqyR%iWcpaFYCl%X=#~!s-7T<ihP{~Vz<T?Gu~v5G=#}ZCig)<7g}FQI@V#_o8dq?CJE}&|g=C%;-@vJb6;|DC2cZ(HSsSVkz^V?#I^Tw>VNo4tH>l^kq#B)=YP*HH22`Po{uQWBgQ?mPR3{&T^b|n#QOBqnKvgFV>jzK`hf=LLy1xz9L0Dm(sH$RB=fXOTrD|DJb=Cnqto?vTx#Mbo7OIAzssL4e3##rOsZNvHK{Wym2S!z`ReBmwRU@hDL#dkDV4ba?wF_M>?tpb8jnzINRwY>ic2ac}svc0)pfpbbyMrfHs@=LR+O4;!nqgGuL!nmkMzgU_3RO3u>YG80heEA|Sm)VwQN=p1TTtul6CF}cRS%=;?{cViLajR-Odu4PLk$U3^@RGTHR!)ViV0M`LbU+u($jug)t&0{{qsV#l15ou3R7K19)t=Vp*#?UY*rIzgIbZyYNhmSr2WUBBSelBW|bGLTNGgN<Qa!`w0_nM7^_;Dpe8<5UHC$5F_by6*xaZF&?al4I&N9*Ijov-ShcEhoo-xSt_S&LZw*A9ur%7^-WuOvc>72t=EsxNRgzJ&OL{%q&mCs(9r*jl@w6jx)=Zvya5{#QJ8aBuvxe=b#%Yy}eK;u(cbEsYAXjG(TQ}86oSS}5yKCW`K!vXbNhOHWoCN1o#i?EAWS`JXGAx+Zz^`a)y?!p7b`MTl!3ksX5T^w=rw@VC`bma!*;>lPktvERVL9;9zy4e}b+)q`tH$CC1x}rGS3d#Ht#~NMX<h8ZITtuJ@D;u$&iQ@@ry5Vwf=f3>Qzfm`pEMVm2Hbi|XZD<?0yOnNn$z9VG(N_Dny@r|x*5%QFwM<cFQ@5EH2pNEf~HPrZe@aMAkEQgrAa0QpRUDnOIAj}QUR9c!g3zQ(x0AX0JHpk6qYR2sad+9o%AB)(RA;U%8eOI4H^WDVd)NKxtVAd<1#8Oy`%f}*q*Y~Aa%a6gpFk%j3w?DycWyNDau*vsSjlY0^|+l(&2altroUJrn*ay881ubtSGa)`D`RJ9HI=M*Ovyy9Wk>tTTsqtLFp?fr#N>_aCbpzK$mR|Lcwvp5<!&uF8z9Zr^+ZFm2RH;P<oJ-g(yR2N(v{qIRVOweS+57MZE{5F5E{0_^(~J@NLQ;f^wiueWf$}H<S@Hrnp7o+YGjsuh&_l9b~+!f$*@S#JwlI52olsMMp7D0W5NUPy_Q?!n-6*GkyyPNCLcZaOze_+4>sg*_(dKSowM&^58zHv))|0{Be}kNXqU?l&Na=GCl5-x@)(FI%|djk4D+nC?^HO`zf0SWev)(-FmR9`3Jl`+XGSdRmyWvT*{V3IaVl7fb!-o5J;!|`6NTR8*)VZqSqiVJ(N@dnKIFj9~Uz2qd$Qf7;~wCfsp46@^pc$h)UzLKz4H{WV|wdY3W;PZ)TAFv}?I64LLj%WM`|lSZnx@eK%xXfgDLM`GX;=F(bJfa%m?&1IW5?dVrAirClI|j7MYqNg#U@q>xPkSvMi81hN5;scJg=Sdgoc8VyZD{jT=wE`zKR>t!0UIs@dX0@*0&g6VfPWOpFZ4<T=fR$D-xNXYtLAv@7XHj00QYgOFa0<v#Ho<|lmg@YlhVUR-sxh%j{0I~*<;c_vJhwP4pY--Deo?$_X-%&a~C6IHkgXMIglY;!gknO!L7cr_n$hpWMRv~Xy&kJO`;++T9>T7c>WNj*t?POyg<h<c~03I?aWM~czA#c_E@xdSmzT4a$#38HR4<HPr5)TgxYI<vkhiKo`eIizq??LQ}w(uUHR7i-3LLBZ=4=+p@S8`9<J7as!6=`F01HO(~9|KtT<}NFCiP+wutXqb-cBqJM)>6W?*6}d!v{m|RpwU_M4mn}}ScK7Qo~{xG%fwBp{W~~JU2V_}9)qmi5~6kHflB=k##re>qIH<vEc1}TaQQ6R?m(hGBz697bVKwGuzn!e>TVO2#PO&E3v-w@Q##lpH=q85qrmD%01H!Urm*VIeY)M6WFO`Oa5PwZQ?R-M)~|W>_wjsYuts8iM1$2R*r^bTEL!j(U`K~zrC`+%um)^KWp-V$!J1*p+Tnq#VPKO6Nc+K>0_<D?t4{$|SC3l?xOH`aHER|<CSajE+IIc-AV90{Ge9N14pi4zr}Q<zS^(Ao1=HEU>gsVTOjZikR>0~4tS-QAUY_bcO{RrlYXQGFML}Z}E?0Hos(?!DN?g^kTx;VsSflt{H8_LjTmvYfgBkGY5{cTfhx3}=dVH=`fx)bm-UGH2+2&v)0Bi3btd)UPSK_*v3Au!;2VBFdShUGPU?0hE{@Pe$1*=W4h81f7SPigCRzt!BqvOx>D6G!Puuc`MrogH%SR=ryforwDLkE{S)`+gIHLNaLnLF|Xs>~o(4U*dss|Qu}Dc0~%SiNYp2F<qe_6Sy+*bXcKf(7e)vS|YK4jLHOKNeOe!a4=^87m-I4X_|kYn*#oTlIPZvk2CBhghdESf^koK30=q4G2~bux>qSEcni%d5MqY=Y(T5p*~zKpDXNvoOkyqxmv*0f$uEl^$*3>D&Z<%`HQQ~8g>U@!-!$E0ILVOfU{#YI?nS=Q~Y6Y|9D+J!P`dYN#`hn508`MKb)hkbDY4&Vg`8|cu;R&dLA6c)Qx1SaL+4a)a3e!*8KeanhnK#{tuh&>MBIzD58|5e@KYh%q7AN34q)!QDZx2{Y1F>r!BTEXmP&OC!dID=qH+%$<GyI{{V<?3W+73x7bxbiPA(3L3BchsxuQ!Qul^k0B<WqRpE!X6#Tfv1pGuqeRg`Xu=+tx6z{aX5Y;GAe+r_TA}T{_oKk$GFcw!s8i9hOL~2fhR1GJJy9F#nb=F~9U6#`)(ON;ZL978byOui9#pC+K3#o@*;C!M>Q&$dA4QBm$h;E+X8B(jg>qClH{p(BRsm?k;t4nO|j*+S{gH%G)Aw(VO2r^yLM>x^=B#PACX|kRl5}iP+A9cyZpP8ufK1hjbFc$IR{g@Di4Fb+XRM$?VQ-Hm+jiBp$tyF(Ikvf1>CrIz|YG19(kCHJuyD(^s2GAF6smRq?A819|u01ADH3sN1x$`1?l@#D^KrH|oP7Tz;YGwYuq(GzumfWkP_`$4G-hzE8+-1aB$$(bO?XB|iHPo&^%L03q)I!;HqjvzPze}K22DDP`ZLM`tdKR_o$*HWTR{*ZNI0<Wzc~`^Aat{Vtnex^_$-<rH)~7CwL1kdormCC$<|8m)DY5?e_$qQu>tl3md^XGe!kz$BuYmi*=Y{xc>zbc}7vi%(U*$6+bOTI5?5Z|C1fRJHzS$TyK2zWeC_dPZ#~g)EkHlBo1iV+F3tuGhMS$-f&m=;8wc21CteKejd{Va-L4~!;R0XiF)+zAmDm_s4C#7c+diK2Z)M$FSzxWL389+~;nVyfPZ{eG=y50H0Dgax=amD*b&s<*{d;$2!&5VLwD5o-@XF7&Y-z`2jX7EL=J)52`YQ^rDo*j7OsM9mEh+Zh@DbPS+sbGTi^c|j<2hj_&^WF4dNBM}*Q+G=*4mvQ$;Js+!Tb#+}3}3i6e4X7=WK(xmnoZAw95STmK%N;cd}>(3)H^-1OezFXr~uM~rSKlOWI&(cN23=+V=wAi6y}Rb-Fr@Ni4knZc;>-Qd=fibJ5SDu=mp>l486n_dOq`Ov`5j?eFr|t*mG}IEbMj9WuCtdm@+OcG<;?wYLB|B_0gL|@a!~qz)J(n&^-_qW?i@RCG0q{jDcr@R^7=Bmsr}m3cPE@NA=+&&zos}P<U@;;oW<NsTP~J=zaaK{~r+VWrP")).decode("utf-8"))
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

