"""V41：纯 tape 播放骨架（fam_F 原带 13/8, 198k）+ V17 动物护栏 + V24 fill + V25 择时。

设计：绕开 V120 执行核（其每次调用重置 _ACTIONS=_V120_DISTILLED_ROUTE，且核与
OceanMix 带耦合，异源带过核产出崩塌）。带即调度（离线调度器产物），武器层即规则浅树。
"""
import base64
import copy
import json
import zlib

_ACTIONS = json.loads(zlib.decompress(base64.b85decode("c%1E>U5}i{afSbi!RuUjNy?UTN0DobFeMWF2;mrlU?2_x1kQz%yCDBPT&;HI{Ww+6Io<D2OJJ`!oSk{6yQ{jo>eQ*~zx?l`fB)-0{{FXrJo@L~{N>TNA6~wC@za}U@7{lSd;RFgfBMa%|M=^F{o8-v{O#sHfB)-0{_}7DbMwEyJo@hC?I-Bfw;%re)3YC5e*f&%qfbwG{`%vmf3Bjxy!-C@`i=d!ch}c1ZvOK9^{dxEe0uTK?k^v|yMFfm(~EC@{PF+(={KwSzj^umPaoc_hjU&6{rBa&>)}-I|M2?l`|lq8xLwhkF}`{G`o)Lm@0Y`T+AP+70<WGuzrOp#X7C@c-@Sjd9Khz~M)>CN)F4jtK7S}1id>=H@BHCLpqnS}G`RYS+abU&Jb$*`2KyxzPtAqguA<h(>u3EMS`%bZEuQ#k=0ChY?=5G-yB|C~uK10Q&)#3Z-OXkD%QUNI7YGG8&q2=cc0>cZcz*8U)p>ry8u;$@hrPb--W=Dw)1zSB)M}lzGL>1PiHlWS&fAjI-I8tg^bd<w**^HBPq%h_`R5U}I1gU^u2TD7{yeEG{qM@vOVs90^o7jMnz5JOk-8ywN4S#GN~uL#OlrHuM}9)<b^XIrMoDRPqa$<5x3CM(-n~0W<L(}{lG5q%%N0DmdHX8Xx5ukr*^W5zg|}Yl<NdUxg_1+6w#I5hJb(S_)%ElDKmFnQ?faLnUjFN_aw?~7d&UiD<lTFfBQr35rHps);j?{bMt@tc*?E@Xk}0!#e%N_dsVAmHaei90FvBKQiDdDx^9FT~Cd(SAUs&2W%Nm%^O^u9r?DFhC^0{hJ5B-7NnjSUq@?j5;eR%A{WAn$-nYI49@7uh)e)TgnwRr9g_!a{IKA2H@ihIcK-TSxCK7M=s_U)gw$HfOZj*z_++y9gCcegJ7p}%(*zba3*!@M!&X*4cm;D0HfLIOy8?7-9|5p{rbyhC^n3fH7y4)TowshY+zDcIF8)-dp<L60M#w*q+TWB+8ORO}~ZviNxqM3Giy|CEuH0+dVth&O5_gfo_)pM3Im7iRxxIFx>FE|gIVD)F;4mI0LJA?Uc@&fBGcDc5;ZdRZY;og*>68T->~&NVYf5P&|6qFDA7lV&wCH(+QKQZ<Q_xp3UDn`WY@r97lX^(Lo&XJJycqdT0bS_o&{vyn?9fJAb}BFE-#jLDg1%|@Qj6)wJj0aIzH2}r<hcc2a&7V^PIAeUzaI`nWmtB?EG;}Sjh?v#Fb>=*agFUYYnQhpQg$-VWZCRk3=f4V^0u}`Tfzv?3XaOLH6E|)n1;b)O^YWQ5^j#iyj^$&JA0p$+u9HViu0nBskTncaWy#C)kd;2dXz%DU#*TEx<&wy$?e@}-%JExLVjOHNL?B+iT-py8T@i^u+m55X0rMm+up3MvLS@dbK9xDL|S^|N8?l=_xLeZqQvhaeZ(R9#y_IB{3f7D%lph*gez<w*V-lxHt{K4HfqabwLbQJjXz4lF)f4cj@CqgZca9MjC>{eMn$?ntdSdI_nNcE2->^*t9-~CZql&5oEFXaE=&y91pwE-e1QBDdjF{NMQD5ZD%8mGE*J^{}RMyIy@f<~uYZs`>H^0Q8;bmEm~qXsBA{(<`j30tqMrB*f1S}W^uRweU9*!(hi0wYpX>LWbQ-P>B*LdvF1=-0m{{~qV}$M{0$-<Gl*X4Hc-D1S_iMPj<v2y|(}>2VS_?nkiw+`tkn9#$s9<Ix;avr%K`rHZPtc)AKpQ?9tN7LKC`E1+KK-7^lOa_|UXt>O$E$s^ElO*^KJZZWb(g9x_!>fz__cP#bwuY>*{Rk3eVYE|j9ET6AS&>b&ulq5XF0&Z)+{jwsO*NC0(L!!z#JT4AuDFxDxl?2LUpd-taaC0<n-UTQFiv$tiN#j1getokae^-x@3A-m#boZ=OwbWn@gS4H*SH;lnt;=R=-hlNQT{uqCz{ywu>-9InIu|vF6?w9o-2{If0&L~7o?pFq`A03sP#^*}J8jh6*yT9&?p?eq4x7VB#FaS2mXjVSVlWD<=nv8$3Gu{CLO}b1#cG~64jI+qn%IRFtTd(Ae_cNdi^x4pO*85In`N0uO~7iIRQ8SI)0=^bk_02O<&0Q>lq#m21TOoY5Q{O;!9XcpU)oT%qF(}DwzDw<8rLg~r(lQTb}&;&DQ^r|%w`!_qG27{SrizX^bq87aX{037KYJxz}g;UZg^{l?@v~LYEEzh6_Q{+eg9SoB6|LQ2~y<WY~N;#Y;M0u3ZDvu&9M(00E*s6>A(5H7~!Ce5drNAkAnt2gu3t`wWMX5^@wzfPBjO;Q{>R5xuAWf974E_&)iz`ku{^xnT{7~8WxokH2nctcrxJ9$<UC!35D{sa8z|<DLn9MHflmS;2><7)pT?^2!=_$B)#2=<&nQg!#JFIrh{{eGQD6<f}4;U4|pG*NF;w(fu*=UGfSbv{v|$fXOw~7hyX#DBZne9iPE@*{D*98H!4D%o~h_`2jRnC$5IL)STBH*(Uhqg0W@~}B2u>ZtAy*=xNjoJ>6vkXH{!>G<K}{6ho(QGF|zJ`!Mq!vNI`^`s|f*al|i+s^0%(>_b*@l>6d&XrI}T{ODF&Sceaanx9@)Wz|}eHH&K_ShB_{IwOEwP*iGzr{k-n}*xh+hP~`hAG8so<DZ1iX1DZD`%aUsy1Plj}%i_#}ptyA-%vn9&jhyn$0J_SSukz6ENi>79F;axY)J*^qvBz|m>eS<`<|FdWDxguWmyETSo);Fsc&3@wx7wEle^E5=m(4}OKK_0gXwy4=tuDI*goe;}WHGzLRf9bw8t(TfUGT7`)<n{28A!0#`p)|MD>DL#^>I6B3cYzirk?k3!Pw}_4?Lj}i@+|dE+n^OH5?{5$sE%PH4(2D&T~LN(R{k3rnsiUpY{b}QWf)oK%!%1mJn_yg!WmP*x#)F)La1O1@TV`n~(?hqq7|2a@TG(maMj@z@n#Af908@R6$b3G3*IMpumEK-#r{BX8CZ)2%3RzTK{>@vD!K7XyO;(a*vL$dS5tYMR{eBVA?waWQxt&W?(YN*;9fi&8_%&O55=$aRi!=j+}9F?GlbeLHgdX+n;XNT#@E?-`So78~V4X8nU_iT}HZj>7V!!rtpn*FvW+K+rvbfxAUs?r0~id)bx_g12XD@%fnW>CS6{*4X)!i){(G%6a%YFzr;+WNAq#y5a)3fp1lm6A@S^SMmAq+Z)vrbe5JaW(nX$t8t>{SCi^1Tl?QsHz225h6L|FTndH;(@ugcPjYfVS4v$DfE^P@%_5cLX(~HA&tURMnkPr%oG-#SY8Z!5HA@tAya206O=vN+K|Ixft5Gn0bQz$jJUsp{FcDA2dEI{o=*Ea};E#1PkK^E;N<aj@}Uja(nFuA1flVLaS2q=;v4`pf3GQdiLQ&(53znuW)-#e8C+v}V5pLn{l#*2*Cg~2B*GjMMofKVpPWVdyd4GB9ANd!r#zX<_mOc^2{(4Mb0U{npM`hI|lK|+Vez_#Ybt3DF2%s7}ge?*!LQ<1(I<Cm4+&YnGOu)HB?Ut*)YC}e{64NA%5f$=6)H<I-$x2LX6UQvynG?Q1@)aq*`VQoiEnjm?!QAW9&$gn{kzO-RaPp0~abO=Ci#(`96rGv$w)JGR7qWkn)RS)dN+t+XQa&9o`&g5)8(NdXDl(D<n%`$_=c0I`opb98g9+mVg2;20J1x6bwi^FCh-MW;znEQdsqkJYm5zkUEs>c#YY3TsdfRHW3$(=k>Vybv&jq<efY4eC9xwzTVIKwXu&mAE25y)Ln(&%3Vw~bPY>ue`lhf50I0fU_ihrL2u8#F`i4Gf!V5rggxwT`MV7&m0yz(|`rNAh%7q}OU_v$Vr;T&i>tH%ZgsG7afiiAz`9W8Oyj(GkY40b*}8^4bYa%ySR(7B<$H9cBr95rzzSHL(Mb&5PoMzh;A#quzho9>2-^r5Rd<_%`~i+uS^n4fr|_mwZMb1NC4apnBQi({dRB?Q_XZ7oP>tu?VV^Q(~M|oi>-53F4<}{TYH;a_Xukf!*5C!SPsRZJ@1((mfK7Uub#gNzq4*T;LT!WYtH4rV;bD0v%Ojz`(6VTzHwxF4~KLhkCN=zjfU=0&nAkjOb{P_X**x+)b6`p~~JFY6+<Y0&6not@TRfNWgd`y+445RZP!OOT`RGZl?FUh9K``n7^sy1*B9+dJqq%e>L8zMNFjcOj6k|b$h*)=jmrRqG3`J-7a<Pm{A;0dn!W!P00W`68_Ao;0swd$q#CK?jlO0?R1MfR8joFx<|~r!AVwpW$!Z018oBBfkL66Dw%9f-y&<?c2n{i7@E>J0yAd28%H#dxa~gvrX4nQqybVlk1I<7>6@ICMI+KC@fePrihEI#oKwI)E$WQ>I?fS=dq5dK+xwS58Iv1v*B4){;YPRfjVgXrt_f^Jyh!87J=;@aAo%YuaMDDsF`B0YjCVkmnUhp2*|!F>`L5Em%`}i30(fN5Iov!fp~WT~(jyXi1r=6?Jk{8^po;Ib_3M6T5H6vu%2gc`46!`sU2VyN5Q{AQ=+(YgyAe6Ha=QjK%^}1L?277WFp#=3WDphIP2iYW*t?4E{s;|wHwA>sfSFr&h5roDdN~ZWcafczc)}BIF2U*gP+MdbS2M*po;K|~&L<~Sgz8kt0Rb|~<%m-*O6kx_FVBf`r}SJoC^;BM%Lz`RWKyq=CN4E0s2)rLzuyywE18QxvPe=3YM}rxJOVD4fDsqhpamvH>Zno&O9T>I?y*6mF5jG<6v;@UjlNM<3e{%;j<RL?NN-w%*5c5`%01e78Nt}`?Yxva9V8h|aUmglN3Lp^<eZSu13dXFzJJxeKTLwWdvjCHS1o+dI`Xj@k@qMjl!4)S*+p*?TcIyfhyH*)azeDHo@O&Mr{RKi2sZtCHjkV+F-HXu00bwebOc7(!Vz@h%#kROfu<)7(z{qGjLAl30-7d@MmHwPU3?0p4pvQvE?PvW(X6^&I{IDGPn*#Z-2~|m-st3@YoRVe)g}_Iq#K$dPivxQRJ5mq)pYTw4K6?q+D~sW=2j`iwzFc;tqE5Lmhak6>s>z&3O8yjsH_HnqPuBjqj)etLN+6(+hJ-wo`4@UolRjtR71?31p#ELQS;%F3Q~aq0|8N`%dqwkHBy4?+YOdxoQ#Uc9^E&e`1uQ?C}xv%sgKcGoAad2<&Lc&sf)YR274!_!*_WMNe5qEu8?8><VN)<SC&wGe<j^R%a=^7HJ7=3?9_~4QYK|FWYX1a9uUm?gh(EHAL|Uk^4x^!=C=B~Uy@j*Zb0!=G@v+7;QY|!YK@+gDZjF^2CY*xu?K)kDhH;3p}x3S-}|{`4gGHO{Q($zBhb6&rp4f431`dHw7W4L!PSt2TBEZ2?$t`o#wnQz>Fmg?A@%@LqJox>`(-(Ovr6TPjk^DlOp_a+myvpdhMG`kqtf0Q5IW9?DYQeI9Lg0XhKh)yO}_*}dbU?NZ^E_ZC>)Q?Z5u7mE1+>9M7;Cz4&L7-6|ly6s;E1-w*5%3ZkS-_pu?hmnDG6XfWc;X7R#z|Ep;qIB-?SMW(*C~GwKZlNrnm~Fp?HW7C{$4f&^BJBT$d5wEMWTCUg!`yWT>NK$5hjE|(sR5P1*2sjYg3XE}$I#zv&I3kc9JUj9)G*kSTcn{`I!q?Izn=yNR#+F^hc7k6#Uaw#kP_&nf~<goU(Uzh{S+2sraWrP6GEKPu;?6U}vlsGA!b{o<hEjTHdgs=}-tlGIhEA@zVRG@3Zag(Cyhymr7Vg}F6m&{JZJ<7KI$zKtV)qwGR!dEZNG~HjtEy<%-HGA|BtoCt!&+8nq6nJ1q(n<lOBmy2xq(^bF$m+9DNh8{tBGL|`xA3)zwcy*6RN!k1(3x*=s}Y@4iq+jykBk8xNm6Z&<BKXZWPTK1)q~!BYUV^JRw!u+s7a+{w=P9HBznR{^s^P?32||-xng?KltNvV-&@G=LZsBCgxtxkD88zvDX}CQ7C${dC0H29Z_Rzwxq;2+EuD6ms^P6-T4Ah}-i)dbS!wvkHTSHAkzHX4c}FCEju=rYF7c5qfRed`%mKi6Zx|s*#K^JL#eomEIs8LzDxb-%QGotl7Hi&@;++vjMWihPNJ{#n4_^5v8PJZUn2hUza1q*<hl|WM*0vO^=}Z(pLnDX&eCce2!g?!#`YE#%cmqfm%H-F6Y?qMf%*?<HKms*&fgoNv<o2GTfzd;;iF(z~x4~~p^?v{_@BjN1cv-WrR^a8=>(l2p>iDKy_yD$4DeI)OV!~8`e7m!SCeAVJkqG7SFz23unsG^I%X34(jfy`BU+HNvHima)vL~uALrGv_DURp^It}oZut>%9>)N*>dBmZb9?m2kD2*C#;<{o3^)RhbDfs#7vyGa*wnJ#mfPd1w8)TCXkgAl;U<M_qyMp4`Ult_p`Dx@=6d0jM`UXWo_XMj-Yb~m;y;%VQoMQ6h)@<)8IJDgdAcRDPLT+Mzl^AlkM>b^T5*hXm@jt2E1i`DLeLb<5(`%p((N3cflX{XI({{F+O26eBA!5$e+Ye2tSW=DbM$^0KLG5pY?$gKi3BV(_Jg~Mp;eZeTQXxog<vo`MX25407<RRy)S(2X=pabL_#31fpz{sP%%%*))d5z|Ojxbb>NS&wVLKfjAYlkg>XQ%02fTz*)m=X&8?&|~Cc+7$eSih;-TQf$%oQy7`1iMpu*L<~9W?Q7aZXjPV8pA(>)*WlMt(ccB&$)HoYtS%uIX_MNJXvc?;8i)O5bBa6WXzF%y}Hqmaw00*n|`;8Gt1bgX@^dN8zhAM+V^wtsi8cf|43fu%?B@eL&Xel?xcvocvF-uCz}Rq$<+HvN+3&nx%&bs2h*8EU<LH(0FROtqT%9QH(9~JL&-hKUvC_C2eXNk4)W=)31q?gg9lS$g#3D=EC~Iaidm`jm&&FJ>&k9I%u!c4uhbF{uziDQEpBQ7jG7uVXH^lp~U4No5zpo4)8rNr*7?c{nFKXD=HW3;*>V)1ec>j0q;^Y(E^ShYJ~Rd4AeOw>7|2~Clpf8j6|tlp?}OggkMMLPyMFJD}>>m&cGYgq#U(BLc;nebs5suBw@PRq?Cp7a#LRJbzt23d0I^ZBSYhLtmFf@c2D2$lilkQ;oshhUUj!}k+U_&WrdvSR>xPuGfQIs-Z|;HXoTAL?7M-+J?&U^U#zYo_>f+dF>cu`P<NvCV3@-sHfQ7_u{J>2(85AIjPfrt<j6zIz1xe<HCal@tzNkoZ(qOZK2sU2@2_9I{^4Y2{I$UN!*B!%e1|PEo@Y~$s?yndxqE<~*l%{yc-qQHUq;ymHTackBsj19t>98{RqQKiWR~^{`&H6l<NJp=OF(RBI7p$|eYGsUvM|{OGR(zM$%j>;UJI2uo3do?Ta~aAh<&o3I9bIyV1~V{!S!`j4w4WlDy5dNQ66joVMIZ~r9Q~KO(lZfK?SDj;8~c!?EU$_8o-oiq(ByV7(igER%gVTw66-YQu03sI%<Hz_GByxg~{S|1oG7M6}Y#Rf{G1=g#!>9TZW^Pqw`i);pdbH`b&m%R#B;Y*zmm1Oq~uOPYwhZq4ES(6>7b<5ygN&bbdNGO1eF2z4Uwnd0m3Y=}PPv@*B0Ns*luGZK5jIPkzed|9o%v{z_ySZsiH3N=E7z*WweF?Ew(|g5I|zui??Ft8(dgQ0H2AwzR^qfg5mrMtFu@-ST#cHtyznGI1#5-$3nB4JYPuPMp@_N~M+E`+F%uVq6fmne@#UCs9{$ePld%Frl%Jbxh@WoGC}oH*=U`-L+M6WApkAl$#-`j3`%qM#Jei#_e#*{XEA9zH~R!^-@SQIlY?74Y>>n7&|Q4ralhsS*m8nT#9Uryx)Kft2vhfkJn2!?aPFbt@jp{m_<~oX@HkXg$EVR0&Tpb(x4eCzo2WUg+acS0n}f2f(3<B69^*cnyrVia|_>Z#W4tSP<5O)=055qf)EHm2K}81F`c{Sb{lOFA@a9(hEM2A+s{GGL!-7>2QFg&n@^i~XMd$~z=ES)Cs`D=S;RSx(~tG|kz$IcEEE(u20<!d!l10}1SWZwjvh06<I-D$bzARsNiI}FPh}wVh>cs!zinm{L|5CIWSE)&YllGfzy=sjI|}IGKA122{qfrABIQu6{0_`q*Iusx5V6gZo{B;J2RL3sRLLCk7-)zHAEdg<-UVKLX_k={VUYs#aLb{)-bl)7i8;B2>lRaCyour=rPFvin``3A*|>bWh)l!PwBis5k)~%WaVTbh61bT-ty5gzyNzue-HGKTvy(JW<b_S11|^u2C9J)*Qp%!_Bk7z~UioMb3&nGA+ioa$nOZJ2JXu(6fSP5PQC4IX*2f>Rm*9Yg2SzZV&%>ljTc>f6Q{vmilA{S#zYb(>;5VK~FJTOs`B%{30${?XGNw2ns3xy`0)J&qFue&lYFE*d(5VM68&R7PTV^B=8iL_^tW?I?zN}7>9o>Gq8DuqOL(!584|o4@(oILE0IDBnF1_*1CU29^Ny!Th5}i9h0WLEdl+GL%QXeK{J8|IMd>VzX*~Phy3U;+!g)Fdd>+sa<76!)A3biYBYRe~Z*4Otv;F@31`;~at{M=2MITf*Qam@zSR2Os<Y>a{HVW6ZGXkV8jY5MnE!)4GuOEY8qWHim=@4)sMtMjbQ0nliQ!fD*%ARO?)c_tjr3HDLQ+!WJSdl4AQL7{!bdyT5Fhw?IVgB$aa2Q{MxE`(}M+4swop|YTDvVazYD5*OSSatp0H4ty<qSEE(eD#8feKy7_gMGw07-Wh5^sQNxeZXaaz~;0{Jf&a`(k)3u8tR~*YTn~OaYmjsuK4aTJZr~Vv(XtRxnh*cM#dLa^^Ol1Aq2hm0q-inMx}xff~VOAV$2x;mI3}_%<UtNMDYSdB$_1WVdtoxzmTaM)ZLIn4{_-2)zyfCAO=XA0sV0?uM_3WqUOy>gve?7rMjpi!k?tlo}OAqv7`Nb$51k$<1qqRKh&9=@YBTxLZT|tS7DmEX240a_d7-d%5LwhK2+#{#mny$>R4h=qgf7G`Ugbw%Xxn*4qbP?2Dt9(&c7;`en-`85VCJBK-IMCQYj07y?#P`bBxHT0TAJ_La&`3-h!ze2VRBOY={e$Bi@U8>O?`SqS=c{rVP)3r*p{V+M@`bdpuF+9iDKN#db)b%0BRI*_T13v#W_%xKLU<!PC9@j$4k=`d36qq|30CZA-YCtqZzdju;85p_v}WqVuH+KqtfXdblaHTt+g1YwxnOZq)-RGP7`@cJISb<4){V)YtcXGq^gmzA1|@%D6bzmTLB`l0Ub!BrN1(d#aSkC9Wug;6ZpWJ(uz#yW%2c4?cQAL$Fd}#FiT8TBvG9gSd_vq|Qg<2*ifowPFbCVAuf?o5w-AJt56&dTba4l#8gPAhe)rA*~mO3fL@HX>>gF8fL)0Lc%4*!bm>^c(}>23=G{y(?^My1DT}ZU1XCLtBjRsGAY^{OXQ;ZgnxaUXG7K)z-Fk?{Y}P>8OfibQk!`fiKN{lFjE&&-XnbRnD=LI>HfN0*DX@{_3B*$DuH_`z1vwrW|g(HVigrxL1j=(np}TW7jz=7%0-AO?8>fCnd@7*{-pGJGW<ojU&%F82lot2NReF_ZB9PsJ<6O{A*BRw21p?z2AeH)B}QN%GLi)vG?=M_aW=Inb=#=nVZKP+8nSf^$E8*B+mhQV7K7W>7AFFz9h*bSq9F!DvQ-ra5jwOzA@;cZ<}eV35@@D1TGN-PC+Kn?e<>9l&HU4XN(%JiM3xEgMR2zm{I?%ozIyS~n@>OZK|Iq0)O*>KX&xsnr0fd>J3yqZbPs#&`8}7hd7#GMLfSNwivj4KtKrRJ-sa|w4K-`6%f5&0X1qtmij>)vRp|hTzEic*_zNMK6&X;;rliuX#~kJGEv1ZrnBsz#&Rm?P<J=G9xndDf+)Wo$tDp``y9C`frM~abU8i<&`x7LpD&+@M?ew*zP%Lf>O1WgPFlUhQX9qwZ2AfC57-79J-PE0ONX}zZwg-~LiaQKcY$q`XT~UI>|H6rR_U>IX`K7G4pFGl3+<O320b2J5w>%dAw2-oIZuLXKpij!h-SIV>OVq#iptwG;vMJP*3AKU5HKBE=DqDD7a!me}VgnZmz{yb&OgUgs0)sXJcpu_K*=!VOsW`o9RloP8B@t8ob=akATqzK#il2!#H+}^Xe={U!jDrN>^+85NVST=IsUVNh`>=H)qr@1gcB}+amG6_#Ck<mX!KJL>(1J7EqlVa|lUy;^NEvpB%UH?HmLu#6Yd3D=xRn`zgyrc0t*B{&vsi`{K~`<8jsS*ND<nVU$H?((>^({wB>)AqF?FN$nJbnQm%8nszW)GF(uTu5to9gA<0SQ+{j8nMli$o%Vai;1DyN%NumiX;Yc-Ti0Zf2-BFD2f9w{#GUi?8sDtMD_SnM`jzRM&cgtY7y^|8FaUchZ{pnQ@*uZ3eDs|BdMp(V_X?j)#HrjVFsvh~A%Ut7+BPLu2VkxxG{oJat)*l{JOa;4*o<r-O$+D)a|p9Uv%5>M}dsA=u32k7!Xynj`Gz7pwbV>@W&<Mp-Z*fBGQD-)(BamhBX)~hfDOH#A20rqAS0K&jE9V}tuK}y{J<S;4Gy{_5tX%ozMwln3W>58=SgO|k1jbkBysZ?*iGXp1tG}ENCcI@``ON2xYEQzrx_R^GEE4{f8M{&4UNtIL*-4~1DLnxbMRiLl3ysGvsr#PyE{rP&=l=5^MLn;(zg%FD(ssvhg)@pm&R+Hp1sz~UC)85}C)rYsb{z~RO8xHEA>FL8_YUrW|Wbogm#}HBo+jw$alw|6*0U`FzEA`3+y0BSpo6Iw~-vugc(hFTeQgOnl3Ab^)ED}E$y}Ge73WQg*-pR;`+;sS>_i}B3C1tEhFo0yA)RL|F2?CBS4Kz2yFt1<%IyIqc1E%e$!^`e%Du~5us_uKvd9Db9CbHHn&P-k`*c$3AkO#c>ik-82=r(n2jU23`J-u5GU`Cf?c5d5!iWL}L8JVbYsl_UwM_%d~#ieEp=TCayfzdvIxcB1yy#D^KM`*d8TM+lF^{q)O5Leu)?P9nAm9%H4w&@Gd;%RQFLJxI7v;XVG3h+a!sm&m@?{$wXzJFnRL?*q!-R*}zvG*&@h1&acp9Jytbpo6EEkRAE*Xsmoc3p=(OhB*!3zFlL(6Rg&xZ2ot=2V?&rQ0>eFx}UDk3Xx3m8?Ses1+hrz9~CQh+6YV5Zt;`O;#G;z?Kz2uJEMV124|a?FzvZ&(|+GHU~Id`X!Nr>)231CBF=BcX;K|wK+fTxqu|0u8qWY-H1(dkf`K(_FfLgTzZ;21~Y2p;1yUMN^YJR(rI=2pbRu~0jw_Tr&OLDh~LBIy)X%CL7->RdJlm)>5!U{)i>11uE&M~HWBMo`vP#klMxVpcFUn#?tBaNG@7jvb|!xu>hEWvJ^7n`ObWsy(r1=>Hm{bGE8D+`DMaL~dR9QJupYWwor;wQnsB^}e@BdfU3m&0lxhdZu86j_O5~pZ+A{AK5V&}J%cpUccqaMY1Cg>y^xgo7#{!XHlVbwulXbdgg*}RXwmPD6@9ptR#-$Iw`#PDC0HVuyZE)GToP6t$!%PU4Xcst|gfaP+5U<Rlc^S5VwUZW~((Dg@E$I|?nU<y!{{?<EQHdJ@#JJcDjKz`%vl9(jnlTFOHVU3LgN@ztuox>Zcl4UfmeD(P?Wsy~ISPSf{V|pGS%*NZ;_DsaG`=M)eM>AAps&&NKcI0o!PQo^Hh_?D4|Igo|5&fy>rd2XBB<v(tgrzHW$dEY5KA2D(aJ~hg71>);BNxzL9CLy!LvoBk|mc=0*rHquahJW<fFH*28N6rn7)l%zl7x{tl<LWqAOx?KHMlmt#5<9SC+D_qJ=A^_j^i>h!<J(WZbrw00~HEDCx9;K17*SH6#Y6d1P*drCc<{yc2%kq_OjGlwysHRT9n4Z=OXBJryI8qM{F{!`*g2IuE&OjB)xz=?$ols9iIBm&%t|X|35P_XgDZ)l03fe45_V=7Jny;pNJ^KzjyL5xuWB*RYcl)Pl%|(M^A8Q#;S*gIJEDtYzKhjMd71=ok;2^9_YB65Zrn9X@Vz855>9p(lBOM?Q&gPgk<hWE*FuCdElkL61cu)ii7+e)qZ%n4!36EFy7bNVY|G0@%j|@C&RBidKkUQ9&kS=;1`&8r72%nFm0k@lLA9@$&QcU=MVVUn%?;*#Mb0ob;`D{pO=bG^QGg(Yw_N4h^pY&k_<xU!Y1_LZ7Sx<Er4{$XO5#l)B{gRx9<JCMi0A$bq%xdxQ<Qg*})77aLoPZ$^BMg+Zn&Xtv!Fl15P`qYCBN?H{=oqO1P4CM6P{cTcAo$pJCYVK|s2j1tynxieWfwBoP%=eC8-2Mu#aXx^@sU}C5bo?o3WK>GQud%B$4SH~}>EzV;Hdf&0NsDdVe%=3cq-lWA9sb4o0saFH7!mt4*12Fx!<k<#k?9-}@6s;DceDU`6o85TX8!Fa^vak76YpIU3Gr+8Ok;ud{fAHvYiQdTt^KIbcp5<$a(oN(>a$95JQkrh}MsB;J7J)0TqzWfJiEBy9d8lo-NP?dJ+JCMW_)bTvvCBRvtt79SjVU}($}IFMOn?ZmT7;gAEkuk)qplG!rSzcX3LGe5A;uy)Qu?U0uv(e(XCv=pw<OWz7Znfonlu-!xu+2jVu57dt9QVbom!f7djoVimLVK0o;-T$0N_RtI0)L!ZB-LKMyyURg8-;PF*m0`eiVnW)hHJWn8YyAfeK(K(Snn<3q_h^tg%od!(C!5C(F+6xSSgig0_c9sY&O<u(bTba|LlU<igURqYTES0R+q5Kb2A&qvQ7{)yaCTMRDNK3<8pFS?`pq6$#3<Pg8ypP0o%S!NovgGll&llN*z#LI|Z-8I&0fXgkIir%6ARlU6?Wernt8{Nw)vmq1Ba")).decode())
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
_V17_LEAD = False  # Crop带每步连续卖单,LEAD双重卖出
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
        if False:
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
