"""V39：纯 tape 播放骨架（cand_2 c333c1, 198k）+ V17 护栏/扰动 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)VGmTlSD$x=@&jO-R#a*T-~3=Cv~0KsJ8WEbRrk6PXR-o15y<T+$jw_+eGJ@xyz^+B@8!$a1u|NZ1&fBXIKfBXH(KYaG<lQ+-bzJ2ok^Ut3A+i(BzFaLS-r<?!${kPx${crzu^S@u8eE;)b{`%(n>gCTb-aYy7)-OL?KEHYK^o#fJ|L611c0cyh)%Cj{@?U#<`TF(tXTJRU!zXSZ^7iub<@T*-hj)Iwe0}xPhZh%LethePSJ#(MO0RBy?D<cxetiCM3@@&Jxfubx^Y(|!%Qqk2JIwKy%eU|LQ~a=quU`E5=QsC1`SJJeKekzv?H`A4s8zb~#<6+S`2n|c8HciY`TftYUcdb72SIrE^UXS$`wv5U^ZNNu@6P))3~qSLevr4nI*tq{@!=^iE(<Gnzq{TXetG`x^7^p9yGMrGi_>}WoECL@n6Ue|Pl6r&9QS5BiQ8AJ2bs&mMj7sxceBf<eE<b|ls(@(^-nkEXIL><;)faB<#Vt%u$kxG&lh(5?qiHM+st8sZ$G(uQ1^?&@`qy@*K@gY91dRI*R6fIe|uwIcAK4StYtwq`-Jv_w~@BY6N|I`!CyYU6c1Unru3EZa}T<@$Cs;C_x^)B!TGpqGfTT!yYmCmmEHc$dHk~Vyd7U>vUh(Amh=2}e>sPr$QNw+qqfWWK$8hysRtY#t2n}NVgXOSE|0oG9=vA}AT|m-Mm(5219*RsZl7^JT-mhVzAt{54$#!!+&q9h;Nt_XUcbJ4@$RpGy1ah(>h-ICK00Ll3E`8`mm0S8<VeL2Ka2F+tDlcsb#@pwKOww^r$;%x`)$LMIeju1{rvF0LXV%;$=b%V`PmFT_r3hFLLg68>nzfpu+DnK<^<jxQ1gfJ%j>H*<Dqm`{RMV>yCN&khle_MNHzZt5BHC@ybt91{Qq$A$3FSb4mR+{`e#m9VxcQo?Fb2feKh0b^5mWyohe1cz<1FA@dkK8IzI?el-)!0LDf%t5h!g#8p`{lrmZ-RuN61zg~wn|Ad*&e!G1t>0=e|#)~*nL9<lYqdd0=?t#v^^dFxk_@Abp;>wj|QK#P9fPTbfcd_>F7qd$##rO<C4wGSf>ScIp+0u!E50E#%q!zqxY^F{?59~@&}osOq5l}Iq}m>QJB>Propch=gX$nY-<RNsTzhSZuIx`?waRmvSAQ}7<k(R#Xj$S9$`9Jt|E)e*7c5#u^;_95oET6Mp!dURHtIevK<#ya(!am0LQ0}XoL+mln-or30bDyJY%2=j6Md`)zylNEGb6>%gaGZ<F5cod<i;3B50+>jOa(u1`%j}R#;=<^BJX~K~e&gO9ps~&=I)r_O|^nGX=>8T>x2pqPjr*qG6*o;KP2_)X^a3*$*m5EIezZ4nH5RfS*dV;`UK-oGr>EPCVPR?`rS$a3mKX^va?W|7Q+w4D~kU1VWYvWASgAShP*Sp7#5;o_5j_-U}$m^>h3HFI0zlZb(69=@b(Wq{i=#r1zZqVCz*Ux|X{_^_zFZ@{Aq>XA9{Lr>vkCUuBq=nNTk1y{rg3lXl(+X^sJqOpr%om=#t%f^UK@G{*5=m$Abdhx5EZRZhNP|3npwOSQcpbff#*VQovH5EVkrhao1<z_nBV+1CE<(P2%z=)?3thXn>;NrwKl~qFyRA#6hP0ggho|=`f9Ba=tYUl^3Vj_u$ORK6UX8OJJ+Ixt4&K+J0iU_M+0HPN{|Qv48vZ$sP7)5$1YnZ=!F*dJ2KrMxI%TOOO&$nqfKn`*34DV!Pi*;K)rWL;cfA|T?lzpH{iLBm9$ZbMk5FcUoX^v2oB-keogAHwKILzyiAx5htHC0+O!EM??c#?7lE5Kmm8DR~q~g3hmj<7LK0amnZDGUmwnNEPDo_oUL0+NA@kT7r7R!d_X;_R2IU$1~!1)8uQ#?X3Su)Spen?*R3f?3?HDxhN?-Y%WN!-r8^6GLtctOiiImWfB=k;A*_vojcu+~KffT(IgfkE&8_}Ria#;c$vw6S!#YyQ-j71j-<GxF4*3X<vh&gaDQgZ02_V;BJ!RMdu0aRl)x+ghZ?_mr`?H<Q0yUERpy#TSMhO_n5KX&J-Y#ATb|^h#!gVZML+!=e51tY~q2jm<L@CMO(mI%28nCH`E&jueNU68>mtI4?p%*UcfTipokY1BCXNrQJ+KD_lOWxp06+iPg%uA0n))K#7Oi#6Yy6h7taR+>Dr>+c0LS@a}m*Lz<bJj|AnD8L?|#zRle6S*XJRgcR2(3e6g^Y#(7x)l0tVh$pSwReb|Wpt{*Wi5w-2qZ$=B)&MvjCH@<SrsE-P^gd{e(rrW|h}mUaj3aA;d4xedkKq7wG?qhGgs*_kyx%c5l@=1kJ852V^C|*_`q<2&=z1`Axr6HZCiiyXJF~PsW(}JAlMogsHa4)(WbF`HIgKjXM_lgGru&CTsk_DyU344qsdU`<&Mx#QXY1Id^O|pr3*fdDG?@lC2>*{Ug5rE<L7m2-kx0DWbb75#UY?Jn^V{cFNq$NVppg68JTEw&&Y#`9(qYnatYqi*vL_pUHTb&&brgWSW!Qm^N7Eoy@w{sROD7u`F07)2g<qVWNQqT1*o`#cGjCbPSy>rGcUQ!aW1Rtr1ksKqRbGO+A%>vbU@;<eZn&*Yrd~1^w}e59XBPIuix#ENUsVg`5`E=MF%G}b=b(lDN}9VRmV~g-q7UD%q$W}7suIe%z*A-fNIZ|%u-z6>g!vds=0IgTL#wz{+47I#;^(i;)~*yuXKYwplvT@f{<Vz{c>Y`L+&xw=N_vHOQ}Ow5gqoXt^N2?YZfA1RcRBNbM(SshI@42=5Q%IRJdz>V;UUE=(&>Qv@zv`;fB5&CVPq7f$x|B6&&|)vGx98aci%ePa}ee^(%qmN4(>hm<2%XS2dWF0@c0m7M1;<Qk;ldJlR)T6V~S_EfZ%>D70p0p6WhQG3L`#k*|;hTTggWqT}*!-?n|-4rP54*OZdJ5hRP-1u#{Ju5$d2iF9}SCp+b9#DN*hQVWMy`{h8_IZl+#?5GKcI{eXR?>?58ej$|FD<}~8U4&*@JKKMK8Yby7m50K?yxLxAVuZ^+tcxg)%6;q<K78Bu-j@updv{@yrez^<gpbf)Q+<x?TMb2Dgb5vAocSlLs8EC29<V2)cN{SZbgTz*wbbo2WrsXtCXeSie;cb-M{lTXSd;?5>qWB&C9-R(Tw3%vOKC2<5K^@6q8d=KHtJG~s)TV8X*o&muVf6N*YKB&l|D#MVDT4@VaINBnd*!SY=SIj(y|`A^H5}vi7Hb(B(xr6-^lt7-m1jEV3R2>qhP8?7=(<67CSEFDCj4=PlH6Pff@ha?CiOq}(v+NjF@d73$kbf5NlICgv1-%CC^90Z5N0Ob=NRdha4ab(B9`wjXsKMl@KL;GPlIF7uhUf|HjWup6h780eXFX7zReACb{e_qjLmZSVlGnoZYp5#I@K`}5i#5C31&lgLC~&b^zzy&N@G4`)y`&(lzgBk`ydM|fibGIK%!PPxCvB;YTp9QDM@ItP%~GgEb`T=#TD<gk~I!nb;o<E<O}Qsk4KSx@yU6iVKERC^dbtb^~$Oh>yJ#Z`A(4^1<S1Y?#iW<N&}^n(}7SvFI+o?sEySQW<!?>kaCT;)P-xlv;~7f1&L9Mm9WJ5)npH{{VM^^%A~KZbJ(ZEGr)n&tXr_rnA-!vFHdQn?He@a!(u{ZsvLt>%u#vCtgT>!YJi0wTF5+ng=rg|Q#;S)02+vWps+t~H^!5QKcDw1+iz2UyyzB3k47hs946aAST$l5eBeg~>ECUpEF37^8%$mlAmO{)8`SR^YvVpdhI0R{NMW%Psqz_cWC697Ct=sf?7tTLnb=`_B;*kEsa5+jZP5yA!kG&mFDsp%eh&3(blRNz1-Q2&F~g9i-u&EQq7uI2+D$0{?4-%<JxrDs!)>ph?Ha8DtgK#!Y9bjYx0yUoF28x+uzN}NXPo2ork*EzJM0%%aN&qlVxX#QmWk_PWznOka_?`e;B-2TGDiOkBvcZsr}r*x!o$Q3<#bk5(DTYh*7-;NI35ujt8tzNb*mBVTQ1m=6D!f*U2uVlOVYkQn?=YaGGdojj>BPb)lR}(1W{18jKG^Q1VBBkRb$wM`cc`Dy#>(<Q=0VlRU~H#@Q;;BMgdgxO2Amy6X1DMP}-1LIJ#;ZfHkZka1}#)aB-}GIfWg^wx({!)9-GTXg!Ljg9sPc8W(N07faO5af)6f^Hv7K-RZz3AwZ`5k~5vhyUW>1sz4V_KBh!V>ty9_1%W1Khv5Okybp7Hm8Di?ei3&@)}F{b;P_ol_)0yj&^F%B%Y&awT!nBhETSBEQG_nltdO9GS!T6ui*zYNxXb5WpiPD%8#1dXR-zPRb}uk+b7ahEV<}Y%38@ne7hKRQT;otN3cVwy_X*)OjN}|kD6Tn1>O*$giH+gGV@;3G9U_LXU(EM#JCRo?VHl?;kbi&8hUC_?7T1Y>A;EGj+$FXJ!muT#Cvuu>I-J-M>1{h*@O3BT^cZ5<l+0eQFadoI8#ZiQ5E`5Ab}4|@g2o&h+CQIAC5F!sFNu0g4-H3|OAMqr#b5=0FOVIAIUA?hVgHs%Hx5>uWm@6K{Tgkg(YBX!b%c9~^2S~RA`CA*{D}m`hVD9LbyewTQq(%2mHVpI(>88Q6!Ws8&*mj&m0H&esJ4`eJ5gqCm%_CvE4my3PUU)CUbURva9t{Hj=Qxn-g8&C;@15VO0oF~4bx;mLuge`#W$8wMUVg^DOIvotxO8kf@JZiw}*~Ns-af-Li1_atQAP4gqq$;8e*yT)F9dw3+MyLl&qafO`2JL`kUh2l<-d)vBl?<DB2-TcxaieL@}yTQP`>09S3>_s#Ym4sX0VHV!=rq5T&4Fb2W%1>L4m|fW_?z(%V=jqmYn%+=?3?S+72%ZXmSLH5{~#0$o@^w#Pb{*dm7OUWJR$*}$_sZ}5U0Q;w)fXOSurh-pSe%QBBfV&%vI)s!P8V&qBbBub}|i+VAN%q@;fV-Y*i^nw~N4l=8~fuDVR;NwK%Q}OqjTB+z;<6^ajPUy1D;LhW4&-@hbyG8FI@VwKYykBxtgRNDUjz-6s#+cLCBzw5z7ZeB-)k82#n8&9IlVn6@s@i)+q?e)|uQ^~mm1rvU3(WH}5tY?$)FNh}3aNR>m4u9UEvvug>O%0GPo)y&NuVRf<u_E1N*R%h!vu3XTkQY^#V%KQ>>`+LHKfUd671|^1u`(|O|z;8F=Xm8%FsF<WFji^q7yMh?C+c>`c;<?65#5}8CTJ1>&xu5yk^G^yc*IfdwRDUD^U=$LPYaiMR4YdmZFxK&Bc;6$7bMAX8G|1l&y@=xxA*tESt)MV|JPhAE!d*5X-zG$XBLY-~sfizrIp)r=ouoi8w{ENw45>A3k};9m9bDz|6`_#(X-LnASRVAV4y%PF6c&-WSi;>!`>})mX@$8PRliqnNp0(kNR&(-@B&>-=wr`}FVu$lZ!5n=EkjjJ$wO1T0iJeY|o>Zd@@BVmBp{YfgYyUbGmm{Aum%6F0}QMkd6eFN7daL;d1`{6I@j82|=<c!c>r8F762iTZ>(*iua&MB?A_EMw_mGovnr;Uo}Fn*@F?%Pb;9ELr2o!xZc)^jSb?qi#wo#J4J|wWdOWXGcK@iOnjp<za*=XF=Dm!nY;4&2Pzxog9=Q?ZOnXBoRJhcwCC-6R>nnZVRzx#HlJ2mvn@*oeL3~m7%IDC6_}tw64N|C<4!d*puIi6AG*5&J#k~7^+~&<y?Q2$Fm7_RT>6k8v=*&kkb9YEZ~F5bcHK^YC=s?ySVzG&3GuyMvSpbkJ!aJNk@)PNQ{8a$C`{RDB#2ab2@HBSP0Z7h}v<2d#J&57V_t%8k#P`o)j((A|=lzW{uq)i4_v0#|`p&n?%VngCj;FXxgW}ej{t(FKyfuLnAaTufhVZuCi|SyF&qYQ>(dHxM6AiO=tB>@FW79rRIN&$R6>+=5a$V<U+l}dx1u0fr`9D(WOEh`$8Y|j*Hi6PKtJs*?yBGhTsc-nZTm2|M7_Ik?0$^#G=4>Sk;%W{xP-7xx_0tO?b!qYy+elP*`N_xSL>Je><fODYvgDPzr;n9RZZ^pBc0vPr|1{hk=^*-Zj%a-0v}h=XdS7y<FGb&kf-Bl(`iePD-QP&OW0~`Tay-EZ-`ZPrXlIjL+mEy+(ljNo$ABuoYu207n%MI}^6fFeMn9yE`P&MjdC3gt_Zt`E5Lbh~~%sj=sHAp!_!2GmO71Kb0D@UU$=2$g1=hgo11Wr;QYe4|)o5H0I+DesX?{Lam(ZPzu%l8YvmCLRtn8xn3TV5Gs{F0$56aj{=>fq$jcndjbV|y<fOqZ^{awS?B&pQk3j#mKZ5ztdk3Z3f>9s$|@`d#(@e~s<Tks%yLMIE^2QWk!?Y|MpiUUHI<O2OYH>7dhA-3SDjE&%qH`Y!{fZ-rJxJmcf18aV(@2bfJ}rAuJLY5w_y)ZM+78q{oo+l?I$h$sKW1-5-EZ%J@7cl=&_G&ivk=;dbvR%f}tYD5&1qisSh&=&TA7Zuv<#1lztV6;-BtUj~GM2vpBLEfz1xI>YxT<22^O0u(ZZi%1Ko6s`{cO(?utOrgXr<zRe6qo|X$)LwUyH^x!I$P~1J38`d&rH5cKpR}|g41;sK1KJvW4F~bCWUs4@epaHVDGo*KypHM^~DkE7z3-}9N(Wf;oN5M|X61{(PA69Cc&y!Y%Z(f*`m!=0T(DkJ`c~hDd?Nmxsphy!c%p&UcyP`@=FrEfn<Gc8ib!1E^$mx;Otf@~9m{A;tCyA&KI~38e^VlpY+u=VCPO8#{b5l&H@PjscsyGY55m6&3@};WTAb|vsyJg@k1U}JuTOF;SUG%9?45k<Xxu|R@bwvgcwM4X%@SggXx+ZF3lXBw7R$F#Klx|pJ)#a3fNR8{|fk-7EmiK`WQA{=GKSdRpZf(Maq8&<lTt158S3qI?Fg~($byA`hH$k@&W2;<w64!`z^j-$<fq+S?Bw(W{HSeD&+a-^1SVJ3C7p9pjTzozW14I$V5~Q$VL($ut0FRAJr#~F4!|+^oEboHfF68w5>b~TBt3k3vV>zDpP$t$8BkSDl%C|uzZEcR3w#b=I31e*dq|wQ%+F-VR4LtW3@S5`O=NLKuRk%S6IPZU)cgbz^TUsJ0l`hGm7nP{=gU;Dv=mDttMPh$i9g=al&aEGeFC}M11eSuOMQ95b<Qrp(Q?QnOa16ux<HKB(X%G-iif!4&Vh5|`bWcuO3+-;EdCUSsl~u`Lvk?*0d@<S**WRcA%s)y6Vy7zjkK{Wsavg?=I12+dW-}OfB!qmwK1(J~kS2-~H)9zUug#}7s*}(`;VP;A9mc`M)Zlar%VFL>?{MqGSTcvaMF+<kv3=9%Nz$cx({zg!tswG<*c}DY4#gd#3OmFysA?jdZp=jV6WioBJ<8}}x}kEdMf{TDte96NoP5Kj73|B|T_MlMZt4>-Efit2$hGqJMH4G%+@h8k0gIe8lPdix#*%`_GNmE!MV~a8cNf_(nLHwoGTO5_r%c?@F+syu#5Nk2I+42IZD;(oX6^)nppr{Y(*y-f;yrOmJ02KzYa+X~fJywyElCJcM_`F*TD7uAJ<3;M9wh^(9BFjZ1Su<LZ<VVRbYOr*VetV`w#kNDnk=K39+~Mt48L*=be@?ODKxb?kr)D?K`JRwP+rA}SWZTaRyVFcRO#iRzm`gEbSo<3!>dBv3T^$it?*KyZBb#O=pU71X%ilWQd{KMn?1?$#N(3TOD2XWS2X;%N@a~Vldy?sn>VKB<`EOa8C0T#`zaKW1I=L+<tKJ9>aczk{E??a<1k<HS6Bi(_EM#hJRbU}y3;JJa<!I|6+kgFqR~DvElgLh@JWTdjVRR)K^@aEqKr!cQ#9pB@J=I`OBWEkImWB=)P8_+71=_e-mo?V2}F&}GB>()WxOY7s5g<6>-+~-YRceMYnv77NOZR*SXM<md2GcLh#_1QU@2`C^iJ1ln~)<Mzbu|Is&<7VnTw56>Z3Y`1y)77hMY%hdzy7bE)X?Ns>otYm6^4&jBRQf3f;bDGAO}U0hB>V6*rCKlNttO@rv;DMswh2vy4U{RS~OFq6{^_UhH{tt8#i)JRC`$N^2d7Qz(lWXw6DM7S(Vj4(r2AJ-DrbRs@M|`nHEMJ^v3!bQ4j5+XP?V7?`8n4Iu7#-P}^l&1L|a6B8kmds{5ynnEfG*Jkzud9(aU#J|J|=tSK*6%^<7$fccVqvTu-CuZZ6gkWaT>4hITKSlpBpHcyr^V8uKBu-VoH4w&(Ckv+#nSyc$E6vCfW!H+B<V}ydbAWYFb;jsFRe{J;TaV*2qN!#1bZIz(Ef|Jfz2trcPARg}9^~(oWJc%%lVAi5#6X-jPZXmsaZ%`)GI%R=$VTz#0<s*ZfC%-baf_@{yXaN&;$n@is)ltCX`a26nfQ*Z9p(5dRFha?0$U=ZV|m;afj&+C#T*4{xqV|J=l2c|YABCt%ct&Q)ou@(sVX2Lb;u!{k-~`rhr|I=Bi2ptdJCG;&v>;h1n;;gkpYnGGEoVcyOM!!2SweuRZAK|D!QxP;Vo~GnYaj5{U#;Jx<(J`flqb_RJ=zA@t#%~m+{sP$5g?g!^QWM2F}UAn@n1|(@h7Js%=H>t`<NaS&HLgd~);+iIhPxWTgdv@t%PZt8x*6eZPvOcN5qZ_k4Kfa9aMi;>j8)3Z+4Ktm+<j1%MRCOERZZ8&QN%^XmPnxTU+n>aQiS$wo2Rydve1aGI?Gy5$(#*5pcvJl>C{R0N)Snv?s|=+x(pZhiErM&>IjRgD|&ITd`+9{2pgl&tbn^ls0=Qx77uRVqTc;u{Hcc0XN!b%#vg^|EJ;uwTXx-Mkb-?x{pT&d~{XsSFVZsCaxLPHB{WhnKB|5sRog^((|YtF{Nw)SYUw51mR`TBogEkJ3q1?amqiGn}&7nF9gnJD|dh^C?J)e!T58LrM?VnZAF_P>cYh+G(U}JQe)3t}!Er$Re*Iz&e(y$N=m;(fuVXC$<GK$`}9{+ieg!CaUU?R3v~Ay9#|At;ISbjss1C0#5~(3*SKq9*(wfoq*`$W*BDLR+rarF2CjORxTl6d#=cUFwy=dEo#zcA-0Vke19}1n;>kZ?b%99Hj$%gl#D)pZ?@50(e3GE(<F$I;>?P76agrrXn8qDKph<DAS8xd=#b#u5%?(MxEfE_XfL)VdzfWEbuR)XTv0fV`_)E4`AiV)2MSS%pw2`(0c7nak&PxD!3DLRAncmvz=~f)+gt&F9CN~sk+t`8_4-oJkNh`t&QtBJ3`1dXxoQBVT@5hD09Kq*-mf_74iJY1H%u~fLMy3t%+2eontYRO3HiA^UKe$B>`Mg%LdaqGTD0>gI=vGonl~8QSUC54y_UWuV+qBHv<|#CIa?;0^NH$Pzr({gA@AjMu6?QS@I^rAjDPrTvy#{40+GWjaU{~T6!uicTOCVb&MUoBD5@DJ#DYA;=_4oKX{Qst$&(Xi+&~ds>n?e7h>k0X!W#k*!Z_Ik<O{7P&EdFmEKi_8;%*92f_&?uLS{wK<`C2o*G{kxmwv~xO_Lls+>+*P6cwD^y}?9s<V0mI?UW7h={nW&<*!9VZ)AC0yx;l~lr(rq46w<aOYYgM5b7AUs?TLX5h|urMB{yLx}wtxy(&<g%zlfxA0QH&i)PR;bXC@YPY)C<V8J&lx41*JQ}Z?oV^1kDmMEFPP7p`ea>ji0Qt4tE`$Y4KDP_5G;5J1?3DHra?)fAQbmP!uVr!JisQtFN@^U4PDF!ib2t`FoMlnp<4PzB;zzdNI3Z}Tt(aKUlfblJ8R9k%{GLc`<)-3pQ_35FMr*g%wCqB_$dcJ9?mmkVRu^fn#dR7=-w|IHhAsCm?26bc?sDPI4a1u3NFwLhm(hkb>c2p!Ut!7k8ux7CyWBg7eI-8z0<7|rD>p+;ao|q|-h>=-Lj)?TDTUvLvGA>LDeXGJG3p83UfCKq~8FjG|yiq~!(G*jwdwhO&#&=$Zz6;WV3H1=XQg8I_BU0TAD#)@vqGQcNcf@FRfvfY*YT|R6sA9WGU~2(IPK*^Ck4WS1&i5~$ef)L8x^Cb36t^afoZHHM2Ez^)8nAsH59sN5EKC7tRq`7NAm!KdLQvJZDhHM<8WQ@wlrl%?NL~CMQOLTZ4O_jI`yFL<$Ta<snIlLzA{o}``Cf&RYGHd}$IJ=kpo4sg+7Q<s$203wymt4hARY*WhEP;Rmo<7jM4HAn`QMHUwVv@8H#S1i6{bX74}pOtPcH=&W;WfcU!S4otZ0>OaD9?k*;=0qS|3Eh1Idqp;=s0s#7GT37vlG0q7jnf;zUP-r4Wl?_exl>b86-d7swgm;<PlZ7f4LGdbfVmQyQyQ<%_$hI#Je)3<c^aTUE;JX3_vkL~2q+A;qQ<*^T5YWS$DqInB)9o(cGubc6~2h5VLG79W^Q52q;BDI_{RDh^i312M01kz*ElYNhf4W@0wHJff;~zH3Ak$DAr<JuobJ2r0|&DH9!1e2HQLa9@VV@ifj2m5U<C>PQy1PwrA_tsXMrRmgor<jth~n_RGmt4A%ge6tX`N!r@o<wM9?yA3%A$-7tu<t?JEArm7&<YX6#pn7Tr7-uqbXky#+kG@R;6GZWy3khl$t&N(OPBV~2#vXN|Nr#w5>q-c2W0N<hC8HfhM)GB)4%iba!varK^Qb~IQRgYPLsSaeLD1BeY@Cc}Uz|$JDNR8Mrx-?NMUg+@M~Y8rawe-w#P1Z?I7#-?asS~5uCI;);R;(*dA76&8QbJxi=<EXI}BH~qJ7=Nb`$d1+D4$DC$2lFREMTWyW?$$h~rfuiop@2njGGV2hj%bTe`7|jIQQTEukA6jyu)Ql3}E<MyDRN<Xq80cZxYd16EzaqOa*ySFfUspbFHQf1SAtQ<;_up){2q7EICHs~U6&b6)c#QSviKMQw#y3?RD_D?2aqRAuRJsx9VU5gEa?9zow-PWEX$e839U=`)^sl75)87rjm3L%5)~Jqnpps%&j~Ml~mHR$f_O7K7~KRJ&037Uy`JUTPL7Uc5<Qq<z(EETeCY%lF`QmfP@imoAgEFf^co3~O9(I#X3CJy79mtCF5-72-5_CS6%0T8&VUn+NwSk^s<h8o~Zm^jUDKEI|PTlQF=s3@U0fsS<a5(A(9e(d^c>Me}<KO6rfgjU-Eb_9yz3CYmHZ%u7J6>*zzTrG&c15hkgl#~_=zD%4<}CS^YHPUrqzuFlC^6<l5{BC2sygHI@-uju-nNPkzFv}#|Y5RD401aI}U$**(8?Lxdd_=hH=90K-m>tcLCw13b-sP4p5yuS(!cj$|bmnJBQ>{lkKssoPX(*#N*ao~4}W0NSHP}P6D$c8IatnU<K2OoSF>ySm?5(Tc(;8kn$oI3&I9hm8H_rQ%*G)ir7k(I%iU@M~4$?wLnKPdPCGntM8>?~i(`p9Cd1G5U1^W?N0x(YgjOs7Q~5zWd1i)x$loh4+?SK(;P$`c0ANI^sv^X@>txW$(q>CS<`ulBF-{3e#V<A<LOpGa!oqE({ilNdKHAbz2lj7V!3Yo_$K0xV=5O~GE;w-J($W%g014wdw_c-vr+dk!@XS=W)?QX9_iX&mW*L>QEpZHcin^YE+K)X#7>*q(|mceRR`eOR-PU?3lcK{e@!auEXmTSKHpFJg4)$DPu8Lu=elgP-I!M^mD$OUgfc3T0X-WC!Jeon^^HdGcAXj*5?dT^^!Lcy}~V68lv;E`t`=>CgFz(>KRPg21KGb})aC_<bY$lkY&RmHY8JnjmOGiftC5QE5s_Y#1Hxs1hY65!)S~nq55zs2)<s?S(rm1h_gU7Ur4F#KQ{1rqQdO6uQPnq<~V9&2x;rBP*OLV<pNe=MJM27}$ikV6k12(aX=&q-*@TrPY-h<ldZARxq#n9fx&aQv`VOtjAU#@#{VpFCqL_42j<Gn!+lmWhT<C!##!mU3Ih)M;UF`$su@D_~+#0Z1V8j<1+^}K=B#{YrB-x0#X#}tx80}D^b%HFH$toJ2k(DjyQJx`jbt_O856vw8<G#hiXb*6C>qhNCrwf&sM`6-OKsq^r_vtv=Q9yR?DA&>{G?@<r3Gr@LIedbABzVuiStf1&C(b=-aDigUX>~-`I^jU6^3x)<obeC^E2xd#Q*36OA&)Bl+UXVaPH{58OpC^eUSy)_kV=NfADb1US#L$ybPN6CS#T-1uV(*T2WG{4(<@T6<O56$v1hYo>(42$r1Yxfa-uSs)Yb&HVbSn*&Cu^5Ss!xte0ylsTH%`DxYe=z%;`nKOZ0+82yH&>rat1(*iM#_7Cds;tE^Jqgq)P<a+hALqC@#1`BPGirJk+qYJmlfXnQZj_X7q?x-d^m7V4OCS3X^O+Vsnhe{l*+%f<N>8skuCVk4SczWMrz^(plaNkKokxYC@{EAXqH(~gao!79Liym?Arv&feD1baxK}_3ihLfZviwb4$4jvjUX7!4x<Bwpz3GX8YLKP?X>n|zGmsM{);%U?oF77gFPG%w_M5B^8F(msOyyf#8Bj}+<H}l;$+?cq!pV<<Ga2PVCOQK}SCh^^+!2dHEeDQB{ISZp34|fi=ODP@Nxi(jdUN=r=l~l@L=BkLdwd?7Ge4vL)C>&Zh@%N)#wa`@gtCfB2tipkN}ps|ruAT?NPEs>3}k}mrUWRG1gsq1v|uRC37w2qC7WHYQCHFXwUTMJ^P=WS+USf)t`ZFQ<GvehM$+|MY9(L7ktRXSwO7u`rB)b$tZvs9eS&6V$lXEL<ZNB-K|6UKrJs66$y1K*QrMf^263NecN4^?g=x;4VIz)%j;|InO}rgHD-9Z%>I(}l8dv50{{o5ts>J")).decode())
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
