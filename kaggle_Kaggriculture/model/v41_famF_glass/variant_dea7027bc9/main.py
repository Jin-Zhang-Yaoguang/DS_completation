"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>-H#ksZpHr<L(hJ&K5gesmS$sNWsfkDB5Vx9Fpv!b1e*sZZ$bX|NYgW2Rren9cgU)i*Fm1t>h9^fA0#h%c*y(He?R!wUw`}CUw?b>4`2NB;LY>5Zy)^p<rfeB?brYKm;e0q)~Emc?bqM_{jdLZ`@jGB@{7$M{CIuy?)&U7etPiT`@j71=H~k4`xoyXeEjIc_gBw9y?FZZd#4ZIUR}LhfAaP8$q!eruYdgb;^Cv)kG_9(bM>I~>eG)s|MAri&tHG~xfj<TKK}DaeDe1DtE)G+pG`CUaP{`xcA_7b>(z@tzkhT8lefQj|FzZ9tlu2|VqB}YSFc~Mm*Sx}j@6@<2b|_I4rTT7yZ5hNzx?InmcM)dX`Re{6GM9Q`uUIVmVFuqH#}xL$kVTmBa@T(_>>n{g_XPCU2hH_p1-@gnf7<{$Z&h*bY47Hi@JN5V)su^5<B{(+?(|zPOpw0WG)XYWw>A7)h?g+K`78?+4I#?|MbcH3@av<_%egLdM@mZ*vw`3^MxJ%_H&Fk+st8sPv1OxQ1^?Y<xh@jT+hRmV>)8>zOL=d{l_cwvf1opV=W7^+9zo*^fsz3^TcAYKk}F7m++8-)>Qq;_`Qp+?)>to)xH1XMsRLdZO_uK)^2$~y0Yu{oW~!wo~QA3CVTf@u$;@s{pB2fB44n>AGKc23r!|`MGu%At2oYZVgXOSu4Y|P9=vA}M1&N0jPhXe4B-7ix_-uTxN6gS`W${(9iXYdxq5)|faeEXzkYr7;@vNQy1IGy>h-ICo*gp%4e-g-A2n?0*^!DLzKHbO>-Y0kEe^x#C%|iXJj?0bZyTP>`J2J$_Yd!h^!U{}S=+dnpViQF-^(AX2;`O3T12`N)>)5OoxrODYX4#U^5*)@cqlEZe}EldugH<-!==t0rJ8@o!~LTz?}c2S{~xaWvETh?2OIdw`e#lUSm+VzJ%PY2&rP{Jx#y<Nlp<o_yJ#~|AdVt-ek4Rub`PZwN<ZyIplTb^P~IQ4+KPF6t+<&NUIu%BNLtZ__5-RD$faLy?GfUyM{NBtuQ&|fS{Lajul-8pdwu`>=AWE7s6}74Q*LY#K2poCM}HpkkwU+E)HaNmun13s0TbS%04m}b52rwqmW>KFJ~+mnoR6_Fm8f9eF*S(8>Pw9@?^<h%BBOs9P<;<-8&YdHbcnMpRmvSAQ}8~QqxE?6kWoVSc~gmBRY$~%M~v&Z*@u|tYSsO^>d{$o=Jd;H7{{sS9!Jb~Hl#uCdwV#Q%_(R;r*aDF3CVn1KVK6a>dFebt_mCp$qa@SE*?cvROBM2tK5(k?WG56YaSseD$?fz*J+0%3(n>|hNB)L;i^53+T))?)2N;b(MI5~J^s1iuo;PnGf2GJ;Y{orD-)X{{Sq>qAs|ys^aO#yfU<RL(&W~CshsEXvv@a`A6yW0JFC<7Hv3N~WR3^U+Bj2s(Bz3e-8^=bu-Fq_fAVpGZm!>*mGX}W`CZZ<OdQazMoV>*i7tHPdL!SyyLtZMyQ`a<zv#!RO<JjT!4GZw^>UJRhqQ3|%j3&?4Dfk_Z8`#*)t-avVde|3ysd^iSwRhzuLVhGcseBASBo}DoYEkV9|-!hh}Y}|G<Hn8603JZh^#=uEO=HM8kweE<RawT#~kQLywGF!Ry#n4x*z@zAG@uGOij{q@*m#4Px&(!f3b@3$x!HN_#hWdM7&zgdi2mX2fLskeKz2;?rxrDn){T;m<2*2TRyB#vR}-%mBc`QinCLeO47~);TWJ)mdymd!7)#4`CiqBbawZ6H(0yd;w0@S4Gr?((KPx9Wmb^$GR?*b5bodE(OKzJ{sB$g=I4+GLu{Gm0c_i)9}-A{4l%1Ng+eA(&dYOY<Wr=Nud@8Mu*veaspKjZs0Pa*uTa$SMl8@4%SO%9uoye!L>UYK=O>;gJc5`kndfUiB(HiE-lTqN%3?<ER2m(VxSf0D)#bQ&LCdTh<60^AcJ{E&Xezq#>=+jSSgV%h9{trhqq3VRPAVMd%4`Kk>#}WmC62=Di!QiS<i#S!zst|}9I9Y7A`7`ZNYy_}x;l*LfU@TR3ObKKRYA+4`k?bp7wJ6c57*b9e($z-Mc`nr=1~et{Iu*UY+DV-KnFga%y%*nb;=MwvspS}$<-#Wlv8zopfgp)8-<LhI&S7+1RAVNNGP*35m89H_KJ$qYSyG@b(WS;%30;1lJ8PZ^?iXFi8{c9yB%-AZX-7LUkD?-sZWDyFhOBQ*7u{&+gT)>N=frDB{53-IyppgnHH#K^@gbs!3yT3_>d~hYSwu-_nxmNon_kT9o&~xr5AAnV>oQ098cV=pudO!e;|SI*rI`8X)Iqa54^+ml^^fcaT$$5-E1_od|}7wwl$oj4>)5N-Sn7w=Rt^Bs@byc0V&Vh_Z2Hk?YkV@h6NR1r$^!dtC20kZ2%E-Qsr6ENwbzduEPW{#>uZ;px7V?diM3sptgW!N>Drf_M1sRk<Jf+Jlh0*e7PLWBRBv<uv1m)3CpX+p5}eJcBQfM$E{vP{%6{;1O{43RrZIHI0PZ<Mt@L2Q5Y;RwQsThMm|U$70Q>X0YWA^8m$}kX>q^fJK;yL<RL+(vv9`P<t%pYhjc48e8E(rBQt&GRr_Nu7vuwWer)_eRb&}>x>?Bc%IqlMp2M|Xj%@|c*{&{G<~%%+$Fm>zm+74Qa*!10n?(s6g{<bK;(Dk$i{nx=8!Z!@nJ#B^obmJOaskgob*;&ajAQh@713Fp6p0E+DY~R^2iY?zXhEdK4_8fEfympbZL<<)oyBk}*x@*kf78;VQfho0Rfp2*c_iacbt$8Vg}FfnR@eN~K_BJYrEza1!!X&IOciP-0{nRSf{Y2t2wLiNwj)2hdj02Hh$V_f)i(pDMsgoJ!(F!G?xA^t_Hn*N%BL^hZJ=s0xD{tDe_bjD^P6Q>Lg>}xh;vNM2+Gu2DE)%dWRce>{U%+R8cOe?wL!`T11!T$Cr@=>m1HjZ>+?#YZ>tipE=9SUBz3ojB_9M$z8Mwx^*P=$D=+D)@=Yhr(@s{2wT5gE#O=UW(s5zG%3ia6^MJL+pjH0KmLpV3x{3vdq^q{cO2`Z8*&S$(v3$yC%AK+b5H4dqbWUAFJi$FA@l^mKfSkxM?YykU#T1a$w%enF)EH%!p-nnPj6y8fq8a>c9hIiVgLNjdjkNjmEMaM7%pt{9y^<QIDxf1F^=^7{JCP$RR||mxCRE-1sC5%T0oGcMS*gCvU?R_zpq&G{A}0-Oh9`vOx>|fR5y1yHo_Z3Z_yuzK#~?9A!EU`%;VGiF5Qbx3wQ~CRD3S7yBNV1yvul<**ugv&KS=jTasAa1B#9Vz#!&5i-<bwzMHwA6V1YQ1fDg?5v8il{4$Y8>8Z>yI6PrIR^*0d`CtT0)tk6fK=+F<=^9Ia1FwynU()x*gpHKXQcOvJ-$jM1~B9G>ex{60V+3=+iMH@rpz9lKeVpvq7lao22%d#<kdjMsk>6?=!>aVBYV!#&A0_uB|jIJH!Ko%kpwUBGQ6h<whq_{X>`zJY|0Lu*xLiGyECjuVUEN~DD3;naa_FdtKXDEOKHq{@wpT*MkcB74wE<vCkrXcz&Cw)TH5P9<F7gkDS(A5wd$tL@VCy?9sECU>@Uc6AXRLLhOUu0*ofaK<9I9kTn33V{bq8&Q&ypvf5LF6(21O-~7HX#TLMyP%4*#v{^aT!X-@@i+pFn)zckQ71&3hqCPsMp_=*}lo}!YS=RP)x-W6J4HAWeN9!U+I3?B`PkY(<|Z7FDbNByEX2Izv%MRq_dEtNY2Jb$usLRT<HzRxj8+^=qp?-KkZh3{lTv{9J}Sq0i}yTjQRz=3oYyRvhSI}1%)2LK;?H8`-v|bS&_I_L#%9!w74)<@MMkHSFY^5nLOF*e1Zq#wFjy&CK`LhvYe7<G`*aWcRIXWuPS1M>dDBwF0X+Md)0viB4R9zXJKS#7g3QDPDB1c@MrRHli4~`mudgIwBP9%qXmKL(AClyVVkT_Z|ghIe^oz@lnzX5)i-XQ&R6Ysu;t`B0s{}z87cqPK2}%6<A_NSUj-Qs3H}_q%;dCniz{vVpLwqsn7R1lnq#W!i!G-#<rQgDAfYI;7m;!{3|hF8e^N6cELr)RF_A1f|MICs!dJ|i1earI2v{hE`cxB6y)3uDbwE`^=AkHuVChiZ7%hnp5WuYZ473+MR!E!TTUk=BMo-*1{qm%pFRn$OlnT+Rab(Pp7oDSb7Fs9z=VF#~lc2d2$!&f5sMGtj*nA*@uw25>xN3XQNvBz(><dVw3%hu2gzqHyFV<sarhNkag_<Lp+$7bSL<ZmLv<bPG<Qn$VX2Q8p<}W6P%9NJn%8q;DFFY0ORePJ%95NkbARJke%k#v_l;*4yYTn(+9V*-)V8~!)Q{}{zIyv&G8ubw61k!oc_RW;bl?sOyC^Y$l*ME;DrJ<+0k-F-!njHjGyP&Y4GNDsOIjfTSOFE(CClF@3DN9!}Xw}vUMA0f8nl6Q+zY(R5To?-H7znZzw0by(ESD$FbMlcX@n&LL9LM~UQYRbM<$3^dW6izrELUEI99)k$jZAX*fp#>XO1s3UtQS5(N}mzVu63-HdPG$7Z0LhklAKuLhWzMMQ7%D5fFdF#RV&;n@3+;{P96>tD$!n6iCpRAdDpPR8RICMBn2WtDX<Z%Z3`C1${kYgw7!qgq`cV>IV1gBBwMAFKva`&#<zd^gFWEN%WqCw{rgeeA}|;@L!tS$*-;U!^TfPtbExupCUj;R_oG1}bx@%Xitq;Ip>jx|0P<Sj=(?o=EqOc|K4P?FB!g(^=Vvv@<;q)GnZ^RkSb-gzRhai2Cv-b`+#p?TBv3P|Fc?SpI2Nv)3wi!~OBoE$h0`}a8PbYVl+aVb6QL~G5NS9U666Asu!|&WOJn5S?(6hZs&nEHGq34@$gMnhsM3?(Fd&gBGSkouh-$l+95*UqD&<5J^{CxjT?nCuSq%D0IB22H&4v-YEzc{SsXSOMZA3osqJLWijT7YMtADgMp0PZ)e!MH9GE}ifD*ya4CNpRb1gQv0*X=3I#}TPm-UTSYGi{eN2Qr*S>gid2pxKluW)5=|e+3ruD4{Gy`K@D7f-LRsH}FLmOEt9D>UE0fRM`LR$%g;_opIt?tzKuGE<Gl{dGuDEwvmx40TVL@n!H=gmp}%VDER$-)Uhv}72kpF4cWYOuy&%!v#aFsR;%OHm@$Qa1exSGcSoWV;I*O)Bf0350_X!L(p!kSh$~;G%AYFUmJKvmh*CEbF*L$r_Exw<m51BDZ#jJhq#(-ILasS!w*liq1{zYjWxbIPVSxdN`C}D}i&Sq-Pf#YqH|h=Rt9y+WGW5k3KjT+n$SMM&PDu%VVaf9-`7p%1EJ2DT_1cDpd`E>qB^XPMq}0l!x~@uEk>hs&Fnp|t=4rX$%#|VOxa_;cQfrP41Ou-OENsG9=u53OJ)nrv8Ls9CRHQ@P%NpOw045G$x1jH=TbAbSb}02cjqDzi<~|nt2nJ<TX$hw{LBh6`=_vG{2XI(k?SdY3eO8nl4>I}~0u?aP^jah}GqkN4Ix;qij}ms(vcMb*(dl&=5|ZPP#=+5w$9#jFK^agU;@gBr6CvkaY6zl;1+4%+bmJo##~81R<2I6n=SO&_5D<*~Xwb^LxcuRftnoA!{hSY>#meQ}tR*Q1HvwtM=>e1ulRlr%wuy-~p`7%I_j{z@fq*;GMVw|#;OZ0`oM7z|M}=$WjyR6b3$P9nVh*jUIK^>t$_}?d*0L@NG82Bbyb{qI&>D!}JbyQrU<x5iSLuzh?>^C$E2?DI*Dey`Il6uL)d3c`Rx8v-KkCt=5@cyvseUQ&BJ<wIxb~hei*OQn-md1=v+rrZAlt<V={EF^Sjp8Y#2PAB0ngP@K0Ox(U*f0XDGQf+OB})r7jy1K0Sl=%4K5!Dqar5#Mm`hV5r8yL$K^yqg;8@6Q2ljSA|lCg_3B)V9o>b4g&Ip7l;fPY@6;L-ne5HO-D&{)-lftu2h%DuoWVN@fGOzNmee&oVS5!Gn44d)X^BNIrj#dQ9(}SDk9zZ0*LQ=fzDa?s*29`3Rd?uV5h28xR_@bl$&wBcW-3^*C{1)fhJpa5NlMT#J$C293$O>;XL8e|WnIz5cxPgG=B&Y1n4AdB*{kY^O_Jf2%==x^6%$0H$tfyQ)uopR?m7sWp%c1xTPTJ0XX*Gatg>rwt^1xgg2kG`9m}mWIBW;77p#W$mGCG43Y4zzPAlZ=BkjH(UcfXdw|fcA)}7DywJUBA$L9Tkh(uc@mXxAZBJKD!II+Xul@|kts3HV`5^vsK)wWfQsSj`YM0QB<IOXj{oG8DSBbJ4v9a5z9)$TB6Vp*E9tlfP4Zk_E>=zbyBsdyCWz0i8?Wiy4lmR~#ta1j?p`5@FK0jJN}#v^xtg8-iCHzgb@gmOSYVqmU_I^~NXhnG%>;xndY*e%^6*yF3yGcgvGV2|8LZeO6ymBO_WhG;asO(SP<FB#vmpn&%zX`?2d+j!3?_$ywzRD6dwV(*5#=y(7`$<>^iz2`VoD$WjuU468EwF&5ojF9*ape#_~W?WF!XVM{H@Y3TCh|Q&<xE->cok>mMHb5ci<AH}A3Jx}l8Zt%YeUTEaZUI@F;0aq*1~X$zScYDlSi!acI#j|dWr|kVCM&L#&P6GT%nFd|dga6LcW#z{r4iPHDA+MRg5w-TAw!bf@@X1cP!GEVlGFnAyvB46VYz}%1VSd<prTUb-1i<#PRL!2Ueqt1aj7ck(j<B!Fe4bLw&K&pUV50&j9;40YBiR19;j;t{XHl+JTXZ}Zzin1bowJe{U9{aDCADyz0QPyTNW|HQ>rIm5i!O5Q}fR}AE?@cvUfrG2?-)qSjPD+gv4%`wPF0FKU7H<6n>~Ouc^9C``b=;8K=G?A)h?!uSbK96&`%Ba@C@R6tstYF)A@4YQ@p|RBLr|@$GiGM+iq-x2;dJhM1a@HKL`il_C(Vgll0QrIvLx3GyN<8|;_DJ>#fn^B;_R$R`8!kUc?yuJI<T*#{Pmfle9Kl*2$i2x~(t=ZUD2_P_-kv*AY#g3`RCq@EiUB&+Z^6oD(yW2?7okQAEHcy9}dqoAz~P<W*EcI2$m?T343Z5A#vNvtvDLLI{$SMuQ|4Q%ahz%(Mb$l0p};gw(~GggZ<hx~Ae0ny3kZUjc5fk#l*N_-;?`$|5M%47nN;Nhym;gfSPXckGIonhepI?_EkpgBn2pgPZD;ejAR?qlt$jbS8J{w&qJ5`ZDCe%$aFmOnuGz6!P2Y*_4^qjrDA2-_1CrzNFUos3nVW4R@z9IDm#SF-RtUQzh@LJH(X7@G!>=p1kZ(cdkM)US)vpk)R&dBrU!mX`#W_)_n}Ro$w;8=P(%>!S*4^2KR@OnX^O(7s)qAz6*x+y@Hq=p+mVrMq0iI5noucJ1Oyg!mb|-;^!I#26szWk|{>=aY0HJ3m=2)U>;c>f^eU4jr6$qj1)~BgXCY7@#wGtuOMzs~O)zG?pE55`RM)xfNNptD-~NV0w5AAVB^Q4pzdNa&;jbp;FBR{EpZdnumtlvUh-z(>uX2iCjp3`+0yv+WblgDqvpc6dhxWJX~GIE&2zo)IahfW7=tYWJddz(57-VLJAm>#EZJK|AfI-=X4K{oCc;&fY*PSb4SryXhTr+2-I~7d-4=`iPI7YO{^=PR}9+&cU`gLiUNbkp9Bm%bCt(Wgtq%fpolDII$F?uxd!AZqFD2)w{)nwv6g_E3dXL$k5<zxWl80z)y-y^bPYR|+~5UrXhUX|s=i&9eVsrw820}$=xpjdRm9JLv*kDBjtN=!48GG}+9+Cvoe5aU4u`m)5B^N_uu|EvW?w4RK){`vg3REHP_|zgxk>l6saZ7getN7jEB{`uu<J}C)jqt7=_n5}AR=(PI3?pjL1W8Zn5Fc5F_H!!$n9?lL)HX>NJx}Ml3#X2ugg9$6S-rhW|s{@$X=0&?#KcZ#Sw2mcyBdX1b?1!$^yGoNn<h59a1f~Fi0Ny=C@*W)S=QKZa5Owj!be>F_aVPD#jW`GO{O(Y3v|CN*=|M!mgB0c`~`*)Jg-&<Z*e7+ZVV^-mbWY3S<O3cp}cjy<y7hEfG`6b7Q#<CK%?Dm`&;kc0d#g$Zr7*6uqqsS%5ED7~I1~oj7FLFb5^6PG!nEFwE2-fn%vm*&%#&jU0V5j9p)Io_Y~MD!ov@QNWl)vlVs6*$O?8(;lHcpK|E^oqa)jFiqho<?W`_rEIha&%*C-57!WrvZkUsXZ_J2Dg~%Z5J^<rl`yLGmkuo)?DM)zE_uw-SMx~P{tSzl-v`>j?M$B~2-SpLcV-SWso6t|CP7#ZO-1a5aqESgN2O!=X|>?UQfikWF{K~_JQprt$V;Q|LE+OQ%wSlhzWg4eR$WX09!Zf<s~FDrPThpL=Tuka@&}^>s>BR(*!7rbvEPKL)?g~9)xaziX6>|<)mEXHzs^EW7&mbuD;Rnjtqd=T{Z`SE;Z*nLn3_D~d(?PxiCt+J>k7Fm)FSt0s8V^Ar76lBM?qv>k!<J}822iJn2l}>`9hctDb=_=f~PI@c8PRs%b|mjOGs;t;cDzi+L%bw?Grkb`5n!4G7}^-JHD_7#%fxe$fPEX$P|HtiYepNQdG+pyH`>@vXc5}j#!$e6Ie<Jg5*=Qxpoga8NfA^U2YmWO5I8VCA(5VJ^0&9k?1)@4Ik1XXNIDZn*PpK1d1@-n^ifX9hcr^P*oJEc2!pnz!}C3Fgo*9L#L{En_iI<ZuEJuI7^L~=#=9^+xG?QsSCL6L>4>Ma?tfKaf?89ayD)!r80Oh`Ax$|(b406Sm7XoqrBF?X&3v)vX`~iQsBGqnFKqIh_so7eHqVc^=@R=lBQX?I$}?LtjPcmc~6-l5Dk=nlK=uGAurNpD(YHP!Z>E~FZwD7(jCU@I^;z(3gTM`A0cd=)j=1y3zQnNVOaw?=shP*vO0zPl_XICNCFrm$ERwiP5aa<8=>kpQ*~mxK(rv|TQS+7g~@#(fFh>in?3@wL5e0ln3!C~wy#T&!hk)`g6b0|F)g4-vTq01w&iv4E!tCL&Me(mV6!(0wRE{$<UkNeiI90#{Afe4rWE<eYZByH$>*8Ej!+qLfGj+#o{O@t3a!EIyeuR2P^4`zQLWP)aQ_5p@p&(*{+Cb<l!1H%6-2t<Rj-&xE|IAHx_rzX?x|HVl63)1%K)Gf=nMw?hhuC(VOCHpTBsr1OUByTlx;Kj^IbR5q;q<faH3R*0&e^od<}p$zurOx%afzJ&urzze}2j1XwR~^dAGfyaITD)E92*qp(0To+n}`?ZpqLtI3p`%Q`5$F%x;Z+6Jmsf{$%~IVAwl73?v<q&Uoi@>T_!WN3LN~cj{hIwp&eEk}HJ6)N9a!1T&yA<U?fIFT*aBnu&NAMO}(*#hWI#)=T!vgVrQ<O0CF=6qPV;&m{qVLi7k;XQ_EUkP)B&x*ems4u3dFaD>YBQiJ53eX_bL0f8$60fDck{3g&VD)b?CGz89o2bMsf3x}(vY-5dKC7g!F;UeWmpaGmtt@9~ixOtCZ$OuJDF0ed#(cWaDNN#dDr<lR$U?CM`I#zd!H}$3C_MEUshN`NbNz<t<N}A+J5I~ft=)KYqssbnNtiOBcG9z=^(Qb}bKKR2pOZR@*Hkr9~Wlq4#B{8a9{o&=Q<X}+anz&;=pxO@_^r;HRs40H$uksq=&XjZuf^<VFzLlL5>QwkSOoM!QKom*}!9lTo*m3#gvuA<CkWy&T#~lL(9JmCf3Q7IaPg?Dd-U@ALbubjUx99CV;F6glbq;n2uru1<K6K`n>5A+dHxa5KKz&6fDqQm_KrLQ?SvAy}9ny#i5QfPWZ@t2lIj|?Qed{&Q%)AzFJ$*KSc6mC5r8%q+b%ujdVgP^_9d;l)2#12~oqK0y+~@0Vl&I;I!D8H#Szy?R`O$cxhh6A|S(k)y1;dtMS<O7!1x?I|C=#xK#>UI$C;&N%KFKm}|DFoF0j?NFhw&8)f^p?MdY%jif}P4Su1Us@6!n}dADv9Zz@H8YT5M7O<*;;AD|61V*`1|8z=bu>3)znAaK5vPR7Qgq=-l`-zdHpf>E)!cX$Cp`Zsm`L_cuduf7VBpiU`ssr>_?y?;-&0qVhk6a)_8QC5@JJJ0+yDeiijCGVu+vt~npTa4DccF59UDKZ;hKi2;GsaDSO%=UgQ<!Lf)@!Yo;Crvi^Sv>i^|j^`Nql#;Bdm5drcHPhjawVw7Cq^Dh}4p$3Eo>00WwDuq+5Y1GTAZ`lNtmBXN47*z>p_9y?z&qqNM5+wo+#WFaJrKcdG1F#_l@k##cXcGzeRen59?VDGp#`#P96?q?MJP7HN;EI;%hD9hM-{~x3GBFc5e&a%<+zUD$8fNK#H)M~$3BWunx>G}A(kR3bPaS_c0I39jG$5+;HJinrLtjV$}K}5zTZJXbGa%v2e|r9(nV;A!?v08n83AhqIfn`f#~1ADd<|D?tqc*TJk)f7WiHMWq%19%eJkO2*=`C>Q(4xHbC%NVlU7dDlQ3V)s;>pefSN?M;)4yG{GF&-D6db^GX&t=^1?YnZmZdnLhbA{+sJ}XPbUeF4Njd1ZWbJU@@XKu3LRV8BEo<n+Vz`=UkyWB`T7ez0-gyx%>hs>99{HB^+<hVu@Fm?kU?<YlEZ^H@Mp(H1AME*xj`t5ne%b`mk4q5Ut)Mlbxog=yZ+(^a{ytUafuSq6#t<65;omE$6oBVjPS_Rp<bn;tV?BuJ}6V=ii-UwsfbR3L-&rSrVkSv_06n48tTn?DZnWiH5@{IM_~X*S(YnP!B3zcd8m%fonwwyVf1~HGzJ}GRe+m7md}It`Fz#<@!RkX_elzy``CO%wSJ|GEL4EWeFO96CMlaA6FnmyH2IcCKaJmv#|h%-D~xT2ua8_4L~iJ+cvYY5xf}Kk?uMmGh66S<S!(krhgzSsf;F?l|+BLee-_1w{H(CrCdotvHjXPXKjB6IIr!E7iNWeVP$3M;pY+D8Y9VjZA!84Ay!weRki2{?eag}+*xe`L|Tt=SC~VQBON*r@g;@vFO<ESLz<7D0D_p(C1Ee;qPxSIkt;|m>49d$ULF*5Apk5d{gzZqpX#BMZtd3@2%wD^rStHKqH6Bacb?wtjy$hsuLUHf?v^yI_616m<>Q_Rh<i;3X?OLz4ZJi+N1;Ea&>L4jNM{mVK-HhgsHDmHH<wX?m`d5#0;fZI%r$7}L~y>^aBS|iSg=d9J4ntd=?HWKgDfpAQ|G?Qq3b#Ev>*o@X@ELRup%bKYL3*V3j3$3R#-Z$x7Q7{7B{dVm_B`gMA(1xn8*uQ@4eeb>jjTWm=II|YB`t2Bs`~v?cGr!T4C=6!Ff6TQ|berw<sqMIOhdr^@pLhhAsVpQ=nB*h8^Q6y#d1>K1!54rvuGAjYpf4BPK9H_k6oUX1<$HXx#60VU#d(AItz%Rl;^zmB@v<bf0E)Z0=)bY4~?RWs=RcJ||5onp92Zvyr8hbW`1+&J<b_!W^v2)C4ZCTnukUJ)R^xoZv~%()V+cQs8sBFw)v8ZXdg+9n(0KM1<As+<L-ZKMpa6@#uLn%!irgL6(%ey#(<qwBH=c?>4&_w#myIXDI@PO2=SgUQVu_s@8R~P6;~3{#H&BDzuz#;=W9pt-|~s7&-?x*(V6%!`=t}%!L1FHzNYj8gARgO>?9$?>rP)gHqe^*pBRq_xe4ClqIODOk6#&k<QKS8KOm6RV(uC7gZF6Yln1vn`%PFm+-Y9j}fIl#1w-&R(cTP0(C&M-tRV10*<Nr0Q1O*R5HES32Hc4SC_$zbCJ$|DF~tK91xExQ#{IT5%ftGcsE=Co|V9ZrUy>9gv;hmi-Y{kad|+*+m$`fDbykYuh6@UM2=o<^I8fZ>Wf%BAW#^gHl_)z^_B`rCNwa7)U`pzbl%EpyP<ptDCwYjvQ&&a+s`@QlC`#CrxsC2l01~%6dnL&?y!<ndH_LfmnR&Ax}o+{@{OS`D{G^LCJ+_lh>+(W_oZw0DBm`BqUoPPr_Tg9X(oX3*9!QO_uWnX-?%6Tw3C9VofS0I)Iy<m%2ImPrTM3@l(OBcVTz8*dc2CFun6XgI#(^+;aGn$=HI=4_4?&6FRnk`%&?st9bt;AaLfYN`(dWvl_s>o-=RdX&!<zJNTT$l%{JJ!o8wTyVXmUHBsBm!caI;FWgozVZ+;F>Q}mmtl*sATpR;w!z6<MWAvmUzqY5kMyxi85EMFjj_J<);%l8WNMgbRqGoc_+7_x~-PvSdrq34*}I11LPjdU>odWU%TN|!07hh;_f2EuujxEIMECWZ;YvAM)}?GNgZjG>ujfh`e6UPE}CoUlL_C^O^=+Z-fG<-mgh+gl1?HVBAhs^n1dk{#axCZJeA@;NIQ+YVCBAs2~zAb3bCO9~EMksyW0;~$3hHy|q{;4|z7F}At=L69JZ!Bvc=C-i}7LGXGVUWqZMRy4FMF$V8b&!jPtQUT+}b9kRrEVg6=G^j@8vKi9$&*Qn}%<(Kyg}v05hnz0(8y;NfLcaWc@PLlEPa=bIccPhpCagz^w1&!4)W`WA+3j%X2b7{+Xi9^s7phkteqAs1C0ICe&>$TG6DTL~2tS4}%ka<kWbjIP89GYXCC)|S96Gs$-*F^V$nIh}$x%%u=p@&{D-JI|C_B;{u-Z9f%ZF!k1@|_1i6o&i>}?kNW{bGep(V_4A%v82LJ{T>%j~=P=;j%D=ODgs57bDD<`lYkP!`CNUzmKhZEjz_zy=30lT(Po!za%ZM{}VYGI!<?)b|ozp4z*7FKGNqS1Gl%41Y8h(d3rzx#s0uDRVp9DWb2=1L+{36-fr(lc;IH_X`mWcv&Zt4B`wJl4KD|ICSi}581X&vO0oBlSB`Aow_>zR<ENaopY|xagLB?9V^S$jP<f7=lN`R^=z}<)OiJeU+qoaMwZSgZ>xk$4P2;FD{9C@GXjx|YS)qj!GW^o>*}r)15)qVY~;{lsN$Fj{~1l{&;JWUS0o_")).decode())
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
