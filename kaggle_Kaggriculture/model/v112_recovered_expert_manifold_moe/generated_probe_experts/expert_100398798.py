"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqU5_Qnai0InT+c;*XO-?&WQ$yQ$su-^9>~N%AS~Jv43RcPUl@Y^yQin?BeF6wG9oL_sdK7J7t2=9On059@-yO%H~!<pAOHK`{`D_^{`U`m_lN)Z@IU_e*MIxdU%!6&;dkHt^wWngA3yxdAOHN%uYdOS%YXahU;o#i{`U3jKYaN6-~Z!3{qDz4zx@3#e*W<B!{=YWeE0Q#-ItGl`0(rRe|-6neDV5se|mZO<=4OXo0lIx{r1DhxcT<<@BRGk?|%FJZ@&BC>mU5|>z9|`kv}+li1_8pe|}6p$oIeaFTej?^23%7^@k6iUw-=e+YkHgryqa*^|!C4Pd<MEKX~a!uK=2Vbdl-icmDnFzyINv|Md0W|NQ%J7{D)Fe^1kg`Qf`?yeycKAN=)?e*5$C`dWX%KfJ!|l+brSzx??2kF(#f{M_kR5kL4B-<3(MzapbU{KWb1c4t7mJr<0&G1c}Km+=UG6CZN^_U6ZY8>#EliGbwqF6XfRf))8spMEcYhtof5ML@i~{FSZ0tIHIms4Tyr4h5NmyGBL+`trv^NYo#6{zoW+rk^-{P<%MZ2QKn}eFnkaC8AEEagC_1J)9-t<vTIy?MVba+%*1rZQ6_t+2dyy{iOmU{n7bh20Jd5e)jew=-RoXWg@RbA^n2-A)kKu;pG=U|I<Ib{P^?tKYah+zP+TqPll}H4Ud+OP3*MvAe`DBjX1P`y`r={Hy+%wMOn64q_cKeA9k?Ie`M2UlmD2vrx$H7$PYoDe(!@-ks<4H_CtR8<EP(|KV(|C$sdB<YJPh8;q@j5KJe>ug)MWow#?bm89&{<8H>2t{;Ic+PfwlgdB6Q)SUt;C5!wyHpML)FyU&0B^5c*Hh-??ghg<ga%{HI2<NN~p<8sCc|A}w0(U*2({^41&PBVA!?ayx8ltg=5ZTm)6{d}+EPB~<|YTNgC+tc*b&aM4M5UbC2t3%Md0D<WZ*QL$3n;5no6)F_hi&YltX}wfRVhhw(Ux<n{?(!07oPEB2Hf0>r_P;;m!K!bs?F1q^Q}B*7==vtvb$dman@?b_7(TaO9&;-e9CujTbUl!I*E_c0!Pu8<!KTIBiyJl=Z29j+s=gbs@7dIWhOrfI{&nNA1za$0yZ`PUW9#;tZN##D4*Nm%Pf3Mxw;|Wo<G?0R*|zOc4^v!#KXP{%Vyi}9Amg(Tdn_LabB~>NmYZD%3$cg$?6CGhj{~>bn3t6OFFt){?a9k;p8kR8B13P^$e;GVPInCQN_Ix-A}HA!sokg3PQA?~Jp!w3a_#FV{_e;B%70Mw2K_CW_BxD{Prdx$VoYtxC{>wGzm^Cc?tr`G(3Tax=_U>Kx>D#=w57KNN{|PGZ+Lx3^!2o89$MZAbxP|uYmj7aHCI5MZe??Yyi~O0q4L8Cwk|X&Ly&VHBMLPABXkl7e$IBk^2JRUIcR*#M^E2}`yH`g%kS8BPbmB&^G@2HZ(v5yKQ?aU{Nn)mty|pb8$XihzTf(xD6P@0-c0{b(Gt(6<%cbA2d=!xDqQ^T9$g<VCy;OZ#lO%ie6bu@Fhv+=U$4E>W$j+RDBP#>zlcE)9eb9aw4C{{*oFiuGwhOo7Qq&V{EqFvu71^^V_-e~GF<kjEsAJRWn2D%wmY>bjh`QXmI%uF6v(&uLXoz>4f-8~wL}Zz+QTOwc^a9*VM=f`6Fve;r10*0fBanCvmJ@%hM#;_z>pn<YRMe6NjdWeHuxd;p7M~7-I7w$GgS3FvmQ<8kjCDs4R)Xdxfo;LYRE(2r?Ah(gIVJdt#BNn?_j&6Fj(nCIkm*uY|v3LN7Fuk`t)^i3Z>7ojZ{@OocX6oMGDiyWcyV)-$x5Ziz`uJhS8Dq3>NF&7I2_K`9ge>l`~1+k~XCnPcC91^HL0b?B<nfReCh|{MF~fBZS#k`KwG{my^XQmKBgVyRyzxZ!8Q51d(qqKTDMBY4C$2b(~lyt|<HV4WO?*RgSDG)cJZJ`{f7W;f9=3#M`Q_dHMV;-5T0{K2bYF{G##-+rBisr9;TyFN-q>zTGOi$d{{LLekR1vu0cM_)NyLk>Al!?Uv3{cc1gQ!FNUTrL7Dbxn;nU#7nmJW`Dm$2AEHI<jjyi#m>T?^`9?GCUz3sE&;pC60wz&TxZ@Mk5R0cEhxy@2K$JGsaLJ$p`>i3Q%pg%m7o5FWkC6Yk`EXx7J8pSRQTA{H_IAP>$w&GE!YE9-z{fM6>eDN3!MD5QbP<`8>;d^e$1^U!$qaO1qo(iJ*2MXf><=U9nv>rq#i4a^fZp>mu*;|Dll80sC|9Re?F2o!Ss&V8s2x6M9(^fXKh;($;?CZB21+?s*52qqOnU9uX2jitrkTeDe%hK2CW$o*kMoy+iJ$JT8mm9^GID|^@S8qFSb$jiwz5T!EJivHWE#UYZrhJHUyCwq(Xw@#O2!a4&R=w5#ScK<Qoxk%E_~_O(%3_+z#7ynSZYugePVzd45JV4N*3uG*tx$tXi~NayRGsK<vm#w2SwVj7WZJX!_9k@LS$041FRus;0^o<kzv^VBv2T@+#F&&T>nm!};0K1l8iSOo2R_iQKrT!)Zf3R(7Alj`QS#P(6|6BfG;~&kr*VejLa_2>HQ0^^fQmBO3}Q-rG`$jL3$N(-^5&5=lko@(pZ^t#_Sr0AC{9rSmC;p_6C6wt^s;3W@ZUYsqins-1m?X8AD7gT7nQkUVZc6{8d-LBvDJpMYY32vM*IFtb>%kq7-N`I4%psaX94LwBWkDf4H)>?+}MrPvMn7twFBZwkI>07J$|^E=G4*cC4iSn{O)JCS=z<-&k|lb80ZPB`SOh@5B0YedVM%a_0`xcL8MPokAj+<YX8t%S1e`k@kgz3}LY#q`<Y9pYfgKh!V(<d@(73O#qq#v%SoFbwtmdcTyNbnIaSpL9jN#hR>nfl|H{<vMBPvdORdVl5DO*#dIykc1j&H6B~jU%i1yVB{~LR!KnRK9F^_rD~1}loO&P$w{5_OOZv9JixXTI*?jcbTw=+sO5!n*sCF5+f;XpXG>yBl6gk$3&$GaO%`SunT*;E3d)BzB1ANf%zij+>Jeh{a)Brh?e2$?6o}A8+11;SF6`d?r!5`+oj?>r-Hmv6sdg7oej)D8<O;Kwg_Tz#l<z-?WTalFz*hnetcnYZHw0-_&Qc00@<Wy76}*Zi<_m0z5a_y0fm8Cq{i^Mdk3AJxfm%Jx@``ga&2ww)nK<W=xrUF0Q)Sa-nq6*)aHpTU7T@L6__T$cYo`UQK#?!)LJp6tm1<gN0_Omdox>1B%cmghO$*gh)FnTE-d201+OS8i8HghjQ%TcO{zKKBA+dy#h}YB~ldhZJlftb`Uv}UL;fG;f2i*%jyQv#$bxL5dw)}pEQeEF*{;1?spwcg}jN@a|)7Pd#g(mW$i7$xx(a9w{-xZi5VCr3zXO8HAP`fndccI*ot2(F&=G4Pi#|~BXNNz@%2N)$Nz`~H^N8WLO$WJ-wAt9d%*qBGwAy)Mz+{;Sm>9$-Sax6le5UAA)`-eyn3M=I-?9}xsE#IuEA{Az&TBg9<U7x_1n&{j|BjZSdwkGN<R&3^XZ1bhnjEU#EQFW!DUlMmp6+aH97A96uvYLbCaKWhYt1fJH!KB?Ja`Get=MCiX&pmpS!{bE_0V7{j+hUs^5oTF_Mz**&MUZ&XgRk%J$4@^`|CZ<|i}$Ln>_$bZ;^-6=lp<G1V&$)a=PDfpTe7Wh$(3jpIi}bLKZ44x(<>re6BQ#9c9b8*u7Pa5N^XL{j)IY?Su8}*^0|?BLq_(BpNbtVs}&xRvyd*1ssdoU;voAnvT{huSNPXg@@-2j{W)_;T6~wCJf^o;pF4S1RPc`(GilgAk?0$v_zf@(2)2`F_|j~!T~WlWXtAIyvCYAYXa2*A1@NLXBBd@SV<c!}=;<M+BSvl3<$q0Za5S|kMEiXr&wzXj9aVI2l)VQz)qKm%DiXjWV;_>PKc+6Z2p+6UHDi9|AD2E73hEoEk4Y~s^s0eC;D^2$c{citN1P?##3^<%D5PT~rYzi0885j^73w4B)cjIf3UuekJ0pqElOeHOWI@SgQF|<bxhe0#MIt<`J}P@M<c%OQr$Xn|HVrg!MahHo*)y!$V0{}dHEwNoMxX-J^~H*K9AdClE%NfnhN$-BbEYW8O5n>;A*xoU!K$wG5hy?7szjM#86|xiO*YTSJ+EBN#Br&uV3$Yb-2I|*+zJl9YO50VWJiP8mFwlu9HV1*KBB2@mHHS$58d)pxB1_+RMF6?CaFy?F93&{sOE<O%DsSjJFSbcbXf)`zK_a|1ymxO>t<X(^yi;~O3qhzQBn}WiN}e;GSoaIMR@oPaZfX~^)QCbC+g0N*1OfOg`7in;LWVc_#>;_YP!N&=djIa4DB(Vr0Ax0yr>jTV7Ci)Bdi@dLi+O0yG1uuapj8*t?j^Hd+C0_8LMu;qJXy>BR47J)sv&tec}6dQI}Y%2C5eLuRB(7GYgD~Ljp}>+2sx|tw(UdWM<W45zfQxXa$w$psr=Kbr|<nBnwawMmcn~OoPD#$KIKDe5Di~lrrV>OVNvjXGpP6&qa5eDJp(ly%dObe_uW#)BVCy$#P~;JhxuYUsQezCf<{%Kk;wA|KY!&qM>>?+c8Wn<nM`f;g@z^X5aeqmyy4N{0WIVx@=VR>mGfe(g=-d^wAZO8iBe^Hp4xmt5SyuPLyK*ExDB)qMBx)@=ye)28ECU&<=Z8DvM=PQ96~3Ju~~v_Cdm?KiTPI>@9$y6Nyxr19C>JW=VMZ7H;f=id%K6X{2hSxI!UjZn88?W6xnqKPfXyE2@g!4B*&Zg+gkx$f3k6%W069@P2>(x5}5Yp287oF3IDL{E_VU>p^<v-|OKt-&xT?#+_NYYU1ge)EJb6n0lUCAg)`H5@}t<de%Jg%g!*fqWkRpgADO!UNClda-teOsd<JGrlsYIpEiqD;t+yd5)r7y$VaQUCvB&IDFn)nKAZ3C2&#PKYFS0BiAQJK0kQlvOHV6)6V-qq)(9(Ct?+F(IXO0@X0kdK_QVaUjyB<baf42Vsjl7)pjLTQan{enHrSsSUXuYX3K)e;d!986Gu9q2iE;D`^6rsV$dn1Z!Wza)jLjx$Sge3&+QYeWR$mHHgB%$%Pm~pIzqhl-TJgEr*9bDiKwK5*07J(XTY2?8IgRNM14p{wdMvNaP4X&6MsUbPGCq*KAZ1r+azWOrF=ZR%;N5Wtri*YYy(sXZp5~qjeUJQ<LDc_~H}+CT3qf#=uQlOz`vzIET#K}U$QwZ=^89E@d12?I+Y3FhE9IZGuu&>dD-5L4At(zb8Y53ZX=XziWVJ%YZk4DxwIX~INJ_LYl#~exE|ez{wDyI=Fkc*RVSz<9wBa=|#m-Vy6%sSNPMPbo;*eDMgPD#YqdHNt-SJ~OR9ys_L##*>@nOynq>(2Gz9LX2vf-Or(QzMad0?uU1SWLui=Zzh!jpW_$m8zNf+0#1*5lKG9x|bgeE_B=t|pn`Er^7ob@?JUG|sQqxwTN)p(YP6<u3<m<yg@;rB>7H_h-u${pE4$ZVK)u9o>^FbvT8P5id%$GZK{yRel7D^R7!I#j+Yw6-&-&PQb3gY?SS~j1?&nsnjMrUAl^g3M<zxbsX<&p7IgDesnAB$tx(NXTkysYIR?ivXA8VO4A1WyG1fY{-u74XM1PMY>|s=IT3Z1g)B<f4{E5EgI?%|C@o%OuLPnjiL3SD_1tc_?wei3NYJ}#8_*!`E##+3-yLf}eJn=T^SJ^Kif>PAc1VYSpGX$=&=NUREo?|#;KZjVN-meA;IWM>zvko-0ge~>UI|^xwT}LZa^>%&sG|xStNTwiPW)0Y?wE)CN8&rpnmWFd24#Y@4x@A_5J#j%V!OQkHCbRuk0feFu-Z72(mUkBTp3qnGZNb82?=&@h7NgpX;$nZJBqN08ifH5$(Dk&qI#XT2X@(aH2EFkcqf$$)|*2yFF{oAHkSGM9HaY)T^wthRQ(=h3QNk|;*rc2wkbGETkZTpcQ;)@hCRLRAs;PWHl>F3wI~#$(5x1XW}KFYOho-cwn=x_LKwyG6hAUuvW6vAP$5blWg~;A*y*6!nLd9zxvZQh1EfzRNWh|Hdpomh4jM_a^=O@C2K0#T&L6W5R@8Uq;oqPML&j>WCX5k<ys@E<R0hNA36-ra@bhuJvCI3USTUAM4bbBwnTp!iP@5tDqIB-!^EfwCv0nhjK8T}#k!RN=sK}_cg(`(KDJx8}A)mb7c&9k*g%Mp!Kb-jX%x?}uo#W`}KG!Cf9i3F!+8#K|$!_0F#^J8~IvBF6teJAbb(=n!=TjRi{~_aF{Ky6GQ;`kS_S~CT8#XuoOvL{iqqOp_IFxx$X_V1|D*6^BekF`nIiJ~vU+jiW$lEG0DBPFofips}f`p~$h7^@<u6c|`mRIVtFJeRNMId=;Y72$tVDi8u-ItX-+!igF$PT!Sam}B*Y>Ab?{ffRnH?+y9JtbvzL?`!(cO_BSx*TFKxWP7~BPM-1W!n9K<&mkbC)HU<Kho?IG3rC5wq2YW0NOn&e_qnEm=dZm_;*5Dj!3LYzv5pJLw|bzA;Nx2YN;%BBFYzNx)N}&xQYt(2)m21dWnh5(e|1fvDFyuk|&<Blj9u261mGh2j@}se%lys10%BPk`;E#&n;A*O?UT@sh%$BD3Cl9(Bz9$bh~1^pj5oAZ#w94Hn=CQJfu>;z78_g2X7XT{gZgQPdqBboC`NLQLoxlQv$Kl3zhX>Gj$zUe$+$A*VG4O)Q@vNX5^to>JhT%5b0rs&nf)7?7h#mECck#mnD&`2y*IKVJACFp=$tj5~R*heC9<ZhOo$%F_9@xJDyFMAP!YqkE%5}ytqzooWhk;@XAC;>luNC67}emF${GDhHFgVYMrrEI+Y5+P9e)<A|Hn7e=qt#h2<Z)K9rPIWReVdcAoO1C9{e~fyjz+>hZ`+9(#$mp^i3pLB>?p^^RoZ`BWadD(dx0CFGUrrW{49_QbMcq=d~A9j<Rk1mv$UHymd@58PBXKdU;gEkjDdE8=+0>cl+}ta2>5Y`V@2>ll2WF9Z>5jL`Sq7TF?&4zlnZ*LJ9IGC;eY`No(Qwi==(9!w8unR{1h!nAsN!@OlN2gYp(O`IT_YU1hZenqR#vY4(nMq+r*x;=GX_~pB9oXjgOWWJH+;M`|+8y%*^tY+fE5OVO%pRq?F|B&YtPi7UEp<jB9MF%`(dBPkxf~p@zh?jfQ&GkBX@eL9!p*@*E!9wLC!<oPs&Gy(F*MOdCao*20E7z^E+=-~M&v9>OOpSq&cty&|NFzWrv_-Wh`}`uj)N98n100%FvG_<LYXIk&fV`oSl&OAIp_eJ5j5S}ZP~RO%|3BJ4MWA3p6iU_onA`qD7>q92tkrWTUM75E%dDB(VnGGRGoGqDm$0Q!)uozP`ASMYffpk2F>SMKk?{Ghw|e1d=4EoV_Hq|e)ll*7qZ%I;*E8;UEbpY2uNUO(uD!X6Zz1`!xqFc1bcm}>BxD8PiL59yvT^|)aj^Hum=kFD^1uiTz~uFMtd5IJ=dR7X|H!Q>pi3xA@0yON>MtkLgq7X4s%o)TyD!`IPfRr^$Ec@b#^iY2fvFy1Y)dc0%MP^m%`26Gkm7xT&sUqrBy#S^Pr5Y=rP4<uzT&7dT=NATiL?oN)0N8Kwq2C*4=plWfeW1%+C-Ew@uOjUU45mzQq(A+QKg2AcpwIA8=|$cz<qUOtl3qs)!_}ndWma3#q{n7Hm^-rlc`*NEoQo=7~M(2RuOCBs3?IB;n&Uy`|VMs(Nnt`rzBoo^`P$?RcdH=0VI)C^D-pzL;}s~AejI8Ed%LvRW?&EeK>jbb@Ac(inWUJjNASb|JR=xo>Q%-0&EeML@O&F{BxWA7+<}{E2<<@Q|L3Mf!3yNgVe57PZ{ij_loKH&N6Drp{r5s#&SR*{En#ozfw6%-0(eO56~`v<Fztpo(AfTDVR~e!sU%Cn<EM`>aPD)<9`0GGYaH$WDp+{R@N*1hz+epK3e)vTp?U--zneosc1s&7*`KB+m_%m@<x_#p)xqCuSV@y&P;IRH&#*GNB6{`IV%&tiDPIt3Fn!ru9Xw4V^>vn4dPMTg{&01%@qtkSR>&%T2og4JUb49EEyc*wm{huApb;UfK;f%k^~KEKF8%>Az;ncF5tI*?EcI#Gh#(Qb~jzGC67y?BS9=cRyC!+w6|x+UoaLxd*PLURRY#RTM#P9R~hK+Qnhm2h2#F!Jo3x=`of?n>3s0~Hae#pT;oW0pJWB97Ef_hU~H#veh`BeyHJ5I`espC|H;v`e{ag~4K&}Hd0H_u)?$ID89na!Nuz2eiZt;h%YfyoHiN6$^1(xzL(Dh){Pu>36l!C?vBd)^azlf^bUiSs3FUR!t(4C;su*-7=Y`e`7X)8S5xdmn+zOi6)Uprk5IuFA7WtKRDS2S)rReN1uX?C9{PK(2&}=$S#UrVM3A0CKOUs(<`*=Yq!-Jlzo%zf$J4Rw^rTYkx|F49>tg6Q=X}9^pdVom7&|G@bVWn)T#&k_92rt<>ulzltL4Udywj4h}Ug`3gE9oxgD}MM|&|7-lQ#saR^nne5o+KQfdTD1!R_2B-X4Ut!uCMt@A$zX0Y+lq&GC#DDV}%Sz;D-mkS3+L{qe?L+8^6%`y>^>HCO5LN)!lnYX*cKI!cH<Y%woprl8&{o-wv<*r4;KbACzkonkm4qcw><vOh(!<?m0fw_cgBNA{8ZQIzuCA{n#$0MDJ&NdWy7roCzvlW)l2v;*1$b?<hr~7Luc$geknam%r6gUlsCFi#0vq-fEEp#A<hvjoQ4_mk6gYuNb_hd!fG8qJ`Sk{*y0^ehAg}ro4!7;<{rPWhNz?o)QzenJML`%xhi4u&rhq7jYcB3^&h<uJ)z)TG`->j5d;YQ+n^N&IGpc2){`mzu}3g-6+WP_*&nUtrpaP$Q}R>p1`}*%MYJ^%c}Ck@(dNPG0Mr1JYW){*ap*?<zsicFd{Jo>TE_2d)fS^%j<&R1WKM(xFHc@o#WVc!Qtxqmkjp3@Zk&JVq(VWR#_1kZ%a_+p?M@vO~p5n^bKW8_<1WGMuzyN$3Z_^NkP{IQ!vQMtvu^G)5@EYIM{PeD4dfEiHRBk%alase$Iy5S&#MZFMB*rC(rf}X`U3)t+~faxsoix%lOa@9w_?^@9F_N`YOv1Ysqatay?&u@)LFiXlrEHR`^FH*yV!B7Rf-PijS)zV>!#T8u?V>3taabL7n36U^(eOhsMS$9m+@*Xq_*m(8E--T%kO77nI3o8-{Nljp9ELOL*8gco}w(tj(hwD5KVv>Nutqc4W<!%*&o-JJ(Tehul3WL;G582m4-q9P_nv$d<xa*->Y5N~ZE{1nn2lA-i;C2gau%)z5)b-bNPTP$Ig5imW&ZD)-d7S)csoDsDrDekOiHUe?VI;UJfP5HXl)_o&J?Pj%8@#+o?GC4Fq;&-lh3a{W{KWyee`%7N*@Ug`y&RJO{How-Y`?s(F;L87Q4I<W9Euf1&3I7tj%3&8sKOQ2|#9X5_Bi5+@K$U1-~!8lxZ{q~Ql3(r_D=gvn0(w~9!og?3J-q9hC1~+^d_H>}t7?*(@x17{5BR5rNwU+vfKz@f4E7i3gsOFx9uAg5d@iLzFt4Gh%sxcjvv21R~DLlgRoU|%tUfG}I8+%Lr<!%$YdXW=xnia(O8r4jKnz=pomyND)WVE*?bR;Wf3i<-9UY<XG=>`aLe;3}g6S=(QRiE{`7{ao$^xApW+I`OXRngh!7g3YjeW8&SleY3AR_j1Q%4OP&*pPjWwDKoya0D?tVqOseyu$1%xOlO2^L0g9yT4kk$trD{NDXAhHJZD*<?p?A`=|WRso-Q6>olYgnePgKT<M4ik)+knPTMppjLW=`@-$Q>Nlvft-@r|c(rREcj8hET(Ho6b!h+tU^GIutVMm*uQ8F1M0>sfmeSYC<m`hhaW<e;+B8}zZmVd&sQytT`w)oWC;=I}s7m=!DSA41i=T`05;A}kz%+Knbpy?i>`NqTyG<mk{&|bD@xu}WZWyUO%EP0r{>66C_5abQUR{Od>c4nWY5(lcxBfor_*0@i_?~GLDS8QcUlUN?Z+S>_~xI%BUJFK8qbs34pjY$j5)(hTgEiFT9InYeTOErZleVUs!5zU^ib{pb_%l51H1jcLpcTuVMr0=Pj&S6Kh(Ry6CqH>_%SNk!LG6-IcDzhai6;ZA`#l!K*Dd?o;RBSFm%R_dU!FMf!NU3YclHK;sq%3<jzSNW%f2Q7DO)Au&hook&B(%>gjFKye%JpGQ;!2t8wcsncp-^b5{t`6{nqGH4l4_HOAzj<w$rK6HF+!$t%QQqIQ=3SgJDRe4a&tdiH}^)ao}AqIISzYFMLHgXLyAF7dmB@^lAYHolVhYH`>f>s1Bt@W`6H?K1H%W7B^SnQ3%K1_D>{6%b_S{Q%oac_^1^Ii%8ZOxwTDz_l{oECXQE9sP!{JCep1T9Z3%giHg%s_U0bUkB~WTQ%!u$K(~B5gI+001tI_iC9~sG{(~!)7A*XV)$%Nq1!io7E@rE^#^+qeaoB<{K(qcK-$JS^SRg@qrr7V5Xd_?3aXt;*hM5QFtooL@1+TZhmbNd%p+clV(%Wbx6XJk^UMT!VyE?U#6QSUfhG4wkPwPm%KDeqp{JoSkvJN+~))3=V(i!qJR!ywhv6#q2&bx~F~Nt;b}ni_)3;Vy47bD#F4g`#0vP9zYz@lLXW7eUuyu@+^Kn2gnLfhEdiR^)Qpj5<LX8M<Cjg`zwK87H7fEA$PcTBG=ZtEFh%xOGtg#k6bcUw_7L8AFNitNF0nK@kb-BISL#bgt4pq7<N}i$w93qnuDQDq^aZR`QgqWW<K=RA@;*^x}uj#BX#-EZHQ9&^IA}iQjEAFyt3+&p(zv-sTopJH7LD)Rd`FrSBv6L}+DAt@BF;c7q~}s;Iuv@=oxsULnXYq0NIZT$5i`=@32Kq}o%<uM>5$I?>g-F|YBIz2fp15w$k9^_Pqb#pXvunwIn4a51)DomK<sd5HN~o=T&4Oi)eq@j&$V>-hNb)6a8RJ7PuV$?cDGMYT6JGowtlSpH_kAI>noYzt!LcWE+uSBZ+qYC8q>sqK-jd54>ZSH0^g+2+2cf|0#Rk&PNZt&MzSAjIDIA%VYyc*Sv=8T9q4s<s~_)Gy$((0|B{YV0bDL=_2@YXqtGAsc6u-E?}Y7Rk6jlD-zSl`MzQz?)-=<8IP;m5$5g8Em%Xlyj_MAIp05XQiFqs0oGesC(B->ZNu~Gb&C9J`FD<!XKc#``~iZ6X}Db)wJ1bX|X00wVdu@MaN@bGYkDpiMYVe5&Mw2=5DYBpVVHRhB-+H6kxsrkb3?vZI*bLoP8T97raVl6YOdXUZR0-?K=CJ6MxS46zZyh6jL(Rn}OfxrIWj!OvhYn8`J85zxp@jD{xbPmwk48_?Ammm{OGkn+BZK1#Bo>m?J|<QBp=%GcWuIEUU>8U0zIQ19NLNet(oc$sDSA54l%UrfS@5C^1}``l^1e_CICUh4Xeb)@#d;(522HMFpmBHT%oMxyYYU9jsYhW$~fRFeRuXDKD1}TS57jfq4@QrbsiFx02ZqqzZ;VXbfwY(Db($($`$#`kvbU^4giwUJ3Q;ZmG|wP`TByTQIME{mV_`!<F1AyQv?Y;$eNRoh^g$4L`dNvt97Jw(@9e8k`63%l`N1XUKnmbX;*)#@!8usR~E(Xwag=+ucWm-EEk*!IRgg@dTcQlyrNmVPs{i9Q9d}$=w~qTbc?}b%}%@IvqjlpW&)pv-4z*sN}Dn{HYEv!w^C2YZlDZPQGyLbcL_3^nvzt048OGtp1PG-K#~&BW~@>Z7$WItgM>9Tg;rDajA1XoA)wZVp#nF%j02x0)g9rH#;AZT~t`o*w6h;8k<|{QmtXBC8XAcQ(SL0@Wsu%ySFdKa}6U+!EVn>6^SAScT^e6b{2`c^40|5$njK*d~EVs8{%%mEF2{?_bn}n4I}+TH0&j>VR_sof8Vm(i_GGXjJ0BU{kCqryt9$GF1V8U#fvs}w&SJxgdlH|kan|5yi1YM&o7Ogc1cgr`~@H)Qp|I=`T=ZH4_u~|X}Q8Y4_@-9f73r&THi{R@mXf#>q+a*?<$e4yBIdOQX<qnrvRiiZ7VD?CuN<*J+h(Rbog?EPQEfv7{0CJ{(5XqB{>~VDIU7W>e3sv^yQXp@Pfv7?&VvFu#pZ!B=f>f-=)1TUtYk7he(D@pJu-ts8z9ARjo@ZLSMM;32Mz2uowtA=z5HAtbUK%>6_yt#q0*sNvKJOMaZuN;%%k}8`;*kY8OW@g&mvvQmrd0(kasDiS7m?cZ(HFt0qNcMN_rIFVWOvX_S(&rVM}C)x?~VBqECgWlr!}K8{;D1r<)DDA#;ZV=fjld0-N93FJL1|4ykjKpx&Ge}|u%tDOwE&XLq|z>`#FwY8)ILFD=U!fY7K)sRu+;#TfUWV(iy`@M){zaq1<d?e!0V<YJZOofNJAv3ZI&r4$gu;FBcjFIX55I;+n%#Z4`Bz&#qgn*+<o{2y?D+OWbtQ#${3}2e`rA(<H6$wS&%jPeUIX1_aOtOTf!pl^32;5r(SY3@d>Nbu`VLj(-+JzKUvXT;Lvs4ireWB}QElj$R2vkQe0w0Zv|Ap=(lqb)eA2}E*W^rN(Z=S(n+<mx>H>rYPo=-Qj3{_s0Y5S|iPhYJBsi;B75Cq2@O|DP8(cq*DYncw9l-iu1gsX)?nNBSH2IIxqGSr{CD!UMegz9o4Em+$I#`?VaYrn8N3=}5`bHo>`7c_lpD~%^wN>r0~mA~LF$+X|-{`SryDO$^TV%juPo_e)4=5w#X!#cl8t0~GikSKwGe{@O(NmNn^yKT1Kr)-xhaq=2XRzP7tyiIPzJfu<z3bHRcPn5#aLgFt5k8ngm*&3NM;qR!`0VoY0?yGLvbrh6HfT&W(YSdpi7D|QA<uPL0idt$L5LKv1)pQ~Oqk4};dC4L<mytdWL<<q*(=2~hbJ?U`<>C>ib`0(1hp^&XJC^(Uh(SCQ%bLBshPe8dnTNtk1k3n+g4=;%?2Nq>o(c3eQu{^#L)ztw>Jo!}s&CTkumAFIfBftJ{L|lFAL~Cp{M%pt{HOo-;qR<cYI)kPU;Ur|`^SI&>mUF8`j_;_5C8iw|NgIk``5qx`P(OPuQ`;DAO8JMe|r79|1tmc*MIdUC42n}Jj(0;`}3#YeE0LGZ(qK>j=xj?`SnNq%b)&v^AmpY>GQY$efia|zWpy46R-d8uReYH>1Fe)z73>rzw_5GFTZ2{_9=Aq^)X)G+XNwo1%ay~`1l9^?Z58ZboJl<TSpTa59e=&#xZ`o);-w3|2_vB)y_r_A~tqnV^76q?1RRB!(lEoB{W)qCcIxXwt~jL7c>T-ans~__h>9YqXcN&dqrcbXzcqyV-Pg@LbIZ=-O;$Sp|Ra2lznbA<{KKDq0tu_h(-(0nD>jubU<UCAC11zs5ucD(|OeB=ii}bG!~$-?;VYu(70vAxzH?V96;j)X!QF<(<5+x0yHW^V=gohjqQ#`JvN&2XPj^Z_a$)b{O~9Nw-B%mDYuKsHr4k0<HU7fVv|JM#bn)Y=Uj<>_e{1&dwVefH^Dh#X)Y$;j%9CT%tYp5^2+2bq@uqu(eIv#$(UT@BxiE1v0EnBzJoEj&TRH#f`(%+CRo^LWpdqj9*Bv)HIpd21onsG9&n&&DHOf@_Y6>MPbjJzlm^*>?FS{IP>eSBqoN-#tzH-^_oQMTk4n6#G>w(cNsQ+i8EUv+8sm9JhLFmxM8;{U*iA<G*{PT=RA4g0O9O3BL&b$18J_2d;`TzZAh|Qw!CX)-DD}kGYk|iF<$_WQRj=tldqL>{MZF6s`hsE>k>eb}zo1NMjW;N&o9yDLq1X({iSy|}nAm_&>;+{DMPE=bDDHxCK`F+n-vbow-!&9-8Yr$Glz>99;%w=;hKjFJIe)>*SjZTw`{jD{vy2QWmGr+CmE0MwkGkLycVQ_NvzRkA2>wn>MFW2?v4r@PRP4t5!dz5PD(0dBih68YaOuQUR;wy~QAvsu%tS?BR3<9Aor-!7RMbUfGlOPL<V9uOgUm$eq5{)CX8QV~l6u3Oo62CCptzGj87?T@p}-KWyP!NA6n*PBoQ~u3QL(p<WV<lD>j~s9DotbMy=H#GBYTzUgQiOp6gxHPIIDqM6BNU2>hkzdY!4`DNy`NVqz2bIpLY*sHLX66iCZTqCaLqepe%7VeL+c~=p;q>?xC1>14Xw$Q5~U#3(BLlg6arGUr@@sk9zMmL-vAFir>#r+y&*9P|R7Ns0&Kkdc}ai>;(nXAYV`xD60|T4COlJPf!$qVlF5;DeXB&_k=2x2hH+yto$;CB0;ql#D#`D&&TZhB2f16#)`(J1~N=rcQ@Fcr6KL%PKwE*4ZuDwQQZ?@iXAX*o7uqle?u1Fte9Ybo4f_8xiH}^Z(ysJhT4#`V%nM+rJ`<qVZs~Z%oPE8`R|1(!=wPFroxFcVloU&>cV8IlTM6DzdKCk!URJg>%L~dI66<E&Q44=IUi{do;Rne+}Vw3y_&$|rCG}M&ru?{8<RtHT<h2FB=x18Fm12CHo;`hib;zwxs8_!456H(-e0?2m@p%r^}lwp7dZrzzBwlEyK?GbHR2y}I5`tKf^ug7RWJtY%SjmM^-nXPMs;yY^H8eBsdFywc^CwBWGc=-o@BLfG-~3sR$-+Hr#|E9U{1aVC$}lgn)6P6YKLK;pOfpu$tJa0Y0Al7oC@VzD<|D@*giQY4LIqG6MDzBn<VedNwo;?PtHjtGGcRaD#T23PIl^HdRk7}>NZk#6aSt`opy!V0}7^{8bN6-C8duFFgax!4x2M6^)RG*jwxJqYE0A(=Yw~G$|MWAn3Ty#t@0gtG)_#)<D|^ZNoh5>22`^YOaXIk-DJn!3sujRs?Y&s98J^t+=7{BPlgH)Ae2cNVo`^r+<i%@XC(DT$AdecKLe?8Cnyhsckn_SrZ(7bU!NA#*A?B0NCiM@renT+{kpox!$_%zBNh9SiYEqTFHmw&2CPy|pu$svQq_I$wh-LyH-Eh5DOl0o-#KqLNI99KI9c6rMtb8EK;AB#hSRtYQ(jmYzhN>Hrl$1f88KNPAzTjt1}xp;*uZ<hG=Nk~Y)b+^Af}-YCIc|py_n*=!KC+K3Ma+1cKcf~y{%2UCBl0~Oa>&x-!PfInEX4!WZN;h(_&H?Ci4xGIyEM3+Bm%qp%E0+&75op$Bzb1>d`n^kVVNk`7WINQ*#QSt)Ky%-ik7ZiIclHf%50KG|C8yS9@}DhjI#CIBA5F>deWWnA6yilR1==zX7Lped@_cpMaBD<b<zmR*#Fbb1Ih7;oF@pU}{{ROeaho`)z5wn#CH+1_fJFub}h<N*@WT<9Lc)IlaxbHIv!MNk1N^&I76wDD{j3s&h_GJ>cr2@y?LzDjmDz<a)I=8;%uP>VhV&ftCfCIjnB=`DvMbuzY6!838Q2v21wfutL%tZq3rcO2joz{_L<+Pgu49OLuD#b~;!VXfQ8W2&~n^DFW{uy%_5EYAJRySOLIN7c2-XBCyN`mTfChJRht9z|t2i9;`KoH)pQQO<={dz%mmojlwcFZ+iFiuxw{o{%o++29~>E!QC(b15rN(gbh%VU$DSAD}dU&H#87mSfYLJ9F|XDIRI<bcZQCK(i6jS2`u~cjXiG+YyDGq!Sd7CF(fS0E%^74En`(=$Cd4djbCI_D=m8xS_MJJ=-9N(hK*mc$?JE{LTlVf%TBZ$Nz0vjY=xq~=52C<PJSpDI;JA<<tPS!WT9SoyjH~pP(HL}Pw}r;=gnuwRWN_>Ze5B7#y01HHG9Z#nIxflK}&W!i<}eOrfr}<12nr6n$4iWJdV$js^Nn6hs23xThF&zk*xW`ctKmC85CMTpt%cL3eAA(EW5FCv6JZkf|fwjENJ$EW)f(yaLZ-TObaxBN@xmr<mJ%p2HJQAXr?1HSgHh}DUklZpnZj=S<p;Uk@D`Lscd?V1!($$hCwp`noS(6%u)e$P0wX|dSHz@Ce`&8c!#U0&fwYzKyub0&>UzyenCslX><BaEp;jontLD6>@akM=FbK#+z1*peG2abnhqm>ej0*Woc{YhsQFPAh77<+1X2r$`AQSDURQQ|duoFl*wkQ@drQqf4z=5-33QC=t`4IO6vmDTxn)Om>5Kyzxv^tCBmDl;vr{NL@7DpOm5?3u9d#g^=|R3}t^%p$0^FwXdhCSoCM^>Zgx0UBr`NwCN(e(wQrOcQTHnQnV%uBcRF8$zZblpQF14V;9`t^TAkEC3-_L+k;}cvDZ8%K<rv*BHh|?rv_e3~NH=M(!O*n>g0N+_pIv37lJ8?@g=HsTFrUlm!y&MGRT7g+~D#JNE4Njx2=kl}}&oSZYHpK%Dcs_Yx9umbo<J0i8X0&{s4jgw@|2|vfX_nZZOL*#A^VHAG(<H}Do2cqjo~uLBdB>+0^IUgp=o0LbBRlk^&Uva6@Kh*I7x(atfG3>wkY@xuRU^;vJUopn?(dce>%j65*!tORTCS%dM>VYgC+4YxfT!8;^x62diE+&KDB8;Np>ruac;=T!$kT(?hX%O&Z_CGriznbYB${snZkrxlk_^(U^p&Tdv_~?Y?$kUTxQ!by(^sAvs2nVihNvm1C*^6MhNlnZ{hi_&k{P}7G(hX7i#+vdc}C?tm#0a1>dl^RK^zpeD4yrL|Ms2p@N_re=|JU-OL#iK^KA@=9X$2Z@buAI8PAxV*iD6}&3H=VA?opXx`6T=+&Id3hD~wuTET_$bP3PU6#i6CGd^WJ*FxR-{OK7y-G-+)IzK!oPDRpm(v(jx3c6>z`&igTqABFV?Va-BPXNz(d<+@Tu=MrlAfy*InQsfGr%OVb9!zIX)YlIps-v8$xj}t>%2Zp`#&li0V0g$*lmifGLsf!Hh#$iA_OT!dRGUD3+dJZN8jJwy+kZ`>MfL!2AS{N9P~+o49r2Yjnr=)DU>cV=(JYGh8}3HR)IZ=r9ZLh%^n_{>s1`sC%hzvzY6?f4B2@P*169s6Bus}*Wv!VguS~~;sagJxmNK>HWa>A`^D@%`gwk`S!xWGcG1X7ApbpCIXS$Y{Voc3)wHYSvJf@cOsg7MxV`-r7f;uk!sp6E^EkTVZggSO(YEh=cl#7fDHI;O|jEhP^PfT@%seT7c9boDKQ=Kq<TMou%rs3(C1{YL2Q(IwbL07*mQ&nK<o`|U{E~vxppgPdo4niFXs73@e9tyR<RQVufYDlIdSWw;4wG3m5Cor{$X*iVW(2c1E>Gfe@8Ua(CZ2S%^sH)0TJw4Otz1hPwE*pPHn8MqsTTZT!sXhTyqdE*!mq887vEKuzYJzGAsOGc-RmRk2O#Q;tB}~I|Z7ngiU6}eOXPWBcVE%2@eWXk^$y7hRnJ&&WL@&5WZ8dUpj+kN^0n_1ROzl`2r~@CWUW7BLWNH0=4mBiD^*b1-Elf=&TUv!-Ia3dq#)PSP4@~!F;BN%sRXosbx)yX?qxPk;>V7HsUTtKLW>`2wx)}HjZGn~FB;q|NS@(D9E?Z#eZ=ZP^?6?Qvn(~bW>DF3`aR@^7@Ca>&&~2Klu07M99$_gG1k9Hj5!wl%-Iyh$2=&t=w2LT7r=!q?y$DT$aCJUcpy|gM5U!(e2SSrIA6R7@fkbF8ge8OqAYA+S8KfPsIxRvS-Cl$`LAaJi^+$MYUcs8uC>(kr)F?uG8icFa+HQn4Ll{8J8zS^eM7$5e@aza}hA<!qZH7>HL+Bq8p$UqQPy_X^1Cw{1$SUz0UJ;rTAYAXrn^EXHAavP|te2g7{#u`Q6p9f>1fd1$R14O>3n5YUog#!v^c<nNOZ(#E5L%~X+X?g%3&72P0FA65!ZlL;><G<J8ikRM&;r|V*tJA&zCZ86(A~kFcp^txm|@87$QVKc>T&GzH9&T>BX5du97kE?KW04+HOO+pG?PnuA0CxG>4$LbuQ?{k6K90UlTbhyGOMtMKuC_lAVTN^icl*zn6?DemZ8t=!5)HP=r|15P)$rBj#1qLqI-&gC|nM00ixFG@iW5xIDnwlb})sLr-bh@BL|oh){Vv4up%aGjwah&@w21UMU)XVJr|*bg}{DOlMN5bFlQXjfO05~N_cG6jRmd&+<)T&&L+yt`LOf!yG3zSDyMp(Gyr8tI(W`OuXqBKHk3!@xCi9`a>i@<uSxX676iZSiASXvC01=6L1pl;g#R_L-d?NOFO+EQsx6>Y6G{zG&JM@tMXAlO7p0z1Dp0Q$lFp!KLb<9nvr!rJ9+YbtRf;l#CR7GEKI=12a5+kgq8yU?vzWAAy-+gir&WgXZOW^qHQL-+c|0{rqeCB*F{|=BCrXfU&PJu(gK}6Vcv>(SK*6sAi3EM7RKb3f2B3_~81xBB56mbWD4RL~O4ku(Ud9_Y)sY(L!3I!76;6#(MZE`Q05@)ka_!d{PlmD_^c}pH1=%1<lQ{B0lxq*Bkf1bYp5PLc7Oa&P1k?Nm<=nSeE#Z$<taqVYloAniT+vApkOnAMn=YSpXR^;9`YodLQ4soFB~C7Dy<|WQ>0COlvR<msKPpW*L1x%HIE+8qMEveH<+x@#kgH7s<J=Qmgi>z~H!7)bwwtx`fl%IKf`6Ui{^8TtZ6E?|=#qi3`e0M>Tj5jv@Ri4rmmI3M6@0mUc-m;&ZLGu(%UpL{-G&>H+?s})q|DSkik#veB#q?GjFU77NdvU9E^#0_t;*@^o!Rd}83D@mkPW*)o20Q<czTphl}DujrO8kZAicjuX|kr<<^(9q+Ph|y4rB;d+j<3}JqA>}_{E#~LWx$LTEq&}FM$UGYOnm_$b8<lQujj%i+R@;#d-=?s43O(^zp@59+m9ygD;}o+NjU2;QE9pwYe+G0iaaV-rWzSI}1vm^d#Q;dn*K`?u^nrCQ4=aq1qg!K~O>?O0}Rg4~$Y)5o1fqRvm}HM`=lvx{6Xg7fK^L48_syMX58C=>%6Gy>J4Q>jbwOlwQeDhNNHa2-LVM$_Nfa{ZXn%8I^Vu^&Y$wrQM*kpns1_d^>H1a(sG}K;yF=l{QEZLlEV#q`2nl{<!g*&?iG#9F;oqD;ffVGA;(m0d$oLiOY#f@`vX^Iqo32H9N5xNt=)i!1&2bV#(8z)W*q3LSv4(`=(jw*~!SrfM!x_<Wiqt(^)GLHzZvgWV0J4tzFVBcC`wfNe&Ci+0Wwy+xLi*G;tjHB<&_=?UF>I1!bNlaWY@k7V!Z|D%qG+I7zF#y=%%E^SCp+lCHJ{0_}QgLTN}j{{$)P!|@f?HajZ2r`XzWoTP1$YrjNm6U&Zq9NinG+Zb`rx4&)Ox=#!mk3!iqB&K?!gqR{wA#dx}=N#*?GrS|p(vBNkSCVsS@LIMG^Vi`FByC}-bjrrPC~bmrTec4K*L?(c7|PfBsbdGFQ-f|VwN6RejHCu6O}DCblw>%Zq}Stqk^|6D#LY!HBqYsKku(C5*1ATLFd?%gsQ}5CcwnA@<eG)q49cj?UX*4kX<a+2Do`Q=Q4Y65>35)XvI}$JcH_q2r6?_la@g2+!z{uLQMw(+^CC)pJCq(p`8L7F1f|>bTkToW8V*KTn&3vMJt$YhloHC}Y$(_2!4#z*LTEv0lN#Xx)TXZ*m9(>Rznb;#C{>qH*^W|gOaShO(mg-Qw1ZQQ(vm1uH<b24Q5qMeDBT97olqLERvJ+L-y5ZAK&kqnT)n?jl+g@sFG@3^)Zkocz!6;m2b!Cqw0A>UN)ASEn?|JpmFs#!seqxB0p<U?^A3)pG&D-v5#_Rj`xIsLyHL6e<=PCvCs*)({vP*3spzn8igNIymzq-0C>=N|sU=lt7S+mrl=@hdrhsx((rqV_C^e`QhA3@El&S$`>^LfYLER%~Ie=<^jHLx3I1O0Z)38(=miNe8w}7B)t&36!UFr5|bh_GoW$`>_;m32-1&(8gJ1Si16t+cD*hh^@*Q5r}O5^~r4`u*G!yzdb-nK<{9ourZz%+M&X_WJ34@|r@x6c|RuOZ4C!PGaouqcTEdl#4%z|@64zi#O&b7q)!Fzxl%0Z0Lc1g1e@#+%6ko*d?y`<g2WZJ}8s^wqN$%oL`r!i-rX<qKvNrk}##0i+Lcn6r82DPR`ru#Fv}k=ejuFe3<xuP_w?^Jcl&LmH&-VX4_H^$l5u2A29BEJr;^S(?q=Mi*J?o3O<4UgP~x7TT#8<3`hta^8GkHa1780m@sY5Qn>=bfvAwDZLA&%}{z^%)Vy7+>KGj<42_gr755^MU-m~VgDXb`ay<r4$Z>L;<(&<<_V6Yyq!iMJiuD%y_2HUBuWd~1*{v6U%J#hJIeA}se@`qIhSohlxAa=<Uk_v3@E{<^c_(S2ucl#+Vv*;HC!m6S91Vmngj6pi4#h-X=CrF=ukgJ^n;?bN-NpbF@R>^5M@YET9C0_H>+?0ly)qSN+a{N51>>y0+b%;P3M^UDyj?}t8f}nx{jl=gwk6lHrcgVM14ftV8Z~&`rkuP`hFD;Kq5e(yhmEQWp<Kd$`_+#c#)hfk<jDtJX!6dF|Ja_Ek@6`jH2tZp_Npr3HD)Qa_GnsM8R#!G6vILm<@B<F)7RrXcz3mSlXT}W09o}?G1<Lly+X39e^(vbizJ0OCvcIQY;6MkhPOHj{&8K?#TVu-e$erupFc%#Td)AP%dSuLDuWG$3lO|xYWB@T7spXDmNogF+-N-)GV#A>d=Eyxc~~Z=j04zIVWW1FwZ$y4keaeyIZgv3M_9Gymfb6FGGRl;Ky-4%W>m5Jomg;z^Zf(Mc#&`y#-4n8kR%61xo!?C~c#u*#_mP_;wa9X+&c-IfXH?vly1>1kA-g8A>feIS4kM6r~1-@U<FtMmYkMW<eRxfYOvkrIXynw<w2Xf;%w5*Vcsrm^eQsN@1;BX{{V%bbC;`rLcHT&kRd>u?2RpYN?Dp1ZB^<;^kx+Z$vU?BwbSFd3uuGj_t+n1Gw%4Fum0j7}uNdcsv2gb)`&5TCL*P5@@qiGIb4TK<Q~tvS%sm-AF14NfW$lDR!`vY3^z>?1AKGCb`XcJtj$acak<K8?noU5LSmN;0-d9G++!LMAF@!q#A=*|Gb9L$B87=@7m4mhGnqh2}t^YleB}1GG#?dQj;X162neK$A^&YSWj$R50Y9)(gKq1BqR%`AnT3thi9;B^~AQRo_Ih<)L7u4;41fw`RjW^^aY4X#{?sQ7&fp%p(Hyba1RAKH1YIwXYmbBJ?!8aK-NFaRQpW^+jVc{JRZw)D2-3hJ)y!g%@)Rug)Zc26P~a&wweCUAv|NhzI&z3!$oM^BjGu0c*1gG=rRs_)AVfWd@Rq^(;^$6p^fL5@w9-a+hnt0lWctgp2fpWXPzqIsQ^#YxxMp)@{CqI-|a@j?55t3kf%+`44;9g?ZeY(@%|2Z+Ki`Lcw(7tHH9gkou?U!<Fgx21FVT5Pkln3I^2t=UwCSSr|!mcI1Nuj@(dYIm8gPx@eGg2)51$TpQo7;V5_4x<f)SR4td&cJpHljXW_mX;u!cm{f6fN(qkj&ys5zcJ_3VxznH*39#7p^0M?hM13c}9r$czUi)UsOTjIIiH&dQ^!?RC^Q+qF-j;>$Y@>F7;n&jyKPYoQmp|IdqJoS!xFd5HPeU<Wz);01RfSMo9_qD9sEtcA=j_oWw*YRmno_@4_cn+YtM1iJjsV>lT<7pm*r%HJS=%jC0tupkYq>PCOV~ukvaC(oRDZwN2R9$%b7{ol+p2g6_9QK9Ri#TJ;v)_5?Sf0MXb4V(a4ZD?#2Gz*0Re=Sb`Z1aB3Y<U3XX2?P<8w&Ff`%<of1B?<b2E2IWFA)ZC~*Efi05!~o=#bP-*WE;46jQ1hB$CQv!biYJft9Wc%o|WgDI{~@F_(*4#BsjcX3*lq`UsB+k`9kEO#=XrU-Nlx=+45Z^fNfJf<pyLx9>Q!CIi>K|6rjLO*kuFozAfO%mWtjgg-os4V~;1~v8s3j1=;KsB)8?pL*ZEKnB<JCQbK=qu@nB+!1HrF#PvYWZzPpf&?)vL@XgI1=d0DBfH^w})^$0ks>Tb44Bms(@Mi>47R^)V+ZYCjjbPafA-G4d}1|3LAH8knBx?_OqMCfT~BB^810>1n972e>Ct*g)I%v4b&^$mPi{m{eB0~O%<loFrez0fGXJ<8ek((DbQE}YBmk#?P-7lf68oxx)z`o80Ns#`CONq1J#{@4#$pA-5IC@xgVH2Pl4J^t6I|$Xgn6Ex*O0DO!>Uw!Rdi27rhjy-5439yZpG^=+zVo*#aF;0Mr$yyc-+ip<AF40qQq~8$E%B#~h(XaP>^f$w!bghuXJs3F6%rsDBioItA(^;X4bGXd?)S=p^|#$3s<;AXY#Ma;xgo3ea#1pkq4Y#~ArMw{4Z@<nOk1wVQ69eq-TpCaLEMct)J3jh1~+%G*>!=NAu}8aYsw6_R#F=B5?<cbxF1z;hfOpQp}vx(!b=@pPae3hcCHkL202Bf?Ukk#0y%oAK~!b9IwKX`^VROV|voAv|}v`CTdM0!2YRnv|kN66mg50=?k`-qxQH2f7M7dI2pZ(6?>CVRviWafluabd3x31&UXk!&cyFV!dAl|It8)-asP>)PSDB7FdAKGS>@eHGvM@=;zw<9H^N_?gf+tYBrYiGf=yTE>ocP0-7rl1`?>+05!n%{{l(?-R65W0ICq6b7t+dK>g^N6bU&{Sm);e(BavE>bn5V6X?+Le+KFR(BT4F0%|g#Is>Y24%D9!Xhib8aajarplj*XI{-RpW7>d@g#>zBPNq3fv#1jeiH@j_ii8e49l|rOJ&#KaB;`3SLC%Y3UV9FclP0N^hCDr}J%>E?jmlqc!V|B42?d_P`j*<>5>JyDh~JW@z86nV^E3(1(F{#IZGoqqc&<KjW43;(=i+JT>Z}b<XY5{Ygp_9hy=pvIKi4z;xp=0vlcRMzc*dlbAM!Lym^m(fhU-!PAjRPwcn(%7=Ze4^AtbFSR-O?U-_L?W4^H||#S@q6;5@xn60hBrPrC2uO^PE<dlt@9Kcpg7=GC)S74+e06Q0}JbI5a+Z2RTnq>s|TlhTeT<EaWftul8_oi|{hdt|>3g2GL4L@%ngKtlWRd2;86V{{{qQAJo&VcFt9POI@WY8*hxw7Y4^^gggk26nwE_66(EzT;TYblB(=jst6-0jx#AVzs_&?l*L7qJ2Era7(b;j^qZoJLh2IBnLS=Sl0{en!3~pSOto#*A@ifW(BLez>eLx20m8<4&~cy<^YP+v5M6JB#9rGYwX4~_Tf4LuF&?`C0xyN<$O@Cp%Ygd+#arG)56>WuByUSpMa|~#qm1y;%Y!?OW4?$8qi95=-7{YIC{MLeq3$FHG=+sVN=ceKDlZiEtjh;at+Hm;HDK|<vPokBH*fz<l5HONe2;D2b$Pbu|mI12g+Q-6066su0tAPjYpLaw%Mr}O&4UQSc4wI9<1vK9YKTu!x}&^x*t}5FRV&3Sfd-pJyh2LIsgT;&eni=&0TFe`}F&5pz1oN=Sx(5)H13Op&B;EYC35Mp~2Fy8b%*R)!crp4#rs-)d8UzLBc5j!=<&&MoQIobFk_})z<ebNgQhk{BTQ}^7NY)dLBqgX4fURP_=-n?|6H4_o9lA)k0ce9Nf5v>T1mZscJw~PgDb-+AoOJo2u$THK^#~9;ybV3ga!ac|h3Ia{HsGswS#NLRD+;+Np*D)%kcD0M!T_2l}N5?7gUp#;UQ=@TnTm{&p)bOR2)Us{&)#bf#+h)NCI})h00(oT{0Gk73!fW~#$-Bj`z0A3IhxgX%rf`3)E}w!geyA)8##3(jf581qEw{KGL8ywAVh)rWA~-s@>Pzn}NHZdvzqN2VqF^PNoT{_A-re-%?4#8mZUYP&O~3b-Ax7=XEE*YSXUJX3QwrmM0<BTQ{K6ZCU1rF+|_OxM0{0fg$^lCtZ-RG*vadT`f(>Fk)O08@Q2C3><Cs9(RHv^!g-8ZaF$rX*9F^+143Ezp7wz;60tikEbcsOi8g-ZLaqeKD;twItIaxtd>0YjwzZrTiS&q?nF}iFBR-Y0Qvn5~=BkG@cVFRxJ;aI)HRM-h28HFHv-}b_4QpW>M-zfYcuAK7A*oV=#OBwVMi3z1S$bWBsRxo<vnCSn3Det11~1U8}qyQQwiMyBkp}BO0Z3ishc|TcTznYBHh+`8qTbMRS{a>`pXhUE8-rZQ?pVE|ICR%kAlGMBn0dY2S9(t;c|<Gwh>18)u!Ds8h<e5e=Yoy8&Zy6*4=dleV2ikcSZUB++6%Gt&7?mjLyH8Qbh}0%$v7k~a6V;>IN|!mI9SJSs72+koOd&juW53_(0X?FQD|f`SGbj|UpsfGRqhmjWGh)K8vqFIRaP+L~cQLYd(`XWWGtSLH&2F)AAYM%@Wx>NRgWH*W7FhH0Lg-BE56?Xb6oO~ebPv;V-+D2M$h=?>!-<kz9Uyq``vwx3$zV3hIJC`|>W=_gV+8_GzaGzd!FO`D+3gA#AhZl)x<-=rv0l;+GRod6}}+igGu%>a3D=#J99UzDnIviwm|M(E_JceG=NC^d+kpBSa;j?zxnauzsQL{P7)I?D}CfRb*(4pEv6rM*znnZ}r)T<wnM>L0Zvae9gijz;NkfpS1l1{9?^HgEF`C|v>NS~nFEl;#8|U0;;B_r3x;R|in~1f{)DQcczkf^w~lcHL3x$3&^eQMCoxR+M@|=`)njd`3-c>uFIMr3CRxys^5PP=@99ouV|$4jwO*rIzXtr3M>Lj?ztAkbSC@p=_=6QE=PYcK;qhH}$#l*`p}^v<00Y$mUI9RBHaHGziLd+nH-oaFk(b4*vW>Hr)F#+NcyCrQY<OAA!`ufNu0DO1qpc&w;WqDxCuD=<kujR(F%{6b#=AE1ey^ex3~W;S}+f0x_!5@?9P&S|Lkd+wA*(X`lY_xY3Et($}nih3iO*%Tlai7#gwSRpV(g+XCB?kZA<ED9rT1T!;N!Eu)t@w12n2;u&^ovK?#k59eA4N5&9`Hm-OFaGSZm!w%qc$EJRD`FG@MXeCC<Rc4+?bA{D;>wzfeYL<@c9k{Avxt7LjZ?1;LwVx@W9v_u!R8p?>KI<BAg=YIV;5zi?YP)caqZXeBsCMfZR|B}}q_2GkuHjg&rEtgB@#^|;g=M9x$W@(;s}6m+S{7Hm=@lN9&cVH`bhSSZS3_`BfUCX-SNEV?wbAWdBM^CDT-8$9rvX>hldC?MYvCR{gec%j*O)tC_DFNJ&&XAY#_LY5uE5m;t{PPHDPWUuaiu%7+pI%-jjQR#bvziW?}t@avFf{FjgN_S6j(sl`n6k7CG8Wn(iW@khPBrrOFahGvO&TCf`nVFA;GFHtm_#o08BB#su!#lU>&BvKP*a6HGTiYSfh%<{*VFKbA$vdG?nr|JF=QpoDQomj@Bq{V+b83wpd}}dB(a%24-8Iepqd9tft3k9kd<|AFIx6CDy>onAmi#SOaLYHDm3!wzeExO;4^vfvfTAzLn{{-1k-zufh&NF3J@wx4(`t*n#xnYtxShsY)P?ja=D{XZyj!<h}!c|2UkcCrvYUqv;q<@UW-5-Sm1tHO*jD8%@ds9_B|a$l%$-*37OmeN8iKcO#kuC<wM7%LHkflhBL>nkF$vk<c8_>@qB`*1+ayZQ1@fG{^lg?GBi>027AhAxsNk4(|Y_^;QOR-c$1Yk;y7BVb$>5^!`*Z^^IYM45m&xvY#2I*Rc)en8DP*jrf)@$A@95y0f(4l8v!cN$d5C<r_-_ZaKM^`<A5wEOkeg!-KNa5w@+CvV=wJ!`)cMV_B|!)i*4y(Waf{kg?PW%e8P&bz~Vjv-C1U?06%TYj!dMlnS6U6Uwn0N`H2g0nG5XF_@!NXGW>V(Ms<<9!>7fiQBkAsX;G+J}BLxD7`9;$}x`8`?y~Y>M2SM^5iQ@*nalOP+HpHV@ybTH~Kb`5onKBl5-p60rX^8PnPPDY-h%{gw0Aay@`7tRU63wdV*=-;}JJzXEVw1EF@ilqz$Hpq?<?@(1=@uh;LkOL6D?=B>$dPlA%Cy977vP4-&7CWZ0OM!r5(3MKaxSf>Lo0Nu7C;2Jm0IY~Jg9KZK;ENGe%VYF!`+vu5{5Y&T$t6ozu4^?=@yRB1$ky8VYwY99>I7pA4N790e9rv~Sxgmw;^M*K}4DhTDq&J$J$*%c%{&cVJYzC-PLAoAQksj*(oyZmvGRZqz7Hjt@8_B{RVlY(ov1U5@%0nY~6-UqU&K-Qr8+ASxll5@c8vErRUwk*i80C@nAS4)9FI_Hn?oN+{(rk5Dcot0F^n6lK5@0Ky{sXu@k7c<qkK*r;S@h~w~L|O5BXN;G@&)t4=Va*7VoOUUTr5T5lFb)F7zL~KuFpi|9{K1UXv5a$1`4KSInW+P0tfvNokTD*B@#kRd!zg8JGRC^fSS5@NU`!Rt+2>-cdo#|vvbzmqmG~~xjMa%5d#8LmW2}TeXS}9VZN_*Y8S6)7>|~7nz`y9x<@7dV?5m8&o)t>rV8*H!<B&1Vt7;WstN~-VRt)_ayJH#KLKT?z!AlwA1>r-&cxz%XpDT1yXWyBzJ(zJRwPRozvxM<hOc0BV*D~grv0dnn9SiWaIhJw3q<9!q9NQRg+rI~350f&6ZqShNTAv@EjByY+^XxzzHr4n6gnm?F%wa)+ZV7Q0QM)=7VwW|D_W-3r;zAVS@Q_mXPK2E`EoX|f!MOon$4%z~Sjgt4^*SePA5gU2hw!MCm~g3uJj^q#Rr?x<ab{`5mau;=!UMh!6bKuA=gR$|kC*&d?S*dei*DiYI;!wYW&1}{EF^}9;JwTa2BYOSnRN%U@*%0&cfDJpH*obGx!OWFafrt5;R;ihcB5*rSt36D2}g0&PrwzX&`jpYzjfkvOGdq0P5;qc^*y=j0$0Bz(ceb%iMbBr*o&)1xel2oWLA53;o3U{E96?}bRgtvz&@0x(iNMl>876T9<J)db<|q-<Z3dmV}Ywa2Um9+u4YM@$Al|1I9o6M9t36eV}_-qT<v|iTENu-snWaQ>Wp}OwFRy^<Ek^Rs~@L&D97klu7%DV!x(JjcRb;8RTEbQ<X|`Ast)GbVZ2%phqf8l0P5pl!h4v)PiwkxToPI*;EIpeQ3*O7U|e%4?Uri<T<zm?wKA^0fYlhk2kYt!<PxkNU=52h(I(4)eZcs>kgDxPH5RDaglbr*20+ySw`0{MIM6%dJocbEj5Y|D)}cVvWK{J;H3F&{cuxBVv}7q$je;A&sKyXw*2V)UB7;~pNM=K<9#qSxSi@6c^=KznoT}CX+c4TARBhrWFvkUEs&C1q0hBao;5+|ZRGo<G$UX%GgsK6~0&0nD&kL(w&R!Ow8Xu7A(21%Y`Bcq@YCx!ZKy~diW5IW3flGWqe<mSST^y^1PZjny-nQn*sainQf$z+w^G`+9D%lDkSXb?)5qAJyiWpT3sCpm)I6GD2fmr(<$@~TkBWX`pJh<C|?(?8GBobGaN6+RTj<I0#H#!g9k4-1X0uRdQb0>qtkU9jZYDKD02dmMI#<T-1x$yfX^NG3hA2!w1O@PKuKq({skN~wC>j&2*=JB9Fy@F?R3DAM?;!k^JThOh1E<8RF(9jGtt$rU1cKiVVU8N9n@@_VpzJQWI4FPmOfT|M%HLxDou<P1w0jSEX?dEzOmsoh82&nH06z`Kg1Jx){e*w)a)=d#;1VWJ<sJVcafZ`SaGf=(hjIE}X^a5I_lQu}b|LVU|20EKmUqClN=l-i4pc+j1^8>YNXakB@^6ROhRBzfft0@%sz(CdAfjR`JLoGgrDNlq0jTg|oo=%fB`Vi;<n)9eB-+lqjN<ej1EDj6uV*(VK`=1`@*Z=b^Kuxjwem#de08}SHAM!3=EVYk(o?59v>pmkifF@>hnXTS5YF4Cy+H(R`eSpqWds|qqlB(Jjs0Bd7d4Y~&aG_;SO8eWdRrD$;Y%t4=w_r~S4;f!pGM)u<jn@(C#ha4dw6=#;^C~HGvdb>-08xJiqPhUo*eE`SZkyV}B6$Viy2%e%gB-i+R&9GQ(9#-e2j?C=jXqEuf^cBP5{R#>-vVO1Q4;<6@!0}C_jRdb<FlJwFSPZi?EW7QpB3UOt!qvLdleo&3xrgDV`pxF(}!IY#fRWC_rV9!WFw>ED#aI2e6X92ISQZdiLbZ`_~@GOMG{{G_#W|0VmqDkTmTKmMn)&bkl}mFzd{uO?22^?e8ssNjcKN55_<N$^i*$pTdVL9&@+IZJ~O?qw~5fS@C}=~+;L(RfYo8Y%KW2e?ob?jmV4;4$wg}|11aOv4~x(Anz}Bs>FKN<?1AaojyH}nJ?}*HLPk%4UI=rU5~Qae@WkAUo&q)BQhKlrd_?G}ho$F*3!f_vzBq~&zS(hX+~5n3hL2qMT(7A+7&bi%^2d;#136~6@TqS7P9OBl;*|=bPywU|i`_kN!GPYu&qgnZPJDhaqA*`fO53;e<`}{1cxRsM#D~%|u{ii#5aA2J?H3w_&G`Jrh|wN}Pq&@;M1wC3mVah(8z)}}>=x&q7=B|9YLB|Cwb2_S@S+;W26$<N89D>PGOXK{x`Z7^mOk)CJB-cQ4VPHex&pjg1xWSLBTpM^^^?MTE&uMHVl*{+U;gv|15VRo3j")).decode("utf-8"))
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

