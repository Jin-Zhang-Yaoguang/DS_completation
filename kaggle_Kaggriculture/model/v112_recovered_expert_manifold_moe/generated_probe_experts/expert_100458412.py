"""Standalone reference-trajectory state-tube Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v88-reference-trajectory-state-tube-moe-rc1"
_MODE = "full"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("c-rlqO_L<aai0InoaYeVk;&T<XaZ|mU|_oojZv^M8cc*lnv8%1LI)X*|6M)Pm6;w99v<$IQI%EM#lxc6Gt*u9WPG~6{`!A>_~U>7+rR$h&;S16@BZ)~AO6Q5|N3u#`s?eLAAa}UPd|P5^6|sJ{PEBK{PoXXzx=m9{`G(T>2I%J|KY>m|NbBU>32VV`sMF`@$-j|A3p#3<-6DabzeUI;lr=L|MBHR^2OJ``_s$IFJJ%SZ(e@*^xF>~WA^RKzxT_xzx(a?zxnQm*FX5_*Do)>BY$x5A>x-W|M@X_knex-Uw;3)<cF;f^@k6iUw-=e+YkHgryqa*^|!AsPriHsAH4RXHvru~y2>>BoqzxP?|=B^KfV6@pMU=i1Nep8@9BD&AHMs=%Ze%a!LNVx+n?9h*ZT|p;p@vz34QnT%a3pWxcCk0&%OLA;s^iYyE=*OR}^%JpSb+p;S7kk$Aa-TruyFEIv&Aq;zKUq-tsZuM(XzIL_o@SS8~{X!G`>&PrsMH!^=PFML@i~@|A7BYseI&sI0%B4F#ElyGBL%`pS=okZ6C<<sYF4x_;v2LGj@rAGpW|95V>^E)i`KoohsM?cppDFW-qt=O+>P;V$EE)TYhYkUf5O(O()c(jQ$OX0YQ@?PuqYpj+pTo{78-h4c&RhkW|shnHXc{7?Vz^5f6n|M2~P`}UIdellbo@Azot*u+jtcfzUfqY;M|uvgTU=gxy$u_((ni*(km>%$Iq<&W&zY|0<=_UT0%4Dv&ePrvtrHIX6fa`8ic`QxYGkw4_JaFag-yVd;k^267g9C+Zb%N4fF+14^=YiIm)_hu~OCjV7$k55mX{Jh_PF>IdYnh0%%@TZ@D{O<GLzx?>)KO)-&@^I^(o^A6bJI*hlAD1&u_@DS18+~mz<{zFV>ojxs&VP2_rX<?iTH80W>X&;Rcgi8#Ro}kH+nz38?cCb01hM(qu5}1n79cRa;kuN4yNhApQK3O`yI2*Wp59BPB(^|p^_8ed=PoaS#@XlFXH&)@ZU6g2K3MbZ^_@UOXA0ht23_AIyY8q6bN30%Rm11@%YAOeg5wTrn{EeEZ+gcTd@%MUTd-*{_u`HX23!6|k!tTo?0YtKpkZvq*}v{Qwtx%9b@$)hV{F@gi;Y;e&tX5P{ghNFHxIe?9tW~OW#6_-eVFP3{E@rE5L-3+0vXRj?6G_x%suw9vs~>uScyH{W{0(RdK|dc#=NHNfAQ%vYfoN(^W`6iE;97yjQr{N>-4}NuViPWE`pM+k=lI*?bLZL=^j|+$+g!}{N0cLmH$D}8}zqi+Sg&6JoWm6t1-1Tqts-2`L#soa0lEqhqkWpT{mg4*VRI&qAk5IP=b6g_=dL+iN2m5%|p){p-ySzW(|_eZRQHd)2(c-ke7;{JXCo&!PbQ?We9TaV?=>2{|KD~f}fM`SH8LlBL|Id`RL2{;eJQ#*YZ2I-4hD`$h?#G=Np(2^pBkzIsZ67e(M@{`p!oZ-S>MRiqaZg>&=XRik^5rEkEpeJ8<PiR^jS*_vrd~Ie~K9ul|Km;fwXaf+@l{`+Do0u50)DMddzS{zVLe=-9LVr1i{)#Wo~RnPHdmSp-`c@;mZ>-TbOU$H4mZ>u}khwy2^(m2Kq%<vX<~jb9#r)(Fb>DUfgRg(7`{8}vH}Yl#-b^@mSB@-#A)!<67?Cj1B}k;=Ot{rIK2Cm)ICich{PV91U_^<<9vq@3jkHuxd;mhzB~!;(_cGgR|DvmH(7kjCDs4R)Xdxfo;L>c~Ujr?Ah}gIVVht#TZp?_j&6Fj(nCJ+;KyY|v4$MAJTh`t-Uuh1#>^k*daqv-~uvNa6Bfiv6md@1q5y)s-kP!{|tQ28(s)1steQz7n5g<xG;dq)jcxQ;Jx~yc9zpo4r!4Y99@L{^sYyBZS3Q<*Q6zmy^XQ))kOAyRyzxZ!8Q51d(sAJWJH;Y4C$2b)48Ht|<HV4WMs*suEdKsPlRs`{f7W;f9=3#M^4FdFA}A-5UCSK2bYF{G$2_+rKotr9;TyFN-q>zTGRjD3_~ILekoYXU(?e@tKTgBfq1g+AW=@?l$LhgYSywOJ5l_a?5}xiI-ySE&hIw46vN?$eE%16gvxlwtv1Znb=7%UjlZQC1NWlxz4<OJVvo%v7jJl8|)D)Q?FUgLrK|cr<jUrt33S+%Ye!Sr5rF=Ec7;msPfp&H_IAP+qo70E!YQYzFW?is@$;Z7dZKArG^-?HZ<jd{Fqx$hKovl3lhx4dPrT%1+i#yJEU*MNIg~&>FFHNFL_v>DlpqVQUCf_{(K~Fg6SQLHGJ$UiJo;TpS5pIBr^})i!hbqXfB4xh{i5ayviw3w^|i_q`(_z8?<IXV242+Y?~RwW-V%c%p-M;%@<NVz1U9GFE%XX1-I#u+ekDau3rE`*bqc!kO~Qo6PIhxJA8Y#Mu1z`Qf@@ZDW}ZFcAe0faXW0+W&XWp5T2N=<oOxdG(_2q+Ef)Buv*b>$=#gi1F<6~(J$UdG9u-vq3fZ`;kUk382UtRR9%%V$gg9+!OGvP<W-ta&T>nm!}-P01l8j7Oo1|*iQKrT!)Zr7R&k%gj`QS#&^(crBYVJHFAp;vejLa_2>HQ0^^fQmBO3}Q-rG}%jL3$N(-^5&5=ljt@(pZ^ZFik|0AC{9rSmD3p;KnQazT(xg+%(w_2jp3)y_UcvvQb~LEl_7B##?V#VA!t5b>eppMYY32vM*IFtb>%lL!4P`I4%xsn~piX}D6nmie<^c9n3sTI>e>i|9AmHw9lcfFWa~<sD{S?5dXsEP2xYoya|<abZBe$xHh+CmeECM9wqhHKJ$D<x5~zT>O8sC(%kMZaxylRzlf!`%sC!UU+oHV)|_H4so#LAL`eC^2_gkg`PWQ;}HKP7>4$Ky<f^sI`%MvPr9MrVolbvK&f1cN}V)v+2mJ!u@(rtYyr7;NJ0&?8jr2%Z{9#8Fv=IuswALtAIQ4eQ#D5g$_Y`D<fP8|rO2X49$<S49Y`%Jx*B#E)bc_(?A4I3ZECy4vn8=L$vmU>g=3BICJVESOh)Sl1?5AT2oa4Vvp<|R?Fcb>xj>YMcK3&p6o}A8+0EOKuI%3YPg^_uJAo*Mx*PHCQvEKV{6gHF$rWZV3oEZgsNa7O$w<3Sfv*IdSQQr*ZwS(>oTU_0<U`fv6}*Zi<_qkJ5a_l{fm8Cq{i^Sfk9{h#0=0RV<rU`^n&;lwGjYx#a}6IWr^>F&G`rjo;ZA?<R(zLJ<I@**Zk-me0!6;G3pqTpR;tT76F3Ku;v9w`TAzZjH?34lQJ4Jk^YRq1><S?&$5;ps*h-q7@*k@142dPwM7)fTN!QKqN#Qo8FFWvr@WU`~gYJc%-P8@WIVG@ITX{c2scvtu{HWwqpwcg}jN@b1r*BP#22JFli7$xxF~}vm+!dH2VCr4eXO8HA(7H61ccIdet2w9%=G2F8jvcD%k=%?54=_qlfQ2E+N8WLOC{H=)A)%ZK*qBGwAy)Mz+{<d`>AqYaax6le5UAA)`-eyn3M=KT?9}ZkE#IuEA{Az&TBg9<U7x_1n&{j|BjZSdwk7JUR&189$A0NGW1?L*vNfS;PC>sb?#!w_6($-c7E-dPgJpEVDD`WuZ*ASA&GI>Au7TrFQHDYH$Wjgu8_n{#k*|twu|1H8wyZy+SmV0_NjwF@>-+oh)6bWGOEi|nTh=x<rG;wT9i*aSQ{+NPYyd6rT){)F$xz?U+z4usV~TzLBdF{;#3K4NQB5-8O8HT29>{O76S{+8WQG=t6!bhd@@~igU-hZjL9<r<5jhL#8mT4#wmA;6FC#05q>6=qizVN-#Mz%Shom)l#mVFH7Ta^DY>o>4F(=Ry_s=By<|uvzOe2EA2{wM|cG_-8V>Y;0be7oY;0?6=Vbw}_(J7IV8I!>hv_tgeLtYLUt$A1eHNnx*v?dX4{E2)9<Xh;lqNAkjT}X%S>uyn+06sGIkaQt3b=yVoVC||o6D-IMg@Qr{>M`lng<dug2>cj0BjHA$@`%#}oH*5%29>;w#GQp3Gvj5MsfvB%q*`7}YZ34ATBjwUdNMXvsx2tpEb5abaXHofQTnE;6A9y&?q_Aloaoob_e({Z7St~(WwgHd4BIx?-iB)(T)Qn2s7Q5tu_8VWG1!`3dF3QfUwT?&mPuVw8O14@>F}(pJpyHH+|(*FyrZOVqs#9Zx#`u*nmBf~4eau`oV#6Ij$6vXmv1!!pX_)LyM(<SoMW`^E=M%Atx}I6G}Enr>OLc!o^l#m-X!(w<&{&RZmQ*BfU+@QUQgSqEM3oqiK98PV*!;B=h_;#5B(-cvh>YelvGA=B66a@3^fl)H6DIL+|yNUJB(rTiMsQmg>UU^A?N<;c{8gq{>XB-mcX#pLM*$2`u-SCQhn1pUNkBwu-gT@Bi0T<A$|Gh-J-k7xyr?c7J1;Wy>>s~RC}oX(gNOYjNGJ<S5J-7^0N{KUeqO)Du!x>{@d0S+}r|V;*dboXm-8TOYad}Fqv6}S%d{KI|)r?I;d+I?IFg!6_Gcx`3v7Mhc27xaC+eQJoApPl*WT<4D<P=YD&U$rr0O!qT9|?rN6FS6U4f|uaC&K!64G*_*{r>5BBm!mA7ExJ&76>|K|H2{tGG_YHJ)E!`(vuo>&)tX$xldt*?9;<vS=pAyH6QjFxe2qz}{@p)rjy$|6!F(Dut_*k}yZ>JY(+TI|0kx3WW4(+yM}ieR)$qQn5S)gG40V)<3nR$@Ogwa@G$B<%iEEXsbg1cpu|QuPkV8L^oq;VE3Wu@5S4HK@3eDw5(#g_ya?+EOrdn9`q=nWYt#$7b;|KU{@Es<X(U#H`QhkeKj(fBCoSm$H$<5o#{U<Bt51Z1?LyM&{p};WT3hD>}%yGb>k3eEKdm1|=e<K2IwUH>_HT^sr)m)-v(S&M=!jYK0;sC`0_27mOvxFX!Vo!zV5CFv7jGUi#DL)k+*fkV_&0wHo>8HTk4{6)=TB-P$Mn&W@l;)q`UGvIjQt+1bWGEN9K?#}&VeW=Ih0iB;-W_zs+$EE`fj*&GdfA_q-#n{d0x!65Hc*KQ2Zsy=F%?3aNX>`x4@-vAc{jKdY}&(caiZF+<jtesyH`4|`a-6Ob==@obdH;fk>yFJ#h2m;U3hjS5azLa{2av5PjW}_%q+<%*AjkW6MW?wGIzyooCpu-LWJ8+f7`Q$XF0}mWQfA3+vH8;r%8X4Ci)62}b36aQa^uQo%*qCAt@}S;7cpIfTjaC)-P){?`gz86r@*wO1$a{RP;e{aN##f+ln}LJeS*cLUAo4~~jXYnoRM*>adWTh7W;e=0X}P0RwpJNP?Ss+wpv7US!#z<mThJg27^;eEgx9G>;+vAv3HAv}^Mphp>T?U40mG45u9w#^%_3Xi@Y<eY$E&7XiFtRX?D$y$ODayn%-hJW&(sdc5B^XE6lAiop<%>_IX~h?9xC|KL75tdZ-Ye#h_K~>DSHyw*2OP^PL>Ey@<k&bcZX;Uk)*IbJ{=DtGvC+)FvW8%Z4GZhB&4tF7o`PqdD||{i0WoGWfZD>IY{$IWG~hX?~uivMSr=U0-f&S<zW>&mCzC|nzb`xm5fz7QYC%aorTe4%15eZ;Y9X23`*Hf%~(AXk#+5|;H3+GsQ7d1rpNKiW(e1+lgx~&0V<0vq^H6P3Vsz9w#do9S0zJaYT8$Ow%@kQO1Zk46QO8X9HVvtp@wQb5{5oRZB--tD-ab-Tv-sWPj^QQz}h`^OVH>lk8%(<7xHP+cgGq~AFCnvQmG8*-rJ`&J5)x%dZdVjXo+&F6-%V9aJ4~MopF@1F3Hwo8&`SJDPsa0|MI<RyPk_3{T1cp-{%NgOnj;avbp~>gU2uJI*?_^e<Z%s?QqIB-JtxEwqcYm1>!KZNS9Z(%qD9w>5)Xu2v+N7Ql*DnnH%GZY+yoLLLm|GZ0N}AS`4EA5!q3Mjn^m)cu=+$rX?QU6*Ebb-;o>xtF#(DP@4^<n3o``-y6>`eY+=8kI4;LqdgpuC1q&~Nv06{#GbXSc6rge8?_+Ao?iEmM@yH@u6IV*lKXZUR4X3MI4u#mi1vjn%Yie;X8E1!Bh%GwSZW1Tr<8FvGK`9y4w~KU%ePZ1(20sc`b2^REPA%LGaKxnktEv=*I8ynkLU>fvFLh5eP<c|9YQf=to91U7-7gOd+$iKG2#%HC)b>s9Ikqqlgr3T{Q-J>B$H9}Q{y{F9HSPa#PZ^kx;%?feVPsp8T;6d{zaY-l%Uk3*?6iJ0Hr)O$(DceLgt<NvKK}yDt)+)yEZ=jouDxdbsnU%1YBocc9c^U%T-|BTikH_PR7Bp{_+?)ucEng#r~T<^_L3)R)s{y*7#8o-cz+NvaG}_(XpC33~*!HL~fxo0&E6sm)NJOU9p(0DtH5n8z10wyb?__(gwZBpmG;$2jvJo3=;C9J7YAu%a-vUS<Y(AE{YAY7lELLqvDxZ`JFQ8N%x5*56)F*D6%7Onbw^8=Pp~oB{1Ql@8%u-I$EESa$KSlht+$SC?sAFUl`oyo6(_@KFcy)hrsg4G-D*SUr2w{;)xh#s#5nb?IrE)vCu>Lc}eGFN(95;KL}|(+OZ`RtA9ld{o!qp2p24=v$NC?sa6YCi!SXIZc$+*VVg5nQ?r}4E@LY_UdBdUx@?wM5_;KlbX7=-&1<-Ql*lSip`7Vs`zSNMol^5`Nk@$2!GSJwrmE!@+lr-Ouzl4bkF&vzdF4Tt_T|-TnV^I>3&<``JV_}YC^Ee3s@2!^a&Nk1Q{uDQE0r~ZGi{AodDKJDx0DTJB#?7IX5_d<$`rEo5ox7`&no=8J2DQOm4Lqavh<e?wGSiZENmK!E(6qAkUB;2sW*x**~$*aRHn@Jcz$VuNK|V@YS#SlB0Hsj3s<aB@5jr$5R>LO0-Go5sVM6j>V6Ctpui|8kvt@sPr(i@>qkc(km=hmddSLtf!sH0GA}X*hkSOP45eB3!VpoIW=%Ww@yJ^t|2`DkXiN8IO!D3Cq(&ZT<*}|tNqbA1#wd~O6~b6nP?a#JqT~A=nS=5bmPYBU&ja_M>}NISwPm~=>G#F@kb4tbF+*PU;B(z9o*4%+__3f8b!;(0-+NyujMP!c;(1(SB>Etcs$hI)5DZ%l(Rvf6_qEJlj5m?^_XL>etR~I4jjV|iL{}ppIzZ4U9AH^vw;MXO{kO``Eh##~Z|iNtXI`Zv^Nn=J^FFiN|1ec;El(MS@`G<$jeQjI4|xvvWEuj$+E21I79H@E0}FHD2uhHOJO0#tF)jr@cqI@LUZGv1K=nl9BEy-$7|s4*9@jXZYRx{**Q*rKvdogGvCnax?-Ckf+JmyVjr1x+V_{TJwa+iYo4$6eqD0p%yT!*6S(3QS1>_yo)KBfp3cXMfRkh`Eg&F}#Iv3K0E&|aLB5G>x$lS&)!uWM98p%)#&N8tSTgc7a87s;;o)uO(RpxH}RCBo|R==A3PvF={Jg4o}IuaJ;?KU+WS-wbOTd&CJ>hVrja!@X1j1`T2CS!D;A?J7N%{8nP$)C;LhFJA~t%-yz0X$_E<&Rdc2qeawZ;voa_*Vu;U=XG(AY^rmWSWWbiV-Y3R%-iVrTDV*=t8o(|5sCD)@wj!hyICa2IjCbuD-Y&ud^}L|BUT1W_THb-kyK8+7VLmFEAeKv%N&l9pzcK<>^#=G~z3kvt;ib9SODx+UnH`?D7WC_%kz?Q%~NwICd6QO8j^jUy9$T=@d0{=#;i0;~gl-`UYsL?r>k}8EbB}%X@euuw7Tn==Uv-Ve=Y{b$Q&iS7N3|pPdJ(-Wm!|92KSLAw1<dfxkUMHhO9|BbCIfV=R4r!Zx%60+PyVSt}BmB7u3IWd4_T45UR@-QB(RaPso*>WAk`+!|6fZsSt?Uw>v;VD%mfutiuBt!zB_=RP+yzTAyhhe;-<(9f6#TD$T;q@t~P%3#;cH(c0vR$dFvTr2{VFDGTlLf9`+`+uX@mMM99yK?&-5;$HHcIIiI-6@0Vv{;G1aD{V36-T=bL9>&9Aip#T6m(=1AJbO0s{@H0tw&WVnod|urM2_a@A*_Tp>>e!2{$v$osd_uehZbtQLR2&2XkhIqnt^ihL!GtLvvOpfD^~it`g2O&4r#5tYepA4h`Z_8-}cYy3eKzKUyQ<Ia*iNex4o2L6#JbabKXk43K}q*_u>)YpRrWNdgKjOXm8okaVf!xa5k01lV<(W0%AVmhA2>-^w)CB29wOfvhY`f9dZ-kH2#)-uA+)F>6G(d#bB>s-V_ARbC`lkKf4hf3@f0&yu<jpfZ4J5+XctjxGruj(4QjP_lqEtF<^1Gq$HWKR!asXsDPPeQ9ZIER6wH>A$^yH!QCzH29XsTQwKglQ74E(~RDK{M1!5A4XamlLgFjah<`%b>%=KZ7r5SLwScploG9Z(%JZe)Y_pjXu6P@6sPhU5*NxdP8U|f?_ln&o59xSO5&J2{I>)3J^CR|imTj$MD_+OgZugulg4aAN;TLTFFK{ot9ojU*7CABbvyS{QB>*}#BBB1)Axrr+g#hnpDg+L%rT5c;()b_5>vB)gzj9se3~}wudEP=m<`SUCrxVV&T&k0xQZ~8-EFLVjcB5RuHdale2_P~K64{Q#})Z~dB^PnsJw7BUc!bzPZEyRzqGj~E89eu;Obkt|F;aZkR4ZA>@RA_S)TC7u|h^g@S}sg+p@W?fm5S4mHl3XKKYD{D`O!*_Q1BG5h+~fT!`2yl#UtCIET_PAodI6mG{(wbM+&2Yw|P83mSG|WXx4O{~J>Sz3*|&CaJ(f*P&YX%RkW@+n%;8{Z?**UOAP=CR(yHW)Z!kRK;aTTKyuXk(bMPM(IT5*|FXZ+&e9DfY?l0iXmDSC=;=l4hJ(vmK-f2Z#L?DVKjGW_JQREloO92BP@t9`+Zm`Cum;V9){sIQ%=OO6EoaoGrC&W;%jxMF*4dnUN`A2wmG=j4k-NAh5S}6rgcdmbM#x0S+M|61ETl<HCr%nKYID$({EX|rdU#<;d(|{Fp>vBLY&)Se^d1U>%9dcfdT3eMGt)045#b<g5an~9znQq4q~O_IEcXk>ljOSd0(kkH&({=*!vs48m<;=oW`CF@pE1r%L~fmcUi+oi&GI!B;7;#DSpls&&Y(xx;c#W$TVh0&k0j;`zdWq+mhMFi<S8IbB;7}|3ty4SSK~IdX#Lqoe5dv;pz3q>5<wWIW03qx>tYLsJxN|ei;wlVdt{Xy{{dvqi?tjA(`C2q!cEWr$=E|1d-dUP>{&4Zlu!pa!n{1<EcH$FgYSu4#zUo=`}EF#3;C?KZ5$q_6%ivkRdqGFnXhz8>w(@^Q9Dpm{you9>Co)Wr5d@;af(u_#cQRl<XY53?od|PE!xIQOiwp9MkeYveryy`p+`l+g}e!ndec?|E-)4_PzEv=8N@^U4}2~qYm(t(B<0*+OOC{w)Dn!jZZ_W@dc->k1Rc+RC^U|T6GdM?!ax6LeXXE5*pC^ySSmx$?s>(x;i3kM8U7i(@G*k&5m4+(*V_(gc$+jtg7^ZkH0W<cIDf%sIps)AXB(Zd6jtwLP{<wOxCqzft4#>twg;=w6x)+bVr%Wak4ACu8QsNS4q*5K5QgYdOq|tQFK*J!hX0S{Ouq0xZQ^KSU`GMkiLB6doH_PlwoS-)3~m1G?{dL8tie)Z5=Zp)O4N`Wm~F2XT=D?7CE_Gp;%iDL^{!)Lg3FYk}w=EfHI<yY}2@pN~U%<ITapud0t};yR+g?%Dr7s5NvPY-`6hIB2K@o_fUVDKB1MMPH<0sYNyE_8F6muD#@~*icSJEAK(vmx}${LE@xl6XJJd2vIe$Y%0oDV)&@kUg*oyxeYc3FdhYX!s4eln_)L#OUVVLRHGm;SLVYfH$QDZWQ6N2tI!q(IV0sea#mXeDc&o801KMi5a+LdiBfM4vUE1A}8uW|{J$EN9$4Dy<LD|$((bORxcS!X%-;V*gS`y)_mU|OA_(wb6Q4wk8m6<0$tBILLeIE%MT)`uclC5CVkyAii2>|ps-m!{&(A$3*M{bYNy;gRVVhD*_aa3d-b=n0@o-+i?_Ks!ES3Y3feo$7kWP6JjTjy*<vr_~msJ^PXaFpr%24CSMu(NBo1E)K~mU|d8H0A~UDV|1lg}RI3PRA@Gt;M(AQbBVA2=cySuOZ<WgSyXB`Nm75&NICMo8CxO!@-U$b7=Va)F!b!>bAGPD{+s{Q&OxjTyq(T0@oD!#$WNg>uChr%H<Xs=XQw8&NpifTYS3K#fcZj+b?4jxa0BPMWf1<zU3AgjvXyz+mY;sf`fwJ?6E;gJn;GDIy=o$LGZTyKOCT(idS+{x$Y=<86U)K+gpK5N;^bWF!y(yWjW*VwYAJJIQ8;cLZ}Y4CpCX1Ne5<`nOq;m@3hI&j>^o;1z*V>mjb8bW{1WUIe(O6sWp8V(!Bj0YLU1eBj_skphLtxt*JD)Q!TsOI``q^+fdo~xM8ZvRnn8^0*;v>Q;Uy>><|qitLrmgqAS<+^V+3ytSMyAPu^INxDB1ilDcUyeDzr3Y0L<M+mW|Xm4KEVAw{;ua*4%in6r!-TyIJ&sZcC&I-<@{S@=+BW+Z!3$`o%6l99fDpIM!In~xGGl@Mm^Sd}SpmQ!R>(2Bb<U`WP3>3k?N#At<zE4By3y#*l4TjdqYN!#sq7)~+*X<N-Zx9iQ7=T53bLso@a`=a|m$rJu?y~~LrQ>Ne3zBjbL?*}JbAg(>+4c3}B%6?Du)?u3zpONAPjz3vh=)#wtmygds;_NKUYXxO_x7O~Jf(YZ&pN8e6H*hvGW*vHVq&nf^PgCAS`#RO|ZgZpOk>E<oG6(0Zj<pBAPXF6Vbv7-75{UVDhh)LKp^MvC>%FMPnbmcJrCer~KFbtjWYIcRcgxea@f$aWy^b->@;q)(yehb28f%TO$>VniqN);_>9*GJK|;nz$zv(vYjpakMZf9#T0D2;8DVZzA=NB5<>_t7@D4|mtvQaMwTCT~b#&!0*(i%pPa%JaGtb{1Ffh~|Z=ZjzJzjQ-ZXNac>Tk+Cs?jKvdmgm1KIr9*1iNk#hG0~yak&nhQ$NeED=tGeTt{VI5f3@uq+(Zlz1rE$XtS()mA&NpC?R%UOflDd%eWG4`G`oTd)_OqrUID3)>82Y-_^v>YrbnsH)#w`^mrgx{5n2<{Pgou+K-sNd9oi1uh#v#wsDl58Ouqo`okF}rF}84@-9sV`x;RZS-GpAWVgQ~;IhYEhF7~$F8YXEk&X0CG7DyD!#aL89f1Kf;F--7_)CaiAE$Q&&(zM?ZpB8k3nih%0gp%jAvdf+z3Dz}MB~;$Dv!w4C3WATks3-er+}o!1>HsKVKwmP*h)P-;vTNktd|bilzDTuG?srlvgGNg`uroB`qB=3)bv9bwVN17D!q11N-C@fo`x51;SXotWwX{hiB>O33yh1`(qkFfc!T&%)nBe*9>{wuEyvf-lq?PW9I<m8R;sVNn+R77a7Q(><|I8(sO5S=`s04-Gd9G8`*|2%@Oqi8*P8);iQ2!nS@CC1D7@U2s5=i*G|E_=rn*qsU&#<rCfIKE7V2%1u$gO>3wHS}e|5h^e2b=vX{jQKtQl)_S(_?%_lU)5n8kn1G!Q==%xZW=7gE#7#?twY-&ki%W{K+hMDFdB<sCQKN)8u1{;c}C?|yD}$z|8Z^L9Me3w>MN9cEBM+56S{)l?aAog2$IH1cOu=W|v+Vtn8;%o^APc&n=u*guwiQkY`YQpQUra**mE{y@^K$JX?>7!qHt-gCofUcXz~M50~yE_H1cO3nuMnWnm2a6Cdr1hyM#Uv{HNIyc37uAR-M@#8^p+h+GZ=<#rLH)=OsrX%X@5YUG!e}HtrncgMS?Qcy@Rf&>Eiylp(FxtDLPc`jZD6jD2saR_xx4TI-vI;gX5iI#9oebl7?~Q9<O_h8S9{F^Tk0*R@IP&dmXkF&8L}irioL6%wat@sP+E+6LqAwiFW#QWtEQ0L1P*PdRYF<j+^BD7N-ra_p+t;i^Y}#xQKsP8wit{et3L|?@Gktkjttso{VSn0#+dsNEcac4LSZd+V;~X@*J3>>9jj1K1)h||DuQ$<m_lDPG?dH!^2AAm)c5`W}$QE%Fr0RO|S=7~2n$OG{k#kU4d_>%tn1#1Q$wAM<GaiWQHcejd%6LxszGasmSrmti_+ko$zP{1Cvyr&2x{<HO)4OhGduXbg4Dvb&xjU;yz8-O$+owHd<7d*BwR|av(iSsGZa$OkYRSyBldV_nmw{5=i})rIwS{cdu*Jca6$=QDTFZY^9dX-BvcnscB?tD5BQ7(eEG*n7wXfBEv!f_?`f`QF(lVbNzPaZ9LUvAdJ{^v!9>iL8SiE@5s1DQIk{4d+n%=H%&{?_>%_AM2IPI~&T%*}EUnIeZr;x+zDy^qEP@59HrlOhD#=dZSPqaE|U@;VO(2Zz4jg>@lo78iByt)guyX2{KScUvbAaG~;;*m|Jo92G>;yAFyG}V`+p#UR|w&=D%a(`dJwCYlJHk4sI+$~Kz7Dp*ETN-()MOn{ELDoxC4i2B?<G80~ROR%FaxE7%=3*gJIVK^SK;FRU77erzs{S2*8nAUT;JSHI%K=XrT2w2O$_SB5`wO!#HCOLOjSIH>Rd>Irdcc|eju_EPQ5qABL_GQ&B)UZ^yvz-`kzJE`uV^YB&~TDWHpujch@U7+en_>-+VNT)E79O+g>qduVtVC@Q&0bDG#bZ~Fj9e3<h^8nNraj5Oy!UlUZ&`j_5s?&=4#AQ-EmwZ+l7FpUx+~^J1LntOI1-DI$e6mhP5+k@FGw+y$GC1T9$}|BzfeS^CJgC(|u1UEoQX;DDOVp4y;tsG|xL-s>3CUd3c+M6W6me)FfmGg43*-A&<Px;H1lmnGUR!3Z9>^YlT6X);9bm_SM-E+n>5A+YpC@+HxepT(KOx*UjJjh20OLI!R<Bo<0T(#uF_?YRSXuUvQUX+Q4;xpKp<rt!F&pGk_zEz$zJ-&AU4Xk9Zn5e$Auil!}sOjp(yeGD@PvOWGf`^WtQOl)IDnXtFd5`{8|hCFUuWl3QRI=C(@+wjGK0`j0zGGkLjk{+8MtfYSKkzOpO9yDtCgBshLhHJHt?zi=$n>b2`*#4?L&ggX#bK}i*xA`zo@TTFRj5IL8TMjAv97vyQyKWjOcQm=A#-BWZBs&lmOSlY?IwSH`dD`j2tR~9!n|1vp1CUg^~j*7JyMyI;hpon&wXkQ3mNQZpUTw)A~aCy#e&6Hk$*5Cg4*Z=vazkU6n|MB79{_^KP{l5=?XO&Xx=YRd`|NP%S{_|h|_~);GNq_wCzyI>@|N6Io{mY-fJ)8TQR{8kh-~aTduYdPHmY@FhU%e^OzJ3Kh+}Hp2=TE=+?&nY6zI=N>f2aQQ^+){6pZ+=f3BUOC`P=`#{OVWV{ujLcumA6_K7IP>CHqz1p7-1D{PoMr@0h>+5>0yj7+>Gy1wsrf0@p<F@elsnf8Do5z<>L18%<<<IDa)Xj`7>I9>E6w_c7S0el~g%v9T96_Ec=<F=*^J9Oj9phDHm}g!hZaHqiL@g2n(e?lQUFJsJzpC;=MxUeVYl8v8!b7zB-eqS?^c;b`31(AZ%U%04z4^9_wH(C8-`h(-(0nD>ju3_xQZAC11!s5ucDGkDbK$KRnAG!~$-?;VZ3pmFPp^F*_vaR7}IpwaIa&4|GH3DBqljd`MhXzXw_>b}vOKjVZWxGjNW=Z8lLxRrqINVz?k<f*pDA17`A6PqO3o=mp=cFC34ch4k0+S?}+a1&f2mgdRi+p+A8jJc3`GWp8nEu^BqG12dyi7A*o$4SZLxyI&9p8F2Q<auVZPbO$M_Q?bb8*NOU_nkXpqOZ*)$}WN9p}0F7C|U|dum3#*6gv`%8V039c3{Uri6|7K&F!e@`%9}=hRQ9enERs=pH#ZW%HSl%<BSY7-7bysI3q(yWmh8Ov{Y=C5q@+kW(XCS%<$4c+rv<CVMm7N@u9fAP%KF9EOjtXC{HNu#MjpXk0+ETlv=2IO9$E~lmSrGyMUsfP|PZFTq5{SD3`Rx8x%E6cJa_qYysuO`Sc)6Y(OaX2_=W3pHMI;?g`}yr5dY#4^Xs!*HFx9ptx~R0t&^7v!&-6D!xhO`~@p>C1b2^m+R4wGBTu8(*HiGl+JKt)CKpr3rne()tsqA@ON4&8u)vOCB&zsVl(p#^Q3}OF;6O>sK@pNmrhJ&v#QchDoJsIxlqwhDi<ocpNe`9RMeA7HiH&T<de#_2bl|@Cl#3XF_*8OR8nu4b5og27Zi6ADAN<la40ZD>z+{V4vM~Z98Smi@u=8qN3va*-t`3XPbytw<-KNp!aaMH>4T<A7ZiJG(s5P;w=O7#+0^C!q1X{n(vp@Z6p$L+>U`ckl+CpIJSJ{~pqQl2=Luzvv*{<46pBt#gzp}Tc{fmW4-_>JN_axKw^mRCq39=+`tGCNyUmb&LaD{?7bxxt<(g2;S)iyVl(hAV0fE^k6i|cwgt9`}j1U(n&tv`tiULr~6N*ksd(P24p$X+qvpfSUzf7e_P;CWqp(D@pvG~3Sl)b;PqH(E#3{&pz2HUfAq&?h8F<G<$*vB=hdjd>x0H(Z|4UGSHWC6~K3HG-sTcDaJCcNbhZ1vJn8*)}mxtUQa>ef$8cw?NUB0#VIePSvwDS)Y~aN>-Z3<HyTVlvH1C&r}T9VYX{1VbR(zGlEUI!~d_PE0mAA88PtH>axH*^Oztn!w|wS<Cj%Q6jh-lS6b|+t=<S^`(O_<yT*uU@~XLq(zuq=A{BdDCem6*KQXk%!p_EuU+j$4#A|aj>-F>oJLrU_<I~q&V+%W+!;VsjKRio5(awx!wjfdJvpU$DAnRLI2ZRg41zi`73c3yvRXMBb#dCNu+oInnDKNlCqIId%L=oWypzAQ!?2If$&KM;lUl7b<z%0nD&<=nC*5<{J~<~1IO!)R^p0z@B=5pW^$71z&PgRQV)NuwiJ6p~?4^h4X*p@D`$*X={=JYo?FzLA6ihpHg3?+_N*@(qa>{fZHWyOrZb*$BQ@HBXn5a9>2k!)xNfvZ5DN~Tz<U8_coS2lyNtvsY(rR)Ys1_-h0_NJf%Z_~%s*x*Ir31)3o38V@1vAf{3>6+gsFO0pq7F&9+mcd`Na~G_2X{Vy22%4*P#y&D;DtC`+F-wZeOgejE4met3V_r?$9((x>*^j4Bc<++R2)kxo*0yUf|7$WV3q0u6&@0lYVLd2h2XBg`QtTD!HV|&!Fjt$%E=tX$?A?X(i^7$@^;}goaTL)%EH3<4U@TG>Pl~(5t9WH!tDTHz|t*_4ZH_T6G*khz9jG+Vw%QaG60j^iz&VvOnMKda8gWLx4#Y3+uEdiBD`nBWI#gv4U^f6$-g5^wjYx_Ehbf9GT$(%Q)AMmkJHy7G=qY=g_9lN_|d^h-5VzhvM41dKZKKiXifpN6*Pd;TT$k8;pCp2K>71q8f6B>t0OtNLpg;ZoHW8o4d!G|%xNCT$sEebUxCxMK8@t0Pr%8na>B1{Hjj(5bE=lo;oF_9VCr0+%pgny`)z5wn#CH+1_fJFZ=m!Als*#F!0{A^a(bI<TPCxUlfFMrg9p?gQ0fr})Zm<)y2I5+<DDV5RXPsI$&G4jHXSRp)D=x!2Q3RSb6DN#<I^(xVEMxSGXhvPvut?hutL%tZp+faO2jQr{^+pONLaQ4OAl)ib~;!VXfU6!5LlasQv}{SdNtG^)l%$aumXUkp0FUSh`=%#EZbM2cs^JYfTf?Xc(Aq{-jca8SAiAJ0?S-rX%v>Zdeggyhh+!D@@IpkGFa{j3+{#i7>N2yK-d5!`4bj6X9ZAu_l5@I3v0CRox}18EC*n1`pz)$P<momE`enqzOm<(VQqivp0NC7>=+W385aDz%a*Y!vg67&W8+uZ)JDsmgjPk+F*`Obld<t@HhKHbS!m5WY1s=cN78cV9$O$Ec8i>#lOGDEfvJd!^NNc{7V3rjYgJqU73QwwDgO0ly!q&~D&7xnT4_y;P0j;j_E69=Njmk(3~qH6IV8BOXP`d=GrNzOEttU^jxQ3b;mIs9VaZGRHW!jDRT!VlR%Qle77%9c$t+=JKv|Z}JY4KW?f+y3nQ0a?`|g>Ugc+>Yas@Nf!_1$NnF7vuB{Q2bo6o?^jAI7tlOQt%a{f<df4Eebw3wNs3gx{sQ^nkzE6nth8N$o}W;XGxGHcD#b8aqk(*rNmIVq>Nz${!{3JaclfC9;kl9>aI#-GgK`E1FSskJNxGIQ^PnRWx2`Li*z*I@=7p29m}W{qM~GX%AG`S1InX4uqhB2>+(g~Vy4i`uAry1l{t1UZxzH5k>-srmb%c8i@r>6_Y#c2JnF(OT1Gh4>qVd0_D({QkqUi#WS^L#LIH9W)trAb06OerYNBXhr{BR%Ja8LU;|oNQbxQ{yIrTxnJl$3cGhhle^eaR(ma$>W*02Y@9)hQVSaCL5sHt^2ywp{QxW{d}asNN7GbjTA=2KG)*#Y&qLD;qd8^0z%iN=_|A61dD4Wth+8u+AG4O37TiAcdj4DL0TyAYjOO$(G~=YXIBkJ*PH?)cKEMH6ClCBVq8Mj<6r9G}nUB+fGtTDFXRA2P8trolPJL~h=7DjV<cMh#*?fv~vp_oS=u}RMbK9q(3$RO0>Ckt&#Hk)1XGC#2wFhSeIN_9sI3vKRI&p?a!D-!Go$Qu~<G|t%*x1=+4b{^aqq<E06XP@joF>ERi_vKlSD5?=+KbcQ@%3^C&ho|xaeC0!&;aNDyfl1z;@ogfiJ;qnE2almBZKrI{fg6H1V%EP?#wtHxPcom%{QDHs2MC!fT&9ZPm0q%3Qjjg--9zG(|N;bfSgTNaq6?;3_7rJngplLc5@4&p0M@sGTHsN@0<qb<{&tbrvo)HF5&3_&$l5QcJR~>!_!+k$#}-%sBRiOZNXC-1X1_L(>j!AG*LJ{LsoRW)n?&5UBWYTMLgBRj87TQtpIm9dwK>>m+=(G<EO{OsYsemn&TNoL0`X(y^nsbq`vKqQr`~%&*8W0FuSl#Nh_uovLv?!)6*r9Ob@2BC+g-W5!G2vbtF`r>Evu5({1sBfgyXL9DocP3J_dE{1B#B5BW-%+Jx!b))CjkU<6Fx{%aD+u?Ktu;T&9L8t;!OKKK1J4P$Bm)3}C+7U{dsxEm=`e}7D^tqoK^5~@j{S^zbyU%&mSsho7GP~D>pR5{a-FrBixS#zPhF`W~pX8k)_%G92dsm~JTb*2*tqL)mkOEgZzR6h(;qr-ltTMa43)T}p~>B61I)N-O;$NI`tPgA>~&THGLcuD8hpvDtIjl-B)l<9OyLdKPvN}5^5RhytMOm%~)eg{k)VCn%=oiKe{4(4vA;qjRo@A{eA22%@~_2o=eg{gZWrbgEWYP=p)2U^xas51f8h@i$pp?aKYj8@9jkW6Q=pt`jg8O9XPUTP83a3A)AyP0Z`TAx;?5ir%s#_zy_s+vsI!!z|ksXa{Ny77mEDZHJ!_2def>Ju=vu{Kb>EZ&zw4ePPr1E}f()eun4X$Pu|sV$iLm8naZhV|N7V`_&m^$*T8RmQ>e+ot+RnQD@$K95IkwxB{~w`Hgkp*(I$5mQVfU^<<QsjUvw$cL&|-ApQ2+P+^x4GC2J4hCuuQ&XsxHd$E7)B~n5VQSt3)4d7!D?#`wr5!e1D;LUOU9Et6Tn2trci4j&npn|tD9dMPE3AB$hxed3-QTEbY=vPMr~|=gV+_viLAa%SV@0{O)nFWgP~AO3TOf2<&(y6I+QTEPq$?uSVD=%j7lbx*Mo1Crheznvb~!p3h0*LrXcB~*sks8ZJkEe{8-+U%nxd<~Cff)kLi<EmLudfPtv#PXy8NosBGi62LY*Mo%A&?2JT|XjrphR^Y7|0^BDAMLxaos;BeVs=0Ak({p<g57V-SW%M`#O#0YPXBgnAf4e~$=*o-7}s2I5}_Chs<pRpKhVAv7mI=&Pe}076&n$a>wWm#_6%N1+^HL=ak_PPJhDdm<z%zEgxyiC!W!H|a`z+*)Xim2D@`JuCpn{t5J`f(W-r^~0})rZx&AAE5>I;IJ);&c46w!qC{ko_HchS(sre?#LKI1Ilsiz4bNLyUlk~hEtqnq5oKPFVrB-3G+-Y>1udT`oxT6xVj3=Y5K%_8N*Ov7z&H9yI@F<!ypS8;tXf+I#W<NLtprU-37xia2#$8Ty;!4Z!0rjgQ9zkk=SVwl0$^17WbMI9yyw(`e-ueP7B{)PR=vDZRpPWY*-Z&vg1jfFMfEGx`uM{u@5CI2KHH5HaslDym2@MN>>||#&J>Bi(CV^1IHDdP1Kpoap&<5(3Md+`4C2-Gyr8tx^ymquXqNOZmN#TX%ET?<c+ryV3TNuEeL?w^Nvb6O042Kg6iODO#x_NxxH1iKT)FftG0qtT~KO(axphP?^-!~yBDRtpj4n{EhHU4PleJ}*GibtlcU^9sZx{?w45@)?OC6Bg3D1_6y=oEpv9!e>JufihFTRU-=@4;8=)-?l;=~URFaD$g)$bEekVm~tG69%_Mn{B37!^B22k|tKr-PBqf(DUX#mQ&jzOQG^uUn9fzqinpj6{fmZiKgtB}+{6E=ZDs&HzQTH8G+1GsTRlv{Vscs7)_KEa(V$OciG#FY=C+<GsC1f@Ck1Q(#RV6C(unC3H-OP6A`hCepJ-V^1jmWZI;icSiFG(fpob@`+(lRZJ`w}#SqK{#WRIk}?ik^yz3OZm7eI;WmsRGMn4P=VIP4VEwfX%hv!%W87X<wUNs492NvxR9mJjyEc)a<<uOc}FbuO;~EH?>>c%Dsy}%3120l;=$hH*W#xK@~bUyde%mEgz<@3BzF-{TWh<_QT(p5*S7OqT_qXa9+J6txJk-Q-MvUE)D1{R{zg$FX%LbIXl7mFMD*w+s{$XZ!XA<lklfDMu>G@1ntO$ZC+Ubm>G>#4fpP*F{v4$#x^0^ipqz%2bRb8#nb#{2?=hg}#jg&{Pm);asYU!i{Tg{Npa9FSw#=tpC<l^+1-)B$Vtol$s7tEh;WuwnACznnpRc0Kt<)E1aD76Q@unmvKvG@y?QtaCNl5ynA93#Rtq_uWFiCTlBvqVtkTeKM=tQYjlID&{%IaZkErw$>UsvkE;T%J$n<&*iq3kRznyMuESMM50U64$tw*sk!$0xZ>Z<~>{LXsirmOBF>?nW|#bI^E_>Q2UFN>bY>CTTO07Ig1XiEF1VNX`#W(h!3(NY6nK<+LWZmfHT9xlQPkp`5BD9b3H@5R!3qM-HH+R7fmNRFXJ64as>2$lU0}79ec`G62&ja}i0N6r^@R2oid7EPXf43eR3Vj11@_wM8rS2{s(#D<o%SWOEy)s$J42c5?|`NKPxs#meLHNp7`sDM@Qh;FGjjqS__7Lkp@qO=4oci7etBlI+dS<|O@XE3GkmJJXYAT|rpc<W!aYBA7?WQXh?P3o54goZ?q#)j4@^@vCtims{;&X|B)(YZOVBS#U2Gzr0%AC)SKdk<?dcAwG&Eq!fYlI4@RTvZ@Eq?}6P3D!W8baU{v59(b!&hZ*Z|7|9!KxX$cHX%m!rtvbwDkI~p+D0RGDhnpHn7y9d~Q<AnIsR2ndtW+H(8O}j+0?LV)-I7B>(wvs0nP%5V5+-7Dk_wQFiTULjNQTOwbTRBjX)blFTPsxs>S7?u>3S&r4wSA_jGUqL+DlPd66KWncEkL^6;Zk!2caWSdKBf`1fLU>E^D+pvW_(zi*l}<DSb41NNy%6HImcWNY*aj-bwtAp!=4|O01W9^i7zOc2pi$r#>8|8ZjvQN$RZb|8^wZ!;?(=HkBkTNm30XY44Jxi^@q!x{Rc~kThVSG@#ypG)dDzQeC4#V2U!#&}z94rMaNg;7n=2@mvARnX93+H$zz=853htK1l;A)%As>0tQkBl>6(!yEjVG&?M~@`k(rtBwayr>wn;r%l9}tkAq3N3Q0SAsRad1(t$&gS~G-ZRjTYKsgEVOl~t!GCuf9i9+5<;K~*qBX$PWI9Vn-9C~JxyIm!u?_G2h52)${5(w+sS<)FMpvbu-E*JDnH{$Zkh!HrHym`Od3FZkgYT@B+j+y3fHI%{o_to2c2GIj|7CW%+xPL=^w28X03IPZb%2KM0YVd-zca-Jr$hb7*I+ZWA{x2WWmSn6xsQznU9o}Oa#ds$k*Qde5~y0v}G!?Uaz-oB1Yy`#iBfZYF-urw&kcr_isJ&enKmRqiCsTZ`Bu8hz;&pufuENzozEE*=i2bR-hbw5jg33~^SEW}wZ{+K6VSu?#g)+i-2dc#;o5Cq>?Dum_L60bMZO{pO)HJhcrBFoUhQs0E7ouw>IcBj!*mij6zu{76w``k=M(l{OaNiI7NOud#QH6VGdgyD2MiD`9ETBG)$v;|5JoY%K(m%B2`c=(`{kTeyNrb=?_6YSpsNk7X-F2PuMNu1XU&oaGnlGoD%gyR>=V6>E^CP`Y*3}D-A{Mv)&(Mg(E9hAZKqg<*pAxe{3AvusYJOj#YQ2K!+CxoO1b?Z7yc1=%`z=k=1TFeQ!_{0lIm9?q&mzdBv;q!fxG||nnJ7WN?z9GqwkhCB@yKPkA3=5^H56URBtPh|ZI0BR&$V!(m`lg)>18Z$MQ2K#4MqNSaqMxNvbX!ExXSBsNjC^eWJp^UwLTP9NAA;m9lGr_yljPuQ9CX7DAtw=Zc$_5m;TTm7<HUD5p-Zo!Q&g?J^>JfT4TK3IV~NDXc-0HjWm)W)R9^?Q!S!J<{Xmv;1*Mzkxxbb0lEf~{uLJPif(F-TMj5pkgK`2nSbK5bF`(Sg9l86CM5#l4hTHutw_>=Ir3SgK>mCaI5yMjNMrjF@`cj-3fm|7)G-pQ1@2Fsbn#Uy`aIhK<qFk~tOMK@PD8U|{vb51o*I+qSSY9h=>u$%==?cr}gWu0`&fJ8TR`v?mkS;OE>#(%fU@04xaduZgsUHfZ%xp@V0VrM4TgGI`ggG&+nAXSy%)p)+Wtg<?L#e?De5-g}P|g6QSy9FlptP}qathA$qnwfn?!W}!8WILz(0rdL)tI$%iq7pp>DKDuB{4ItHN+OUy{fhT^$?Wy3h9J+C6KWI>5^K`lY@-2yb9YEASaNPi7QB-RLvc_PF|(9Fd=D`GOj1YW-m$9EtmntrX|Ud1+T}F+-z`Dl6nqvPicd_SmJIb!XD^+7Ls|c>pn@ko0GIjk%(QdgRl@x0r!uEqyc02Ad=w*B#rk{$@3OKpD!e#WY=c18<xAyCm>l{CtXtG$&pl~BsEDAN-*rDxcCr~^T2g7j3B9nBrPE6PC~LWB>e=M&m5JzZWRvuuEOC!=Ug)mVb+hGxxOL9+N=y3HYzg$h#`X&D#h0!fqN{_zOD$CG!D-O<!pBF3?Sd1rl@_Ex^}}`GtbBJtSolHKzWK0Bno5ZkPCU*gePouZ7zT35T0`vPD2`@WSg*u87>LVDZ>eChoOf!>^n2EN%OHd-BcT%&{synb1ryVz|&=UY}oW#pMd9$aH<5S0yxd!e$DrZbArwF3|kst6PzY%e7$%CY&qEb$7x64^dTzg-VSlv0;dCA?aP$5x<n`+9j6V|;W>@sX@Ko8<f%`{Gu{fPUvX*#ryhoLItxxi;tT~&m56~x;SBeP(@!q+;53)K*JhOsajImpL!5RPPJis;sd1h$kqj7iPH`#U+|pvO>%9Vd`wX1h{p#+1e>`=cmF`%a4&byIPKV%hPn@|6Yz^mj&rEUZ4Ck1xrS?`h18Gm3?L}b@Qk<H^=>Sd*thAw+;95BK4xdCBPFso6#Tn+uBs?b|--ok(E8%vlS@tGfI}6Wsc-kE2GzRAcib)h`q?RfH%`lwiK5(i8=cM^3PYZDBOV28(yVzoz3LM)b=rwT9IMoQ8Q7bFOx%D81?&Pq`yI$oOInHq>rDJh!C(mqn3Q`=<I7EZWW7vVf0<Zj-%ytD%p7SH|wEW@eRMH^TuodZVv)vaq<t_=v!}=WsPM!zh)avRyt@7rk>G2K>hU{Scbr48yh?{;lBqYqN=Eq5pAB_=I$Y&UX3VkVE9G4~WZvW~!VM@KDfq;;xt`W7$>M=?3vb%O#;+RSg4k1d4)U?dbV$=KWAZjZ;%3+!ucG)&ba5Hs3ete>~HtS=wBZ<Op+Y3<*ytc>HDIZOAt`K!L__0!sND>{_FnTo6AQM#Dfk15m)D*q9Juo5Ag&n*(F;E{v&r#f7fZ7b`QicbCD&Pr!zd-#Mpk@l@)<CBd0QIIeLMP}MEde@ZKw&>_4Klqc&~etX7*KV)LJ50Cpf&+It=S(9+)-icf+tWkkv3(Gd?(N-6{gcLpz6Fpt&6@NXlwvAS>Jej8lbMehC0&&)B=+nm^ojnaZ8|jFwp7P5vm6Rbs+r%bLS~go3)`e1A)e4fvTGUoxzkZdmEe{s0~_4f!fTyAl>EX^-8ZU!H^v2d;*}L2U!Z#C+*NB5xg8|M1cCtWn(1JFc_#BGeW~G+2vss`3%zLQ2I8nVZ7@C_4fi)=RgHnN()kHGYE+2Bm=obL{*X{RzM7Lt)f$PyYgLy_L_g4@lFtI%DW~n8Q{DzwY%IredgG2E=teG=eddBQ=XFx>@BJ6LJj?1Jm_EKKs{DSIv1I%7V6({!ka2j%jc;Jo-X5QE<7D*e*$}I*&}(nD|Adx_oHc!`tTz2R+F~a6%*EI`#|R^ASNi!c*H96n^IIb#W@5uGKcP}J-*@J^v4{)`?_l2KsR5KQ9x@c^t{nGY+!8%4$-55PS*j77n;Lv-)UxjT;cxFKx1X$j8iAjNCGvWHLwMy-;2`q;eonX9ieVa{v7(xFE!;QP;(i%ryZeVfSSyNegSG%<z))gK7p2kgoy;IGN1<d{GS`B^<fXtJl(4SP=x?p5^E0+)Z(XkZ?the>E043Ec0^!==A77B?I)8X9#1`=g{SU;pqU+>3E*%K6#pgr!IKvtMl~t$x~U^&od&q-ngy+3(u|e>O4FxevkLAWBoK)ngZi#QJ!WMCL9tOQP*fA+|Sb?Jj=54xW+$Hp7R>teDW;o&S75CB!$wDrw4WCkf**<`O8&!2D<nqTR($QJ(ayRo+hyjza~$8E1n+BGOy=PlkoIf#U7rv!qZ-OZr*Wov3{z@;)xe$)p^c)jS*6w0raNvVEx?A^XKBJQl84};2D!je#q0TA?CPx7;fkMgT#in;Ay35*a(~vLeh+4;~9a~{h~GW;GF+ZJQW?KPkBbm&+<Y(>As`0^hUhwSvXI96i+u$$YsXzv<c6=_#E<F)Y^W%H|e9~@3F7SO*TLSFq^nV-n@eY?JKUUr7A|#T?;c3iNNLF6X%Cx+!~tYGZfaLTDCBd(^xzW83#}??XFrey$`IFfi>YeU>(|I94na)nMmO{u<jASS`;i+=es3-!@!=|$AhgLCZn1Bez181asy1AOR({x1+k|du|7<rz;1a<oq$!Kz<O&t5Uy6Nx(}=wG-78r^T8T$EYEY96R1$f%2g+jBEDy^Y7E#(+i48g8Gwb3&n^LL)?4SDf}QV!tI4{STfkK{xau=-wb$orKw(SBY)lR49z6|g!9AUbt1Y-j(DW~4wXE-x>#X4A)iSDGFs@-;2i#=^*tjn0r3kp{Be~99SSxy_8dg0CutLjC2Z~(78m`B%ZbKSkjdxi*SRbuUfHk-Y%EaVYw-Gvn7y*VgfOzycto~M5m4s?^-tM8g4bTY)n02uRENkv&)j6igZwFQ1)we)K)mtN@8WE}?^HtMHHwX=uhRrehFsk+jW7Rk>qdFl}Bgi=gV7IjO*hs0`Vg6NvsM_|zN>?qVR43!uV>Qis`mA%F2WpbVbIGk#EuiWLUSHj<sN!cUJTVZpHS->-n=u2VssUAfp&9_yabc{{RMilwCfc}%szIs3fXiYX5VA^ce-zb$UeZ;n&V+udp+a>zo(4cQ0>6QANdkLl7T@8!Rdg|UK2-yn-sTFklq$TtDlmr4V5;U=ZG_%W)h00(oT|BKAH%w5EmWuVMlh19K9uTaTT4*AMMA#=gT{Q&zuwGSHQbFXN$OD(T`=ZxGWy4JG&PPU&e!d^o~HE2*`Mo<l~3!DP-`Z1JE78z*UNPNrl>dwsu~Ja4TnnAa68~K05i^R;355Zs1+OZXeTq6>83By2va-E2K^2O>RcVDlO5C7K83n9cMBk1@7BEC0I2$22kIE6+v!~cri*E!0!;OjDbbOALM{9CMZ%La)qv^rWJ)r%MH>Xj)B;WT1RSTIO!2zz88seQG<=3+s-H|7OfAWDO77=RrmcG9vR;0PZc<F=!<0G?fHW3JHHp*=L>kYD6swwtNF6{rA8$W>e@I*X+6_p`nN_YA0aAOc0ricLS|9iJY&Q+0dUaBE$68QNBZ<Ze(IBp_t5+vOqFc2$B<cqebz_KzCeTU3Ginn?wQbLNnhQ@;@I1)fVd}DFjbx|XVLW5ew>{@+6Vv&54NJ{KZcgXo`4*~68@Iz&JqARaVJGdyH|w-KmF?siK<9P?#^I)7c1SC2dr?3h!qfNJ-x)gb?jX=fYksfs)E*~*juR$nbHB)KT;d?SiJs=8vZ8LBJ<is5H|6O&CcMp9EzKurp7D5|ahzSomT*dW1~uEePqveC&M2FxTh(_qux78$ooXLS(cl#4<ovA%QA|DN?ckp6$Esk=aFTg;9d^{PiDbbHb{^1oqSERoN%s}EAf*mn<^AP+W5+2JjwM;yEGDb`7?P$z(u|WO+=(8u7?V>U$w-hi2uVFmjG*pvO!kn(Te6!=&fI4i$&{oyF-a>RNjY^J5HB-85gdk-wD-AAPVwp_)!@wdu_SGEOuEoR(vl=Kh?Ad<q`@nzhLE%uH#rNOD<Y^*RfClUk57{Bw+=~~f}}k^Nv%6c=810&{Ee4dAGKy{Myd!7CTT~H$voe^kPIkEb8LoYWcA5(9g?m>a;uRF2}$$#B;#0;rPICwYE}nG`h=uCEy-!-pC@b0)D1#%tATdINgf=*@F>YyD{cCsY8y#?A?XW}&}Bwl*42lv(u)<6^Q8GC@%HKJLNcs3?v$ii_wM*4S?QY&NougylqB6{_c@59y#-0={jP-_(`V2zeW`EuC`o_WeI7rmRyhUDMnT&sE$o#(gB@q7HNi=Swg30Slf<i;zlJ9*pQO&Z%g;bjVL-q6l%!oxm8T$C*}I(rrIEKtRja|4Zgq`g5P0Xlu5nPKbMKkzqam8gV48yA+c;9NLXoJp#rOT%9{uBSV^eiuo#~qJjB4<mRPmDVG-+*tElDV(07FD%`dF-LKUT}=ln(vfEwFHgy_oF4di#U1R(58mt?HwSclWl1xjXFcy>w(6S8#tjs<`5@a&+`F-`c%}6&BrX2cZ(HS(~X3z^V?#I^Tw>VNo4tH>l@(q#CS?QmXCt=^9XlF8WuXIt`|3M^JT9(u1JgLmi`P09Bnds~<o$97?s~;r2RM<%g?wCv{cDs?LRV8cWr(sOqf$cUb!Yk8;P={w!1tK~({&`W95(JyLb^H1|`DK*NDiRcn==22|BZs`^l>m4<I~h)ytA>0)sQtQ%>p_5raf$r7-Ws;f}-fT{+ic?!54JgHLc)@{*ly+zdwqdFf7wXy*Cpq&(|ZbH>JgBlNoYISv}#vZCz=XDEeoqeK1%BkvMRQ){;)n2G|gM$f#0&}P#fvTQR|F8!AH%Kvos#mBMKwWy;Ppi69UA})>sIQCaENk%?fVD<Qph80^4@4oG)x_DLRu|P-iQA7sLx`LzOe!x_w;;gc$TN=WX!)!eF;riv3Jz7eaD~_+D0AYkxj_w}N!9{&+@jiZR5jzM*3wpUbkl8X%k?0$?5%sK6V^q0+*spvh{4jyyDu+49;B{;jGC?S@@y-2n7DV~?;nTLj-+YSFq)3x;SO7}+pJalscFtZ_tB)x+hGFKf+U?iY|T_7X#$6Fm(tY1jG;M!%3ceSNsy*F2Tia6B{a2C%DX<C6PiJWh0+@M6m2cn&oDUGFr2n~aM}t^7>kEEEx<Xw3!Fw<8O~*6DHBGfD5`{Iz)RoybK%ta=rn#T&QRdgNmum~-~{c1a-3%F#5or@HLw%DCeHbO2B#WN(}L?ZMpGp%)SomLng(2XN<;RXrUEqeK$_D@X~L59>1H(J-O|)a=Oro4si3J7np=6G8c1`rN@<cwz^}$~OHxL_QUR9c!g3zQ(x0AX0JHpU6qYR2saY!RX6Z%9qiNnHg&Q-L8uSGi!_pnf(%TwK<AOLG=htI<%2I=r`Nk49lzlLkxKHp}BsZrhz4o>bWdy?G4dv3=cmf?3wnL`6OK%x3OXI94v%9%B#`U2Lpv9L4h8;1pGh0y3XF=&JC~a`62c^59G@!e-29e;nUWp(|eV0BxGL)`5Dg}0hrI~O@%K0@&QNWgo3IyODA7#ZhL91Y+--A*YuA>3`*REUmHsudNInbWI(h>d@WzhPjId3!AR=!?ejW&+)ss_Trg0*{3cppsBg$hL%6*$HCL5<66+3u1w&G>6LKoa1MgA=zx%GOsY2h~p*D_ajl7ThQG)tg(FKaR2*N!eYAGF8Q1X2*R}Z|&AlXU!<!(J0#rWgC1LN!c_gYfyge)`L~eH{k2$_&}6>eO(TYOWCq0#|q^MP~JQR0_l)HpJOQZLyl-W^cv))caka~Q|9^c{X)k5^CwXIVlK5W5b~Tso-U9TQDJ-%$abDXA7s2De(B^}YHwzc{j_VDEDbq46l6D7AbY1~K4jkwSyv!O(nJ1W$ZF6??uA_1$j<<>E*u^pWPNE92qELq7=IGT9*V`ipnLU%_E@h$RtaPSAX8Oz_OT$>A~kM~u@7?Db=_r<RbshJLsln%>`W~RWTNkfjFr}xkhesuEg(-MWPPuYooFNnYXm_ey3*bjkbM*KJhGH291K|vgB%LTW#O#?kTrk|my2mUWOpoNGu1b~D20rdj86&V+~Z(5UFf6`e=uZwEM!-Uc18ut@<fnxkwL6N-m0A!$acj$53JGG=2*zOw((8TbVAM>y$9eOlR}23&=B%g#UCFGa^Snn?Li!}s{H`MKq~R>u%Mc^hIokfUEL+(SHfM0UC|ES1C$C05mAW4UFzXwgl!G+99-AAB5i1Hz}GSBUjXag+-1cs5!*YIb;}S}4i&Ep1*{|VyIRJ>ywg_WuYpEq(L3aX{bLbEuX(yk*x$I&zk|cn)&AVz_gz&Z5%nXL`5%nYh8jjQJDGP3hRbKkb_WvmAt~~AqZ^@jfb|2xR@z^^g0)`l0Sj}OHd8v-A~&D@grmUfM*s^`YNoL0&;7aGnq(hl18_80TLY^ljXJnsbp@<n^XhNo`2=8N4Qvu?*#}mmV5dSTvS`7FfE^u<m4a16z#6a_mDzR025W{XYljD}hJg*RHgi8%Q-GZ-VD%}$>gsXJ1+@pPS+nRd0SkT6w(GwK0a|^Z0jhf$u{E$3fOSB@bT+WMdfZBqw>+@60#+Abbpdws@KpC{E-eIGiAKHtU-0~fC|s`U!c_s4*p;}dW4TtxtH8F~f|#@|xCT%{2Q%Q)B@(q|59c+#_4r)1s}0yGhCN_Qk!=n(0<iY}!CDzubtSHwnUG7kdcZZTibb0&1on}9=C6%4R<POxYgn-cfYkt-WHlsAFgpG`kHM;(6=Iz#SWSUdU$91iRRgzbe}@h(b*xcR7^RJ!t;`sC0%c~9s|ML^$kl_g`jl&UD6U>IT#cXD;cbs#wTbV*5+PWyzGa&xQ1GCEWBp@cbt0@$u~&hBU^T#lK&^r9WpUN(5zHc3;~iq124PL~LM^N&!x|8*9$?*?(^&AGMf4IM$<PVMT0Od&2uj79Tw(L$ysbyc)dH>#d}r~ke<-e2$yNbAR-fboA=asa)dH*@2m?-!)lTZRIsP!XalEb`;cX-Kq;nJ@JW!JVaE`jl(Q6QPHiOI!JSey?O%D!Z>P9kExarj^(JAy3t=akeH64oC{2w;k)m4bbQA8<A|Bw*1nN5Tn5&^keq829fB}6B})<5m7Z9#AIr9k=diLM(`$oC_~CYsjC&lP9?0Eli9i6x=8_*I{1j9!JPA&5>0QFUsfMoEcU;Q5^sRfQqmQt{&w7w{7i^<#<REw&e;8YSwVM3LHdQzaUKf}|vBo<yreakqelsLncTtIKNoBw8z|Hi$LAX4g_Dx_DeaiRMI?X09Bf8qE54Ky<dDk0@UBuP=qCI&1u_E|IxACaP{v)FDJ2Y6vo2l1Dhv_#}#y-D$F%9}=BFryq4m#6O9awW7KxD~GlFF(C^31Dv1eG+EO_)Km-gxAUk2M0G;+F7Nf#s{AMcIx9VBhz8IVZK=oAS^sB6nyx)2P&EeVGPm;*e3g{nZa^&n8qN$f+Bo-YOA3TZV8OjgN*~NR<t^Bj!d-@&l?-ULlyr8`CBm?)zZK~14(sbxQVM0)jotyG{w|5yAw$$?12tj1v#4E9PGvd00&v~MNLYisyBb!Nd#6B6nBu)>)~7Co0nVXThGa~fw!Hd$rL_9v<EvN>8LMW^#%HtKFKh`wwF<aDd|rsJHVv)Tvk;#J>MEc4pc~)`Vpp;8A^6N~@PU3GGov6Y#TQU~up5s#3ZEW`Z?0{sa1W5sizK}W=-uOyL`ct7mp(rkCO)53twm5@?J`LL?5cGNeCitXOhV5->9OhM?&33`X8=8YW_o(oeGA`|Rqf6fRsonIjw{_in4XQb!51R;%x9B()>a-;$EWWWpBprFCu`aCbWtgG$Mo#L3kN|jis*%co&xO?mhvS?Pv7Bzc@RD0qVJ{$`^iUyp1NClQMmBcPJB)Q?Ko%QTYSmp3}3i6e4V{gM1#+%*|6zZkV1y^97r?6g-;D@mwKmX7H1||qyW-`h43DDWI&hUN23=+3m?oAbE14Psd~@pEg^!<7SBA`i7!a{5EwU2T7)kETVQA<w&3%bU86k;pYA*Hi3VSAer7LxF0=e~z>{(5py4wYQG3*7t&iR$f)}RH0WS?OL-RmbmUZ32m$2i=G6r6pz3WbHxWv)cRp4DKKB|u%c~*I49u(f!qVVob!&FPnTlBvC=l=)i&1+N")).decode("utf-8"))
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

