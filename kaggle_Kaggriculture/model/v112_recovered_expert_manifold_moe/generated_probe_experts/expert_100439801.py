"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rl~TaPBmai;lS>bfrc>=C+akvSqUEf&$;oWcxI5Qq_XM_7p3rMMRZLH~U+E8}49Zf<Vo;om9pyJ;q~sxrTL!jERJz4jlU{`5cp_AmeTmw*5CcYpkkPyg4S{`#+f{_E?PpML+t&p&_q_W9HQ`qN+j`R&hMzx>xf{q_I(^WR>-{^O^=|HFU(r{Dkd<=21s)i0kufBO2HmmgmL*M0l^$4|fc?N2YCk}ux=?$0kTzkdCT|M>Fbm*0K*9J6mP|K6|P{^57O{l_1EeEox;fAjM4d-4YtA0mGH_Me}V2l?%<{_7uppZu`xq5k;k>&wr-eE(s;`|{H-zxn>v^5p9m@WE?8dI!+`qpM7_-}(1{`0bCs{-@V}|H~h~V*tN!|2<s~^WzV{df6}~Klt^Je)r4v`g(uCe|dY^DWM;JdHL!69~Zx2`?<@nB7X3%eyEe!e?>uu_=)S^9nOGwdn_35W2)~hZsQUBCO+iy?X4g4eWdQ6P6VWUcO{4Y7wpJ?{_+R;J6!%zF9PD_m9K37T|=fIMP>U1Z79ebJTxlG*H?Z#ghcy;uKx%{(Df6S2gQejeBdG<aLgb$x<s@|bgmK2wTH7ry!;?0ou5SDhg-(qs7;%(A$$DnqQ5m@q(8bm%wWf*+Rx4(LATBwJrj8!3h5Wr5Bc)rk1xOa<)8k`%TK@j_Q&7;kMA$(=qE$g@s5vHj!o>ebSIqpJ{oao0eeMldG0*86^pWLvq)#{wmuwSSN_PZ&8GY@@1I_@!5}{b`SeFWSQ8ntE*C%K*FSyvJ^4eHg`4~#*sbR0mmlA5a^QjAmMd(Tv#n*$*3S6p?#)=lP5!IiAD^B&`FX$pV%R*(H4)kj;m^PP^uyP`fBEUB|Bh@I$ir=WdbZ7%>^Q%Geq7Et;eX;wZ1lC=n16VdtkcZhJO9~zo04d6Yi-}is$cGP+$o1_SAF{)Z+lw4I=Ho82x9ZIUFs0DE<j*<!*wb9b{E6Gqe6q?ez7V-J-wGoNo;}I>MK!^&Rt#tjkC|U&!&t++VS^?e6Z%*>pOvn&J?^O4Z6NbcHL1C=I#@itA@|*xBJ|R1;-uMHr)=SUiFSG_+acywqVm@?!_G&47U7_BGulF*!OJeK*QLIvwz)rYylUH%kIC2$JoC878|i_pTmAo`zfhVZXR;&Jq~1n%D!!v`Y_c6_%nBhA+~Dt1u~w6*kk!Xn0xH9vs~;tScyGcXNR?SdK|da#=NEMfA!@nYfs*O^YRZw7a4kUM*ejCb$VcsSF$rw7eUF^NbNp@cIrHrbPufZ<l5^f{^6(p#{Zz`4f=aB?QIw*Prd!%YD{g*C^eZbzm^Cc9)P>$(6$x6>n08Mx?1Q|w59h2N{|l*-|+q+(bv<XdFXi~)G2M;tU;2w&0GO_x|Pip@>0>0hbj*z*t*cA3_;F)j406ZkI+dV_&NE0<*S=8a?tpmk6ykH_d8<0mfx}Mkx=+&=AE=Z-@uHZf9~AK`NskBTbH=gcRrHnzTf*$l-B4{Z)W^c^u+UN`C-r7fh#Yv3Rk~-MAyg536$G@^)HMHUu*{!OcBP}*IVy&Tf4U}D);H~FJcfx$DZvcZD&3#wjqJa47-%iBG|%^-;w|8=2sm$2G*zFhRgA^MHLOIY%3oq->F4u{POs-MNsxnfqaWE6zL1xpx;4QOSB-aKYa3;r;(`~rUXYb;YUD;RNnpQ$1l}A`A9SueDXs9Lv|FZCv(&%<t#t2!4J9Dl!tsCmXwm7p_=EJ{b)jmG>%qnumc^)#TffmM;-z{g?+6a%sP)~mE#C~2RkH%!Ad9UsU^;4gN}+dn)da}m)FH9)Se}eR5do7^`}Wi3d@Hn_N#inj~0wpSE9fSqa*1VEY_VDaG*l@N_>))GfCc(HnkW}DPke>QVe};_DZ#?eKh#_o1YJl5EfsRuQGjIP8O%wRzTwH$~sTIvoIhKM83W9EK#qg!4HzuablmiqU_sufWGyqN@Pu;&g*^b*Pn!k8*)w&Z>zcHmGifDYv}v=MC}mqi|Q+E|I+ZD4k3TPEY2YKcCYB7T&_k5NoyaTHQSoUXEL6R{Em)lw{)Jm>zvOGzAKt<eP!6lEd!n;UW&E1`1?IFz;enXXNK}q94!3V|M|9LVkg0T2{>Gqh^?IDI`jVV7{!Xkf`XiFut%&+y=FBJC1tCfVk)Yw^7Jn(11cAka=>7*(CZAM%40X*ENevV=T`i;U>~UYZaHJBa>J@$;N-8B8e+)W(3A)AV{SbeE-LjcNH7!YA$2Vm#G=XVkiHos^;kuur*lNV<Y9fPz-<3S{p(}-^O3v>rgtpX@Ug2Tde*6Y*1k27%sg~2!c>Z*xfmiN8oNaCDyK-@YE|@+0&kpc(3$~(9R_u<ZDtIcwW#$mkJL3bUr6=zVmnp8*szcn+@?ovBhiGoegOz!LlBukDkL~gT&_Lu@a@?e0d8SSxe+0!oH85RbwX#x?XX>!`S+SZcw)Aa=VxTo5M?uJQ&n)lYDK#xcXOT(#DSbdzjz<Xh?J*>u7@s%-}Y8v=o7h7byc<?zmEL|D}S?+S7|;u%Pox#=NCs4REyIy1<Gh9a^s>7ryccJ#eE7p&XWs5^F&&X>;ZGVJj`_XaUcgF<OlQAKcZiZY$%*~Z%-jIA{#<ZW29b5Bo$f9H?T3b-*xH%e2H+E&Zks{PMP`21wk?u66q_~li$KsJI4&o%3)RpeRI)}JZ?Z0qf{k9#D|i90*V15M8P7!%woMx9`vu|ORBo2V)F^&aHV)H^Jl*uD&caq*bVv@(QmSE3chLpL&iwUJIuD&RWA=%@}&Jck$Xzx!hn90m-cH;IOME|oM*^uM9-Sbm%wbe`2XZcqLonGd?t#mgtG1Sp%Qz&@aT%g^x5Ja;$X=?)NlXf*T4M-^xP>MhxjkSFtqpU<5G6gv4;_S(hc<%YqFLFO65{i>ZFm&Cco;7wLsuy3&^!Y5^A8;cx+97^9CY;QNDmyB>|QDK-SfssyQl9PKc5uCw0y*MHWT!0NYdOKx$dh)v&{$mKVxluZDbWQ`;?`Es3p3<{7mw9BYJkS(s&HGFmq%C?Cp1h-e&{{o%A}M~KPG1)@B(hd-30K!h&JZr+A;W%uTP+S=jY2}Ci}-H3OW>URO<7vdgFt}uI9Sa~Hv{r-bUM%r}>jVh*Hc-pMBuy`vFR~a%>r<Rt|RFRKa7hLdan3%7$CuX4A!Uawd2=}YLV?Xw($ePsV@wTsAmm7R04mxDA;dA9!*>#&{*Bc_3>CfE?@N$ZL`r^*5;{sNp$k%our$^ROwJbM*a{?(2VhEz`DF}blO1Ttu%P&7KPXfy>5u%ceh2nrMrRk~vp$gBCU_wpB%lMdd;rx*tZe#kgBTooF4D&wdUg+6PT~V7;0t>d47c`XW{szmBN=^kT{{rhcK6ick)>LTFL>`*>f|wtJY_iK;fvEzf-bH=ph|UA8TVr_{DlNI1gPLGYefZ|sp~@b~&8RQ|qZ9>L9FlzG0|$uml!G1;%Bg^jd1M`8m0!ZWtag0vOZFkhBE$-TTD`D;h(w{VTF%N&-Ja6&&6=uGVTP(@63oK|3XG|V&V4jAj$~+Cs?KW3W_ii>-+JAcXxoi!O=!AP(C>;nv#L*psfLM#l&tDtIbASn{hI4rTR3U6gie`k;8;|YanK{Wl$*zmoIG&ktEyXU4<v#s+s`Q0cxFxM)FDB5eSbfF`DOXHL}yvNXKiCsTG#P#I3`7fqR54k*Z^AKxr&Ecm!ZC$xe>!6#}xbgM^HI*h(!c!qM~HNmh!XMJ&><(H{W`LVPuLHixl)cH}Y<%2uS^@*g>;a0TMY2=_08n0Jb|0vM(bmhop>!e~TsGw#3?>Gl!%_c*V(Md5i72Q+7uM|ClqA^zoTQ-yFrSfayd~%pP&fswu@T;bPHQVxxmM(DH{>OW{SQL`r8&220Qu(aVQi4jHX^SN=7@(b2Rf5$*hmd<NuO=&+)rr2Jh-bzgUj+63^Cv4^B9k*V7*f(PqY&6!|Ib|@57I#7>EuP*emfk5ELz!_%@`jkhUCg8-W_B5#EWhC}2+?W|JsZ5pZBPZ4JT3U;Em+ZYHR8PjnO1T9koJEbY1U9F<4=$49VU<$FCqv!{B6zCwVC_>w6PJ`ST3>vIeH(0V!?hN!-5v>4q`JLW5g&&bY)!MgauT?2J-so@q%J9q;#AFanAX)EfpRu(ij^7WQPQ{3W%!KT^y+m@9KYHIcCOut$S>-`;W}=K2Vd6Jh=;PnMC{V`ddv=M>HWD7G&YAmwf|BNCbZo}pMz~&h<Lnp6yDIXC#kb9ukZ@>T`f-yl;HvM9xFIiDzR``bXuSi<y^bt_FbTS3MzTu++0b)1Se1@iq}xHj@0Dg7so@2z3q&K%^vD1j26VTZ;Kr5&%~QYjqyj8!L@XUt=3{$7oe#>^pjNOv`!t3$_nh#!S0lGKxatD1bCP0t}?H3v7xme_-n6S8#rS%99JCh_Fm+Ig}i!llrls(B?^`t7Q6jXPd!4X%a}MM&@{+hZvoSLG8ar{R>2lwO<WtC?wcS1LfzJAZ!zv=i5#4a!WDY6LN2;&2MCV;Gw-lUNk6EDF<)P*W+gnw3ZdTXbKm{V^89{XyM~B$-QOOaX`5lG=fy<{s_ofczQFR*OuRo)W8;7P?T`NzRT()YY^RLUm%k@gd_dZ=nSJ*wUq<;3%1=lX;1#1{T-)gzN|Vr7#~2|JDJp3DYcp&&hDv*g5JfFj(36Tepu*_}Di267B0!XOfVSqtGG8ozi>oLBn0<$Y-GYwi{F|bEGVe&0M<8d%W>SSGh~dUWsOZ(8(nqSMimNPQrZQ_w!8~%9(w~%>)D;!aW^uH6xM+nGbCE-dS<cg;Na6kd@^95IYa?|g)LfFsBl#ma9+!`dOxHKVY~=?&C;%bj(X7-q@#(w78<ggl`aG=w-LT>&(({V-S<5^zKOucY+)#uHWr)A>g0zRV8O^Xt%WRBrJFQm=^?ADzhY;kFh(N7IM0!m@Y1aizP*Ar5%D!_f*n*E|`|Sv9;<K}jgji0T)sHKF7tK&1)<dh5xe$(>+lMaNTlHO#5NFA<II}r;jszN-LAh|fK*JzwR@d%3(5h`}c=(rb9_&vHublxGg&#T0Scd{hP~^Y@Hc*iv6EyHjcNi}*cH6aK!3CZf5a*7{=#yUEJtoG?6Q!5?FZ!&pR{h-Udj}blAnq1)L}Fkwud>XaoW^uaf>RpMdya3-P4ezWhJ473G(M1nAotg3r$JW3G4&th;O$TNH;Q~3T`%yVo+hygp%CMg@wswz;u{c<SN~d14MCKS5VK_3N7vhc9OU0h^;1ThH`Hpch_8nd+#isDZlz6kqY{-CPD&+l%@J39pmq{VGke(}%NHu6YsB3<S`uTI;$ku&(TMtlfhNLmbd`%EcYGb2J!CT-UISI^bk!6%G4+F#u|F%6NkveY86BB^klFzGVIis#gG@tmdM)uoZ{!hzuPyA9>#Qp}-%pDU9bxMOQz%6xYErx5&uqOR)hiPLPYwX&F%HPj5D^RO<I@o&GFOg008@r1TqsF*XhKT6eNkF1msj!9^Qi8bQ--6;CqkM`Hbhjb*^9oH!k&RH&5d%NO2CL0qdFLes=bwJ6zYAEvxlWMq+*twdYl*>Q&ee?0cbm8P|Qc8GOs+>-u9HCtAVIEbL*DJG1(SrCyUrQR|?TtN>tWtNRNsYL_?(!L~^EmWoH|3%gmOmqm2kL%i<HYy9PB3>k%&A*{AhzL?IJb1;lIP-EmznRSJ^wC1`_{2PBB=2>CSWdt;y9A~GjpvFDfr0wQ2SQiLe9L=@GE1(M#(_+wDgxFp?<?K<TJrM%2@{K}8Y<$5k;^jDN~Kj#R|n95XfV{=DnhIn7NH%7y^E7W?>Mu@~wD3_#tFr`ym98#8TEksM1GOQvGDN<9VQI5GpuR888rY6F{(hbt?CbWSR70s?4i{FQ6{X$whvdxSORJrj8+qY44@Q7?JMk_kBu6H1c66ZTLRE;*O&7M@u>l4*7j%T@!2fW%BCR15>)}E1MQm{|ixzaz}tOXgh^eTuvLb`}{QMZQ*&03*k#yN>dEVQppS@yd1oYn7imaJiU5>!`G2EoWkCw5{WT;?k|kn(kvI&-2fkUq8`Aqh?l{v+AzpkXE3j>lPM$d2d}-Hfww^jyfm?A3EIVu%;^(2+`5#L*~EE-<z8cs*bsR(qA%fAj=MCXMK)?ruuM&~#C1ckzK-o=!O2j-zso<DM*g{i%{ewCamQ3A&-zqL-BYCfWQ?UbK8rF!sU-M5Pbce=XnN0lyi;SBCu-a&)9K1Y9Fuvguq==bt=YR%Yskn|d;ilJ)n-&}J1qpDU)|#KTwa2IU%p6(EsOIesLC_oVIcA|rjpIx%o#+C)B~cW#;Edn)#+YL_l%1B=$cs$Nbkqo!XrrAQ<6=JQr=Vx)R#=?TnNwjgmWx>-h}zib)J>8ya{Z<W|!dJ*Vdx_s5q3{DyAr2E8@=jf^hl*|#GKPTC;D}lEbeGBjC&e8gml#vph2&`VhM3v_CK!w3wy&3&D>7y+3Fwu%el{FZo5DV#sT09Y>%2a9!W+q8Ddn~3<eqPcinUcDEec?1`ufCDg{%8>Vdcb2(JXZgT`1L%z-w|PVCAD_Gjq?!|LlQPMW3@1=j&HW<TI>ESHd12iJ6^^HX1ctTSZa9Lb8uov1Duq&&6UW4O`(FRj313}snk4Q(qW_nH~u8HWH@t!=gw61++usNG@Q4aTIh;`rgMVeWN{DQgKwcOvyU>F3UAtwy`Y3D)A|P;>gL|`$)<E?wKpZ}5NF!ym-1AI&}^v{$e17Jmduo-h^!q9`$Rz7XyMZb|1N(^?AjCQOEOE0$<_naJ|}(fLT5I07^Dtde8!y0681)(&bPX09?u7j3Q7pqpJrtaFThh8t#I`k^|riB-3DoTBd~9xo{I9Ap)SsF@OVlc)>3L<nS3fwf}KaUkB&Sb)2E*q?tqUM7*~v%R*THHA)lS6L}5rx<vI$}EIg+^FL{4td!K)n<PR8LSEZ#hCKhjZV<V5b%rrsGKB_j8syaezN2z2iD=<qKPSN52=F(p7?&S+Bz0z5q2X0r{&uXr7mhpCY-@kKp6*It94@%cP;F<9ugP#g2F~$}n^j-Fa$VkbAEPBT^HKNZEsW!%UhP|-$46Q<8T3XAz!D^GH*J2zdJFBTPZaZt@0MVt-m0tN9B?2rD>~=?|wwsndRBnb}*4xg`y!uAwJL-<{eP#FmVXEI+9x+GEsIlKn{vpq~p3FKh+XB&xEIPg^{}kpp>8VMoJ_7q<T&j2Q5+5XVLOVHuLJ96g1}?C!9Z*FlHio@F#>aKer&_u5Th6h?hg2Sm>N!Y=Uzt7V*r6{>y-?P`k&c9DK#Xd(_Vq;=5=b<yEz1Q~p(9(-i;pt0%yFGg$lI%_s5qfm(c(uG@Rmy;Y7Hdme%LZ`NuI<?w8)5ns=3Q^yS@lR;;oa|BvW6prQ*yzwj#u1MVhB>Jyvt^Cf355bWq^N$hc(pswD~E@^<eUj@F-{ko+vyOp<bnhH)U(&#}643GQK)t7mgLASZ9@^)<W{$)C;8dU@&8L1s8l+eO)()vE_Z!Y}_#ARR2jC@@@8))unbNHSf)vJC|f%FK)+Yg-NI@Qc<@rZ1~oe>Ih7z20MX=%1Ko1P`kM>kHuVIv!K~&)8OEMxqh%$hE9_QDa8;YNaM*A%Vc2j3de?!gX-Z%1^p2E2!F|5nqx10M)Eg=ne!R0X#uZzFNgz-c=gM(98((GE1Rf9w*TEH_AjsT^yK?+$D)ahCk4m^^Mn75##uo)vg)h4K})bS9G$p_HbyN*PyJ+Fptxw(+*O}HDsbV1WEx!IK^|u*b(6yJ;9r?PU597Vx4`mH?#o)k_~G)FcQfoeh9EEz9MFPdHFz^ch&vgYY!(c2Csg2z9g<8ZR55y#sBqJi96Q&#?hY(z}8_&^s+(Xt2n#y{Te2|38U&WR!d~+fSE`#l1OapD$KOSBz1Jn^9j2Ozv0~8QOvDTW6UlA9n1KI@N}Y10F9DeiFcSlLdR>)&fMkOoimu>jDtEmq7bCrm7v*2fNOR~OfDx7*O7sHOtaZ8G9>mnZfXkY7GPYja;~)>)#CzG^r3aUV<tWNR5Zwo*}jFU=cqOyt>ZW|>rt6i52~AEM8}#sI&p;UBEde>)J=0jdG?~AJZgK8m0|Z;o#Dr5B=knh(Av*)K>xr}&N1!=lqCZ4PdNIA*xqm|C0~-TK+D&;{wpL6Da(gps~Yft0Cu(JxGAwh9vqQJSMT{&;<*-I5`+)9g<Iu0o9@HO?_Q6O5iI)l!mCbeM7q25cswmp>&_~#ud4@lWMVx2^r=e%DkG>SBf^vF=vr|^B_*;nN|wB4H5f;k#&%5SYw&1s4Ha>tFEx#=s4>F0%>(2cXnAL$$+sNhs;N0<IdC<kpc%gVf`nBw3q~3zla<hISu`ErEw3GAPN&ia;d>0CyhbA0iq;fqWfHi$AyRUOMyu(9Xj0$GTBbQ&el=f>$F0c0R_sdtn7k*n<M*Npv8qz9-cqQQNnxiOsLKM&_l<1K+*kL()_>8tY+g}SYfUUKp;LEj04kzNor0KcK)J6;-lM~}o#)B=p|2d1Y9tz1yI3*v$G)6oz8!(3I|5Xe2}A*hCjXP3ICaB1rYBuRORC$i3r#%G#l7{25Ax==XKSSCdR-?zQkwxPH(ZUQupvktlS-o`X@^c$hKa7^)w13#gIf)>thta4_n-}ck#+7YPj}>KBI73bQG)Lzp)YF()hKmkzaXJMe|!2PJ6zl7h?J~zZam#euyR^6j+S&hhs~ZW(%~P9Tl1G$HqfvQBjc;0CL&}pi{$7`U*@<*l~jPC>-?;%?ws8kQS|0^q#I1XGaPnGiAY(`XZdlBXx7e{l=P-k6{R7G_eEkOsi6zV(=kKlSOW>}eHS@y>~1f`XfBJQiJ%Pg-oaEwFuEP0HSNuIqA!d_63w2p^1!rb6xq~#i)vAzdM|IWXDnq|&Fe$N@DLXXN#ya8S`4o4d`5;S$qOpIj}!BL?(dh#?*?O97YZ`ZzgMdj)1UhyYopiICp^Pv2g_A7ywxb5NAe6wD0(S3|Cb-X{Ela9RekQ>n<Nrkpbl;Hkmt`>{;`uhhj8N{#Hu7UA9LgD9>-qU@C9wNV&k+6ZHS-qGFo0Zp6OhUq{6ANCX(i%EE>P&0%v4oXPqOugpB$?9}8143Mw5?+iKay3zS5EI5BR+9rDy$-ex2+^-Biao`$UV`}70kG*0agi<apgsZ}$bP~}zp5CPKqLw9t$I_B`#j=0fR(RNs^!>goJBbLWKVebTy0lAT>5c!3PRMuTC1mzg{n~P}>xtcbXQ%+}pw^m4j>*gaUz--S@w)+@@1C4|?+P;ypR=x~slE?)y<uF(L&)rM8q1oE!?-=Q2tcw2;S-Qy1an5kjWNk|IFdDToHHSPc_9N@eWGw_(u6)Pqp4<Sxtx^!!$YM0&JYu~zqE2%C(m!Oc<BJ5T>jI^j`93(0>k2BeK;*p9I7{FYpK8;=7tB(UzlzqaI=>n>>$Vl5;I^VA_Ib!WX$fIjw@>7Oshk$wQnAaQnuskmn};=yBvc2LWAU-imGmZOd8ZGl{AHxG3*nIq2fKp`GPBEkTA7p}6zttE#ZcW4aU+RIq97xh^YC)Y$6fD`<YVngXn7wtxF~HOdeSHwyC%^<Tp<4bk2;#mIL7zM?0flYk&YRp4<Py4${rhKWSe++_(&7GovnF#{EhPXtN)2(2Bw<kcU>)&KFd3=9O-yVrWU`xNMd=sC=7XI7-i>2rBJ)ur;_z)y&hx@*R$eJ%FR~Lt#-bGg<rd7i#X@9-b4Lq`t(+Udch-=suHJk%6yNEW4A<^WZ6$e5W(;(AVxpk%0lj{bEvhn@iKqCvTC+n<wF>V)<y`+NX+;_>FcIc?(2)Fsj)l`W4>L)U9Y}swz|!blAt~ZJ!E4gTQHCgMzqBwGr><xQX(E%nW_~ZHdY0J(D3U(PuW&mUfS=Hng@(KH+OF>$44tvK)K#ifz%<*WRbFNzE=Zs)g(e!WaS9Iz1TtfJ1QE@yh9&TIF0%~R{DMcH$6)Cf=x(HjqyOYJXYZkdciM4!>tc&58L2Tk|QM2#F3kIlyVm|@tJ44yzyARe&rL^y$fagi|+0k+d6C`a-bs4K(%Vk#iAX7BqOl9Yd0gOo6VN{7&HEbBp+;V*U}H<fJc{-nx6VoL+YgG1`y<ZMXtZkWgPFmN~IxGMND}QHoXC?h9w?Z)zGl}sm)?}Fz#r7S>iUIr;b?BxvmyxLPPzEdtOh!*;W>}5JI;@UiNAYXp0Zmx;62lddH=a0y{nat7w$a(zn|}k-=|N+m2&5bQTorW}^+#-x(JHsm^}3R0zD?A^?s@PT4Cpg`Dd5urGpvm~ne6YDo!y$ns`J&7!P}Ez35Kui9nC#;JGOno1oyQfd}UG7-#TGmd9EPjF{rpZHYfgf95%m?2a3sX8R7$mydTORZVOklS@jz6hH=PRLbmN{2{rT2pCo2U~V$ckaW<cPDFP?QGc^ee!g`u{&g{{P9VY)Hl9g#E`1;^5OXcU3tX-uK_E^wnF&)GPhzRkV7ZDq~040BR*EzgVQd9-SoFn5`oq{A?3Nnii$;Z#x|g7Y9*;~Epe`*PG4Dsk<7r#o{KWk+k$4KPvBQp7vQGE&b5S+xe?@NnWL#<t-Huvq2+gFV3CZG(s@&6D3a4$w?N2Qita5=S>8%7Skc;U>cfamA(2MTn=nV;TzNpH>N8}8u(dBb+^6*6h$=JwKosC$KaT0}dF)jlZ%o38ONi?vJD#1$u7v@f?5zVmsd^(d5@e9}{n&~n-$MV%=U@e3E2b;yOFv{WArb=g=VKZF@mAQr*@Ye{sfN4wXD@HDoh@^;%vN;J^bp);JALH)yEAk(*{xKF)0!#P1&<cN+rDGA;GNOsa;ycv&xMrg^1)I_GmEbovqa(rg|0AEg)dJ|$LcUy`LxXnJZ_-9s@Gx~aWS_Aa)2M6zijE?SK6qzu45)1GqB|w9HBc>Iavw~8_h~;;dxf;hxbSD^@AAWAy83Qv+9*65GKP<EGc<;SI8B9bp0~f&WjLnA%Cf_$t>;v7HW@|9kg5b1HJ~Ga>r^kHRYZItgNKJyvAU6G{V`8YL-r_(HoM5vMiHdd|U>CxF*oN!Xk2<N!7M?L}&=wdzMwVvKLt&3CupabZ1@He$%)VZvE)xkY&E+YBr)dsV4I2DjMDoZB8c*<%u2-#G+pZ!%ts+S+${veVuRnjSn`oqm0&A9(UCr-W;c{Gs0EgsL9Y?BQ_$dp%v5t+wRELx;ZVwrQNp|eMGKyNA@N~hI#y)JMzdtD4uy&fxm?K1#)^;uvB|&5l6FYB_YlM&qDtpH-5pIhLs~FQ$Nu-=acFrvOh}QuV|#&lFSky$#Ow^(t7+1yvk0IAEBzcPzPW-EK}yv*}7WJiKhB&Bf10A9)8sHL!Q6gnxM-mX5`$Y!iC@|c|jBYsAh(hD))C<=p-#gE?!rUJ!Rv~;<M9U#AT58R$8{RUnvC}_&KZ?6C$;!GGIFrRt$JY^~2`mH&CAC5<)SFo!*6*$Ul#)3*IcVeS0%z-%+%O*i_n4?U286!sF$BMO}iBGE_mQ@!qb-EjLA(+`H9>sJ9tI^(lv&BjWosRb)%mRAfC|n>V<~?|&rsQsl>BS)H%wN@_YYSeoH+1x$wFJ=>WEqIx-zdpPBE$4!=!BV~XKBX#>`RgSY2g7t<b?J%jMIw-X&(EH6C%iu8bXH<K1RvTk{;4@bSN17WZ4I0WjTw}fv7LR486{g0tRPB-(6r?(cKWcc7t?6$u6unw~<UZ59X1KJ8M7!#pC#C9^i4AN|P4&;<n1s}3H^1V#r%g4xQzV@$Vm<1?rquX}p}1AEyC;a+o78*ug)4QeE|U)R9t-I6mOnr`ERj`|BQ$OFwx+5?$#X=HFi;rDJ<$1@_AZoH`0<oOauFJPfoL>`p<?aCZQ;<|Gx~Cku&FXo!VI5|<}q@145z+>9k9!km8iC|o#JZwcR9xO^;lPHro!`u<IT)_n*-ZZlk!Mb$5QHA$GJ-S!+oc@P18Cgql`d4b{iCQqtzo@Ni!XKSdA|0BSX}Tc)JvhY$#nE#K>MeEK#udA@$YzN>iPYsg<VHlvZ59H?cw?)g3gp(<1DK(^Q2m;x9;5=H&B;PTTdgpQ3Jl)P<H=EK6wo=@ffAOGR{&CNE@VP^NrMvbzaCNXt+M^fiU%om|8f&XPVdgiG3dup2bhB?ft&gjk$a*S_~KX^SAfzH~N#Chb+r_k@U5F}LI9L)osD%}iI=dP#j5?&Q6RLNm>%Z*7J=!=skfUsa3Sc7N<}^F+I!kuT_&`c_y&PwGvp+o9-ivJT)2w3(K9<M8b;j~9k>>fh-QO7*xz7RX(wt2DP7gcm^`p?nqej&4NNNT(%E1MF{?XeZ4VB`{(bk|8suxiklAQ~$<p&QZoKNEzx2w?Ra!-31onAcrG)Q1RV*Q>=iH+q0fywZ&{AVK1Z{r2``5SAv29rn?>4S-NS_M=zv&otISu+)GMnXG5b!`exBxe~Qtr`a4A<zr0J8+0b~g>N1m1o9fhBqA^vjbs`yTVy-~nw*oH_MIuWM<-G7!J{ctD3uQAe=5ZN)1?3{jT#IC4MovX&En;0p{5aoPX*offuytbLx_wg12~Yb;S_5Iqup{p7FU)?^Tsa&yNSIl8v6`Pu57C;&7m+?$Ce32{bIlT2BNc+?M*PS|OD~-T(5UW?;oC(^77>3@mSU0WuO)o14cQX!Teerb=vjYjYI|Amw6aXqBNetq-b?nE$ov3D5sPrHw`r0sCKnF=H9i~P#7-vE6Zu6}i%IxCifs7?l@q1p=`1Y<M?&cslFMz9$!wxY-xh&>N@Anbc!W^~QsgoAGY3P{p$}OsnU%Ta{fgVhl`5;|T`;6--s(d%i(4AH5;C;WzJ6S1n9w!CTwhc|?aoi>wZg1S{}_G;`_JrvNBOCn8VhmINY-JuHJTM;rQB`HU)X&gs^ec2z2lWiOpNhF%ZXYVu=*F=#qrQ4EV<?~1-|0(#EfxJZhx&c=IhwOBbWw_Ye3^)m!+Si=OOy+lvt7|<)T#vop&4Cj$3pUtdqB2vIGnJ;i65wrLvR=GO(<4+tvfyj+zE1+>@2Dg1R{}&%)nQn}#}G7zsR9Ud5iRh9k25%IR%Ez2TNtj5ii)CIa<GvCMiy;SNMqN>W9oNSKEsJe1Z<lDjL?2ZLzMf;`RkXDw?`>Q!!Tck1{M_N@0VU+j^;wS8=c^<!NYSQari|1vp1u({yLIA=|MUi*G6@X**uaCDz}0`Y|ahIGgm<hV2rwZ(k>H-G!nU;pnv|LyGq{l}+&{kOmT`G0@<JFAr1KIiLK|KI=rr+@zIpZ@apm-OdP|L?#3`@j6{U;gbc-=D#~37|iJ`u9Ko`R(ui$NKx;{?)rm?d>ao<?a9e^5q|Y_~py@FW<TTo%+w$AMwBb{Lk4>_|=!M-~adJAO7L{|AM#n_J9B3%a@;DvS0Q6(Z2uA-@Ls1p84CC_|5Cbcza_Dgcvpiu8H9DAN}|Ly6=<MfB$bAO=NsHe=#(U@!Pc?!3O^KG1#bnHhL1Vu?rh}DmL>NH1<0V^F&iaqXlTf$3<fsX#7V(V*nbrOs)@)#sV}-fX01PG`5Mxehf4QL8G5&b~JW48h17{cG!fnkB!EBM`H^#`iTaj(E>E)<DxMG(3r<Zqc1dSPK3q`9yR*$cc>MO1!(L?M`IT>Zd-AlXf`wspm72;`s1P*5jZ~q8dab%Pc#sX9garbH=6TjoNxr!C2-sM;ZXu^BVapHZciq8s_pT|i5tMgCW*EulYPHkb0zk}Gs%zk_Q?d?1lNeAc{2HaEPE$o7BWvJZ%p1pD*8JU{o$FIg2{87luVv$Y|iAl?_f-xXEys}f`((COt7%g&g6ODxg#d}(oCZ45;z`;yTgH^rBL+t-!nk5BcZ5aP&#A>b{v$5LNVH0kBYv(w0dQzT$75qKPvG_rE9DVPGUUH$WYVu(io33GK5qPB{EJ+#bz1dN2g+jP=Uz|FAcOk3>6m+WOyDQiaQF$g5=Ix2lIsTgwjrYy%l&op**3~Le+aZ&_1CIfTBJG6#ax^Hj(2R!GA(o(i-nj)G*n_Lqo9zloRLEgD|lHq1Y#s9EyHI!JxP&lqZyGtokEB(f&h2F{gpz#z6@v6f4e_o@=Q1CYAFStjv{+vASNaM?cEQkWxwi`=nAj!;MiF+~Y1RrD8U7rVhd1X{l)7?<JNHpOT8r%rDH73QEO1seqy$+ZS9qF_qn_N<XP2#R+DiqMuY2D!QMF`Uq6ilS(#&R!!uS%DxAgh0v1<O#7JS>nD}e8|K_pCesDQodnACgfbio4AHtLl)HnXFCB-|aeh21_R^7T7p4zAf&7z7*I4<enV)daUS;}5)1?cFU7B>9)xfO_ieWZ&xqm2j1eCO-<p~9(2KPFj4-aKGtv-*5+aM?=sq=Y4+2U;a2_=Q1lN8~Hhhjbq6x{<w4TKV&Q0}c2)Iccu38lXKsE=+lWS>xK@%t5udqTM+6mu3R>Io%ny<$LM_6Y^lAU~mOP<A8470UCNzd%s{ig`lONomhHx+gTD+-a6)VC9#o6bY)mATD&|c|I547lE?(H&!$*HIQM--Q8e&mX5TCJ1HiMHURs)MRiYrDGtDtH?x89|BfucSuw%>Hf0M`^TdR=yn(G=I%-4CiYYfUN=4oJi3x9vvsMJ??Y~b<1ttYBbrnvW5tCtHQcp~#IqAfh^oPS_o|s?=WZ%~e7)R$R)H#UBCg&p!!t>@-l{<$q?N<|cyfj<c{y9nn4`XtOj%)wgous~W5T^X<YZFZ7teCV2lgqqRU<l<L_5Ru&!h{*|?Ekf!y~s^4>5F6Xeki9ARwMo%hm$j5ASibRP!(gav7Cf~UjHxyYF1B9X&y?oI1SFlJr0AQZkdYn_a|Ac9F4j-?NwN5!fDKSx-lm|f|JV%v(~(mU)o{V$LHk6aI#6QR+@6MPfnHct(}wZIc%StlLnmhlM{N!wONvP<)nIq_b2D15*e|1a;n5kN=|m^VR~9l+Uh=1Hj96+q)xj+9RUT?PMx5%mXgx93NSfkIu4sFDRnobMvf_5b!tr19p{4&g32Tdx|ozHNbT|+c{EN;%HyQW#Yt&3xeipT6ifkgZQW(ZJ_^;ym8#MKWS&je`P_n;XHSL-4<OV@8Ddd~q}+8$sYfLBPRD~gpFabs`5-6{f_Lyj9F{iN?_Zx5)a#0FMWg~CwbC))zkXZY<IPB^yCW6Hl8Pq=WuKtrpbS{0x<G}81f`n$-en=U%WwX8%~P<Vy?=1tZjy2`x8h`V#~JCJQvi9pa2ihYF-&D)Vf>ECESS2|n`gvifrM~B02r`zi(>;H0n-FhEwL{Ne218(F_;X%WRGHs9|n^?f+?I7)86fG$Mn87>7EGh88I1<5P!#Hj$-m32$Su{<W7r86`0I-OzPB_wCUsYHiTwSP`7fj0~|j(IH`N%WI-0C<m88N@(;}^fVP4LaC$GwoEA>*$qAG{zo$`VP`o;lle;OWFocsvIH|#$?1?$e138(Sa`G48w69MiIq4H{GMk+6jm_?HaduACQaXIQvlUF8%aa*|X<)xCjaRc+W7(i!Yw8`8UO?$vf*LrU;!sZSb8XLLc5>49$7%3@8U#u`;(!{QlT&xN`e?i}<i1MBAvw8GZOx|J3N3X-6W2k@g3KINxBB?B%rRKLu>Xtzmdz|1J~*t9G>6->bg&X}kCQ(-EHx6At-#X5T7;brmIWHjCoBZk?%@=H_m18S^+&Z7I~lA1V5ui82rDA6Oa{yLl_;JM)&yYbCoCSUJ%_huuFOSX#k0UN3oMPoG8b=p_wcanU|9Zauv7-iJz>G!FaQHlzXXI0P?A4kfpb;>wRi7mAil6g`#v}<pTKee)~@di0}rJqhUF4i_Td|QUKrN?r|t>MFJs4$u*|UF-(9whRgoQ6wiz40$)<K%_9V0_f{xj-X_<_T-?GX3cg{j<K1j<hv>ZvxeVDOzjhtY|p<o)A<-#EtKi{%YFWjMNEe<M%uH-5H^=`cR=(MJm9%y3haUS@xhXR&KvZ+sGV576h5y5301N{k*g=5HUfea>ae34BJPh`-5B`@RK9Z2>xVSFN6kr@<OK#;j7GM$A-Bd|ycg(1-NL<W&*7Bc(Mk(mS;tkZG@GSh?1pAeY>hIl11n<1M|fXt6W2CI@FG6gdIPh?A3Neh`tN>4sGGF42>xq?hTk(I~{KxPx0DzlY2JtyV@!UOlyIVqsGz#d#Jr3BCAA7n2|WDax|e<B0tvNb!VwlWlm%zX%CMh!&fPlha91{w5o3LgTQ*50w983I~d{`(=IDK<2lh*EQCA#qjdf;Q@EZZ8haDn2wA!p@=j`+;_aVsq=RY8=`DVZMYFy-Vkt+iULUfn|#D`w!1fq3nX&layKs*+Dx|2eOnN<dW9n4q>cck3y&~P@0$YjBtM12^wLZ7dnl?PTkPZE*>wT)pxj}4WMbWu?7uEEohqu4c#J0A9v2~d!(ty(liyC7HIb&O_Pk=C(V-Ply&~bXinfe`yuB^6YeB#%eQ>a8f02<{m|PHa8>`WGEx~$|0pz#@`j7k7C7ewr^~7V958Y6zzrmdak_`W8NK4;bl{w``|;T-PP2vjT!K?y8mD<+oF+MD+C(Iu;@l07PCGiam*U*_Y3TXul9M`gnJ#gvv*L6{seYUh;Dl2i;*0>N>cnXu1*Z+ZIyx;8%7LXGu#L0J+NY;MMzu`;^WyZNIZP9$$#D8&blSuNCO?Aq;xu<$OmhHdd1Hh)J!oQRfKPv32tGY=?l`AJziq%3(}Sy#LAs8<;q;5HXh0LTv*2{#25!JK-*IXnWUxT{p_V9~6sLL=oNkV>2WLp8^N!O16`QW&)Mv#Rj8$BmCc&w*-Q0q>Cu}slPImwOJEy_vFM!j53K*B*bO7i32oC)?r$?dbW|+$0(2T`7-85+0f~FbJq3E_WokDR&7lnf}WaY(s85WMyB{)M*v@<@+;FQta3vJg^r)SV~8BKpCQDU8@B4N5)sZ6xFfI)G(eQ1#UpPLk}koLYub~fPfW?=9977P&53t58Og30NU2&M;<*%Q_AlZdKTa;yWXIvnbxT_4na?Sc^@yI>ALdJWYFE<t`9sF$en?S^U-sP9`x+|Gd!Kz;wONtDJO01kvh@FZ&9bz`Xb+UbKD2Gszlaf=SEig%xZH&UqP4x!q)HdMn%swSao0oAa5{r;z>a@Lt-{Tl9ZsLG*+1nQI(%9;i94s}kTn(gmsDO7b*s6I=V*P%`zgkD0OmRQ_Lq59zLaj1LcC<fJR*PCepe;TN^y8ll{sLorHsko$bYgFSIsm5VYEeds7vXF7Zrjp*3aT6!#1*(2R{o{6ow;;7UZ^4We>idc?cS8+lSX3v|57joHTF{*@hpH-2-9s&^mC*YHiou3cb)ZQdq&gE+%`l_+o24_N3sR<rWIBU2)oty^Fs670QxEf_zhWubVWt|S*QbqX1Wa|Z`8%+rswPwQ@JxN24>66~-X9XC@RsVf<11vUPr%gb+CYu6&|eBQY-fKDpsEF`A)uPm4pbRaTQKz-Q<pFe+vT;!)DB@99-L{aj)RG~UHOqR)g)7WQl@^gp3gLw$gQbjifIH)r;{<Ysy0vsH&nf8XHwD9{{0eaNTBKuFi?A#nnJm>OT$X09x#mwQ*&0P(>z})7e5MuwpTd+_-Y~bxNQ8Wey}%YXz)-+v?lTy+6pV5<>WmmQXlE&Kg$`qOIVKU)N)+gBMA58Z>%V|_BxE4AXImc&=v??)+Kdse)jMP9f~ka{xCwjAhel3LW)p7JVNVgqtG8kXcC0Gleq%jJI;Vmk3eXOMgqHjBajH~6JZUZ0SNbod<N<3t4_NX&Q>2qs1t;HY1DXx)1AZ?^HCT_A=D^Bdm4n=4nt@QgaO37Aws`J#O(=!u>%m=0%1T9+5(|IN$j<TP^p=ZPy-#X1Cw{3$SQFa-VvG;AT)Dr6b?Y>iXB;RJN5dtKJ6$JBa8?_3skBWtbb30MAdhS5Ngs(gl1SD;yYanC*gJi9mE3g>z_blDu{58R6qP$7%QXDXg)#<48mbY5}kd2-G!mKgFWv=Hd+>Dn2I|xhR}e@96Kytcr}EMcArfV&d@!G6Zwxtzd{YNoG{Jgl0Js+@eyu^nmIM0m5f5X<)a2UO_#U_-8;e{Lg)>OaCT1h<)3ndzAy&63xr|ZC^Y+87!!uGHkV-NPB@ci9HCaqxw}sX4;)HUZ73;y?sV`KrsD*sqwXxxh6OPpJC)>V;zuW`Yb2u$eI#Kqu+QqU;Sm{Ti^Ca6y4sk8^ICUSxCU_XjT<+cNHW(`&ch%1Dr0i;vmZs$0Foi;$+-r*;t5E)`j|XKassL1z4+H8GGPm1UiP$OQce;pwT_@Fc-n&g8W?Twwd_xlSkbDjkW>pv4M?tz#;08;Lp)4UFC-PHQ42}G&ohy9raC64BP93Asgz^{jiwARc-Cj0-C~j!B{?M(XEAB0`XtFKnN|hK_xY~2=4WfG<oU!Tr|A6{lCh}jJ10pyRqx&E2+3)i-D!Pf0QJ2N<PA<RCiOUy29S)~2=oa_58NjlD3Uq>Ni~jSS+g6nQb-NNUlXX93MVExCB=Gjk^$VZA<4ZNXFM6n-9qAMd=ip0i47klxwlyg2}yJ2*)1Sx!8&O{^vq`@*M`Jui+Jp^yeG*&Zjsx)uZm8peKa7sn{xT20h4|FNN;VOd_9`;N$yf6S9Di0pjLD(5m!Z*)W;u_wtB~jGnXWcH`+ww?y{;|vz)_KmaRDR?AFRD!$+yJV~tA6m~FODK0HbzL>a=}C#ucBG3BcuoVhO>@nQJ%74!~X5_ZVz^h&?*w1KwEyu;6sq_#DZL5CwGbCYnB6qCAp5l*NpkhIPmC20_n1}I`(;xqK<Bx{i{V-A6g0OWqYhW(vQ(!DD@{*VmyG3odyO@VR(sr($JDcWh96QG=ilXM^<xLedK5acnSpv7+<%ukY7U8zOPKK&MOFrd21Z@$ZCT_>#?1`-zQ?%jv=5~WZ}ZsDwV<+m}(J_Y$I%G@h`b^g{TL>X%&1t|kQ$qA5D%eFm^q`&E1xlWRwGVox>u?a~71QI1lJ(#4u6OuNIgt>l@1_238Ce;Sg+%d=?0tp-;Y&s@qJ@HXm5~XgUR3|_=U67<MNT#z}frP^2lZ-Wz(_~~ML(&X)27=q2WCX{c@g((qjLA6#se>4#%|Kevokt~poVEZtKRieiDkP`LNe@Ag<g{h9)}sBG*+}S<k(`c$3<$`$xgH15Fe)V0B`Qf4o)o09v*v@$4NPnS(k37SFmp1C9`gP`su3XdJb4*N=(Vx7)-<5oeE=XMu#dLG4wF{{iMIDMt~w;GY;MB@wM%-z?(Ux}$qBTzx67jX=p=QGq@N}}Nt@-TU6M4kpnTIL=H$DuB0dsHMW<yml0jd$jvBMAGlvqaR#pY9YD3C|2S`uf8lSEl0IgN?ks@lJnM2zu*Kt|Z9+m@@5|tTgT|7`k4Xw4;TVGy|?i0(!OObqYF}zkKR)wVRE$oMsB9I#A<>+fd^|JH(ZO&ag)t@bnarPrgu0_9lIXX;MhX*5xM-)wEP|j00iqa-1^LlictR5q+yERIjq*F%sS5c=VZ9!54l4e*vI!e;toTTAjOzI>jAexBTEjc74&80}XtKCd0B(3Jp?vy0V!sH|sAQ=-=%QKLy9LSy5hf$iPWOZ+msz4zOL^<6jN+-K6S5SJT#eNf(L^)-C+%S1?JCx)-$J_v=M^U~{@Hs*0vIeRni&o=pQO>pb9o!L;yA?`}<a9QYwb+ICQT3p-Nfqz}YR`93O4=!TTupks?XFW9ls+imM^a}s{?{XkiFw}K3vNs@PFhy~>#HO!Nm30X=`fP!`XqfeCcT)X%ShUVqyY=10oDDZN!qKCY_wcUQAWqV=+sb}1*HaON&}AP3Yg2B0A(CY(ty%*y^vJED9V8Hem!{i?jdO}(ARV<Nmr2E`x^M<@;%PH<HjT%PBM6BrIr&kNe2!|YReFsO{j95q!~@p%1BmFPP4?x)q`jxj#7hSV2IKVM5#MaPU8k;P4_q}D;$**DCfseS`d2E0Hr+(%1Ur8A$g5lbq@x*mbxl!(n@0ct*2>LkK_A&dyW-LTRnSypsbosTU#V;eXCLFyS5CiB+hsTVFpkY9FltAyt}a**j-y+ZU2?QG|HK91SZ~L+ZTO~_rT<ZVCsw9pOwTP&&Vn;ahMjs)RlI<Zfg#60+`j2Y5mk+VjX}0U`k*b6lT1f7~md8rkRxOud)scz>wL{mtBz8JN3nq*jJP?j$~<@EMw6Q`6IB@PQ`wfehGdDkTS$suBMomVmV(8Wvy+3dELmJ%;60~89^j`N2w5$m&(3Q*Bh0pigFfc0yG<?z9330(G@S@f^>P5CcD+>DoTA3l>VkD=i0V2Pqv@ry6wR1Ye`ZAl9$REhO3cuwOz+qGao@|3zQxht?vmhcN&znLFpX-E^aC$O_k){0@$CBq(4Y<jmN?};=EmV*6EFtoKH;BYA+_KNs<<r|L>cP-`dSQI!Q|m%Gi%`EzpE0P3DB;K<e-eC@({DLP%;*xvsN(*YqR_{FehL$DDwPPh3c<tOLDYB0}S|&v&{|8mDD9#sJ!QLy{pOX+ef|->AYF7D`_ql(WpJK7fkg2vB;UEM3FsyL>VXEVt=E=`RuzN>K)*XK4`K7D4nGZD9@L9{Yc9g7WhATq((GB(gg&%oGM+jeg@b*S-cq!CKdQPh;PjqN-5z^AyL_UPGU#S_A7-j7VK$8LaaC)z>hG9h2(ofVQx{9Lq*cp&Q6@KgH;5l?%4NU+|j2F3Yb2aNUC5)+a{k?WD(`oIv{3F77)9lpDH>ZoOATxtA3d!*UMCS?<MfDN7BqT$eo&y4w%S+1N>n(h?~3Qk)rqTp6Og)IG&s0;Lg=3_i;0jyx!a3!nmf&Bj2IYX)YG?c66x+uLv_L#Zco36xU>rG6xocv)erp`7OFILbNm5nj91D_}snMjsy?Wo=Zxo+_0dk5WGrN}>0gsiBO@NDF36(v@*9;(~4!(-xC}x!0SaG?zdbQ<BE1K9U-ozV~X^mE;UanvG;U0ZF4PB%`D=MNV=`rndvrd+$IPfHCtKNbW0TMsjxk2uZiq4X^o_X{#Q#z~@zMm9Gy(lFlMr3S=xmx}=Kp+#t=YwCb;9pTI3AfVr)fNVv}8;qe3@y~Bs35gg57aLq2c(>;s<1*Rp*k)^J;C8;YU-5ga<L4#e)aCiG)59B>7$vnmNBncCQFdQ_2ysHQDo|L2kWB5iS{pCs8V2xDgyob)`g(MW}+H7{iLf6X)rOYL+IJged<0SpeFJw0eNllW3$_u-c72kwp>~cnG7=9cfsf8phAn8s*vT~Y?*4vw>tXn0+<RUlKFido^HRE8kdhCq#6(QDUWehN#WdsmI1}jvmu0sO%wm?-EP)}NhXFMIW%9Qd9Akm*Dr+t>RcEj5-Yjs<owbd>v#RZz?2xDfB3xV1MDC}=-mcMfwpmP^bx^Zhh;bC2egy)p;geAk!KOFX)8QGh8I8QI@R#BPplZDy}3DCI!Y5`D}C9z?%YkdZw({*^Ngr@>L&EQ7O=izBH)v{ZfJwl!~sVMw7JYx*v6BFcV3!V-%v@es|YKc=m{sL;M12l{RYJl%B1gg&nG~ztx2(t|%c>0Z}MtJIBJm<kUZJ)j7ah!(4848>#(F2Xb8SfIOiKYjqS@K`ISvJI}lGzS%+F>}uO>yeVb~I0u;`8(w&k3Z*V9$F6w)Yu$xBJcC{W3iDf#BMR;pvo)@d!=_aM}!~LvXsY;j}4E>x>L%sN&pjn<-A6;T+Sq)LjdwBMpjGiZk&a=i$^OP6u#mV5SX41^0+k)=O>AlVv<-sH&9koPdBI&i1{6+iiB)yMFB~JS)RfM-|54oIp8=0<F|iIiMMa(_Rawz7S3eaO$ON71UqsAx;I3?Gbbv_y9PK80X%F82XdLKJR*yW#l-=os_PIvr&bd@tmQPr(ri}(V*}c_8_ppEk7o+U4fJ5{O~+0!_z9GWH>!AS@MNZxl2Owu!2W{ljn_aYISj*-hkEf8fo$l42D!y>8e~HG|KEkN<zU1@VzI>Z;cUD$fp=x45}}+i{r8+-u+))C{C#l^bimt)itCcS~DhFUN+cHs~l4e!flX-uH>$!FEj^;+De;pm@bEnwoMY<Os$U}pQx>^p4NqtL}A12m8b?z+v7@=hZBt=qHeAbeI26HSV>1DiH_?TJ)Ec?Ge)ELT{+&As44nydtgMM3paRkDWd8CQFjZXKI>v0vXQsf<3XYdSi+y5Xt35_o9OglMDb8xsEyG$t3IMrMijQ?)*#)R5*=qRdt;*YSwDcNO^8lg4oCxwRM@=WNfghgO<70Z33N<_Sv8EPIx*4U;sK(uLDXa&<n4Kg0;}_4jM^Te7Wn1B6#818TN2fSiO#njqBWqC4_!%g2l7BLiJk(rSw~tk5a=`*Xm^K*6zHtXG#2O#=6u=X;DkVRI^}0CUPNtXXOM36^LDjYOHd>SI-dZjjc7kmH*42fMwIi62v47xZj9s^?__``JiRiKSTigtpF#E<D&XcVn0Hy8;XZlVC^*<#kWiaJP(&wr$Tcjgl3cL@l8{T4psE9^!(N`*hUBy$Jd$@$Uh}|tgKD>2J$+`|Zx+4hjd%{s{aS<a^m>}vRas>>YUuvrK@%efYO_MpzQ|m(Y+qfiY+u)S&TiuK)CEtM@iYrh2YR5u##;84JoN=Sr>8iLnd8k%&RY~hSC?wj=pdMZ(B3_E&G}U+stU!)nUR@vS8eqT|E9mq>AP=s;y}$j8fYz#p11pkU99cEA$n_|(`A6-Rp+qfcbZ-wSH^#9ps@l}&8`n<B!L>x9M}T$?^W;m@Ib3O(d7J?Bs%n=U(3r&pk^7lryZfMLv(;D!DMFiD^R=XFH@lQk$`F;P#^n52@?raWk3z^`@b1bbp@a<@Plj^&^+I(0Z@eiUGr)W4|LD`<Rdh6rF%=Du-MN5pwl^l)<$UbaT=39hlc+vPzQicj|%kSJWat<7d-XFd4~JsDL93eJR_3njoT8i^4u%1&coAIu1Rq+rjO@b$(+aSSX%Nln=audp^=M>Pt(oQAw0|K^SA{-Ql9e`;5;|asC&xKVOr88_0o{12j%CGr@l}X%td%MYG72#GrGB_z_-TJBo5-2<Y}(O6ZJN<7Uwy|xvOB>R(RTl=k6mn7we~bES_k`DTCMZ``LJZ)E^<`89<*J57y89K>uJom58T~2YAM$pda!yTZ}nweun!w|5jSVD*&Bl=>UzuAt5BqDR!U{Sl_QwLk|x6X8<~*K!XZWAy-^Z<#6ZGS%xDnyA}>q-wdc5SEsQn5yk+u3DCR@9Rghi+kU$`>6=O5Noj``Hl&&=M5lP&<arMWP1pN+VbVfZP(=Gc>GRuj+~t-TM?V3MmMstDv>8t$#{pDNyUSKjA0umpS)foIq2UNwhc+F@>Zd~{R=6SA*jMW>Bde7;MAo8Yv8vxa0~`i6(Y^p#Y39;Z$m-yalg(R_8{qR?l8uWh<UYyH_Xl>*VCn>{0_E0wH-d1p!qqzjYryF|&uUJfULC7koj|hq3044h24JBBv`fI6?e=+cutvceK{;5HwKBH=tZIP0)#XT=F0gO!0|9F*U=1{^IR@5%8kdk6n;OtmdK%c7dmdb$F$nAHJzk8}7FZ+b1{kuM){|gWBC4}uFR!*rHEgSZTju{xb(JwiKvmz8>NL(Hx<=Ip=n>GO3Jo|NsB{fm)E=X{k7r0V-en1)%qrSf0(o(UxlcLOeSFR!Mu1TbASgYKY8V_I9Wz!Zr{*J6_whLa9kVW0fOWmyeLKf={=HACvs1#c8WE}?^H|eKYX}WihTT5;KB=lPV|AL0jOv6?jUe$9fbY`Ya3iH^hdEhwP#xH%+Tr2+sFY@p)in3%vu1i8Xi8S^CAU$vfT|yOcl9@=YVgcJ)K*VNsP5(rkg5h$^+GiOs^el<_es@w{;d_GYEY^$+Oir5gsh<3pO~r+?!Z_L6{_p$Gytj**ba=#5xCo~tN3{}+9?RuRRcQV<~p;KD!jKUFow-wsvU|wd-<^{p=y)x3QpB53dpeSSu53PyAh0}YHm7K^~|7pjg)=|2D*EAwUS$FI;odBQ$-u$zJ2c*{hMPnHH<d;%eG-p6Z!*<&^y*W?FKTfxzHVCO1EM!Q~A4`;zmsENTzByQ>u*H0iyw!YIY-&%(rG*aYK)0vV)QC$`Xwrwd35-Z;jLtQ-4sC`;_V4<1K(Vz1y;N1DKjS9j0TD?#Ffwkgkr23Lw=_r1j416YAQp7u`;dR0E{b$&o632&pX^AwZ-S$iXLIH+>4EI#!42)Y%GQMr{XH;hrIx>T}Qh<47%ubV_dJPo#}f<g!$L4QWzH=i5nhu7cD|u^(wHkZKaC8HlvU5l4?)ODpF6(P_#4#3`7ENF6{r-`;n+6X_%wqt044s$aVSc{sDF^CAFhZ)-f=2{c|7XxXvdG=S>OLD}8bd3q$!I1s320Nrc6Ay7XMsJ~C3!A*8l)Ak&wS%8`X=#5Mr^gvgKEr#zBo^h6T>wv+Jv}=3L(<WZ?^A?PnhuoPuc=`+U9Ug=8JwBIqZHN7N3<xsAHrlIO)>(1-+4kWKpliDUqi`22JEV=aT?CIe!Fdt+Qp$6lwd=FQ382e_NjluG;u@FO2JaH5`Bpj5k)0(R%5ySWi7i}g#%k?2LGz5~;;AY;{p9aHwQl>m<QlrhI|JdM1@##->q99ToT7^c)E4ML6jNh)JGfo@Xw8e3c`H>(`p`!*Pp88+8a9zAn87{+X0S7|kfg4WoDG*G-BH|vBs#Q`_sj9d4wEE|_NNk(tZWw6`DqME(;#Vv2@!5fa&O9BjLFbPG7=;WLQ;>@AKc}b^h$dvNxT=kSrX+wOGKt5&51~=bWF~ZfFxzlZ9ufl0R3+mPSV{aNt<YlE<;icPKe)@r1RA=IrosXBuNc|<YyyU8<XD7`Y1`e*vDC5QV~Hlsv0aPxEe`yDUx)Lbx6__B<<-*zFxU~AIUu9t%0ZUTG^wvT+K-Nz->v|xiTi5H~l0hgk(TTn%kyl20EPT=`ti;h2&ll6%vx>@kz$9BujUF1thEvkn{;jds>n%L?tC@Q6Kn}<X-XYhLgOl!?wkJrKS*~>5HoEB=thl7bKyhj9S*!M<-bulVJ{yPZDpLt`?GEyK$!^&9-;PC&@~)bVyQzy{07Tmfhz@B<&SQx+sYB=54)a&?bGYX7(sazwAEu7*!M2F;`AOQAPHcGziIk$5{(ZaFStb`u*r6E49nh>y|U|N$RYn{0syY1~i#ZN!smHc?y!1SkSEed|hMr!KQdYmSe3rJ5STB!vndx-x#8)3?_kD6AddAiE3MX-)}w9Ki_U_sxGXaE&|V}CdX@gxCT5;T3cX35(+86khH70Emn0Lt7WuDhhFX$xHZH6OLky^{f)8CHLBkCQN>$&+rq~kw)9@RFpVp*A5PWE25W6)O;X#(u)<=y{UB6gHCqSu0a*1-vCh|_YFJdqnF|_q7OL%@=^9XlhWX>E>iHh2#^iv?I|WdU(=n<BP}NC?`T<nqO{u#2V4cTch4rDTidCHpD<0{XRgA8Os%25tS<mmV^#C5_g{#B0sHzK7H3U@!sOoD_^>;{hnw9naR3p%EU{uvsqNf2>HIk~iDb<R|=xwkH7FN1S+ySFT8mm1E*6A`-U4^O#R5d8fQ^4lnNtJ4`Zi^P{EvjZ5RdrLUmBi6(qL)(DO{)58RHvIlt%#Cd$Eu`lCf#n`f=Xwf2$6ECdKlGkheLH%leIli>;484hy~_QLjqOZAyhL2>dd#pcfgQP7me5FMba>VxU~X}?59oMsh02GBUCkHQ4MaEwQ~%>StBG+p%s(|s*v4i;%rbW3Z~bgYQ&xKpdCa`6=s!Js(Tb*b>kUF)!pGxovreM`L7F8h&_ZdC$5@1)Bsvytx(4;s>9E!rn9)5z<QO8y&3I}{r0Dod^0|6J#M2jn;F)r-F?>n_8==}!>@x%vqfH>?cEMD_YVC1+u@u>(ln|@Q%^xg(=lAzVFPxXHD<pJ&3GZ2KBehHCr!$)9cDl+$kN%Ht(kTt&0RUCZ8kQ|Jci~3N_#EHCPA9!W;E5%b#ps6YMs)YdT08CW{_c_v<5y!dw2B{(A=wpa+>oz@oCx$O&E%YG%cVxosy<HNORp)%5;$_N-ALy@Y<mM)HL0s$I=W1O`SAPKLJfMS7<t=Y#+_Jps9g}@I`5=dmWoDi3#`7wBV+V(NsyJ^gE<EiHunXu{7YWQ+lxHEEQm>2eO>+6s1?DA0@0rpRR^-x+zNI>Z5Y*M>!QJb%Js)2~-17#`_$V-fMFN<(`&|0Hp#b&4O|shB90WrK3^K3CS?=E2wFb0nG3BAy|@BcS+KB`Xktkq*Kz1k4KZbYr-~WBsJ&&FovYRlghxH<TOby<bFG*rzAB<kMAU5uh>(N3^>WCT<jwmfyj6#x%MocKr4m)P^s?HN2Zr#y5mG`LLbQhns{m8%@H%_vX$g~7LpZFVKiaxA?X&926WBVAmkgj3lJo!&)~?TMw9d)@d`<X%yksbZgU2b741N@F&rVO3wO}~{%g0rd!O$QMA8UcqEeFA$ZXreDKB9ewXe=is7AZ@toDr|y2_^O?F^38eo!~^T1LABO(TAL7D=#dx-Dc|*^j-0!7@LfG(8ZBZlBap?~Yvlc988z$dwJod#{c_rV7=|{I^d^s@)dTta$-k0kRqi*<J^-X+YMXz}jsms+u#v+p*$<LAET&u>yGlkayF7Kw99>Ct)02ALEGjIIl5Ydn2iWF=dV)Z_8NSjxlbJKY_{?vsAV~#&gDaS{N&$fcPAYow8FOW4zvdZO~gPYi5w&v|AA@%{V+1<4`-kg=qPVeK%uWVH`<=_{U;wardS<c;$N-mlp9eV5|%G2FO@19RML?JOJbGl<_1(?8U>_6o_>bu}TmdfS4+evk!&15|VH;3>W%CZPZ<cSS41<G-CDmh(l$=3$s)Gh_QnC67il*wFTmdM64ePamAl-jwT8&d35!>EfD)A;(26sQoJeRT83s;uye3ym(p9Zl2!r48X$%X#WWtVzsuCkWQ>*~#w)<51aa<Ju%0M%Qdd71vAaj7=GRdSy&)xta}`0XBHl}vSHyOMI}a?l*SAfZRcs7qt70GFykUC)HZUn+=<f^(@Adfc41_CT<JU8r?;{+t^7{Y+J}NQcu%IlrMtF$y`nKlTwLD!^a}Qxxv~~A@q(Xv06yb26;&x$Ser+KRy6ZTRb|yFA>zFknfc0x`S*%OM_6}9rBUTBml+xnUM6LHb%r5P<`Wi@ZRzX8f*gqCwT-Hz}3~F7jQm{V{E{v}BF*kThzOr7<Q&107t$$;RHq`cYm_)Pe9ziKBpXJjX$i;`GRNoEmXWqlr59DfUH`n0jBV1vk(q>u)TcqF9pKvR#dL&nK8LlvKW(uGE++^ErdGukW{I}*>TTMNTw2b1aD_s4SI)5L{CmyfKE_IBnM!8Of5@gkQ58*mG_A2CBQ^Cu)8n6$Q33SEgYKCcMhli@haD6>rY8ys^H3itY0#=^`Y;A$H-W}m;woG|UxI$mE{o3zAL{{HtSW3FURtKzw0qk*LEdc9)MCoi`eT}Q1qLizxaMcA@U2xqkIMsuhL*rc40IrtJRV`c<kbzx@tG-9B^E5{RRt=7yIo1Hm;$W(KTH;T8s&L-2S&xs^R@Z?^`6FOU32hEG0<iXx!D`7mpp6YjxbAj9F5&6{*RV+vZL$v7hq8%(tIig1bzaN3#tK)Pa19&R0Js|9a;%0#2u6pU=PK4ogjI)0hIOi7H3e3^V2uE)24>U#k*rv7tg(jG&O%$`2^5e)tQusrAyyA6<x{NT@v*7_SUrN(CRPG#cwoi)o@1IoJ%a{*^G~ebu?7UI0lorii*T=NtKN=a7Qq_NigliYn)y^sMl~Q*J)pX`ma*VFtIj3fp*542QLXegc{>Rx!Dxl8i}RiwC07f$I`Ey<bpD~Z$}X@HtUgHrLab8-s|8p+Py?JEt8pN+b&bS+9NhL@*Dpqa7X9iRg@xTo?>)7DbB?;o(M%voVg|Vucu-1Tx*6PzsT;{up&oUwL=*RTbJ(K5B+?1oqyJ{JU0sA|97UA!;|~c@n;Ag3ApwxPC7RS>N{CK`Cx6-*+k(#IYyI(wh=zWmX%+lj@#PPI=q`>}vw5rI^phw})DT1`gs3_*(a7KH)6hIlR23$7YkiMPe7sLY)aMb;c!((8AbTaMQKJ47ME6{hF9xaSBZZ;38qx^lBPCLE8l<&BY9{0Qh~kC-D^Z;_##YO6ddEc7?TDI!Xx?bJPIPswJ}*)2To=)`6)T6R2DAP=L@hB$=RTx(dB0vtO?B3{SuL@-^AFN!phJ*hSM%#iH9sV3D@5ai5tRXr{B;x-+i9|P9|D~~vmUkN;m-s#i{^#IC(N)5M0HU{4lDIz0u<W)p9ZL@Nt@!VLl03?EzIAKqYe<&3DLW}*Vll0$q0Sr8OMy!0J@s3HMlzK-K<DYwcGMkH|4p`?7Zk+B^9?jPYZa4GxJo=_H0RMyZgPwUL`dTW}EL8Y)RoRW6d(2x|U&|l5%guF879=?qNZ_N-Ci2w#PdF)ZZmgH)Md$R=OeiqRBlhpI3mbTl|4FNV%(Fb+~uQQ!8i@e5X0}sY|@+B}HAY9Ds&<zED2>;pzDry`Tb{p3QQ;(Bq%-{=W&mK39L7o~_ZFK@Tk+JqtutKC?DA!2iQ;3ges5)8pvXhMv~Ou;G~kUO?f&zB=YESAQ8iQ`=1=uu74@izK`V;Ms?VXX`@`q`ziHJH}AZd(XZ?6#;CHbq0F+67Wm{&wf03M%ylUxnKAU;28i<p8#I<3Nf3$MQ_S#bms+C0KSLg%Jgr%=&9<^Gm%NpCU>j77^F^5-z_~q<hG@a<-^lORoETFv*T_Vb$HH*;DrL70?iQCQY8rQMuBH@d3XvICraVL7Vr^)r|uTsBs(ToPkJV3(W19nkIfmqaBuYbd@_XdHt^@I1*u{P&w+F@T=dkiZl`y7Skc-|vnVzI;lYA;53Deth46#HbD~Ah%~2H8i%D&J4sVSL?7nyAu}*p@JW~rxX|HAU0<iprZec4upSdyGThY^9Cq2>7dp)c0_gj~_`8r^^xOT+wnMJ6*)eWr=o)W<e&Ue5|!^zMc5Efruw!9@AIIN6;XQMaWnGBcM)w&A2O9e#r%}1V_eRxoKZ(6eP&N5AU-~RLe0L}4c_y")).decode("utf-8"))
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

