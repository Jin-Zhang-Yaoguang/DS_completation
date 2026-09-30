"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqO_Suvk)HocpZgHs0QNRZ){-<0*|eFV+E%o-HJX;vuE~~^xYR*L<9}CIR|4=rxO=z<A`_XYybO!g-BpPP@#+5h>wo+3hyVW9fB*BJ{`12>{Qhqr{>LBw@*jWv%hxYI{Pw#afBf*}<A;Cy!=L{3_0PV3`5%Ay%m4c0U%!6+`w##4yMO+d-~RCF=fC^ePai&h`25S4@4o(T`10}hAAb3(A6`CWU%dX^A75U6{`D{Z`sMpizxnWS*nIo)@8kUK?|$>EUw`-g*FX62moG2BWq)w-A%-ts{{At0kYD}mzx?jE*$-PD>h~W$zx?>qw;%SKPe1(h%Wq#@o_ziSJ~;KGR{+gFnq<29o&Wf|Uw!}cfBE|FfBM}w4B!{8zo+S8zW?rLFAJvZ2Y>ye-~6<^zSdvxPp>aKC-mJ<FF(Bf<Kj0gKlk#hm>>MJ?`RV1uPEp+KXLxM-5D@%PXyy_OtrnmWjuo4B!^tSz4>FljnwtiseqL4uH>-(f))9XpMIx*hnIiUihy}}<ttl%SC=WsQCWUL9SSlBca4hj^_3qFAyNOJ^FKlnH2uWOgW|(MKX8!`*k=&zT_Wlv8rO*G+9O#aUcOV4-kwC@hr5iwUYoXHLyq{_#eS*4$bWQsn8A)q)X&~Nf~}o9S|;*36!I^)AM)w@?_YlQ)4%-F%MU;O>ib{)w{I_L?<Ygn@rI99j!o>ebSIqJJ{ogq0ec0tJU1TPibYwsS>&^JSs!+=D}Q9uW>fx{w@<IyV2~ezeEPi~tcna-mx~|r^B+F_mi-}@g`52$*sbQrm+xP1a^Qhqmn&?U^R;EpQ)m2q_ZBSTZu_g=9-p5&+w*?=#jtvot0MFpgg^fD!*`$m@#Tjf{u$XWkcV6L^vyP3vXlG*{&6MaME;4dvC&hzvHb9?S*L}&_x5MEZAz-Wt+st5tA4rHNv9mLUA66dvhC^e)y}Q`N)W4`?OKPRc>w~`8?H;6Z#OY)J1SHtt{1B!)YE#Y)WjCJt)7UAH16^mXp()tel`^x()PbU<bze;UfT&ob*7LVY0&jev+MSXFgKsT0vSH{U+!}&RvdRk+jKpUdeb|$;)97V*@{g|xED8UFxc|ni&T9#65q4A1C3xS-u&yvV+*)oTzCK7J;v7Ux7dhv`yBRz>QBjqa<?JZ*5kk?P}#Qaavz3VfImui7-p+RU!dSwm_1ewM7YOZc9yGM2Z`9jZFX3Hr^kV7ZOlu`{%4;)i}vK@H(&mN>LSB$&d8tkzfN}y@@jTQ?joq!8oAx4(@wq3CEWw7ZF24FDE{t;|0@5W=neW?GVOI3XHUKSU^1q*WR$8*FTa)v9qxd;<j|HCzUd|n_Btwbs@l@q0wu@?gKv2Kkm&1a(LA)g5$=@MZ`L5m+-k0XJ>BZ&3VW$&$wQTg6Kq{*QidSsK0y@d@{iC-p!hl4{VI~1FmllNmXE%CAMSU|eyzV_`#quXkHR}?d%i&!LI2pek;{(*?6<CQr*C{D)qTJ9p*XG4wcbqsr)Y`i^YX)%w*yyRWECdAyGPe2%L$a*KKU1Vg)f!^3#JH@?CZ66x~$#H7sP$K{EHX_)v;&!Nz0iJi*0D23d1htvnaMO<accUb@i(T9fRo8FT-Vj+JZ!bD%;8j+V0e<G=6#fSt2Owr$D|X7mBn6ZqV-_tTkGY&>lYdDAULghbhI;O!*N|BE-Az{rIK2XFC$z6`y=pz)&28YRMe6Njb|8?C?YGE#)B}yCtQxXQ=9VW<8qlA&tFN8{$9*axuof)sTn4Php?QgIVJdjW~|*cd%Vj7_4-HPAy3`8+266(X`K>K7C!B67?+GNL6LSnSYvAq;UB##ePNS`*^`9xe_H|7#&H^V6pCP0S79SC*qT$oJsbUtfOK)rHF;iO9}L`n^$TL_0izxuYNu}LRfrNzRLV{1zntCSpk`|tLQxS#=?O>5c~GZvjkmFgC8Wh<HR~~RoS<10AuY_mB^|>ov-(?pMOvuZrC}+yshe*SI%GR*3kCznc5-d7tt$h`_k~14q<=4F3zC%cB|;3T&{WvNvRJnnr+qNGaJuFen&&KTRu<2ZO-Qo-xb}LwlZwwmH|%^FU8th{QVXgU^(THGeh|)b{77u|9n|8v6J9-3D{khh^?ILI`j7N1jUNQf`XiFuty}OUbUKsld@5#7(%sGp8l0(K;?o`4j3#JdYeH+Ja+ZXibm9WZpD8K_JOMJRx+lD8y0<m)4x`3h#_l3RURmhxwT}txYV~I!OX0O+_hX0i)Ob&{$`BSV-=B}#u5Fp4eN6SX6q+vUmwe#kK|1-y<@S4_gy8?vkviD+tx%j^U%Bqb19DMVu*}r>=GrboMLsWr063DUOC&KH3JGe4DMiC%@|f|QRy*{)HPOL2zh$(jjCU4Sm+CG^CP#@XhK4}0EDq27=%G8Bsk7ouA}Vm9mN^}X<<vb5h16XG8@};LKnvEuw7U9_o_j7X122DXJpe*WizO$syJZPqTQOixy%P*M^2($ypLo=%2PwrLzlyEd8;t=iQK4~DqE0WCw_y(-z4%X)h8FZrSakX;%I_uaayK88O=m)T-@Qbp&qNaPhrP-c0s6~NXwDkVXl{lnFc=&<RFCnV43<y^^1`WMH26ADMUtOL&#~2)hnr_B6Il$HpbSw4jsVP2zU8>3Ndub%-2>Bq*EcWzH%-3EnKy;&(N$KW@XTKD;m<r4Y*<yQWC^`DE%kk7$8CvECMVn)@$U!|4O-}s%a`#pJ42+6sIzO{>!csu0X|Z(7%X&Q+!j1qyY>YBQ5VR%VI}f9<by|{dXewl*)wx{iZDKSDkRkSrIwUu-Ax|HCHZyS#Zh!$(}?jqqzCV6k91}+x0^w_Ilyb6^rSM#XHQwQhumk{>jgO^$YaesT+s*FTpU>_v`&qcGj^+5PY%~^_FO|mIX@XQdH`sk;|sM>Pxgh;AIQQwL=qX;MI6yO@H+UqJdGqfLbL1m-|50)t0I`E>O;hk~AlE$uC6~MfL#OQs}^HS<%(7!Jt+a$`P-Ia&1%HEnX~%r6lu$+82p6!kaA23o;qC8x)ieZA6G@99jI~tgA<e*~<l@JoLLil%_z0FUqdohAgpr%Reo3_zwzE40kt@-KE-HK;?zFJCiHIUKU<oi9p|f5XnfrPC>2&97Pou9&ZTJs+{E%RP001@(NkSlJEt#L<nqMrXVT#kbc#6$j3evTY*|V%*u*$3(a$D?3p>|u(^hh#Hq6BGA%AQM7Z;xyB6P-)cCZ8oolBBtUysN?LrQZqLu2h&LqhJq&SBmh?b{d>`jSkDejVAeqNaZR$L*(<roXWfmlh?QvSo$oguLVO2jMpn0(#*o)m6n`icWj2tN$-I_O^b+0ETht5X7twUzfXl<N8h%a6)V1up#p%Q!wZefru|sL(_nn)!m6ADvvX%UwYz0_NTYJ#$nCgxaOCybG0%T-8C%Fy}seb?k6ekL+etcz|(&0xS&4KJtzOM0v_V4+-T|z{WhX4vDHS;a*0ar`vLU$gv1<Lf}>}>>naQD6Eu|*s1GNTEAIyMJmEbwN8P#yFNiMHPN|`M#hl@ZB5ikR&18Lx;kctJR5$f&DMmfIR*c&q%(_rDoixYETn8vhsfwcQ0iA*-|D(azscv6xdw?tMHvR&BTG3tY!r+>ZWKw;Ew%?T(U#?B6l;7_AW5b``1<~S`1I4|-!hG5@s_ofO=%u!X?Ku{i%qc$C9?t4z)J-WRFk2$ow*X!V#k#D{Krt)b%;guYpR-L#+CA;+B{I+U?(&O!`KWh7Aa_XZsgst0Y37n#6h!K{SiA0`5LJz0I@j^vM(bmho*`}ev4(_w#M0CGKaJ^c*V)%@)qlJr)-W2{;^~xnf)_~zd5R3fzXJcm_6o8v(t7(8neR1qO;6K2XCO|4<jq#Ri{KwX3Pdl&<@d;4|zFc)aG6J*Az!bSDQq<@h9>bkZ+;GijR_tcOg48Uw4br1n`luhvW;9x!W#+2WwX?m|*4O@`pl2p#%4r{OZCl8wdn>3|x?K<4<|aX#!3hvZVo$m(jShNMmNQEHhWJkDOG?Ybh1+F4=ocsGg0Dm1+x4H;ejYDO^rvA6%uz!wRK}Plmh^MDIkjU~LmaGnbSyT3>vIbsMa2!&C>?W{U(aQe9uHn2*B@wyIa2;A|#pjaepjS!I-@Xr{rlj(P;n*tn`y7I;T#-$s+)Gjh|T%bFy1wH568xLmkhTuxfbA(wAe0-xe|khp}M4$cW$cb6lY+g7>9P@3t|pSsNmr=^^Rmp5tsdS&HQsGDke7~pISgxAx$D$CM(IHwjUtBwU+MqFxZEI9P5vh>wmlvPGZB66z03^xy1H6DIL+|yNUJ&a-ViM#Wng>Ut1p+rG%WHYNW{@8N2n!vEuLM$JRVMmN7tG=lnFDexj*zH2x5o?E_kiY!PZqZHUT;*cJi#+hxPTdbAmNw&lX@P7vMs8Bbt7ki1j9=siUfd;?D~76t{_EBi(%gbz;;=yTXg1yIrS%A|n9QQWEXIPE8l1xyMW%zhmhm29(pwQbIEOEC#~i+Frorh!;`1y!zH%B5t})E#7t)kO=1j3q*u}S<A*H{eUK1p`zb}s{w88M4W&ocHf_^ULiz;uy%zIKbD*pAazW*<%Y{&;?dt{Wp{ym8<{Mr`G;#*(&GRk*QenO_8t{4^l+DIR$H9}(=eUwG4N}%qSEwIt(s?}kF6IATKCAYFeR?`erABqsPOX9=;ywx6-$`biiPyvXsXKG*AM@ZTIrwBKUy(KVwB9W_iK+cHOEQw6vB8`1;ajQ<nja-qGR4OFQO;W?u_8g}CClzLCRpqgp0c^XgP*`;qJCua=ISmpM+3zp^7JVt}DIDSEl0NPz9?3rL*Ms!TzgNR)K6X}guyJQmuA2GuO==8IM9h7jS|F}lwG!)LCHkyo;#Ztu_HKt-p$G};5Py~hW7+X5`S{iFNzFWraWADyf7-lSnL`M2NkpKMk&jlBPu^DnQwY%3KAZ3C2&$0vXM%eL1DpBmVq+kYvnKg*)$gJj62y99mAVzV1E(a*hLlfMN5h`TLDk$Q-7a#_$vZXF8w1p;k18hnW#9(;6DR98AVmS=a7FvGywcB_7NLb`=hs9&`h|Y?2rhJb1zEw3;KdHj9&1<xLFVZrxrkO@3SFY?B{mAGTygttUNqLo&n>=Ouz?5W0>OtJI(FbHi}TrO%m*GMg8tUSdTnm97c@4m!={(<fov6tyh;xYwuVh8=3ob}ZNC}wr8$*W75GrkGt!LeM}P8Q>;c$&Jk{_*5pt6&P^8VkLGG+nC~Y9hMi50_9xbHL{u0A0qGfiaER>f!YGrHH15okdHn)bPPfS^1zZqn;LM3pOSUR^Ne3MNE#iqasoRE+MJ&~aEFC2#D;&=^*EVkc`tj8&Kma1x#gcoJbdtVft<boo?B#rK_%x!n_NDo&n!DbdKf<=6o%foBz2|}(D)JbpTo>zP{2wNV68YhKEUHqbGTZ!;wUo`S@cPPX#+nT8IH0FV07k%Ubgi5)ZkVdv3GCJ4gi_-77yjqveL$q^E8FDIL4$|qdqI}AosMqh$RxI|*{Z!+~-pw9!<w|u95k`_lu69PJsP{<5rrrj%<XuxF)nXe~E6dJkNf58Wi&SjNjFm1i3DzdJUB0%53pLj+brNfA*=Q18$6L#N%DM{enUFvsFSx>%IQ{oXGE7pYev21dYwKK-$+et`I_p9f)b)cKs&vq+dZV=Dq9!j^k}7~?Ex8-6`_AquQG%XU+kgghZ(*M%e|Mq*^^uIOmv?(xY))>6pa{5(6k!jm5lPj;hTH{CeR|?VbXj5^+qlYWP8ku9Se5S;*0o&g_^&wAe#v!7;Pk|mJ689fYMl6`Uh**y`H#$Z=;vwMaFM_aXN|NDqkJh)N2FB}ys|qsTXxBhByL8Cx;(RjJmkV$8CPtt65jm@33gY{G;c$SUY8~D)pA2owpimR;1O9WM%(c00jEKJhdJFTokHuKql8x=uCbfU8NImrp-(9dSEJ1ukOgJ#|H$SF+f<#@MmxXH-5ptwQO~b>$fM<pX45-klKWG=-l-Og7MzusJVgCEwn=si$7cB*@{##6HY}}z%23J}8yiB!&IZ-C_2t_srRGd&Ab%b~!WAu>+nJqo&^VH>$LhQ=oX50&{#dlP;=VHv{{}@EGFDp^VS*Usl}&cEA{cdmE3#`2wnOq-AGKbr6dIt1M>Y|~KQ$g`82ZS<I90s*oUYGckWbSf784)Z(Z47&d{WeOR69&j;ZM#?lkM%NuUOtGBzqA=qVk7pxM>UhHa`m-wvh86pCgc3@QP!crdY0$?Ame#pH9KSk$!msL08emneh4MPyOXWfR!7uku`ZtMD|o{=Qd^!lDDSj4g=E2Hj`OsjQ`pW@@ni;QCBQsPYT(<^0IkWKI3Px!I-#H6!Nwx2E<*g9+G3UFi60QZ-G&1BU^@lbQ!BYyC^oqUKC;)Nl02|?O299`G&CU!I`vxVq5Q)<Jz~+U9ose;kL!!%^MnX)IKF=t;DAd$$OY8AWnxb9B$|>XvN8&Wrg-aV0lCb{iKq8A$?Gb2NIN{YF)x6O&5DC@KAnS)*zV^zzFDfB1*?P)?_02SJccO-tCAnyV4psYkiN(<(aQK+$-ARf=J44W}@C@H|<a+R(ZVijkz?rDT&1My5|s8xbF6-k+w@>i#e52rjPZ5jPLGOQ$1Po@gjX_pvi-Ybk-6(u2g)quR7#$Hn{(;KEzVLx=Ji=vuLSk7O>5lWO7nGOyq=0#qqk9?Nu{uPIyMWQf0rly1uMD>LKWBvIaH|D7hUAGTbUv3ftj`b<DzN75-hhWw2>k3HW=jNPAgP`Un!vMt7P*mjUi9$ep6()N8erQeB5&DsvusGFvo79ICb=RjYkuah=kpMJm;x+wS5!;-vDxQMfsAPsKUZaMxqF03}7$h~y#JYzlU8Sw1@QfI@qI)k6~d1#;h@L|$wL4*Bdd5lXe@MIfPY)zWqD<FU6w`F$wX(UvC7nB2SGFpWLZ>LXp1iuRf^O;8-!DueN&kSgOr#YguW@&@HAEd9_$p9k(io1ayk*OHPq?e{5Hq<bur+!OMmL(jA)yf6;r@M8fHb*wQ$-+Nmqj8#$S;(1d4BmN+fYhYqy5DZ%l(OMIs#kI~xOg53^_XL>cBvWS6e$~tgqN%qOA0Vg{4Tv1D>wTL(H*}cN6rAC=^}4UKtjbaNMw;V!pT%8%gqpURn~XsBA@`=nJ_`GXG9!C74I%7+!mqLDfakndgab!WepK&`BEA@x@*cbj2nnz7=1`z^qH>XuOkj*=doWMxkI!{r?`PjtN@ztkN!-|%n9DcW4q?iJvapS{Bt&CjT<f&YFUp&~4U&Sy^5MjyTYN0B<%siKK;99heX3tp_=Sq8s4bT()B;G;ppdt6QAnN;NmF%4miA{+#;<Goc}IuIl1?fmmT?PrMnX3yGr=ma_o-PuRb8%`)sGVYDU2DJ=k(1=N5+Y~-i<~g%GW8}+N*C^DMZCckn7Dzu4pgKp|x_wVCQ%3%~ebk*`F=lhP)(BR+~u35+GA%an5LTJs@+qkI0x)$o|UU2n@oM<%6Q8kU|?VSt)`S$4Y%$tQ22%9$iRATYpt0X06_1zU!a3YG4j4;%bY_$r>1QZO+90VosJJXl?CBRgSQFe}(B-o8cvL?kLZ?H9sfn(U`9!A-3i_IudMCbkC#8>$ZKK@n;q;r;)vJNjxh^O7eJ^T!>$(=v4J=Xq2`g;~gl-+6HK?>TqA-nP_g+i+f}vuwGSrjTpA9k64qxU411MI=F;hMoJZhCyt6!^f1=(lEB{{AsauntC33P)d`lqHenmu=m1G&)oc}+Op!w98Wi)tykj7pxM*K@>f!Xo-Q<UtOWZ0_HEDlR{9k_-*k83C3a~|36RoT~_~$k!G`ZYOR)xtXr_j%s2U=U2Cb5FH>LEj1G+(h_-&uC8IC2ebVmFZ)3uC>+?f#WQTP89V5r=_x0i3MUy6`Me?~oyk_z@R3scep^;i$JCsCE$8QCz{u=hzTFCakQN1~S`Oi=>o#D5(&xw(HP$d@hnuJH*vP&AuhDjJ%QMTc`|<Yw%G!lnb*Pl(d|fO%Ez|6U4r%;x~2t>?)x=SJkyj0(Igt%&q}EZoAOcPPZA9;m2wuG{<Yo>d&*|C@7M_3GND<ivjXaRGprQ!Yxh6pk}yC{|W_bv2p>w^JBMXiT9Bx_OZJsd@XTI1&$Pv09}=p{nFk&9)H1D`0PbiGFAyzD_umm5MO1Wi%Z++sEZ_P*F5s+Ts<);D3uSM+eYVfgC!kn29&Kp)q*OC3QTM{E)QYwN*6Bd#osI{>wjf5_38q{lti*YaIP&PwSq}JRVqnsQG*wxHJ?1cR83m3?!#=Av0ee^a0OgB)L8F{IUZ2n^$<BjZKgDKreFneXrP#{Hf9y1vgW{rJdC<h6`Ba4hpV)>1zVws>@IssuSe5cL_XznF)e#)i4Ae|pF69oywkeWQ;3CFeBN1Bnp7LD<*jgRHrMBZo!qHM*om{HF^_Pz`MTFWTbT1%V(N?p?5N9*P+5>rGuU0>8*+_6G-qg<KI<bx`@0D(+z3UdxFJ~i9?^sXUua7QXOLIAJaZ+JCe`A7dB>jqT>6#_ZHOW8lSJajukC*+N(=Fovi6o1{WYH}WY5*s<g0pSmS;S6tgz7z{O}+*V(4q9RH+md<5zmt*Mc|5<VH5Ox|a~E8JAphgwdy_Su8kR@_`)j+mTh)P=Pf1pj?~KLS=u&sf&$|N^+XJ&d>b)PU-;3MH-q8(U{@Kjy9L*t!+>Dly=WGMN!R+Lf$o9Fz5I^g;aqdDe#NxMeoZ-CCFm^*|8Q3(t9m(gjn5FieXz;5;O6a2CFgJ{&}pgwrCxAwa?~@pgTjgjjJr+oZ0+1WlalGIXmumSLOVjWvzGwF4_%lSxG>FO(UbrJr$6n{lnPsBzrsMckk*<=+-K#rEj0B-6`1Y`&v3ytQOpWkQMZ1CFL*QfBKE6fD}t(RIJQ6Uq$wa$tZ3cJZ-3QjMgh75=G!nXZ*0|UZ>XgEGf>Q>}f?B6k*o6J+5GI7>B0%L~2;~y#?ZH;bNO6Y1LT~G;a%DWf%$js(Q|x3x^`fA<iQ4^H#)+%!f^bhMu;UaYq*kNBH-Y#-w!_Y~{6T9Qh?D9K9o=Vo)qo8d*C^HquUmqT%p#@00XAZ4a`RX(ijLDy-B}>0-o!hi))v+2_Ys5Bc#|VS$!R??_V04a<|Gvd@8pEiW^aS0!>8eZ8KuMWfItGL(wkM6NfjE<=_0gw&ZwQAD{r+|JtLq0#k9zcp5*TIb6N2r*HwRL3vf1$FA)hT&UAv*aI0q>F4EyaKmM(dI!1+PJl)I*xe(AX^fqbLJPh;_WY5<Q(oed;VH>2>V`r9LvRe$d)3P^>Jr%PU!M&1npPsA-i;C2gau%*PTLAeYdGdk*oFyZ5lZVDwo>2lc4JUbGhqVx4YFE`keBX!=l?D!bTO$x;(8W)KhJnRXGiC?L&kiEy=3NpYG%fLu2c_{@MZB_7jVbV8XMPdYLMh>vZCr02L~y!%5z2v|CKy8Ci;Vzw?_sSt4tFSpPmriWl@@Bbih4p{I$W^=TH!!xiCg|ER^1Hr2-h(rAJ;&tu<n*_xt^J2Ov1y<px2%0Auhc(*(HPl7O(Q?-H9m5q=m1|qM*u8v%nS9i<G+|MtX2%1b!)}yOy)kTlXfi`y>RUT?(#$OfhvEon4JzOrca<?$kt5;<)r(Dr{pr58qOr@v@+*4iJ=y=Bli)%_twtR<>H(+i6^1;rxchI}n?CQPjl-_n_wQId(hq39T21KKuxa(zMS5?S;eo^%Z-WP{yv8$uk$67ZQR@>8NNr!BqY*Pc)5~#t!v9!l#<|h+JBxWh$bS5eQs0-^PZr^fWx>`S5-fWT^_JXUsbT2JONiE{QxyEyG(=L{CNTIgePXW0^GJ&d^OB+7?ZD%VwF8D0G9m|ABl;Eh>_b~;!?QdJhsZOv7DJd52XhJ6{=Rt4!Wz4ufO82_Uae^NtMkSGe?UcpQGjC|Jq7%90l@CZe0t(H6HNK5lFr#+XMkF^yV1jFOx>bF$#Z35w9~B;R_5R#^tJZQCW5Qs(m^8Mw@q9<_a(wNlYbh9|tm59%K2rq<^1cQ#W_1(SxX)Ut23PJ<-hy3gw5nn&$5tp*+<T}=tdG3yZMe$Z<+tf4Q7EpuT@AXcJ>f&w(tfp;oGoO?ZPJe(-B*i`Qo9Vvf^++Ig$l<yIrvI7D}Qw@6c{_YwASO(75xPVzuLxv6=(>1KnR<;a-r?I!#*6Kl3G<=OJlhwd=d4-oY8CHNly90)+4t!brm_=$z`y@;5PU2YBHt<ttK~rHK_z)(U)G`M9LQ8mnP+>&M{o^)jsh8`BV)GQRGBXj-}f45eVz{H-SZBb%IE$-a!tL=G3NA=Vq|thUU_T({DrG=-R)Eb@1%DKw?EGRMO*7I7C5+guT6K?-r|9<;yyfN=zkm&(GdLkVp)lp3?eY2wd?*(r3)VLE7}TQd5A|0U<T7#d3*7U+|=8Y>byz1(IBFl{p=8XQ)j;P#5Y`J}GBtw}ib|)4tE5=D5{INu1&jvt|4!w0%aGQ)E)`dbu(L$VM~yET>QjnAGCPI}aU}x5q2ian^g+$i$0n!nB=lt~_6Ig%rB-PwI>2gQHBgBlQ?(syl^_OcLT^Nnt}94M|u)T_M=u53lzpubrG(eHg1QVBPjE6($nRx7=Q;E(2<)hpUB7W!KH-sn0~z`A;LVy6ZT-1k(sT^l@Ec@uw*-k-Az>-eR-U)KFX*6+=hhId`3YuSB6UuQO8U<zy#T#f#wU#6*j-s$5vq!a^ht7FH2ADdw1(Hgvt<id$vUGD)CO?ygpo{lqWYx;SY(o0LBZEvot#!^ykwaAgA3Oj+%qh(vplTEkLPS81_91+MwRR(u*5L4+EWD^=?}Wdc|>G9!0q^sEa!`LKn|jW5|{`%W=ZCgd+k<~}8?czeLIqG+NXZ*z;Qo!;egY|e<O(n?dht$SUU@bZ#@-JlqAEv^x_UYH&0wTkk3-ZI!Cbv70i)$GxkdUkkLYF4AJWOcQxEXz%Gub3Vq%w8PpeO=3!jElnNkBD@Em%U*!hF_glqp0Ck{ZZewIhr=8rg}UO<^4K7e)#m$Tw{;er^Ouw<-}d7vjH1t3?}kqBY${xsE5WNR(Y3Zqj#04h_3onQ9;`t>6&-A%kZi<l0_d;s*cgVNnz%SH-(d@!4Vihj=gbr0)Gi{zLPX}sD*K<#}!L0s_h>c2@QBW{tu-g5QWK~P}ESlbFh*jwzmjv7t~Yy$R-JpoVKE^CmnACZ%!<+!*7l0%T-$9^5LB_;Vss*N=`>*fkOEm^7(so)8&otxao&5s<#5r6kY9_lw1fBJdG^cA|KAOtLAcvRLPFC^}fYxX>n?-yg_`X4qvX}*(ZA|HCNTooSqE)9JOH^QaN9O5ZeI~CbPY|NK3LIDAaPj;6}Lp(&i_KDeku+d&TP&HaM>)12i)I)*iv1C4umASK{tGNd2Z@bsFjBr1nZaggT{lt!Yndvw_v?s$8(kZ`rHc6yjSnSJ%o_H*7kfR+qJrxXlj&RR`tcQcVKMgTbO6Q+!P`pO`ES=j82a`s9_k-bw7<&N<CV6SM4a!B>aW*7EjqwKc7{OkK9)wJru!@0PcXAV^}IB_pX}Vi|`<{)}rlE@}dd4}5`dLY<OobqxyF#j@jwP(@nmZ`m{sQr06GNaa|lBq%V88sb|>aMrx%F3qy;v%H@}y#)QrYSWI*ow-gD61$Ebf$d7tSKNV-&rOM*YiEaN{CH5@w#6+6y7o<J>+xJ>9q48Q=rfc*Ks&CSa0T4m51K34WRD9i0>a%*Tg1(wd22v@xt&azN^H~ZouQGHt#UCCX+8M_*Pg1trsmLG0Vd-&&qwZ5M$paGf0a9YnVC{mHP$m()xjt^M(*naEtH79NPLZzuakP9J<Xk2wWO%ECwF_3%(VS&o28Av8Wg0$NLeMJV<jc+dpa`<t#3rl8|e|TKb;}%u3Vg_*cLY;4e;lFHkHl&lDWRW+#*uzr>ZWj8#SFqkrfsHTj=~w^(=_E^)grVig@;M<vQC*q-s)A6TS<gpsbNkSyIH@goJglOld(&w`nIxZZW->*-Kj)r72&x?yjS1D$aMsz;p*~U6o~LBXyZ`B@2yj!ggo(WUe&}@;Vs_yQpNHi6aW^TZNsGS?AO8tsnwg%!s)9P`;^WvCy!UuA(pFpQ1NGUNOFDJS*CkqO_4d#ivKDxxcAAxbD{2;J%4akNgYTC-7Ak*t3#Wa^qATk>-JVh0e=5-y6Ao<^Ec9NfkXGks%LaTvN9%S8Bm5Emx7nop0QGxe}yfU6cf(U;E`6?U?0y20@TSGi3TSXO=*%s_ClYV^+rcBJJ5w>p+3UMc6^tV|-(^i_*^Q60a;_LzPZSQa)0`ex=Z&3%%#qHq2E6J$@;a-x~DIusG*Q^nxn0jN?44h01I4k>ov`k&n|P*{n#ucKA)YdN7WYTGqtxFS}aQbDBwHDdB7!KI=!l#>v6?#*-~dyj&cGi;hm%n8kCFxGShvhPNf(nK3#==CF3^kh*bl3yMq=#?~5#J!wP4YqF+$6fNa=nDk1nR&0KV*Dk)ORLt#qE4sN%+3k*#FLL2%X^f8TWAxHkSnWj9&*)@`h##m(g~)ZUQodF?{}A|6ayl^YTGff8SQOeQi4`gtxyUQ>UN(P8p!mYhNGyMH#3?Uo)gf?eiDGp%mWb~p?vH|VYP)iS%Z+ksbCC>#8ahp~$ci;H>++%yMb*6b6uu(8{NLCU>PHENiU}XLGNSIkWy(m9(v<c^<!Yy8-sf65E>qJZ+g$WzEfw_%8{UvyRrK=7D-BM*s#xf(%8B0P3BFp0Rp@XdZ!J&G7D3y>s>(whZfcn^v|>rp#BlW|e-Za{ASa1##Pi2s#dzYCOEoze{e^T%=6ziEci&b?-^Akyj2nCgxGxH?!rB`1x!2%PSLRf18nq24YAE2(&gm|hN-td-1K)a~@?EOl*?Tlwp@seMHi47yl*-97*uM2L6^uxGNmqsml<iDe9h;DmZ>i$`kROHHQ)D+R#i38V3%XHp{NPG4t4RXoSfI+b=`rHlif(E<5LZaa)tn*`BWB#F4)Ed|C(<B;>A`|L&GKh8`%>;zF6Mh?N5LT-%-XTEvwv&(*aCA(S|nK3I9LBNJ3vNs6V{nqJ3*{Zs}&X<QAwm10vOURUkLkv&!5i)lH8ZSfBjj1{lj1W=O6$2`a%Ep;XnTTr$7F`5C7neG0W%w`qlsWzkm4Gzx?4(uYbvY{P4g3{Gb2+*MI->pT0d?culK({P3TD{NwB2{oDLoU;ovca_#ji@LOO1?@yn8{oPNWzJ2+|^&iaNzy64S`{TcEe!|Z_eg5{pFTeQ3xBmt2_x1n&;?t)eUpBw$8;5Vd^Or9#zZL%WOEl^0$9R2{7YIXI5QHj%kH3%K{u{nc>iF%ybu@$E!^Nwi34-5lZ4Wl^zmLJjw6n3JijBXp@uy-l^+Dsm;c!nh6dJ2Qlin{HUqKV!3mON|gv;c5_h>voV-#q@dqv}`X#D#?;}A6ViDpIPyQ2wbL*u(mDF4`K+&477Kx3b1AR4Pc<K8bC*8z=td^Gk-qvk|tT<1|^AAg6M(RhHyzjrkLf+j30&J)doCIB=+fyTaHG(7_6CqQEgH13H8qVe6)nEOU^{)`ij;I;&gogWb;5EcTyA?5aDvQ4!;{x}I8nD{Kw_GGf|w{xz<zk4RzqrHDJ0XM-pV(Fetz8%Zn$hZrcCzDquZy^=?jfs8tOkBa_IZjF@&oy?-<hk!)OrB>p|73!OW1md0u+hrodEdDsCidD)2HhpFKa_BX1I22g*yX=xfZ}^XG2Ngv$PRozC<6+`S$8`s_Wsi9#89~<6?cDBh9{M#vC=t-@i-&HjJHc;JkH2aQrVTrI4u>w$p}9>71xCdOlCxFpzUF(gtQ~W^Y~E0UML<Ucjh{nCzL0YdgAM~z~c$!355z(ujxSlgwg?uc^6RZ6N+0zj&lV63FVU3c!OfP$u1rmiZ7s?IG>)Bi46$FKcQ@)*e4VWN_awfLLp<-?*WR9?;46b4V2IiN<yJ{b++_eLnT(JoWEdYA~MG2cDWw=C?i8lCI9b}O6d&OM_q7_yRepuTg;gn1b?TcVu8PxT0(qEDt=>r;ht1bD(*=I6!rMF;L?eytX5U_NhK>za2G1}N##Ptwo@_hfr@!j+039>6ZxdF?m_NC=t%{peca{iCzaeA=G;_9*90Y;1j_h?(j5v6(S|3KyMtn{9fz~S^mtVKwIkUfjqiE_#V3`fvGQIsKk1&m%IrbYr3s3^H0e02fm;(4Cv56+|4@7nD0xZC6ADNTu5~`|9?EK3eI66HPEcG{=ktWJ#M$f<N)E+lDZ+OT#l0ISwgrmm2qitC+*>QCj!^6q3cdT7_ii)fpHQgy{R|~Mp<EM+I|~%^gp#*jaUd}JgaT@ipHLPks}bT1<$27%KrsM{dqS~UY0o*jCsd)_X_lvB<(DIh1kG9ymm2asAB*p+K>7O{D;Ad;=rC>F-C%o`hO|dGDJG9L0Q<N^bx(k4=zwY4%m&8)8?pdr#RU7?lr2!*6BFL@2DW->s0}$QrmdM#F6y>VOn76Qxgx+W|9xUAFd2ZUsc_<qn4AEUd17+aNvFnS-yJ6R!~{bi>%Qi|I66<E&Q44|J0DpPo_D9J+}Vw3y_&$|rCZAO&ru?{8&g1ZT<h22B=x18Fm12CKEveBipi=lg^iaA456H(-rt5@m@p%r^}l|x7dZrzy*j2CyK?GbH4^V}I0ctFf(mB<MHqwi<)jSs#)lbDlX-H=^H8S7sdFywaTp|XWGXJ+pJbId8Z~iRtFZEfQ=jp4FsImqQ`i({&3UJIX@}t-pHt|=$!E1%dCJK@IT7VsD<|7>*giQY3pm*)C-jc%H%Z=^lW7s&pPZA)WW?^tiHMn$ocyJS>1jDxZ`(-uP5gT%b=nnb4=9*+Y6NAimXtjzz!Z#YIBd?O%-xXcIi_&csdIyEI3K(dR4!Z4)udcOYL)Nkqj73d5hvxYPRg1wG@zQLU<R0L+a^2qUZ{GmR73}mX>v{Ha}Q>oKN%`KfIyRS%%ToSh1-%ck4Wl`P6T(pcm`6_PEZj9@8E?vUD{y3eSKO`UsrUmB9#ECnU4GR_3P?B97f9A9jT!&so}(+{1cQOlmn|&6R7l%piFh&yDo%q{mmb*c}iZj_jk_Qjap9bC{ErsoRQu*C6KpEr{Og1!&DX)4&N}j3#O*@<{2@0AR$~201hnO>e#@0z%+tX%g~ktzC%o7A50El@_R82?*^0IgDIU9)7tHC#q_o|*_H_J88JDK5P!qu_F{_f2$OHe6i$oD6qwvMOy<;>tZU=+I)o-rP&ae(9UMOzIGKCn<Utmt<P^JbiVw{xfwqDUaC$4s950;0lM^U^eoLcFpm?<>r*J5z)P<8pIGN6z{E0bD9XYu}ImIh*TGywZoa_lWxkXO+%4YSrI6Eh@ln&qSJb|fkd2*dFb?mog@oE<DyciU0O}&D$7f|*{P#wq9(3R8MTw61ljhyWLaq2vvI)O5eIG{S`<jfteJ{Io`xvtVfmz-R$wr1n8LQ6|%;u>gqkeS2kRv(|1+XpKa_MZcQ<u{fM?;KXjn!~MGI#`Lg#>pQYmgx!06R>Qz7GbA@<$(tC2@8R>dN>Whd&e$@`n_6;oeWk2u*?${gf$?r+y<6!D^WZjtP#MnPgpWoYYuPDT)C^j8qNaCU0_)hmb-e>yN8G6JHv`+gJm|b!V?zU4HGaBjhBG114{BIEO5?Bp!V(!4aAq0Xx}@B6*E`?z*_a4spFya#IQmJ%RhW$&nv@P|1>;d#mm@nEG*Y8_;;5rW6dCrEBg(bxX7kfTK*)o2tmgb#I)RoO<c0c>vzsVYuZW6UuXrERyg(83MSn&Cm8gHg7ND0XMr?`x=Ep4y1!P%1Spq=rtB&H_3FI&@VM|ZfeY*88U@>21lH`Sz~!=p>JwVF+j-=i5H@WC;|ZXRJDK@{8BF8EBBz?3%rYOAZ8hI&M6zZJhbOaznM0W+gjskp%a}P(ndLV&F8(6;e=>v2tcaO^_sm?z43=z#f|+Y!7SG7c0CT*Oncpy*PQYyF$PAV!L1qS|{h!Q!e<?DlF>_fV%6n&Kin%!v%<PjH!ps3?KC`WIOWD(NZq9Qv0z1?xtEl(DFWg*e3!Zy`0r`xQSpdDppUmL-Y)+V&r7{IF3-5y2G<HN5Plk*r+1SktdOW4~!OR8|#MB%^ZMgjReNgjaYCe;yZmFfrYo&==uWS1C3(#zgMobL`wYSvb{ZPApR=|cK-PBODfx>i+26rJZ#UIuL+|;pr5q|&S*+rC{3oANnl<c6*XaLE}2+~V)(MK)#A2xN?QzwM>3a7D*U|d)G*A@z@>@PGRg$=x+&)v{aS$i#*=AK~s%}9ebr5-fXgEnsi$S6za_5;97C`_Q=P{DKrOb-P85T?t<?Rj9jUNFZ^H*gH*2)?tPaGo&1CK8ss%g0U6Ob;#}b~*md1p%|NR0nf>6qq)F<4*;rFK|v7&af#E2*B4V0)vo2jdOSuoG$n%#~Hv8XSL|_Bu=-)`a*`&UK^)-V4N;HVfsurpW|FTkj^?f{WNHCuDdj}0S?(A9U4!UIL+hZj3`b&?!h?#oN&rRoCCmV8gZtF!Rbdw;q*)x2UdT;&dy=eQ9Tban#=S*F;1XEui|tYoUs_4KC^|{o<Li1-gDk$2hQ@k2ysTx*U$m${%vje_{6#595X$)0~gE)ZblAiMEZ&|UgSkOoZ-wk1Gs-XFwIw-7HAnf(0`aq08fk4KMKw;MAw2dWz%`Z>42Eck~r;IaV9ewDNdK+w42@BgP14mJv>kL`0YEV!8u(4X8;v3A;TE}&bJYqcHp#+f-^=RbU26NpzbO-eSuRO0x|c8)8YNGhv1Yv)28NlEzH7shKy%w3U``E8J;?vYx(Vb@QebSVS`g0iXR`6reR?QZE~j<1naJ$n8??>Ay8Rwf1|AT1HcPJ0%96hLD=iDK}j!d^4lKF&X7ehBbd#RDViTuR3|;vo=|b7V+w6d*R=}<h5Utb0s?HPJqQ``LzrHp6sMV~&zQdL9K&)F901d||GG?U90A|N*ankKhx=oSUuEKCx-oTt>9B-{X3=}xaCcg!@&1^4OAXYaCsda~^#E#GzJB{tM;vrWsNqots-9`en2wu@S$CnlGMzG}ZuvV_%haEfY1|~sX{I9xpqEU?OC(Ok)IJPT(}U?+J&G}P%f)8AaF;Rll557XS8!^e4rUM3Y3VsNTvE9d)Zv6s`!V$>)A5pk92ROO>ts1Bx&(V+YAa0bJ75|B(+HT_jOp8QFf}txkI&RjJDB<kQx7`zZJ8Q^X?P%}&QSx^Uk_>k{pujpiGk`=P=`AdD5POhGj%M}2`s2#=|qMx#WR;y#WdZcHnxGO1!?thVLAY&Hrx0ESWr!ssd;#&v0?5*ro*!Fr;I7QordM)3YppyFm)3(P?Ij+mqSg<u|EQ+<^t6*P~B+<s*b5In8t-^$e5<(+Db9?U6{rPXPT?xVD@cQeB?|m%haC7Aa@f()iB*k<K_f0$8-Qp$CEL2<UpO|Q0=0b$;C?R_e-cLgKFQwKy6{_3dPbY2`iaKz;wu%y7$0zZvy^G5ME`p*N)Jon5f$6ei`^)tznO5NC=IbiE@UXU==rc_z3FK<BdAT5)4yE9S9!R7?L-85UwfTfzWNO^%sXAG<T2C7YM_qVd~lk?cos`9HC8iFG7Do=r^7SIYRsJ2-g6m%|~Gfdl9+};c91YKqHScAY4b`4uq~~D6q;l5{uA35mE>pK)Ckib4ZI{b5?}O7`qpt%@D37QT-7fn^y=EH43{Sv?xM<8if4_`hs8rA#X@9E&=gA1k-~P^aa6$5cCB>+l^qnLxOpglMw`8Qr7FoZf3E`%!F5h?gRwGKn=nU2t%<Q+hv=czqThGgnEJlLeK+cst1eTlOSE_ofCv2^pc>vNjKud7DDTkTM4ubOTeXn1bwL>!8Jzx@C#w;FbF-c1c$9i?B@IP4h-!a{Bs&#2H03!jxmA`)ZzGh>t<~CmgD3Ihd~+gABu*B7Nj>}eko*)3=c}1xQ+-{$Jr@c3*%&U3=_dH6}Dh^!H^$@Nw*j}l;IS;YfC+C8OFj3>@FClp5t&`4u=fl1XIKPAcn^nh>iNsoS`+=+q=&NcjVv#HJD&Q@fnlBx0sP5oRPM%DjU|qq|Mo6n<ajDlq5;pND@{6$4xCZJSW3saXQ7IG!)7)N>S34tqI(IhXtI^B$@MB=ixUCYEatLjidu4Q`VDnj&}`bAh}A9ij~srK{<k4@mlulGM%sofiHjFL8&H*6<H6UAb4Ej{uVfFuSM)nl32y6CrFwLNef8MR>r3#8N#@iq`i<dphzuc%|1^>(viD26sqe{uC-G+$^o>Oa=_Zzo_Tt!NqUsznAMyOSvS=uNm<FXDM-Fec(b%Tn>!^>Cnh<DWcrXCin_j&l3XK-#h@Jbpd6R!otH=^P~sav2H^xKhkhg-AUP~UFlHnpaGwaEPU-|CQ$Lbr+3v8ZhO|KcHG-n4bYhZY9Mc|>30$-x$+ZXPa5j>Dq$0i0KF%u3o?T|Z2T`sqmQse&op*YxNP4hPdJsX28<KM?VzUH2R&m~w<nNd8?b=htW)(jckX${vV%B`gKYqBEB55=+%2m@8iq1+7)Qiq#;-+YhdV(?O$c1tcAI@RS(Pu*UuqnNDm!r7Z<SfoTy)`85=3Ha4Qf9wdDDQ~m4W_p>W=eOTuWnS~INm+HAOQx|G5+D#;%7VZql6DG!On43S*=$(h3B2K!^SoIu5#6_2WpDs5XU_vxBlQRD=7{4BA_rgAQ=X`m!v~TI-rgXncL8#lN_nVaoRT~2S9Q?V#DsvE^FSE9$&T{=s_9fC|!Ya1R4D;N>?<~b|*kNb|)D?T5vU}Hz3gCKy6E0T$rCEvGP)ncz(tu=HNh`Ra~r>&q~r-=&ZPpBrMupyARt-q{3Vh3=h9~GlNpR=R^|a)-HW^|F$PYIoy=w2uPaCzTJ;xI0?y^^&8&0cpHSI?M%|$B}wZ;Xea3qlF)6^EF|3>lhoC|c=ALU;~+=rS(LVl(wqP#x#h&k?ImdolKJ#DAgl2BB-iQfw`0=iNT#eC?gWIlE6D+zgZh&+cQPh(k~X=hCFwULJ?PM5GG|U-kenW#q&M`S^xAU}L^&>rt+|MQ*qBP#lc5}GlHx5VAtZ;z0Xc!TQ7LmWF<H{^G$f}TAh&)dz5wYnkO>$&xr;LLq#*6&lpvw`#@t)efsXeHfE<98wC{GFJQn0?LAx1}-i*4r4fE6?>jk?yfzBjH(AwT#R@Fx*X#-Buk8<%u0uB>1pSW?G2$>1q1pa2|7N9i8ItWIJBxnM2i!?Q6Vdq-%tP2RQ13@fven|cSvebv;BgRok-tVcXjvJ$BPjc;-TWw+Ku8>^qMKWw`w&#oAwl+Ox{)<PE?3nO(y-7k!1JE3AYt!ef>cR87<2FGoj$V_cu9KYWf7jA<n6XZWk?fg$p$6q>hrK9$hH_h*4l~w$Bz73e*QdDE*@Yq*Q+q*mPSO`7Eg<Q-m8PR4(>X|vKshmNZpkSl=}t@1Px3%mP7)?!wj>Q8Ib<%ECm`vFg)&+<?M3M>#j9((R09fPAj<K2DB}*4p+^KK+B9lOdY0t4@#co<gDa8@JI+A|kc=qFx9L4)B*UhaYR}r$bS%k%*m4H%_mEsYQ7Dq**+^OfWpduMp!8WW@Ca(qS6NElGr3=FdUuqj$DnK{X*ae0w<8%Io@CycsU+!HlBOF;f1f0c^IDQ&L(*SJI<QbWP~_j6q-!AA^K4EW&WBMhLZMK)3rY)4lnxxu4KSIx8cKgNlti?5n0#y@=|F+Hy^u7(G0K4|f7^NYMoBuJr0-a^Fq4d3Nrr;t+U6i;SMPov9tV?j1j%7=TIUI#WB`XGv*ZWeqEp#V(jGh}Esk;u+J$mpQCd(E3{m=yC`|*(@d^!$H+mjD$`KUxV<<fcyjg(Kp9Q6rpu9z@x`o5*F{eTOU~BE$ZH~f+>2XZJkLT!cj?S29+N&@5thGn7)<=!Xp-BK>ji%0jC(Hy&gHu)%ylr$GIyTyFff;WB)7miZfr&TUjz!DkH8Oc6nD!cX6|3=Xw9}N#UX~uPv_#|Hur!N#e3m{@1JjJIy~;X)^#7Q_bSTW>YEpnZ7??X)uIaA1WY81+7ol;Uf3nP2`YOwz=!^UwSZ0nrYL@X5`%WNXh_jrnG0(u#Q#*MWozmzHgE@du_zKe?Ft3(<J=_C8iPDNu+AE?=4Jhp`P$o4>x4G3=5~aNgN-Whi-9A6FC28e_MkUF4<ALedlB5MBuaz_$ZztCc6v`<~dr<lUWdx4vYsM>F8Rc;Npj41_1W8AdTzdk?cR+GflAHsw@RB$!_nmoq<0P-A2}sA2407eO%PKD^k{&bxST~!vG@f~Ml2osmuY+=m?I`E^Oo-BL%#Z@e9i9Q@Iw)gDk|RRWg35KfNqCJ<lE8&IfojYV`1lMLl4jGAK3+mX{iM%#N-}Eto2`}ACCQYL^dLpMZdB<6B-c9O9fQ(mrPUFXeNEuXV?Y>v)la65)iw<%V?UG=K{CapwtV$P5Pd=$TEno%`rkuHrY4dVLuZEME%MkcbCVrWQJH@A6p3ITsF(H87}v`6Eyk2WpW16^6-9NkK5R@*9a$3gJ1&i*X)nHpIqV@TzD{U6>%&lnjwlBbrBCghgXau(S$&;=?H2U6J~PTe({+bKIfDGFznJehP;D5F+<SYXw1%GHc0bFt7%pdNL7wZnC&GBdu(Z2TdIqJv)MgGquMAPTGo$o_uJR~?a<~L4u;+9PL^-Em=HSjLP>ux3Xwy|tjs(hU1#H9ZP=-XXoQ$Rhn_@X_yoBe@^#+)b&hf|Vu=LkpsT!42h@n48`%om6PE)1>%8)gdahp8Cl(|)mOH=|TUr&v4w5AcI1?TUz;B`hh0hDe*Ih+8cCnmTz&hJ1uW)nPs3BI->Ou(J_K2e$;OQknHxIHApQae1SWX7d}*aN3mvsAwxLegC!kuY2d<WPVNStaMWLAuE$*Ivy&f{RW9bK6{^;dT=fA5H*rRYT@O(t1rlq_D{lj3AN$Ri-7$p5?B`lC%yd`4y#WDQfT+JKWVkI0A*wOmds$x=)hf<|KVq9^#kFAS?ni!24q+>A)C1h-ADzNf$Iy$Zb8tbRh|~x_&deVX^CU0+KG`B;#PcPE3)Lv@A&|zVMgQ;zLM|*N_10A!(H)Js=rQLXtR54#ua$)7ICi8Xoy{YtA7-$MlCxTHg{PF)Ih>LFV5nAf^qhL=;}94DO*orzW0}^$g#P$qAU(t8pff>Ce;Cag(+V-McbRhvKA`I%lF3XPzS*Hr}`pr_XT0CfDxrcMichHsK7c3Cd;*_9?aD95*;&$uM*ehaG2nwr4&TXGqlWw6=}sRPgkGXV|2$VY_R40-iU*X)>G!;B=ikHQy)B2}-D(SQX$ioNm+ddbS2w^RM@h)Azucf=$}39pdx_&H(z^m+5SCiBCQ{&S1#l*^Q?Imcx*zJt5C{E1Yq`X%U>Z8_w}8I30^K6*x_%1L}n{-6PI44Za1ZyJWpqn{0^FWRo4@^xbgALvcFdVl=sNkn@Zio+C(#!G8A!?Cle9ZI6qy`~C5>Z8o}naRz|XZ*T?#XL#b=I>1sm*L!A;({6C~=~wD+g)_0%#5v9}O;(H3vN!|4X@QM4loDJEr`=KarNilnljoG;)W&lJ%6&N7*V65<7-g@zwX^VChNsVQ4uk1~a|CrH2DDJiWq__5PIn(T4a6CYafAHY9zl`&xbc66u}uSx?E~mDaL+hR2b_NLK522T-G`wwIqdIl7cs^bXTOuuu{iBS4A11Omgm}KpzJ>2flvOB&2|G$p3@`o^orSTCo}1AM&Pa#3yboQ1><4qjsYjngK$n)#~Fs<wz=^J3Xb(#cpU?Z+IF{!cT-Lx>$!XH+3~|MdJ3cWrY)h1<MJ%t^<P~lN@;hvlPif@lIRHa`Fm32Wn1mMxG~oq972>;s9Bwj#VYpOLDUn?$zhfpw%2x9Y%}*fete>qTs*_rlPGMnJrlLSVY^?2^3g;iK{Pp^`YJgFmT13D(Y=YL#ujQFfcgTcE1GUcU_W3B6L@!GpkW+aPU8Lo)Ng>!C3q010Z#Du3pDlt8j`s=(D4L7BRN8cF|+|4H$Y({ZVM8<InaKNvKUZvyDEum0`(ctaY_DIV2TPG7CeEXd9-oU!*>KdQeid?18PnT)cUC%=uiRbHXY;rX@HXV`L82%Yys+lJq}Eq&!xB}P}>>kcqq`RGtU5$KQMEi^Yohrw5}u1;ZUCA&3H~=!j}yVPR}!>q~+;1z6JRfKP~rpbBTm(c}^$bNnYfK(F|?jyDiWG0U9^<8a;ug&Ol9<0Xjw4m)0rD$0v|6hpM+}3E^FrXS@@hHs_g=LiO%J5^Vyp5S!&5=U}MG^1}wmK(1A6YHn6+I-(8czv8rtE7G=A@|^nJcB2lLJ7?Tj^t+41^YL*GD9&gydqF2IC%2%?8K!dI(!c@KVWq57k-KVn{_SS_YMiy<Ik`#B(-u6#hNrvm44~Z!?4jk4<ms=_B|Y1WqKzQic~oh6ttVS*3I;p;_d5cFhYHq5tS!GK#np=~r}*lZ+%tI|$gbY-Z^mN|-)(IdaiFX0zZXy{cfRfH4I5Vbjzjclpy@h5@d9($-8)aI_p8@G8ffedbYOux&<WTBpYK`W`UF}{oI}g`xt6>H>MkSq36uruHoo&SP`@ZHbD;hSv{WLDEKsun>VUQX6DR|8o9DFvs6l|v8MV^_4MARgntOhaXz9MaNDfz^<D&z$Hvw8E&Y`vc3^V|s;}a+a)D=K&0n}a{XuMCL-q_R*bU^aF!?Fm>K-a3P69J9HO({7)v;m!n#QCtCOiQ3{Q6(G_9WfnS2gm(91H!W`IUkl7NX~OwVw_K&Wz9LvOS-H`8uE;w<{a|0SE_xv3eUtVWpbX;Pobr%m*VL%v+!&3w724kIvK_#Q{gh6gB?=~Pfzgl7oMwc+*GWe=COF<m06D9>5bcKijeb6peaoR>*so=KNnAv^K@<p&mpVghddqVc5jQj(?LqZ8}Lj)D}^0^D?-ZJP^>%$U~)eT4I?<|KNL^=bP;i$lQl-m(-ixT-K02%%btbvv`6s_{e)cJ^yTR@p4-B6$a9uz$K~Q=kJ7#mZ6$7%RMG~hOXE#*=M5bAHrSS|Q+chmMuyfz4J{WRCwYE6Msmdi?df03sfEfwNjLF4Y@9&3bhv7{^ggg&2iAq_fDLGGajafCZG;NPfenuU)}vstBHuOnn>x12J|3*QCfIG?aR&^YOR&R54{~m>0XC)C2X@U}+6=4#)zxdufpoP>)qP-HC$JNYzt_Mza4g^EGe=OKj@7D;AWeMFU`-dW$z)x%_kf)MSm^c~GO%vBb>1o1sndXs(=M)V)2-YCuBO7(o`9?O<aix>adn`wC2cHB9cUXpcI>@99z9-dKd!#uI)HY6X;aAhPPvYw_(b4Iu4!2Z!es?mxy}lv0dTcPa-Ev6+EIly`9Y2q+HD3<<C>OmJ%)81(h%!#RPkVH8?CqxJRWLEAr5H|)^&tVAVz>;O&}iK4{N*?R-+lLX>?`})pdZ5K*Vf|HDF$ISDVg0?R|S!X8Jx<Cu?<72ZU<cn5x;V6NCjz!|E1&7*&7$u{s#99IGQjbpSc11iY5k{u((|-_5+L6IEYdSa~(chHB;-?FDs(V^L5OfJLvp+y;h4b?+|Ol(;e8Pe*BV+NfHEcl2N^%-QRyuEq?Iss&W-g=zv+`-QQ3Q#F044q@0s)uB{jz-9IhNSk8rcobFB&q$i43X@n`s)?XFA5RmYIsnIken|p<tV$2h5DeB2lbosp{cg7kvz#ityBaWtU1zH9P^#2e)ll_Wj0LCaF51Vm>{&C_ak&xnq-u|)ItZxVBB9@a;Wb=eaCp6$SL(QJC9jv8)C@K=o4xmp{_z|Q!O>(b>#xymJx}TP^FFr?E1$JJp-xv}%C}rEv-zu_;vlA`C)2SzQ?80T0G|PvZw?)g=*Kf1ZpL&~mso_U@8*Dh4yJrV`<&_8)h&TweOQuq9hlm4GhL7F7BHP16AfT$pG=un>?3N{Z!h|tEmI4aj!&j6Q(rVdfJ{9Qgpa^$`pFcp>z+{Ofmy)kSf=*Lw8GT0OvmhU{$yG!MlQ?c=g=m{bUI9?^8iSP0;y$@x{gSPb0Wn`<{{DmkWR;YPv7Guif`2JKt|3jTD<`v^~btT-w5e6guTt$T?MIKjFiK%2GnCuqLGT0X012(l_o=?YpFLR8aop0<e8kRKt~nNVKTk?wQqU43r|<@JjmK%Z1QCt*dDpvcn(Fw_AO7JS<X*ORBGySb2=B#w@6*yu^l$)aUk9dTWHU|S!d-LoC|F{6KL7)z&Knb%mL}4?Jx4jLwL5Cq+3+Y6c&wG$bb%m4Q<{y3G|zAS%3RkYZEdH;Z^Z89hDLd{k(D3j=MR}$&cy{-fvjVy(f5{!|^<aeqI?PfinVG*u5s&St;kBo2P5V_jX*x>D+1dt`rSQakSQe*=ajb%su9P=VtB4Dqvi9lH1fe?5N>0xq|ELI$-Zaq18^3Zz%3TLLIuw$IJ1?_md|aOOo0wrfB<+bQO}WpD5v2M<qv&$)Szpz>stZN!v||VD52DHj%`8vAavkJZ=(_IZ1b3l4ekl<ea)42$wma22R~c`nx1)EHq%a4oTBFF@7vbPmRfOY9i@bk`{!?&qi_`lcqaKe{quYz_nrkwW+4Fu;B4Y@{QIZNmr2c=O<~0Mv~jSw*}tDbDfV_k~KX=1P8B^mLNGnM@g&B&6Xq+O41#hpy@d#({)G&g5+8sl`@j<@kz$MBukfl1H`NWkc=5ge_oP44O)^O^@GnzuJzBMJIRBiYQ*ez#;3NZ+Dg)1NXCLBbeJ)hb@kz6LByE!5he<4Q}1+hA(@sNcTUnRd-w1pNpwwzBrVu$N|NES`y52l-+-i>oSfvg!}kOlrq8v_5hWQfyU*iC)tn(nCNC!G5R&VTGnbm+B-7IW`{AQ%14VKQa*}q_U48<B3J3bl=Oq1dsyqcrPm)YGO;wxDc5bx9F)4f;zU~*%KTf9lXo%DTXEm0i9IR9%s(tbOxU@(Ac-+`DO;{(k9(;4Up2kL~csY2Uv-ZG|Bo#`4E)p_(DAjR4RWIn14xQaSFmHxkn0&`l`-7<t6jit{``x|0ePQbkdwb8lnEDml-;Sy~h$<|&TTekHRkw6f??BbO2dYj)wV%(Ro$isUAHt-iTJN210aa+9e+8;zXR5vjRXdE6_6)!^P{*h`K-FfQ>N`+Phf)pXV2z;<R#+lxNUY{uSW{oBUPRSyT7Rdd5pXYCTpQ0q)iG2JplWYHHQXarXZ+MobpQemjH+2G^emuidQ!E=F04f6+>a*8vGRrD0eCj@Sp5THHJT-0C)Geujex2JWqAfT9XzRWeb#-^XT3(%b)z~R3YAD2Iq%g_Z567$8PwrWsGds2jn=eK#aga=Q0E*o5z>~b?M5};<4|pdN}C&uAQHHRnlh;73HA3&#D9e}WKit_)dQ$=Gy8FocACrgPYcz>G3t6dCSa?PGN{lDDgs5wYBO;*s6^lJF_;vzeaD~~#Fi?|D9=>aAi(U#(~oLz?X2rDRAbaMbF+mb#2P`FGH=ZlY69J{W~luZ)s~~G>qnJHTE*nUZR^TyCzI^8YiLl`M0?y*V~k<44^&!yI7l~9AQP<7=e0CZY~c=*_5u9;<8b<(H0{`pW)PUS!&dBm)1v*%G?SCpq2@F>+jf}$^dLv)4_h-$SDLFaUbqs?5mfbhkV}Fz-AQOBie`Wz4h_u_%^$-WX$u^R)=ul^qUm?g^aM>9h=(*ipgFz=n&V`3H0NEVOcuGKniAIk&duu2MbloHW-4gftdshgX%5zzHkwmG(*hIWYto$V2d3!`(}R092Ge9s)1NReFdew-lqT$3m<GVK9bu053Nr<>112m(A8!V8I2h(yh`xb2rj*)Yjs;Ac!CWf>O-Go$wMnB&piGX-y(rhr<N#0_fYM!1PTf$(v!hI4iocD)5~VpcN;_KZ^(Ug4-8pMJY*1Rz2A~hha41SgqMV%9-pk{1TF+5hkR)GG!rrkDh7xxLUTWedNOE#n5=TRF07~PP<lMt}1nm^o!=<@PCz+_LvRp{|oMeirjbsAtyex3%7&hKzGs)>JBt1bg*d~(ULehaQ+7?89hvgy!N!q*g<cW=*JUL14!_-DHg7hmSnKr(oaCW;hki?VSQ}izFA!!SL(FFeMm(6>f?}w1==|eveB%#9P771?G**=~wq(&RWgpuG7f_t3g_R$dWlK#mL1}t!~Q*UxAv0Z}Z5x+(NH1XV_bB<OC*?S7|xC1g)ot~I{cg*UjS5K~Z9AwiIvbzpsu2{WHgU76_IxL}0$`0VsAmcSFUvE3(*b}m=K(?UDIxHtD${pbKSn)uRW1>bfbO?#NZ5QSvQ3-hjkXPe?#G2qwrx?iXj0d#eImLKxj${hPoIU>VZW-eS`6H-rahLiQ$avZ?9xsdyQ$>6d#>P!;jPauPxlwN^u$e%f(=U~<Jmd6GjEM^PDLQDo9e0@O^NcOQcwjB!4`yuojN?|urAhn*7~8_a0W!9i9)OTB9)OAGVC<nuWmI&g9?|~k6l0Syc7QQgCFdWCu_J;rAr7gHaoJEkY#5u&PMK$HPQW-MDgYKuJ7cVHzGS?nRDHpCWEtCgWgIl)IL1kF(c{bLeZe?Z8Baayl+wYB$6kz6!MH4{HGr`NjNw`__GcUpW=yOVVS<H=aYr@ym@(ek7tH4ho7LENX6%n;?1{A^c{{Z+-iiqZlJQ!{JTvwS-Kk^sy>-VjwuWFl1k=WN+r2#jQ<$7Fw0ee&*Yf<~!5AmGecTShX;Y1#K;*|{o*W)j=~9Hd2;0p)5{^NB|H%DLwjJIhAZd`O5Jx!OrPy5um`XH_-i4MEMc$&^fv<;6O9EKV7A~uGN!Z_^Xj?}ZKTcR<d{Cd+s3!0*%d}SRTOh@mg$-N6@v#V_w>v`-b~iTLZ*emnn>w01{F+OWu#aT7e>6r<+yJH_8l52wMk{U->j5O?Q&zekdbc)j;2Jw}b%dbn>t?fyE6iB>ji|vFdHDP%9L3c>09TknbA{>t)^a;63H5HJ{YP{4x8!OGu5rnszm4V-b5&Tx*SK1g>sUxaX0dk{uDv6$TCS!CR|oc?GLvq^TwOQuZ1-qYAFi**sxkEh>k6<F0oI-ZEYZJq8i%lpt6Ng$L&g=_oUPaX2!gWqKEqPldqAWI?05~Z9)Jx%t8_N7mINCH^@#NZSX+R#1=!V+)7+<5v=Zz@aZPe#LoeoPE?f-|gk6cNIhHGNGZ@F9XvSl~`E!dkfdV<0@g6S`s5M_WEg7xH#~M5_UhO1zH^;!1V%ja(0f6=Q57z6znk#W#{eeQpH3F__5hwa=9q^Cj8h>r91A*0NSkr<v0jv&~9-A%^g5GiGsT0;TOggM1fz=gQ?FH)quv*|f9q-VXg~mE)GA4F%lg{OM1eIhEs|6Wth&6(e`5bF{D6CPp2t@HB5D~0C^AwoF12fjQB-02A8!WJ&e=Mv)gVi}BjuIvWs{;lDW{GgmYpY#OU>?Cb+#%Mn4^}f+C&%hGSQCOZ0<3GN84tcQ3tfgs@@c}c5{ho^aD{!0w>>&at{!j=;5)Mk{X=o}=31*j%yNJb>qubr0BZz#fYW0QA^Dr8_EYB;@RmHm`%2`=Zc%t>qj>MR{lht0l4Ite=sNiqL{L;;`WhU@H1uR@P(Q1$L?<`26Q#`g<B|!*O#2U;?dB>(hh9WEgZ`8e^&2aQ&?NwJuSBCwjkA7aO#1Ui*&Z}1pDU41L^QP%&FkSO!l*w1qN_S$PUp=Q)K8*3QO6J+5u)bIL_JhQIB~7JCy1KD?ryH}37NC^iHOF&MDc#vGf|5YjZdOT9lIlm4nRIq5_M0aBvITMU?yreZL-Z}HGLAL>Zcvz1F-tC&_rkR>hlr}4w`(+iO!u_B}6Tl_2(h#0)aHyXxfnCMgI0uY-%@coXsUPcgILgpFyf28W5rZwf`6|*(03j@Fa?q+gY}N9}*ow_a1Xe#GjdHG-=WjwO}mb<@!TL6k7kEhv+KL-yoer8&XGB=dUNy0Fc@Y>0RFJ$x{45F-E^md*5k{CeZ0@F2uE)cFu-1SbI#MrVr40a&If|O;&fi0`&lBIx$c)O(C@GO9li=V4=OqDj(c3<vrM!(p?6ejSeVPGh%HTqL!#%h?a%*CM$&U%T6Bv(Ri0cy^bg$T(BXGgZ41$m!nfzM{fY!a4`(FAoFgz)#Dxvlp3MQ*x}xD>tmC~fEZW<1;W}@WH4PRvHtk@JcV!aL5$CDvcJ&xpX&#3fB2#jpC$1Dj~f|25A;=W<9F_W8Hiuh#)sf@x4<_TP(wHg3bJy13B?E7?YN`x*`D~QO&}&4oA3=Rz5(F7$1{l%UvSju3rUJEW@T#wsILwiRRL_9bqajs+>O>W({mX;e_nc~H@&Tw_yp)VK+m3;UK~T)!Z&WpcBc!g1iTRYmF^!*&r@gSVThv;pU*B@YlR4n&)zM*&}Z<CE_g9LThxl(F+Jb$#zE7IPDL*j^bBa0Fjp`^diD-a%$?{BCWdBuuu=Sg&@*>SZ%{6L)QNA@E_|~m*|foz?hRjKV-(fkn~bqydLAT^A-w<+&2Zr}-5R3a>6v9R-m5|dkRB|BkH91Yx(h!Vy`)<B(r8p+z9Fl7-_o071gj^Wd$1E9ZWK)5b7n|Zg)ad^U}z;a<BJ=sMt>AO+jip93_fR#k#8GeWA+<>A>-UMBW?^t{ZW^-HhQB9o&)LLN!i^nfU2PgoRtFz&|k0iCG9w}^nvGMaLw6`keS&A0^YR(r1tQU7lIof6yB>&vU$^RWVLyX-j~1se-D@&Fa")).decode("utf-8"))
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

