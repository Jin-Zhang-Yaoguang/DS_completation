"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>&5vD2ZpHr<Lu)TA$+qO|WT__>Ms^D=DZ<1M1_m-gfMBw4vJ3LRN3HID@7}sU@*J|Nr5MOcPyIe_eUL2j@R0TEe?R!w-+ur5-+q7a4`2QI;PtaNZytR3`l|>3_S=8_%YR<~>H0r^|LymG|J#3E|L@laKfe3RUteEczIgZi?SqeRz5nUr+4YNuk3W3)pRd2#{n#&;S8spHf9=i1t5@5f`QhUSZl3Yx;^M{johOHPe!h5h`OEdAAANf3r<Ye34@$4Df9%;WFModaX$a3R-+%n)5xn!}r;Cf%pWZu6@%_b{xBD4>T*H^o|NQRt-A{h{y}OTX)@1v~;Tvj^9(v>0JnH;_o4Jfb*}VMm-OE=m{`yf4-oCqDCwKdgLwfz{*)MO;`!o!0c+7r~H@`ZL3@7pNDbFv$mGejY{@L4$tHVz2emvYr9QgBRw0y^{yc0Kbn6S?`PlCPs8h2qkiJMoe2bu5uM(ppFce9_TeE?NizL>P<o2UNi+RzLu21|TDgS&VJmIXHRy!-jWj^F(p<IOg6Sm2vat{&9g;;{VTn8x*7t{jIGmiKjQU+&)Cn3vsVCmU;7kj*}!z2I%6E%U_UY=7{Vk1xeT7Og3LW&GT|uI};Ws@1*w;7)Kpt=i1eZr1MnfOKWIe{&wcY&~zr*O~0?--6{lzujNX;V1G1TmGo+a^BNq!dL16N5?7-B^<Bcldp@Tu8^<pSp*1z0*?_7CeHxg9i-c5oDWwvtvBzBAEpB|^*1*UAP@NXfXi2}E}p;r>z^*J-oAYG@}G|m8Gl0fWb~zmEj>9>@x#v|{pRxBajVV_!{#T1*8rjP?Qa{N%;}TC=;w#`EqeU4PS!S_&Ch1&x$otV6+(8hT4#~&gmu;<HYf1rfSNyyUtC?j9uK9n>MyY4+Z9=PKHS&2L#p|Ic({MG<-I4@=l_R`Kla6ccCdlh)<1K?5(`~HWk>M$yQ3K=mnZk!=u9ah2EL1S1Pb6N(#{V;6lM1ieNgq&UIa?pkcRU9sA(&X<7>sudf_qH6Nsc0U9cZeoj@-AxV0<9pGR!{uwHR7d~03MPu}{K<a_<}?CPJKInbh?w-YzE2p`e%^XN}wUMcjONA1Ii0~X<Fu)u_86o4X*@o)+x>AX?F#s|mPx2NN2Od1l*J0=0;u=-Mi=AE^+C^G!Z0@e4Rwjs49hc4o5OO<km$P~QK<!C+LJ!F*7UbfrttLlhY@rZF9H~SFtT&=oaS3No_&K$oy3}c;o&NyPevw;S^@9oK{>`p=RIh9k8CxrR9e!eC;)X56Eu8KGkk{JvuTs(?URB#c~Rc^=%d+EX2nn#Ef74-Rp>onoW3TN{;hE)$ixN62xd;B3Zjr3FzZ3GV6<I}lkIBZ5D;sg?Jb~qEe#>&K|h+m2fX9&m?6Fos-FraK5n{;sNz9#3n{4Bkj=N~*H=#8vS(d9tD(|zhpHhJK&jk8w|I(Vnw?H)U>&YVv=zVmS*uP%ec*cXNY@6$(2oYJnAqY7g3OFnYDL2uq(J$wJ-#nshc__4G}8+Bg|65@pF4r$@^$K%U;j9~5tTe1S1WzWI&F!O~cZ>!->R!~FowM5ccJY6K+H;Z<VIMNo6A1HL?EM7-1ps{1@N^JfbLSzLJX2G-C(a4y3k&BRT3v-|&@j}<`EjvI<!7l%Y*KTWX1cqmYRGs``(|eac^Xx-baX$=?z6&4Z0*n&F##xV^*Y02k@9VRHp}D)+&N`F-3G}8KCOVEzk`U1>VB-DWd|M<7`ctepgO%f84NQtfGl6HY=7}xOtNM`6KCX9y+1ZA3w4X9GsDrCX^by8Pfb)5p4O<`X-^tC{=u`fNnz-aox*9B^$TSOJTPc1>APF2yRyhiVJSxu1^VRSv=;2e2-xfA3ZaWlQr2^I9807Vd9Bsq`ZE<X9o`%JkkP|W(0-8UtJjEjvk0tYQ?T6$wui!WGQ&SGJ^h43;n6&NO|E?~_y_d5bm1A71dRE`{Y9AfmIiaeH4ggWpf&znn{_(SgbBtF(O=x53awq(;F)OSZN@wJ$Kb0fX^PSI$=LhS7wZ<?4E~lssq2dVQQ?`{zjqfRAac3sqUtV6z;=^wYJDMy>!qGB@w?R!d!|4^w2*Z5$_Qyl}#aYqfHX55}C`3*;;&jAP%}e~bf*mOiJ*E56&~RRagRYxHRuh#KS_b&+F-N<Zh*r3KUUT69jS_2>aX&;@R{;$Vm5G69Lj@!J37Hu&Ik#cVQsLdRf`)`Lw;l<KCo@{tynLHk;<HeP0SGCsQ4*T9Vc9;SFx6w9BrhSS<Dj&fSM?Gof$C=aByyiHx@uJASOefFl{j%6u#QK!(GQ_9O1C+UAZwS=GLE+i{1ImMJca}K(O3>$CB6bs^M1$NR9Z+B@1&u{^{WUb>LWIXLhQi==5A~8WXD)1W(}Hqkq{OqHZic#WZ4i~IgKjXGhEuz2Kx!{Qg@9ZzUa2xQ>nM{on7!z&djk>=QZCL7r<>GXfh3O5dI%y48{4*f;x>uBawK$>7-hls5~D(=eN(Vk_?p^Kq33Jd0uc7oj<#Ir30nqXvxm;WnVV@YVdal>?lBa%g_TIk)~m+;(6CXmQFq}Tv$a33%@u$krJz3up4Q>XO6Otw6ZdY?yiU-$2tQb3E~|~s=NeELkvN=ykbP?+;Cf)Oub|_ZV7`H&n)bR7cEMkzp56>CHl&jVjO;<&p`|Ql{9xtED52ZMIXLjNll{ERV9>jft}0<ka!-iVY@A&2<b6w%%RG5j#ja$vgIGe#m``ytz9W<&e*WHD65v|{A(K@@cg&fx%*tbDCreqOU38I5o&Jo^&>t@a66NgzRj8klu<vI)R~@|gh*wp;E@c;4i71!O{W9y=a;Yk{PExKhmlc`CQoTNKQ})w&&adz-G1wEqd}PINOyzoGPv{9kMAV69H=f}!sA0Y5fM5IG9DMtPXnPRjY*#2s)4(;R73-nPizA(D2({DW#g(WY$f+}bTR#TxG%*Dm&z~!F5&wM7#5d|!%_}yMyP}8yd*Fkh6?Q|B14ws{BrT`24<p|G5wk8Eoi1*gRmyYZv7yBr9L3WB#vnvyXNHL$`0h<-##Eb>Ts$HqBoG`b-115(ASOe^LS}X#1&Jbv$hlAF^}6F^to9jtbP#;=AaG3Q`~;^fkn<-WO!7hTjjK)Rd$mTkrFA1S&$DB+iDX2rMa4x$t<CrkYtCqQA+oRoLgQyjANqs9sM4i4pS7FYF|F9A*4YQ$zd8<%+jmMZAjFnZH?HAq}gHg_M&=*R+9gdOfM;f2<mOE@`XF)tQ6u#$c$e|YgaZL<MtMB85`22l?3!|?lzTYI_LIL;-7}KiR<WML3buzDqbf1afFiITnK_^mvtufKljp<oPIfhqOHi(T(wC`S(34C)5a(=(xnh)rrqZl>6Tn9DJUXt?=NVnV8HNEyk<{>W6-bERU|f!4^_lHRxLeMbwp2dgPfg4ZaQPLT)vo#RKA-E7`#q(j6_7tc7uZ1FkO(bD;d4Kx{A`6c|B5s05)rRHtVKj2EE&RS!@Z6QKbcvx2ge8piWc~7id#SYK!HYxpHOEuvRy&gQu0O@!G08-cv7MU?;deiU5pH&dU#r!J(iWQNXQNR;^fnWP;&$iUuiwX3ck3ZW5A7$Rfii!cJqobq&T%R|=3Cjd#?AtGl!XgFys|F^iR;#QD`^x3T>z0nN&kudZ^~C&V+jfefl!uF;s=J%KNeX`b!-Gv<S0!epupgI2^*dC8ouV1sIKg&$bREPRD$8=XiyALRfUh<%`-KW;b1lZZc`_bS_OQ-8eZ07s8Tca2;l+Z9+fVijiKM+N2IZKW(+CEXiLUK1d}yPNyd@AzutK17Cc|E)-2vFE7r8E|9)v6d%cSIF$Y7W|pGVS60p5Z<X(dvx1Wi@m7YslzD^o(k)uUYR@xpkZrsSsuEG0mAm=$A@x}`%+ZfcU-$E-GH4mNxz55(qgzh_Oo51Re+WCmSF^krfxdNCE+RO7u6evGD#MVGoRk-^JH&^{rnQ{Cy}ZRESAkOaT%?wkrYMo8*wOZtDt~7Jv2s#4dmA5Ve4wt`nIMGeV78G9N3D^dLG`$U;o5J$1`PPX3o=~&NqU`%cWm(Vm6W9szpf~{cL8MOJqbmtsIiW3aagbxd;xS?l6HDX$b6kSgXdc2@s?zC3_2^6{f7}&8x<!o!Y4AmB6^LUBI)ZP_*&1aCFrU0c!|F;4E(aiajOZ*x2+GlN{f2+oAq&qcH0sJ{@7WsMok?vu#?UR*zH6BbmN3i0)1!E{P8^^OxM|JQ!Y1WKy-eXx=e1T3RP7cP_X!IdKdR6Q+ci<Et#SssM~=HL?UnrUS?CYA#snGKIGBZeAWXU7|6Bb72wXAd6yjsb+;dJ<KvIdt0PS8T?&7_X2G)6xonj#l8|18MAwVL7F3DPB%-bQpi=E=*8f|Uf~*ticx4QF}+U+uwiKCSVD0FGBO~t(@ty*4<1W<d<qefhy9wq``d}UPzggeJ%RlD{?U`Pr^R{Y7Pc1GiS{DF5-!|1whzMCCFUq{q->^~P#fuiJ8koI>*VxkVtJKBV6Tn={SX^AY}_XroAUzUz`XC!Yh_~&8jYn-!V;Uq*e~foOfwBfnTrx6OvPXY=PwW{0y!H;-(mlji9HTh9DLdmjQb^q%V|6U#6(GCuW1p+ogOenLSbWiol?B2Bs7U_9W={*)#`&AH#3UaT+wIqvb0KlEaeeo_D+<c+vRg@qKhtJfTOuy%U3OTH~g21uQR!|lpz|bWZWWR!ZkKOp@E$YnusQIuH><-Ey4;Id#U=jYME1@FC?T#g+8=jQr)@Ax1&!BZLP8*CE@f|(hy6vrv`7YSdAZmtYijN;?m>*(BBkSr-Yc&h%I`k#N7^2#C^+bCB{)@j}su89;m8i%1dqzkxpn#WBh_70pSZeN>?LZqN1WA0$3!Uz`|-|WSDe8BKf@)*FG{_;_#HWcofVmwhIZ|Eke7q<~|*9AQPLDC)A~~Re%W{5Ipbm4l>x1<%qMiEKfl+F<GhDTIO*{JRUiqn%1Or4zFMuMk&hAC}g)-F^!>g!t4blWgLB08x5Zc-}fJ)PX*>{O0S}Cjf>S9I$_T?>pKt7JyTP-J{Mhx!1GR{^?n6U4b)aGKN{_88e>jllkDM=kx-yqR1dr?#U7s^Osf%jt7;<`k$j38#^$K;R2r((d@#@2L_}A+>x-Cys>|jfSF$qREwBEXtNX=s29`>#C((`=m*1T|s*FVT4s*;K`Ry1eD7MVX0~o=Dt07GulwhYAE0BRvzM2(2M7wb3F2FWW8&k&N@o*DSkr$namBwb#IW<7F3?ZSedep{UciJK|2QIJju>-G$1j`2D?aoaU*i3>Ax$Nc{kKlk7%}gzuoXab#luhQLT=eIYTsBEU8T0ZKv&<@wq}jtV9HI*Sqik-8OP$X{*?9pT(5wFXN|m013QXAI6!IoripPEU;(2?F9Rg%Ct6~|m@?5Q2>k@*-^~o@=tTe?$efeS^6{e{Y4%x3Gn(l5CGdEirRWWE9<B?+{ft%qzK70TYy<*BH$sAoKFZvVF4HaP@FME<3SInH)4Uy!U6FNrqkIu@U*3Le0bKq;FO&l6e2!1w{M;@3GwDgo3V5EpgnD3Jj^rxSwPpAV#)$~EI1T4=omL4`U>gpNJ4&k(|g5OfET7-^R5yv5kDcDt<v;gNuot##PZ&g-n4UGcNj)D*pn^j`V!w8eqg85&?dP{Pf-^CL<IVeNgg((70B7DT~xD@Co$m*Qj7GleYfK{kd=?G~%aUwJ;gJ4%mE{AStU4;XYqts!LQRN8b7xjcvtZDd!v#OO&edfHag%WZ*h2a5vg1Et;hXANNY&DXDgeJz6yuz(RHEAbtUR>PJ=1r7lBgWVzS?q$Kq!Y*&q*p-SKTT;CL~>?1>P{aKNCFpBiJEo7fuOH$iUs7AAewZ-E>@Sth?B$4l0+d1a_I)seZ_!r?1H_TcY`n71-pl(zOkd#jRRw-gl6(pSjN@$*DZ*5_~348HRlVrGOh0sL&w!G0hb7UmO2bB;*7)#n@1G6_zT4k?<yL-g@<58MFFS6BKtxgG^mT$X-<lEG24EVB)Z@Wf0+lPuO#wF@sa2oh{d9id05pKFaI&M*tx_jpskYVhCBqyiVP}u^UKS7r<5UO2=?SjffKb8fS3R?gEquT_*CdgP`lvUuAGNUM@Cfrwr9AP1iSsY0TrLJwnD*4XO!F7=jAECpJ<Tfi|+EN_i2#vkz6F?h%7+TCBiaOkOo$5D{wOcI91WSGb!vWyM%9ZH;6>tC=;!5Ja=t1pT-l2ScL2c>6=zXUcg3yhVhr>r&7n(YquH;S(Q+O7?I5nwIL+&K~Eu$R({;UFV3h@aF%m<OQD&7hEN7*W?Zm7a^$*yOk1cF774^D{XGhRl8T|oBJ3#_bj-MI8r&Ks5{JALdE%rIBc&8~a+^`XYr##CaHo6D%SJ8&3MiF#D3)hAghijWH;l;UAig6Dsit~aNRy^^f|MZkMa!#Bcq`_mdC1{0U-4ehXYYIJ0#GrSI5hw#LKD|`y`>wy2WTV$p11yS5FYoloPM<7H))9!L030;Y-aT2$8Jdh?j*h6prpZ25##KP&WgiK{9}X+vEAoVaR92w75}uityG6%3<VGA$Z7;OJJ70w8i*NC$x6ca8doW&W2s`Ss#m4UR|Mhd0G>U~3`U;d3;9QRhU4_$Dk)LipqLxhGRQR-`L9<L-5mzSG6Y2OJc3m~Nvb1DJwO(BhV=H9777(a@g*y00hgi9jauV!bnKK|(fda?aizBTJZW|K<|R&fMSRe!UEl7L_q|zG3W--ORY*mVic~mC)Pi_LA)4S$4M4~b@h9t0n%I`pBd7USUmRhh01b~AQG|A=(_^o)S+%wUjP9MDrEBx1I91^X*YdE4uA|~@96^ziCGtvDh=BYs1Ark^iVouHXa#?x&#7XR#fa2J@k}MT2YzXZuq9zX^(}SJ)x;j<1eC3^?1C%ZKgFv2DF>Gt@5=*}O8zWwK_Q}>DtTavb28m&g-cO8-1fLY6~(WB&idhfWa#STMlEiFwk5_^xt}GjLhI<g4C(^`lU7N<NmFXxKTx(y9^tcwHmasjGxyE-#1saOBJ3r|dBujJw>JS!8y9Ck{AL`U%d+KN@Eekxo?qRUoVYbemgsZG^BxM(8e(LfyIuJ<2&t{jG1D12Gb*8;4WBd`i{)L8EG$gSfjby@{ebs#jQsv8+8_p;w_eVh_BJ{?EfJJTgJ#j~N|X#j({3^J0POrGu|KWm%s5=<5)y`&lCvTLQNhw8vV{xsy)nfpRLed%hGG5jQ7+0r2!tkuw(N4WgVl1HIj7Bwb{FM*&Pqj<ZOKrx5fIe;GTIW?-lzb~KS~8)r+Ne&$$DbsIt&wW76xq0axkuE2>F41_Dr5QO%x|?_cAJ8o0xA@IiZ8X)mHsWn1h?O!RZ#3qeiflPIlnZg<)n6hKu%*HIDqI%amkZ^M307E?Rfw>9IQ{qRorjRTXxK#Z#46IDMmu8z{EP@3@pP%yjGLS~L441z<51OZfkWw<`#nv%5l0k=;=!AZI9!X_21g?ThAO(6~jpGGZAy&n8v+RU{{co@Giyj*UKqGRH5nVV%~Y(U#4*YvMAI2}Zx7!qK?Yfz*X{JL9i)ohNt%bzHKbCP-rv35tv6@w~9RAKA?dOsZIJNJ98Jf>BJ%s&zf;kG={GDcLvWVxyNPXk0npt6blpLk27_i_eF$NjALFWEm~{4Y2~*??67kbu4$D%obTUwQG@l?s@BR_g+$9fu{1BPsD^W^0eB6{h>-e4-LOmilke~86R~O{#ST1Y#Sgi1?(18M2b#VIVLyZe<)o>4!_wXEl*%B8NOt6h;m57>#J1mcr)4gM<qg6sX~&^KY_RlSVV>tcQYuW44Mfks$1;9)j4YvRFY>^V@N>KU|0Y=5>%z*JvsuYxzl8?axqxy;V1VhkmMQBY@hNLCc;<vv_b?&kZT9Pj)@*oIHqtdnsT&1rxDC0B8WB}!`(S)AOOjVJfu*SSV4l+q=t5xbS<&T1Sk{}L%oTlTxV9eHdF?`THCBtgan6cf@Rg<lMh$SpcukMahTFpK^%46xCuGJ@yl{8qfS`3mbutC{9)DHEU+rtS>!Za+xM&^dV#2MPDYl0s+_Ntq->MkQ0VqmnnBUO3aJdLtGFd4pVTlQi?M{KH<|-K8D_K|sft*YY-Okcwu{emW0ljh;^Dvq?B3CNfh92+WeEkXX9@PA!qLQ;HJ7D0_29AzS`nnz>B}n0MFD>}dYy<E+#de=Cd3>;Z@_lPYxI^PbT;qMoR|ow+*@!N1r<_BC^!=<$kXLdB3dR+M~4BZ(@b&BklfvgrcTb4cVae9Aqr+KolgFdV^s7l^C>~;{Py&ULw7&%UV-sc1zrQ4yq$u1U3IyUmS%a0B5y@@65PRfdSn(<RWmwORlxGpUF7(TaFdcGy|fs?77W9#Ts=ijPHIYeS1Nj$0jB~qf+Uz(Be*3747GWp7=4N0Lg$k~hN06n3Q`vk@HkUM=s1mAB%j(fwvuZXYjjmLtP@Dn`mGFxdmfeeE3v`^wnT=^@?<Nbf0|H?i3`+n`wB`<10EjKP#)DCP+cyo{T(z@Rg^;Nki%jlg%kA@iLawZtb6bE7BuCw@oHPJ-f>YP10X4DqVO{J8Ux)9YRGY`mh`1m99p~4T;8cOaS^KeO-hn=wI0+1pX~6gc#jU^9f^|!;;g267LTqSp{dG8hxzZR6P%!dpPBTcrz;vN<>QJ;UaiDFav#UV_~L*Z(ldjq%*x#X#S0Qf_{s$d_Kh=^UaDZ1{`0Y#BW(HKif3-1D3mqfv8pTU6$(-uFUg$Fgha7J&ENN@;?@uctG|{7Cp*?;^NN%wZcb^-zHWNPMm4#`B8LEkA@DDw5ZaM@(&*CX-FAKKsYdxLDo%|+?l}&8m>#$H-V~|wQZ$gyp;Heav$ZF}xZ-OObizMffJo%_XQA(lkrD;oFninx2WI@z%}cQhJ!J`)JUTls)g&Se6%S9uFO4$u@Q%1Jk`WcIemR<F@Akl&x(ZIV!&5m->#Wu5Q97=wJz@jEhEq8^Lm_~E2W*&eJq3f&kHejwOzE*Z(|(ZYj1iDjJEv4Zse+}}^@rpDS>#&;h{sYD8GsYTqINw@fPRdfJqR=tHF-!f5~zq>@IH>#Vj&UdfhIvwr$W(%Qz7IIM_ah;Ky;Hc>@sbu8!wp4Z~4KMn-JKXE8-wbw7*G<TE$sFZle?6AC1{22wZ8CxDvBXq;47or=Pz=+~}?7CV8?y69i9j!X;V|Rm`qfdO34Iog3&LBz9b=kf7la@F=6W8g19;aprGFE61KCOLad4C3I2zjvHyR-7Hn&<3lt*D8w&<d=pI~p`FL)EzK{&5NcgX*k8?Y7#}l9CR-%N<?J3K#qTHf^+lwg$a3bKr}}Fd_QN24)$mNaW?+sdthlDUUvVfNzz_{0nWXWAHd5=DO9D`J{w6gOQg(R|FDmoc!wT4jklpaLNCmcXlO`HM7}{8H2YTI}o|3VIlaJPc_a>*-L~}mzg6sE-7>D7VoSJzY*$mC6(wXnFPh-{syTl>#gC)2`nwDarT}_kcRhT<VFG7mS(Fx!n$8q{B%0<9wpKr45gnc(KN7w92_8nsBO4RUL14KMd#saxTtEqQ5t{nOk;E}jcLsU24_^uEU3-TReK;o_pcJ9*eSVn7-PlsF5yh5Xb%DdODNIsn??4_Nu@jzYXTIJ4F0l<+F_VB~j$=D~jZ_uUtgbbTJyX0=r3i*zqhWcC<)UaaqMcfwPO;<E=p;v`YmV`EesmuKUkp^8fgNC82auj?jp<oOPZd$pY9-^a~<xv=WO0BU(>Cw&-#ob(T^$7vSZn+axMW&IGlDbqqaHFE)hUhR+*OQVCx*=-3FN@U4C?2<&^>QVSNeMA;YF3x$a1<k@-Je#`47?zzpiPPi9jz>d1Q`0RR38ai<oC)o3kO|&x-aFa+)V6=PqdewcUo!`h%!+uE8;Yu6^Pd@UY?K$#wD~t9ohxzprt#UcFh+|GjolMgfhJy70FAq8J7|)Tddv~zY~ehrYX)in<9%l5GJiBX0{|^a2E3>A_?mj;+?IGi{L`zt1$lpeccQ2Kz?9GZLkE-RIq_GCDm$HpP!xaRh^;lf;3{nJp>Qc8-4qTR2P~Ga;=Z)So6@GHJWYY>O{3veEjslX$2H-PGVjQ$aZ4&!6S*LeS7dfdh+Sl2?o1)=S$q)FtT?m_bLoqUuf<2bv&TQ<9U%DjC(6vTBj<*j%1V4^?9kO>X4PgQ5FvkePznPBjBX&xQ~cx-O+}<XUn~ovPx%~en|8YoF0)vYc!#+VokMBzp!JaoM0WokS|eB;=1Q}&Wh8rz4--CrzeGr6GVeIdOHNC#<u-W$JJ<31>?p^D4xPxh-)e^;N&@^K!YWR`y!Sa?{SLFv!Xw@K@Un|=)$S!up$HTjsfJreui914N4c{`eO=`ZbQpYZ8SX!$q06@gb_O@W8Sub91bpWOT&GE(3Goy>&H1IxN6nHxQnXOWzEP?0FSa&W!Y{f4PZs2CRKD&Y#Q<7NWMa{st}#i%>3<{fQ3m%xI&<i_mXMk1IH<nt0CH1sX^B9Bw9@>+E&T`FfW#oV-~4xWeWn3#q6|sgkkI4*@$+INmxpgU`*nR-<&gx_2USM+7iWN;=T-#M`|1>DtSd1*O7Q`AL*syT|H#Nv5+o_P@P#mVA99#ui~}PQO-i{CYf&gDx*Eo?dCl~_#Uo;_!cqUkh&2db+Szb<Txu6%aAy;e2XTw%@^tWD=?!J-|~<^cG22Ma=gq-kVVE8c%lo4m`3Xo3htAWcf}>69feHtWnuB5l!=7Ou)q_QL8@p?l!rzW-N`SYSfWbV4x6U-YU6!KOERS=DBl#?$RsM#E&QE8Qlg2Vim;yI9VaJ$I_y9Gz}4k(*WK0;P1V`5C}d=l2Q89X*>7xI75(-t6WdM5XY1}uMNeF3P^k`0k#@)15E0(1$`ylBNJTun6ZfJG;I(uk6&YL2fn7p3I2d>8s3jpuL6A;mYss~uh3=Gvf(ER*`$b<FtgeAY89^23^%i@wJMSd%qmY}aP*YREVwn|v#j4SWu=F(-6O|(KVbm^}EhS_(WOW3{%vM=3ni`F1S%ge*tw)%6m#Tdn4<A5;b*hdBq9iirJV<X7_<SztZI6tmlqy@Bp1sW}pp{qFm&G8v02c79K2IAr3oS3+U@-E;>h+q@x2)ycXVsxM(Y;rCZsXZqT24~T(Ci8_u5mx>OkJmRX@&EyN{U1sq>mF#gLKkqHsaz4RJnd|c<{vSQRK;k6Un&^`&ZFt!Ec+@J|KZGG#Qq2Mg28ZK9SuFyG}Nm_zqInG$+4hqU0l~i&nC<tC$V8YRfV!o*5B6Z|u~!0qe#=Y_5kHcP&=YO3jkN%Ti#1An1+QqczurYzeztENiMUUxQC5$*ySatw{e+nzU-Eqd=1ip#|?NwF$JH932N-ZsUBRv6}622>jJaX(mq;9%)pmDmP6qBw`qED|~qE!@RrWQ1x;hv~x6#+=SoKj!mL)OH~W?A`h=nL%&mu9Sre9tV0$*OqAS8gIBE<bnY~acVMO=-#s^X(LlJtf>s7&f+vYqC%@gp{-7Wr%p_9^$hLebD>jSG7tFd?&bQNc=(_9-dYu++L`EwMEGl-?tt-C6L56-6P{({gVHu4aM>N;llltKefc2T~QwSVx|8COnV{trw_{s2zq~tDICF+!k0p$Y98QRZ?E{8#AO1vuoMb?=W?4^ALBROAY%ZKVvNpFi+EEZYsP-c-eNQuPnwC4~e6oXgdd#9rmK~r8{CN_kLkl)4!!wiXpjjZU?H&Y(Ck9XV<oD@en6oI#{QPZN&F}nZbPHAPLHEt*0PjZ`MFQHb&WvV@eGR+p!mGUsqGH;?F`Yc#S#YZnN4`?QQK^iED{VE-oA&wg&<b=uTJ9HyK;5uzP^gl?vTf3^27==Lb+#--FO;L%Rp`#sTzr<l;1LIS|s}`RMG<7&%xQ9bvu5)5x9?nd8tPpr~TYYeyJS$)0MpEpl`0Y8I-jN?pov~tNReXoh3An5R+k@kZvV|3aN$M{@X_IdF>(*SClaSMM(r>{6>vvMt-C7YO$}=Zh<;Ac2yuhR`p<;FPhSxM%p)xZ;aUB^dG#{%Yo;XTrNMoSmK01lrxjvg*K6ft7@efeEMpd1@%{;ztv&h0il~#E!cqMA`;`NKx;MM|+RYtq{xV)J4^RdVTJ>_lEj?_7vlI6rmIn|Ou-p;etFh?&nk`$LkMZI*4J@8rUx||bS{$g)=^CmFq+Zt&)wN?GXdWVrL7c++qqDk3}iajMzGH$GGo^(tA^#zNpw%BJ4OtkG7&)!d0>y%100>2RKwn{yVjNLu)O%!p&NTl-;G<grPt-<5f5Gj95;nvu6%zce=t0_Tg=_P(#F4PhVBPey6`C6b#W)X`Rre0=szrhGdK0I9Mu4a<9j*bLq|FlD30xC`rPbBi1{-D{OGF%f1K5w#07tsaK1&6@tykwqiXaw!)&PmQrLC2F=C^^B!k+fiIm=O?>HsuBdR$y^wrhK=|>};WdRNxBwIEI*y3u(}p*(}X=q!+h~dc}2x6)qq_^r}8xF?OF~bgFiX!I96@s;bVBaqy*a-U~QD`QX`q6YRcx?#-Gtm%ika&a>oNa@JOBg4_!saNtg>2_C#RV|noSH7vZGh1^hySUge5-6ML&sUK8~a^*kDgh}&|p@zb$>Ma)hE1T5v<XEwmd2+HlVj**zfjv<3%RlTHKhuO1N<eU^;*VAGO&}1Fo(F*rPwK_h<?F*AMQ2)Js9}`}SJj(;9-A{iqc+tH5+Juj6UdBIc%BG_6_XHxvTT$-+p<ji!Kjh;oW~f*1kX(gP-vW~;5aG26>~z5q*VZCS9u5({T^oqXVKjX%B<RXsq<`YbowMWC5F3n*E`qr#+7IZADm<~S6n%8mq=m6z`BQA^a+}cA#w*ble7KKR2(#s=TZ9UWE3yocTbX`iN=&t6r0`2Zwl>hjrg>%)p^%$#DCC3)}p5=x#MS*xIv}qaXRDtKm0H9t2b%")).decode())
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
