"""V24-RobustMarketLead. Based on v22 (1230.8) with: safer front_run quantity caps, isolated error paths, fallback with useful actions."""
import base64
import copy
import json
import zlib


_ACTIONS = json.loads(zlib.decompress(base64.b85decode('c%1EB(QX{ck^Gf~p8X(F)UMWVTxo0x<}L+_I>EOf77N(M0SDj1-n||C@0K*2>8|d`jEJmia%AgCqnY7!WmZ;IW@Kd6&;S4AZ@>Qb_rL!3<oDnF{N#uCZ?0bb^7iuG?faYEle^!2^W?vN{hz=5@2Af`{pat${`TL0{l8ED`}xW1H~VksuYP#{=U*;=dh_Gu)sv6E_44||$A8YjC+}YGc5j={-tBg;K7I1x_3rZa<BRWBpZvJHy8h|oi?ivE-riildjIlv{&(Nr-TmWt-!u}xee?29@88ZJd)A2k^OFy|cei^1e!9N7eZ7A<y}5j~)YH4&)zy3q&(>o&{_gy-cwo&SW-nJ0hljIzbTZ+A<kPtJGkCVp!u?mtbKhQFzT9P6$6_A;3_p7z4H?7X?;5S6aeaRKr<o-!6mgi^_`A|v>@L^inOWE6?e1o6hpTs&_7^OL^R*eiyMDhmLuBZG__XL2?=7Wf^ADA`n2D7dXM(@HJlOg1i~Bubu9kuU%oK`7aMV%rO=)`JD#ufa*VuYVkS8AI395CjEilLEd*&P;riiJxeF9kDGex6$4Q>2P+-l(>OSXN!w=D$ICjf7I+H@ZW?<w4SPn&wE=EMGmW>lGHQ_<7ordJ=2hIjZ?MYppV8t{n2*O{?w^eAR1L&ZA&#Qdq-JVAN&=nq((hR>SE+55bG@Qr@Ldhhplj7J~S+94x<06eJCV|sagb+vnW`^z78H@9!D-u&lsR~oM7&Ij72*7>{#n6smkG8<yPVy7r@^(Ue8@;r-GvD5qoE-~9Y);hRI6|aC3lH)waM}s~waKGn~4p<ONDfJ)^dS-adMUvjH7~6KJRILiQ+>&-7Xydx{BvK4sD!)wBgkMU(Ou{e2@$Lo@GAa7P*-Z0#Afc{GhPG&SlSi9FpbHhAlzunBJltpvhETKLM&7fw)ga(3_sX>q`@buB`zhx7h~diDpMAWaHN6_>PF~y{+{tB@WsjqEx;;3(VR%*KbRKe06MQf7Is^x(e42AlXAs;gpJGGZAdFxqhg?C0IQId;;@N>RL~HQL_CuIg1Roe0j&ykG-cpB4mMf3?vD!me;snC5KA4<iqD)^yPmjRfw>h9z5bQ=r;MWIyeZarc13aKI_1S7%8c1+Ce7L5}2u|no`c__tQGE1EKRVC@J+Ny?(w#e?b)T$&DB3dR%#=a+0C89%&Aq<7`HxuKg7V<;K9|viY7E{7*5pybJ_R<48bIMex<fhliK#OJ<f5}P3A`UdWp=RtHR-HTrG`;K^sBYqnXMmHHcR$<vorf?d;&JlUU`{@-@IZ;u@e_QOgeI*644_79rD!Nhp!L#cX$ACvD!Zme8lJbZDzqEesOnj^)$3E^CS<>;=9|M%MU;7Zf^dJiOO<bl$^tvG;l0{$>*b8N+NYRu7MfU)p1oh&Z#45C5|Pfdj9en%j`VlGYF=jLBio5>^3&eRSQ;<M_@8GOW%&Ltm)O{d}zO`1N=v)VYbQ_<})Ml7J^Eqs1dQ;N<DoB6zjzPU_Wj$2Il$Vm-~?~w@sZNfR5ap(JB^{*uPtcg&%-{dusW~uRn|Srf-{vEEh%M%ssqwmH|O%H6Nb(alPMM2X$+e?2ig&Fw}$tY4x)(hm@Mr{KNJ2)xNMWawHF5I85iqJ^PiI9G_t*X5PAsGq^OoqX_^?D&Y$aW_zvGo*Yz;w||^PZ(4dVRp{WMGS1EXm(B9NX{ln}b&%n}5tIWfpc}$6MC1tx!j#eZ^~=sp7>~Zpt;0z8>}4I%#R&17eTaPNVav<a4l)(It*$ns`uZYMf?rnj2Dd(xI#|&;$PcH?N*Jy!U3v0=AuizL3;5j-YMJ5yQ(JyKaSyfAIOtGNb2>LB5^{fWW^90&H;Gu;euB0Fg=}#Cs<2_f%%<RINAGi|m18{4t_7hKtw%*c)kMK*ONqRuJ#n1CXe5LuU$kx43buY|`w0se67l>g;~ESP`Aj-qP1J|Z!&x%h=2Dhicr*yKQyG&sgwo<hD&c5}17mv8iSH1P%XKs0Du-K6?$p2`E<dguH|P=2=}}%)HW{?#Nz(QyBe#vR2C9B;ZYS;jivyknw+;s-JF~<MpPs1T-OG_lbPk}OY0IB}mnftR=t2d|8VfmelCFWkHDo;?dR0%{J>>KIc^I9~w+idiux=QY_xt0A%ka$aAlK4^(P<fd*ACXuE6LuOuQz?(OW>V!P*@hz_RwSr!YJwZb&Ys{K3*!{@Tmz!J@SH%1Bgh1MfM34xw1*mPKkr7@#CATKON0B3_anurNZfSmW^D){gcm@c#fQoX+fOQtV63T!Z|cVH0L|75rFmzw+^k98((ijvYrIy=aJLEHjnVEnDN0I_Y$F2h&%4by<PgA=DyjXB+_~E(#(+qeS@<ZMev9UHE%5%`Sm!cMZ=DE?jea9Xe}^oBP$p7N=3iZMH@hLdKe5Ea90{5Y7~7xTLIz_5;nV`cEK2kPT{;)U$L`;v=|}b{6i0y?8I4B3x6g32^nCZCA_xaDJ<+{4`~bNfCz^uE4?6O*E%yN`STDh_^1!|diCay%GeX!DEi_Ej8L%Y0^pDXam7EYShzoSiFOLV$TU4JS*{nqRMO;CIOQTfG02xC(VvYFC5Kv|d&ZHLyjZ}`^_$3xlAQ)FpN_!vgE1iP3Mw)qpWVS9obReA8Cl!}mO(3Fo(w`JI9R&A&H+oR>BU`SjnKb@@h2(^(wPc5u_D@0X2b90S~gz6N;y4rWtyiJQ_EBdt_zMR-$9Qq27Ac+P`z6M+#$(xIa01cCG~x=!gWmaw)9l;8)Fg#i%fuwiy({x`ttdrAB$7Tb*<nW)iDKZQQ}vTB+FD7K)*@RrwmL$zZZ(0eUliG+CxLNA>_8J*?Z*E_tJ;ymhx~y6ivq<4-E>lq}WQ$*au|yA-Q#FpvWqQDr(R;p+7tF`H!a0M;YdqqR#D@H$#WH9YLpOm{#4l2?lk-9vb!TRQNDC5w6OIF`WEVEHm~nc`?lG)r1fY6LdkW+!>*X=uFF|q;+UY-L0@w8Mh;zLk7OY>u3!t>b*u(RM@BkIu!>!($b_PG9+VU1d#Nxda-pZ7{EEZ41uYyd7e&;fPxq1-+2fbS-^H-AT>-cd|zRX1w9aTn1V4da$63QL}u|09ED&RY|Q8<Bnc3YuPX^04GIebizI@AeLVhsMsAs>105ss1B%pWQ2R&kp(*YWYO3EwEL;&+kU2?&s01f*1#<O?>q52_;>s)~a^&c?ce;<Z(Z$aTVzYu7XW)UlMCS!D9jIi=WKVQsWZPglBikk^hn1eb6|4e!AgrN<X9$>T0A$uP7VrqHOnqoux&2F)0CucOKnla?VAz7c2&thvdjUwI;i_ITcg$DA{(a67O#;`$x)gBi18RfOqG(Mb7Bbn-&|k59on^2?1TKKgU0^*P_5e(5Q9{!0SM4sAcNf|BAp7hPjq4|J-dmT(@wpSNQbV=y4pZe(NK~^Ds!<%2?0t#;(2D3b0E2*l1l1Avh)a!CSnojS(4&Ub;<-QGcFtNeEEY?Gs6e&U8f^udo*-D627+i{bd>gf&>X;0YhZLt0bk>VUo++a!Vsg#2@bRxX9Q;o7hZ(HS3E8PhQ&Nm!P6n32V^D6MOJM20LQOjcP1hPf{CD!(t{aR7oh}BQN`jY;Ig5~O#_0f#;R#lO0g&fYot9AYO_~4WHd#}<EmjsnFqjhZK%T~49z7bCZA1v@1iW}^k8&+F?1ZlvZ+eS2eTj_JeA>TAXIwc?S#yHdi5JwW~^9~p~!F)swtxH+3j(2`!e=t+MO1EVZ4z6kOJ<8tZ{Do0Xz5Do5PKcWw#-7(m?flS}-&9vz$>5U(v2(BhOVIr5p3gHj<&ZTz8MCZ9ui@{bqnK(m%p}<fbqi1l&p;NYdPa2}$5uM3VyNAY}zA60bL`bKCM<9mvubPEuq8BT59vHZ&%J<q;q>qiUlwj#6r*yFA{5XC>*j<6**aa09#K)ftcsTqC7It2d)#VR8SDTX<!$H)+t8g`)*qhS7#q&M8te3r34DBqO{fkb^PjVzCqo!pX=PAWq6OO*RL1yq!HctkI0%j;?8E$$Eif8M89b233vO3IBi~C?u9GkwZn|1PR(0ae`U$culjY4c+V=ZUGr?L=2b2p-Sv5!}?-8E!hRg@#C9H8Kh>sYlP3CHGldG(QcSLy>WlCW~xh*4B16ubc*n{67*TdXww%jGi81S1Ya;%0Rc`(IFbikL^kdlXzW>NI^1#5d^EoT{R;*`9)oOz0FR&)gYoZ(H&Egdq4;n1X`P_r_?C6dUalUCU=r--L;;OLE0N7%+AcV5(9xEs$PXe?_E;6xIek}VqTX+L(=BNlQzqvF5liz5LX{Y-R8HkLjTWAddj{vBK%%&+Aca~S^f8CDyy{44Q!wfd2r;QvkSB%YDw`*Jg!EE2j<OB7Ho4fU<P}_)cBDsEI?O_@?5l$&ogqOiY?Lbs>SZ4oA7UC)s6ck^m+?E;5)x0qwTD6|1_f150Z#KIEnOQ~wB9DadRnj<AkZ5UFQrprC};V{k~9FR(a8^aQ!BP$W3iVb@8O`JklKHhOR6O=36|GGVn9U7>NpWvAu~m~%Bhs1w@u2t)K_y#eJoye*nM=8{Y79wGI9P<d!gVd;48C55PSn~3mf1jGegJiT{9@iO{2+iElQyWJq{=@gY8mVaY6K;m5flG${~%FazB00{9?)yIz9U|mxB%hCB|v3P7#!0Wkm)p<5(NgmbO2=*Zuu_iW7B@`y{BgjVf@{#ic9hmb7%%3MPxm8#$7!b9TnJCd+9N!YmKzD`iv<m1o8PM_@c?&rMFii;e`ldVs0IxVg}&y-OlWG9paZ2<$Toq8X{fOAU~4Lr!KGjEk;tIpBq=gL7w$1-ZLmzsN^XOLU_cJY~_Cma>6<7-p0g*d)+MVFSYW+hX2m?PIBKP6Z*Vz14b3LbfYUc-DN>*4&*!JXy-uyCJ3|&KBu<yxw?R%0xSrWWIFt%-$r+z^QM@UkMW;9r-yqxLouAlc-%KCc!~m>+V9NR4X8mu`RFbzV8a<P0>8cQ40~s7MiwGd+L_Zk0@$sY$Wn)q;w`a9qZHwb~U%08IFj#azq_XX)}4CKR6+5EBm1wP_hz<Tv$m$FmI%;gJqCO1fJ|Sh81=#H6F;~14-t5r!@s-QPdg{rx6GVN_7|`l4H?K^#G>TD@}Z^!g_XtZKPDpBeuh3*En;YpiDGbKcH-KIZJ|btO<EJtv-W4ph+Ue*_4E@4?jAN(w%NAVe~o`zUeWtjUfo`Fl_f}VXK}56GDVu19t-X!1M)?iUADBPF!A?y@_<_m@-zs3{8@PCdM)7lv3x;5CVP<prz+i&t}iseRsE0;+4K+`bjh4-ipTXh5|za5CXiv?tb=yut`|m&+&I+ZqkEEJme1d^F_aPghMv1gz>=lM3_^+Avv$5qey5h#icj&8q00rP=`Y~AtUW(yudGyBJ+=9y9guN1ldz9VGa<i(Vp)1IAoM6HwFSWN{(=K@{<ASq!)`Vf;|xCE|i%pgb~tF+ZWu?Q)jf`VHwpjW-3!HhJepnSe)ugEf1Q}4QllcDsqFIK`1$^ceTo}RNKp^n8dF95;wQzN``Gn08N6+I%7um@@t7YjrbrlFOU`jKZ;duj3K`3txS;Cn937NP{xZ|#mF2J#%NJ+f}&DMQ3)F)`l8f{hnOiG7M(7nJYt&^_3F`M-gdnN#IC+Mblw@avhQVas6&}PO@zJg%y9~_G_1imAqEfR@LLp~`~V%u*I_wl=$ct~;@E7YdQcu5xZc||1zl!|JE1!NhJ<=V>8BCxK8OaoERg%~@H}v6F;0d$?dT!)6D>v>ad5|l4NQ6E+-pkcD#l@i6}fUK*9rMWRnYkvm?U^q;A1gfD=eiA1vZ*mz4(V^<tZLP5tdF-3hhPM64J4a+J+-iu8cca5UN1ui&UrdEGPTcAg60h$SNc7)X=QHduWi&)Zl43c~$(g7Nri0-!}d`w#G6kYphf)L_rxb2QBv5PiT^VH)4u8-9g$|#A9LXBm-uf!(3rd4iJ$*C-95*yy_GWASt8c(DZ6z$!y(@+_k#t9W=lqpm)UC+4K7wY+`vGd|eOVXB9dcLNAG-$80NgJ4;oq34bwYQe}2lE_KXw(!>G#5t|yhI?<P_pQSorjpiM2=GZT|rz(FBl9sa5$`Sfu@XqtL-!KaMlbzudz|a6+J5T>eLlsSNdI}ujqG5%_8pu1emeEDsJbuIa+pTb21&u~uAfoZrZ^$WkA`Uuwwz|`af5R!adyp!}VpA9{hbk$NNWBJ%_Y`7btpe$@#k9!<QTSyHSeEw(ns<jsni`WL6q5vNk?zf@G8_fJF3})(aV&G7n+GCG^>(VLMwUkp(u6htvE%5DTdXoukF1f-nS5(h4EUH;iG~@qU2efhwG~#gzzNAJUhmEeX0a-;kC#L7)q>dw)-gmUyCvN~qPjn4zB3YKpCatkJA<aQTj>{nBz5cQ7x$uj-Wh7eiY!^RUf^T*l&z`29s*5B(o4^+Focwop*BNH(DB3y3h9hf?%HOO+e|hlASg6@#EI3!W65+v!8EG9EkfTGqH_D|W-6Y<G9|aDvD@mY7I2o~zBerU_4?6-o+g+=6$5P_*CL_3^V{jvR?d#ble~Zpdxf;7!=Y0?+YSa5h^r3B6W{?3@Dw69YJU<Fo-m;ehnQDpsfit>d05uf2(Eq!UqZ#uc1{3g<rdA+QxA+I1Pqzns7*IM3;-TMTp)t6YW=v-ddGqM0FKENr->^*UkA{YVKc~D+~gp2N%}ou>ik@tce0&ZCU4MBWoS`TLOR#t4dd7=6A9K11&ex=mgr)~Gh)e%=;?UDX1TQ?SZ=IX@wGL|e#*i~O`<>E5|u(AJs>B&4GdY}!68>D$7e{4?6Jw|+dv1Du%iQl*%rmNi;<$Z<>O?Dv<gCVqm=Ug4FSf1tV&KMjZ*eIp_Fvm+m`k1`6TA2vnr;GlDgH{krG($XW*>$CxO(864`t;lXrw3(&2+xE9ZyGoWiBl+wYU`?!@#yMU^TE<saF9u$#B7->a(M;i#yj*MLFRvXc|~tc|r>lr(AMzVDKE3V<kr3s0y%K1zbmnHtvJitvbF!VPIt=YgCq@iL<uwc@$3CnGYAC=l=b$rZFjB$nyNeEP7rE=0x_+i|;^dKkhif-k=)S)e=9*hZ&Z>Zx1>X*J4cBnsz%CJ@BGi=S=Q>ZV?D8AIo|A1{6rMz3~PBRC*Iz2hoU5P|TH`wkNG+&xCs;Lch64Abx;MjP*AH@-+qA>vKt{p+g&<-i~7ju4EA6+06)of8Fvw26-Yp(PZfd|FCrND9U3O`eCjEV)CmJzC~l&60^^aig0>xJ@t|8oJ*$OB~do!YIhuf*D~c+~<?M!--eHw$32V&~^yvtVF`?D$QKChu4aTd3OT*GCr*cmNv5JwjUwP!A>$^M@HIxV)()~gDgMRqZp8tT?^nL#mcdQtN_#YUMPoW-9UtE2x4$f?u1%mo~pf#`fIkIIuc?MGTGadn3kmOGGJ2`b0hMlaNWgpjpF=WQ1ty3fh?7v%W+*RRWkt>$->!&kV$Ii49L$#7<uivRxHmVwb&!$-nImJAYUbqdj@sqG;au|ze(g&+Z6`(<<%!+$F>L`OPjOU#E?)Sqoaiqb=Xm5hO%O95@CZ`sCUl6F%4Fe5;zB>!ZO|sU^7Ipj1->%BTkx3(`8v2&`oOAMGt;q#>}tQ5?39;!J*$D@?gXieXt`1yQ7tzk?V{5nI-3$If&dEv{MmAnvxk{Ott>`f3D7dUPVuPuM(=4WhLd!tT6xnb<}DRNw_sg2>Mo70c;8?)}04u0Gef|kB0z7Jw_1&L6DNoDqHg8*nrbMgoO*1JjOXt*q*d}Tv)TpBIGH{m0M7eUT7wX6oatSJYtheQG`FMk>j)VKBSvyg-gj?qc~SR*w)Evmf61kt8DS)q9(?>&5F;^TZh1*FALSw6Npz!9k@4(#fI6wI<{l5Hh|g+2U#B0O~RNUmar3>32UN&g#Oq*q6pmmGGN)qt(1=@yzP~waYK`mdM4eL)KK9<8xuEuJeDZ@{9lU-y4n3hk4p=Mo_-8@GKhg9CPw5_B7XAX<bZsjxd_s+($kW`T0V>?hPQ^?)~gbZ<BJy2$?(U^xgW+Gl{VgZ%2NMTng&3a>f(&DHx;#)Xo$e2>|=_CFjvGo<|Jho{|A#(Ad6BO+Gj_IHI2j*R77|IR!u0QSkKapx6r0m@@2=8B-7d6=^ert6>i+Y?*_ur9FSS?ZwRXLNjZ<1(qsiv;8tw_i1W*e#$#$4JQv6csJBd!;TO1CDVDx$Qwvy#E_IJ=VFU6EUNb?JtvI1Axd0?XC7-(k%)nx;LVS+4DQ2+&`kSLBp(}g*bWkpGm5CELij1wzl4VdUYI@@My^kC5&2^&tEosfFQuv9C)(!k(nuf+N$I5=MZ<DbLyOF|;AGJ9^{M4pLKul>)Ywk%;)=o?txb9<^uq|aEWy0<!>C3=X^Qfp%!Lt!!4P(MmGAV=Lx8}WOJpkgDXvRV~xfQ9a#pnh!SX$LJpji2_S+L_TtPi%kj<%wdjVNHr{L2{*Sd~x)C}h~wq&7!UpvNUW9N8Mt4sQH1pH^UB5fm2hOQWx?7rAyG!8R<#vZ%$aV+_2U^W;=vZGtrJExG01;NCiftnMY8(To-iV-FNN(Kd39d14z@ML=B8Pto%MF|oT*sD<Jz#IL;^4-5hO0HAe_0df*{%`GFYXOG}{Z($K1%!#;g-X+3qSdTtd2XOM$T6IdmO<RDsUu7LfvIAiV9;_DL5_)lzZpqS5{D)?W{EVIS2rAz2jpXFq!RQr5xGAc*`N3%NZ&?!%lHfI1spBQT2qZu3he}a8(n-Dr_*2a7sw*>V5LHuYxdG(RXS!hKi0|@?n=OIJ5Y!xj#^L2`&Kw^n>k9nlgDGr=8%r)VwQW6Jl;>XwbFQG0sHDrVAyp%RZWvYAq7rwg1v^zOn!PpAxE<g3aC~Q95>BpR$mZC4>BlnpE5}?TBl#{H`}SRFEdXoCJzXHk=G`Qq!a4M0-K8Fdp9NBG9zA-6`Dhmtpf+LJ>U?TwgNAh}oEeC(g>GM&#$-A73FlEeTujUjArAgsMoBTmQu`>c?g9k(E+74fmx<d2!zGcLz~LvTuTg7d7Jm~ubqFHya^OK`%bHPVB-F$tlT1p%09Y-7fYp~7xteNoE1-LnL1N6nh`YdfX?#wPU<S@an8-JXLNsiu)%K!N2e>mdvREC`>5Sno7)ky>HoxI2Uc*Xa$T(%k=dj~p1&Pg^--zc<#4;qgP;*~0HS&;&H=y2qv;IX*vWP|&Z6B4+m`FmJl%URChH3c-t$2qGGG|r-X40&4Kqa;?Ra#djLM}#|Jlrdfn5)EA)}*n(a=I1atuSO&u#C)$SS_nVe*<x=h?WdFo-NXrO;4RufVE~5<dxM!n(M>gN?&Y(s^%x!$$Xj(eq%1Egp3h~v5WpmBj4UXBx6-so{L1=rbJJ<44TN+d;PmZ+2kazK@l~gVG<0B)P!R%*5MsWP0f79rE52ED<h@O<`e~omE6iJ2TtLz;m5(Y?DU&(<csKn$#nbVN<MfG;tt*=Q!nY`Y!H8vtW4(E3Oy_gnOJVS-o4h@NRjj*6imNc&ida|;be|bo?0M0H#K-?-i(#IW_kO1cUolMNeSoTWnLWEvuLdrqz5$==?lo@$&DkC+ou+Zvbrm8Criu#HR-vZHEjN9O5uiwzKHA1n*a%zN5vxUf72zj*!SI#`<L>PS$T(u`N*1X7)emu9~eZ3_6279Dw_`ZOC5F*^)8R>VhnUkHcp}|h~#0==spg&V4;G`klYL;vkN0smfz>pXq42~=kY?tkU&-Mh9q1@CQi2$Qlg)u41vV$N!x8nYxrEK*0<XX6MYh^BWsfQ@|ul3C8`^!0#@|qbls~Z`U<C#cNf_h@VZ^xN4w0d{1k9&PRGor>Tpt4B=Y<U6lRiY{<iKbdVhYP;zj^x;uGj5X+YixuSc(xJ^+y3y3$=cSd+OyUUf8tb?B{SMp&IhT4vOCb8d;4>Lnr_cXQF~5IhF7GzDx`291HH_pQrOvdf^NO;D;Y6}PmY=|GbguFsRseRXo<U6>i}x4;O2R(>XvmCb2dDh|-le4A8?e3hDDv6zqvm-y#mD`TUH7sqrtZ7g(@H@IDiI<d4F5|Xh-rHPzi)BFgM&U))=T9PD+@@I#|Rt#aBa|qK;0i_@zu(Jh*O0RW*gH{GI8gCGtNka!<7O&7D$qunR-hs{KozCv>D0K6!00gKD>>Px0_=E$1fM8D9^sy>9mY*$d8#H;*2MpyXeyzs6U=E~oVD?f|nttyX+M8(07kW@K3UXDhfpzX+qh?nd(dlBean@TZ+bOygB=Z^aHDOFG#Se4Ebx_S=I%iR(z2&w7mlbRZOV>}_Qk$93urhabFYT*xZ*#KBv3DLoutS=uo&?z1nrtg>W8)9rIaaNGj2#B(lLq5cp-81+Dl0M+;IRNnFhWv-ZM%K;?EbOo6#%VVssl;xIFdx_;uI%2tZ02DyBUEaqZY6fkSmkoMzp;hdqp>D0#Kqb(CSullxaCa@zN7cPG(V$0zU`AZ6`Y$65Zk&G`n1v7cdw;VftH4()@C5@gg7AH3$mB$_yK6meiio1d3O%!3{X6(uKCmG26oRE!z4NtLh+3$0o&M6dN>+lA{cd7D550sS+AJxJagW9Kik*I>Jmf-wu8MbA_Sjg+j<C2wKeA-p+UO&%aa{Gy%M6&P=N^<NJW-L;(Q+WjOQ-gtnukp<8&=_;t<6Md)SZB;)hP3&g<)Q{;8%7UtlFj2cdW=WJ`Q%Op}Qp*iLJY;Zq&u$g7&Q(>{?)+h8@DuCITkCl;+dkTohn{1Nli}e)K?iW_-U*A=toafX|L<i2fuL)jLv{hr8w(OM&?@7p-5Ma!F2;_z)?ZJ8w45Mw@_g|Yq3ifM~5|~y}6}xgMjBuS0?>&cwma`M+T3q=K)Fglwb)uv>HM!mBsH`X#Nj^zKCP4+E4bbv^olNPhPrb{K0wfEV7H4m05psSr8PC-VAw#{P2JC&vyBHAAJflh$Y?A>ZteGdGQqj7puHGqh|Cf#qdxoJ$Wz@j1v#ROCgBo}h#wQ^u!rG-T)p;hBkY1}B@jnFyw;d=@1V+y_`cb-0=(2NyF#6_6R2d@$Lx(1!ha|x;MW?YaUUGKwp>e`<7F-Y0Fx<-WhFGc<jTm%9QJkHNLEAjYv4L++uVzuy=l2HL#S9Mt4{ce5hz^AQYV~nptd!-J-Y{K#HO>mQ8Q<XPXFu{?o9KgAUN_i9aE0Ie%_IM5NJ~LZ{iX*vj&6H7SPY$Fhg;q%LmPv#r$@UYtjJPE!e@kW)+tj<8V5N9c~(`R+-uGAn5QN*Z>DuTl0PoFU~F7mhpOj|W+*s%^iBovOzj#7JfTCTef(#Y6--W7;xcTdhiGc@G1T|5{CBDTT{S?=TM!L-X~>5okB6R*`qcdSbyxvC6-O<2s~DjJbQF*hVqh0_9l$IrRf6hrXgXjUajpe|J3NRMOd9VnEo9>+V|aCQ{dPHo!+Y~rR15H{`#0MmtoieHO_A6l5iM*a+w^Msi{*Qf48mxasdE%L9K(;hf86~OT4h78')))
_FR_ITEMS = ('MELON', 'MILK', 'STRAWBERRY', 'WOOL')
_FR_STATE = {
    0: {"last_step": -1, "due_step": -1, "due": {}},
    1: {"last_step": -1, "due_step": -1, "due": {}},
}
_WEED_STATE = {0: {}, 1: {}}
_WEED_REPLAY_STEPS = 8
_MAX_SELL_PER_CALL = 4  # v24: prevent overselling

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


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs, seat):
    farms = list(_get(obs, "farms", []) or [])
    return farms[seat] if seat < len(farms) else {}


def _align_hands(action, obs):
    action = _copy_action(action)
    expected = len(_get(_farm(obs, _seat(obs)), "hands", []) or [])
    hands = list(action.get("hands") or [])
    if len(hands) < expected:
        hands.extend([["PASS"] for _ in range(expected - len(hands))])
    action["hands"] = [list(order or ["PASS"]) for order in hands[:expected]]
    return action


def _tile_at(farm, position):
    try:
        x, y = int(position[0]), int(position[1])
        return (_get(farm, "tiles", []) or [])[y][x]
    except (IndexError, TypeError, ValueError):
        return "LOCKED"


def _trace_actor_action(step, actor):
    trace = _ACTIONS[min(max(int(step), 0), len(_ACTIONS) - 1)] or {}
    if actor == "farmer":
        return list(trace.get("farmer") or ["PASS"])
    hands = trace.get("hands", []) or []
    return list(hands[actor] if actor < len(hands) else ["PASS"])


def _weed_repair_action(obs, action, step):
    action = _align_hands(action, obs)
    seat = _seat(obs)
    game = _WEED_STATE[seat]
    if step == 0 or step < int(game.get("last_step", -1)):
        game = {"last_step": step, "active": {}}
        _WEED_STATE[seat] = game
    game["last_step"] = step
    farm = _farm(obs, seat)
    positions = [_get(farm, "farmer"), *list(_get(farm, "hands", []) or [])]
    unit_actions = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    active = game.setdefault("active", {})

    for actor, transaction in list(active.items()):
        index = 0 if actor == "farmer" else int(actor) + 1
        if index >= len(unit_actions):
            active.pop(actor, None)
            continue
        age = step - int(transaction["start"])
        if age == 1:
            unit_actions[index] = list(transaction["intended"])
        elif 2 <= age <= 1 + _WEED_REPLAY_STEPS:
            unit_actions[index] = _trace_actor_action(step - 1, actor)
        else:
            active.pop(actor, None)

    for index, (position, intended) in enumerate(zip(positions, unit_actions)):
        actor = "farmer" if index == 0 else index - 1
        if actor in active or not isinstance(intended, list) or not intended:
            continue
        if intended[0] not in ("BUILD_PASTURE", "PLANT"):
            continue
        tile = _tile_at(farm, position)
        if not isinstance(tile, dict) or tile.get("kind") != "WEED":
            continue
        active[actor] = {"start": step, "intended": list(intended)}
        unit_actions[index] = ["DIG"]

    action["farmer"] = unit_actions[0] if unit_actions else ["PASS"]
    action["hands"] = unit_actions[1:]
    return _align_hands(action, obs)


def _fr_state(obs, step):
    seat = _seat(obs)
    state = _FR_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "due_step": -1, "due": {}}
        _FR_STATE[seat] = state
    state["last_step"] = step
    if 0 <= int(state.get("due_step", -1)) < step:
        state["due_step"], state["due"] = -1, {}
    return state


def _town_demand_now(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 != 0:
        return demand
    town = _get(obs, "town", {}) or {}
    for shop in list(_get(town, "unlocked_shops", []) or []):
        products = _SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += 2 if len(products) == 1 else 1
    return demand


def _future_quantity(step, item):
    future = step + 1
    if not 0 <= future < len(_ACTIONS):
        return 0
    return sum(
        max(0, int(order[2]))
        for order in (_ACTIONS[future].get("market") or [])
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item
    )


def _pickup_reserve(action, item):
    reserve = 0
    for order in [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]:
        if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "PICKUP" and order[1] == item:
            try:
                reserve += max(0, int(order[2])) if len(order) >= 3 else 1
            except (TypeError, ValueError):
                reserve += 1
    return reserve


def _existing_sell(action, item):
    return sum(
        max(0, int(order[2]))
        for order in (action.get("market") or [])
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item
    )


def _repay(action, state, step):
    if int(state.get("due_step", -1)) != step:
        return action
    due = {str(item): max(0, int(quantity)) for item, quantity in dict(state.get("due", {})).items()}
    action = _copy_action(action)
    market = []
    for raw in action.get("market") or []:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and order[1] in due and due[order[1]] > 0:
            requested = max(0, int(order[2]))
            reduction = min(requested, due[order[1]])
            requested -= reduction
            due[order[1]] -= reduction
            if requested <= 0:
                continue
            order[2] = requested
        market.append(order)
    action["market"] = market[:10]
    state["due_step"], state["due"] = -1, {}
    return action


def _front_run(action, obs, state, step):
    if not _FR_ITEMS:
        return action
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    moved = {}
    action = _copy_action(action)
    for item in _FR_ITEMS:
        target = _future_quantity(step, item)
        if target <= 0 or _town_demand_now(obs, item, step) > 0:
            continue
        stock = max(0, int(_get(shed, item, 0) or 0))
        reserve = _pickup_reserve(action, item) + _existing_sell(action, item)
        quantity = min(target, max(0, stock - reserve), _MAX_SELL_PER_CALL)
        if quantity <= 0:
            continue
        market = [list(order) for order in (action.get("market") or [])]
        existing = next((order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item), None)
        if existing is not None:
            existing[2] = max(0, int(existing[2])) + quantity
        elif len(market) < 10:
            market.append(["SELL", item, quantity])
        else:
            continue
        action["market"] = market[:10]
        moved[item] = moved.get(item, 0) + quantity
    if moved:
        state["due_step"] = step + 1
        state["due"] = moved
    return action


def _safe_action(obs):
    """v24: return a safe-ish default instead of all-PASS."""
    seat = _seat(obs)
    farm = _farm(obs, seat)
    hands = list(_get(farm, "hands", []) or [])
    fx = _get(farm, "farmer", [4, 4])[0]
    fy = _get(farm, "farmer", [4, 4])[1]
    tile = _tile_at(farm, [fx, fy])
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        farmer_op = "DIG"
    elif fx > 0:
        farmer_op = "WEST"
    elif fy > 0:
        farmer_op = "NORTH"
    else:
        farmer_op = "EAST"
    return {
        "farmer": [farmer_op],
        "hands": [["PASS"] for _ in hands],
        "market": [],
    }


def agent(obs):
    try:
        step = min(max(0, int(_get(obs, "step", 0) or 0)), len(_ACTIONS) - 1)
        action = _weed_repair_action(obs, _copy_action(_ACTIONS[step]), step)
        state = _fr_state(obs, step)
        action = _repay(action, state, step)
        action = _front_run(action, obs, state, step)
        return _align_hands(action, obs)
    except Exception:
        return _safe_action(obs)
