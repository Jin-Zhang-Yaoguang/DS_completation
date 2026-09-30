"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)UlE!(oQlck<m7>!$K$uTAaVPGH=1PCUJNp?a0_ekpQ_wKFxBhMkLUMmK&(o?^WTOTBgJUnFm`M;n1>#u+R+h70w<R8BH^OHBv-@bkF{>v|({M)bp@h|`R@lPNB^S59B{_lVNuaE!x^OGNb{?lLH+}^zW`Ng{@AKv=q$Lr@GUwr-a{rms<@{8S%{d9Bt?#KMs-d?|cJ^aj<U)(+9?e+D`?OV?d@BH!l_03NoUR-_k>8&4M-CjQ_z54iL&wqOL$LF8M@Z#o|5C41x@4Wr-`ufeM_YQOX<@)Wr{S-ee;;R>b`1#GlPk#EnhmUO*W&6kB8)}uVym4$Eb$-CzT*jenUjFd&tJg38@<9;Z{rqvA%>9QUy?Ooor+4Rl8U{B!W<SWgUmZt=llbtI7uSWAd)QrX4!=BqcYS-<-`yj_?ZxT5cutEtJxtjByC=bpeu;atoy6U%)q~9CVWSKW%e&d-(>{O#J<6VMp8ETb=4V(jSmMhJ?)o{{8`#YA?&k|Te)loPn{DQ>z;~ZqJ*bDpVfn)`jqABwISvOe@9WmSJiNUzFT2f7HrBErn|(ri!P`h%=847G{@^bkUy6q;T2uPU__>R&?(yZS)qVKjPH;Z0+RV~!*6#d(bY-`Ha~{8JJ@3ZXne6@Fg5^BF-Cxe(C-Mbb{;2J8UT8AmEA@b*V--gjPAuTb*Y#0X$b<JR0>nmv$A|}$X8<1#((N<Ohbx=byZ6Np(*c_Lo0|ua2Yh_M&Fk0KFW&v-_t&@YUcG+x&qs%hKOuZF`clJ|o*b$8;b)P4d-L;gtIiI?<|l;L01@{6ZyTP>>65|e=ZE(-di=Cb);6Ba&t~Yk@8ypb0(r7pXOZrNb=D&`C-CNgnm>$R-rl?!52dr}FR<g=6<K*cT<Y8*)%-s^+~3;rUdZ+N|KZ|~efFOnY~V-hpE+TPg|1+=BP9II(TtPJlY4G-rW6qa-$gqD1#lE;=LaE*vU`X=sQPIy0;O$8LwSGHv=ztkwc=*I@EGg~MAC{b*bk^qAeVmJ+7;r@Bes56uecb#wJzu<Z~aR0y?%Ut`%lgsXwlExi5pvlk7)UM^rtbe6#C7h_F=>Ui|{m9V8SyBKoQ4yI0ce)-l$;XgJbOL)A2N>5((xVQ-g9?eW^k7&RSa(8UAH~>U&VzkXn;N7jd?wO1VR13f^NmT2FTm86~ur12_DtIwDp)VqC|~KEym%tM1oTkIsrS$1e}VSf`#dj+pOkph53@dvYqfQ_y@)<rL%zVLq;(uZa$IvVyLwB94S)2Ez&$k0KNmT*P#h8?wS)da$<U5h6teeLmqjO*pc`**uP6)k6@jnsL;gz7I_!Jyk>-fx~vDm>CY6k%%~f#G4(?#ICV2u_@x0BEuO1GQ~ts5Eu+7TgN6H+`2Exc`iRo@8<aj&j`Am)oFX1{U;PM#{*|=oT+-y!4v&v_t;Uw=KRm`oev9ndlMwVJ~QNZNq;bLK)V`^>V}Cf`N-`Cy?uB4{FfiDZ*Tv^kEKo8sCK~*ZTs~&$+|;YIQ{YX@*X4jyumiDz-HNVa6Qa?;mO--xRVvskbEtXbQVt+N%zg79VCu4$m0hJ{W*)*(F<to7`qaizlIQ5frMG`tadaqre5SC<lDy_=t#WKwR_7B&{Frq|KYXUx@2ld%gKLudY|%Vp8drt#)qNMH{pX^Fj3;wIP1~#+8ylReLWiRnY)|q3^VzkKxL}opX2Bx;Sfy#CfP6M+afX0pW@LeOC@RYKv)BmV%bdK8?1R^%lE22q_ey0-C%aN;Uw)R4Gr?(Y8rinG85!{o@V0&2>0*g=xp>Ue?v`NGALaQ7O`cT2e54yKO~R@4l%1Ng+eA3=jFLH_!RW<Da&sQ8<w{nO0H6YYOoCQ3Pp}LVu7|;HZ)JeVob;h84Ll=A9$YP5sJx@dA{~T@~T(xCi$r;i&=W7Xmm{CcJ7r|m*e6EEl1@T*Q%b^cYWQXpLW7p7aahiss#lGz5nB93+EWGf|}6A(&euCQ)5<GH<ZrEQ-3N*rsq4K6VDIU1FMZ;1YA&28$!hq#HVa)ks9Aq#^S+D{&I8kQ5LU$XV}qXNfMTpF}zJ&wi!;ZWJVa~hqpf*+Aq(F7Pr^fJVRk}!V#w<ma1Oj&lT)Qap)=GkA{ZxA|!O(9I~pYtkg0<XpdRi%|x`q<@1^g2WXU7t&IC2!nz8Sc&JSbL>p=t;ZMlTi0QcvW0nf<o)<KvnYsB$P(GOvyXNKF%pISFIt)NaagCzTtP#uh5$06A<eQFo(#l=cH=qQnn+=r6QNlQ?QGsI(fa6i(zj0_f9@0kdgT^S`Ml^z$UB<;YvL={E7}WC^4lqY!Idnz%3h2!H9dlD@AyK@O<`o}bMSxHrn>iF+55_KcP+i~T!7hAnmbS;NL34i+!s5in1{RvE9U?2IQAPWR%U#-Z{}3s4*BGLUZX-UGjvL?Eg&yT>9lLa1^Nn!<+_r)y(*OtI|1m~TobN2C(>OE|iPxJ>ueHg`^O1CZ`}``&PpJVEa$lS01;^9*vzu2sOj?eW?A%`VWW%ope|Mmc0+6>1JJ9iH8pJA|cP(J)WCO#6Rg|#si_;S+vFZi8kp_I`E$cWdD}(6niWqXNGXRkw+Oed{OHen&5R@A%Mug4{x3$UCOXlL1Flh12!hU$sqV)NzYN1@BuY4)S;TQTGw9sEkbGO8j5EfeW;ro@;BuZUXLOB<B%8USs=kXf0+aiiEA4AC;sBC9w6_+Yo{!v`~{I%KIl_Kek4U3DiYI)ATw($Yae~X>F$Ld8%uMlr4J|B)ybCW+l;!%RznVj@}&OD%z`kAE8^wcCoB3lKIWJq>+NHL3aI^h2J>h&K!{QK=NG78e<DGlf6=I7-Zc^1C=ZyoMA2=g52ZqN+}51#t*o#gHV)dfs=d<ZcjLTACq<Kp>AAoQd$#WP$$@UWJOW}vc(ZQuok5udhfT$P2b<fD!*rauq&rC8xoX(qrWd|v@W<&tk$%B#%?bx@s`1g67Kp*_WvD0hP}QMj1?%=B_MQ?Ee?ljF30z`j!U5l<3FvW`=88gXR@a-eS?{2lc*m3z?#$nr4UE^+AB##nj0v?Yp)DbZPriSS6r?GAd{tP)ng+y!&chT$o0Kl-~OXD+fiDyp@+qa^GMwA5~LB2p|RMGNvlVyjKMzcgXfa+)Qy6N>EcHcIaP;8O*@0j57u{EmK)PKPPlOtmkc)ezF4j^r?nEM@6c>NX^5)3!$JMbhjrdV5hdLo3PuNv4;SK?F6pR`J4va#o6SBV?vtTr2Auj&Xa7wTunv(mDcqH+QAVGo5n<De+Ik+QfBq-Jm-YFBLBn{y0KOZY~7Dv&%Y@`k#AgN>0C+K+#rYYOdNOr7X!<wP|A%84*(mGn4LfjC4ylmJ}2b%l8+wR4!onC|<Lt!7=F9=_(Q%$BZfpA8VGrQ&mLY<pw!Bjofs`X1RPZ7pZ(V6)<?6>KKWLnC<oiv!S~nXjd|Nd2JP?F)vxQvsoi0ALz+mWML&RMwJ#w)T#zIf$C80Tc9~52`v_C=8BX>zFM`o;+<Bq#$l`Ocu$plft}#-D6%g;IWIIU27-cKM8UOQS+!#QkqI{6De|LWnKj>Cxs+0ApmcIN5X$F;Yo`#kvD(3G=u!bvuJM+-aLt#tU@)j4F>0|AmN>tf>_N7FCBRvk^wo6^`;>SFIFOlj3pN^ayAb^Hl;+vKL1R8FCRC=%F=)jcm6y!g3O1+)SoooZ%)?ihw$VAY^IQ&~f!GHM`{Q<FJc;=8d9SklHucAgZgKQzbmGWivK@p~BUZr&epHbD-Db+dfzrLf<V67zzPr0Y{eiJI?n7iK_uq;X7CVtDp8-b}P-}S-c8$#bYr&t19kxe84ndz<wXf0^t*|DXx#01#(&_2vP`^f}&ADHJdn*z%3~B1k&mATz;XAI~lmfs`n%v&QWN9(n_WIeb(JH{o>Sd@Vl5ujI$@Ap$o97L?mt=p&IZkitd9ruIesKdAjz}d2s>)`WxGq)}J&G##{<aEEr_(57^uIttC9!&X@6skbOx#dTXGH})uWV$Uf8vkh5wWov=V?&48o|Ehf-O0*68+r;7pS--?c1|igj^ycc4_4}92QsYB+Nw+1$D~^yct6P)WcdehE1p+l^xkz5Unt!N$*}oa+U!9SgB+bKt-<vjD<Y`o;L-h4Vi_btF{4H!x{otF|-F)#~PSZ*l}!Y>UKQ+{!WS3qj)-qaDlCH(Pn$GMBN;x=tVMbWiZ^G4qOrfWXdl&(|NqRoUNn^bkXEvO0=|2R_<01XmWNK9x%-NFvnL}YE|YJac5-hiOd6z-_?Y#)WZsG<HNi>__@SY2<O5g%7GU}=u*uJ33`}iR@=5nmokLAeC`F>WGJ#Bvx;IRN-<{l0s}Wk#+){mQl*fPI?-^!1--&G4i%%&J7RjD5MIMb&as5znq#CsWT&0j7#=*<^!VH%VhH=ie3#payg~`XI6Z;<`)f8Nx2CnYPV@^2mTTcIu`LjWEipZj(`3`(#EwXB+v$R@J0YjX5X+`y_Iia0=yTYxVdH|(*mSo`0lXG8=Gf5w`GhJle1>>Q)MI*RILcgNAk8TTEBJeX>=4Y^IL!|Gw@kWmu;MJ!3P0}GXd{iby_~Bf+)I=<_8Jgjc<JF!Bq%m?*D0&3N=K8T)&Z^DSFN75abu#Gmlb_BFEOjsx?VxGrA*w3GIP5Wu1#6d<p^*p*X#1C<?M#*QgL(Kt&Q=X`??jk?w3%C%};2UCIcEmt9mNFv5YE$1Q<!FlC^4OQlJ(ji$}dZbWBnWwaOQoPs?VlKq4j7^j6XkOSPv4(XLoPA3&yL?Nn;g%<|LU6z`^lf6|C8KBq*{4spVzWwsK<s7gg)r&@O$=ozS5rM#r(5dDY+CviZOf{xAAAeN|usK@~pw<kz%W0{OXLh^AdZhU0D`jEPT&_>sA&^iiqVFlS9>tJGw7_NI2E<$Gm&-T2*3wBI7q9&b1sz@NF85J$dJQ|6WBL`Gdj+BUzC#91poklL|#V9hjI4+Gv>_pQGYQQ+ito8<e_UVC-6Nyj7-)m~6qHm3h)fzgX%Qk~MkHbClQ@HOIy@$Z_PJ{A($xRKmR$V$89cLP2PGgho;gVlaAW&2f!7O1OpDIj}5t*rK?-h|=ih8`}fbmqKsnjnp&&xzqR=ZJ)n1L#!<{?)SGTybU{+g=`!E-*9N|Yyoju@BUP(3PTL@o{!%<XKo0~8dyT;;KgV7AqeCJ#!mvx^nTz^FIPsvg9Usmmxs>v)ifsK|>>#1OH+bDro|T|P*Ft1D+*MW?MVv)A&P9Xs%9NUQAW-EOQzLCgvf&2tsOnJZd~T4pvEOV%8lfkT<)#}iPtGD7F_ni8{YDi4m?X)=7A3YkMJ^NJu}nQnmx(5wFXO3j^${!Jv}6vZaJg2#RM>=}0q2Lb>yD>E7M>0Dx3>(qe&$+$XM?TC3_JYTP)A}>{AA$w*-)7_0?=6*?|Yz0kYJaVk_zZ>q;!v`RDE2eC+z|k}E0y+_}Q04UT$|bpR#XN}Jlt`{Q0bY60V!ZOFwX;v$9LpM+5Qn}Hf<O)RiwE)pEj?ub82sT8=KEyC@#!b(6Y5|~HGL3?f6KFsrH9Rox)g?!Ksap@__-{zh!C-4jUx|Ju&dB#0ilh$DXkFSs;t(U3I(1W1tBChtHhRv5vH64UB3$7mgF|SB`0=rP=>S%Q^b-)_=w?gDV|Tj(mA;;#Fi1Ks!&|g5z=-pL}*rqs;-n=4&BhY3J0PHJPTq^ek)EWteQJd2x()ef+d%8{Z$^%Ce&4F7>sQQ9LhsV_XD$l4<^$UuK1}5HA(H_>Vr1pp)?yY#x6Z#7waS)IX)vX0y-aSGP0n669>%cxDjC?P@f=b#|iGC2Gd!{pO<QAx(ItxxHO2AJe!y`c6TIJNRS>k$m?wqCCdzs7>S^1pZ5BVtbxC@aZ?P9(6qb?3%I(<y4mjz1>8-o=3?Q7rS&(R)i1%52ym8~|1BbW#0#6p4Y`mD^$za^8l43y@)AXt3UTZUeb75DUZ*)J+C^sjO_CUbFZ^W!i@yHHBeF-LZ{QM(0^?y-U%vXs)Gp@|ui!M{9q+RZkZwR>k+I`$f_eSzls2T?zMeoS45D@fP{My^(1tt-p9&oYYTA3>O!IKR#|WO^x99e9UH3mXfZtQ*R%kdWjdDBtj5_7_6M?aOt6V<yK7lbllZ*5k0rn@Y9Xi8SjJW_DRXprW*gC_MU~KO0kVG4GoHY{Wu8ZY&@dP58ANxD{_ELfJ+hETy{<8d3YRr1wO=BUe(qj+`vI(3vQY1d;Da6s3k30C;`7sK$a;`%uRQqeBWV{M#89?NEc}zm6RQ?EHDg8YPbdr*u$Rg|s6zKK-&h>gzRshX9_eYYVWM8wyNGW5TTo6?7PH<ONVKFccRJc-|h2mzGLsE26d&7uq3*t4hqG_tBgfv}hCrH*~*Rs6ogpy)5nTH%6=M^snUGTo+EdUaOKT`u_B6M(#cU!s*dw@D3AbINt2hnanY3WB5ez%lJ5p?N+$3aGqeQaA4;7HQT4GIwq6)}#;_rXbhm`QM6n^=L}Qc|V#t3VY0biaDU7z&=nk<|!ncA!-UH4rnPLX(80HLg-lqLNqD7cH4CIuSIb0~YpOW-#)!T*w;AGZv=@SE+>J?!nx!mNBcj2!Fkz=+-SLmLc$w=LL=#CgA&$>c|2Okj0%Ly}$f~A_7qv$qHJ)U+9WHt#LUDc1o7${iFM^Qrmo<v^sqA!lb-3J!pZhFU`rD(yVBwQlbJynowaDQMca}RbqniG~gQF$DgbtV?serkDO*reRjZ%;xIf(M1|O)h>o4dW=Yu&|G7A+N*B&eF`>c_+U%*~ECfeHjiAVvs%C=(5<u>jfwK_!MCWaFw1Rfgr$RB9Vg%%(vZd4&89>w$(MrO5>RalXsEJL=i6dKW*#%L$VTo0jQw}0Eu9pWQm3&y<2SP+K)tvtnRb;xg2^WfXDCu$eD2iVJh4sVu$kNqGiCWwQ-AatDa^*=}Bi7M-8N3GqCascyji%JRf1+%cJi=iOZB$*DX0CAY`6LVwMHowv!io(=Z*KxTHZGn1aI6l)bJ?-H3x2zh)AOtQlJl(w$r6p_c-}*qSVN4gbGIws29dP2IcC}-XF4T}vEh?OC$DOQ+4?o`++V<J%DbOq<oH+N1~K5g|8d?Wx6yBDiJ(-vB#T~DqS6mKXN#c+pyuxq`_t->jKg(q{a}14IV&Qt6f7-5Teu+K8dIEtwd{jq7}jqe=Aul4fM`-|%Ptl>SS_b}a@tyGcQegn78t6mN(P&ah@j?+(U!ROMg?I0Q7RBSRl$EG--(gyFigZ*7_c#$!MGzK<ooqmGI@eDQJlCL%cyv5KD|+$gboT<N%ikA4lbq!r(0MK^Zt2<TOY=fIpi%mIM#^mn?_HPF3p>!TdZgWkw?VtD2R3_?if|rA(lZ^6XA4YCZeC%Cco)XMi<i!m1`~HmlS8kyei@38!oM2U(W6dc|LYipMYth2%|-=mA5aNSV7|!wZsTm<fNHY=~pq96hxLO4S6s6q{+Oy$cD+}5qXr+p3OOB;*O398ona7(YVx!)CF%l<F7SyClCacTymNwC}0xriA&n?z_42r*{uak;#Y1-LXbKFOH9+Ml|AZFz6$dw893!gqnjp3Svh;FT&<u311t)Q4~Vi&Hr&!=8O8L-Ob254wPT?3%(O_Msm+PR5C9EQNr8g$Do(_5GGes4as8%BFAx2-RBEGJQ5hdz72;NC>$h!%mjZ2z3KK>Ds2oe1@F<kpBFEnBNtP!bmkeJrF+{nd;m1`fYrL6+O+?$gF*P@jm>ABW5+yuLp@<x44x=bPv4c^E^`qdAJRKT``I5iF65z3yDvjjv&_~ssW@(kHwVbQ~ikT6O_K9g>x_X6AD&%cMsdfnJn2r%;Tnd<?DMx~L8o^w;fY{A3UY)1*1C*=C77F!-wIN6#YHXId(XA`vJwZdgiKJZTKe$p;2CrJ%tWZayyEVbGD&omwE2cmU;i3RbX{(@jx=!1K9O3w7@sv@uD;&vOY@AXb)j2G%D%v&VJX+h+tRr%PsBuz77GtW+td(VKQ`1oB_BE413BC%T3__~7X(XT2Fd&Opgr_%}13#N(Gy<uLSd|iGr~&q3&y!n~)3f5?Nb*!#>qwkJS<FCdRsyo9hBI+kFEjPvwgy@eB)aL_9?JCm-yG3RL<MdWe0^hJj&e7ExZ`zmOEEW_0ccK4giP*jv5ad9sU%#R*$?E+@+T4h5+|S&b?a16oYy0lcA|}vb2XfpjZ+eWnMJ1;e&qZV{l|Pt1zgTghgXm|RsGgL7&D$MoI+#@${nmUBTJNBD`Jv2J?hQ@)<M-7qyJO|B2R5Sj?ajumgUo>;Rv>17<ToN`xQ8)$WD8Zzf+PKp$|-g5i}43aoRjljK0K0p<~M6t<WJG#iI+za-0Gp)SJdFvP$iuSILWuHM*)A)<L9s_Eu)%d$M+v<F8OnVucB8iHwfraaRQTH2D{E6sYC)jg6e&J3OeNJgP09x{Fo2J!qz?fP~Z`hj2y;Ckh-A2S|-rH@)jEXi7ih)wU44<Dx_cK(fn3C1mbO2D%*-b>mhoX$Yz4u6BpFyhUc>B2@L8lqBmKJ*Wph*&$Hz9v#GcT47wqTRR+61&0n7-%}bmCj)OXY3WWk9aO5e6}7us0DWXBj*Icx(KjSg2E~w-7W~C~21cyPMFjT!Dwf_&U{~Dp;hDo}`QM5sYoI8U2H~-)d)yTOQXDVIoK9^-5kk$Y_ow2P?gp#Bmc%9-#bon}lt;p8whHK$V{BWKD<SfDKblezc<O0R?n|RnpEtVo(We@juc%ZtZn)=E@Iiar^NT52<)!G|o`a_zL}sg0gmT3<66oxHx&Z4AnZWC1&l+LBj32srDTdrriGZA=6Yf$OA`VdT_(Yu2DE$sETMHu=QFZE9h<R3R51^?#)np$!m9n%>TfH8old9UCH2`KfWwSE}0?>Crg&F5lkP`iP+i8ZB9<DQe|Cpf|0Y<gcNY!{M_-S2ZMh=lhUPXX)ELD*K*n6V;OIS{93u2Tp05Z1QAaqPr)gh@!03&u4`Z!vPbwnHongj)&3N9DEgAhC%ZQ(ir(Z|g&%(Sg8uispL%iXP9LcsQ1kpW?%{Y_fbq|HKX8$I}bYfLsl*h<^8m6&WIN7E=7ef-{Rqr0Np)5)eu5F^Ez74IklP(;!4a*lvHIM6{z47t!D!Mh{yQO0pKp03eeY)$qs%YN!!1WLG~a2)rmje_!-AleTUq7p%!iF5+U+D#%GO*(=LYCS>NHO+w)zlgTE0suMYgdHPm@8|0ErJkSoZ|0n*+FKch!r*e%07|<WV2%N-IHkN_anv0k4h?RYWaflcQtOzT*H<<9CfgG7b9uZj>gw2+3J8Rd!|=6e=TCHcCr&hPFto97?)Q2veMiO;iW6xacyDsHOf=^c)wh0!hjBta$mv}BQsLo?fY2HL@Y`l3uge7@hgafAq-iPasf@QemcpD@dZ$oSGfs#Fd5F_TPQKGlCwh}7C(O8kBD&UH^5zg7R}zIc1R#WQvI)o+T1}e6aphQ^K!e2H6ru$A&P9dHilEIQs3WeOU>`31j%AxBIdZrq&D$s{IJ<j;iR8$M%3Rth8{pG*s^!aHi-_LH^16Dz^(822a7hfX$(>8?*{l%i7`3X;WkC@trc*@YeQ&y=(+a&RP@K$ui@6^l5}S)=&@gmW)`3qC6f9uDH!HWeL$p)#HVR`;DKVBPnZQmEN7r)3eDqT3VjBBI^NJ~DxpLq(MMVkGQKIhoBn@=q&}3q3l*y?5wz=|hC5|ZuF>eS(MM_37Oxg`&6>Y!^kqQc?xXsbZQb2(5Eof9*eIzoGU(nVp_;dB?Qp!`g;@1<OXfHkAwA9NFWujOP#7R9X46j?fJnImQOK5{SvI|r|OLsVlnlG5<(;8_9WqLa*l9yI9DkWI6SdTG&ClZ}aPn&TzMecPVOj=LOlt{$LEG9=p`qeG1J6jnSriH#$VUh(Jtrx(7{J@O5SP9;!AopmBsntC`KRe?)FGJr2X~Beg2wtf-`t}j2ZUz-(Ss&4{=Ak=cG`qmnd1p28IZaft-6XKJfFdWx3XVsl@%QKZSI<8EI$>RR?|hD16GqN$<vxR9hYJnZzKjR-bUYTO0JJLkjRcVL>v<ulYF(8BOBM|Y{a#9$BXp!Levc?*-O+}vUd#QCvN~j%e#p!bBpi_pYxI1tLP@o-y|82EgmTb9zC>+^YmeiZ^(kJvdsPq*1VTe7s-nvpy&WP=W1IZ%#)VqX_=_7Gq38-zBCdzPz>=qz0tz#m?$xi)P;*wa$~L$@Nvv$G&lRl?BH@AL$3SslTSH=`2A>P@`!Uf7NpW$aqrp;$MX-A%EZ8|U^M(uLjBs&U8rBOWrd+*SKk6xsRjcyFT~wVYYet3wb(F0tWp*=Z03{+dsiKf#(}?Uw@)a^qh3K4S=5Nmg{7X8*g#SW*OD2mCOs2~ziggN!j*p6iRq{a0t6b!mMV?xze1Msl4KI(VYMt*IQN=N*N?8vKOD-X0`8{Q#Ly9j^OaSi75ILU4xuJ4V1X&%);`Yg1Dy`K+CcFx{kBGdPlz)>8cDZ`gLd!P`p_`<w-CsV0thKw4gOI$dRZ!j{+8Q!30z^)BkqD}%R)BFPGlwR&P5<cIBrrh~-?@;WcG23XdFeC*S!C={Cz^DKX|%3{;5IgSb6PUmQDh`vR_cH~p)xG+L^Y2pG!u26Vmm~oupI<VZOO*Ti1x*)#GKL;lyHh+WL6aU6Mm%llqP4gx<vd=fsK=7KOOfUe&F`zC=jl&HI-*ei;%HR9=1sOWWU33RV&)pJ#052pRH{K3VPzYgGzO1inKf4hKM*`6`~j%L8{5&ow$fLfZx)MRb+HEhiVDk;BefjewGX)g*7_$s3qr$7P?c+2^z5K5*B?;uey2_Wdv2A*8J<tU6{(WR0yT1^sr!x=3dpHLzwfLCyA1uIVx%^%who9l~~z%nWrjCe^YHS|BA>6uJs7|?sBqE<KY8Vuuh-x)RXkXoW1C60w2N!z3oxRlu~7D(=)0$akKKu`mz{g7pK~Vx_3Co<MdLqK=I;D0we9KUSk=3Yh1pI*I91E&t1Aq(!$Vy3Noy5z3EI<rSw3BudPaYs#S>7;F)w~jc7GOK|VgXXORSemeUCKucFU_Q)LMXAef8+hGkGun@N?p<AdI=E{$flt}UA1Q&3WW)NLeL>a#!5r!>(d@nK#9YF$SkdMzc?HI6Vz9X$rw%vGTV^E4^*iFZ2p?{alc=BnWGVi8e|n;LvV34KM^??w9i(xg@U8ii<7XeD^7r%isHD{dF!)xkeB8RZbLhg%op3!?pl7D9C=p5pygXt+aPbi6b{No2n=NmU(iB%dZw8i@nHOB|a-;e@LG<3%=Hp<;cf7(4jj`&fr8`j#kgl?Ja`o9EmK81KMLkGl&uQqd^2!9`XEV}h-SRwut3!~US)2h3zT3b3<$DeEJPtq#m8RL+yrcIYbT3^JV-ZA3IH3oNQ_%6FEKJzs^RF)L3PKqCbaS<L$b`RWc|dZarC0>9e7!t>i$>W&|NHhdzfeT!C!nonZfxPbVDW-=nJVXT?b-wLphbu<NgY2QXjK9<=>p*mF3+v075MeaG&G-O>zdP{9Mzo&7e0}^3SUbZF1&dkHFV^crF*<gDry4=+&V)kLpK7xUK7zWj(Bg#bx{BI4B7QKkkp&xfj>kX}OI}Lu4+Z;`awk|3E>?xFKp^zPv2X>Yv6XnTg!8$5F`gM7TGU46PKuPRZ>9`D9T&F+hCr;lS8wmoJM%%&sLE`s~>`%S}u~r_&>u7?Y2`RQ&ghr()DY0R6xT8vxm_%%Md}?;}AfS3k9k&<mun^$toLHD=HWLpk44X!;dQ#{b8<7G^MK;ed@{X)<s*IH=tDHNGPGDdY;)2C?Nk%U}Q<JXo>y}nmYLI(#Qdz;g>USL0eN7SI$+I3?eZ;T(T)c$vUoj+l!)pqwpq80Pw+{Cd`ghgQN*rahT_=a&QQ@DHle5XgbC1s))Bwe66s+x1QVU2?sJAK+1+PR+Tf9ioMDNx70XpK?^_$N&AuHYAQ_&`8NFAyvc}<LzlOY)>?L1ozb967~m(!<q>(WMWyIU=P0<upP$Cpc7>%wdCe$4r`sJ?Ooaugt%ZKH3mnhh$4l6_-0@^oQ>ky{giv!KYp7Vf1Y0!%c@7?0$uuZAJZC_Qi&!O*L0vRLz(>L*3`FcRQA&n90XwoQ2G8gk>0DO~>^!}6=lt7z?2WmhDCT&|fC3L{u@n&(<zKW2eUv^VqXuWk+)p~|bn-REkGX;bECV&|t-yQ2s4P-V^pa%o>McA-7e6ACa5j*ZiK$y8a3V|o&(Q=sxJmOjpLafmIr8D`Y<EVgg0HYb6JSllQn-$*leTj=K$c$Pl)A?7nJdNdifS+kAc#g(33bzEWT3$PNss!vyp-6tWPm^zONL**F(mqp`%RpY!Du!Qo#vqLCoe)-&OuW+w`5ES`5P-Xd>xQ>@%C%hU*>2!bKk$Te;1Jxi+0n*~wKxZH)O00WK&Nx4W0$(o4$L%*+A2RSz_?XJKxH6!YBFB}rD3fy?nT3-d1!pqKg-mn?imoP|f4CzSg<1|Ak@#bka}x+dq|ZTc!;^Y>d-LY-N6`T`l872GtM~XkHfMfD{izukz!66i$c#~VL<nUSlMsTkY?MC9vP|p2NRjrO#~8>2&rJzXBnenKylKHuoD(`3tx7h#T%)d{4{IgUZ0AMIleEzplUyYj?#Dwn+Ki;@xztL&gd<IYnrp9|lS{2I0$JUzE&2q_#*n*%uF2WD+JkoTJW4<HjFP7u-KDTMxeekz&F&_MPYctWH^W982OVE6WSV$8epVVZGSycWTr{rA`~L-5530!")).decode())
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
