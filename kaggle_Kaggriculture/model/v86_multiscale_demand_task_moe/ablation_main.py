"""Standalone multi-timescale demand/task Hierarchical MoE for Kaggriculture."""

import base64
import copy
import json
import math
import zlib


__version__ = "v86-multiscale-demand-task-moe-rc1"
_MODE = "ablation"
_HIERARCHY = _MODE == "full"
_PLANS = json.loads(zlib.decompress(base64.b85decode("c-rl~U5{kfu^jqe_}mXudskKW+&4-rO9N3Hfg)Y-J!l95&M|CU9~(Hf9}MIC_dA^KuCA(#jEKy&syQU}q*k$~dhhj_85tSzf4}<YfBDaU|KI=Ze|`1;{L}ya>OcSe-~RPq{_WF`U;X9lzy9^B$Gflo%isU|KmX59AAI`pU;qAZ|KGp-^n3sG)$e}%Pk;N%_aDFc@%KM`b@$crkB6^6{qOei?w`K;<A?7LUtRq0)9?QEaQNoaFaG)P?Z@xFy1T#n`1#-OUOxW%yAOZ<`rA+c;je!@9RBjt7eD^{-NnOw`2C-L{LA?-ygukZeRVwi^@q=Y`MZzb|M17J9?u^=`=ZxZFuy1rgR8&ryB|M%`_11zjph$OejbmruYdkl??J!)`uB&^3txQAr~mZb52wNPzV1K#H1L=2`t=Wo??3<RtM4P<^82szS9<<F@~>Zhckorn0C(Pr4D@L^=y!|b`|<=&>*VvdeEz!9@WvN<{<_*Q|MlaK_AHU%jkERq#m(Vuyc}4^{v^fmjgzF`=w&eBo9KW3{JeN})CvKAyE7@j*e!JUS`5(jEq4AwPt)JL9E_`Ahi|#fqj=HFua5UAx>&RCzJ7%bz2B_!7Mx0_Nxl4meaXjfzdii^hrj)Y!}mXY`1Zs9`*})6pA4LIjYo^?E<D4RGfurnBRB8s-s+r%EUc&;ir{2^+Q?@=$i1(|E`DX}u#aCO50-f5gD(M3Kl)&D$iSH!zT}(lKmLV&$<trqU-I<B<w^I~!?!=h{AVxx({Y84xm6u=YZjEgY&`V$;UT_U|EZ_f=UeCX55~V!OF*)a$REP>Y6$=O!}nhwe|Px)`~L*43-EF;Gj{eU$=Er6fWNM@PW&hKzr?@jv)kAYOG`<gcY7D|U2-Xv?lyIOgHu1=b?%k}*H!P{^RA~(;?SCl&LDQO>M23c%K>z@z0c33tB+e_*b5cJD86P>6>Negb+2F4N$*~dr8*+OZu!cfIrn@6p6EnW^(alxUM~VE#S~sh1JAe0tvlxq8;HQRFX2OYjrH-%yow9qj&)7Teekw9cHzP7B)f2FnRjvHf<edstdY{Uk)3C=fX29rul{v2Y&lCXZhQX@ud&zbH(bQEdk%e(eoKa~zWyXnB^nMq-!{hAkZYGcOnLy{xi<{Cs^J70??Ucae?ZJT_W5Qhzy?#UrsP6=n~Qh-LZgIR-Pfm@@9#ezt*iR<m!JPZDZk-&Hu$gev+Rl3Z{@;d`C;Y8WS7#U3%pXwd#ka!E|q;+#b1B_9|x;ipQ~j*E#r%~K7DZtwVeu0a!jB9Y_G_w2KV{TogMtG1pDj?%n;SmP2a;$z=NI7@asdu>FLk_Iy1t8w|Tqf`m3B00u6d=dxhp2o$^$SS<tzlzlXl#X%iUW(DOfno1pML*Z0*fy@Wxa@wrU>{Q3EPNABx->b;I2<acJO+Al+x!1`VDBKN}q`q3>?{pKr`V1VvRF>=qXW@i3dbYOlGt~6)o{Nx3vaQbOymTIMfc<raZFbmZ<1uWsvH}7>dr>C>~^h1(n$6rK)Pzrla-*k%k5adxAR1=Mf?^3wJz~8w3*Yc+Zy}^3=({dTFW~4(CVH5a5*Ee;kx*x-z6R`676yPK0c_{qSgL&X5U<xYCk!>GUx$_t`@M+#Z79zIdBft?!mc;DWk6fVZ1-jhu&4=Jc8=UIYnR>*}_`nN}eczHyayPAnRSm6VnDZL3aHNArQ{xfbYd8_(C-hOHYJr2ZV;ZkDBex_<;i=gWaVEqecdQWQT=H;Lynt-Sj~_oBPW$X#t^q7@;XHj?gx?gU;rU_0eU(=SIlVMJiS{PC4vIMl0zW;%>r<W9{^`FZu%#6zT+GsD$)KM|d7)J-gH3xirJE&twDaee&xe7-@Dq8E1yA6%256klL=xm$5!Ts5^~!D_sLTtpBEUE;68JEA;PH6`cj~d?m`SG3r_Ak}uZr;w-DYIE<S`hxbe3QAzMu3Akw26lx<)_IQ-y^7p&Im1__#~Yh)2~d%4zoS*1qZ%(kb!{{`3{$z7(`SpLA~$vM1;4^4RMa28qXcaB&ESZ}|NVk1%d|5JtqO80;K+{pY7669tFYN5F79B04$gIrH>*opT0+JLnaY9Vy#^7#A)JY!cd6ObCj7MDd)73kIR4Z?lM!*OoJDt*F;f7XKCWK)Q$2SW`*TmFINzX=O_coDGs+*lFQIISr|X7i!Mr;A1Iy0iLG!9?yzF=T<;@>K8Fv(TD2-0P9eDebD~-7{4D>SP)?{oZ)j%Nf-hp&)Pc^X^o<N2(w~{JPg4?M_E+TdUfZK5h)=yrHx!pgot?@?j;kaU~#alIm#y2d@q28NjXtzRI@he#AvzHJ9#fd@uk8l+4d<UMBm`v#Ipd7PLl4O7nJX8mVw(b6Ynh${lt21D{?m>K6FW&zbEl}vRi3f4K9<8bW+%=g}_Sz<CRq26POq%U-Y{IK=C9-6Rnqy%kMO+=O`)2v|24Q;Lq7JnEYl^f*BD|%Dak0lnmKCoh=YiPLPSQShmsV74j?;{nG<MMyhdTPuS}*m}v-ofItX*vBw`O{b6vSI5=>p!x<2dKr}`fPZlhE-2j5t*lP}y1N#-~FE6wtOD7h|t|>(|9ut*x>y*MU?`KTBEH1MM24B;T<^a-{Y0n+$vg494g_i~76a)dA?S9P{=YP_tS+(|@e1nJSr1HI+t=77|wi%`ae-VCYrv$rHLWY8*F<CjCYH5~$swetyf`mk52JpjH-7ju95EO#Ih2{&L!_}w7oQBK)CnJ?s!os;DeOX0@w~ijs^q$A42-LR;JtTtkqxaK4`R2nPV1QX$hxm`6VbB-zIP0Bi{un6JMliap%^G`|;!zYS)gY_%8^o*w0(Uro{Gx&>aE6{u|CgyoWia9dsHOu}69MOHr@@XP<%E`03CW#53JygYsdjoID8Ch+h7Pr;h1uArp-*noO6N9BHlxuSZ88pl<%t;Plq^)LbWSU}A|^t>*nYUkFN}+rCKrH>xDG#5shNZ~aLaUPlU(2a<7UzSwm^$v$&r^#^@T+Jrrp6Z3eKl=bwal%<OvWUjp*hDzn|v8YQtEu`^5IV;ra7Y>e6W$tBSs6PPy<Jo6ITgfCd}QXmC11?&fK9QYe^qt;(pD7xAu0&s~g}ggLaPaF+y?Gh0_;Kn|8Bd|U<Jwp8H=maHNJ)VJvKxIm!DHste360dO-WQ14??4Q%q6A{#;ODcw{;4wXRtKAU9>V$zbV6$W@vU8-n44?xUFV}cF(lp<yxrz;G14v-x(U`t2tOMV#<N$nLMtkEn0ofHC!PnV}5121<(VY^O`%^>4UF${E!WY8{-k<zH!JYw`?0CGJBwjWdl>$*bQB<lIGngp3CE3qpfQ<#Te=M{u(%U3xd$BS<!VHV8DE8^Xuk^Ue(Q*c7jC&VlajjGMBA_1{!PCRBqY3>(R*%h(9KB8Jmn>@>F~Q>k`?1IArgvxD!4Q=O#Zg<`HUp{NKX#RpxFp8a#+DKhy-Vy;OCi1tqT!OWkG4-(Dif;LZis-mUe!w?mhY%SM3_;dxnCL<vwf(8F}swriY_YxSe(8i9M3Iu#;fapnzipg{_y;7i8UxT9ToS<%dfs0#(5aLLytgmhO2>hX#|=1Pw!F{xDZ`ac6>%grQm`{AfwO%<8=TNS;)JxdY?@Ox!<-iCR+DINqXnK!Q3#AB!4R#lu~UybQkj0BRK%J3=O!1!O2l+0`XHyI@=Y+eP<6<JKjQ=@jQ!q??e;Rvw!UDq;-5J@f5E-1!miS*gflGTk2X6PF@EW;h^NAJI@*8m!%EnrPz?MbSZ{`M*QU=pMwmw@8Yi&LdQjIBCfm%o&kIWmlc=y^lzbl#u}LYXOE0tlDGY`gcS@=5P~*0*is7$3w;9YHTmhnj}0&geix8Y$Kp{Qi6+iBPU<O;R6;6RC@#w76>3={Jcv|dGK$h7IQIMd3WQE!tw>>DY*eU7Rgf9=9=ybHLw!c!$-s;N7Exl2+M^hgBqf6A;Tc}9L46Hp&Z=!e0tPAT!-_l(S!`03E^dPTW5=>GmQg9)$muz0sKaHiz?6k01K3b%s?J7Ba2aHJc~_7l3@e7c-fgvgJ6z6fknlNC0`9c&AiD!R2j>h+?YN@ZwaQ+jC|jF9wF6`UowP=i3g-${m2tf$C8%2(g8`-jV5X-Ow0WX}rf}<iDbs#SVF4>ty8^;G=--!$=kgY%j0FdgD*-cXA5xMY&Jagz&0d2sw4Yec3){(bTIj?V@4THQ)*o#mQ@lOp;dQkd-}Nz`i=Gx0UWmQ~lwH`CR0GsKp8R`RbgM}!9yXkffu}vo51hKq!#F#@yNy961*V>@()g@I7mFpati?z{|62LMtt}WEhYsi^nw@*CbVKmMX13a$h_Y|CIQNf*N(W2JxCED*7171HfAj@scrQvrD8Z3WmPKmn)4_-y%(3NoNVPsZ!G|JO>$<bzp=Je>5_Pw_CCAG2PcLojO_0Jm-Zkfhgg<}y_D_IM7<JL(WX24d%w@@C_~oGjKVrA7&)?Qips3HK1s_z!tnC~!PEVYb_=KeAEv%?{uFyXta|t3Ob9hRWbD%}74XKN%%pU@EWR-+YrDlMn(;m<|uwmF7F=_$Vy+egDOH<;8lpD^=7<cWtJ)wq|C0Q#2h&W}<#pBDkND4#2CiNY%ZYP&`WL7%ggwMjC)U5fI`c-evX`x&%x|GOZ3=&qnzaM`qPw{5bP}p9oqnQ3m-i)(LW>)hhICsC9%nzX`wpIBiPv7EpFiJ9e9tG=-y67^9t2lPCjO^E|-w$vf0>D@s;-d%cQgGRMd<n)VfiEH@+Ugr5!l@((0ZAel)D$o2DsFPg1H?DT<#(<=8G~X>5>jcf$+O$yJ(l`qg?hy2LIRA)xGJ(>e3eY6W(V3Q<!Tr~4kXQS|8~g1Bz@DZR_Ry0OhWNK0ypTtES~tkI~4l_6ka+M4eOS#pd14y(nP98jp^XE>NwGBTk{N|1)iXelXS{S*{9b*L=(WyD^;2MnY$;)lRdYcNKlZ0Bnup3@QWvY8P(gy9At1>0lI;?+M6^PqZke?Oq+cRqy#9;CusMZNdu`h9r#%=Z|V^q5qPOz*0Kp-s2*hy$pD(OXHF9Zc+KaoxQ5+lm9xlgx*9}p1!W^&5E#14^Hy1i1W;^ZbS+v;Id!s1flHQF78c#<oL85nHm3CpIKLpBP9W**jKG?N<eFe)DF8U+TkBk#_k3Z-<MI~TSJZmOvmr&%mE<|$?X#_@<6GDygG9^{4b7Cdl?%|vd06KKtt$%hBVOh{xJF|NpL1BF@%Z{y91B9ngUOfjd;Ru~J|Sb_(TN6+JHR#rd=%^PIrKw|+~@^N)}12Ocn2ck%$|OTg2XY|j!H$Kn+yC_HaWm_QHYCNN=3hZ{vzwL39-of_~rEa;Mv;F6hs!yKMAhnL0N-v)z!4PFx8rJ7sE#0j0-GNE-u~W4y-57c@wKLpO=+fb1aBF9`7Au;Im5o9QA60wU(+kt+U#RV&6tJPE3ZvZ|LI3p8HukGNeqSbA4L}+p<goFW_U-HDDu4N!U^?sySzu7xh0N%}_2U$aBnYfCAgiNDI`tX4W<AL2?=THkWf}EvOW*276_rp^gH@=uE{VKp~q7ZAyWQR4?`OYb>Q0t3b57DBh#1EG9z{H=scJB=TJ+`Qtw^^?j!;=Dj`&Sc9d!ktDu+&`l<B^~6u|_vu~10KQ>jOs~u6@^C04*(I7@w6ms-o_r;-9bwrrQ_>zttHrva1|wW=3V`G?%6VE+`ANOIH!`Sr#}vKN*f3z=HiL4_Zke;!PCr3`T{evAXbIa==>cV?Ma-g&sc;4)?~V*wdP(WbYDtci7bizrW$bZ3v#a)HqK92pz_RD(9(c9OW3xDC3ai@fbXSzZtd01I)GKs~c2y=<s7Ct9>njhozoCK*q_jkIj)Jc!UXb4NalRr&oirKp7zKbDoeS^RtmgyKrd30FtBLv%Tj#ip?}D2ZJFG8`zjqzl8Cb+!+L?i2-dF>u%CxbNlXwiBzu(U2u+Fd4GAS*x8DOMIYg_!S@g?(a4)=`F?8`xYy(p5tO@onUNBHm;Jw2*IlZdpV%Ft7$^+|pF>MhWNY_)>{WL>^oBP};w9*%|p7ziDCiNRF}HcOlMj_@$;hv_n+MvR$Hp1~Rm*3F3wIZqJcL4f*~C=BNVDBfG?oOkV|Z&oni0^_7G(S(n;`|;}%Jyn*CnU)#e!dlIJwl@xz(l(=V>~ai}v`yo8gkA&CG49YIEMp^7R4aJRxkb?uI~4di&aJbxibD|}<$ka<a84DfsNrs0*L}}<pAS|L1LH}1!#6}dB~y6fRmU_BE1~B(uCZXfaSA8kLd-$Ka~UQ}cm_2p8E{PvZ)7yMR#nWlOU1h$VG{9qse&_O(8%%MEN-J(cdT=K<h3Z7{z`c^e(}mmL|CgTJzdpUiYK?*;rO(cc3Ebz3^T_V6jiirvkcna)P~KbnjGdLH!YDTi`8Fy52x{VH?E!InnKaWQwtW1u@8y!!K;l5>BtC`<4$#mp(PHLN`Bc=FhVZ;ri&hr4VD?MLp3@Dj*<$T!QyQL>Ph9XTC*#_+6?>q+bYvb&2Pqk%cituYlrweGGGKluc#ChPjs?uqo`h@!cZe8D&>WD75>!kRcW0BJb$(*pn_hcYux*yniV_-Sm4OwD1X#bVo9;r*x1TU+|Sc%E8tn`M3Rk29zGQHV_bGf?k=2(9aqG83Nlmdt(bHU%d*p3C8PUP-jbGOP~>uYcJPL#4MFWK6Jj*TIWlG$t>uA-_joP_jkQkOSY+!xdtRC<`t?0SX)6j!BO<!Cilb4k3*uyCsg2QkFZR&(eirv;wcuJJn8hmxjhaN9!zkx&J<s{QboE_wtG_qqqWXE6dGe+4yG+b1hqZG7dlMa6aHx>LmTHW^d_CwB-h|93XQKuYx{^*j+_+@i?3!R1Iv`;ijH%FFQ%3W)mY+?W7gf^&oon7r!VCvkTWT<Z=x4A5ytRpyRt}5LUFnX)IlY#p_F6K{8EK<_N89qqWY8%&9D`-zOKYP?q5sj-;ir`i3;;aT&RDqMnRtx3a0;DK0SS0$r_Yg0gd3Cq2*dTR&YC(zw&QGIG@5<L&z1LQcJ%WU$s%Fb(s^QQ-_gcz**hbiL+rVuDvJ;?V?J`nLlqC$I=zyP@pEY{(N4*iy#VGYV_NC-g&$O;**6|nP{XL=)~K{-9A`Afy8^r_c~QHrGez(_Q?fIvHATLb%_TQ4%!It>iF@5?kusaYB~Nj3C}s@Af&?Xb&$UgrB>L*wW5?+XD6xD2@$UJPmfbyXCSkg3#zAL?YDShq_qUokAr48u+r6DuM;uLUBya?H<S?fAmUk;M(D9vKVvKwkVU%;YCU!Sk4w<Gtnu;A>PK4`d;yuM#v&rW8>*n!S##ze+%p{wwtDv?{{V$7z@I))w=hd?TaswIG-bMR7k7(xoW=pIsUMZsMcbIj*(4K{Y?pjX=6of4?f>x4N*{hMC9Dwz{o%#a|uiz<|^$1>jY2%kRPvad;<Q(yie3*Qk&2J|VeW@jTizcxStoSqjT5pM}-pR4{Ics<67A0>9>fT^OKBJ6{d-iHAkw2p>>~ZdPyGfio!7s%_#rQ--W#0i5M`(0>YfA)_Or3G|^=Ng_69SaTl(r<PKotbm*24aeNeVD1%LVVVm#ep^rw{KF>;zHHwQa@!`e-PAb)y1w2v<;0@#4px_?u6*^Lj~X(F;D~C4lQJ{Y{BaC!-9z_g@Ip4|b1Ng04-EYiEhd5Va|G|BHrU0u1h^((gPAdNUf(<{@T(N;chX)*k69(OwPGZlR!}`@TTmqlE!P_0+A6<c@2xT+`QbnRx0l%9DQvF{s#1cZ#ptT!4`Fz%)S~9y3HyvAS6`iM@~|2hZ&<80}kY?7K27cN2tgk?rXY{<j*8%L~@+yPHCO>~g8~i}z&Na2O82JkD*??=uiOT68=kw_w^0;GeYAJ>sR6G@w<$2c=e>|A~sn=eF<hi2((anmh7P7O>KkSd&dL85BnYJ#J>v1>$U4Qa0xZn>%>jZ~_Z=_QukqCaI*h-p`kVJvyX&2SU2OohacQBugkGGT}NsJQNxle^g!R;s}$SWe(BJ7JT>76wcaV2pmsn#ML5J7~UxF9>*`ln8)yuSF(0#@vgRIQsg1NG_X(fYhAK{Ms=QPyLFx9w_uWATxwK?;{}+wEI%jafNG}{Q0;w5PBC)+Ae7C!u_<@fb9xR8IHwh4Noj!VL$|F59o$I;n&t%>@9*%K)`x<#k}AE}^$C_8lr-w5bduOyGhQ0^nzGbtjS1>Q+wXvZu`EC`O;mlg39<|EZrf}71KN^wbi}g(dYC0qE)@*`e(S#8BDlReOW+{^XmyZDaN+Kg>*$$Mc?kd=HSTTJT%1~11mS(iIdlYO`7{cm{AW{Me#1Tstmd5JEA}9GDs}sgM?%%o)GBfD4&%*R+9oK?FmOLt#SBU|s4*U-i-^K2IMArOUay<midKnETYF-P4g)&dTAeyCxH7eh6D8a`d6fx{EuB4Y#H}1nvS-X|OUiJ*JOo$U-)xHz8fg^1b(GTHk3{A?b9B`=8MM&~&%riY-uF4GFdrQ8zv-*p$^N4l+sP_NWzX>&C}qHbO8+zCr`{B}GrB>NcSj}~ZpI7(j#tf^uxw*@HUWIh^u;p@U+&%hhj<LbrhDnPdN7PPq`|KTeP2{}7h@r0B22G?H7t3{1iC$&B|{*+<2ADw<3QC_;7yRBfVrj{g-U5g%rADiNgRcyrU`b((Q#4f3Z)&q_UMJ9g{=_}GhHtDcZY93ewVK+qx%R|Uxe-))5WBLD&Z_MVg9FgTzy@(Wj8Bz1uzGT`}nS@oe#X9a$ksUX&mIDHsqYFs=95Q+u(dNZ2Qflb2CqTpq|9<9N$+#7QgOB_NouKNqjY!0Sw6n<u0audAw$bgKcr;;4xLvbZ<Kn6bwj~M2;z{(Q59onDL4cgA+qJu@&7rY`L8FJUCq9*tj;8wS|%$5e=K;-=>b^W(-e`MYYX_+Vno(<eP#~@1|KG7R_@teBBsD*-UK$(YCOo#y)xeZ}9u-8a9zH8YAGMtwyQS=%L0F^&3<fb)rtyrKni;D$`h^E=$o8Rci7>6@udmKNVVR^$xY=>A-NnnuPEaq{QPwYiUWG4w1XvMi2KIm+<!0THjAt>k%CEpV8vFHdneKsA^qHIc~|$Cb{T2fs^(Y)+{D0;l{$EpCP#x*_@*0BTzA`wLN_SpP32nFQ3E7k`hK=`n=r6>6su{5P<;Rv&@sl>G`BhXpD=QFb>llBNBeCj5z=S?8co2;p_Uo-Bwl%hNwh;OW&4&V$w8D#2d^!#{~bJqnL-3{sGanjvPr3Y&RURm1D^<7Hmid0joFj<TG=)JYRbE`F?v>q2UqNC9ljrE?pQ|@2Ni9`N-TG)tc<{bf`F86D?)N)r2uf@DIKKJ8>Vt(?61<_h2ldq<|II2(VhAqL6g{qd7}N?#-9n?2FX@E!}JhQRg3mk8ZE_)<mbImSM+q>)uB3Xz7l5D%<7n8O`FyLj@D`(3}~@$WjWDRj1pYy~X(0)2<WpdEvjrFrd&FyL$scNZrjxB4y7zIenWRC$7**I?}`36m6vNw<65a{;q_If|M)##m=2i>heoN_T}5PCeIkVq;*dh(VEQ`L{n2AyiG6RkVMDhp=7dMkw}=MxR{@h%BYC)uzISB;0mRFA5_7rAws&X2&oeMGTEhxSfADPp=pp{nGbjuD?@0mm&%sCk^Q@OX<Q`=v|!E&43(Xtng|;Febo+-h7zz#=?voDn)j2%6dAN_=GTL)ukEDIQA5uA`NE5g!h?3C(@s87M$u~Gf~Y{mpY<{wRYPR#DS&f1RJ-HBXXTf`^!2_aooLBB#y8AGEsH&AZI5CVZUbUcz$Tb6@HNYpwxwl0vA!gt_PFQP#_=K}pcyCcZt}jEf2bh_4x1ryXm$!Olwkf|42Z%*GvI2>z__Syc&yS)4x+pFGC5wlAeIn7q)jG53@Y2$bwF;^qL`%k*M%($p_4IHUWvNj*1&*7GO^=jtV+Ux9<I@^`|X>#8;7S;8I_0djngd);)?!Uh|Xr7{{}|LfD5t)xdk7D4ZgH<p@b2<zm}$1GQ-EU)5Q4#b^4a+rdrwnd4vv;Lx93K854>2ruR*gEm=jM18gGXZ1NPXs=-QS`?pe$FkAQPY^(Irde>vJ)>QHfKaG(n(zj~RTS5F0*OJ;k2GMWaWElW{1{_=0DFhTDwUs8jD$}0Otn9#Eu6_+g!+W8~>N5UmT;S+nnmq$Jty*K#5Hc=*=yQPU{Rf`4uOl#0dw-g-04#^sxT=~chW4UGkw<bKu6wlTo`CI9pi4O%mk7VXyKLVC-6c_z0kkAKVlmVerdUG@i*L$Q6HmYym4-Z8F4Ou|7Dhlr>YsO+s<LyQf?dH0dJ#pWfGDq(nq<8ceO$}z%`Y64jCth^J889(lUIA_@!ke_w`CV*16^kgBeibZ?1y$h>T!x(;e66eYpQ-Z^JViL8@4kJ+)(bZ91y?SZzkyRt6-h-+9)fcrd;>Z+3xe-_m<+BrZhEr3Kgj9WxYitomD76w5^ibG*q3q8;xBDV^3z<jNc~avOR^!ov9Exc_S5aT1$c6IUdtDzKvOP(ud9&Rt2V@7iJeGhj-aoCq8*xqNl}7Uo2X**|+U%hx<Z9AUs`I)38UXbI?)VJyDQAiZ3ji3SAIBC4QMoX!AP>eJ?B4AR)_pDhdS<HE7g~Y(im5lcDXrI~Z?+odK&uo|bHq^{BrTPV!YmSL%k4zHH$4@rGyW>qaPC;Fo;w;XP|L6+9A52~??pPef;OUc&HJt90kRw<UUd%xO@<Mnu~P?A9Qu?^fO8>GwxR%*a*i_BxE{3aqkl*Fp>MT5AD*l~s-HyR}KqS4mr(GwXV#qMdP7U^?B)E5&7QE{U{wAyc~t`qsehH{pK#rq%bVm|^Ml&d}{o>*M>6KfFMCK%Z|%uTUo`UT-YO$Asc6jlT5DOB#|@Swa(#i-|r(A_ZhqYx6C%Dz9y5?&bP?UWwX78or{-AgWHfDJ8{K1AVFh7>qO0`;~mx*)IXnM8^!JD?DY>QKUaBp&6aM9{-On;=*RSNBj^e4y9F5FP>cDX(mCG7Cb=Rzu>!@Lw;v7XVVZ(sj4|X)*MZWqyU@u>jY9UU`j)%-A(MSxw0YKeqfBWK}MyyZD><6#PjTJJaETf&R%AF%1}$xtZHL*n3j$@r<lRFlwR~^Mak|S8Rzcod&(kvK%!tk!ZA@Ho@Mjy6lCC_#`A)$@XcdS0}^#5TvrGR)5}N*6-ky#D?`_<`{>~A@m6B#5$KaOPN#>wFn=r2$Qm16d0BPMGhRi-;(;Bj^tYFk#8)(HA7&jOS60Mr*}8kb1iO}NPCoW*d9v}|ab5?F+JL@8)0{FEa}=X@J5&F2>%ermVEvVS&uRK79ieSG0Pn`LCKT9g$K!#+p#a$4?z`HS5#k2_4FEgv5HS~sabjdA!}ADi`1s|=>(=!xBNCa>KgVR?M)EQ(9)X@He}%2qaBTQT0iFc_?>o2j@LO_I_bi{e&W08Sm_^i$>Y5ySzNsxcvoWbku52G~V$N=xp7Iiz^<IPC>^SrYnY`^+(b2_xGk5k_>&QJU;M>J7a8?{RUPS<VBPVy(U`qp+4x6%wB@fuTb2Z3%bEHS$eL3u>dAfshP^2gp@s*d_Ox@0Tw(hK5mbesf46&rG)t2)VXhN)!m3mNhO|5joWb1Rx!QJG>9vms_;&f&&G-At6X`+^OF3TgGKF-asue$4A*PzZyt{m7_RyrEJ<VKv+O<5z$`!rt><AoL1{5(Wo)F8<sKU**J)^6s^e4Cvr%DTAR{rF&^1v{VhzD=R*2Sb9$Hb7@h%Rsh~^*LQ{tCHK17!B~z!@H6aQ*6c}sg&8rOxi3uR!@sjc_a4cH0z5<QJn8uO5{Vz(i;VlB6=3)Ubs|lQx_$2d@t_?oywWT5139u=eINm@>6SX<8Q}9(}SGK;>Otm1YsmoEnjwRxr3W(zPUO=#Adx2dg8Xe<IEe{6?*R#2n|4wBHO=dUbI&8YzVf3+1T-k15V|kE>r^3H+E|z>(i!G-t<mxG(bN*-oUK9ritVWp^l3NI7$c{|4D;9)zpk-@77z{mb=|S9$ZevB-gj_D;EGF)#EZ=V)J+l3v-|KVE{OEf!)N=+!<8KIkd_6_nQ(8_~4q0D615N=FsIxH^ZjA8Bq5rN1B|558Xk38*(m(eCSUFdcP@oNUh7IZX-WR3%Snw39>hlJu8@TR9%hRL}?H*zLIZc4j!k)f)y;f0h!Z9ql%2Zs`?3-ja^5FgEq1=A&z5x)mOAQ_V>-88IE{79L+<g#uc@^Z+A4w%s$x^KS>1|NeNViD6R-BJ5W5%ZD=v4ypWQ(|G_jxcbSB2t=OVxZU3<xSGVWL0BK7V+_SZaclNfz2xTa`i!4$LE^mq~KV!82wl!)e(4n=Moy>Y|U|#Pz2Q&X@wF(VOmk9a*W}`(jHc6liFb4B-^-HukxougYgON|yU@_6-_5GiL*C`KZhlc3rh3fHM`m7XI_hp=Zi(-;3oR(~%5DBN!Jq5zop`b7$lwoF36lu_U=M00?VJy<Mjed%lJh?W%tV6v7U~H{Jdqkx;eS6tFB$zc6@o=&igQfpAi<9?mn_9fAv%s%NDu~vU9CGDHDzRpKYDrirBT$-}RT2JmICZZ|`3KusB;6$DijPq+VU+ltDr=3cr6_dy5AIRT`z|&&u$?av06Qzs?BiupmFhG)&RS+(j^S@BB{H|Gi~@dl#y%yTcSWP#Zql_*Q6Zp7IBkqWU*6+%nei-Ro}fy(7H>fpS2-$3_u*RTW~9{||MHa!@V*E?o=?brd{-`o`?3<Ku+~^vVJNPJtc^ZeR;PP@sUCt8qf*xO$~uPuMx_m0mva9r4IzNx3vn9)Z*%%@O7oU2fRozdJHLOtu<!>i1o~U2$2QbRb2eq{RF}U@7YK+bmmS?zjz+qpot}Lza8qkYpGN=<>69Pnx?CLXUeUMJUU6%=z5VPU`}A7>=kNda-#@(+8%(FSPD-Xea|!QpKmG3I<FCK_@aL~TkK-Q?hrfWD)d_e${Q|q73iW6Ii_$T;`U}7N@x!;@{O!|d{_tbY@-QCsxzpt7g)bNRGq?O{aJwz3vF-Kw`^JbXH5ZP~tB?Wiyb~GdA<K@eBd9dImYP<>J+U{uakjt(UKrlS%W0Fe()gy`Xf;cUK(rzMoIz?GJB-ex{9?C|<`;#K;94)Pc{w=JjfrZEqAS{s2*!7F+Rw3L`VLN|x|^WNms(E-PP)dUc`UClWSn}BMs8lFjG+$_7FJXaMQ}1F?Mnk=mo{=058UuI@?eQ)KKK#=^mQIg4jDLe!<WSL(#H#&gvt=!lC}t|Y9p}Ss10#6COs4XPAvhEl6$@<=<^U>Cg46Op`E;)KfqttSttGz`(HBN7U+kirKHchy$ks+xs+!1fqC9;?v?}BRqx*OuBT4o(3*?RAa=6qDM8T70d%&#&(Ec+k6UBd3l(g(Zv~s6NgegEDqQt-M1bA$l|ggv`35}EiKyyPnx4I01X7AAypRT-Z<Skj&K))of#q^9>*JSs6&J!C>zbDP;B9m4!h_jKcHz=8@8ZS<W3~~uMrzm<H)kRjuVSm2y?{vE`2HPUV?@cOcF&ojHwAQ+X`58Sfvbjx-nCnJ7;^8@0(<Ym^xw|BFs};Mj)?A@o5tfi-RK@&(|hzw4F_&@F`tUNzyEl&?&Q;7e*OogM226^P-ta#Iz18Ot=x<(5uDZaJn5#c)a>4BtgdTfkbhgvpg)(zep<$k5&$Ad$T0<S3w|}#7Dr%)UX`mng-%OXdJiZ84<@>jM(h2Z8DUY{yj_!;dUd1Q+FqeaMW+rG;~ApF-F-)<iG00gpZ^iu1cmRpzOQy>=jmp{7?QmP)FjE?k6__tskQJf-9m&3t=~0oct1{{AKfC^Z@y9q2<W~PqxaluX6C;|2k0kpOmlV$twhD>X|z}n<AL-SQt7A5K*=x?M1v0OQEOp<ttYOuje+zF7@AU)#Efox;EIXTXv4YM-^e>hXiIEq0b5VcgvEy!29sTpFBIb+Cb$9gi_5}YYq^!7ET@u?L6$y#a_5m`QVIM{pt0*enLAMI`L>fsOR|9`zJEhEn=R8Bg3swH=utm2GlYZEA-*M@<ZfCKs~TGMEa9lqYR|#T_gwF~&y+NY>6ecYVwCV3oWddMOj!k|CsF!>zMaYAaLI2569loHDyaeZ#%!dc2_cxKC((*wcf-;HyF<p#&sPt)m;c5k33&D8VwN^bh6zQ|i|Q@48|Pp2>60hBLLB(xVL(xIJfqpVme1dg>U%b|B_ZDODKq)ztAenSWlGJuSn;M~pkGXWkQdEGp=sM#zJyqRmC}-lh|lxdTi9S1!3W@gCTKsWuTeuj*&9<f!(FJ#lu{sS0|Bb}=j9sS?L@~n@2t3bOYWHTv~X)9jjmA}gL!@4Mn3~cDWMp40cE<}ovT8=!_``j>#w_z7uAKlcn(8r`r(mD+9W+@rF6?f-W%`&up~*1Si1F=j$QRo`!I-c076&<<}RzixG}NhF*ejvNu)k2d@YvhA&a~2;L-IFh1V-I2X7q+<IYY;KUoO!52sbqUQK0wau=6XW)(3`#?R6FPS_OBINSfEGb^N%`}!iLa$B8Owc5XjWSrckuS*5>GlLy^Dk>UW{0ydPI4W-n%1l(+zBqzR0>X>#^yo2tliVV-L0^21)i$+W{&fmZ;>EEjk1#!sWMD)R*k+f3N$B@H7qTEvhga*n$CBBL;~`Y2fSZ68y7Go&O5%@emYq92PVzP?gcF^2<eovjh=LqF%m*m_Z=FkN{@mHHJJbwSdBCvcn5XmI;h@mc4D|5pbXWopFEC*R4(stS-(jmpENKXDJEj3XX(VM~-t~Cgjw+RO-s>!m2!(?c*x{Ta?~Sn5XtpwR9IE)-cWlz!k33dmSN0@oPBfIwgX*3{lrnk+MKDsf(0@*O$6uEHYRzH{qtv)5&|1Bp;9XNgS7EdWJ+G0_3;I3yVI6!mZ05P)GQdi0P=wvC#yHFYPs!a&tr63$TRdNV^U4c9!|~|XLJJE(o(Jgo=Wx8`02tAUl0oPiF1dIK<PljZMpc7{R+<XbbOqCKY7wR~gVG~_v1=P*AN@$0MHe7iIi!5p%IlIvEQa!uEAmh=q^=M@8rJF;xFTYWG?xY=PXTZYo$knv+2iUsvP`tr19s=2XyGgMC{YG=j^0Xs6ie)wmdA3V>*#SttQbSYRP)Z;l;ID9g1&w76j0jmcT>9f1@jD6*vrB^k!JN^NX)|kGeFkKV8z!P*5xr|@!6oBO*DNo`#IYQ$y}$*OscPzX6#(dc$bc#NrJYskPYp7T+OBl3g_m4JUH;#znhfR2&mo$`g^45F1k-sBYclcOo}Q{av{J0_iQI^r0!QoYSQSKQ1uW(5M0HDFDu8<8Hf2rJsD&e$iitg0Y7V<XWyAU|MI~=wqo*>%FB=1nhQU|0^=b!di5-uUc;WQG?$atpE)mm_(PJ`yPXw7S-<2^fMt1Fvf66)P+pNXY=Dp4I=RPGMD<rErPGRU2jwk>R?x-T1S!C`t5kuV^^-_^WMFtvCi*@52_xCbcD+U|NN!Heor`^HAVQu()0<kHuXzXi#lhVk|C(BcM=ybQ0F&%7nHU!+CsFoR3hnhuyswc=<Z`90C@Tj3I!{D#ova5Mx38=Dt&CHIdKC5oBok5o2cDad=LQn&5uv_`2{ur`wrg@uq3-<GLemF}-5AB~c^_{w2g&y-{IbQCciYU#g7wgm;&-)`nl?W*l)fpp?EQV~rx{Jz0tk0TE&F5!X^3TOoc}V*1)+%tq)W-{<u0u_HeW9(5O3(tmg0;hMmR(%FmU=(XTUmyDiw8u^=6kdN^vE4wir81T4a^BB}Oi?Lq&QL<D|Az`X(z)<oSn^`+9W;s98g$f09&yFt@|<v$H4fsZt_Cv1{p&C`S=D5RrTF*Q$xOA?cX{7RN=n)P~Y_Zh5Ac*Q{22a8wlMeEx(j!RQK?F%4PpguX*(EMb%%glN%#9IfTqBG3eR!GfA~uKqtD84p?oX*bmA5609xb#E<|(V1voYOxGy1jzm^aiSYnrN3S+us&{Q;b6SW&$oNK+}WtnHZ$op&7^Y;Vq9bm>9yM>_CzH1%pHnJFZB0f4b7y;MRApW63j2lmZU6{xH1#ocmj|v4^lRtA2oWJ@MtlMWg`Yn*j#W!vJCAGbMfC=_CvK~1XY@Ox%Otu3DtExsRN&|LRzL&*}<9~lmv9J0EW#`Hb>8ukra$0g~DDaLkYBd<PgUys}F953b0Y?qpN2Od?Pg?SxVzGn4g`sXf`e;dMdL?8?(YutE#>28ZKaP#2F!2YfaBcb}MCT@F4mIteczBL>#0;V3l2hx1EfPLlv=j9g{PVFENQ^%xG5gh*ZK2VlY#dya~%$>pg7o0N?1rN1a>FS-cAwhM%`;o2#>JwaT5zdVVR%e)#rJ&w3+QEBdaucJ_so6TobYK;#FGW;%)L4B*_hhH_ZcnrZuW#=x&x2^Bz~zui$Rr&f0^^gb$iVtKmR?6Ew^n7T4(BG|GWY-nzP!X_Dp&gx{#fx71uWh=;m)MZcejBZj%(&%U@>$?mm|EWC5o$ID&c{z|GB<x(d=w96^GCAQKzI;Q0qKoMYxKkDM+g&aG9u9yM<WU9EFCp3z@3gJeh7SCues*C`ba4mZGWAOGpMj)MAV%(p2Gw#W<OC2^4Ppz{`N<=dTF4>HWENGWs+>z0sZQ$P1Ro4(YPvnLn}W`N=~?<d<GY%a<L>5+SL6cV)Z}()%EWGl`E|Nd2D-0SF&$4wT8{MmiQr(Y&A^)%9?h!Wyd$62_q<XJXORxE_CXo1Vv981n^p>pTWQ=|n2vgzVANK@H&kZ}jJ5`|qChX`h%1aJM>}p=O;BKbNm-A31~w0JrcoqH7f?^ld4xCZEufqT*SCBp_yMQKL7yRK%IXEBMlG5BH*%ddb%=c8H2a90xt$<Ytw*NULzQ&E4!tZKIjg|)xUD@9V80oS=ailYsM#=BMQbWPpl7@ar}zHRF`&M7`(rvBV6=1(V#S+`+q0$EOQm)ipYwt)U<~(+C^XjBK(1aVbFv|SDGW(tTceb@dQ)FD4yJ&UaL7eZc-nxcS86n;w*7^7KAH1pB-FyxTz5T)vgWF5odiLR+I%5ZhyP_u{tej^YdM?WO6!WA@1)mcN$77LleZ4UY`EW^%DKj#&yrP%QR!u{;l(av#?2CW=S47DZ@GM%!stN`G+0aqr<d5E(Ptk|uc7II8gAV=%JsB5#n)VF6Dd<LMRwf*+t@gG;k^V_XWS7G{Sn}#P$J~fNPSPG9?=DLwoG3M>&}g@W}_o-qwo)+<$ASV5_)IxLWoO5^!CzYE!~;}Yll2_h&31^gX+s5K&4iw*Rj<G&u_fpJaV(uMp-Yf#jOf16`S^f>CczTWNtSEIPoi&3+*2ve3}tjc|jkaAw-(2H%e8YWpu7Y*$^SBE8v4dAuTO%@vwOf4UzY9PUp02nydzSs_BDISH_c}?3fLv5ksL>swbzYJr9q*0xj<W<jieffrGSPdYtZy_gng+qLI)6=Oq3oxC2gdeP_Ay-r_lZX*kDB(XExE8$7C@fX6D9|AmtEJDd5v3J_zn3178ubs@*#)x0T)Swjx)OzTJHU49286!w<lTq=&@soS8v1ni@NfuG0@NZ0GnNpXN@piUW6lKDKw1NaEYPJ~Y`i@7)vYxdU1kl^eG5z9+pVRAP#;o&eDa1z^RvDXZLTH|JSlkfAKmm*|cwrSZ+hHNOWEbkCyLb21MfDmhSw#hi#jbJgdMv5^FlQyEP6eRLoa$cjRAr0L<4rOrg!}M>eG%UbNjzYOK35U2x4=HF{2IQd^&(S+g;dwWj5QfU3&zy-=x^*GlDLy6?=x3M5_1ci(d?+MhMH|6}Ix=AaGMWIM4hh6{S!3Wv#)#@^kT1_6fEj=m9MJo1x4(o^u;{SeRvHj8A_D9LrZGF2zkJqw>?*zl;D^LEd_OLUSc7J<ta|X-ZO>cYc{euNLXgUpj{Wtme9JERFA7HKbivyYK(8HepI{>o2_<A7&VeNXPsW<(T^p_z=Fo4cuOcB6MSq+&d&{z{Hdr_4z4vImg`p!#<={#zTPxGXm_ed_1#&s^vi$J|&;VsTfkBZWO2^em88D$F1clA`zdM<8VH42Qh-%2?XG?GCt2H*FOOfFfz1_gX2|Z#vgC=I`SQO0BX`X0~nJsR?tj&F>+1A)*oe0qb(J3C&<hR#+ZCeL8ZdgUhoLmG0=XgxVk%1F8lf{toA@PZsf`4J`91Q`s*VGQFrCaB*@Ak1E-5*8atoCJK@<sXuE;Dq$ftvY%18NBA)Yl783$Cp-IRuD}FlB?N;E<#?e&)~AEI{W(&f*WugCTA7Uxja%mbWp{g?b~zKFNAB1_2-&Ty{oWfj09c%&V;aZu8L$Rr93aGN*@QMCqLN>npP6L?t~=BoOof({iYjfElG%8AkA`5Pvl%RIa;~abiD5De57!0|w9qsWMuUx6SRq2M)QMzd%@yGw~<s$raaPhAdzZ!^c-FBQu&E9$g@VyRx@*cGN)fbCZ_+^M-;^NkL1?F`HweXi>g$)L|n^rL49~X#f)&0xDM0{Okm$037*J{*bz?6}>F1Wzb>*Da3(^pHfgfCa)$f)<|w39$_iwQY)>3o~+O3#@G@)j#zJgq1JF&R((*qL%zr=NwR@g6=TsS-2jL;wQ6SoevE4k^oZLOlH0Z96_7$Z@Ii@ugWIDJ%kcMFUP37M!JL>&*m*)8Fp4fpqA$OVO1u#MFi?oHJVV|)LH77PW#z=S2t&(Z9J)9<b{#xPt&kp)ksh!A6YrNhN|>cY^_vLq$EQMS%q307o3R8A3Cn0havU5xvi~<pX9LYVkhk_b?R76We2*TmFbdGH6)j$*jnwgQgQlLO!NPJDu!L+X7#=z;cxSi_XB&I-SkF--#KSuh;(4uJ#9J!VS|L70yOv242hk@#<l88KKBwnK9GN4vYN~Q`pnsp4I5f_T%C1uuZ)fS-w$g0lsniqMj)bT?;$RZq>x>@E-i03HLhD6^hO8<MaD^bk6SYd@Sx=1&x)Q4>mMX?H3sdvJ13skqLAJ8jxXa2PX!jO;tVZowm}rz}KavMigOq|!nTRM@78i+JQM`mTSPJ$Yd{ChR3C3Cq7SV%#NDgR~7$Yc2<(wf!5Na4j!agW~IJu%V@u4j*jxQXWDf?Z7o4`N;q(?>(N!S>il5K@Wws3)pGZ=?SQ@ks%y^{0AGAh)+)TI2TV-1qM8rDLkW@cy?XNMx8Y$)o;Xhob9KfCO2tpiwPfZOsES#W0pYnCcRXZ3PId|a+NvzHO!6h{sa!jZKq*b&Eppoyxbb{FcEratK<7-bZdh0&D6KpyOm@QI9Oh&!|U;s~`;GdY#XEf&nM(*Zq-bPnPAL2_7pRPy?Gr9a<3IERn_d_g*zIUS{e<AJ7Y#+16OkKqnXkQMo9U0p`FwPIN$!2OuaE<=+{|L|Dy3{k3Gp3@FK6|B1-*1-(}5l(+n+mvdcv|OmT&OUL!G89CFK4mAOqLpFfhY;qHaXxDDNL(i#A5YO>BRA9`;z~yAk*vrUyo<oGlQQL3EvT{S4ga|7$rtPla&Z9J-XPilSQrQrHpuxX?{VA8%O}rA$9p_15sld2!0kizxaYWpTCBG=0#OR-ytSuroHlJiEWbs`=bdN|0^45jh?UvK!-9_Sf;3naLTNzxhE%RpH)hq6ga_@gz*0pp__gX4F%tnMVN~<vj4=J-552{#Rj>}<e*Df-1Wu?-c~0w0g$zu3R-m@5g|DK*tBdKc&1hs$2QV0Nu++5o>Xd~8E+1Pj#$@zqK(bP~V?Z<rU<lyE(opSEa|-~)+MZlRW0q$s(=vj8m`D0FKA$2f0V1J_u?W{|wi$BzJ;;Sqd0yIh>$SbQwZo0ky(je(Om7l~NFZWWq1ismY$^6aphM4V?BE!ku*7S8XMm;h>deU)unD;$zS5NtrCw1TT~EgF;wqAsu#S#ytc`QolhIQp0Rt=dmldl;*eWx%s^P!!dxfebi^NDvS}nBy<#h?|8uqTMI!TIx9OwJ=JqjT2WINEBoUXf0KTqrrHsvsfl(R4e19ZWm-&5@4rtxWAKCutOl&ZqQodk3r)cV!O3}YL?N}+-FIG3&B(LX2=#jR5J#BD&mKkiu(INaP@1gy9!@3?@5wWMpX);$%j=>c4{n?<U1#^E!KljrM#fWaxbvrxMJ7|lJG<zyx`!=9$Y?DjL$?kI{)BD2c45hITzQ+JhhyTisj6(wNJ>q0Vjl8rhKj~(aFqYE2YGIwScx6?VB4fT2m07sU}rZbt`{H9;!_TED-_i{qLJo*AQ00uyVh}SZZ2kGYgP7fDwT1EK}!&|)03rI5Rx`t`lSA_#z328K&gv@lD$%#hs(O+B#h^fxO$P?rG97{vFV;zAwH!Dxx&u}*=(6M6H#ls{`4m;H=H2d`xHcaQKHy6}kovTA*HA^~!#$dUK##sK&YEy-_d)0+Jq^_wRL#;wyTb=1HzzWo)dg`m9^gIVRnbzAOjvwb_7n%%Em#G8GA%=IyutbIKBbl>Xm>N^UrbszWbFowcNSjj~%NR32B~It3=DJ=pQ`3<nf+D`6fn(-5Dt$sJ7E-Zwh<^?ectdzfI>#z?6Pc_J!%0ble@Wg%d!dqdGAgdD0>TYYxk%J-s~3zxDIbhneJ;0SSMl#~rH@R^6~~U8wNKS$30Z^BA`rNhUgVSj-(_f!4jG=p)8XxUF#pm`Kl1!r+JP9oCp0VUX6^Tm=f_!<-D#9q-W788M7Dvq4{!s`dgal~<Q?gZ*Iub-PPT6Ir&O&bq2KC}pcGY@qMnH6jWMoB3Q`O}a(V%6!lLv~EWKu$8GfN(Im)1E`TW04A4MUF5oX@A4w2mzw{aG=SlD=6*^AzSF~FiKj!7uQ0{VO00;yA#n_4_h`deBM3d}#b^#di|P}0Q6diTWnsAwr=J+m&MAwGgkw9PgqlN>+DDDqdc6t7h&GNWwI&=a9mK3Rt}8sB(#yuU4vIj@Ugt)e$S?!%V{(nn8MZz94ugo9(94@`f^sl#7$B6hV_J-J>GG)du8@E=Wg2Crk{rX&z`I0y|+=3CLUT7rH)WP`9!mucYn_9cz}kJ#htU8lwIRNN+_)s-FVqB2j>9UQ_tM3&5cg&Oq|#ZJXwJpCe2_=t=Q9C26^Q^J3KEkq9Cg=5v`NC!pU(Ui4CL=}uBV_(emND&hHbKS^oHbzU3<knOSVg6<Hc}z+3*z(>a5rS>rI^<RY3Iwoa*s1<BSq}q@3`x{*i3NkM!R;LZW1(@T2p5vz@@{0N3(5;N%Ey#OMIV1x3T3Fhf+I!@iy?{oD59Y?TMY4-sv>g9Lx54&D@fL)O@Y%lOSjQ#$D6S;NLJ6p8!3J@#1lc=PQmh?Ea!2=Bd4$pJa@!)cf}?uwl6xfzI0^SD<3C#R7X!uuYo0Nt!Ng-6X#I8$LJjh6QzpesqWiflrJ>d`?1fR`0UQhG3mt@pXoY285*u_c2&fukLj*@v4MsZx#O7l!D%&e&IULn;;T_!QOFh_e{ISK$C8TW>dQL1BD|NU@AELPIHji?j8EI<`;R|(B03aDjH`=rl&TyC4-l&AB;-;S8($^IQ5l;{^<`;<(tV~_d@G$$MXj!bL0+X{MC++~XZR0MRQ&lGeco0|c5#;92Kciy(&xgD;M+Ji9GdYwb_LR?C>U|(IC|`3MS3|p<fv9UnzNyZIm^o=%%xxe0FhK5;cCuO%&S#C>?|Coo-SxGlrK+&Ugz-FaZ-`c2>`SF@<gu7=J5tjB9evSvK7K`wn1haE?~HXOovO^xp81v!f)U>78bhHSQn*k#z|2H*c_S9NPs&SjS)V;cEuVoOsunkF`jz9nhCv{{bQPfU-X>T+m5y9Tkxjy2>@`^#v&RKr|+P2ZxO#iI>agG^>-D}T?n41ao4k^4tX|%2WHThFKEGhM1{Zr(`!JQ50{`qL9k(K^jL820n@zzzvYn@etjMt$2v{HgE>qH>^;?C&GC>||4`-@x{MlhP~H(ldTZ<e5A>+pbHGl%qW?&xdS+R205N^mG0(`!4ep1pOO^6@4IVoU^d^`vje{<naNVKDHgwTFZEYHv_-lcs`y^YY+5p^2u8|iD@e&3D#_&0(-cH#vJ_P8JZV<Xq+d$L2F-mVzqRzLJGOZ%M)n)~f(bmyg^kFXVr$fWf+6R7tglB1M_4FW!y9GB|ayO6?-<{}g0S=eiT}0(?8Et*Y+JX_-m?ovgzN`C!HdZVr#aJ1-Cvo5?R2n@NqM8#uB&l>|LY>bUK&GK&WJ#}W@dUOnO{YmRd)AHO*+4Kr6CKY`8PuGvF`5f4%w~Wb8e!1KkTOfUVk*p-MCw^Obm?EK<AhJLD98ufw2Lz|A!p;9H~YjLc1gpi>M1j^9j^J)Rfw#2%yIsNYgK9TEavr52-*jCDsao`qy7{C5OG=xkCr*ujIjAOU_;JNX$IAlbEHKx%z1B{YJ=SZigV(LM3HP_2NIE?pr_MlkAPhx)`lnU1{R!$Zuf;!l@Rse!isHlO?lQl9ua?5R;>8<um#R<hs(=W^Q*#f`*>L<B}EUJU5NfcQ-cszJ)E7wOfT%di(UgplRL;gxqV4-;WvJmRm*5_4G0XCWuhdEybzzbgg@>QbfKGS(+Yywz?g2xCX>ReYA{M*qyK`Xq4ZVzgVYHu0iziJ2{Bt17(@kJuuBA{;w50H5DUpGr)}0vvFwe;kSr4|qF01WvPsh4Ti^sf!L_B5AOHaVzL!T_Mo*}oWL`F3?M7#>6rNvT8k@(GM7|j+rYw85BO+|Ox!ue($+Bg?gxbu+*QPHCt_8H>Dv8sVI$z4`Q3?7CPSV=nJ}uJ&YL}q}%17S7j?Nr;yjJ$ze)LWU1<P&;`Ri8C%TpflWZnvyydElwwZx?2Ef#~TL&P93qfzz-LrXJw6Aa^zEK{HwXr*r-bG8SxJt_3eFn3l;NuJ9-HO&SV@>A)#SSLBlNbQE4##n)80%;aYxN>yT-Iq@R%i``-pf!-oDG->Yw8Yv^`wJZ4=S7L0II0x-KhQRc5F=%@^hhy(dN%a5BR{~WeQE7q?m_Obu_1%^pWflq_y6<X|Lec~pHE-U-X``02ir!iNbu|hd5>B9yO)o@{_ew{zy6FQ{_$}53;p8o5cetb|MkoG5!`nh9r@~XOt1dt?|%I7?Kgk>^zVQ8(J6u!UglZz=4qI&<#0apkDjKl`v-u%PvAAa{)OwaX}FJmP!Vy?7?9bs21A0vWENSwUI*AE3X1-K0N*5w?5aUuFo!5~E(`&gyf|eYKV>#~WK;@`Ys6x!H6&04EESF~JSZw|AgZwcjS+-Fx^nhhp>S%-A{ad)jPAwW8PO=DI?7{uSA@6<S)NY0w2cdSmvkH|uAj}pG`^cRGkP4zf`8q#Hu~0+fpfg^XiSgfiyNojqmiJ+@bzd0ZlyA8yetwGx`DAvxz)w9Jbca5)0Zw7@Fn2sM<1-g0E=G|Gh-j@a1z#FlNXP<RULDyk~+4ts>MJWNbotD7|K}AGlDo9!b@>UA4a*p=2PV_`UixFgRxHhC%(l+-&R>@U1;X*eLM`<JojP%b$zEb$<CIe{MpK5d)HHkl-in$&LDRBgQo;RF9*=s_C7zCu0C#!VJ}p$i(r+$0h&}+umyJ2C#XpCmahz&bI&(8r=5tZ9;NBo>qQ`?n8FKb;Q3a$b!Q>W?Fej}!sqMbmw6Qz!X4|H)<Ei;=GYTOg*%s)c^5Y>7{Zqu9;sn{np}mVconA<twA@V8{NOdYmAuQb*(t4&qD#qy@p)7;lLG8*}Hbx!=wlBoqNNOt2*nCSMTCb8fM+GSMBiA)4`t6;G`RN{X)ZmTV2ejlKt;L9<4k1^p~IiK`D{pmoqm8_)_j^QloArf|aY$)90Rqhu`F)ZjIG-aSgH-s~Pm?V%ks3*iqU+w3m*PpznZX_k9<dO}V;k2A$TrS6e^{crd|09pyZ9W`sp)^L9<gW0OX=wY@@<icTFW1}ErTXfZ=_b~jtI&;JN+g2MOs(mkewZ@)z^$+6cFDE!XMN&EE%6G6XgUgUl_KtH-gPTzc`Qoi4PDaJLr)y&L)iw>SI6j2Uinn6ZK&5#mMttJq!{qz@R!57r<#JSh&{oqQ*CCI^^4?-#IIeim#WUCCS3A>O^g%*Q?DhlKe(9{+nPhW74tS^k3`2p;WaBn^0x9RyBl+74C;0Aue8bb^&$hHrk+<6?CB$z6MX2nN<Ba+Ph?AJGxCvN!WLxAB7?aFkA^{AYQ1#ef4@|MBvSo4GzLmkH?@!YU!JXB+1<;RZZsw;~zXq{F!w}ewTM1`@$uuHmha8<mZX-{oyd)b>v)BdX_xG65+8!5>^2&3sqv^QaN?QXqE^ob%--d6&T`S-;v{iOYcF`h_bp>-*PAA2on@h*F`%T7)4d>A1VJ=Sr$woTI^61!UQ)QewuyQ?<ur@?_F3nyMTZmIhAc>s6nsesM7BI<m~$G-Wh7~If3C0n~o2qtm8Z+t)L9U_0IrNew#_n?2M1}GFh?y@W5xipJ0nmxR=t-2*_if4mA-RO3^+^5^OiO&~&D=v?{HteeXLj3&>4bU<+U?y^d>@6TY4T>E@&97&R4V|3yoOyb@&N%~O8)lz=wIgLW52LaPJJ@U1*1@vP>6r*o?cTRpM9FK*nYC8bYut+e3VI+px6YdK1@8GjYA!J<Q^b+>(NY#QEB7nO<lwV(i3jVrJOu`gR{_$gU&L%h2Q6;T%Bz1q#_y-5o9VT;nS4sZ5GZ-pL1Q(ptv=q131A4$+*NA8Ugs3$t$KoWDz<?=0|hw@7VpZ6q3lJ?*F5NJloOIhFKd(ai<U*b;r24*UMifB8Dh;57r!?_Dgcfv7bqQk?+R|yUSkV!pa+*PvryK-m5JM-%h>!q3Br@zO5<m6X_TrN*;XwCSOs^3A>ONNWFusQyX1XP5s6Vl>!suJ6Al;5!@INE{Tb{?aQ9X{wV-9uaMdU%-2xHK1Q{1~=pL{(VNpIk5M)H!u#+z2U01Y@9=C>C?Re~;(jNvFii7ud8j%5Q2t;F)uT-LnytHqiHTIh8<N$t!xXbG)nKw?TeC4K}O@{QD#Yv;Sg;_gef@Z{p1gr*9&nW}Xht%v8EJ&i<Qg~UwIDxLBURPf8#rdD~xl^q@=b1TA1?Ts!3r($8Ynx#=@E75Sc1p0Tn9?vmC*X8XdG7At1PO`A4B&^Y`W`V<&+7*&U+5gJKG#K=E~bT-i2-Dcp{TdwKmtV<$9as3!21FBNXDX4SMWC<{s05axt^fN?xt3<snDybG>?HYZM0pk-mI|`DIP_U5Dl`*!+_r;#h0P$aZm7x)9!5YzV_fL3`U#))iPjtGFC*12)P6#K7@T#3CW#53JygYsdhRVC}|a*h7BcJ53{jPL!ZQ?W#N5W^n@F4G`ToLl_&m}<L;qSrE~hw726O3#`eQ)mdAp%XZ}1vk8$XsDxDy_`&wp0o8<QPpEe8rw*~eK%Z<ETsxSBHcic{~yp*ODYrW+l&wq%)3?+!0Ju(kgYsHG4Ke`lIMwN1$GF?B=K=n2!u!9h6G)=+j?dTX#`a!<(>T?Mf&O1?Za~EVLagMS`gHdHGnYQ~1!MOA1RzR-P%+te{RkVOQ5q%C92p+AI>iL}6I{`?D!@v*$ziH02J6cWH@p(O}tKAC3iiv?)U{hu~eLk$g3}6WvTi19@-XK3xs}<YV2A;t9p<#YqbO*k>S%xaN1j5>4es<&zuJKXnR$z6O^L~xH*3+x4AV$-&<E9e_r=cx}9d8Ab?aSsO-#MiKK_!hb7mCtba#52pXAdve4r_0umr)S=V$1;qL(*3s2q0pV1A~OP70{Xo=aAKAd488=@pRKJJBCF-@_?OQ=pO<Q3iWIzH?`i<^~;)dqnJo_jcPgEh+u3@xc4D44hpo2y_vRV#_8#snsa%Lt205WQ1H2OcUJmVh#gE0Qrf*?DOwn<e)4?N1j+TPo)c>gjub_NK}Yx}KR0Z&d0)qkb}73S-GKycIekYs<6A(I$3S@Ty?qc4ve=teTuLvax*G<m7&b)@N^$|Hfp-ZHnVV4WW)`3pT~l`aM@D5Rhy_HoQcp6GpS&xp1lqKfxa(~&j8<q7QqXyCFgFz7OW(={%~Yci-G#gvN)CXnf&=blaB@`IRs1ZL&UQt@-`PXe9=s5FJkO%uJJAL8>>oQj>3)1C@yxM21*Q-|*gf};ZAooGjd>khgwB$S?mPpHUzWDKm!d?*C#GNtw1R$q$mbwK?YsDEh0t+Pn}{oXf@c69!DYo!QvVj(wbR|ugK+l9=p}h0GRt<s@E~7mXM+`k!a_#_drf}2@M8lEf{%e41veh$k!a$4<D}jNNnNI*&f;QbUX_`(=7UHzrllF;9dng;6{wzKW07sac(YIts~~6UJ$Q+YhdQFdlYtole5b@~wMT{~NlHZP!!x{IgZdiItXkU=2@I*$hZT7ove=|3UZljlf9!Z*#-c7|MmgOv4RN~c6_|pt<SHB5QPtUK2|I&KFYjM+bZNz~*KxV++u?F<D~C_t62Pa82id*qIXGu{bjKCVu2uFLMb+H=sU08-D7Q7*X*j*9D$MJ(Q$g9(7z{AI0y90;tgKC53wu{4D3`(lRuOmgi*?YyysK2{<t<8?5e_0(0%q7gq-;E#A&%Imy#`}wKe3z_Hoob!(8*sPyqzW1A8mJ21ViN&c9nuY^f8``?i&?ehz<&rUD(!F1B61J{Cin+tDP$zHk{;vr#;ILoVB_irxtj(G03FA)YDaJux;W{SiD!1=CQY)LC7^W4js@-G&}cn>4xBi&1^Mh5v}2Dac&<Al@6Acaj`HrE24|jXi(vo70769Ne4&J*$ZD8$AdY*91p4bh$lfYM(pDLGAZ?Ut9yd1{QdNbw%!FPm*c&#XtDJ;Q85c9^Hg#q{_}@#{{(46o1%y^9{u_}SqXnt5ZliB;$*}*h)+lw>cVQ7=NJ7ma*ZISF^5@1Spr%Z+mO+i%GDv@M27u$YAXY@n)ZO!p$NkliID-grXDI~S$Y*2d_1+ZZyE*_ZGHk?d_S84!wZS5-vPvkvP$AHTwLsf;Z~EH8(EW-OBFI}li4!e&0MDZNzE#4sXg{;0q>@>P$)Z#E+w-+r$I6C{(k(eJSm$=9ASH@jyw7*c^&72%&fmlIBi`gGdd{lY}KmC)3?|dj6}?yM*(rux|OJgmG!K#@atEYHv?>i014KH_~?PLbp1MyFX0m<9!6wJ^VXl9C@Tp<K#~XsHAOzUYMxwI0Wkz}X`ic420)dx=Jx(^WU$Gz+rmJWvS#|Y<++fMATqy-ycJ)8)2Xt7_DQ)KMvw!E<m}%LIhdrKy44N<s{2T&=||uO{g=fv7I25+9EZE~IcqF4>z1#e9P?n_5pqS1o8UFq7?XJ4)>A`hfv4Z&B%N|n@^<7{E(SZVR2S}N?$%mMpW99(D9AvP1r9OzWe~sc>1|^UGC1V@ZeXtVCQZgDhC@rqX7!sC?S!!f?N>928@1}Up9S+a9N|BKm-=P(nJ|3nQ3jC$pgDWyVo`wCe71?}@O@S%i)^H;LG)HoHu63{DL>d9b<M;FTeN_3YGak6mMo+!2#Q6@hAiU7G?4+P6{Ncf+?<^VpDB{t!ll5-OaNZUH`2Mv@A)!}hvO~Ou&9ZRXIzS6Dak{^Pyeo>vu`1h3;;0;GV}_0SGn$dREKp&&?=%JC*o!9LuoXE@Hv4snvJh-#gQL$JeYi@f*zg2uwpDZI?>>92iRbUYqBlr7xMu}Nj-Q0lNF~(Gv0wnIIX82qPB5Nt)t3Nu2K`>r8qgjz7br!8$%T2MRsNL_~mroBnl@Jg_K1nP68QuDAgbmmCaX*Lp?3()mQ`BNS28;lov~Pv;){RbVqFgX4Ixcim5GSUEasTU}crmIWpMZYQklPWmaoX?4hW}gvn6&%~j}#tACb`3@O0qEZ&yUt|=s^XE{NgYmh~jez2vQgI@3@vcrqoCXmJ?m+j;EY<JTA_ap5{=lWIGfCkB1=-XV*owcCuQgr<e$UR+OPRjs!=uA;0z#f|lAxgo9EP=}wWxC@SVeX;`k1np5=0rrmktH7`(RI=~{u2}EH@1=?kH$J1<@F<B;)Cw)cv<mx<dgJude<$0Wta%k>ms^52+DYLiEI}QuW5rNUq@^|SjNqidI!>Fv8<>o3D<c7P`8X|o>o+TDjTH=aGey*)YvFsJT^mU8}Giwqmh0>V!M6O)>L{#nF$cHaI-YfU+_7W3Z@s7&Y_m%KzVU`q?N)Re>2V-kNV2qD`3_0QxCk_<)K;CtrrMX)LDw1O$v!NA|+CV(8<_Ushhm#O4nxk%DiC>6;&V!B_eDTKt-W}bfS;56G`Qy36O^)0IcX-Zog*D9Ec*V8mU`NFpro#-vuKp_Q}igZ}7puTJ7?|3<UDVaynHCOc~zV(K9Dwz2*00nJpG+1~7P}WhnmEea^c<3S<2Da-3eTU!-r-po-Z+JN!jY+NsdJA-$wB@RP}AQWw8^Z}K3G>|o$fmoL{yv@v%5Q1F^z@gT1dxMI6D!uc*7S9=qZewePvX#|e><Qa6X;MbfedS7J&@*qHsMHE-_F%j>rs7KpKPG$uIF0M`L3QhEP*^OV9=&7<4%XFXc7S?L+vz>9Ul(rdFHkV_N<YF3<BTN_ocyY4}VHg|XpIW_Y&Mk_T*r7nBac-T(s_jI`lUu*iz&RCrq9(gWNz>oEHg&6@tHpEkh6RUuN+zPji-u_)RszIx_+r7*-G=EVk7Z3Ep|j)BEND{J7qC1HZ)9|ymIcAyR~+jR^bntyiXk%sj4}R`hBQYzUW<w8uapP<7q4tYgsrM#%~g$~ctG<G!%@-}gOQ5PWtLCbo4S$NERVxn)TO1IWRd4<?_pWQ4eQak)=0FO(?axO*g`_|`Pwuxw&aLW9UN%sEu|`2wz`VY%)aT8$76%FcIzOEPF^=PGKseds4tVpCdD|BxfM3I6=#>S*Nk?SO=!*8ZPDzq80dkKSF{F-13KBUK_n}&QmB^^)yBem3V-U?8}^-Zfakpy^HMN<bisKo#!~PUV38n;q5M%#SsumaU1KXVwLDJ%t$;(R6G`^^c(_g!WO1n)xxubkd7x@H1>Gk0R!obAWyj|S(BAJEv0jo^Q&8A)dUWuDrVxMWC6oICWE&aDi&o&kvwI{I+3{jfC>Ghc&K{5Egnkjuz{;Z>Ga`FyYcv|r){!pJx1Mc}$XH8<qDzBWEl8E9O>uO;Q8$QF7?sbh=Q+QFuD(m|YgNAS`bcVxlV4Jk<OtxEL(jSTyNLoVI4npoM>R%p-g`h8Wl_}7JXigQ2NIVYm|YVBL#H9^G%>}j=ZJ{WG>7B~=Vi{cWac_klL(?EjzQr8(KBF4U2B6TLt|^C*$n6ETEE%ra5U$mjpZF}Hy@MHrj%q1)`zb_jUI*mM^CVxmLN<DIzM6IdS|*T=E5m7A8AUtofb!O5AFd1;0hOpI_sPeX^gXh(P;LeJXZ&wIjzr=?urCjOCpJ_eMdyTWj%p-2eGY<$`L{&j9H`|55+uxvvs-=<ICBUTfCNNGvdo$0CSWvpLD9i4=U148;>g}|5Gs{<T5S=!V@4g$s5`AVJV{5D9;MPKi)ap8d1t7aho?|!kY60u;NzPwz*UCxF)AxM*S;@GLrXP+dN02IIdl197=wT-`4NFp)?2~BFH=#(-X~&$yP&bknV3ab3#Coez$uKtur<fI08IY7E?vby8%gXzXNNoK>CZ&$T<WPn+GlPM^i#fH6pwm2zRA^&TOuWUA@0_5?L<$CFx~d-LZA*e_13fhg!ILsGMh1%<Rl;ZL!6x4|Fa3vc3_@_AdyI^~5eg+!144rR9{p8u`g77H!%|Isn@WHhEch-L;`JerfYO-O-fGk*vsv$w$O|BEIP8EIBqbiEUuTpYg|fOH_3ojy0ZHyGu9scuP=s)fz?-Wf0qQ3~Q;|>9g2WZ~?E`W4#G}Cmt%s=pn-K4)ixdWaC>~VwGg-jI*ytY=brjpp>OV6-lM2Ky%#{_J7PWfag}O>Ylw^y}3Jmc%R}XsA{egDgM_-L;k886`(`7f>(+cKlYT+e7c+0g-Od(@EI?mR%huiB}SW!GVHE-p}s!YcU=g&tPx;}oJ@{|h%d4GU$oj1bZiGS2Kp2@&sE)w2DC$liTWkUn@gM{JsjG8KspE%Zk?sTprbfG;#TV3KyssXSf!=ygisZA^W>R6!xK~>rvc}+122OqIei4FaLnRE1?FarBj%<h2g>a)7@S*c1h_Jab`wBvk=#}Xu3NhV#~~PxT^P0Q>7Ga#4y^$|$9ZM?eFnloiwbAt3rxuX{1dD3O5RLKS62m3P-4vapQt!dE^Vp<h6qry?MNkAP|2`ays9*3I8y;Qs5ND69{aZPc*+slcJMmP1iD=m9bt%|So(G+Tn^GWWxn>x&x`xXqR41LxEKz1c|*aDY6o4MNwWXSp^e!J<v!xUsWA*C<7tSvD#U8S#Dw>c;}=}aKKRHh(YCa}){)}_=)h`7%M|KSvdBfnifL1Foievz%3NG(RH)(wJcxNA;6JFH(zLOl3_6G_^X6nqIrW@`1E0)kIwGXHZq*&0&`CL%2J{+yZ?S^z3;sT;4q_JzSXf_@TAR{<VKcXQo!aYUQmZv4kPmGweuj*)sK>PJ?6~-Z&rJ?q6o03UJV!?Z8i0FQ`eQN?_K<cbky9?hpPUhZqz0?{7q&CG8k{NkmQX-###x+4SbpGrxjBvlru6jAqVVRD_a1-4767c;o1!50An;A%$oE&xGOZdCZ>-(CrJ}zQ#R7M3wS~WAuo+`Kx>hLKfrAHMw_&dOlISe8hrcLsufQ9yxxvMzrH3fV+(~onVn<^a8_^{Pa_rghT5&QUEf18{hBjLPgs>OIN6UL!>;ss^xuTE^PiTe814K=jhmF{$^hMVSeKpBz6Vr5K7x7ynrGbG0_%rRr+fSK=Oq#0VcSjx!Zl(%?f>$|}utZ}sF+o(!w1EPv@sxxO-_lL<V3;sSuT~EzzEJa7j9I;u{~6XxWs1$7y^bM_ZE77k!e5J97KW#FhMMJ?U=%~7DI~vQOIjuLMSY7w-%@2!fj_OLzcz%01Ar|E4^dn$fPureAHTEuLQ%0n=#w$AL>dSZ8m$ZRgC>jZtjrE1`z(m!3%|C*c}L#95Gv9T#KkViNjIYPb-s|d{Vv0~nHfI%PReJF+os?oUw5r~V`es9fkHOJC_%-B$s8W9iO68}Us)_nm9E?j7(pzF3{O-S)l60~u@zB$Cw{5R8WvW?X$OO&B94t~7ig`Ae@O5-#-)AeGZuR`U0R@Mh^isC#!EMJR>nm2G!VzrS%cwK7Z!<p!5AtQtqMvaur;2b-*d<c@O7pp#dB`W5_DN=md;IAS4hASt`<+BX>u4Zr-FD89vA*<ly|DfmoWelf!F2iyBB5+V{I(o2wwRQWDy&ii`USnwC<T4S7WD*T*sWjM;pLuO8k}%-guKD)3jr9{HnZzKGW;iXWM~G#^>d+@SQPLKChs0${o1S#bu4RA#<Z}dhKXG5To5C<g#=VhzwY32O6o;sEHbUC*MxkN)o|1)EOWI-I4BB;+khZASR0C9G5(h^LKpH0dIa)KUeTXAPJ&`9dx%Tt4}V}YdkaRYg4C)ON>{0ou$;~ltDb3!U?tjcxf`?9K82~CFun`hsoDZ|EMDuyVvs$EFh?`9i7u?8WFK$^KB{^@ts!*{f9!G+pW4afg35^*6G~X(@z|zbfa8Zm$&SrJsv7>nTK@DaAB3ocdWwMb_gworJhumPzwwHC0^Ere%kkMpns<uqe$%PIkl#5(_=psn({^(JewMI6d6`zN7_M?kQY$zzQ5SHB|}|pX2>gf+1J$QV#BHKnjzAf*@9?lfP=T`r3I4Gc080keaDcLj=)@gJ}L(l%G~LR$bl=A8WB(lpN8h*QrVvb2~2irqD^LT@HIycEc3OmB&Qr`xjZCW_C}8G-lcJsC}@Exy))!<ibx#jmG&hKKypdoCnc+fm;bxT+Hnj%HnV1rWR&&g&iWitQ{K&&nPU_av>}~--HD=cR!0p)03zzESLvu49AozYoXTN*4N~6nowvDfNyl08cJU2!2|rWMH+^ciS5QUUfMFA$31&`u&FM7d)6OUHp`Zz;J+-;LYP`oxfXwN3NcPijSPhOhU@o1m%}m<uiH7}N3<#LP`>v|r9F@0Ym2Sa0RAL^ybnz-714la$goIAEiR;+gs7Wfx=C3PF78oawk^B5&dRNQ)6Xm#$ovNzG21c?5y5ig1%waV=ol2fOFmIf6SP+@>=R!1~@>Dl)E(V-fHJ&XP7i{pQQ3a)B!2NaK^lN2ExR%gAU!P7dD%(@{Z6rKmgh=^ZftifyLtBgcwyl;Folk@{p>Q^Lini3?X0qK|DLk0{Uv)N9c4ciJTSU*A9C+cUy1o%m{n<{SGlSS8t|Ya23>w|I$t%G14AiwQ_y+hoY9mcHd$kSA-IuFhL7SSpt4(^RA%P<tXwv2}V7JC*Sb&gk`d+Yg2EOMv>gYw(UZ3VF0I}hPtg6I?Az^3HoRK<%YiTR`2Vi>;=zI-_WkhLu__<_8GO(4zKP*bR!UqRMgTUHmrl(Xh?`WCX%E#U_CLmHpyfamo;rR%bIp@$t@Q>n{yuxY1g-*NabkgL{0Vc)_@rI3@+JD9nY!PI&O_{`Y*Tt$>dql1OGy9<(AbM0DSNfZ@cbc+FV>2{vgyH1=<-Wg$Y<pccTt&!~Ge#K)R0QuS5Zq9?(Q3G4P=gv>ZVEB=vdZ?>Cm1__8cTt0;`TDO5e)B`*DHRTm@Ljv$(y`23aO!`h`n*kP`7byP1=_^_o%?3^CH>8MDUI<>rgH=0b9-z7Gc=z4R!#9id+#qFIdZ}M>lieMBZ1h_*9_y!m=sOMXggxlqpFyzZ1?k$6>7lvKpoWMF8r8M#IRn6V4YIJk8rx@itfuAR1DbWRs^yilrEgFTS|aXeoW!Kz-xQxzrAdu$#ayIeR~&T0FgA>^^#*z1~$8r=oYCqRo_;gc+tA5w10_@0etu42r00F+1%#SvvwVv9Zzb=8Y(ft3~W}+JtpALPvG*nsk(SgX^nAWo%BZO>(|U$ZfpS#I-ofm?-x0h``O=o8lC&mmBNBa-#axa`b*4SgrJWXZY`@_3{13A6{DQfr8p@pw&E)nx3q|#<amKS+?}c<x<}^VXT-<Q~XZgBDJ2>LSJnk>w3B4o|l(4gN3i?vS6w+32)SWP5sTUcZ0DwV`yKAHl6(v(7tm_7d(ZyeVbAtT^R{c=IrhGe{>-bHqSlsg2*{2F^F1z<RU;b368W#0IJsox6K@HJDWM1M~9ut9&ch)%h8=!*|uq`PG}Uxt>Y(!2I;cJEf=$6n-2_;mj17_VGV6b20)&@jfb`Pi`h#wGaXLOE~<6_hiU1kFNzuTlv1b2@OhJ>q*ITKG<NnqWeqmeO5e8AO@w4;89O_b5ICmsw4f~ok3EGz#Hhc9>kG4MdXCFNK!t|iwe3ARAb7lzShfTDIgPXFA>|N1+(>M&Mx|DEJYB1SSLv&`oA2Tv-CCUxU(c+`l{GJ1S(3^#?IFqH?>S;ai=ndo<HNv~MHKIF<|WA}OXpkB%&90bpCo#(Gd()DBukeI#+`RP589*jinW{8z5C9Z(5JH<T<p7+Z%aBxuB>9jpTU1)4&at6FJAbDih>@K(&4%-XfsB$5tCOM8M(B81KM`{g|x9=d&566*t)f{#;?sb*|US?;tskU-J@T%d8QNHmYG+CBi=Cs&=%!h+gg#=q^$QEv|PsFLCCai3xTPYDLvEWSZ&D71K>NvFL2fsH~}+iaF$Ni4Vqa?CJh%l)WPEP4!AXQp}=}WoySQ{uIav2GdS5qVqmd6haK2EZq2Nbl8DK3Y;Jx@P9){A$W&@Y)J3V%`H-!+F=J+v?s;%@i;Gj2z0io;GG#tmwwx><E1h4$N7?o2YH&WKbpDFKoV$h#z3r52O4V52iuoLmmm6HS;}G*uTN#U?dz>dM+4e7HHoWXuP==@Fwzmf>Z{DHfk&v@7YGV{CY%65es|r;1SU1h}E-E=7D_(m1=zU2`CwBahbj566CCvYp`?FDhBG$+>vx-nkobFmeQUg#Z*ot@oJ>O$5+$nb_i!w20KfE8bH)bv?U^)rI-0C#XPpH+1;7sRYDpne21+ZI@cCdV@wdE;nYOLnX?-8W*X5ur^QgBRYhhc$K4FdN4Ke)Rl#gw7!R4x<D%??e(EcR`&|DEzp(~GkfBRwzR8#p7^1ZaG{$?;Zkr^%heCTSq18eeCyWIK($obT$v#<!uq7R-?a>PDrHjCa^P-oh{0Cny*g30+<{aZh#zRZ`<@zIctRdT_lOl=B2aQs`<dMLG6XKpl&&A-ki6Wm>CDVvuqKhW=DwpqtWi)KXc><MDHJqM<T#_7FTRDs9EBb?WN4g^kvtUkU=(fIj4+VLL{fR4n$xkbykoKZ3)7$uS)3>$qdPlmxnPT;ri;9u_q&;sv~u^~dgLT9<vYu|DxDdn$-<1u@xi;PE#@GchGFlr+u{rdhK~OJnQeR(eyk+QYephZ4uQB<~hiA`Yq^D)d5zM7!`Dbsai18=e=d1^S^z69k%^7E6$MO$|)zmKP@Sk5&t-U%ITqhmHp{1nxYhAp>2(yj=ZKXP6f;&N(r)c9!sp_Rl~el&7&nj&pPwbuD@6^DtOll(E4rQbo3OTC_zWk4*Jf3Z$h&K{!MSeoSKJ)0p$l83rMbS7rdmn(kKTKCX)?>uN3m3fo>8p<Z#=Y|CvYf@MM>2uBXiAb!8i;^ZB_rsgRltNXP*g_xSkGrkdgx?A4sr<M$lG9;vFN}Iyj_TD(3Ulqj<wxdG2Nz4@=W8Qr6JQ(YVvz8QXEdRkhlDWd_xL0<G;?`MDrZ6Q_5maZ)aqi+NY=f=en&?n~sFWgnbw;8jjaaq5p|zVgty5akX&Ox%sL+@9s7+>&%7_`%WZvVyShPz#F>QpytE&4qs$77(B78X395oUOuKPmt!8#=+>R((7Syy$wMpm<1uy_HnK1bFP3IHSRDY=w89_d~N&K1No1-#AazbRc&HkBt$ymx+MaACC%9PRYCPLFM9M&|Uu*n%v7nJy5t7j_gdb#$m5ed_FUfv#CY`aA+?NT>WDkC+8K<+26i`uOjkzUzPf>;L#4|Lec}*MIr+ZR{-!*27jRN<P!r?s4n#?&agJzx(j#uRp)l9}kDW&@V3dhQ5B8a3{)#yNAhJU+sD}{_e*Q-+uGAPyhahA9H#`>t&vsBA$lna{WH@pr59%`v-ulMrfma{R`KJ`!La?LdHWa>Qlym%$_wE+9oKU#UoKR=`^S^&r*9p;@o)_s=7(YbeJm)0hzowWq@`*vIV<xCLL3&p{>Un!3qzGGPl(0&iY1%=`|KEvMiXg2u6<xJrd0`LY_U&5fN*odRK&a3TUX!xwMT7d6&qpD7K{C*<gG(XD=N)#@^r@u6xv}^t1J3;2du}nny|dLdL20Xe4N1S{AKKBbS=2T^32()4<rJ4PeEyJbca5)0Zw7@FfBP?L3$qGH@=3FNxW@55GA1si9mYO&(U&!(eAsivfd>;Bz!Fl(C%0n>!oAOFYBJc(_rn`v>^zI_t!L;#*ww?MA`Yg=XH~N8dn^TuL)r&^$Xbcgun6s(0^s*OSrRU|j7t8pMvr`;;K)<p4U{-sk7i)yJ(d?1c(8k-5^BK$FS}w!p6X1QluC@|8hz?)hWAYpN4b)uS{$d%Xyx6jOL14W>{$zV#h85P@y;67=Jjc@-DJ9qXDN^jn{uV;3IGPO=M^mU$O9E*P_ixiwP5{fas7x_A{^ee?xH;>P#y@ERjZH?@1t6vZh(xl9wK5)NDemAz}13$!E$@SS_ZkgJ+f9C~-GKOp8Edqo+To(_7nk{jKy>lYdh-0EUJmF$22@o3%2r@#FC4@!v)znr1Q%j|S|BFJ008CfDYt3`X#P0d6<ey*{)F0Mgday5hgTul3E89NdMi1s4K6sSEAd!nvt19QEqT;(ZrTDsDEKnZv-(StS0dFadti_+%pn$-HL8{O9S3Qa0Hb*LDe5LNB&I~FvLU;Yu?1cmRpzOQzw&sGS%ZTj7|NshgaK;gc~Tesd|BItL`i`)+f=tsB6>6@=q%J;i3#kfYdnwj};(ZTaM{jf7Tg-)tskThBoh}VAl3$x%0U<z8h*KPf9C1wm{YQP|r!XD=C+CxiB*hM?7)&54_BSSlSOH0*ydL|@3yfBzVjBb%BmGNWv!?Z*I^{^~5ww4=1%1SW_7i8OqPwqU9OcG2LLbKu{z!6F2e)j7dy*M{~^C7@+h9Y#j!+KQC%=_S=B#m!L54oFGl&Z#1J)1Qu+uG~e@Qud1J~AbJWBTP|1Q(@I2d8j|3RBkb=_#JRplN5~K3qMVrTsxFs7g`*HZdD%U_uC^=}ELVVRTTQfsTu@F*XwAx%2|BnOw}$X2~#~NMcc~x3)sS^Phf~J=&GE4}U(45Q^UJI9=PvL6y-V)k|9xfhpWkFB2=A5UO0+2z?&FoqDP`WRj@!DIfdht733N_Y|2edFBxnt|{M7dWXm#%1>CMiRh{BLH|$<P$+!dWmf<rs!5E|?BT6#)h%IDJRAJ!Mz`DLKHa`ee7@jYacN4Ua?MWQR~CN1Lj#OkURyDbH~s)06BG#+%u&6zM09e}bLQ#sI_C_CZJ3?!)sB?iJdDbg+X_O~R*e3OZ9wsyVWNzP8-2?~l)Sc_S!+eT#;y3TKuZTTx6YbU&Hzx+zBa9FiBUx@j<k=KvOG)NMyzvmMD7ZpGrjkC3Je;r0;E&Fh}nt`t_+?VdH;Nj-w*00i0>HA@VTcX41tno?VX9V^3XnnJuyJe+`S9NfSt}M%3D1WLn&rqXY>pd<S<ygD=UVw7d2n=ps!I*NE*GYP1Y}37WIbP%aD7ia6)DXut!|{-UO+*RSihJo#1<Ca|GPR7UJ&<E?;J*qk}6Gw?mh)`Fj$CC%cu#&*0K1RWq`!S_rVDBTFG=_jDizY7%|&KC<-6y__m9O`M;xP$-HNe9DaPv*l$*%0H{O>Z$1hi-sW=r?Ukjnn~?P8=a+~a&(<fp(vjo2r?oCMp5H?Jq9xkJr1g1%@`!LNHP9l%R;@wyE*1{RSN1;zEX)Q^3uM6*4S&VlLPn_;x4bJWG3&S@&#-P3oIn6E7z%SVb;!=pjqZug;#@VH)H|N!S|dQu@mK%!pj2233TZ8y7HPY&i|y(ooekl&xUL&IKNNL;)i;*wi$K<e-VCYrv$r-zZ5fWKb>l6mVl}x`fq}SL}Ui=!&ZGSZa5GWg20953!TH&=ekJ$<gD;AF@TIQRMpPA96h4xg+8$967EHie)N9&C*OSd0}L>0>rgrIy4DkOIO|lJ$3U4ju8nZ56Nz|7Gvi&qy~{cvaDM{GFDjS<r`_4)eVJ-h1|v>@Y8ha)kK9G2M=k-04`ClwLUQMif<uu;s-2DoN?L`dVMB@5!))x+&?hlzS$LcKnsMWeCKrdO^2GmIjgo~*mCoryS8PKF7~2oGSu_+(lM6sGT!$a3(h0)5uVps0Np5fdX>EsXQUqqXk(W#L<v#t6+qpKjw(6E{Imq)L$JW+M35--STe2&5{^(L<8C8nDRL-ODT9eEP>>vaiO;d1sJKUdoLB8*NYV{o0UATeV+y$9QoI{HWndx0CnYQ~1!MHpAfet^a)%{HHWfd);PDG!>1%gNGq<TJQ96!q#hk+q_^-RrmOp~@KmgL9h^{B3PD-bIt24;axnd$WTum&@LC1h+}<1u-I{79`<Y+oCA0^^5<IU4nv)Y8(HKv-MM&zM6ld{nv>xbNg^zs6nb>D5*cqX}M`{6O}{BsuJOE0}CwHW&HMDFp~BX^gp0l-`nynv6Mnc)501dn3J!g4h>h4j>qkzVbi-5u+R!B*d+N);u_etTxN@yR2k`=_8A1OkaIH$?0X9$)ldl<fhhJx_()+ZWI%#u2C(A8xf4H3HLrk#zBEru{YD!%y_FmJa$!=xV*;InIKgt_*}U=D}5{Gc@5r(c5hgU7DlU|Jl`}ya=ohO#9D(RMG;}p5&p@~4I6Fl>$uS_W!F+WcM_n7Grk2Rc?^UXJKG20Ad9_eJrCy1It)@VY>FO~<N{Cw?-Cv|H=*9mEI=)~rtJ8SjLJ|D3y5l^o@63Fc~@2m^qq7zZ7_^hXc1D-d2cW`6yQtW$_C9;qY>SOyctRkfUSZ9?qzUtRN7ViESAo8MZ(|NL)9L<5P3Y$qTV~v1@-J7J3Hy!_)g-PV|fZpA%d`b-aWP@wFNcib#M_nOD?+e3^aaO+VWnC5*eSEf+f%j`uQQBgABFr;;$7#$3<--uJ8$-0el3P6-P<!TWIsXo$iJngtJFRFUcE`S+)y?2l-MP8!Wyq4+;w%4eT}f>B5f<FbF;dZWP>jlt-e8^No{w7bJC=iaLvnnR!)a)|w9@)tHuMh<DstC8(ZaW07sac(YIts~~5(89?bJs}sQZQRXZ{=ERuK7e)o{1bLDY(faTVuh*cyhBK?ywnPF$s`X(-9)~P8DT)_2!S1o+ff<Xslo{o8$27$0vR7aV#*(XSXh&6Nqb2MNGQGTi$<d`1!(PYbwr_{axvd;NeM<nJHXda6s^{RG;n5veG`m*WYZO&;^QU%zETG)hXs6-yrm8Tn*G>gxQ)4i|^a{-MRI{=+IiYba6O>C~0jr3+`o%ivk8i=M^zs&^%m@dOD*-cXA5u0R&JaiJ(_Vuyw4Yec3me~bTIlG3Y`mQ%)*o$mQv^fh6?U~6H+_ufqWeaL7ovj#Wf!*f)c~Q8C;wg+-D>BGhYcrr;AzkD11A}OKTa+1Zex&1fvKlR<oicosf#7CtQkr{|5~HMtt}WEhYsi^nw@*PbVKmMX0{r$h}LknIPV_|l@6Acaj`HrE24|@{?V7l;cYVwNe4&J*$ZD8$AdY*91p4bh$lfYM(pDLGAZ?Ut9yd1{QdNbrryQMI0JYu?6lZ=oT!)ulX)sR694(bw||1Pp=DR}L58DWpC>EfuL@$@SznxtI0x|wNkd&&74!U}e@3nm#5CqGizrJ#3u7BH8dJGC1f0mQ|4waXfL7BU&^i=h_#!bf0N2z*r7TOY!cOl-O8cf^P|@aRJi(JJd|F6k{SF{TlvNUs;o@Q+47Zxp+{l`wT&j>+o3t~#k!8xC)U48$+GAzzH_Aex>@2#J%>JAP#l-vj@wf7%Y$kDp?WH>I=&$7aaX!e*`n!bF;sXydIw<aJ)vC$Ux7ZkrM9iK?0ddp1m8gc5^{lb*Ygd?;hXJ-ifCOtpeDuIrx_+I<m+*-a4<j<AdFxM4l$8V_AV~y+nj#-vHBYXqfEWU~w9nNi1E5L@KI|Vy2Ae#)EevESYo?D|o(l;HBJ-=rTk#b*ohln>pOmX%1UZo6Hv6|j4kl@*ZnXn|>OK-``VqK6|7G!v1>B)H$Kfu0&Kk?iy5%b<$2^#Kgj`YMCV0&?#w6ai_0$kr;OX}`NvE8YydBvhW0vZ|{mk83Yw2^_i39~1NV32o2EPpA7e2jh%s~c+yx$GX)!wAZ7{zdCDH$*1ZJ}r<j4f!tnn~QCi+9`4f_WQ`@Sng-{j&N@7(VqVgGd3;oIP`~D8Oqz+r)MFKC6>OHqzA~dMhX!c^gm3<NS?N4o-ZqMGGjWHdZNWNw9O5EU?&!y{Q+WHl~RTIISSvP2lG2MEFdR+!ihcMrH!=LcWpCResNxVLTjfp@v0GY&_#q6iZ1S67KtdSJBzGkVpoAm<1Vjg~TUj*PV~*u+9itMHJ*jyv%(ljYbeYC$L7d@%61Z@`H{Clh5S$;;oLx3uDRAi3X25zy<?c6YKFg&_hew=mktxoFdJ52O{CLo_>hh#xb>yDnq$SO@x=?<N*6da3OCDQIHqemCfT9(s?scE?M;3B*2h|MGfLj7YmZ(Ox}!+a%Cvhm2Of8gKJ2M+M3F!^N7?(TVlDqHHRU^Do=Bitvxy;KGELI>eh*E5!Em+84AB&3Y}W@&(e`0H5Hwh+sfEA(c|=ZCO~oxg~&1rwp4Q*OD2h%^knmUja&kcXPw>1;A0?P=`cE%q`Jl^NGd|#=5p?=1$CDK=64`*xx2cvmH|G{nMg=LGBy>ClR^SnPL?gobjL9c+(lg-U0gA9iAlbrG(O6U>tt&DC#JbSiOtEn73KXSq2Gh<*mzm;cjS{c)6<v7V9G|X%johbD1*!;23>Tqrd^YKC9xf0xiM2d9ms*jx}sJiT)YY3*D|JgT2h1r@?hjf@kS|Hq_JVZC~JnhHeP;<ha>%jgm-bYgj=b!eln9F=FDbEo4>$rcPL9#mz2(<mgGozF>s^>z#c6#yJ}x1bl6e_EPH<LfmgdcHmh><0$7TxF*YnIfZ2$aNO3_YWLFhzg;%7X*c)&wYbB6d5`i;{i=ya28qCMpiCl5g+s7jk09bUcw_mdq4n&ex4b814dPlsQ?}9%S`{ZT$H)vj9t#)Z%2IP2Sm7FTGr3`WH=$Vs|+46g`OahDS0T@2g>JoqJzF3;U^<uR4a-?1_OB8g|WIkkv?eG^p#il}2hO~&v08pleNzM7{EysiGu!Dg`UA|l+*T&0#DOkv`c#u~KTn$|t<&1#Y-h`!>=|Y=E;FwRI!O{vg%!yDpkNV?5fck|fw&tTE-dj=YwUM063I<$ko75JX2=M#y+Y&ugmSLHm65hI6y>0g1I95uVjLMbEAxJVY4apID3jn;hgN1N`jp$FUVm0RuMJw!3;Kvwu&U>r46A@2t=SrjIRKSTE=jv7MZ(N&=RglW!d3nQCLp>$aMdC%nGzTle;W>1%U^Q;TN0Y~~rZ&*o*=QCtDUl1fn1(kpnn|k~Uk-ngOHIY+rTWH<0Aq~*q#@0bj@M#h`YYu@|HX?H5v{7K{&H2eD4x%}X>gRZ#UP}j8JT50_NE47Hp}BM8FA@|Az6I*+Iu)U2g|s|jB9s98#IetraK+VEX#Dk85vu0yr>Qhv_zCrX)IeZMF?TvbkXCn!2-H<h()KazzUYqNxW@9-IhE;DTav_6BK&5t>(H^vu4z@Y)XrUZJJ>ggFP_xiq}AKKqo&oD%>Sr3biPrl2>?F;ZObBZ|$4}JoUBMmxAk~3(i$@S9lDtXpqHG{-~=4Nw>Gq*vd=<&(k$4AW`Z>k}W(QvJ-VyT&hOyo16TXiiS-=jfuS!Q<z~1^7;9*H+n}3??`JYC~P@BIe0%)UBC2>$!!7hjf~<&>u=!MJqn8Kc`*nSi|j^ck4LjY`$pIrjS^8~8PUD9-x&>P>sVJx9L(C*#eT6`j(t2rf~rJ9ilh6Dx<Q=6C}(ax&-o2>^<8pbtLlx{NmA>b`(ipD2O+N<e9k4^O&n;!K|z8#sxgA|-h;v@hoXk(xspaajJRaL?3y4LIt^j3iK$RsQwD2o8j>ZPmpRj#nQJ#qB8W+V8BV5b^&t+A5%L&SR9r?H&Ty`-WtqJ$M{`EnXx`B_=`k5?N+8ByefZMS=uzl@^mOQH8Nzh+=4UKi@Jvp{TsVdHBkj~}r^S)ngS&tLxWe_G&N?SVBI9geG@5-V&y}}l2I}(^xgvqqQa)m9-_eF|xpE`!L2PWJDuWOSW6o#CLow0cY@LS00ntUgmS{WT%U%F;lyRSQvceB4(oq|aE2!#I@fYOkECtFFpft%F*|k?GqSqM~X_Q;m8du6Daho?|!khDStqcU&=1<Avnw)+a`LCe0NZxa8GaZSLxHgk<DET#tTfg^)QXzykAhT9XPc%Cwd#3{$y1&)T30*|`-R?ECI@&5~BY`8pV`ee2v%DM7Tysw=Z1-3o{zY))9E6F@gO;bGsSI|t@9*5!1m4e?&2_P>_m@s2%XPja#jGndwod&oiv;FS3s(=9^ZbXIOPQ@Nws;kSt}|cOH$wUT1<|pdh9!tQVyvt5oU&IVKh?b9mEe>g_@>!-au;W>Mo!K1<7`J0t6Z6)k8%0*deNg<vQ}u4)xa7)<An7Vo$4bTYbCSxi*DHQmYeRA9acf|_mG!PlvfL_(!~ujTO3JnHt|p~jt)_Hcfh<6Y8v0#5`837XPk3Asv7ho0Octql}M^T1$)AW!v2qW12D(R<=3;9tG8=6Ws2a+RYX9Jlj47UG$gIM5db=bD+r``@ncWj%qOsUot3oU1fTH|Je}oph}MB$`%~4C5};br6tZp<YXq3iCKFg8a!Ty}7wxkoXWs$UfIh9wvp+YZ0c~Yb!c>;WCK-<OWoVxODfM5tb#?_-97X04Us8AcksGZ;6iwgCCAg`ZC(qp(LZAXU4d<;Lz!*%)=_5#QV_qC8FgL3fF%K<SMQ(q=aNAlVwUu$Pn?Q7n<f}RW+}b5A4gquQ!l?B`_hiR#Xbm7Y&K1+|GY}41^fn`3VEP2$pR}UFcr_)BS`|P+Ni64oqT(58Wp@>j0HxcG{E-Eg4EwsP>T!lN6`+G!qt)iI?*NbI9N}#TuWL*o*3RCz?@@hJqFV2J%K@C4x>)*R{yxde`^gf@h(Wj<4iANfh8@)px;VmQ3zkD1vsKD{goKl07^=q87IC$R6^1v;_Hq0|jM)kwc_rJHme@Lid<ac&{Am4Jl`Mc!xnkOuTqn&fm^2rc8kMVf0UKf-2^bJ+r!>thD2EQ>(7ZjFl1@E~;J_%$D0P7}fj3__yoV=rQV^yIfClS3yr8Ax@}ue|c5#8F0VTb)DJ>W_cZ=7sy>2G8T4Tcb&{pGTNGgkjOh3+!myfsGHikGq?d3T-D$oE7%(5kurLc!WArfijGW^LI0cdKF1#n?KlWW46vTq3q)b<dI^9aioyf-(;eZZ8S-dPmt%qjljdsA;|0>G-nDQaR50^cN#fPd98)2cb~=Gx6$YWgc-EO6&m+xSa1n=!_tYlUJXIC!X=BHvh;Npzjs^HNm5*O`)2b_JK97Am5YbSEXU3n`5qZ$zRT2(l;4Yuw2ox;&^>o8N345HesCd9~W<2SRP03cC7|43uca+m8H>PZ)*y-H0(uU(T)2vGXz#zRS9?<M{29($PR6{+WJLZ<^cLA?oV5JGdDz2sU1&TEeQ0ZOR0xX{eax>e9wp3!BWPiRZyEevlrq9yEQS7_=1IW01b-xN<8KkM>-C42^D6bjcAQTijYUJnb{+E*B@GKqk#&`Q0sdf-RcjJ01GYE{n=OC<WlPFD;xFY(Zpj=bsPXe*DhrK}BT^p@znU8EF_v2)?!~&ZK-1KnN_{;w!nfWqGIHz7SN>0K`Q^$kFAfh@G#%t#LeaO}Nc%(>i>Xoix=P7f->AzV3$g(0bgP@?ezA8S)A0KukdKcuj`}tN+TrVWuW#eBFY{#FEJSMAcHwrxg=h5$tzj6eo6}TZFBO(+&nlMI0N~hR|9M{}A_c3{m@lYAhjby46e3mQ}-pjhAldw~Wd4X%vqqvj)qoE?5#-i!t^qnjko1%Q=aDgCncn*J+_0K0=dz=+fUTQJk&_kw6$+;hsW2rrvb6ju;pY2$%~$Hp*z#<I4zyh#Ty-1Gu-KfLO<uZ^Wbg2eNpP&BbeoSz4Dz4wbR9MXqB`_M^RJHQ9bkG;h5BkqO{2?S56=L7(Y$>=X0AmEu$QSWM1HEuUA=I6DvA(&7fj+mKmTIBk5i)rc|l5*}K*2}D|}g$4%_-Oacm8+={gme@)P!4Q>5QR&+fghzU7iKu{ijF?E4bGq^<&p#lV4tpbqtL+*BwsI_7#ex7Kkh7xYLVe6LBS4dPw^sOC#GJ;f)s73q`DG8!AyI#BTN`a9%Z)MkU{nztQZEoa%mRP<M;+zby<Q8zkAiCK(Rq#z77=bX-)7s{5&sa&tBB?0|7B}pJyJ!kR5jT<;))r%8j5AiB-XA_%xC~U9x4c%M<JVG3M)nUSe3KwS6U2uJ&iFTa~A$fyxV^kDL&nYMS|P{D%fN|6&n6VT1}gJc@!U3<Vf0`lW-D{j)1>@x#2@y`NrFJCH=eDva0)Th&*RD?VgVKoKRm9)sBaf3-B12(vh#r4>9GqLMb*qi8^r4QR4zC5Y$n0+!b~l0RxkLmnffEjD5{-16A=|U#Ctv)^hPlw(O0(+r0|oDp7C&Q-){Y=M)J#&{^%vC4dZ&z)VWC4KM#?vN9b*kj>QAqjqKFp;@0J%E>Zc#Ewx%(1vundnZcLS^YOKO^?8@UZta2bBwhE049gY)o7wN$=2^%!gQ8+UVOt`Ah6a?6rbAdEL8C`V9o^mfZ3T|b2UwIw)07RC@9Wp4{mPA8t*X^#o852ApW5>7dTdifSlRmnL$xcRO<I)K)`(6cQpg&XviI_jEjS4!o19EmoBIzMCNF#fDqitHgO#w8?{v>`T2GA$U@BIF>;@Wg!`JteIiTO@n2PS*T6Jp?mF4q+{}?RJe^9OJS=XUOjr=G^XEdepz>5V&@Kj?TQ%q`NEdAIr40sUWtb_KY4FPMYOT<JzCfK8Q@W}8U2zc+M9S(4pk#C(+C|(qdbOnMeD13WZ?nl$+@%IVlkMM1<-qLXs#BWoY%Nuf?pf0tFZ@&&MA|#5`3+hqh(F?5QrpL1(~TR$0&LGfUh5KZfQO^D(qw~J+vMDRx%xE}H57&FrAvONae<>XXwv5~YPZI&*2NK!^jWoaD!%7Z>S#gK-k)YH0Jq`gtg3v4A$w=>ossf_YlJHr31IUN=xYtfCBka(E_>I+*CiX0fw3eyVlmVeepo~XYj4UF>rNmURpmQchPm=p_KeVjbQe=bk#n4aO~J`=5iq3KC$EZ{5aU`TN7*_GUm5@zv&tJbb!tZ(Pr8M%(3SxXYZ2dKT@|%n(CmkHK<N>BTyb&I>S+orIU{b1t~9JU9Jrv|E;yhwwAoD1ELXucC6!SELro*>ImoQA#GP2oU>`Ml=@cmIWv%U#g24FvX)Kw$iM!F*bue~hX0`ZjVlLW~;=6w=X>?B7M}?Hs((ZOn$Lxh~V^NzlRC6j+fzsy%$%VP$jcC?+UusLXY%whQvDvNcK<tH<Ie4_N9$Jt5=0KagM`0-tlOC&GcP@aQ^0Q3ctNE>VzSj?HHjt$`6@dbH8FVs6(w{Kx$dGc@KC7P$vZiFOsK>*lfRC@$xN7;)z^vmvzSPNzkf*>e`3|akgWK`+{O_~ZyNaPzpzkxlnShgU@^quYwPsWv^AVJ65m7GY1zzWZZ{O+WM!x|#0yeIuvDNj&*ISkCy87u$93|f5`YKf!8&qqPoUamcz3#NJY@B7xLwk8dU`6juaass4q1MRvJD;luBQW?)%c@loxYFyLLB*fe$M+w9c<IUq!fRZI+G|R`t#lic6tmRa(l0kuL3@Z-%%myQCoqv(UuvPZc5P!{FL&JY^3qPW@D*K(O>HJiqH%u39K7-w&-+UK>Fk$)GM;1JFjtvN`aTkB&Dp!~|LEcrLoJ<<>>!c`N+qI3A-Q(YOj0B*5`bEF!Ot_t$<AiZq~6`c1(zc&vD|GlTK%wQ)nVBTV_dFl$2Jrg53SW-X~!DcW(@f|dm9ht@E53;5oXp2oM2S#1P;^E5n>cGh&dh0<1HllyjfAAsYk{fJNurp9@`dBK9;r(Z=xYP%MjYBOTa;m=LK8go5!A9AmY|vBjttZHT}ya245lMckO<U4gwu-AeNYb&Q9ZWdMI#-C+Q2;IMvEkr|Ty0DpeH^Y=eP3U40N=(X8Q>^)XzTnaX4BAxW_B{YqrL`r>1@mI)N^cINfKs3Yh5$IL0{Fmoe%w=)4bw;oED3$870d+xPI=`w3KuzNS2HK9+Z`xbfL-AT`ulnWZi$kjoNU@`b_%sbrj^Ti9_P*l)kQaW9?1u?~FC}Q$OBh!{vTR;PkzmPW8Yj5~R1`Bud?ze2X?D@rVp$FZXeq;XVM4x766yXSY%s`(-ZPvC(<OL+_y#~#iad;52ZQD^m^rm}GlsB?#jx~eaWB|Tg`~qjefum8xm>a{HvTp6n8aZib(V_hf`?uIW&s<Ef-h}57O_M9VZ}JRIL6JmQ3{76KdTXC&)|E*V=Q+sdano;W@*GQ0rA|j(vML=f+3Fm#bT&Dh2S>oTIGfoEjrcTELZfBr$?`m7pKUh74$Q6tScBv#75BledT`RkhnXJBrgn~H;+QXp@w$iWlN<ssYIS3=bdU3tF5Aw>%-ffpA<9{`+*9}9)2w&sK*hg>quRZ$m)QQwtPvK-{;}Sh>s?f`sZsVdAaJdz`@{wzk~Epkv4s8K@#t~tV8n!(=64a$iSu2{erhldg?temq35vd1xMxHXHl?*+jKwZqs+Wnz-$suy4A*>A5Mnip6QTG#Z%*)06HwvGM4YOw!Di?&DXrKJ_4oQM0{p)u9UCK+Yt*aY!KY<|3UUOIjIckr}CX(ZaA0Motll^Q^(qSDM2;8HcKJW%L2ZE19MFZ$Jf6c?=^QC=s6sd#$l=%*280FnKZk7DIRpqud6rkYZho86=5>oVe@zk3um7sVc;ordELa&*%?$x(X(5&HWk^w<H7ZgP)-;KTcNA5w2bVnfLa_~<9A1u%d~o##AM|F4E?FVZZ}o#sLQjI>f`6=M2~0YG$P1iR5puS{nXWZ3mdIP0u>~(0j<hKqjrqEsi^aZAy0e8!UTr{(_=W+*Kx-NDhYJqxW+@xJS=L2$O~{MYpCV63)v?d>l43XsDcPro0A;}9*Hz`A5#)VNpt;R8bZ6&IJPcqEvvQzR1Qtsb7bJ04KOd)=W_bsY0bf8FVe>7>J-IF)8f>gs@?2B9n@kfGViP6wC1IUEg~m-T#_b(@xi8v?t8RZlkLbbS1>PEzeKBf+Yu)0)<9+XSt6IfThkcjY3va69L+~vU0(W}4OSLqjC6~Dku8%Jby5g5Q^A%38R}3_8c_m=lh}JS=Dc%;L2Bt0S;$5&V9b47S5?+AT>=!gy)r_*;;<~`))&D$p%8?l2WODa-)3?0&SO(gl@aFs+MYs8O{p5+J>Dlk#HW@7k1`~riAx3X*7yqGe126cKiKXL=_WB(e2jVX#q(gSCr(;YM6&z`_ekb)tmEF@CDL1GJ(>3f6B1Ns%yI7GDQp9gX{Z2UR~ZHT?u>Csy1{DAOKUfwTBmfz(>$7XaiK5oF`LXNl`%7@>%GT+v1pfgVsIDdT4=qaMHBx@l?!lJ#1F?hv_@jVwGw`?c1;QU7uQ18+MTbF)ofWT-axF`lJ%tm#7LW5F6FjMx|e}1261EoZ*%%@N{N(B<w-^Fo!^~YSnUHxJN>QGV;d@yIXy7;LCasJ3k2<j9YstXDQZWeI{RESP+LR#JOXG)r~J_H5MRJ^e|8&t{P+JKpFB>~")).decode("utf-8"))

_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")
_LIQUIDATION = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
_SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
_PRICE_BASE = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100,
}
_STATE = {
    0: {"last": -1, "regime": "opening", "first_shop": None, "recovery": {}, "dues": {}, "calls": 0},
    1: {"last": -1, "regime": "opening", "first_shop": None, "recovery": {}, "dues": {}, "calls": 0},
}
_STATS = {
    0: {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0},
    1: {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    return int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs, seat=None):
    target = _seat(obs) if seat is None else int(seat)
    farms = list(_get(obs, "farms", []) or [])
    return farms[target] if target < len(farms) else {}


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or []) if order],
    }


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


def _align(action, obs):
    action = _copy_action(action)
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    hands = list(action["hands"])
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    action["hands"] = hands[:expected]
    action["market"] = action["market"][:10]
    return action


def _reset_state(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, regime="opening", first_shop=None, recovery={}, dues={}, calls=0)
        _STATS[seat] = {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0}
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    return state


def _route(obs, state):
    step = _step(obs)
    shops = [str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])]
    if state.get("first_shop") is None and shops:
        state["first_shop"] = shops[0]
    if not _HIERARCHY:
        route = "dairy" if step >= 216 else "default"
    elif state.get("first_shop") == "YARN_STORE" and step >= 72:
        route = "yarn"
    elif "SMOOTHIE_SHOP" in shops and step >= 260 and not state.get("recovery"):
        route = "smoothie"
    elif step >= 216:
        route = "dairy"
    else:
        route = "default"
    state["regime"] = route
    stats = _STATS[_seat(obs)]["routes"]
    stats[route] = int(stats.get(route, 0)) + 1
    return route


def _planned_action(obs, route):
    step = min(max(_step(obs), 0), 718)
    return _align(_PLANS[route][step], obs)


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
    inventories = _inventories(obs, len(positions))
    inventory = inventories[actor]
    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    seeds = dict(_get(private, "seeds", {}) or {})
    op = str(order[0])
    if op in _MOVES:
        dx, dy = _MOVES[op]
        x, y = position[0] + dx, position[1] + dy
        rows = list(_get(_farm(obs), "tiles", []) or [])
        # The engine allows units to traverse a locked quadrant; only service
        # actions are land-gated. Rejecting movement onto LOCKED tiles breaks
        # valid route corridors before the next BUY_LAND settles.
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


def _recovery_order(obs, actor, transaction):
    step = _step(obs)
    if step > int(transaction.get("expires", step)):
        return None, True
    position = _positions(obs)[actor]
    target = tuple(transaction.get("target", position))
    order = list(transaction.get("order") or ["PASS"])
    op = str(order[0])
    inventory = _inventories(obs, len(_positions(obs)))[actor]
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    need = "WHEAT" if op == "FEED" else order[1] if op == "PLACE" and len(order) > 1 else None
    if need and int(inventory.get(need, 0) or 0) <= 0:
        if position in _ACCESS and int(shed.get(need, 0) or 0) > 0:
            return ["PICKUP", need, min(6, int(shed.get(need, 0) or 0))], False
        access = _nearest_access(position)
        return _toward(position, access), False
    if position != target:
        return _toward(position, target), False
    if _valid_unit(obs, actor, order):
        return order, True
    return None, False


def _event_router(obs, action, state):
    action = _align(action, obs)
    positions = _positions(obs)
    orders = [action["farmer"], *action["hands"]]
    recovery = state.setdefault("recovery", {})
    stats = _STATS[_seat(obs)]
    step = _step(obs)

    for actor in range(len(orders)):
        key = str(actor)
        if key in recovery:
            replacement, finished = _recovery_order(obs, actor, recovery[key])
            if replacement is not None:
                orders[actor] = replacement
            if finished:
                recovery.pop(key, None)

    for actor, order in enumerate(list(orders)):
        if _valid_unit(obs, actor, order):
            continue
        op = str(order[0]) if order else "PASS"
        tile = _tile(obs, positions[actor])
        if _HIERARCHY and op in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"} and isinstance(tile, dict) and tile.get("kind") == "WEED":
            recovery[str(actor)] = {"order": list(order), "target": list(positions[actor]), "expires": step + 10}
            orders[actor] = ["DIG"]
            stats["weed"] += 1
        elif _HIERARCHY and op in {"FEED", "PLACE"}:
            recovery[str(actor)] = {"order": list(order), "target": list(positions[actor]), "expires": min(step + 12, (step // 24) * 24 + 23)}
            replacement, _ = _recovery_order(obs, actor, recovery[str(actor)])
            orders[actor] = replacement or ["PASS"]
            stats["inventory"] += 1
        else:
            orders[actor] = ["PASS"]
            stats["fallback"] += 1

    remaining = {key: max(0, int(value or 0)) for key, value in dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {}).items()}
    for actor, order in enumerate(list(orders)):
        if len(order) >= 3 and order[0] == "PICKUP":
            item, requested = str(order[1]), max(0, int(order[2] or 0))
            quantity = min(requested, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - quantity)
            orders[actor] = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]

    if _HIERARCHY:
        for actor, order in enumerate(list(orders)):
            if order and order[0] == "PASS" and _valid_unit(obs, actor, ["COLLECT_FERTILIZER"]):
                orders[actor] = ["COLLECT_FERTILIZER"]
                stats["fertilizer"] += 1

    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def _public_signature(farm):
    counts = {key: 0 for key in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "COW", "SHEEP", "GOOSE", "PASTURE", "COOP")}
    for row in list(_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            for field in ("crop", "animal", "kind"):
                value = tile.get(field)
                if isinstance(value, dict):
                    value = value.get("kind")
                value = str(value or "").upper()
                if value in counts:
                    counts[value] += 1
                    break
    return (len(list(_get(farm, "hands", []) or [])), tuple(counts[key] for key in sorted(counts)))


def _rival_distance(obs):
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) < 2:
        return 10 ** 9
    left, right = _public_signature(farms[0]), _public_signature(farms[1])
    return abs(left[0] - right[0]) + sum(abs(a - b) for a, b in zip(left[1], right[1]))


def _projected_shed(obs, action):
    private = _get(obs, "private", {}) or {}
    projected = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    orders = [action["farmer"], *action["hands"]]
    for actor, order in enumerate(orders):
        if actor >= len(positions) or positions[actor] not in _ACCESS:
            continue
        inventory = inventories[actor]
        if order and order[0] == "DROP":
            deposits = list(inventory.items())
        elif order and order[0] == "PLACE" and len(order) > 1:
            deposits = [(str(order[1]), int(order[2] or 1) if len(order) > 2 else 1)]
        else:
            continue
        for item, requested in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(requested or 0)), max(0, int(inventory.get(item, 0) or 0)), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def _town_demand(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 == 0:
        shops = list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
        for shop in shops:
            products = _SHOP_PRODUCTS.get(str(shop), ())
            if item in products:
                demand += 2 if len(products) == 1 else 1
    return demand


def _repay_market(action, state, step):
    dues = state.setdefault("dues", {})
    due = dict(dues.pop(str(step), {}) or {})
    if not due:
        return action
    market = []
    for raw in action["market"]:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and due.get(str(order[1]), 0) > 0:
            item = str(order[1])
            cut = min(max(0, int(order[2] or 0)), int(due[item]))
            order[2] = max(0, int(order[2] or 0) - cut)
            due[item] -= cut
            if order[2] <= 0:
                continue
        market.append(order)
    action["market"] = market
    return action


def _future_sell(route, step):
    if step + 1 > 718:
        return {}
    result = {}
    for order in _PLANS[route][step + 1].get("market", []) or []:
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in _PREMIUM:
            item = str(order[1])
            result[item] = result.get(item, 0) + max(0, int(order[2] or 0))
    return result


def _market_router(obs, action, state, route):
    if not _HIERARCHY:
        action["market"] = [list(order) for order in action["market"][:10]]
        return action
    step = _step(obs)
    action = _repay_market(action, state, step)
    market = [list(order) for order in action["market"] if order]
    projected = _projected_shed(obs, action)
    planned_sell = {}
    for order in market:
        if len(order) >= 3 and order[0] == "SELL":
            item = str(order[1])
            planned_sell[item] = planned_sell.get(item, 0) + max(0, int(order[2] or 0))

    moved = {}
    if 120 <= step < 680 and _rival_distance(obs) <= 6 and len(market) < 10:
        for item, future in _future_sell(route, step).items():
            if _town_demand(obs, item, step) > 0:
                continue
            available = max(0, int(projected.get(item, 0) or 0) - int(planned_sell.get(item, 0)))
            quantity = min(available, int(future), 30)
            if quantity <= 0:
                continue
            existing = next((order for order in market if len(order) >= 3 and order[0] == "SELL" and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = int(existing[2]) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
            else:
                break
            moved[item] = moved.get(item, 0) + quantity
            planned_sell[item] = planned_sell.get(item, 0) + quantity
    if moved:
        state.setdefault("dues", {})[str(step + 1)] = moved

    if step >= 715:
        for item in _LIQUIDATION:
            extra = max(0, int(projected.get(item, 0) or 0) - int(planned_sell.get(item, 0)))
            if extra <= 0:
                continue
            existing = next((order for order in market if len(order) >= 3 and order[0] == "SELL" and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = int(existing[2]) + extra
            elif len(market) < 10:
                market.append(["SELL", item, extra])
            planned_sell[item] = planned_sell.get(item, 0) + extra

    merged = []
    for order in market:
        if len(order) >= 3 and order[0] in {"SELL", "BUY_PRODUCT"}:
            same = next((prior for prior in merged if len(prior) >= 3 and prior[0] == order[0] and str(prior[1]) == str(order[1])), None)
            if same is not None:
                same[2] = max(0, int(same[2] or 0)) + max(0, int(order[2] or 0))
                continue
        merged.append(order)
    market = merged[:10]

    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    sells = [order for order in market if len(order) >= 3 and order[0] == "SELL"]
    fixed = [order for order in market if not (len(order) >= 3 and order[0] == "SELL")]
    sells.sort(key=lambda order: (-float(prices.get(str(order[1]), _PRICE_BASE.get(str(order[1]), 1)) or 0), _PRODUCTS.index(str(order[1])) if str(order[1]) in _PRODUCTS else 99))
    market = (sells + fixed)[:10]

    safe = {"HIRE", "BUY_LAND", "BUY_SEED"}
    for index in range(1, len(market)):
        previous, current = market[index - 1], market[index]
        if previous and str(previous[0]) in safe and len(current) >= 3 and current[0] == "BUY_PRODUCT" and str(current[1]) in {"WHEAT", "FERTILIZER"} and int(current[2] or 0) > 0:
            market[index - 1], market[index] = current, previous
            break

    action["market"] = market[:10]
    _STATS[_seat(obs)]["market"] += int(action["market"] != _copy_action(_PLANS[route][min(step, 718)])["market"])
    return action


def _safe_fallback(obs):
    hands = list(_get(_farm(obs), "hands", []) or [])
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def model_status():
    return {
        "kind": "v86_multiscale_demand_task_moe",
        "model_id": "v86_multiscale_demand_task_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "public-shop-multiscale-state-router",
        "production_experts": ["wool", "dairy_fruit", "smoothie"],
        "event_experts": ["on_plan", "weed_recovery", "inventory_recovery", "fertilizer_byproduct"],
        "market_experts": ["financing", "rival_supply", "terminal_conversion"],
        "stats": copy.deepcopy(_STATS),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        state = _reset_state(obs)
        route = _route(obs, state)
        action = _planned_action(obs, route)
        action = _event_router(obs, action, state)
        action = _market_router(obs, action, state, route)
        return _align(action, obs)
    except Exception:
        _STATS[_seat(obs)]["fallback"] += 1
        return _safe_fallback(obs)
