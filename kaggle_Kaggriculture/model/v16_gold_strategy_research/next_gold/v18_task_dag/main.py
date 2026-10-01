"""Deterministic market-aware full-season Kaggriculture controller."""
import base64
import copy
import json
import math
import zlib


_ACTIONS = json.loads(zlib.decompress(base64.b85decode('c-rk<O>Z38k^C<_^PpyT^J8xusl5`+8448ThCLt#1K0}#hW9YLw}t=v%4C03)r*Xb%zQ<11m0TBR@M7{nURr^KmXs!fBpK~KmYdI$$$KO^266pHy?iaeEsGA>)qz$;q>J1zy9}M|L5CZzJ2`XufP4{Z~y!4^Uo(AKRy0c`|!ipKmT(5)2AP=Z%$56-rsIdPS2XJzkJ+mJ`euzWwZJ4?d$Ew&Gr4s>BZ#hA2&C*Kb@Q|4nO~Vcl+V%`}^bnIDdHf*XgihpFh3-<JZr}H!TKz`}t(M`Evi*)}L<g?ms?$I(#+xFdm36o12^CTbI+f?jJXJ6==xtwZ~7>sXz^wyw03G*uz6h9_M5+>g(=T<XxX{uHSF0@kIUE{|E54NxR8gcmHKLo=rO*zx(O97)E{F&6M#ocZ4_B)At{j$MyZ@Zn}u3-;GxfT)Jn|MfBzN>vR#di}Mfv-Wj8BCcR@**$&QlfG4AL?BDzA-O}9u=xJvTx*nR#<8ZYv-H*cXSMGFy{f8z8?1W|oleg@~9*o&wIGP!2f1}UXZrth6jh;K*dB-7ar^#5C3*m4Bo54I<`Pnk+f;O_~(D5g4-%@=n<!}6X1VgwxVZa=D^QI5t;T?w$-_G7I=tFGaj^kc=@a~s%()&K2PI#9N?EmlJO<kYset3b$PHvT@VNE)RY2X6s^VI3t8ri<j-h!z;LVntq5q(<l{`Tf(^Zx#qKWy&qKiz!#%lJ&_G<fNk1eQqp9W%|r{?;C}$J|2)M`ZG2<0@Z21T4T;z5WC9JMH5t@7=ogU(qH3=3Qex4vcWHa5H`eFh<~>z`fcn?U0$w`!MXS*GG2%fny&qNSUhwKY0&iV}U-o4`d#JXg?PGQM<`W2g)8)$@Wz?5cSRd`6r%E&Gl7)C--sCTMjr6z_>p?vNZ<%&EEni#J2R?7kZp)suJAnnGNf=r}clDeD4DrYNdkQdBecA723mj45Ke5u=uxA@9q{MHPUg&u3G7k%-9cyw+;@h_}wYCz0$eR5F%u~bSKdJwPbA2i#9VX+>SA!$cWSAwLf4sQOkpv3<-OTF8U+t=VGG-y>bS_hYTYJ?-a`Vet@gD$G$!GclcNx!0KV@*pYV_!gnF3br?V~Lh|jq8xNMba~i&q^cn+rN-Y5CSwtBSB!)^w+E1eDRY#Ux@W$ADyuSOB)v<mzegG{Hqu6Mu4t+@u(Qqs(6oYnf+8E@4Oi%(+_@Ey;_Vm`+pd+K|Fet;3^5GDGuZ))6agFW=<rwjl2mSa&bkz*sH!#q33}(vFp!XSgLngx9KDebxy_pSfkFA14YtM4p{qFK{ySK*F8WSHE5z}gC#C*BGyWak=xx4!_uw+sQliMNl?U06f)*WtQ4Ky0Dc$fi=dPWc`baw{K$SD++y-RImAqzasWnvAjlOfg=Lzp<IQd%E}4~Hw=f1HN1?Qi74rp4sfj-k$ycQPG;<SMZG9s2sInOTbveR^tWCdAs_a)j_EaJ3_k%fN)Q(ed5_TQ3zRJC9&T>!Mw=d`KLhLcGke5s0CJj#tH*roOrd#$>J)hE@zN!R_ts&0|^&G_7`j+)dE8^YOz;+SWVz^SHNxucf0?GY1((q7!FjI@H#!ARD~nSqZP@!$gRn9E>Gj2<#t_snpw0NKFy*L$vsqdS6R0REZv@`z|$hR2%(tkunLrZ9b*(&W)8H5o;oVO{d}5SQ8P-IN(f;6AQ|_Akg`Cy3x@$JuNcZfDJSHqz?)>by@&<nmUtXd;y<iV&2YWMV$w;Wf!T4-8eS3@+~izu^KkVM9P%r=*r=(39ljsh@k9UkZo$T0bIZAI@8e##h>;D$oRUw$&DX!NWnNSmXXPZ8M}UZcFaPM?roZpXH&ftNPz)lhsaU@?E~|F?POFl;`kx>L^7J4{L+f`z;+N#FxB(PSq^J>1;YPOG=NQZ`Kc3+Y*9h~mL)y}+i&f9>1CU>A?NAJf*<^mX7<FP7r+28ZH>@4w_Rq>HTxGcc__$DI@koBK^AUiX)CW}qk&-D<T<Cb0E~I!Y>SMu0b7IN&m6K~Ky|KXeE3;P|NfCmOEP#h<q^mU-!G60-UrEDgnf`Y3-Ahi8zF(5A)&Cf3E<B{o<|~m1Kh4PgRN7p-{Hy{qQREw4~#nE%u)FxO(=vDQ@Q<$SxVVFkAQ0cuFJy&?+xA`Ki&LsxAH7Msr{v&=~n^CcU$`DeG3sfkdXCZyk-@hVzB7KumT5fD^4GH*<mGuEiZ`Mgz|HOVJIQ>bWS-caAY6N^r11_041$8&!Le_LJx6ahDV7{Iu&!HLSwn~0n^rPLlRixTEvHE%{c>e-J(YAIgX@(TKTosC{4y(TiPtUWcXgOEp(rP8^f8wJGHOOzvY}0$?;8m$R?b7u94}R^=cj226Xmf9<AOUw&KBs)jC#vhX+mzg;v~&Bu-)HW!Ao+g><H_c+68SIExza6n7tMI&8-in;hnqR#kap5UKCo9x2tV9uPG6*&s%kc60?Vd}W;|<ae4v)g10QFgrZ&oX~S)kxkuMcimNH#fTY_ey*f%@xweKY-P%xY$$cGl7z|p_;wW^Ls;#P^i)cntfT8JKe549cqM_fLJ8)f-a{3GIJ7v=q8eT=<55t+9_kB+qq;=>d)KIlqbw(jpslazf&^kifN$3L#h@X`A$6ohTB|q1<8xjtMea#xlc;gzsZik5Y2xN+Xu;03wXoS!s~)sAtWaOOwT=^XGl3+|@=jsGOehu;kx~IkD#TZStcpYsOtG62(rM4(Z77pD(}&_TK0~YWr_O5_L|}rwhGxAD*4y@+2bqw4{<QB4>Y%)uuzA}y8a5X~)-hifbwjszl?b}rN)`vn1duKsYC^}!+$>=Fs~m?MsGf2{V+?WXLuL4Efc!{fPCQ(P9#Yl~fUFAJCO=gYgUSVYTA!F<-L$m~lgiB{_iKl55o4{@OfCLscHZD-TMN_0Zm$9!ual$7$h}A+lPos_M)z$j;_jlY=xiW7)-b^kw0H6DA;F$y=wACHfG-@sf<brO)XO$RvGOk|8a;)l6hk34iim{V{Iv;KE*AcpXY0t7eZ}*_a6GwJ=MS0iKY_+TX4RhSHmuIrZ*`3x>vXQ&FQZIM(oCAVN(g%-1WkM3&D+9WjqAWZlkRaoGF)=7bGMg)oknH_OkEqO_RM)WEFg<n?(q7dqnH%UmV)T8S<Mm6VH@Jksmt3UN~c`Q2(iOx)fuVHfIP5quM=x6G|2?0&34YUzlKsB%7Gga&YK?fC>a9nqyd$h<VqhjOtSgWBjLMr-U3HuUN(oJrETi&v+JOnzGNrv1c=ZI^^8MUMl|p*;5U~M;gB|v2dT{6XQ--!b4-(fMVHZ+netzwGgZGP%~hXExM7qdZ{S&yVX7L3l-1hCq2qiTZd**)k{S8|a1ak2@P<{ROtZVXl7VFn!bV`k*B69&?r2toR!EHJA%K3Nhq$VhrDa3d5HxG%HLe(D6Vp9xB4%>sghc=~V5&#lAPy`FU+dIP&5%0C=z?v(@RId#El81Ji^~!wbGXL@*LFLg=&KkH;YUW+cZi9WDGFph8bW$kmM_!RueGRH_x!x7tRRZJXtbu%!VKY+au!Ld<FaoW=Euf7e21}snEQCzUb%xMRcrl35r;X}lO$`j(5fj25}2o%${Nhb6^sKmM{uStF3}TnIea;6&!q#=%#XnU#)BFxH6h@f6{=^Y<QXy|_M&J^ybC6&Q2RLUsDo&KNO7QD07<S<U1Yhc<HS~wj)j1jC}-~Y!NZh7GS!w)D{ac*=ZN<aDjjTi>FF#gHtlZq4I@&xeqN1quZVmHl2!tSG}-gw(6GJHQX`7lJ&e^=@q2|F(0~Xb(GVVZJESYHo?RvVA9GafNF~mZoaFJjgQi9W8PQ1#u(BbatO7}gSz80F`~#y_VV;T7_{lNb6P{q6dEALG1UHjRI93UjyY>3Iu>Ck)5xam}#~pnE#Yl`a6FA9(5sKVYc`1m)MYSQZ>x@#Jk_^tcch5)<(~fqTa1=AM$Q4rY%)$tEcJ048WLT@>cj4|o8|R|6=Ak7aB@WmaMZ)WEZILXmAS(D!m1kEoDv&8A6Do31NMP|N{e9QT%1lNPC}L6*)bENH0o9|Bn%af#v)Y1iNl@Q?b<5A#N)86273vNlg6P`BCbtuu+i4L^fsAlb3WD;!q}uWk#gp-6lTd_k1QjIN7KvUOq$9KC!Q=Qbtq8ZRtA|8kd3y4T(Mz`bHJ_Fp3KVpq91of@mG-|SJrF0L&K852Y9b&Xf|;%5;nBsw7kaj>L3&l|C8(}=+|@o4T&%V|)U9eiv|5WD8cIEDBI+nf74~oq&jQ&8Nk%>!SkXhwXBx1nS86)=OQ*{alW~+5ufA@2G`E_g5fdV<t%w|yaP|6F0z5MV-TWOP0gPM&!Tbi(DAhy-j-6-c!=OjOh291O_w_;$rM!lu53g6JC<{FhXPq+2_0clo*{3pJgXJoO>v$-zlS&&{q{_fBv|-OdZ}HN@H=$uZf2icA#Jsf7t_8^&8rwcl;DOABRCT~uC*zsOPz~B4KMu$E=|Xl#4*as~?`0hD3^zs6xv3SxR?~n)xy;N|GmQ|qkQ_2XCUcOM^Yg@LD3B-u9A~)`T}pcjOS~*Y(KlVIN2DHW>@KC$siVzPAlj@V4nFmkZN^OuE_>2VUaSm1;35L`aE@LeT_T)rAW<j);Kf|F=S#3}g1WCXc6-sqD|^<^ZLB6(As2pzAa1fEV2qQkuvxsJ#ZEJ|4T?l<5UI;E;vF3^p5R`jX}7CoT&?g)btB+)>*@MT_+;?zVgN{9+kpZCQXT9Hp%mF8R6o@drSnFiRBXx@W@z=$s2@UUvei8RB0hTFfeU(tD=zBtUDSrxw4j_wQ`U%76!65Tt2BOHLa~yZVr-xt9(bJ+O;$%lEYpd?QciW()gh@GgghYrD0Sd3iWF&{E5@WB?Fg{Y=+m;VqB+Dg`p-PWs7HTQY&*3iDH4*VR9~gp>am`XKqO*A4Lknf(|<;Kv^eYCcFY!kDiu6XTsyZeFKdbUU0Dw-%H~zVtU+f+(p5Y<`0Z3Se>!}F*K6mcIBm95O>x*Jz)nZBi;YK2h{TuH>JDp>qV8$*a4cdHy>lQsBZzi^brUBNvkPNqoW0gSe2%VP3dwUVbJOtd7m4@MZ8u?Qz$)?Htur3fu$?CuA1_3itb16JTA-fZEVVXT`_n5z8log8+3_qo<oVj2%6E7R3Ru8W`gk&LU87#}dXbwR<;|Jfh(Rld+n`Sg?dL?2`P{ef$sK)oNG&Oy<!@<XBS~ceDd>w9P?-OKdO;Ni*w*G=eJM_k(8~baOJl;`RFcqQEK<UDA<?HK9C4k?mG>Z6CWabzCor`EL8UzeaIRTo4!;Ic{}v-<J}E%K7EhQSw~Tm@5+J~0^8h;QLj{RRM{*?zlNr&?OJ_A98M4B84`HA6Ohg$wun>lqx!IIg!&m?u?H6Sz0KY<}DA3y1b&3K=E6r&03wn4}_ZB+(eh_e@M-hu6PO=N^{avZRDV8J5yU$q-w|0rObl5l}z~`~{D3C`5(zmf-MSL|Xb?8o~WW9?>TC1bG<q0@BzGQ*tqbQ;wGJ61IqmGQXCUs#X-vOdJxS`k$2Oh{@lXduXl!C7ws-G0j{MRk}#bqY59^n~g0jl#EC&;ba7E#y)P6!Fsb4<sJOlh>1-Lu#FPLdX2kU%2TdkmFKyaE*yMK6PpHAFE2p4h_nqkK@T1n*7+zi9ds_&uY`BpMDOAB{nw6`0ocMkJv@C?e_?M?SRFy42y18Tu@@AJ#?9ZVp<ikYF$4ZhK}zX}&;zFItmM37)&9Z#)JKTe2nrg!-ahhnuIVWqu2&3=NSn(@HI=lmW!dWsvJ5PjCq34KdP;RQ{;36L?VP)MAymY79n&(#A*;39c=hBuH;{x@0WjRVSqGY-Q{-P_Oyyl_e6rqM8pJYJ#*X)T5;vb?BK{)D=Ps;CzK5n{sK0j%6l=amq0lq!cBU^P=U32ngCNg#{QSqnD?Yt9)o`bcbWDlqD_!FY@e2^w5JhsC%^_ppc1;hW0|D2Q)#6Ng_}WP_3w#C{t-Wz~l5%Jis#VsJUKp$w#bih2|Z{1ywc00fJb7=n~H*QguYbO7Lfa>?7VVO-w@Nuf!Wp)`*(Q2YR68{-zsE*2p+0fj6718r?NnVI85X#44b)e^X^}Wq<Qs8dK3~lBg|b?1upy^Y10xuTvr_U?>7<d=xf^Ppi9Mt`b>z{P3i83|L{s^sc!SR27xfDeAFvZ5UO{1GYY^zezPpnMCA<0C4Nhl9v`Vw@!CED~zdRBt?6-Y+%(@$9`q1dMY30t^C=f5>3*MUJe*KUY)O_7>L8y;`G@jQ)+S~c1D6mNKb{rr6f`%Ib8hF*lLTAxI|w)$L50V>_Fj4VnI%&Q!&`7$R&FDM;@L)!x1iYlw(LO9y02T#3>Hse+6+OW!6p$Srs5<s8!06^0ts^(%RyjJsAi92e@HwxgAOEhI1k`7!rhYH6`90KaAIUXq|Z+!lnw>n#jep`vHoM<PM6CWI;FcT<C_h22npOPK8+2vCG<9Rn}gix(JP&)s`NrZg-J96B!K(8!j3YsP<(|*Z}^F0X#rlnhwRD$z7zRsus)KoO#-U2IOip$ECu4V)l*G9a;63GA~>T7ehD;^>W77^P?9nbvmNT!jstT|K}y2PtUDR<gD|wuoI7aXc9dvI@O1MR}ij3#pETRajS_4IIOg;WVDM&#vdaOvD81QMxs2KiZw=ZLu0+swBCfgwm$ue$qQ+PhbYuM{e7|<v!-vJtp!rp%jaswOZ<#_xh}OlsX3IX0pyy79Y|rVI+2?+sq(z$EEJpv%jT_#+^xv)R;qdY3I&lEU^I4Zi-n&Y^E9EJ1U7?aWC7^G?`m0IiAe=p847A`ib_=%mQgj~Xvhhe0lYX)lVWM2?$m;_UO^6%v(FY^JD*}PCwb_i$bowVSXdWbn(hE{nNJAM6NN6$Ig{(PYS;`jw@u=>n7wE0Jx-LOy$TRbL`h<UIq5OuAbJ`uy+V;By5U0bUPPliMuS%goW@Gfs%<m>C4+5nMBYcp*}u?QF;~dA4_dM(UCciACbE}lvUftvi%FQf74NJwTL9|Vcq^JuIzg7#RQDL8-0KqjZ<bWc8boR?lk(CDvAQZ1Ydmr>auY=V=g?99o)C-|EQdw8OVBD&bMbm{muL&MG+zH;b?#mzeNNV;!nXwpRu#2IxAT*f$_1w@tPfn~OU;a=HHTuO;DVDh9oWINSsg8#xD-KITwfvx)t}e+Ab4xEet3_9Zo-c}%QD(?mK2A%jxB7(gp+s<n;N5ErN}T2bAn}4coKP*RhMFooTv63zek<2LKL+jG{a={*1awmC?==%GM7WFwWbmd*14_4>wp1%x2_N)R_mTw0Y;fe2SKn4fM@qtZb`zq5{eKp^wYS~fQufGj0zD5TINh()#@|H=~}L$<7U<%JO#5fsuDY$h}Py@Yn6NchDGHkIM}~0lD0ak3o)pJfl=W0-&Z}GYu=uo?}&>CV5*l--0;)BoyvE&_j+;NaL<|-8Gsr(J}-p>qv82KIWkLu3_BY?Yh;uT+QZlQZiJ-ERLoRyoOgzq+O*p)8`|tF*wH*03pJS@bu_3_wu|OQ5=Y8eUW-8aw(qPYTOXd3Nh24?+4EDQa*Ut|A}A3Vj3DyjT_oH_;m|A#N>@Ij1Hs_F#Y2ftm7GJDX+@)TQAl%D(sg5tDO!$Mm<~DL1Y9W0((^RF0>9)1gxx;cnR)tB^s5l~6##^yeXJYnN-|e89g=d@r8KZEGt!=b0fb5|1kaqV;2hc8sZGR|RvY6c@_YhKqrDF<Ox7E1uCq`4@LAZ^x=KYVoTb9G!c;sw0h+$c<*zUrV!H-;KZT{*2V_zTg@8DjT%dqxcV+V1*Qssep%s++BV&K0z-2XsB}T>r5L3H08T#a<O46blk8a%JibJ?m(T;YGfdZ_Y16hcaXU5NTr)x{0Yj|13skVN4Orn6_c_GV+)J;UGje>Z(maZv{SV+z*xH(xpMp|fqqFZD*_V8~$D^Tz4GJ@$-Ct6F<Zm*I7CM={#cI^6DBu$bq5)nE)&;~ScW~$j|pHLRfFE|88Ky;=Y%Mn1mH28=u8R(6nh_{&&-2|6}56AT7Cvy2|sg!3-8m<F8D1eqOR_m4xay{^j=se4i%M-xz{}VfMDUGsq&6Rd4$hyeLHa>xIX^B-t)8;CIF#@F2gAgSIRZil`i@`)S1{1h7MHdrLwtDNf=TxLpEITS0CC2mn+Sv32H^~sv7Af9{yDc4Ueh#}5Tw1TvUYcEHZHqM>gxYkByU<66N?NTf{1U0qQ6L8Z^57yglgj|^sa0e2Ma1x2XQ~UViqNN0NyIyQ*m}?r_I2<52f$CiuAe_Mt~r>{p;{D#nc9uI)$?wS-EA0Y`!5_{MeSp3de=E(-j?^4*Z1{HR&2VEdII2+#QhAzjGc&ibsac#m^e{L7HT)47`SC)*QAqt89Aw>dTB&djG>6G97Y0C&aPsu@)3(XiMI~8W0Ub*ZAk+pDhPjYD~U|GHAYFBFCDug%ZrO0m^UyaQ%G_tvCUfvkdz=&3(K_{G$&BHMo{S51m;%e&ubM*Pi2g+weCR9_95WG0AJy+jQnCl#hLPTG*MlXQA;oochz8&gz)wZ_jKmHzpK?R1bv>3uYrcqEk;A3p1I#B1^rJ}Pat{jac<Kt>Ys@T06{FS%;gIlvnB>$Q=n7g<hKk!WvC8Q2vX+=AiVr$dmtzkB#X;ck~uVnRnl_KRRbl|;r1K|;KnMnHf<n!!?3vyyH^@zx|Q7EmA^<CY%68g!k{-{P$-r4{EY5UP|K}zNV}!g+s%>@c!>!&y5oV3#KR(PgvpvwCxQ~zXv!;PS_;Z-%e;r<Y4~Yvq<M7`Q*9Bf9nW25cLlhnQevU7luhIOi|Hl$yt!BpR(akSp9re#<cAGhphM^XEF!EhMp;)2QvfoU$!HDfBq<7ke!W{slEle?EtSQ}PMf4TaKQ3;)<-+L%@cek@wv$wexU@{VRpcNcmewNf{CoJxB90OlxE&ap!(;t5Yr;GgP_29xbmlU)aQzS26W>ko>?El*i320A<Lss<TDDjS!XH*j})n=zN9gcg2Dnx2*N*0bH$vR%n=TmJ5$_G&9NOrA;l2K=rTpgaR;Hj+o`ZiTz==g$Pe>&rs!~anUaA(@VnWlVRQm1JngHrZIarYQoOgGT21@O<iF<TX%haIRJO#_Z1;ZIQHqRFzNieNcQ86xy!s?vgeK`MK=;xX7J~|eaP_uS==t%sUv?#Z(ZqOk@nJW;lM-&wl1YoRIl7GwIKiqYm$IJUrLI6sX%ZB*_Rcw5$##wDzUOI|$&?LIAvM#$Z)I_Tb)GQ7EB6qHQtLkrRA4e(I^*zSjy0gwh^5m!<-!4&(J7C-t>0JSZZ_OntUqY6z$BVq2TanP*eF`bH-uQ<p7fbGcys2Dhw;g_l=N^9UID;zS!RjJIKuaoXzQ`wyH_urLz%CC2~#1@_Nto--zz9+DsDpeyq`m}kMV?S*d$j`>!Qu)_6|iseKL-Fbu9y~BEv;t^~6BM7p?lAPjY+L3;CoG8Jq(eDO#b(^Cd8NT-dHT!;$YJ%$A_UcNR)uZT17K!^5&yNH(jheK=k@t4ty)&%AUs^ZknVIVK;6E@(nGXRl;yv_+2&9$-+&6M+g|T3RP9=(|y5)Ep_M+%Qs}F#V%V4YJ!F8%2`EYN2YIlqzMc_^c1ZifO4{2^60;+(P7v8kj0LD2c(9<S&)1X}LgZ+crPVU968<=?-*VSAMXA!spI`8>)}&LvMMH98Mkq+&D<6R{&6Im!@SFQKm4B3~Koy5-UzHPE?AUnO@fvaUJ;SM2f8~F57Cl+0c@^3Kdd95&&9R^*)wZJ8i;tS+b16-;2(gHR7+eLM(OaV1u?oR-IZ0R<6gBksPa6e+^|QxSyldYYT;7LtRf*OAT35Vx?CXQV|QXyR<=;9}%nEAg0*_N097!r>Lq6`)oIQOs*F<kyk@yLeMmK-p2?v9$LFzo${wz^Awwy+aLO>fXBTgKoOE%2_-TxU_=5Q14)A!*(taF#uJv93W#!VV#|DQr;J-D9vaN)loZ~^7PVdYFD1cPt+gB~GAeoM6i{^O2e}H`VK>dmgJD{{t_M^t1|W*wFhwY*5Lsv?Iq8PlyrYG`-3V-_%-Sa^0CagMEUFUyu?L0`OzU-WuOIjRz!&8(o0LJ>IJQwP1*t;d*Y=E&hN5gE(r;BC%+uxv0`-Ik#B7mP9ZaCZCf04PzCgPrTTT?K6cNbgeU>c4QP#t*GUlqG{F=2k0n|An9`0#C>kJ~&PKXZZ*fLA!FO!kz!OdFU3T%j|faIkf>Iq}K<|nkVR}TplqzpZWUhMtca~+t;{s2!`du){WFj^v#Ehr+){4(mDP<+snRPeJuf@=WSysR9CYnKx_8h37)SS2oI-%?R{$}X$@rkpy?j4=j{B7)XKUWbkaJS@SHGCkm9lctv1VkaUT*5s^t6dE;$o@lZpv(TNya#c{QBp1Y@m-1QVNgS!5L&)j!2oqHM)cenZ<(<<jatbQYJ1dMEXalLL=F`A|Rk16kNz??Jooxzz#eGXgklOysY4p0-KKKrlGS)=FSwXWdP4i!n`_R2vT|RsVt(rn)G){3z-Po3%Fmj9E86K~h;}Z2A0~hh+hzz=~0Tf!Qi7t78(c8%vlPSHQq{cI0EKdV19r0HUKt+`;#u4>+RI<t7J1ca;Db3Vtj{9zMdO6VvN{Oz#mqv-@f+y8J!!=GyiTVx&c`dk10W)sEsBO%W+<T$Lf$T8rvd_I1^sS}%kqHRB6&z4(M8PtQ53o>@<$2%9vn^;nqd?lshr8R)ZUVch;3f*$STJcjA|g^(9g+6Met7|>;7xq?pQ*3A8RmUGECc<67-`&PL;=Bug|HqD?*u17(F}iT*b-?@KK$$9{{aJKcGv')).decode('utf-8'))
__version__ = 'BL-V17-R1-RC2'

_PRICE_FLOOR = 1
_DEMAND_ALPHA = 0.25
_HINGE_GAIN = 8.0
_MARKET_PARAMS = {
    "WHEAT": (25, 10000, 400, "sqrt", 0.8, "log", 0.2),
    "CARROT": (35, 10000, 450, "hinge", 1.0, "sqrt", 0.7),
    "TOMATO": (60, 10000, 200, "hinge", 0.4, "sqrt", 0.6),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.7, "linear", 1.6),
    "MELON": (250, 10000, 300, "log", 0.2, "sq", 3.6),
    "EGG": (50, 10000, 332, "hinge", 0.4, "log", 0.2),
    "MILK": (160, 10000, 122, "sqrt", 0.6, "linear", 1.6),
    "WOOL": (200, 10000, 105, "log", 0.2, "sq", 3.2),
    "FERTILIZER": (100, 10000, 200, "linear", 0.4, "linear", 0.4),
}
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
_SELLABLE = tuple(_MARKET_PARAMS)
_LIQUIDATION_ORDER = (
    "CARROT", "EGG", "FERTILIZER", "MELON", "MILK",
    "STRAWBERRY", "TOMATO", "WHEAT", "WOOL",
)
_WEED_STATE = {0: {}, 1: {}}
_WEED_REPLAY_STEPS = 8
_SHIFT_STATE = {
    0: {"last_step": -1, "due_step": -1, "due": {}},
    1: {"last_step": -1, "due_step": -1, "due": {}},
}
_PREEMPT_ENABLED = True
_PREEMPT_FRACTION = 2.0
_PREEMPT_MAX_BATCH = 30
_PREEMPT_MAX_CLONE_DISTANCE = 6
_PREEMPT_MIN_PRICE_RATIO = 0.0
_PREEMPT_MIN_FUTURE_QUANTITY = 4
_PREEMPT_START = 120
_PREEMPT_STOP = 680
_PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")


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


def _shed_access(size):
    half = size // 2
    return {
        (half - 1, half - 1), (half, half - 1),
        (half - 1, half), (half, half),
    }


def _projected_shed(obs, action):
    farm = _farm(obs, _seat(obs))
    private = _get(obs, "private", {}) or {}
    projected = {
        key: max(0, int(value or 0))
        for key, value in dict(_get(private, "shed", {}) or {}).items()
    }
    inventories = list(_get(private, "inventories", []) or [])
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    unit_actions = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    tiles = list(_get(farm, "tiles", []) or [])
    access = _shed_access(len(tiles) or 10)
    for index, unit_action in enumerate(unit_actions):
        if index >= len(positions) or index >= len(inventories):
            continue
        position = positions[index]
        if not isinstance(position, (list, tuple)) or len(position) < 2:
            continue
        x, y = int(position[0]), int(position[1])
        if (x, y) not in access or not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])):
            continue
        inventory = {key: max(0, int(value or 0)) for key, value in dict(inventories[index] or {}).items()}
        if unit_action and unit_action[0] == "DROP":
            deposits = inventory.items()
        elif unit_action and unit_action[0] == "PLACE" and len(unit_action) >= 2:
            item = unit_action[1]
            tile = tiles[y][x]
            structure = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}.get(item)
            if structure and isinstance(tile, dict) and tile.get("kind") == structure and not tile.get("animal"):
                continue
            try:
                requested = int(unit_action[2]) if len(unit_action) >= 3 else 1
            except (TypeError, ValueError):
                continue
            deposits = ((item, min(max(0, requested), inventory.get(item, 0))),)
        else:
            continue
        for item, quantity in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(quantity or 0)), room)
            if amount:
                projected[item] = projected.get(item, 0) + amount
    return projected


def _public_signature(farm):
    keys = (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "COW", "SHEEP", "GOOSE", "PASTURE", "COOP", "WEED",
    )
    counts = {key: 0 for key in keys}
    for row in (_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            for field in ("crop", "animal", "kind"):
                value = str(tile.get(field, "")).upper()
                if value in counts:
                    counts[value] += 1
                    break
    return (
        len(_get(farm, "hands", []) or []),
        len(_get(farm, "unlocked_quadrants", []) or []),
        tuple(counts[key] for key in sorted(counts)),
    )


def _clone_distance(obs):
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) < 2:
        return 10**9
    left, right = _public_signature(farms[0]), _public_signature(farms[1])
    return (
        abs(left[0] - right[0])
        + 3 * abs(left[1] - right[1])
        + sum(abs(a - b) for a, b in zip(left[2], right[2]))
    )


def _shift_state(obs, step):
    seat = _seat(obs)
    state = _SHIFT_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "due_step": -1, "due": {}}
        _SHIFT_STATE[seat] = state
    state["last_step"] = step
    return state


def _repay_shift(obs, action, step):
    if not _PREEMPT_ENABLED:
        return action
    state = _shift_state(obs, step)
    if int(state.get("due_step", -1)) != step:
        if int(state.get("due_step", -1)) < step:
            state["due_step"], state["due"] = -1, {}
        return action
    due = {item: max(0, int(quantity)) for item, quantity in dict(state.get("due") or {}).items()}
    market = []
    for raw in action.get("market", []) or []:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and due.get(order[1], 0) > 0:
            item = order[1]
            requested = max(0, int(order[2]))
            reduction = min(requested, due[item])
            requested -= reduction
            due[item] -= reduction
            if requested <= 0:
                continue
            order[2] = requested
        market.append(order)
    action["market"] = market
    state["due_step"], state["due"] = -1, {}
    return action


def _future_sells(step):
    if step + 1 >= len(_ACTIONS):
        return {}
    result = {}
    for raw in (_ACTIONS[step + 1].get("market") or []):
        if len(raw) >= 3 and raw[0] == "SELL" and raw[1] in _PREMIUM:
            result[raw[1]] = result.get(raw[1], 0) + max(0, int(raw[2]))
    return result


def _preempt_shift(obs, action, step):
    if not _PREEMPT_ENABLED or not (_PREEMPT_START <= step < _PREEMPT_STOP):
        return action
    state = _shift_state(obs, step)
    if state.get("due") or _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        return action
    future = _future_sells(step)
    if not future:
        return action
    market = list(action.get("market") or [])
    if len(market) >= 10:
        return action
    remaining = _projected_shed(obs, action)
    for raw in market:
        if len(raw) >= 3 and raw[0] == "SELL":
            item = raw[1]
            remaining[item] = max(0, int(remaining.get(item, 0) or 0) - max(0, int(raw[2])))
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    shifted = {}
    for item in _PREMIUM:
        future_quantity = max(0, int(future.get(item, 0) or 0))
        if future_quantity < _PREEMPT_MIN_FUTURE_QUANTITY:
            continue
        base_price = float(_MARKET_PARAMS[item][0])
        current_price = float(_get(prices, item, 0) or 0)
        if current_price <= _PRICE_FLOOR:
            continue
        if current_price < base_price * _PREEMPT_MIN_PRICE_RATIO:
            continue
        target = min(
            max(0, int(remaining.get(item, 0) or 0)),
            future_quantity,
            _PREEMPT_MAX_BATCH,
            max(1, int(round(future_quantity * _PREEMPT_FRACTION))),
        )
        if target <= 0 or len(market) >= 10:
            continue
        market.append(["SELL", item, target])
        remaining[item] = max(0, int(remaining.get(item, 0) or 0) - target)
        shifted[item] = target
    if shifted:
        action["market"] = market[:10]
        state["due_step"] = step + 1
        state["due"] = shifted
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
    if step == 0 or step < game.get("last_step", -1):
        game = {"last_step": step, "active": {}}
        _WEED_STATE[seat] = game
    game["last_step"] = step
    farm = _farm(obs, seat)
    positions = [_get(farm, "farmer"), *list(_get(farm, "hands", []) or [])]
    unit_actions = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    active = game["active"]

    for actor, transaction in list(active.items()):
        index = 0 if actor == "farmer" else int(actor) + 1
        if index >= len(unit_actions):
            active.pop(actor, None)
            continue
        age = step - transaction["start"]
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



_V17_R5_MARKETS = json.loads(zlib.decompress(base64.b85decode(
    "c-p;M+is&U5d9aPc>von<S}hoHCozKq*c_7M*IJNu~cDG40E%AN|hRs_<}v>%$Z|fuh;D1<MZ!ZcY6AGe9!Xi^4uKy|D}Wcnmr%8CKEn<H9x!_Uk+{G`tfw>+s+=JpPS|_%iaGk&Q0^wKYnT2(`%ORCXa_H?7oNTKV7qP)3)E=?(x1X-k166V)@@_J}dP%ywtCzdq1|vKTQ|B_jH|S+f>1*FMK1(wk5C)J+KpJyHx#R$wGv?TTULI-@C)*q3OEMuYj0sUBuM5pQ^e^Tl*5$h?vO>bLbk+X1ca1(@YPY#7G!#xnpQ4A_!J^>EuBSth-X^Mss0J04yE}Q{FBs5@rl~CvSW?o!TJ<AZu{X0qx=SX|&m4I2dGIn8EsaD-&W=t~BJzav|WD=-=ZUY59SYsmdzy3%W;fI7<X0I(8+b6Pvb+6z|e08QDEET{PV$?SP|i4M|P213nE8;_6zUzA1~P5aLi83L<U1D1&bp<mK4@9!m=C7$K9?AwMl&lhHG5*?kgEg}S;D*^(eCd>wC{-U5O^Ld_5hQATi?WCpCEm8XZ<F|+eTcV&><r$Y%-z@fW1>(Bv1px-5-goHiCX{F5GYrn9hifb{O>C;Rf-4ug(U?`sCw$h-23djb=Z4oPofDqyrCnZ7srio*dq*M(=D)=zTjnYE0N<!nrK`IK^cA8gHDEje!?qLHZms~zs5_zQsAzQ6UI&}I96hR%d$AW6Y9=X8Uq)NmUf`fFCt%{Uk?F~?xsMgk|oX{~VLL^=&>5zV(c&JTsQiN-Zt5BLMc8E?lp$ZcU3l;N^d%QWzVWQe0(PG>NvWRF$<1{2pw3sB*uT8aH4J`9>!*WBHO|cy9n26;H9GZSHI;-eW>J=5=0$<F)GN*3+o*gXqmSapihqFzc7^gX7G*ht~47}e)7e(cDu4IaL28JK(lf;)L6Jnf7H6#+l)UC)TcrTuYdNGqe@wNp*zdw@mohJ#ef><v=t*HjXfi4P(zGof`I}>W!lGQjvY(5)#2b38yRR{E$E*@t!GMf9DTq4Q}1A=p^VC|{ol*~%G75Sq)f<JiOSIl>|QkF?W{ou5@78f%)Ixkw}*kTLkNufIzot4(w(lbh<$i5VBjD^)VmH^z=iye_cM)HObAM6n<cZwPZChjhaz`?4*Y*c;6TX=kZ#!-P?Nrx>uFdDx)b3!Sno*}jiU?W22@0t0>xHXiBB8=byze2@Z*QkAy2B<J@wozf2&B&mGx;#PD@M`T*A)Uxj5w70E_$!tJt=E%N&Glo1n^=PE3G8huMlegI_~GOr_}w%-qt75L@Q2!X7-|Z?8`F7CC5C5J@(sHPuJ`;(VI@-@f3+!o>&1&9#GwiHj_PYDgRMcQ3c8XkF$C?o0KlYLp)wKfSDu*5C^L`9ud{Ed-W|<Uk^;zC3Q~wY)ceKkvYb=w8iXKu6u+P|tD)`6s8S!Z^Yma0IWGhPHTh5lz5xRsba$8T{m&A*!4L2aQC`i0!$X7wxuFpL0hMf{p8"
)).decode("utf-8"))
_V17_R5_ITEMS = ('MELON', 'MILK', 'STRAWBERRY', 'WOOL')
_V17_R5_FRACTION = 1.0
_V17_R5_STATE = {
    0: {"last_step": -1, "target": False},
    1: {"last_step": -1, "target": False},
}


def _v17_r5_signature(obs):
    seat = _seat(obs)
    farms = list(_get(obs, "farms", []) or [])
    opponent = farms[1 - seat] if len(farms) >= 2 else {}
    cows = sheep = 0
    for row in list(_get(opponent, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, dict):
                continue
            cows += int(tile.get("animal") == "COW")
            sheep += int(tile.get("animal") == "SHEEP")
    return cows, sheep


def _v17_is_r5_family(obs, step):
    seat = _seat(obs)
    state = _V17_R5_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "target": False}
        _V17_R5_STATE[seat] = state
    state["last_step"] = step
    if not state.get("target") and step >= 24:
        cows, sheep = _v17_r5_signature(obs)
        if sheep >= 4 and cows <= 3:
            state["target"] = True
    return bool(state.get("target"))


def _v17_town_demand_at(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 != 0:
        return demand
    town = _get(obs, "town", {}) or {}
    for shop in list(_get(town, "unlocked_shops", []) or []):
        products = _SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += 2 if len(products) == 1 else 1
    return demand


def _v17_pickup_reserve(action, item):
    reserve = 0
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    for order in orders:
        if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "PICKUP" and order[1] == item:
            reserve += max(0, int(order[2])) if len(order) >= 3 else 1
    return reserve


def _v17_r5_counter(obs, action, step):
    if not _v17_is_r5_family(obs, step):
        return action
    future = step + 2
    if future >= len(_V17_R5_MARKETS):
        return action
    targets = {}
    for order in _V17_R5_MARKETS[future]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] in _V17_R5_ITEMS:
            targets[order[1]] = targets.get(order[1], 0) + max(0, int(order[2] or 0))
    if not targets:
        return action
    action = _copy_action(action)
    market = [list(order) for order in action.get("market", []) or []]
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    for item in _V17_R5_ITEMS:
        planned = targets.get(item, 0)
        if planned <= 0:
            continue
        prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
        if float(_get(prices, item, 0) or 0) <= _PRICE_FLOOR:
            continue
        # R5A moves this base sale to step+1 only when town demand does not
        # refill the product before it acts.  Counter only that clean case.
        if _v17_town_demand_at(obs, item, step) > 0 or _v17_town_demand_at(obs, item, step + 1) > 0:
            continue
        existing = sum(
            max(0, int(order[2] or 0))
            for order in market
            if len(order) >= 3 and order[0] == "SELL" and order[1] == item
        )
        available = max(
            0,
            int(shed.get(item, 0) or 0)
            - existing
            - _v17_pickup_reserve(action, item),
        )
        quantity = min(
            available,
            max(1, int(round(planned * _V17_R5_FRACTION))),
        )
        if quantity <= 0:
            continue
        current = next(
            (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
            None,
        )
        if current is not None:
            current[2] = max(0, int(current[2] or 0)) + quantity
        elif len(market) < 10:
            market.append(["SELL", item, quantity])
        else:
            continue
    action["market"] = market[:10]
    return action


def _shape(name, value, scale=None):
    value = max(0.0, float(value))
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log1p(value)
    if name == "log10":
        return math.log10(1.0 + value)
    if name == "hinge":
        if not scale or scale <= 0:
            return value
        normalized = value / scale
        return normalized + _HINGE_GAIN * max(0.0, normalized - 1.0) ** 2
    raise ValueError(name)


def _market_price(item, inventory):
    base, equilibrium, scale, below_func, below_target, above_func, above_target = _MARKET_PARAMS[item]
    if inventory < equilibrium:
        amplitude = below_target * base / _shape(below_func, scale, scale)
        price = base + amplitude * _shape(
            below_func, equilibrium - inventory, scale
        )
    else:
        amplitude = above_target * base / _shape(above_func, scale, scale)
        price = base - amplitude * _shape(
            above_func, inventory - equilibrium, scale
        )
    return max(_PRICE_FLOOR, int(round(price)))


def _is_sell(order):
    return (
        isinstance(order, (list, tuple))
        and len(order) >= 3
        and order[0] == "SELL"
        and order[1] in _MARKET_PARAMS
    )


def _impact_score(obs, order):
    if not _is_sell(order):
        return float("-inf")
    item = str(order[1])
    try:
        quantity = max(0, int(order[2]))
    except (TypeError, ValueError):
        return 0.0
    if quantity <= 0:
        return 0.0
    market = _get(obs, "market", {}) or {}
    inventory = _get(market, "inventory", {}) or {}
    start_inventory = int(_get(inventory, item, 10000) or 0)

    # Exact 1.32.7 per-unit market semantics.  Score the revenue lost if an
    # equal-sized competing sale reaches this product before ours.  Sales at
    # the $1 floor do not add supply, matching the environment commit rule.
    def sell_revenue_and_inventory(start, units):
        inv = int(start)
        revenue = 0.0
        for _ in range(units):
            price = _market_price(item, inv)
            revenue += price
            if price > _PRICE_FLOOR:
                inv += 1
        return revenue, inv

    revenue_now, _ = sell_revenue_and_inventory(start_inventory, quantity)
    _, delayed_inventory = sell_revenue_and_inventory(start_inventory, quantity)
    revenue_after, _ = sell_revenue_and_inventory(delayed_inventory, quantity)
    return max(0.0, revenue_now - revenue_after)


def _demand_per_day(obs, configuration, item):
    town = _get(obs, "town", {}) or {}
    shops = list(_get(town, "unlocked_shops", []) or [])
    turns_per_day = int(_get(configuration, "turnsPerDay", 24) or 24)
    shop_interval = max(1, int(_get(configuration, "townShopSellInterval", 4) or 4))
    demand = 0.0
    for shop in shops:
        products = _SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += (turns_per_day / shop_interval) * (2 if len(products) == 1 else 1)
    if item != "FERTILIZER":
        center_interval = max(1, int(_get(configuration, "townCenterSellInterval", 24) or 24))
        demand += turns_per_day / center_interval
    return demand


def _order_score(obs, configuration, order):
    # Market slots are resolved completely before town/shop consumption.
    # Therefore same-turn ordering should optimize only the exact revenue lost
    # to an intervening competing sale; cross-turn demand is irrelevant here.
    return _impact_score(obs, order)


def _rank_sell_slots(obs, action, configuration):
    action = _copy_action(action)
    market = list(action.get("market") or [])
    projected = _projected_shed(obs, action)
    # PICKUP is processed before market and removes inventory from the shed.
    for item in _SELLABLE:
        projected[item] = max(0, int(projected.get(item, 0) or 0) - _v17_pickup_reserve(action, item))
    remaining = dict(projected)
    rows = []
    for index, order in enumerate(market):
        if not _is_sell(order):
            continue
        item = str(order[1])
        requested = max(0, int(order[2] or 0))
        executable = min(requested, max(0, int(remaining.get(item, 0) or 0)))
        remaining[item] = max(0, int(remaining.get(item, 0) or 0) - executable)
        scored = list(order)
        scored[2] = executable
        rows.append((_order_score(obs, configuration, scored), -index, list(order)))
    if len(rows) < 2:
        return action
    rows.sort(reverse=True)
    ranked = iter(row[2] for row in rows)
    action["market"] = [next(ranked) if _is_sell(order) else order for order in market]
    return action


def _terminal_liquidation(obs, action, step):
    if step < 716:
        return action
    action = _copy_action(action)
    shed = _get(_get(obs, "private", {}) or {}, "shed", {}) or {}
    planned = {item: 0 for item in _SELLABLE}
    for order in action.get("market", []):
        if _is_sell(order):
            planned[str(order[1])] += max(0, int(order[2]))
    for item in _LIQUIDATION_ORDER:
        available = max(0, int(_get(shed, item, 0) or 0))
        extra = available if step >= 718 else max(0, available - planned[item])
        if extra and len(action["market"]) < 10:
            action["market"].append(["SELL", item, extra])
    return action



_V17_MD_MARKETS = json.loads(zlib.decompress(base64.b85decode(
    "c-q}u&2HN;41O1%eF$a8KgYE7&|qm(xE+eF5cd9Wv35zD*d`^CqMcws4}~q$6h(ggNK1Ktf6wl>eV6&1_s`9*w?CW5?Zal5<=O52HOt-P^7DPyJ)PZn?z+2=%dhv{<|WJP(dCD3w|~rX_#Xb$@9%!yzMP(@{Ku{L?77?RP8W;Mi|2pD!)`o|9ty}%tG{pce{}uJcDMcA^`CQ~ro2YAjxLauC7d^zU&-~VZ|yM$gOS7BZu)+2w_FyQ)1Hfl!1^@R;SD$Al-8fR3}dLlBN`-gK2G5IrQf{XbbbGJoCWzV^Z^_aFgc;IJln`Up0;O#m5Sh`gEKtYWWV2?dD(9Bc$eW~osZ9*5=%-N1!V0Lt;~1^U5ZMWnLriY!%!`K5R&Z?mS=@@%z_m@;bBxiY<E8~!&_MRJW5Jj892ATz_Y*9PFk3NLc|UB@(r=B4EVJ$ty1hmD2B?|6EhYhT9ux-Mhh#W;grG#dDJRs2i|a6t=jX${3AZ;l%#kF8qDz|qpJ{>$ON%Q4=M(02|!O~XkJW4Y=TZCp^9M&E{TNh>5U?)4~6r?1p7@qEFj+%-XJ7p!4|f15boIt6nt_9VI>%B?b7Ljd`V~vH9i7yK6r<pju8npJE+c|Y69|dl>&6U&vNIGXB#}S@q~ewiwh-6c6reH*~r?+RIOnkA!1xSoT3e^mBLS0gcqfcnmf5_JpxX<v~OY+9%a>$+GL_{)p$soy7h7_YZTJJ(YGooHbN!hiy)S7F65lJQ~_!%6Rw}rKbWU@Aoyqpg<11sdK83N+(OYRZ!NXVO6o|A$(j399*GLgXMUhGdcfJeVU)lSyN7+Sow{0mxx_%jY#t)URFq3Vt&qUQ8nc?@ZS_PX{bdUvQ8dV^@D<b8kr=NPeBPGnLurzcoRy2Mg`*iz5W`s)Sj$k8KHA@aiZEcK=k^E5jY*T0k;@tdM=ZUZaXQ6&#B{`YO>02-5>tK6Cb*W0QalhQbrb*ReN2WctH4?n(3M0AlBeq&`<xoevPi~5{aZj|TTx~&MWaD9dX>&G$kDYue@P}O=`6>fw5_FtT|y*k3su0%2ehv|z@KXw`1fT!cL|^icKrDJUgF=T(S}>iH&1gN^;YzIpp&?ls6uLtQV3;q5lpv6%2czxv^8jWsZA2aIL(*s(gOb6HDjn%2B9`~N?*FRFjlp!kl}PjAHW$c)=T!cctH``zFlG$1A8xu@CVogUhNhdJZX$_<Fa0!d)4XuI|Zr^q@z^NdrDe_b~{n<Sr8b9JvSrex6u%ivca*{wvf(olm!Z95yxw<k@NG}r>uyV_Zg6N7V&G4aW4^!w3k=pfG09VoJf%(85qafx`bMQ;(dD8gYwdif&|@Z41z|md6Z@~!eXw~u3wbznALcE8eP!FEr|UX>1QMwY<G{IiN|-hvFNk&+^r7LR<mZ$M8R}fr*K)vlnt7Ko!gl&xWcC}OWG;Yz7UjI=xMn%c~}d`xM>3WRU8W^28{NyCo38+I}$1E0V=3c#os0+tO-qcTZJ$IE8fD+uSH_%=Ip-+IrZ~{oP?`7*Y?9}{pw=<N*c=Yxr$z^ih8+~h)jq{q@qWh!lmHptnkHC!?cc`Ce0ZrO6c$@fS#mis90_Dy2{|gfdzU+l|C}{l~vwn_rX9}&&2mo$amNpOlM&sG*@jo$CnPPj>H5s*N;Nv`K?e~m)uSfaxg_#y0wVdLWYQ@AB_2^$Lg+dt01*gtNSo9?NmxIkV#=S%=HFc_<<!`R^xCI7K7Ro*@JwMAXof=0lB3G{C{)tY>PDWI2CXXeoT5QUp`SSbJ~b`hBWq*6f~AjCK%}>pzSFj2Kv8<5=ij"
)).decode("utf-8"))
_V17_MD_FRACTION = 2.0
_V17_ROOM_GUARD = True
_V17_FEED_GUARD = False
_V17_MD_ITEMS = ("MELON", "MILK", "STRAWBERRY", "WOOL")
_V17_MD_STATE = {
    0: {"last_step": -1, "target": False},
    1: {"last_step": -1, "target": False},
}
_V17_FEED_RESCUE_STATE = {
    0: {"last_step": -1, "day": -1, "active": {}},
    1: {"last_step": -1, "day": -1, "active": {}},
}
_V17_ROOM_EVAC_STATE = {
    0: {"last_step": -1, "day": -1, "active": None},
    1: {"last_step": -1, "day": -1, "active": None},
}


def _v17_md_signature(obs):
    seat = _seat(obs)
    farms = list(_get(obs, "farms", []) or [])
    opponent = farms[1 - seat] if len(farms) >= 2 else {}
    cows = sheep = 0
    for row in list(_get(opponent, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, dict):
                continue
            cows += int(tile.get("animal") == "COW")
            sheep += int(tile.get("animal") == "SHEEP")
    quadrants = len(_get(opponent, "unlocked_quadrants", []) or [])
    return cows, sheep, quadrants


def _v17_is_md_family(obs, step):
    seat = _seat(obs)
    state = _V17_MD_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "target": False}
        _V17_MD_STATE[seat] = state
    state["last_step"] = step
    if not state.get("target") and step >= 160:
        cows, sheep, quadrants = _v17_md_signature(obs)
        if (quadrants >= 2 and cows >= 4 and sheep <= 2) or cows >= 9:
            state["target"] = True
    return bool(state.get("target"))


def _v17_md_pickup_reserve(action, item):
    reserve = 0
    for order in [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]:
        if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "PICKUP" and order[1] == item:
            reserve += max(0, int(order[2])) if len(order) >= 3 else 1
    return reserve


def _v17_md_counter(obs, action, step):
    if _V17_MD_FRACTION <= 0 or not _v17_is_md_family(obs, step) or step + 1 >= len(_V17_MD_MARKETS):
        return action
    targets = {}
    for order in _V17_MD_MARKETS[step + 1]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] in _V17_MD_ITEMS:
            targets[order[1]] = targets.get(order[1], 0) + max(0, int(order[2] or 0))
    if not targets:
        return action
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    for item in _V17_MD_ITEMS:
        target = targets.get(item, 0)
        if target <= 0:
            continue
        prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
        if float(_get(prices, item, 0) or 0) <= _PRICE_FLOOR:
            continue
        existing_quantity = sum(
            max(0, int(order[2] or 0))
            for order in market
            if len(order) >= 3 and order[0] == "SELL" and order[1] == item
        )
        available = max(
            0,
            int(shed.get(item, 0) or 0)
            - existing_quantity
            - _v17_md_pickup_reserve(action, item),
        )
        quantity = min(available, max(1, int(round(target * _V17_MD_FRACTION))))
        if quantity <= 0:
            continue
        existing = next(
            (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
            None,
        )
        if existing is not None:
            existing[2] = max(0, int(existing[2] or 0)) + quantity
        elif len(market) < 10:
            market.append(["SELL", item, quantity])
        else:
            continue
    action["market"] = market[:10]
    return action


def _v17_move_toward(position, target):
    x, y = int(position[0]), int(position[1])
    tx, ty = int(target[0]), int(target[1])
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return ["PASS"]


def _v17_feed_guard(obs, action, step):
    hour = int(_get(obs, "hour", 0) or 0)
    day = int(_get(obs, "day", step // 24) or 0)
    if not _V17_FEED_GUARD or hour < 18:
        return action
    action = _align_hands(action, obs)
    seat = _seat(obs)
    state = _V17_FEED_RESCUE_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)) or day != int(state.get("day", -1)):
        state = {"last_step": step, "day": day, "active": {}}
        _V17_FEED_RESCUE_STATE[seat] = state
    state["last_step"] = step
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [4, 4]), *list(_get(farm, "hands", []) or [])]
    inventories = list(_get(private, "inventories", []) or [])
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]

    threats = []
    for y, row in enumerate(list(_get(farm, "tiles", []) or [])):
        for x, tile in enumerate(list(row or [])):
            if (
                isinstance(tile, dict)
                and tile.get("animal")
                and int(tile.get("consecutive_unfed", 0) or 0) >= 1
                and not tile.get("fed_today", False)
            ):
                threats.append((x, y))
    threat_set = set(threats)
    active = state.setdefault("active", {})
    for actor, target in list(active.items()):
        actor = int(actor)
        if actor >= len(positions) or actor >= len(inventories) or tuple(target) not in threat_set:
            active.pop(actor, None)
            continue
        inventory = dict(inventories[actor] or {})
        if int(inventory.get("WHEAT", 0) or 0) <= 0:
            active.pop(actor, None)
            continue
        if tuple(positions[actor]) == tuple(target):
            orders[actor] = ["FEED"]
        else:
            orders[actor] = _v17_move_toward(positions[actor], target)

    claimed = {tuple(target) for target in active.values()}
    remaining_actions = max(1, 24 - hour)
    for target in threats:
        if target in claimed:
            continue
        if any(
            tuple(position) == target
            and actor < len(orders)
            and orders[actor]
            and orders[actor][0] == "FEED"
            for actor, position in enumerate(positions)
        ):
            continue
        candidates = []
        for actor, position in enumerate(positions):
            if actor in active or actor >= len(inventories):
                continue
            if int(dict(inventories[actor] or {}).get("WHEAT", 0) or 0) <= 0:
                continue
            distance = abs(int(position[0]) - target[0]) + abs(int(position[1]) - target[1])
            if distance + 1 <= remaining_actions:
                candidates.append((distance, actor))
        if not candidates:
            continue
        distance, actor = min(candidates)
        # Do not seize a worker early; start only at the last safe moment.
        if distance + 1 < remaining_actions:
            continue
        active[actor] = list(target)
        claimed.add(target)
        orders[actor] = ["FEED"] if distance == 0 else _v17_move_toward(positions[actor], target)
    action["farmer"] = orders[0] if orders else ["PASS"]
    action["hands"] = orders[1:]
    return action


def _v17_room_evac(obs, action, step):
    if not _V17_ROOM_GUARD or step < 648:
        return action
    hour = int(_get(obs, "hour", 0) or 0)
    day = int(_get(obs, "day", step // 24) or 0)
    seat = _seat(obs)
    state = _V17_ROOM_EVAC_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)) or day != int(state.get("day", -1)):
        state = {"last_step": step, "day": day, "active": None}
        _V17_ROOM_EVAC_STATE[seat] = state
    state["last_step"] = step
    if hour < 21:
        return action
    action = _align_hands(action, obs)
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [4, 4]), *list(_get(farm, "hands", []) or [])]
    inventories = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    shed = dict(_get(private, "shed", {}) or {})
    total = sum(max(0, int(value or 0)) for value in shed.values()) + sum(
        max(0, int(value or 0)) for inventory in inventories for value in inventory.values()
    )
    access = _shed_access(len(_get(farm, "tiles", []) or []) or 10)
    if hour == 21 and state.get("active") is None and total > 100:
        candidates = []
        for actor, (position, inventory) in enumerate(zip(positions, inventories)):
            saleable = sum(max(0, int(inventory.get(item, 0) or 0)) for item in _SELLABLE)
            if saleable <= 0 or actor >= len(orders) or (orders[actor] and orders[actor][0] != "PASS"):
                continue
            target = min(access, key=lambda point: abs(int(position[0]) - point[0]) + abs(int(position[1]) - point[1]))
            distance = abs(int(position[0]) - target[0]) + abs(int(position[1]) - target[1])
            if distance <= 2:
                candidates.append((distance, -saleable, actor, target))
        if candidates:
            _, _, actor, target = min(candidates)
            state["active"] = {"actor": actor, "target": list(target)}
    active = state.get("active")
    if active is None:
        return action
    actor = int(active["actor"])
    target = tuple(active["target"])
    if actor >= len(positions) or actor >= len(inventories):
        state["active"] = None
        return action
    if tuple(positions[actor]) != target:
        orders[actor] = _v17_move_toward(positions[actor], target)
    elif hour == 23:
        orders[actor] = ["DROP"]
        market = [list(order) for order in (action.get("market") or [])]
        existing_sales = {}
        for order in market:
            if len(order) >= 3 and order[0] == "SELL":
                existing_sales[order[1]] = existing_sales.get(order[1], 0) + max(0, int(order[2] or 0))
        needed = max(0, total - 100)
        priority = ("WOOL", "MILK", "EGG", "MELON", "STRAWBERRY", "TOMATO", "CARROT", "FERTILIZER", "WHEAT")
        inventory = inventories[actor]
        for item in priority:
            available = max(0, int(inventory.get(item, 0) or 0) - existing_sales.get(item, 0))
            quantity = min(needed, available)
            if quantity <= 0:
                continue
            existing = next(
                (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
                None,
            )
            if existing is not None:
                existing[2] = int(existing[2] or 0) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
            else:
                continue
            needed -= quantity
            if needed <= 0:
                break
        action["market"] = market[:10]
    action["farmer"] = orders[0] if orders else ["PASS"]
    action["hands"] = orders[1:]
    return action


def _v17_room_guard(obs, action, step):
    if not _V17_ROOM_GUARD or step % 24 != 23:
        return action
    action = _copy_action(action)
    private = _get(obs, "private", {}) or {}
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    inventories = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    carried = sum(max(0, int(value or 0)) for inventory in inventories for value in inventory.values())
    farm = _farm(obs, _seat(obs))
    positions = [_get(farm, "farmer", [4, 4]), *list(_get(farm, "hands", []) or [])]
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
    produced = consumed = 0
    for actor, order in enumerate(orders):
        if actor >= len(positions) or not isinstance(order, list) or not order:
            continue
        tile = _tile_at(farm, positions[actor])
        if order[0] == "HARVEST" and isinstance(tile, dict):
            produced += max(0, int(tile.get("yield_units", 0) or 0))
        elif order[0] == "COLLECT_FERTILIZER" and isinstance(tile, dict) and tile.get("fertilizer_available", False):
            produced += 1
        elif order[0] in ("FEED", "FERTILIZE"):
            consumed += 1
        elif order[0] == "PLACE" and len(order) >= 2 and order[1] in ("GOOSE", "COW", "SHEEP"):
            consumed += 1
    market = [list(order) for order in (action.get("market") or [])]
    planned_sells = {}
    planned_buys = 0
    for order in market:
        if len(order) < 3:
            continue
        quantity = max(0, int(order[2] or 0))
        if order[0] == "SELL":
            planned_sells[order[1]] = planned_sells.get(order[1], 0) + quantity
        elif order[0] in ("BUY_PRODUCT", "BUY_ANIMAL"):
            planned_buys += quantity
    actual_existing_sells = sum(min(shed.get(item, 0), quantity) for item, quantity in planned_sells.items())
    needed = max(
        0,
        sum(shed.values()) + carried + produced - consumed + planned_buys - actual_existing_sells - 100,
    )
    if needed <= 0:
        return action
    # Finished animal products and sale-only crops are safest to liquidate.
    priority = ("WOOL", "MILK", "EGG", "MELON", "STRAWBERRY", "TOMATO", "CARROT", "FERTILIZER", "WHEAT")
    for item in priority:
        already = planned_sells.get(item, 0)
        available = max(0, shed.get(item, 0) - already)
        quantity = min(needed, available)
        if quantity <= 0:
            continue
        existing = next(
            (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
            None,
        )
        if existing is not None:
            existing[2] = int(existing[2] or 0) + quantity
        elif len(market) < 10:
            market.append(["SELL", item, quantity])
        else:
            continue
        planned_sells[item] = already + quantity
        needed -= quantity
        if needed <= 0:
            break
    action["market"] = market[:10]
    return action


# --- Premium-over-non-sell stable slot bubble ---
# Move premium SELL orders left only across non-SELL orders.  No SELL order is
# allowed to cross another SELL, so existing commodity/premium sell ordering is
# preserved exactly; we only remove waiting behind HIRE / BUY_* / BUY_LAND.
def _bubble_premium_over_non_sells(action):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    for i in range(1, len(market)):
        if not (_is_sell(market[i]) and str(market[i][1]) in _PREMIUM):
            continue
        j = i
        while j > 0 and not _is_sell(market[j - 1]):
            market[j - 1], market[j] = market[j], market[j - 1]
            j -= 1
    action["market"] = market[:10]
    return action


# --- Same-turn duplicate SELL coalescing ---
# Preserve total quantity and the first occurrence's slot, but merge later SELL
# orders of the same item into that first order.  This removes self-created
# multi-slot exposure to the opponent's intervening market orders without
# changing what or how much is sold on the turn.
def _merge_duplicate_sells(action):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    first = {}
    out = []
    for order in market:
        if _is_sell(order):
            item = str(order[1])
            qty = max(0, int(order[2] or 0))
            if item in first:
                out[first[item]][2] = max(0, int(out[first[item]][2] or 0)) + qty
                continue
            first[item] = len(out)
        out.append(order)
    action["market"] = out[:10]
    return action


# --- Safe SELL-over-fixed-spend stable bubble ---
# Non-premium SELLs may move left only across orders that do not change market
# inventory (HIRE / BUY_LAND / BUY_SEED / BUY_ANIMAL).  SELL order relative
# order is preserved, and BUY_PRODUCT is never crossed because it changes the
# dynamic WHEAT/FERTILIZER market state.
def _bubble_sells_over_fixed_spends(action):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    safe = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"}
    for i in range(1, len(market)):
        if not _is_sell(market[i]):
            continue
        j = i
        while j > 0:
            prev = market[j - 1]
            if not (isinstance(prev, list) and prev and prev[0] in safe):
                break
            market[j - 1], market[j] = market[j], market[j - 1]
            j -= 1
    action["market"] = market[:10]
    return action



_WHEAT_PREBUY_STATE = {0: {"last_step": -1, "due_step": -1, "due": 0}, 1: {"last_step": -1, "due_step": -1, "due": 0}}

def _wheat_demand_prebuy(obs, action, step):
    action = _copy_action(action)
    seat = _seat(obs)
    state = _WHEAT_PREBUY_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "due_step": -1, "due": 0}
        _WHEAT_PREBUY_STATE[seat] = state
    state["last_step"] = step
    market = [list(order) for order in (action.get("market") or [])]

    # Quantity-neutral repayment.  A zero-quantity placeholder deliberately
    # keeps every other market order in the same slot.
    if int(state.get("due_step", -1)) == step and int(state.get("due", 0)) > 0:
        due = int(state.get("due", 0))
        for order in market:
            if due <= 0:
                break
            if len(order) >= 3 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                q = max(0, int(order[2] or 0))
                paid = min(q, due)
                order[2] = q - paid
                due -= paid
        state["due"] = due
        if due <= 0:
            state["due_step"] = -1
        action["market"] = market

    if step >= len(_ACTIONS) - 1 or int(state.get("due", 0)) > 0:
        return action
    # Do not perturb an existing same-turn market queue.
    if market:
        return action
    if _v17_town_demand_at(obs, "WHEAT", step) <= 0:
        return action

    # Only shift a clean singleton WHEAT purchase from the next base turn.
    next_market = list((_ACTIONS[step + 1] or {}).get("market") or [])
    if len(next_market) != 1:
        return action
    order = next_market[0]
    if not (isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT"):
        return action
    quantity = max(0, int(order[2] or 0))
    if quantity <= 0:
        return action

    projected = _projected_shed(obs, action)
    if sum(max(0, int(v or 0)) for v in projected.values()) + quantity > 100:
        return action

    market_obs = _get(obs, "market", {}) or {}
    inventory = _get(market_obs, "inventory", {}) or {}
    inv = int(_get(inventory, "WHEAT", 10000) or 0)
    cost = 0
    for _ in range(quantity):
        cost += _market_price("WHEAT", inv)
        inv -= 1
    farm = _farm(obs, seat)
    if float(_get(farm, "money", 0) or 0) < cost:
        return action

    market.append(["BUY_PRODUCT", "WHEAT", quantity])
    action["market"] = market
    state["due_step"] = step + 1
    state["due"] = quantity
    return action




# --- CARROT seed surplus pruning ---
# CARROT seed is fixed-price private inventory and has no terminal value.
# For each CARROT seed purchase, retain only the minimum quantity needed to
# keep the planned CARROT planting prefix feasible given later scheduled
# CARROT purchases.  Other crops are untouched.
def _prune_carrot_seed_surplus(obs, action, step):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    targets = [o for o in market if isinstance(o, list) and len(o) >= 3 and o[0] == "BUY_SEED" and o[1] == "CARROT"]
    if not targets:
        return action

    private = _get(obs, "private", {}) or {}
    seeds = dict(_get(private, "seeds", {}) or {})
    current_available = max(0, int(seeds.get("CARROT", 0) or 0))
    # Current unit actions execute before this market purchase.  Reserve for
    # every current CARROT PLANT command conservatively.
    for unit_order in [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]:
        if isinstance(unit_order, (list, tuple)) and len(unit_order) >= 2 and unit_order[0] == "PLANT" and unit_order[1] == "CARROT":
            current_available = max(0, current_available - 1)

    future_buys = 0
    future_plants = 0
    peak_required = 0
    for future_step in range(step + 1, len(_ACTIONS)):
        future = _ACTIONS[future_step] or {}
        # Unit actions happen before market on each turn.
        for unit_order in [future.get("farmer", ["PASS"]), *list(future.get("hands") or [])]:
            if isinstance(unit_order, (list, tuple)) and len(unit_order) >= 2 and unit_order[0] == "PLANT" and unit_order[1] == "CARROT":
                future_plants += 1
        peak_required = max(peak_required, future_plants - future_buys - current_available)
        for future_order in (future.get("market") or []):
            if isinstance(future_order, (list, tuple)) and len(future_order) >= 3 and future_order[0] == "BUY_SEED" and future_order[1] == "CARROT":
                future_buys += max(0, int(future_order[2] or 0))

    required_now = max(0, int(peak_required))
    remaining_required = required_now
    for order in targets:
        requested = max(0, int(order[2] or 0))
        kept = min(requested, remaining_required)
        order[2] = kept
        remaining_required -= kept
    action["market"] = market
    return action


# --- Terminal WHEAT seed surplus pruning ---
# BUY_SEED is private fixed-price inventory and unused seed has no terminal
# value.  Once the current turn's unit actions have executed, suppress only
# WHEAT seed purchases for which the selected route has no future WHEAT PLANT.
# Keep the zero-quantity order in place so market-slot phase is unchanged.
def _prune_terminal_wheat_seed(obs, action, step):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    if not any(
        isinstance(o, list) and len(o) >= 3
        and o[0] == "BUY_SEED" and o[1] == "WHEAT" and max(0, int(o[2] or 0)) > 0
        for o in market
    ):
        return action

    future_wheat_plant = False
    for future_step in range(step + 1, len(_ACTIONS)):
        future = _ACTIONS[future_step] or {}
        for unit_order in [future.get("farmer", ["PASS"]), *list(future.get("hands") or [])]:
            if (
                isinstance(unit_order, (list, tuple)) and len(unit_order) >= 2
                and unit_order[0] == "PLANT" and unit_order[1] == "WHEAT"
            ):
                future_wheat_plant = True
                break
        if future_wheat_plant:
            break
    if future_wheat_plant:
        return action

    for order in market:
        if (
            isinstance(order, list) and len(order) >= 3
            and order[0] == "BUY_SEED" and order[1] == "WHEAT"
        ):
            order[2] = 0
    action["market"] = market
    return action

def _fulfill_planned_sell_from_idle_carrier(obs, action):
    """Make an already-planned SELL executable using only an idle shed-side carrier."""
    action = _align_hands(action, obs)
    market = [list(order) for order in (action.get("market") or [])]
    requested = {}
    for order in market:
        if _is_sell(order):
            item = str(order[1])
            requested[item] = requested.get(item, 0) + max(0, int(order[2] or 0))
    if not requested:
        return action

    projected = _projected_shed(obs, action)
    room = max(0, 100 - sum(max(0, int(v or 0)) for v in projected.values()))
    if room <= 0:
        return action

    seat = _seat(obs)
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    inventories = [dict(v or {}) for v in list(_get(private, "inventories", []) or [])]
    orders = [list(action.get("farmer", ["PASS"])), *[list(x or ["PASS"]) for x in (action.get("hands") or [])]]
    access = _shed_access(len(_get(farm, "tiles", []) or []) or 10)

    # Only repair a sale that is currently short; never create a new SELL.
    for item in _SELLABLE:
        deficit = max(0, int(requested.get(item, 0)) - int(projected.get(item, 0) or 0))
        if deficit <= 0:
            continue
        candidates = []
        dayend_moves = []
        hour = int(_get(obs, "hour", 0) or 0)
        for actor, (pos, inv, unit_order) in enumerate(zip(positions, inventories, orders)):
            if not (isinstance(pos, (list, tuple)) and len(pos) >= 2 and tuple(pos) in access):
                continue
            carried = max(0, int(inv.get(item, 0) or 0))
            quantity = min(deficit, room, carried)
            if quantity <= 0:
                continue
            op = unit_order[0] if unit_order else "PASS"
            if op == "PASS":
                candidates.append((-quantity, actor, quantity))
            elif actor > 0 and hour == 23 and op in ("NORTH", "SOUTH", "EAST", "WEST"):
                # Farm hands disappear at day rollover.  A final-hour MOVE from
                # a shed-access tile has no next-day routing value, so use it
                # only when it can make an already-planned SELL executable.
                dayend_moves.append((-quantity, actor, quantity))
        pool = candidates if candidates else dayend_moves
        if not pool:
            continue
        _, actor, quantity = min(pool)
        orders[actor] = ["PLACE", item, quantity]
        action["farmer"] = orders[0]
        action["hands"] = orders[1:]
        return action
    return action

def agent(obs):
    try:
        step = min(max(0, int(_get(obs, "step", 0) or 0)), len(_ACTIONS) - 1)
        action = _weed_repair_action(obs, _copy_action(_ACTIONS[step]), step)
        action = _v17_feed_guard(obs, action, step)
        action = _v17_room_evac(obs, action, step)
        action = _repay_shift(obs, action, step)
        action = _rank_sell_slots(obs, action, None)
        action = _preempt_shift(obs, action, step)
        action = _v17_r5_counter(obs, action, step)
        action = _v17_md_counter(obs, action, step)
        action = _v17_room_guard(obs, action, step)
        action = _terminal_liquidation(obs, action, step)
        action = _fulfill_planned_sell_from_idle_carrier(obs, action)
        action = _rank_sell_slots(obs, action, None)
        action = _bubble_premium_over_non_sells(action)
        action = _bubble_sells_over_fixed_spends(action)
        action = _merge_duplicate_sells(action)
        action = _wheat_demand_prebuy(obs, action, step)
        action = _prune_carrot_seed_surplus(obs, action, step)
        action = _prune_terminal_wheat_seed(obs, action, step)
        return _align_hands(action, obs)
    except Exception:
        farm = _farm(obs, _seat(obs))
        return {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in (_get(farm, "hands", []) or [])],
            "market": [],
        }

def _kaggle_submission_entrypoint(obs):
    return agent(obs)


# --- Demand-aware route selector ---
# The two complete route streams share the same opening, then diverge after the town signal is observed.
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = json.loads(
    zlib.decompress(base64.b85decode('c-rk<U2j`ia{MoP*29pZC@F6mn;RRe85y#@#AYB22FL~hg3ZGuZ^8ceII=`u-cwy&)#uQXCwil4>fZBxx~r?JfBB!2fBWtCzyIy`lYjc<<j2qNZ{Gg;;ripJ&v%=X`_q$u|Ls5j^}oLS&zFyX|Lynx_}hPf`TWbtyY~<Ot9|(K^Iw0x{`vh+*Ec7pCvR@IC#TEi>yPg?n-7!!__*1;{qptp-RAn!$?3)H>z_6^w?ChpE_OfvaCiIm^P5lmzgXYj|KoJpu@CRx{Q2{T{hJn(zWs8t-F*D?(AJ-C?>@bI__X_K_Tg|KK5lMq_HR9#zxC;HlUIR;OkcbIG@lC8fZ6N9*@HdYwd7$=76*NO{1tiEhnwp+n`k^yf1dsTylvKQ^47;cnT}`Ej)(7l-Y<rOzCO-W@UwJ;H`nv`@0Z8*r_J4b5zW6lTs?5<F6WEr<L&49B5D`spZ;%W9DFnD9h=H_a1IA}HcI>cy}5o|nomFax-%zTx8`y`T<uGrMq&D^bh^O)Lz4q`LbHO&TOP+AjM-#3ni*?<qtDpmxYMCKc<y}X?T4_PreIwzgu@MNhVW?RXUjnsw2?)JPCj{0E!D?T{wAMCFocgM449*A-t<A-y<_*`%h~%8eeecuKkhvbe*7h!^s&#U6F#H^Pk%dk)6nOpAD-c{vs>jXuqKnk)VM&#JavAyI@|Y~w_t9Mke@bY#F!SmxxKmBy!rI&pEh@&-rv0cm%}q*(BPF{Vl0vJJB~C5Pq+4@J>eeOIU=(k2Uq#|y<q{q==E>R@4Szzx_6t}f1Nf7Fz*`kabkpng<J76fH4C11n$-2(zeWG-iK*#vp%K+2poIEAZ4x!{FFVAjRpFYK9G3?qW#$6kH$?dI#BVTO17`Efv9hu&p+{W`dnWHcuF4!y=B9B0LK0Pk*zV9Z~hiIA+}}SKI?I*sY-COZ){k<K5hKd<a;03P%9PWt{Voit<WCMhcNnL28(|=_3myFQX?IQ?5dRx$%_53d+X%D^6yTu?LD2dh7cj^U3UV#U%QMAdeK&fh1)S96zMokS^EvMiCP}SWGL8UbkXlozZ4rK=v6WpIb`S@ymKh)j{{u2KKAvo-{E6*0BeM)6Gz@*2tS3K&TRlC2+6naZai4#&T05c(Q7pDl)eCDW)W3D5D%4d+E1eDy^buq;DfPwcYXJlsAJ=9d;={Iqu6Muc6})h(R3_&C<g7|v@ysXnV<_u;e)>G*w?pugN}@<-JncIDu+V=zH+ea_G|QMQ1%f|dC>PyL|4u9eG>y+$6)3h4SJt}H&i0b?SosI)T`O>`q*BO=sdHW9)EZFu-#i@>Kqdv7mjK5XvBQ{ba%b|adUU~S76DM5T>+4;oBh%b2%JtVhs!$vA9118ubl9DC_Pt%*Z(uRlQ4NWT6T?9m~X;S|?Mi$wQbpsM57Qb{}?Edj2>KXM4JlCz}?NUk8RdyS$V62ozUA)NkwSug$Dlgy_@PhE_tX?JY+LZvt1_d0Yi1JQ^MEHL&$uVY0P@9i4aDHD~vQ<5P&2B{l*vRM7FNIMdWu&%l_<wZhPf$tAeGy}fxzi-D%q<9|L*(3kV^?Md0z+xzplx5n4f(W#k(j3P0Jvoas*=vI&o-osh3*Ya*6L{JXKk}m}I56Dy+Z77tci1{H}d`!KsB^auU9;W*)ee9?<`k5kS5_;QwD&w7-C_ln$B7jZj;aIPU2xXjbrVbMex_5!m`F6U|(KkOWD%*e!Gy0?t3OIFI0C}D|Q)7GqpJZm<9?Obao7u99Qp66JUke<wTjf?6%x1MsHIYuGIl*%1YsR_oz!H?%3o=oIHh`;{U3EH=q4?U_00m#Sw|wwJ4mYT037c$~&6}rgd)9+=r_*e`m<Fc64GcWnMV$;J5X}E|l5NdM<-5QX$#zb1PkSs2wu5N$sh(@j@>}f{2>+ndIGzn;N&o|6rr*HCzi0!)U@GD^7Qx6cT#S3l?3;?Q0jz^2MB8M;TO;0fKD2aB#s4djE!jKT52X=r7dIJ8@^Y3a3{c<he45+_ZU4_Y@7S=?uCYHUI!Y<XOCWdl|Ftv^mX5;Gt^0CI<n-_w2n!5sJ#)PFN<b3P9F=~m;Nl1DcQk15lM(UL`<p)>`c%;4LS_Q|8H<PS-gRW(>nz8TcK0hX>vU7lCFuoT7-SUzYcTRInrmC3cyd6hj!)>=e8tt&pPnAfYzu((5xg&3EUmeE;MbGX2xTh?42|msKn7w%$m5W`TSatA_E9P0T3tMvTUkQDHA+Y8+3ziSX7peNVIMTv`Vzq6CUGt<0~UKlW?tJh33LE=h<QPn_h}kR#8+qs61ATA&M;8c!wyy8=hGxu(+CfEa|)=XU}^$umJBW024FLFo53h(!3F3*6Q?V$<r!BDWzbbgYpT`jYrbj!ypmV27p#ll9a5FE^N_U+*}01f?ML#*SQqwBl9FeHM($?aYl!606!Ia#91n4##-~sY`S9A9@4hkJLBm6e^f{H+Evp$YG26Yi0#*SezteQA25K<0_L=TY6B4f%<IFkULp*8{{j*p>jW2X2!2;OUP*W?5x=@3&H~}KQTO}x>f;{I6Hk1C1{3Zcb_{ud~;T4E1><S3NKXC%e0Vi%{B=j~tOx&?V8iNMd3N5$t1RQ*frbM)CjZP<>JK}tFiGRtJG1Q}J8^e`g0mLb~K{!34%=K}pNJxwYBUuQR_N))KNw^u4V2v0!*E}wrm_>Y5zUmOKBewO>S}wE=Wc@z9fjC=IAdJbj)Nyp?@DYD(tQ}37RU5S-twLt=afXIBtA6kt+clEJO|ETazUN(W&)6zpvA%?6y)LW)yHm#sj_K!j2icF|&R3%2Vh~!7juS`z0B-kPdCh~Dt>nv64oeU`u!zJJU$;Ub)5GGrdmeR3P-^rt{8=Dea{h2wu`EJBMHsVpNqAK3i`Qly#67dgOQoS`R%qu;)8U%FL=3xkDoAq|kz{z_$Tk2aP`Vv}e-{hm4#2N$+YNt*<T!Z&FVNfz<3`Y^4HC%|Y{7hFFYa{$DjQAeH<KK|D5n~?_7X)p^bVl6<6X>1w*<B-^<W*dBNz7u4FD}A&{PfYlAzeUXF3E!rR$Q7vSY?gi$ccQZ(d&x9-8zIB<)Vh<B>Lk-tj*m*FGXg9`<Fq3N))0alx3yxsh(3woXmfqB+C33qRcJDMXx1L?Knk*8&qpmK<7Hyel0lpKJoEq}v|RFEq?iHO|zg)CCcFm?)$HO%pA`NsdNR6&gUxLXficYRySW69wENqYSwO2edg7LjJN*FB!qkU!GOb5e}KW6r?07GHf};N2fsS(R-S14tA{P@aNZ4k!uZ{JOMwE{QN8ldpc4TeWBK$u7W5<E=TZnYb#BAs%QBs%T7&IVPxC18!~ctWu>)Hc!6aXP*cH>*7HJR@^Yg-C!r5ZOb<_*r&%w|rJ@a?PIis1%LKYwf)7iXpd@!7rZHrR0NfGjvQW~=kr#+G4U9!boes8eIH99+;eZyil^%2WHTg|A*qh@ls&)_W`_YuNpS?=1wiC7;?XBvvBHXMbF+^!zS^z0>&4Y;3snjQh4wJ8UPK4`SP}LoTp&l*CD6AIMvB->5D%}sP#XQq2#)|DRCtN>{hYFH)32-s|qO(^k%b&74=&T#qE;(IIDfa5mj9(Rqm7Bl=FX1WQb{%<uQ0E70jo2X29`KRG@&*7wBe5PA6*@lb1MnZH9!!MsrZaHaEyub$n)PItI_-oZym{kcdP{pix0xX+ERqCsHC<%;R%{o=elmvQG-2qW=3{5A)W@BHpd53ku&b2t2sQ9pRlx)URb#j3_Z6yqEzJoL{n3LQp#dh(z!J4oRRKe<kmPIttc3#&vI=J#C$Fja@f02<V~cQAgd|U$$ss~gXr$ZWqXdCUNJUBv%5!<f(FMUEP2djovUJ9YIlh=Hh`;4KWR7$U#pIX(MdGkWmHM!lk+?t34U|L_0^!0lpyTR|qQ<V-GT|Fqmp;@)FnJBPWEn9uk$bP%s*kyA{(6b4CZXl25i|h)EIZ^1byBR$B^*|Am)J2JG`hUlDSU5&GsOWv?X8!r(WLZW`-@~SuCQ24seTVh+ko77@oW+sBLIhQMl@meH-{cT#;_xE;B!n`pP^rcqV?Gt{DgROz1s9J@hDT|pi~DlXT*b|`pZQrGf@FAIx#IqBatLq*j}in?6j*ymAjzkNujb4&EI2?h)%NM+?!5vP?}<>j%#~K7HgteEa-N<vH@lnxNm=~?gu&8s%Xm-vN0oCXSH3ip<rAtik4=Q>=`F`So!HRNtS~c)Z{dZo3Tcr@(v8`LAG%!-Bp1UMPNnU?4^Oz{ACG$QaMzcF@+<<+k>vUQ9~vM!WA!E%37#ZYZ9A8+a^}7E)tDcl{@5#qjpJ<f-#`3P_Fu205i2{GKIZs90Z?`BH{{qRS-oj^X>b8?jRBvZK=8YSB+O60RXE%8fBp1l?A|jmb~BTC^<1jm>oK{v~X)in-Uq_{V4<-Ww%5Zx6p&(g*h)~>crv5euvntw42o?ff15Ew>T{C@%Yay<723Eqig2cLL0T(fT&Q2mBCZnanyP}oSIsFY(+^zTc(LxM3*Xrs`px%V({KQ^C}zQK3y5nOA(Y&YEr9!*DpHh6(>pNTO}y6K@XIM9QZqu^Ia^D&9P3Fhm&KAny&(*^~}YuyqM;U(2N4S`&0-`aeuU8HA*CU0BcgoC`ml=&2jvj$eTIGe$PwyZ;&1JA_9~MdK6=L9SQI(IH~3&gZ)DdHkS;oMj(~XiQeD{<$Hw^tz*i%#+*Q4=Q-g;i8N^~r5)D&C2{O@j!K>f&t%B~^R5jGO%6zETS>}tida#5HtTmaJqmOhJc~g0&74*6Q7i69XC>Wwz82WpP~~rPKrD$5CWzUZ7Wyg^^a%HlZIeN$x1l;9wus{5%;D<FnJa1?3R+h|MNpPbLOo5Hbw{3M6cyS{*1VOj<<*fVa*cT(&YeX+Z6k6kMTeW`j+E2~3+Y@sX^kgmOSI%Z@y?}lKS1|4;7@P7obJN$1bVY_ivuSJhQytvLCZnYv=-RFJY0k~7-c>Uk>W+YxfB*1yLcHIg2hS0pELe_-;`YnxQYny@Z(Keh%AH7=o93sEBbsIgF@U)0w_7Me@fEQux$RO_!8m-^>uO#+I8^k@TF5B$IHgoTCBiLd)Wn!p}Bc6^nJsi=6Z`MXj4h~Ch2UzVfTW?b<Kb(b3oa(iORojW0O+ooz#Ku;QZLp?!ikd!`ZcbDfFa?={r#@CZ(u52U#Hxxb-`Q94HJ)UH5@ZZB&zn=|=Hz_t!32;IoGCBLn#`^v05+os2|~y%K4iuR}oY@EJ_$dF^^nEpno<J}UY4Y;yy15XM4h>jQHY@^#bN@qoq;PL~`8ZY|xf18P<_Y<vkYElk}cJQ+PIkPZr`ksCpT-i|Dz1Opaf<cb%YLgAz&gh$U}fqr1g^0)IBnV7J=Dv@#(tAGeI2FFX$-HQ%t4X*82WAmmYi5c9IZ~KL(g-m*IHJ=`v7w>@-V$@CmA_fpSrWb4)K%Bq`vy$Vld=KK<z-S%2tDb}H!FZm6DG$@n&#FW{FZp~cb3FjW#vI~K-xdWu%c#P^U<1tT<@mwC98<)gCiIA~z}DOphKJnl8BPrYwOFcQ?>foaU5TTtC;&WrGWLa5G_cb<2P#{@<5CqL`-uM<b(AREwIX~<CAHKasF#>qI+gtx`y;W>6R~BVvSiUR+GQTrw_DG9b!aQ=p=?cqAh)Y3Vrz^uqv{i?0{cv^tOiGeMN=wvOoQ36eV*IhYe#pDZXe-7KU{yAPFtZ+;e}Djfs2B%<Cf8CSna|=6$_<G4sk)%;5&Z2nVEQ3eY&GA{VJ_PTWvOQkV&lxfR$u0i^zRaBm5e`qLCB`buw}4v^3Ia2cP!hFe*FFPYe<h?&QF|+F1%v6Eum)XzWg>2YBSnRV#%*njG(DJ>Y#K4hQH;93Uz!<MVDdo+Pro1cLcq4Xf;V(G2R9%-r}c5Upp_SWI#<^CC*e!?8Rl#i*WG%P_VRnTm`EN3DWgS%Xw7+O;E4WVR|mp%+)xb@_6s)~AD|k_kl}HXVlHPF~I>0$seU<v3AIf|#b&SHg9K#(zgylGtVA1pbYwZoVp|HBkWyblYdkuCfb92r`m<C*GkXfjwqz96QAcyg3(A;Tg8&mP=_)wD@7qQsSjVG@W^t<&=2Fv1CRj{^&b7m-i*bkG6$}OGPLffkWsb>rVt;2$)2zKUH>-xZZC5YfU;|T~cs)ap#JqWt8)=HR(?3=QC=F<WL7%L^fqZt&1VmkwRU5k`mmvxcx>cf}D3{CAzt61xgy0-sEY+Bb&)*ab(~J=fW3H2e$MWC{y^Rgk_zJ1Rf@N%A}5%k*Vcc6|R5)usL@kjZ)EAF}TP%S)(ylUR;F;flu%}jnz0p_8fp;XDXQN;%!qT?J(o%0ZLmgDY$tUa(G4EMpQP@m<HcKI4E<d3raP4(UbGzlr_QJhygv^rZn8rrCQJ$veZPliTj-SSJhfN@=A1);LH*!En=ps@{uSvrpX1akfalvCt{ivCK5v=YOGZ~#ev0DOO%sLj#4`%#1&61icQ#4HUU@n1+m(aK$KOUL0jqzgTAB);WDDjG>pgz0`!8DrUV8rl_W(){nl2;c8Zm-!hCq5mX$u>tDB>IS}5F{9~!D~1%XwLtb${RRT3kYPZ1T~^6+a<rAm4ASWq&d@)D6~5%bhB%r#<y7}%eh^T2Pnybw2AFqg*3OD%MIE5H<qiF3LRm!YJSlWh0qP1-S_0D%nJ)42K)I>eAO20To?<7kqrb&l1dfSSkwy`l1D9L?df4EGUrIx6$N5g2IkfEA6TwQ=`~8s;tjE>b8})bgUvqpJ!BEd!Pr%B8&M)y~#o_ZL_;=y;qoiHVl@$={Zg2D^drCs9@Ac=d+>t4VRGnLuAj(1)F4t3HIxNtXkeY<j65!Ee1d#@aKKo&fYPe7es1Qj4@j>c^90MGh=;d)kAan6;P=|3x@dN{&hC>`=fsV%}i*jnUggGEoE`DzIBbX^7}s&RM}(J;K3o-dW=dS;4B{ZBl`1K=n^rHr!TLQ`AxB`=M4iie&!Ug}S3<mKLIua?E-t?|F9VpjucdchacO#rSr?;;rORszbypsc8v^<q!iPryA>lQ_?x_vl8fOSBRhQoWQ)fFt%lHG8#Q$+-1Rjjh+S^hoZWf3ZoEcG%pg)2e!%uByEx!2RdxXad{ehT%eWhEG<pjF3-KpJwrEDJhAkIYVF*E7)fMW^Nh@iOwFtA)xbJuJgD;w#my2O6g|D{+3K4`Kaja$$I11}qL#yjwnb-=q+fTX{plhhiX+h}Z6rYxW*(rg*`zFEgTbi9Y8D1$ZY2*AQ_fJi$@PRi?r$`?UPfUqcDw1CTs4|=PNF%8D^iU*GW0Col!04H*-bsAF0O_rC0eB=u@$E}dYQ^7o!3fABj*WBnNv)fCOw>sGud*uDj8~ImFg<hXqnPzf|wp8&+nop!$ox`C7pJl%zxzlnMG+F9(hp677$^+?l%hDuzrU@?NB)(pYwC)g0gdlpo;Wl-=9bOzOP7DyRDUOCRJNFo|Ob#L#c41Qm#CwKR61kY)%;iMl6bMOypV3e9A9Ln#Re~)f4WXXc=DgU9(hqi;{a1!eIgrz-kxu4cRN9m0PpQge$b~&Z3@01;4Fi)a4Txhj5NMcY3J@4OLb5pwCT{=Bx|FTwXOW=ArBV6~{E_s>}ZeDVpJlcvkTo=Pg`?U&39a|2enaT<lb-XCSHE#vH3y->O#EN|K__l-?oWs^xnbAxq$C6f#9S*j*gasRh8n6zdoRMdk~cvpvg(lN~a-Fg+i~Ncb(vy|5Z<6n>PGX$6{+mFbiw=eDvuL<Ao8(WrUI=pGyKIHYy!>R}GT3NfG~&?J#ityS&HX?YUTm5&ld?ILE7m=Ko-pI6TIL}J0s$&;u~MHK*<eQR}q`3i`gDe`U7NJ0$cq|qKlJeuf#TlJ38rKR#)>sd#NGIpZV%LU^ws+8BB^sAK=a~!i}Pr+?TipZX`LAgiCR7w<6jN=QG@nE)VvsiW7#X^xO7?VM4$62ftDvNg$)pnrRQM;O-66yvcpI{p%3W)NyqDh=yO6shv%gBAGCX7hMBcj8U%cUP3F-xGXY(|wo7=#IquZa2Nw6v+2m)|Sh55?^kU7b0uY?-5IeiTliEP-tZ!9uOF%j0O3>4h*o3<LIIag2(Y{pBpB+36)i)&$CQl_slz1NEpRioFoSt?HR2hrm{%2bb6<SEJG}X#%s%xCzo6`|4Dj^#$fF88wT3!ss?IVEVwym`jgqD$B_ndn#)iTX5-+QgWFC$u#+8|ByghxSiHjMVyT%`{nq-q|56<dC8C|vkn801*NuZ?FNqUP7|D&uSu%aP$4tK-Bgm45>LgNsBs!{R5CJi*2PS>_z0|WgO&It=jr62pe-}M?qeT{Vk)7imTKWcgG|D8YXUb?9VUtfou;XI0RmG&bT5p}m8B@L@J!;Vn7O*CDposp7j+(%m5P~7EjuZd4eWsysY0BRBc|3$5a(CO-tMD!Cz5ESbg7naOp{PqUaAd1U0F8vS&=;{)%uVp^~r*1xBj>0Pl_q`bUHQezPf6kSsG4~?>&I*E?7$2F>%QyLL1F5kHyKma+D&*@Cq3{Z%rxesP|p`DwuH#`FGh#k+MkOZKQDTOejx8jw+OfGM*}fJ2vx8sF&D<UJ>D~Ds@n$Q`fRNdjM9jK?Wnr9Bi#I0xC%|?I1|VhEYjsFy!c&2vl93DtQJ-PGfzHffSiuv0s0pmWJzhZB^QLWbFZaI}B_S6SlOayk)quGJVi#PD!RY12jq-8I#qY(1vKPY_=$mIER;g(F<sqNP5_GGIP>sYa-MEfrY|uP@HAJOWt3UcvHrKm`NBS98j^GXBgNx7=`n(Tpgk($~imwPEK=7OWImA<RHQzY=Q--|I8X-k`I?tWR*f6UQ>nhpkritR&T`bwge9;^DN8E%xPt`pv=P-;jPusJ+iK)$_H$zG*P<TBMi~UFFn4yowamU1J{+R%MVyJTA=Jhp79bBP6;)!M#P_28GRht)5WonwK#=!^;%7I2rUmRW0jWo?W>3;(PBZH^W_x?%}4vi774|Us^+qO#mt9;L^_05bklvwx~T<x5gcT7DJ-^r!IhR4CDH1rvM`7)H?SB*)YFU$lKI4S_=gmhl&N+WD^%F8Zov15Y`cv!P1!gU=WJc!(W!dJa7&35QpaTQD1^DRK|nW;g=u|BCSJ;P*%yoViiUEFo;d~f1l9rsYOP0h9QI7rq?TEEN712`3LtWxldYmUic-hdQCz2zsWU`cv%`^A&1uuBsM7KnIHfUAF2taRilkrFAx3IlQBI0P(W-0ydgtL~1uhdZOx18f1Kr3$kVIth5Kzx24<Tww&pFeOF3;$B%~HRt%6OkjkTa34q7*}5-jGcCdU*NLyy0Q5S4IU^Rs&eFPpJY)Nwx4m%5CVW6^jwcp3#;_DDM&{#0b%q%!}*0sH(iZ$YXu!=we?n)*c-^fhrd(*%kgIj(XL+*|9=-ToI2m&4uunaG&=O^;E7A&Dj~EaKqNwfj>=2eB3|Cac8jz{HoR7>~kr2^|ee_uL^e-s8dQm$r5dM2$kVO7ni8^c8sDSx_lV}sdZJV?Pw6`vP67iIT|g_r$>3z8nty<YgRR*xT$oZzZ|OeB=`;49wry5>vrnDbc(qx4da6fgYnvsQF+xwd%WV$6jh_ZMnM4&T2j;(Bq)kSEQ~`QEV`tQXC^?W6k<uv`Bjl>kqJ9xTEePaZ?S^95+&@A!;^wGdg`x>hjUzKV}Z$<e3xbtC2Q@xPHUufL0PbZu3eAdnW1lISyph;ZAj{E1Q~cyIZ~2syXh~Hx+ra{hI5u`GAryzA;+^<?vA$uU|wqNlc!lVIC0BPni)^6=H^42UCX%UhZjL<kDZH<E&!FpdLs<_Wm_hvT&~5okKp|!=GOW<m+xz(3Y!jp*L8gh7*-T@q4hL_j2NS$s%T|NsA$qatGusWz3oyu7a1N?8BCK;mUA|x_;bB-urCVZ7ONGMyS5(v&Mn0n26!yoSt}WApqE=w`KipDop<Q8L$9mdC)AzDxx<k}swL1>EK|*#+butHg_0mnzNt=1Gltd+OczLwS~R^46)_gwgT2|?KplQyyp)zQnA5g8Tdt*oQ}SVE!i+04!7{^>nh8n*28g+fphQEf)OTdNSV1%Jkr2|{#Nd`{(5$JNj#14M#F@Y}L{Q|kD15+SBR*!1`1h68g+^Y&6Xh;3|FqR`ziAJz`m&)l1xzM9-l7u>`?O9rv8F)47M1ks2$;LI^cOGc&_m`Us6uv9Vcf!zy)@PnxKuoywnX#VBU*ba3g64~W1FG*Xa`6v8*&042^9i5Yauh?;6z=uRZ*u8dBPU~3-7Xmw*bQJXfWwHQcAOQzpZwF!iI?YW3sWQL_=wjLwMU-h2ZKLmZ>YGs^|BXZqVrOII<p9+pN`F;F?juKcErlN<~r1``@bU@LH5UzmGZZ&`DFK!mRKHD?k#G{NJgjE9xyMw|uKu!adasG7b)$mz%s%tySZ-3BOC7Jxy7k8AA)RKpEYnk`@Wm%&fFdR=;N{rlsJV*E&_(J|T&CBA%AYlN^ppfI>@qNQ*5`ppfg2AM+Fv*&}>-nm2-^2I{VHnfI1|yL(iniR~oM9(M{`Js%f1+&vA$Qgh9_^tX>{*tXQFqmP#~k<!%eKFkOe&oP;W4_3qG*f&LJ+BAc8;N+fB8NP^ici{TE-eYnWGPNGlf32wKN&!%-)Orf7rZIdHZA;&d#7w2iCM?vT81!10De)n|VU&Aepv$;)&C?^f?J_@snEywPHg>MUq7O~$+%=|LGzbZdPbq=_q;wY!y#87?%H)aek!%eyu;qrl712kVxf}b+?Q1XpFui<xcl)8Im*J1R!pRK+`uH>$Tzzaa9h}g0N~4HNVDO}kBeMgpi4FdSOcNUp&}V5pa*AC0)^_N3-;n>BeWNaosG4P)KG`;Oxcz<qkNf`xM_OOm')).decode("utf-8")
)
_ROUTE_DECISION_STEP = 168
_ROUTE_STATE = {
    0: {"last_step": -1, "shops": (), "expert": None},
    1: {"last_step": -1, "shops": (), "expert": None},
}
_CORE_AGENT = agent
__version__ = "market-route-moe-v3-hinge"


def _route_step(obs):
    explicit = _get(obs, "step")
    if explicit is not None:
        return int(explicit or 0)
    return int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)


def _route_shops(obs):
    town = _get(obs, "town", {}) or {}
    return tuple(str(value) for value in (_get(town, "unlocked_shops", []) or []))


def _selected_route(obs):
    seat = _seat(obs)
    step = _route_step(obs)
    state = _ROUTE_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "shops": (), "expert": None}
        _ROUTE_STATE[seat] = state
    state["last_step"] = step
    if step <= _ROUTE_DECISION_STEP:
        state["shops"] = _route_shops(obs)
    if state.get("expert") is None and step >= _ROUTE_DECISION_STEP:
        shops = tuple(state.get("shops") or ())
        dominated = (
            len(shops) >= 2
            and shops[0] == "ICE_CREAM_SHOP"
            and shops[1] == "YARN_STORE"
        )
        state["expert"] = (
            "high" if "YARN_STORE" in shops and not dominated else "low"
        )
    return str(state.get("expert") or "low")


def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    expert = _selected_route(obs)
    _ACTIONS = _HIGH_ROUTE_ACTIONS if expert == "high" else _LOW_ROUTE_ACTIONS
    return _CORE_AGENT(obs)


# --- Stable submission entry point ---
_SUBMISSION_LOGIC = agent

def submission_agent(obs):
    return _SUBMISSION_LOGIC(obs)

agent = submission_agent


# --- V17 complete-route public-shop portfolio ---
_PORT_DEFAULT = json.loads(zlib.decompress(base64.b85decode('c-rk<O>ZMva{Mnk^B`6gNy)d~Zmy@XJ)?nIZDKtj1_O8v1IGF=_Ra8rw_4&yu`)6;GG9^Kv$Llb*iy0HSH8^1$jG1m_vYV!`Sq`V`Ss?Xe!BVb-RI9Y`^C+F{PJJ__TSGRJpcIDUw-}1zx>bh&p+M#;me<Y{_*kQ!<Y9@H;bFyciVT*{|@`bPdDFveB9n#{P6X6KX11mo`3QC?WczyZWf!#$A`aP9Y22e!^iL6eR}?n&);pgKYo4i{{I#iFZc2NpT7J!{)O|4{&ch3etvrS<{us&pT4`<k6+z;(0K^rgWNfoe8V5UeEjs`=jYjc`tmX#qsJefs=er^ckj2S0be}k`M-X6I!&(jxIccK_{*`rd)hv}{PpB{<SFmp`9nH9kNoxVcN>R7Cb%*tGSR2)5Rc8y@9_;@_sPpsULKd4UOS+}<8ssd`QeMaN@RNNY8@V2oZiCVz&_R&$<D7`q<BQf$%G?`|NQX2cy*#30=~PlD8Jbww0##$(DW7?59oFIi<g6N6|C?rx7-H<y?nI2PtnEdJ$pKYCB5Gydkd`6X;CkKU=Mlt^lAJ4>E}OgAD=#c`uMLeOVavgz|s|7&F(w%4&Tl^)n1L<yyvr3v4za7$QVUnnO_g`=!fv^M{{Q%Su*zaF`;3xHXl3$ynXA7g;NG>u6f9Z$A=&3LtejyKjig?OH228`{}FCKN|2?bA`-YADOw{b4rf~4}Cv0;@$MCUWd<*&iM=N_v8W)&n42Qu%Arf=cmVayFY9nAO8%l3oy9jij7{ynLFhR_;8hdqQ9~J5dEU}Ze!goO$B}0?VX5s$)%LK+oJ0mSbclfsYec6SG9XjyPhh6LuoB4lURwWXK{j#255A=$98G*acK@~u0k-2=V&T}P0*n3{GdvBcQ#9TM1bA$nMqUb`2svq@u>1%TD*ES4<zMNXf6%3Z<$+no;$3;0~?O+gBeD@|2D7Ugu5eM)8RRI+Za3XVsen3xU|H(xNyNB^FP;2#kY|hXETRJxQZu#U36PU0mgOj-{w7bzJAR`oV(}HgW^##boKmGXqBitaJX%R$B=86y^L#s7wQc|u4=e|!dS>1t51k{#~yB$1Z*(N)#O}=Z*%eX->8>xt^4|v^L_uYldkI1Hy{2W72ohX8~pG5QTB}3Z|1^e@nPo1WS7!R7kDO>_f~T?O_e?G;&+e#(wNnH$(DWH#uuYLJ=lfXPKl;)P7hyOOR`3jd-%GM;V%W)qbtxuR8u#74L<=dHeTWLOTy);&;Tkc!koAHPR;aDN(zBGy}7eOV~t9B%K9wGF2v8FV>}%K0USE~5j+Hm=S=Ubm3s*TN8=?;efWHQ-;w(|AA0vK2>C(`RqJU85m;XoFLK=-pdVc$)GrPx1p`zE#mGI^TABGrQGxl1yHZ@8vE>C;*!{G!O1V^lz4qN-m<!c7IV{HLi}!l8rYGBd`oRga?JuH9NVz?yC!Ksg1bJj8RYYU#SQ1wl_>Spchd&kQ4bt16wo7|9!<`xno4^50Z|YQb-?~31VCDQ4;3MUIDEv}`dEh5t2{O!)p^mC7G)4`4oBMsjV@tjQoDpYB%sqU|1)6Tq?usLCf){0Qs*-1_5kKt<ci8uROESq~wiH&@wF=#wv&X`b4(?60dvIrW!un6>qe9jKJ7+uBUn_cUj+eqivnJw<@k16Y5v5%6a912bw%x<SvvFE`W0?Y2!G-hsGz-5)l!n90nET4l4sv>_Yl+q(x(<>#2m(L7!uhREd;j!*4s0p;2^Xuh>^$hlQeJ2lOJLJZmUP*9uQq=F@cl4wXnrCu(%}Uha)8FkCK4xC@~}oPRZF`8r_xWz1`ft)lfakp9gmk8Tt%;C=PYFUJV$OHZj$~EJ!WLNLNjQOv=?90o=<9q$QSuWSEwg?&5+P9%0Ul_kE`?yYpUj=oO&-WovUghog&}ht0#o}l+%8&bZ_FaJ9f6)*Xo5q;4yYCw#N9H->>ip?U4s=gnf&~%Axb0pG+ol4yPudxf~H$PHJafU$0_kfV+c+=$y!~9Efq@JjceNec6B@Sx02;jNLE@HGP{+<P1ApS!qX|U0M7s=!N1MQejUyL6;xX<(HLhF<=`)eqp7A55+Vj8=lBH6T`<s@&r6h?>!zBgUT&~^5idKwxhSx1OTg0JHKe%KHBGl3=1Mm8XG>Zm4q&k^R6|UNOKfrBg~Q^p)mv-9Ys-2>D59bBT_=FOB=adh`{GjxR*?vg89K=&M_=<_0Iw*m<$)n^=kSeofvJGd?oLtE8b;TB}1J;Li7zbBAx|sbP{y0G^czevkcUV8GCO5@5knIOP;$3@u5pv{JjvbC#RMA)!;IzNGF-2nsB@#U_2AbYXTDu>5F<*07#x#Z=y74yZuh9Iz~xBq*W@J0beJtp!1tf3Z_Ls$*(F3ykyAcsT=`|a)L;V`LcyVFB4}W@1Gik&{MTLdxo=aotc8r2XKVIgEjt8>WjgJqTs-l3THq(0^S&9JV~(dv;YL{v2zUM1N#~3FHf{MTgN8Jrj()_kBLgURZ?M?_tPd`X1AFIgQv8kc>w9luxCN4?6@RMVz7Xmf*@eA+^;xr{*^k-s&wYU5!}sADqpM7YOdOA@Gu?ti||7^Bv`o;G881W!OF?1xlsbjp2Xh?0+JvyfFG9fe)hltrw}+UG+w9}SDhAfnlAlMS~9JKg|i@aSxJU>>^-989s8&V)Rzf8#Dmnm_tT$z`1sGz!OZPL{3U1_;)}VR^-eW^1e9qRFuJ6}YHOLSDYBGm5LN00Vv>Qt6%HW2$Y2Vbp(oS-!%!nL8Fm4pq63x_0d}=gV8@VhLQBfH<jR)<qewl~N=*diw?b>EP>V{Kjcg5da#O5yF4JT^8of{^qYzkLiD630A_|qpw4w<y5dy~Y%UOP*-NZDw0Bpp*`K40DB)ot-42PD^^{v0I=lu@}S_})0v|y?(B&rwfHl|T<JQZgr;_?JP00N|uxOhRYr@52LFnZj5Vi*@Zzig!{otCkx=rDcCg;v-kE@=fcSjLP7r7~nOpGGHzf@#%i=+*Kh-h}jA#h8hkLvsoX$ElpNbj3R4U~9tHjo{moDjdO*BhLWUE$Tcj;3%>Kd9Wn*8b?ls@wLGDIlVm*L3OI6tg8xMQ)9Qv1wkxNXh;JxOC}>bN2<#JI^gkgg|{O`^QD|?a3Ey>3Cuj2)APpK^7Bdz;9(oBh1&!~S8xW;t7Tu%-{e7cirMb31sRLdK%$KwOeYvW`GJBx4Kmr*yo)4WwiuZNk+mpMsAnS>E4dZ2pUDIZ8)&^xlr7TR#Ati5G(W-&lcgxKb>UaK-Q{RI0~@2>MV?=)B)$mfhi35fa?CWLKV<n>-{i!{G=Ism!VwWXPOu+qoNjt|+7k>>X^<S1)oneH>V98UO5&0jlY<>fMAR;^ODzRE7(~M*wvU!iNGcOitz8oVv7h8iES9gRLRgqFMsvS4EM~aNgE1?Yvx+V&0$7}$Va#(0oze38&#U(M@O1cF(i#*u9S!c2<FDQ}<2(%Bp(c>n@Mz*y8iCjRr*^3ZxDee_vVTTqCD8?uKt`qnMymiOvXG0kdY?=N*$icjiRL{~kX{)#SQ`eC_@k0Rsi>@no<d%F6i$FFLjx{hU^y~HAbLniS39G)ubiQ5#hY<64yzcS9oxio^vB9c>f28e5Ao7VAeQ}`)6?(EQr7|D<UF|u2PGHXIA*jDa|_H<z9D1jQVavl`0*tVPDXU@?5`zU$1XZVTzM0`1NaDTD=zP;-$M0>)iC=<uZ#xC%YIqF3Z};hL5l~h%Q=OKIsrCJZe6(90F$6s0SS35?&T40VtjDio&ruLB%_6*qFh>{mKDMSPt^vaC@g|=zusgZbP8)(3Ik)KLPe^C%&7L_DUKVeGcs=mRs^t!oYtr{iZKaNEQoI2;d~9o*Ra=FwJb=$Am!Ltk=G%cEmWnmhhV+0w5+sgR7y8eYEBC3aNZD@vT(=%7L=N@t5FhM29cg$6{HBm2GgFewi@0Jms1NQbWT(NcglE>TmkNbb3#jPyQA5)%7&4Yt@Ynp0kVKjTA@gVbA__XxLT1C)Gf8n08;@F!&3^{yi!43xOLs7X}>AAfF-I`0pZx`U#F7i;VnuT3ko8a0%q7bq$E8YA-1$NJ3C|OJh7M;mXpO{q2gcMY9}k$f3%1!;_XE}ye7NxwvO>!)U-tIMNpT3q6@htRReX82me|WT`H2Y#)h*o@UnaHfs(hmYi9>&w=syMz|yl_YTuRUVzD5Wl^8|Pf2{nV<`#s5LnrhS&Gvh(R9*1IVV26Bh_bJ@IoJC{rh|oLT!KrDis<HC?{&c$UW-x?N>JpJ!z4BB)4_-ytYgb=>uP;yf)7cq*0i$XF4qdiCF%}wNsbihp9U@KO_0PoJ~d-P!uKCP{R!|1tuDG<OdCOywM=yxKE9OUN34eY`VE2tMSd+M_#i80Eys{{dF-m#HzYN0W=GA}75Z<;T!IM6JUk`JIfzBA1*wZ!nLh;T@G=RNOicqxr#zu~U_)qg#Ha;a_YNh-Bu$AcQf@deqrGd-^$9gREy+q5fX5l;Tr|Fnili_UY^J(HR_&w`kHk#poA6oqn~FK#RK4oeIW3gyMYj@}j7GwW_Wky^{19(W8VWm0c@$IM$;)<j$(-5z5S-gAXXb}c6kE!CleaH%I~XOIy-x(|wRX{E5La^UY#Le5SKl{q9}K{lo8p}Y?NV@AdHoQKi3GlglxV4LkO-#|Cj<nEU{YPYq^h{dB@Ynaz?a{de9{KRh$N)cWRrK7#d{?6%MA61uSEzjqQ+I01*5BEDmgn)J{j(Y7UUqLIj-LhIhaY`bcj{@qgtjw@!kSA=zls*{9m1lwF3%w6^e#*%V$uI28%Q!RU^lA&`Na_@3pLXhR^~{P)7+m!$n!U*MUV7z{yKxnd_0eCdcEww;V`NkbwjX9AeOuCwdxHJH{MjP)Y%+j(K!8X)s1H9GaLG>lR1~FlatOtKUQ#NUrEWkAitoPtYR*Z}rPuHsK59y$m85Kx1~V(?kMZ)43~Z!|qY$%yOG1lc?<=Z{`yMLkmA{4HJ<7igg-Y2PLMQI+>-wIa|wfixzRr8>gj~V(S-RzaX71K+>6wz?y{QnqXup066$ZYpl&X-k8>0UPJqeww}@2kRtCY<T>HvGi229C2W#GB4Ub$M#@9x0@QIHR(V15iUIi%Z*v`7qdtYsIn2>`bbTw11tIew@}=}zzqO)I$XIxEp~34mu+0D;MS6V>{m>*g8i2^Ui-<LvK_r~n(+^gV*aq8HsR&eaf#32L2Q*y_#6>QpqR*cnWnGrW7wPxkPOT4Ktzk|<<e>P+!Id;9s}Zi6EQ<<L^)7eO9OPxYz%u3H(o?R$dZC>cu`2O>S<2PNg2?Of+93u$N1>mhUM;ZJT=k}Yu5uz<w~_S|ovF|Zy13a>KXYe>q-o+<U)I5vS|))3=-6})*ziIUwpEjA&feuk`yY^ED3ueWb<8e+0>iSU1Zu3AHHAG$EJH_gxpvZqasg{_R+cf;k)RljR7?yMvdqw?B5;xFrM?WKOZiv{qTNOE9$jTN7_ztl1=43C-&KM?{u5K*SIT1UV^hEiEW;Zq#Fw{mk%`?s_7i_RwJR9FH%yG_yp1l6LmJ6W(e!LPYg*{ZcM>}hQd?$9+5=&Au&-!?5w14{K=RPbdEHXJrCx1>2+H0u$zEw}8ZdC{LAheJ%xKu|C&;n$rqP|PplxZ`14;~wSc^8M!fBAa1(`JWl8Pg%&M_&+PL4FoSmS<rSM713o4c%lZO`o<7}}-TOs-jkRjpQWRaAso3;q+ySHvOOBuyTn8ty0OAvc!4p@a;iv{-bGg0IM52z$@l^|BOoQe?<|6aZ>eF1){IJs*fR^)aN^i>M!I>uk62!gRA@#`?ni-BxI4U=vqqX99+KWeuP#(?&v0tQi`QZzWV%`&Vk3lxEos(9@*3Ek0^|$=uGvJ!3Tcv{Ro?inyaGFw$fXAO51IN0lfN3ENS5=qc0sq<#GICD4s*wXFbTT@J1gmWy2;c7gyHa2<JyK~)GAQ=9mX&@k=0*=0lpAJbnvfi-4YH#;)qJV3C90M##17)}RJv{A(|Z(j@FBxgVc#z|tL2p<pY_UjV8l^2bPEi<%@)r;qBEf|*6F{5(q;T$+&Ta4ckdJRCwc!!RlWvqpYatW__Zc((wwh4ZYa_bCIa>(MNydNxeoLz+~+HlwI>w3?5oe!1}1LHw^p>Ig^mQ3M^XC2)*EQOx?xJHNd#wnbD6EWKup7StS!ZXNG$w1dsGa{kDHLGGabeZ1u2$QhyOBI|MgC?B+Wv3RZRp;8rN6tw}_gB)Z@tapxBEni(>FKP-lC|7wh2!g9T6vL0*UTJaP*k#Io7AA~P1~@^RFmzz$W2M)Nn-Wq#-SA6uG+P8)TU6h@Kk~Yt?xtpd@!_DA)U}e<+xKGVkn72xsqS96igr&e$`En=LX9R=b@T71h$e2oWY_U1KN{HW3_r$fOHtvo9immhnnAv|K=@euB{#7^Mno~nEHrHLGeT-$`+F9DJl$Y<V2;s@TtO|>a{8*OTgo2i2@qXi{c#jI;my_%>Z*8nIEOkx=Soc)*1^(nTh*pdTj|jE3!yoA(Dm<S^XH59pZNv_QZ}e;yekNDK;u5ox`GR_g3-fKABO{v<&iGPVWvzD7GQUjnW}TgP6l(meE`uczKQIBG6d#w2dw-y=U)BLq$EmCn#-ML1{!pk6Xo2FINR|JhIeMD7_EP(6E_{d(%sBEfLJ(nS(-3!mgo}bC=#{d@oI&6(03_VJ)(sr<o_;8ox`#%zRke7qA!6p$@wW4s03C5m>Lg*usmD8Rcx`AVO8riMtz@jGI*vEJFqomcfV$-8p46?P%%I#5k$yCg{}W-NemMfVD0MBLwvfl7M&I#41(}v+td$j>9p1EK9AGWQr?NM*Vhj%OjCN7s=rWEE8Q?8@&qsPfdrPW;QSYaF?^OaKkh47;)nyDx(Y%a90kWEtv=xC;<?L>s^hCI)Z3NIlyQ(>yV!+@6X!N&!<Rc3A>Wc6WjZWHh!tSGvYbenmekp2oW>ZM{c*x;sJwFE2%VoPVFUHDS12#V2wPcRUE!>Lq&>xt+|34MwxDnkrs{88IAF-0Iw>%sMW4BN$}fKvJ<j3NxqiMB^NJDhrFkWdo5y-GMT~^T5)0&JqBVzf|880FViiFzIxnaN2v@*v3vpX?(j*e-90ZRVY+LAp_5%TAxfd=J6gFw9Fjg;y`6eR94$IXzyxUIFsAtCS1U5m@iyLKjC^Qelrdams~e>bnW8>g<U1TK!ql6%r#P#(*c^Xd?*Gm>YrcS4$Y!f5sP(h{PZvUXK`GhG?pXr40S{}hqJ3JAXx95pmRRewR7ADkp;!GvYZel^Yc(BE;I>!~I+C>VhDLr;0M<=8^amJTqNku&BRK7)jR!4S;}s3$6!8v!nsl5^FDD4<Qd8|Mio`mw<463p+7^v!C)>*Bq|+6bC}~?Tt_>FCGt$_&)?Te7@+YK)HO}2?H52D9;Fsd5VtgW^vabM&Ei^iQv_k}xES+HcYP34o69S~jB5g^Mfl3Ih^@;OugA~x9%on`(2A3~UcVAv7*abv6wQVc@>z$zZRrLyx5ze5X!N7Ml@i(1pr`3|uq!)b0O8{5d`pXobF7z_w+W$b9zOi~d<8&=+TsuirhNw-k`#&fcCcxloR{EXRf?o6n;^rY@eTui-W!4_4Dv5hFgzXj*D!TUx`W{UTAgX6v+DPuW63f*cmdeD7E+aqqXAnc=+r^dQecW7tkoLebK^`7!h!XkgV%EggLZ&)+4!>cvug|gX(y-iB5W+4jPgn52USM2aux@X!3i+|iC08$AlV!thH~{lFw=Et|gX<{K@r2ldX*YmBDXDwdOUo%h%YYA&TDAWbnI4}*y~ig86i{fc$U{lMN>O4hEQ;}<IO^!}W)@W-PNpS!YmTtFtyT>eVByNy=xWrYD5%ZX^Z8&;?9$x=m#*GUl<*FmE#wiIaGo9-g@VQ(Rad$&VPR#NLUfY_-*q&FvvwE)#{-(+Y6*52J}9^Q_6yO*F?{ADSvxm*mpd{p@?ZxI+9&F{t}uZ{b)IRtb)MwcVUnNSYE*{f2uxh2pPlA_(Md_5+Ut~@qUHQSD4SPfQ|_$R>De&glv0q+r2+PL)v_LBxSb3%jSFJDzrthc?-HGrqST9=pJ35JN~3O;N)nlC##7^3QC75DZGd`L?svezSmq#!O;mNY333YYX<Ntb4`@l!P7%)r=%E)xsZ=xo`1R|2iQq7?CD2F!S{-B(Ty*#Gb@W83JO_Zb8uv15&MqxXg77+IA36f7e42$I{U=jie#d<lSkBqSSL8|1RO;519tqi&rc#QFR~RqfvTZ`783yj>te8Qn4XX7A=_aD^3U)N|U9bD)bw#U!N?Unhk{t%(XscK9yx_`=Rh%f{UWuzjaICAGdBJbxXp+2QT3M2Z^Z71#bo|A#h(IHa!ncZ2+I@>>&Lc-veUm{OCHEX0qwc=WQHAkfOaGg?+Fe+GWPQ6Z%aJ*A{04Fva3IrvVEp8Z0#`ych%<K7L_>|3fx~gutTEfxR%a8yM+{%IM&aE?t$(m)7#7`!{Z_X^<BhPvuLgZzWOqAZBX}ZA=gDf8yk!F2TAL+7AidISrW59Ys;j`8z(WCjO*aaa(ukN}?BO9%6q<@nuqz!MyC__tw1abvo-r+Kk7$@_cfr5getP)9-&aEQ5z4*<x^qkylRBz|v&@9~U&q+%x@_HQuFw_09L(?IrzU3~cs=Dh;oVX{NJVXkoy@AbEtT6~d>Dp$@#wsfCpM@j@jIpOYd{vCRwHZK2V5lH3(Nq9<bre;)4tqI8RFnrOgebXs%W~FI}#)skaUh5lU1XQxyQkZXBsgmK9u5H(X+$0%jwJm<6`GVZBv=sD4vNZv^oBL>Nqaj@MN1*TP|sv-os74Of>3U78Arl@mvmH7iKXmrWS!{S=cegK6(5v@cZ%_HkL1HJ>X<pjZ~%4U5+QJ7pOAoM4qZkQ88~Qv#~@~mZBu8ROE+72#zZJlqj){PpB+U2c`q&B!ZrTlz5ydElr8jA#%4`=%HTYA-p}=>+2czx&;UIca*rU#hoq)s!G?Ak6SX^6mEJ>;H0&MxfT<WaARWA&mp;H*_=VnCqTud(sp+MIx`d8Upj}A1tpBW^s?RB>6yS;2pj=?W?4@brRI|sp)oF|!#H$LOc3zL%9srhz^c8|ARMmVw_A#e!4#$FZ|-ObC>A!23;Ye%JVylo6jRJyO5H#dTSvBp2XZ$YaFlJz(I#w21p&)9^Wf9#a5>(38~?oBW@vb%>ynmcZ<j8#tan$RZ9Fp@AzR~p?oJh_Yoe{pxSG%hG5v!tz)oBT@cKvL?A-~Q$Vp(?Jpx*-P*F&_{<b-bMefBxF4sxw|3D9$L)7_);G<frJ&5R3sAX7by0wu}Jes;=J(cD3_Z-FIyKM#&)X<zc8Y72NkSsf0?%A94k2USOKt9j>k97kQg|VwQ5QL1Y`G}{i^-gw2Q{%)XDoI;vn2Vx~6#k9~v$Vd;p`sw=3VpNl&L?^KrKa}fL!Xmpv{lk^O&8Ic^)^INQy+|`7I1__$K5v7WIH2~FpuJ*Zy%#ZMU;nCQ&j|4DDC$_6|4#(q(eqXmEf1oDRsp9q^ggY1_`!#L+|3KAvD)ZW!qke{?)tG?ve<!V4V{fDm#m6A}H|JRXac!O2Dp2XAsxc+|Mkg$e?X8zHVfF4Ksa?3Ucn}7hYr(9&{p=a`G8v6s00AhzeNzIo_tNYKV+I1#m8fYPZ|!to#(1-fv3MiITjd9icC3nXE}G_b86sZ9q&i*aT|~JZ0I^vNW$xtS*Td_qgY+jqOE7Kr>F>UHWw~|4>6T95zAXP^=X0D8c+bn2-n$^?<9k2F6K!!(EnUvJI+xFN5Q*3StEUh_uKg5QFj#b{>#xZBa}@{AprKLg+%D%Fje?h8!5+NG4W#8AmB$Ll2M9ug&mg-HpxLMG=*T@U_z|6XJ^cS_GBNJpMI|kcKYEF~}Y8LD=Mn?OZ5f1fQ?2*esdh<8h~n@dj1umg%AD$^f~A4pE1I2;*c-BwCwZZ<;L0D(W0y5g})b7tyK;tW<V>Gx-RybT7}gaxbmh8k04rlArjgjYQ#&sz7fA{)gR5(eV+8e(g<`0pKUVv3Z?BKoN?L(#&0zX-%k?c3^|cUqiOxeW1vyGXAMwpy*(VH3K-T>TS^wYFvI-=K$yH546_4ioi&2{4`<#SPsu|Wi?R*?L~<qkK{bm?$JT@1T2pNRm#R(BK!uQvUL%34~d!#pe5cB^Pwh~Vh$}#j+Ch;o`5qd4Y`xLOvgj%7y%8be=a;#WyPL?Q^5&(7Dc3hD9@FOWIY#s?9=ScZyc4hape^&Y2!{#TJE97du!m`rn@i;=sGJH$yM8WKa?F(jZ>rw=aXVuQT0n%FPZOHXgj084e1)o2Jx%)at1yA$XTbnHp+^~Dc2n<+jai?T2efVDNTi%!U)vWqTVEu&N39h+m3=-*HxYIGzzB<`kt(5GaikNWortND^VeG=7W@oX(a`E#XPzrzD~1drw*MntP)H?&CO0M4zIG4EIxT%qNl~0zDTrav2I&A4x2<lAha&5XjmiFDd;G#o=8X_*#U<|g(?W|62C+xwD~Iu^<Gx2Kq5@<MP4X?s6nBoWfKNXX*{%@R|n%`uo7T($kPgoWHst9g_Cp@(Vliga0hGneZ1hA_H`o^F7Qiw@8LBoH4S(qm=YL;209U)$$140Z)25izxFmoPq#4*3fPEf8-d*lB=uDv*Ldpn(H1jO)w;C`Bf0~#EZja(0^H|HfX}k3wtP3Y$o?)Vi*tHauT-?t?g~t&I}XWib8$<!$%`<wyQ8B9-F_YJ$M0HwFN+zbhBrdDpZCY(!_yJc1NwX`dW9-Maerk&J|+|=Y4o`dPiaVIWeG(<&IbAvi3}i{T$yj8RJkuhbI0rRuoL4Z(r}0>gDAV`qLdU@4b-UuU@}Ie_lbPh=$C+KqS6edDm*3AQNsSLgl04v9{*1jabYW6BYp%S4y9GmUOc|U)0_lRn(zR5|3u$iAMzWmoJ>O$rK;xXW6jYdOA3&AzltMe9VXX>T3w~xHCHxd#}CX=+#n-U+}3m`8R9t_jRx-M+gXcjPZ4U0nw2fAHp@~`=L}ZxEu|N=Rf%MGcZ_p4dQMto4@eX=NH{tw#B;TIR}wOCQmwsUJAApXX+WZ?glUE#vAm3gkdb7`lrmJib?+41-QG$pJOXvHf_1v{6Z6*+jm)vpqh40k<{4*EF>A1Gmj3#ZlK6^d<-@E3WYUVbEL*qHQ?PwH=cHrLQcpHsJI?c<RvS?7&@@jPi**#EcRN%6Q}e)dyI}p5b*<C%F6;;`%K>ONp0uE#&9*fU91aD*_OPyMTUv-4{2u^zpb-%_h+r{1%W#;1C7(avybfyLG9r;_`{#%ZTuWZ2$s<q`rSGs_nvNy^$iTAz;JsB-55K2w>RQWZuCoyf1I$I#wd$H2dcJB~cGkuuE4ec4uhN`dZhFd7WYV}Ad$VKL!$k6Ozlw@3=9_hAx490#hXov+eSos#fO!oZ*ei8%X9c#@ajCE=lUQ;?TX(JonJ<pi2)svQKU+_CU<ZQ`MIyfPRGX;VIbU0MRxV4r6mSeNrL9$#^9;}gn<GorpvF11l!fv3XIlq%ksG^Jq^y(6=?$o*Ejy)&O09EQ9I4cCE}Q$RtKI7g)Y*_L2ac5#j@n*wEuGUvStF_UslOxI6Dw--bK`x{21ye6SsKh+cQa?rx0zLmS{J9QAMYfzV5PI(2N%k|6C{Y_2I#D48OS!WI;ZKeN_9I5W&?b5cbigTvc*^=loIQhNts2Z)l(;A-bnj%8ueME$gX!TB+?<}ur~@KMbuiDYwl9IOg%`E<9m74*r}Yg_yNmF==_rAfN!<dGXA#P7JHCWSzNnXfFO)ys>8wdrS9OOny;^pV6j<kg<iR>x14!Ht3o$gf=~eTD6;*#=0(S9o&~{Huo^4AaG+DU$qS{x^rc)H$?CKzmDjzK3kA@3`ztgn&uJp*La6Pc0g4g=$A4TWFDh!rvUmNp+Lo);K^k06#U%T;=vN*9h*XbD7{qdajTYuQ>q7u==mxt=Lvv+PL(ZX0#@{ScG~lh;TqJ6hg3uhg9qD0MmJb7}KIKT0Qt%O1&|im~%OM~7Q-a<vN*>bI<)LmPH>HVK=Y9s+8_S*zm~m8Hjkk%4K}b6!y_Gq5oe~Q+V9_<moOUs)$k?k<JppTDSJC01h3rg-W0&9c87+?Wrsy=o8Mnq!G&(u1sMPy*MT1Q5lV$P~SD=xkKqD7L6@g_2MdRF>5_8H6Ns0S!#ir;glaTEdS@f*jf6T|#<uwvO+EfO2v={No9x{wjhN7#;B5lE?Es@mE7@fZ%N9_bUv=XzEwO(sj*A3@j`XBXDqM@r2LGQq7lxW5x36ufGU|lA^M3a+4sTDeyd3O&c13jMK{~Pc+Lj$eQ5EZ@9c)q(jD~08K8K+;On0OnfBwHAWgj4CB1mSC&P?!mnVdkPJQm1vHOhc%{n51h9^%OREQrrBp3iT9#F-S(cMWxsseONpcFl#8{p+qkNOaE;)C$HTWwRl-&fu50!AX-s!NR=PS_?q^uL&8cLfr_bF8R1`rQ+HO%-^!gu+(RPnc<TidMu}dj(&yM(5rxkGK{eI9?qYd`w(}_hU}fitb-YZfGO|Xyxwe@WW9Y{!5}8|NW&w|#u}?|mU9wScHR$SRQ6Zo~I4z7r53g~$M1PhsPf(^j7H>fpSK2FZ&tadaW~A91{qhYr;3f$_ju&Lzek!}feVK7oSZQpSVMy);uZ-Tdtai_Qmo<VjdZn!Dl~oP{j4E#6+NJAXsS5!bzL0K1U^J)yi!^W91~{oL-s<(^iH+ZIA<*ACy|$o6>a!_rrF!_wbb|novRlzprD&up+Uefs0d6Wy>0t)Yl+N-4-ItxB-5b<xm3Lg9E^i+hvi<)9n{Z&0')).decode())
_PORT_YARN = json.loads(zlib.decompress(base64.b85decode('c-rM%O>Y}nlKd|^^I(#aEbmQibEbvSScW7oF>4Tw26hGmEM^Zqb6f0xUs)oHRh5yEk@+6gw)fO*imrO!FEcVS^2`66{q5J^{_)q}&i?Jo*{AD=hqK+{?C-z+_kaHL>5He2|M>N{|N85{o<4s$`|0yve))8N_u=#V$Fs%R_UFy@(|^x*i!WzC-`sD`CLg~3_F=R6@btq!Z*K2Co-N+azTW@)i^JE~A8-DAef#u>ho3i_PhTIr``^W+aX0V(^!d~H2ginfIooa?9-rU*@$UZd=d<0o>E45mT@WASj=}5=KYhNr{qW1vXg+>^9*@!E_fORtdVBqTGjw?Jn5RE|d>jT>d)yzs4*ayQ*N>a~=YKtW9(l_9YrjkT=aGMX_-$iX$N*RRL<V|T4sqY?_#RsDvQD0#^8C2e@Y)XTAD0{Ehr7@6ERo^0v$cP4ad-=z1M66yBs;!#lHwj61{3xq{^$Gl;@OE-2zYm8Qoh?Qw7CujXnu>0JM=RB#mhms3NG+1x7-CCoj%&$r|4q!o;~lvlHPC9c?(XZVN$0b*hB7aZ#VBBfBD1a{_*Da=0BdNq_t(>q$@Pdt~=9)Z)copO(Qq&ac@=5LS|NE4n=S>zii~uhj8ylV`m>(I_&LZ!h^-0`QRa-^{ovHhYXy#<{=;M?>^Coyu5`!<mJQkq<h%hezo~W9sYV;p<`|x9dm2XC_QXE^nQ4Vuja3M=|0~&#~0f7<Qx#sB+`d)JsZM@$NTH;Pn-MuzkurkbnY-?qoz1xr@Vl7S6L@|i}i=-7rl2I>t<=n>C<lSguhEJrPSRPUEko;w|AYo<-m1SyZ5x~sp2@4=Atr)6|cIB5p+0!M%#OQF3r9!jbY7H2uAVfO=YkN>eL+{RB`W)$5I{<V7Gi`(3E?=08dmbs=SpJ&tA;}N!b*dNdwQf%&pt!4r{Q$&JX5;>Bf5ZZC=F*b4R+S!+r3&K6avEvXh;-w8Xo(aKWJCzt>2`w~_2;GlNFBif8}2Xts<TjMLt~&1>v<{hEt7ch8{*#l2+c>hV)}Dp7M_f7=L;A=hrAG34Hbvmrc^T$p<A#0ztOO(ZVNPB)E%Fucw^x_0l;Z`B+))x|snci-P_r8{|e^Zp;C92tH&gTMB7r#phYnVXS0f|;w4-9DXe>P*b;wZ>{56MI_4*Z2S47`}QAi+x?jlU@%Gb}_Xfq7;tl{<XDeYBad}*NrZPk|#a7>pbW*b*0yU640>m3?CZ_r>7F{ugnOu()#V1`J<Fr0kv*(dxbg`l{l2OXVAG2KZo{l*aQL!wEstN6C|E9zppObOL%XB9PYK}iw&41D|}BY9~>w9vIPrYh)${BmuetFgw_|u8(y~)=vSw3_KRIg0Rh!cF?!FbW~P5HDnLK6V~VpgK9a%l?0#FBrChMU+5_$nz+Hk2rPZ#4b`187xg$g~Ae!mns2@H!9=rV^8k&@qG(2fA5fK!U0arwn#`Yy~<AHa~|8@AOKzoo{KP;E_D2F>V7J*SZWbK~;bvZs4e5Jpk2KK;j!02VjAgellvd~B}b8G6n#n8B@w@e)<*1q%3qZP7&I`*GHZ53jWj9OJ9O*QJLZSV@)#IH#wS#%3xWlgKl%sE;t90K9iRJ#RtG#sq`guW`oEwFL6b?vpH<>uHU++}N`&KQeh!9r2W-2_*~0e#!v-Q9lmQk}lck*(m^Jv=Q-YS=f%TyK7SkP}SZlW2`$cXMfi2oS=?hbA0bHLU&NZw{U*MPDYfv|M?ZkR`p)(3ilcolWVL*RmPnz?+8wMf1td<b1Xkv*w-W@QmR|B-U)&%oy;NC(q==S-hYm8+Z6%4U1^gG0@LCKj3fEK+}0)`4VFN%%vq0VcT=eEiAB$U;{XyIeZ9t2H{x@kWbcQ%4S%Ys7%TQ0=)vK{kSd1a1GCPqT}mlR?K>7XoZvSUKVa{q|r4hV=%||7V;T@ONlU*49Ya!o$CnsHdkxfuAgTiuc9pE6}G2=58`}DOdL1IEah%#$a?`^n6J|XG{f6sO4uMlUuH~TDL;F#aR5S?1m>nuV4RqUO_|6vuf(K}2cYr(GJGxO>VX@#Ja}|{40GeZv3VUhGjn)zC8M7#gz&{~l(ZI8>F?axWpz9j<l{yp<NN4+#cZ-?ob5u#Ss|I+^NSeUEpB8a?y8jj9R(_=Q==~ZI8=~7GuWXQSw)SDpTRUN22x+6fKLhz^yCOK2?)))i${;?n;0tUER8coU)<Yj%Umx1x(iQY|FE~dg{g5Q4I`4kHWwb4gnmcwFKAj{`n=XRk!`wiVB5`n@1qNSleSScQ?Z9lY2OX*CK`6G<T!=5QNo<4^pV&MWs8CwJ$AhSn=>N?<y}hs=T3&*$M|7H8Q^r%jB*o;DYT`((9q2AM}V59z=wHU9#2?;!wO#E%mKIsouB52B@AJ~AhR2Zs*y%q7UrVH<5pCucv!2rI4l$nR$zs53VLMM8ueD1j>E`4ALb@pk1_Ydx7FB{-HDoW^uFu}x{-yHMAQ-O31UhBNRIgs_I1I`&BA`UWHE+O#<=O5ao}lWyw)t?BDxB#MUak!g<jC_;Fo#u)kL7|X+v}>FjgvqBJ6e*#-R^*O7320b`lu1(&5mI#oX2o)~|#XCV)H*(9zFfd&>bZqGBZj)74yZ_7d<dvXqS)4IWx)k)akxFgGp`i0l+-vNuYP0LE@~o!hx>l7U3l%EslxX1YrjaWIrquE>=%+cB5tYFFk+;b<#jjTDy#BToTv44v-41KVm`9YvOj#(Kc+Y!od#QjZ*EQ03^&_(wLxj%j(!H=0|IJ#0m5BD$J)+NLxw1_6Ef<Vm2k=DjXme8N0~5%#n&kEK~z7MN)uHZToj?F^RfUb8OGa@RDdqlu<HliOK#NE)3CQK~QJW?ZP4@r65rA_-ddLY6e|aV;iIP&n5I<iUZ@{#_@pCV=W?pua|%uA=+YHNy8uN2e$QB_|9VaL-oUMu4QSbu{h_W%E_AU0`jKg&#(ahr^cag5l`g7swEhg<&-f&(HYT3o++EY#8uXM4nQ5`9XYm<FAOK;Jq=}7;lu?-&JWY#jiiM<-^S%9k*W1tZ4H3Lk<O4mcx>DbCUfGpm0UXumL`D^W+{;5mjHElujEw9fY?ST0s|U5u^Z5k6Z<I)^{TDk%8es8PlMI!$@|r9IuHMB-}UfrmToElE9)(dW#n4(eGeCY~1bkZP7B^Y7V>tn0U=(Vq74cMA=&|v{wu99xWNm<#JO|))@G!w20z5UJf))UytTDGfo!jiLe(SnTY&9&~8GWYjChzg!(!<*gyeWj>##3y7A9U(g(BM7{zVBkC!V)H|d=VzntTecjsOu3zkDig5TLxYMT61Q2M6Wvi5%IQ;($V00>t`&HJVYX^44iod43R3PKSNaF>#p%bi+rY`zXI5Krj#mST@3MmR(+Ffcq+8L$eWDzdu4dXvK$DZ3K1&Dsu~7Fi~3iIIzBQ<0v;*r~0AzR5}p{QQldO3^M{6wVq7{S&7Gn7I{}pX@zpt#XMB$*iS~qZ~!5fdsx6?^aH<4N1==usANl6>X@voSX0I`7x_CJ~%Rpb2@)QmS9wc%b12NXrW%A(}pn84Ix@Iz(*_9YzfeW@PY*~YhV4pK{6hs3es$-;f2=qcB{9h!stvi&n>YGX#}YJn^TFdU6p>mT3~!!_QJt<r`vb&dcLy|qb+*UYuA(ZHHdML)wtJcme>oCSS#+3bb4WZFP6|uf?O0=sXM{^vMfo;LWwKU;k73K$?_m!^Zr(&<_Wh3vzRv`(1gVW*CfkO&M*)DRw_S~b4F04nTKmnwwzF0N0U0x2`eOJDhfMD(}SFV3KqbyIm+g!Rb?arV@sis7fO=@tsXg~VwIE!*FyzZ2=&p`(+0kg7*QBX<1^@=ojGgPE+%>^vq@_!g%ho+^0q5f0fQsX2*I(|bPs1Y6Sf8oiEqGsaWm?O19u3lvMG35@yIw-VT0G!IRpL@lSsyl=4c*~O1MA_X3CN$VL8Wo59fG*Pt@?%$}M9S?}`k=?;ExC)!EKtl{=C3d<e<j-2Q2=H!@q%i{#q5Ot_o?W@7{*-Eb7$Nfc)Q=e9JI&7#&!+pjVPddw<N0R;Nn6~%H|>Q05;TP07Vnr<?C%r`Q+t_<o3mdXwmG&ewClMF*;b+Y9^tLG$TE69OVWlwXDu2V=-$Y@FHyEHrht~|*?t)?f{av(uSn7J~^UcHFO<b-p0ctV1ri|GnDQx)Xf%@%(R2S5t)C<3X65M_yXn${{q2YOOJyRbV}aR=Zst(By=fw)k>My`kk<$Nbp3Balv*c7bs$rCEIkVBZsEJl&4v@apJI&K9g*f6B2spiNo6FUE?w$$s4U*x15FHX*QMO6TlnB0ZyGO?SXf1EDmfnH{#m`Y7Y8jjTJ6T!h)7Y%P7cod_0{f>Md-_t@doJHEi+6Q60Oj)G%+_aQoTyo=Hqv)u%30li4=mpi;0;8$HEGSSjI_wG~%F#--tRg7TzNDn)j=<(d&NQ+_=>n>$Ik)hpwFTr8;p!#d34Xxoaj?#iGG+OIQX!Vi{zk5|q7IQxoMvB<Gq+--M(dI3^-v`putTSTBV`q6HEwea0_-;-@to5005uyLt7uKx25N;@;q<=UDFvwK)&7_c2N<n52QgEdjF)F~v6oEj)V6a%7Z8TKhZSn$Yrt2}lR4Rt9|A*RVOt@Txz?sWTR4~kPC<oS)WTr{4qYlFr<UsrU+84c-;q!YUGq5WAqZ=(<5(v_P^~tfan<2p&dI+adt#mT=Fh{@6}7sPT9PH9ziCX~JP@<w_4Xp4tF3*KtctZtr^be6yR;Q<4v}{r1f%hmX>Ssv2RYDSF$tVrQU;B-z1_WrMGvCkjx$HOo>nFJ>Pu}RWeTRq9%sN7HV$5R2g7Q_9Rb!K0ZtMjLT-)Z_mo>BI-$<y=__H~x%Sm8WaKR){DWw@&en@V?@V3@c8LVJz4Tafw`RlIA+0vH24iGUeHjF(<O21vZMDSnYi~G>+$^P0=EG}ttAa~KrhQ=g^K_Z?&4vIce&%wa`6Gl+(?Tmx=;JelC?@N*QWa<zohwlmM2PYV_#jY7LknCytY1Qd<-LsQoKl%4DM6lU`ry-*@nk4FW{GLUP-vCv$wkzjtDUYu%X0uZb6Z#7AnBJHr+d=BRb5on5<1|V*gwG?Fv#_deC11t=k%@N96d$1)*Rj7Rs{t-*1__hC|SRencwRG#8@uPqb^HX$kuojZwgYZ!3TG`<s<VfzfB|*_L|~cksZZdx5n}kFpmlvet~yDvR;2riUT|YW0%n-nfGHnfUkh;g!yI~%*BpaF}L2D1fvguEgu34owK0{4~NNs6WiXiy?WHA6>fIb`5ybc6d|j!P1D6>$cECw@(NML1Uoef2q~@3HW_ET5iBN*kz!0kq>V(S6hh=VRe6mT4JqjEaVUd>A7cHcOu_=Z<S3L&op6YI)R2O5$pGK<;y!vMDcsLS3xuJ3=+kE+rEXnFce2fd0{!grn6Hh{oHv0)tY{Okp|(s|fQ%-9r;P(K4{J2s$QV%_26=i80n7lT;DFq3IsL_if`bg(^GpJQM?`>`z|>|Z^XJc+j$PSK0Dg!~!`JN+i#5b7mUTS%?6&7A?>rkDZ6QeIa>sstE1xn;{+ohPDp~L{1W-!{ymYXUD~A$tY0iO_1D>=c&#Ps)N|-}Er9O*<bQJwj((I*@Wx2sRLGHaq<4p`5Q7Q*lV!E_4O^j(I+Gik_Ef33YPXG;2#uFHn&_t<JHHr!_AtwZx&G_$%=bYFC)HR|Sa{k#;Tl&!&Ytg0f@QT`QVB&-tv7JE^J#{P+#nGvsD2|ydZox{M>rk_-vCT3OYz;&ucubw&TJp7AIzXw0m6Xi!MKG|B$8;PSIB_yrj8HzrwwNjSC&o_E5MX;P+95f2Yi#?T?-J7eRuoQ3Uj{|KNWQ?-L)R0iSsidd4I!EO@dAtm*VZ{X1c;3=Wdp0=;J7xr=g-tEK<0$c;y28LCT;W|qHb3#ZzG}$`9z3I$LsYN1b}QX&5W3VHvJ{cv#kDV@=*^}b0^@^Cx@d&>73^4M`X>8N_w0~5YPj}l0y{-ObES(W(1E4@vbSRa=uy_C-!rcB5yJ)U;tf^kw;7Xw!Rtoph7O^FA$bvPy8vY$z|7~hb&+aL&sO7LT1!E+^RqZugYH1*@*^{pPMx7?<W+rN(xF^j@}#-MT_*66CE}|sFcNaDGi`wLO`aJG(S7RDF8=4<v+Mp){?a>q-9WI0!4@e6F;S(xOHAdTCCvQKs-WH%%!EY5_+;apBrOK^f+R<`H5J=G^~0R=?>{4tHj9$wW=74-pK|)ys33u8Gs+-u?D)uZ4%DyI#nycg?3;=iF|{aqhQ1EZ)16hK)Db4#9YEo6Y_vobW#$1_5ULh9|(U4C`4MG!Oxu_d;BeB<=C_cLCc{Xy4Wh^I=GXXAw4)F-5&oZwO<yLFiVN*ClTJatwL(dDNV<du>>{_%V<e_9BezX|Ldf)fo2}aTkDzjaV|LQM-5nL1!&lc4mwgs>bSW<T~Cr=AypQTglsYx9y%>}W_W1M7WU>g@1t6Xhi4?%^E&E?wp3_o1>1~rER#A8L7se5-NpduQ*v&CBeNw|O;v6-^!==eL*dNG?7FDL+sJ)8&m`MuD)mIR!y)RnR4_698qtGUU+6I&XuU+HA&ZIwT)~L&Sgn%qtfz$xsuHWnmP*<*E2idw2fRt~gKT9jahHWZ(C$stv1%>P!bGEj^rP@#Dv(mpDPs`@sl<gNS7a~Y7%T;Q4>mMVfdpe63Kr3WzDW*f9b$|iB;|94B7#t%P$bNQ0*I3;T4Nh6)#CWZv6*ze3v&|)C_q>vBZ(v|1y0F%hDEmG0u>_|he=bsNwB?~^F=CD82_k9`E|z{ID0v)g-Xrz&@T24MMBw#s3WZraT5HjvcF>;z$^n?mZ$KHI}uouR3R#>mlNXca*aLv&?4+okpq};WUU75h;4(>MAcHO3w5TcPjU%b8AWMfv`AvWH}+fjL_#veLd?F{LakI!PNj2-1uNL8fF4OYM^N>H_^|k><ni%Le!hHgHXr}~f>bnfDoO*}4RzOqDOFh?%^8@$E7IM%yo_*Z#WG8P*JBd13`H{i)h<;tBvS3tD(&D?LAv{499$?M!s$=ZHl-RUr7BchXP;ER5)?!NeaebOMI*zg9)g)m#`(y}BXOO0d_36#8-76@BCaH)9)%J4MC~GQ?6^$%bu6f{tPOvA)st_yGRWirl52y+1%QJBf`kn+9_34%wsQDpe{{UV!(!2h%M(=lh;rP0Tq0Vmr!E8%DWvn%p2TrlEDIvlTMYTU9m|8jv==;LX|{2*prgGY1y)6%G!WGd$y}+b%^FJ*ZsH0H%vA(~pNn3RVj`eO7}Y!(5vFhcSX<1o3fAWK?xUm#>`<9}pH`WQ&@ic$0+nSgbQKjIU37oeBatCGfWeT1r54v-?Xqyd<s<9Gh>X4%kjzBx7!VB%7y>vkH#DwNa|!@O+MZlRqgTyTrey?Q%q@LtpLdaz0G3duun5;{mKkz!KgflXX)jH@)zV(o*x^#h-V5~;#M&ebkwC<%M6$i-*;4F<K!;kbv5ivbggIXAI|D40V`WapfOW_fwo5Z1%6LUpbUhivi>pXV!aA{aBW;{%PDV|Y1PpArza(4D!d6~Us~rAopBt!3GE0o4q~%Qe?=MT}qEOy-9i1deL5}f0eTNLlMVJn>c23ueN<NRx4;JMxo0PLK1p{Qkq2ER9<6_~{ynJFEhDk+*gX$z8`yiLE-c~TSV5}q(Xt#aYDjNNR5>eDBbxqs`#QW`@4Gf2q*A@XQF3USkpkXEH8mx6sg==a67tLk~)jI9)iG`E<>w<v6NmXZ|bp1A(yD!VhiqtgMG;L<LkBW9%QEXzFWyXyZ@^CzLRav(>Y^<hY2w3yDQ0O~_i8@!iO6AY33L8i=ccK?}5&LX1)T<!?99c>io$=)6m-Q&O){k(xryc6mP8YBNFaR1vyq1AHNY&?8a=1XHRpkFLyhY2rfFz@8)v#FhHNt^rLK?*+A<-RYa-vpz^t;Od5!E>ud7@pPV^vV@Shql&%Qbi2N4Ogl=vZUc#Z@Ow4%yX9B>UABHpI$PuP&&;GFO|%s+V*IwZVK5jW++C#ikNz_fZydle%WqjA#||*lN$}0xUpHqNlnlO0DJqC(~*>M5)KwxeAR3sE4it^C6mdN3%ploJZ1Uw=gv(hfU#fn)+g?1dtY|+J-TDfJ&UsPmAkn$xOwH92OMO6%CYPo~_a+lwuJowl?w4fdelHPlc6ZBXyI|S#O4uoCN=ryh&UOmGnu7xUvWcFM!HLqMB2^pbbj-VC3pkxg8go`W>qDk%+ls+mW;Osk$s7Yw%eF0=Ho;a!P=&GBikr40qw_@K$RufA2*<eE&Nv2O{L2P_MA+wZBzrevG2*N}|N-O~Pk)WE*(;0571Kk35Q=yds@(%$3@6vg0&=O4TY7`lTERN>PO_>OeFvjB!R%kYWHKrx(yBBuanB(5t7Jp$Gb-iZW<gp8s2{qZmkHn3>l~hlJS`r>QI|v9R&DvW}jDF~F=Uj!8s_1+4FJ3ZyQI+~n+WlHXE-P@w<GOFvNJ4JA#qtanYEkBXL3)-%fzYT_e=j<%S_B$DGB8AbYP4#jID7nxDEd+3SKC|?+d6cXQfcD%kVw?40nV68!JzTJn12E|8DRd2$=IfR2FoexZZNQuMGIT07RRK0M$AZU`pr{Irbbp|bC;-n;y=x_)$I9c6_VyPuq&xdRfX6iBxJiUBLA^*eXxN6sFay%n$6VdAOj`biiPthH0!Yf1;ulx!v)JqgQBL?H}L!j_s85!8(kR~RD|NJOKj-VEf6q_R%6n;jNmlk1FFjgM>qHm3qKtjK7HFBAaQ4%CMH5DT${w3vkbaC_8@?JU?f?T|{sagpL5WtjSCHhljJv1;fLZXIBENHA6T;37T7HVgTa3KjU??z@ip}ZiYd`xLH$m6d{p){peaKwmVF~o6iMKof~7C}5FtB9PcA;75X86>OIroir-q}wQ^<Mr4X#H(lGjTFCX;)$Sb7s2wHEa$eRMowZIXw?zR*%eEx*uIKA>uE)n%czbMJgRL?O)Y`NORXpd#huEbc#qLL5IRa3$<sJ*e-+h*CVSuJxsy7({d`P%@!2-b?USbAI`^&$+j{HnMjdNNNC|fw6F(SMBj;>@L&A2A@`{YNxckwR54I^4%e5}+sEY7TPv8A8udz!{IT%md=Kk(c6VahKqFr5#qm<<^Xn;^wC&8DpSn4V{ipp4DsxNaRBHd?-#h2WPD5zDfVBkk-7}2_`-Wh%oMaB2m=zd#8vWvayZGhKOOP>orf~RqAI4s7qs|uu1Q7}@OW2>=`Bht%OAxD+mQJ)P(inAOhp)Umk0Ei^|2v@V`V$N21b7f&W^>jglp**w*b!YR?PAUp?0>CUETBKIl+@7G4NXWua*$QSj%OJB17cg8Rbca*kxo}`e!f)U>4oc|K!n(+H6HbaOz^2H2S_0fgNQ}?{wi#<gC}QmmjL_=-Y9{n*){kile$jI}-gYcSUxGK4ZvcQ3Z7iY@F+79Py#xCV(jf+)SKn1Ycfr&=wY#1rb%bX#XfT7mbU_PNM>G%^V0sNm^I-}qBm^7Ig&YgcJz%;Q;8z-H;m51dvCY#IG?+t#z}`_ERv!;J)(>UXLRYN?Iw<c5BE30wfChTx%X7d?zGVH8O!Q1D$pOUlS;jmgCl|OMx-ON==M{MD)X?itgsB~L;e_i7J+`2Wu4!vi%S2xb%-tv6GSvp)rQ`~JaUfp8U_fg=`_$VmTSkWfRniSY7jhe@TWyR~Pg2zRl2WD=#Fx^nfHPV;T9b8{)B9;tsAsJMzd*t>wY6$`5Tv>VFSMj?ph$eTV|5E~xa964Du2sp>rJIC7=evxQcCQ*d|lAOishsj$wSv94itq-A;%(!=GYpNRJzik&if1?v7n@7Nw3S|32a}Al_tsTNjHjC27&>a=y-<8pyG73(OhU?)&u0w2!lKZmswI3Q(=WkLOn}`F8!lcoX|-Y3He}|b}>Q|d^XNF*~jj%DGej5r_985xaLn)Au^va$N3X#sY;P&(Jzl8pndR41!_3GwLS#^M3j`mtyCPWhuM4@u)*i26pd=iIf_Ly#Cb0l)dsr-1m}Vl1wpco8AwEif}T#TIRbKwI4*diZs36PP|d!GR3(D=aAL(4vZl1sJQ@+dmscF|?_mm@o(|`St@=lW?e@{UOiGGwDs~a%4~iOuFzTV~6jt;?&bz23U=+E7ye79UDIU}t-}H)Q6u1TihVnd7Vn$BHC#LYn!a*0Rt~QMzhzX4DhAc8Ew5SH71Qzlym>WvFS|6l}VF?(`07$Uja)3c(zy&!(ASzx0h6*VmIjgkIvME-VLSl&Li6+r2LMB-{?(ZpZ0-fMmQb`B^0N&r}5$DkpvL~75&1bXGS(i-v159JNOG)I5rlQNTXFI~ew#(DaOpz>`u9uLT8QX2zNpLNo6_;_GzSa4PYCT4RK8=&Ku5X`G(F0m8BNixc>49vWDe`zF@4MXeN(Ke<ZVCD8RPE(1PtY=Lg>+sI8O2&sq~bLegQ`QsATS|O_5?#qJ$Mle<4q1-pd4rw-#+4OH)wlO=$T>eER^E3OFlKl1Qzls)h?Dv&OA~%A*V1_piRKdVh)#&POAIz#b8;fI~8aR_;LyaW=Sova%;cC0p2f4)MBersDGeo6vjsKXz7+>{?azo+LjNnwTIOH)mz{@EM>^x-BTZS{|6BQA_)')).decode())
_SEED_COST = {'WHEAT': 10, 'CARROT': 20, 'TOMATO': 50, 'STRAWBERRY': 100, 'MELON': 80}
_ANIMAL_COST = {'GOOSE': 300, 'COW': 400, 'SHEEP': 500}
_MOVES = {'NORTH': (0, -1), 'SOUTH': (0, 1), 'EAST': (1, 0), 'WEST': (-1, 0)}
def _fail_closed_units(obs, action):
    """Turn engine-rejected unit orders into explicit PASS without changing state."""
    action = copy.deepcopy(action)
    seat = _seat(obs)
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = obs["private"]["inventories"]
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    seed_demand = {}
    for order in orders:
        if len(order) >= 2 and order[0] == "PLANT":
            seed_demand[order[1]] = seed_demand.get(order[1], 0) + 1
    size = len(farm["tiles"])
    access = {(size // 2 - 1, size // 2 - 1), (size // 2, size // 2 - 1), (size // 2 - 1, size // 2), (size // 2, size // 2)}
    for index, (position, order) in enumerate(zip(positions, orders)):
        op = order[0] if order else "PASS"
        x, y = map(int, position)
        tile = farm["tiles"][y][x]
        inv = inventories[index] if index < len(inventories) else {}
        valid = True
        if op in _MOVES:
            dx, dy = _MOVES[op]
            valid = 0 <= x + dx < size and 0 <= y + dy < size
        elif op == "PLANT":
            valid = tile is None and seed_demand[order[1]] <= int(obs["private"]["seeds"].get(order[1], 0) or 0)
        elif op == "WATER":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
        elif op == "HARVEST":
            valid = isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
        elif op == "FERTILIZE":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
        elif op == "DIG":
            valid = tile is not None and tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("animal"))
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
            valid = tile is None
        elif op == "FEED":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
        elif op == "CARE":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
        elif op == "COLLECT_FERTILIZER":
            valid = isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
        elif op == "PICKUP":
            valid = (x, y) in access and len(order) >= 3 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
        elif op == "DROP":
            valid = (x, y) in access and sum(int(v or 0) for v in inv.values()) > 0
        elif op == "PLACE":
            valid = len(order) >= 2 and int(inv.get(order[1], 0) or 0) > 0
        if not valid:
            orders[index] = ["PASS"]
    action["farmer"] = orders[0]
    action["hands"] = orders[1:]
    return action

def _fib(index):
    a, b = 0, 1
    for _ in range(index):
        a, b = b, a + b
    return a

def _cap_fixed_purchases(obs, action, base):
    """Cap fixed-price buys to a guaranteed executable quantity.

    Planned own sales are credited at a conservative price after assuming the
    opponent dumps its entire 100-unit shed into the same product first.  This
    preserves every unit that is finance-safe under any legal opponent action.
    """
    action = copy.deepcopy(action)
    seat = _seat(obs)
    farm = obs["farms"][seat]
    money = int(farm["money"] or 0)
    shed = {key: int(value or 0) for key, value in obs["private"]["shed"].items()}
    inventory = {key: int(value or 0) for key, value in obs["market"]["inventory"].items()}
    own_sales = {}
    hires = int(farm.get("hires_today", 0) or 0)
    quadrants = len(farm["unlocked_quadrants"])
    room = max(0, 100 - sum(shed.values()))
    for order in action.get("market") or []:
        if not order:
            continue
        op = order[0]
        if op == "SELL" and len(order) >= 3:
            item = order[1]
            units = min(max(0, int(order[2] or 0)), shed.get(item, 0))
            start = inventory.get(item, 10000) + 100 + own_sales.get(item, 0)
            for offset in range(units):
                price = int(base._market_price(item, start + offset))
                money += price
                if price > 1:
                    own_sales[item] = own_sales.get(item, 0) + 1
            shed[item] = max(0, shed.get(item, 0) - units)
            room += units
        elif op == "HIRE":
            cost = _fib(hires)
            if money >= cost:
                money -= cost
                hires += 1
        elif op == "BUY_LAND":
            extra = quadrants - 1
            cost = (1000, 2000, 4000)[extra] if 0 <= extra < 3 else 10**18
            if money >= cost:
                money -= cost
                quadrants += 1
        elif op == "BUY_SEED" and len(order) >= 3 and order[1] in _SEED_COST:
            requested = max(0, int(order[2] or 0))
            executable = min(requested, money // _SEED_COST[order[1]])
            order[2] = executable
            money -= executable * _SEED_COST[order[1]]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and order[1] in _ANIMAL_COST:
            requested = max(0, int(order[2] or 0))
            executable = min(requested, money // _ANIMAL_COST[order[1]], room)
            order[2] = executable
            money -= executable * _ANIMAL_COST[order[1]]
            room -= executable
    return action

_PORT_STATE = {0: {"last": -1, "choice": None}, 1: {"last": -1, "choice": None}}
_PORT_CORE = _CORE_AGENT
class _PortProxy:
    _market_price = staticmethod(_market_price)
_PORT_PROXY = _PortProxy()
__version__ = "v17-top-complete-portfolio-rc1"

del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _PORT_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.update(last=step, choice=None)
    state["last"] = step
    if state.get("choice") is None and step >= 72:
        town = _get(obs, "town", {}) or {}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["choice"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    _ACTIONS = _PORT_YARN if state.get("choice") == "yarn" else _PORT_DEFAULT
    action = _PORT_CORE(obs)
    action = _cap_fixed_purchases(obs, action, _PORT_PROXY)
    return _fail_closed_units(obs, action)


# --- V18 P0-B frozen task-DAG/local-repair overlay ---
_V18_PARENT = agent
_V18_DAG = json.loads(zlib.decompress(base64.b85decode('c-pnS%g!x3awhgJH9iC0FFh+sr>#Plx`d;W3vEGYG+=vVcwpEAqtWl~y>ewn1{vQ+a+hRa0~`30i;O!Xg2CW_|K0!kzy0t3?f>~d{_o%YhyVUN|GWS2FaP3x`Iq!d`qy9n<#+%1hrj(#|NM`?`{j54^!LC1`s4o}e+=oD;QsYrfB9V?L;v#kzyAKu<Ip$`{hNRO!yo_dzy9Oz|LM>F{M)a;yT+CL8JDIh|M>gA{Z$tKF)sd6^N$bymw$=B#Cybl{;}5Y{^8d@{^>t|N2F_}JkInVfBp6EzMtDT!C!v==U;!jzqlWN2%n$$<<w=I`fq>##UXxh)f0?U|M+43{P0>jEEj09K;+c=Ma=|}aLYCNxCW#2JCni2yKxFj;xOX*l?w%f_u~u`CEpnUesRRl&V5PeJJ5pv%4FD3Ic#Ljr*W!<*aj+fag;iXP#zbV$o<Y>F)iaSEt&m@pk4csT#vy24Cpc-ElCv~p@}O?@Qa!XkSgpJ@#7*3;SOk#&lF*t!V0$=fiN@+@g|9*ctl`8KEF&`!<yPN7TdX0KX87&m-Sp;&sCve`!U!3y-nZ$^v6H``nP}numADa-~RlEKmOr=xzPJDn-7=C$L2vGi&*((wHT)F>(yRrL!0ws+H|wrV@3Op_)L|cqJ07XMXm90^z+3HbB|v>b7rW5FS4_Wu93YM6=wl@XKT~<<!s48QGf7_!tcNP?N9&sJ0&k^;{ZfGcJcs*xo)Da*^*ARLeB<R<nYGvu9KILzB3pmr*f{hsV-Led~e&iYIw$WXalOhH7&cX4UoCAhc@8HT=(~IU;}>4=EJk!4aV;SlNi5fzkF6m&~ALOL3`*hXFy+~amn7*GPFW3zU9CQDSSPJEi7Pj7`6rtk)nhf_w9fB^KZZZ%isL^+i(BnJM6W1VLL1uPw9oDL*w<Ok%j|c?Ge@=AKD!lyoavQ_%`o69`Ca6fX5H?Snt31e+I^Jpq(i}J1J^b^7wrgrBbHv8<ai6sBO)zsB`Ji%*glZ&dp5qo4NM!U@y<u2u)VcH!W-0nyh!O3{BRLx$f`fz-0ZH?YkS+2F=eGGNj_4FAh53-!GpzJ2Wz12rphw#zB7B+=2P|!u|^gcHVjX=pNYt0os}e?aO{SYD9hvdyI%DG-weTk%tC$%T{y^46AftM1->~-(Hbp(^YIs-T@6-0Fm0(p#^ww3~SXFK)c^6_*eMv@LX%7XhjcDTi@^TTw8nE%$0v)uDz4wgL?*7XePYxqK$c)=5PP>m&-h;N!r$y+=JnSX4GfO4o%Jnu5jl@+=0>gO!#Q-<S1Pz-cxz;<|7*tpwSXK1>-d7A4h1NZe;G=H?SY40|TY;^c;?St6%sUf;lztnWf}mmcRe~Z~ybJ|MchkW6#i6&`T6(<+MBn2}7=w!AG3F1L`=tS^Ap4LL(=neCG!oa*#55&DnSP47n3Dt{s>{;lm3DWHu#V7Z)jR;Q1y8Z3a)UqN0FYQ3Zqd<HSq^9A%Qnshv>>!UDe=__P6jMV$yYicwC&UqPI7;9_cRbkyqjEEzq@!28#j1&KphZZRS$G)<^F4n?yy0hBKInrkN7VdDt@K+31*G{Xmv_oWnXPr!$;-*nV`5$`7{%7}EbpZu8d>q7WY@Q$D$tk~?UHQR}8|E`JhV%K6gF(#jq@%!#i7XW?qT9u&vShbJ&Jn%6Z*Ac7>ewVE<y+B2W_mC9l{2+9dKjTOy5|2wJHHOC(<JfATJ>Hm7RPOgrGcTHL<e87MRl{j0e?b~fHnK<P6a>q0#pL}E5wG>1G{Ce`KkQwTx!|qk`EfQD|JAlwPi*(A;qkG1qf>rc6_B@8_9pgigdy_;x<Xp4kQ@vd^a%em7B_{}d>32zO7W*wN_*OrCZqBBi!YT%DEB;JoM(SdqetVDn$N1wh$-k%y7pt5euFk`4iC^E94S@o<{U|sC;#o|L^KxR(qzM!ww^Eezo1y>SwGuN{P|RDobrN}ooGuW^Z-ts!rD`;v&TxWL}0mrKJ>`eXBtrRZ2f?p$%mT2dwS-znWqtDO3lfCWzsdAzW(J;fBNI^ektFHs+dE^);RKI2VokPQ{%qcQ{~Xt5#cIke|!}x=h5791-+HTBVN2K7?NF!6kPxEC7llnjc9$8K}Y?bW@WR<mgj`f=ZfLdG{(STG~21MyBQm-US0Fx?6&;2kS|wF1atVW1X5PBMB@v*5R`*WY{2BexR*z{GA@z$3@!KaX&gFbEfhQQ%7rXdT+Om_U7vCJ^Uv+a{h)sxLp(I@LL`rf%r^AJ07-ixHtdBHsd|M*@q(s|(9BxwKR=E~cs(iQO1BSsoO21{Cmq^@h(_NhPrsvYzb!Kl<{4EEMqLF!{&tHeKd0Y^k;%FY{W-Amax#>0LEC4Yg3I#mS+pC9v}ZskS^zI7;t0j0EI$Um6>kIEyH{o%Lzh1sUT9ADq7jqN)4h;5jquGRw&i|+IM|Z+_f)a11or{+MaL{vHr~v4sSBSx;xm);1qO*sk@7tzZyw6q4ZJ_(MIf?L1@^F$*x4WLo)mbEn1@3)c+Q4E1gVX{b3u>CLKAjS?1Z6@FahD7o!^0<Zbz-pB63=q5os<=I?3!lBu_TmVc`Js+MYw24oP(l36i<Sh=QbvTDy^~vJ&S-r1@HMIfyOfnB@^|n*({6b)o5((7XU6p~*<8FW}M$91&el%Q*yqV0`dF3Owh)4r;#tTo~jL10d+0ED<(-`=gNggTSdUSo6@z2;oehclrepcKY6`*l$egiwg%^QL>py3(e!+D>gK#wRfBKe}dJcPbA0vW#iUd%5b(LQG~i17vn}f5OQ4@rz47c?&dVUAsrD-iW>^{a$YEZir+n~yyzbU3BJhKO+N4)y~^KZH7czFK)rIhrE)ZY!DsPm68dueHjlprX6OJOKf?2x0$h#%V`v%Em`|~~e~Xu<K<a{dgkt_twuSdT%T<Cp0yRqdXJDN`Lbm7w`deEOcK|M@DE3OvGexx*i4-Pn#AIf7G;yKKo9+DvHE$p1oyqIx7(!OG=3yiT{86!YfClsf1~WJ(5*rbi0UY9gXx{Sx4iFy4NE4i&)?6|+n%n^($9jqkj==?qVy_<!l=BRW$C|Z`UfK#<EkW#xiqEp&m_iAGy@FDg`{M;-96?-ZX`r?aexVH35EG;>(9#InJing<1R#-=W;PQwiVU20EeE5Q{hIvX@`wo3^KfVa!w%-Xn8ytUBYYPI<qnJT7X8)w*Hn*3R}i@_8ka?wsO6(iS<|_8Q1AW)q4tZ-OlY|-)Q%QNhU?0jBS3-eU4gaZd&H9S0%>{X{g`@Luc2nz3DB5}f8CJqt;njY5phgEf)SU}r<E6~M{k^|I66}qtqL4cy+T<zq#tf3Cu8gOJmem|a!8XJmDabio$RFBxi0wHP22f0br*x3(U<GDecX`e-=-t1^HMKfNCR;>VpnQAU19C&uppry6>v?o%RSK}ha)-BmW1h$H}33rhHJ(5yw~F^v`!^(FtX7kc;%CIyc8Wgq{A;?-Svz_aRhjB6=G+u!XP8lvHb_jr&y~n;R|V8d7jvM0<o*G#_tHU<aIXw`9R2PhQIs6|8#$dqt7+|<ih1OS>dM^UyduLn0MSY<6ZIEOtM}xxJX^F=i=r#HMja-z}53kLl6boV_5@P-rM{1#xTw7%Vvjve$z}+NyG9MYz1PQ9H(E~(vRszB=XcpaKO)Z@$n#R@krPlu{zCU&K2dP<kD@qxCS7a)TUm=-@9DIyIeJyTm9o8`G0CPA{M7+GG2P#I0A*4+?WBByX*m(m0y569p4KHiBLP5EFi*iCov6C<AOO)FfV7aF1k|FcDAE_%Qkmj^{|JN@|=4!yC$up(}Zef;`ocn&Dt2m#`UF-6FuJP-kXYpH<k89@u5gJpoEL!Ly5am$RzWu$`;bN+P=VE=Cldd@|3}c6!&S>l2ie}sHsI7h9rD%9iaaRYKb(3TB0iDniapiW$Lpt`~0q1f9(0xZPHO8fv>|0sJo<VNfLQZ+iKAz(2-zNtjGF*U2WdQB5S6+a5}ld4<Mg$e}My#H`6w1^rMQjg-KP64OEk`*~=b4t$LR<1G<7`DJ0(6l#P;-Hli?7Dj$G`7+m0rKcE4fpcFJ6x9U-fR}N)1W0|$b`T|;BoH#v5ck2~sIwwl!>|kZD&^eg!#c}{0Zi!udR|g{P?d2~Gn?ESe720~^GAnV<hvM#uk*qe0KbQt6i3<0f#^xa64vpdq8a8Qr2oQbawCG-TA$^nS$%T!9w{1K$H0h4;@{R=P#~DZAg9scTd2JmTraa2sHmsP&fRw3a1PW}*k?Z^o$CSw^cVDr>H|8&y^AUt~f^er{4cosL6Xru?^s{cyEJmw^h5E%0Ny4*nG;GlLp7z2y{^pvsj{yVN0NUXOQ1A@J^qiwRs$cA3{*3WbnjWxdW^s{MdJwp^bmY^QujR~Gc*<odiVr7(8&^C}OFdKYA~3=o1%*A?^<qYRE@aCQ=i>fYq3HX0nP@?P#J!X<VbxJkB3h(<B-f-5U?I&@+xAl1JI^YT)1#V&X}Y<i0o&h_lZkE6C*a4QTC?s0#Maa~??O^q6-mLZWB`dDMz^ZS8qseqwCZm4J4qAv<6dk;qFNP+!o6+;%w43|nu@m~n&CxfT3%ydKH1WB`E+H959rfvuKUHix)Z+_V7DCif@Yv@Hue2{@|TT0lDFz{)H%pbJCdESqP&NnuI=cI@_mo1{pM{pOmXZzFUv&L%0kt`np_K9u>c+rxrr+-(((w)1@LvS*I*0WX9^!Bcms1>WQikLfC86e5f5kvTQCnOf#ls08R#|+A4LF5pQ4xj7HyELL?=x&I;F&N+$B7H$-ZPytSk|fJKvsLx9)>ZUCe!<mB-i;N_S^U-UwjLp6*zfAE<uF%5Q)A^B}P==#aa8!CgOU1DM=)rqgVG-HOa|Cd#cSc)zmwqlcc!h6R?MfScEO*#@(#fU2*@Z1kp^<f(|$OIt*?I+6_<)_9~h8C#Gmblo7Az+GcOfZv<ZUXCNi;iWCyj@+ndK<YfbC^JZ=<C59dlIcf(J0F^#NU%!uUX8%JGXQBvuD?RLmlAN1sgGou<!GUR7yD22C+z@)dy9k1Ud`0q1oM(<_Mo=aIeRvLc~K)Yr=a=iJQP_vXal>+LWwbWS2TKhtr<?vU<Z?NU|Nz%3O(?2lY|n-$J6^&O5|FU>;k0Gm1Zf+O}=mPQo{Q+v(f~}axU9)Lt8t?9PDWFr0snb;OVQH2tDH_h1s4y6QLEHDQ>10{dT500`=sU9%I=}>E;{pw|(#R=!1;z>-@kwdULofqposkb|+s(RXb`*VkjUxevBb{Kc^e!FJa!^?=RP^_z8#4h<!KJ1ET0r$)x%&KqSsc;L`=;)Ef0QKA)*O%(VytVct>XOPsB)5X`1t1<+<rN#s*E$J-i*cyNOKLFd^jR+$$W7uH*kjEl3i7b0X+N+9@n+ig)Jl;m2#0YdiBSeCKZuQajUir9|9hTqxIs!|rJ0>9XdE&$U=<^>IYyGN^7S;+2I`QjY32+Y}>ssfnj4e~SO+1nB%@mDk=C;!w!7wc;|7Vt#17t%ACgAIYZNTvY5R83y&L=Y7zF!xWo`T~3bfN>oi$Rrh9%6lpA=>4mk^B2?|rWb&otU*cUL_?eWLd2`mJ6s~1&74u531^fWjRhOTBDt%d6Olf<k@t+(njZQ@qdkg8(h;$BigRosUtYM7ct#iC8M-z>kt$%pzv*j7_TA;odGG6(L>CW^&H-hx-jtI`s$}eRzV-Tii(DjbRCMX!!WCEuS(=F4m1~ha9=*@3ZtEoHz5F#(frt1%x$$hObM@vwy6~@88(oFB!eosm9uD~J{uPzcLrq6+`*yBQp|w>N8eH7!4uCj+iF2f*X7%ng()ne5s{Q{9sqzYPzov&Lzx`_{^^3ZixR14>58Jc$7>kU?FX6<P56;@}c{XS5dbRz#Ix?q?31gPG`}WN!^s2ZmGQjb%B{7r3ZuyNp9lk!v>2QIciaBSMPtBYu-=8iFDm?8LICn8uEabFXX0Yeh0$DXDpYq8bRcoNz!BI5=Z8^>!eF`++BOD4&hey!D(PR!zWnz1@tT`G8IQBGIL8Bfb%|s^4LM8)|$w*+a$u%u_o*?%nD3%Iv=&jN7@N`!TY&n*SKn2!uo^;L=3UoL)ZbhK&1U3?Ak~!WQ8CE&N9A%hWGR!mFBMzG4+Z3a5a(js2HE-IUZEA~OuyrzLo1-13)ODP?o>SKmMD01uM0igL-#OtkJjEOhK|B)2j5Woc!|3J9_JmLG^7%yK&Dq8c%C%mFM`Z%+=1}5Z<C>`*9AF7d<^W3wY!0wq(%aBd?3X#6(m3{mv!s!6Q0o0If_#bby`s7~mXam2#BeI&j8AW!_`Qj0jwqBz6`zh7fzd!NjwZZ|Z5pp=)Y3H5618T|ss<fR6r&7_xV0KK>^B6H8d0{%K?eX-nrl!tRi;0-@mQRUuKV+!;!fQ3!kc%@(Z(~hoe%96!l`|`Mhd@z8FOdnMY*%{qWs)OjuF3u`5AF=UbH8o9u@6*QSS7-==oG^qCP*@YGXQijPnD)d<-+8X-}1&FZP0|K-TO@hl0$HGN`Odaq_yw(oUE6W_E?^+<r!epX}{S4IO@46bREAG<(TN*6;R+NUe{b9v%4sg}K;7vEs*^&3!(B%aa<KlSfOn6qSXdr2{pXo!{J*dzKhG3r8Ts+n<1(^OqMGAfVYs28z4(<mLGtxJLJK!dnMlAyQyZYAu)LL@syd8O6<kh&h?aU3I&STMB`X#U7R@QT5LTsZ!G)u<}SGGw(&F3cG3pt|CiI8g2{5)y6dzZm42$&vdfth1Jv~{nVI0SCRhV4}bhmUsoXaxu5zhNN*2g$bhxvyEE1y`JO9N@T)BV0l?z0vLb=)7jp=$3`}2f-EF7=1tL(Bl^uLq0qj5<$0Hu<d03k{zo8d0bKXYN3PBIwS^x~BidalRs~OTIG{@3tt}MQu-3vXmF?o6+WNUCE@-df!x{$_hQx2nCc@8*9+o)YSVqed1E=az%$J_jY;(WqK(ph)BJM;U>ig%rpARpXR*G^m_@}D;W`!j{T@2}}mVE=s;g?#T-cavJkPY0s-y{6nZ!GC%B2gTg++3Fw!p2+KTLitw&frU=eY-Ugk_7nlX;a@p87i>vJ<HkR+oizTr=h@XpwscY(*%EDVG;ey((1S9{XXrt&-O_Qet?0LJWh4{Zz+0&7PQkm@#4iqiW;+PQTbl2?ihQ-_&T*XY94q6|605vyksbWCsGb6YUy?l%Y;g|xhn?#O9N*h;alZ15RlcRO63dp@abJsb{pkD!WG7mrN0cqj^`i{IBDE5caN~sud`$M_v_*E~Q9gmAOA9fQor+J4TVzF;O}9^qd)DlVPg|PvA%L*YE*=;f4IdjTEi3p-vPX%7EJwx(PdL$Rz|>T0ipp{5?5$6&#^qQY0##}fU$wj212{r$x~G}P$T@fsR%yo3jc$MgRO!_dq=HGZXV!|jjWD;NLjz#}I4RcrZIr+2W_Y9u6;>wWWSej#Aa7AZiwec_0ukTf9<4#7+ekRl^3HY25oXy|Dw<iIshb0D*1wDdr^Jd9_|o=hP!=XU5lkAmL@B@PHbtW#I=LdPH_mcwouQ@3_6&I7R9}i&g*WTPnm2m?Q44BYYN1=QwsY3z@x?4?A_Lhg<|BAZ5-hy&XN9-Z3$;Qac%}Fz!iDJmwzUolrYLQ&w&7<b_F<9Rvxwk#VSq0_qkxC*W?>UuT1{AwtCENNdCA*fG6wMn>1TT*c+HD%<sQTslL!Q?5lN!kZyWW`hnV3Db_(00d$)SK4+{a@Fgcmq%SKx=xE3pXYjTi8e3#}&WS&so67N9DPJI_oEDC>@P_S+GWK3C>LjAO%;A517iwt2c!6t*Sby=tgX+WW;Rgkz`K*lw%Z2ri4$MbJ&Uwi}$G{Y@zb3Dm40X}c59PZJZOpc6NW^!cICX=IwZZbJ~=q5emN7M_fg-EWFS_t`KY9Zd=_;s=-j1W{<H}RQmpR74xiymd~*<L{7;t2WFOyR=)=>oqU)J=Q<z;zRXrm35dFL6!>2%+C>%BuvQr5+{dtZ?EUv@M(vxZ@nl3v{+_Vx(JypSmgdkWb)pts=L&>mAnedWsOB%A13SbX7OQ17#&-SX}241Uh>;P{{Mf(0V7iewpDjHWOhT{^lj`f>90!bseLWM`|>-%53ul0%(<N4n)6!VhUkvH`y#LSP?$11egl+lle-YF;&hV(*`4?C4piCssuDT>EPuiVc4d~Lu<|2lM;lJIgr#6+}9H9sAk$WT!2`!gZ3GcGP{xd67<a^0l+Sz;$F{Mz4MWDcOu<|-aQu_s$>Hp^{9+5?>D~`ve`5(RJg75xK#(D_Ys@Koo0BpwK(!=qZcQAr$<A^Y<$G#z+Sr;B|lN#sq7dNz;^IVme%Tcycb5|V06M9TRk}P&8<b$olpVs54Xb}cUWk^t4YF+(iB&_hNGgEi9PuNY;w5Q^(aJngT~HLm`XxMM*&Fa1=!TY8d<|RA{})ZdaCb|%&FquM`u<i$wmBdsIp~8?JZ5?o~DZ_E}-MVEe%=H76WShlN@fcl%kG1+rrK|wsU482iN*}T>lQ!-w-ajvW76hm>0}bS1bK|ynHhBTDNU4HK!P4bcYooDf)wokb9n0z#7%4bsph`X?NG%t2u2*FOd6fm4#l@Z?8$qn)clPS`?RA+@G#B0z4`Qw0^WbdQxK{zp?Rj^sL50ptRKq^2xqAr4fkmkX*pr#j7!pVhfqUhUU?$_lOFF*|y}?FsFkvV+7f9+%EQwLDkST2=yBmDnk{6?9<f*OEKsZWXhxrpYavBsHO%)K>8*k1Dm+Ov)xgABNg93#Wxc1jhu3wQm&ZV11<LESYA`SZ75C&Q{hqXs1^)fQ>8HK0;Fd(RS6oJc5uuq0=f&T2gL}7iotLN&d9*iz-+4HhHN_i)P}4XKS1--ac+C@?gpnmhC6gg-v$Xgzc#*ofIJapwG?1waNG0OaU%>wlLDc-twI_}yQUxhdI9d?vFm6m0x=a+J|g-#d;<VgbJjJGxDvI$U=7<dRX}8{$x|vp3;;UG)*wW9{5l$taHOP>^2~bEgQw8B?lrdSx&_G_m+EwItP6138lHwchik>B?`=ETvzsY*)JA3U_g@b(6nuy0&7c05rDhm4h<tg;5@A89`+GuBtz-{zH6PmA<qacx)A`E`x@p!VU(C&R?bA8x$3(Y3$Bf%vR#W`Z31c^R=0!HT3CKl9ZR=-^jK`TC>-zsSbe+F+aGpHa?!<&RhW$}<E;1T-#7a4z1dq9#goV$jbO6)#WI3pz9+>=Dj})r=c3khwCML~UofwVIY0e@e`%YaWH6mI99;4=>UhU0beROMGgNECJ0Y*P+kuy8*%~|a_5&fp4<GcLy+(;33_>!N)GvbE=Ho$y-mO#P1CY&dP^B!fK6u6C5Wy|clxH;=SN*zK0kAR=~(<Z9TMZNVN;r!K>4dkp+27yUVKMB8cISZ?waUfqm$g#tmvNr%GE;`1bU>)Tb$K-Itopsw2%(i4AW2MJ^#f!*z(I_wGXWzFr3~FZptpP^$id5YLnh+eCDQ1QRGwtcPFzk)12s<5TXMh*3M*9+vw3Rdw_)L}X0ncEK7<M37&bnQfJ&*ptl!vHzMbK}N=I2YC$OSE2itPHBK)g_aT@?M0Gi@>u%7}GJxoR_Knf8i9q@k=-L?UA@Ql*2-Yl4c6=?Cku1_&g=1}m{e)qY#6O`eW(t=$Mj1lIEG7QR3#IMFaTCgDg|12t;N<RqTyZ7UA|_@qtU#t9?wJ=NYX0~%vM-6t|~nVGS&O^tePQ=%hh^^{IrPTOqV7C@iu&qLJmI_Ih3{K<jn*|dSOz{|wLU~ke!29OGNhN^waO>=oF)yM8+!SWi>nfBo0(tS8BwhgzDS<|ydX>dL%^4AuzV9~QLM<O2Yc9?+aR$*J17f0LD5^-~}FJymm!fpYD3dlX&!X2ii&}DqBPg{gQLLhWua1tIz2z#xJuhD6?d+u9@6KWQj901>J*%kmEk?iEQoeq4Ub$e`nXRBm+o+s@xD4DKd+ETo$ugq>P`$~i6WOT*JqS{ZAMUA%<oDcPzJIO0Gx63Q(QTsL(GW6hbLp$pUsfYG`3CJ^am)Hs;TiQM-l$lLpOPJ?>YR$gSbPWtI#zM5alaWn?)wd(yT#8Yj-ZQB<oY1nu_!ykpXLzP*QLd|Ymg{<^!|g5vz4x{T_<SMaaWbs-vyzPF*qw;l=e*c@22d4KyGmH(10>BaakC8h<+nUGuILj^@=s0o2do?BuBWgqHUJqGc$!ZNM<mD*=bi@13+M}Om!X;B7lQd!_yuPIs$gkPE2>ly_9zAgj6?zBiboqVKn09&I&eC!Sn1ai?N<`*mJ%HnY*BPa(vY#YG+2WOnSzp0g9!+G*{?QBZqbGU9=L#)6F;iCvvQWE`_i?I5CIy&qOIp+ljIWk_+^}1DvT{yQ3_K}N=}p&as<CBISU9!w*@I9qXPcsZCtOI*!G1igOdR*76|cbR}aZ}V&)pLLz+zBW3|a0!8X_on!>i@q|{*B0#URnv+{i5jafcJ(s-Q+Ak$G1jF!#Fm>xhI4JDV=?XymnwE&2OidQV7kUTraCe**>#X8Uq88=NY{5;Mr4JI`lx)#*pH0n1lb5P3n>eTXdR8yi^AGlyF<-CTI)Q$2m8}=}5>k}c3eUWout~<f&&cFWnUA$Qur82*77_vqw**fal=XNgGvIHiwFWgkoKV0dYD`{7URJ*#z+4nXjuQ!XZbY|Sr>V$>W=_{*~&kCU|s#wIR(^A-e7ibF&Z9K}p#7d0gnyVF;U#T$J69hB;QQcR-sQg1gJJSVQ+gEB?IPn(Xi9q~B0tQw;X^YmW|6Iw1JewAnNg3&v1R8c}e{#heXfFFEODw){0NtIG4z+#j*zBG*q^aT7vDuxpj=ksErthK}x=i26sB{4S$z3ZMTDFNS8M-evlcD__fP?g%X3M@K?K|_FzPp)s&4atlen#vYmyGN!qr`nac9^OY*?AK{=4TgdCx_;r@wh9A;9&A|0)WZS$!}0OonZ8q(}9m)r#f=1GHYleQ@rUYy}e$T!df<gdXuvgTD^G+usSNkd$Dtph5@i$_~DvCU@+D&+ML`q1uJ?RnNuk7DyZ5+*qKGYd=22+g*7ft1TwhB+T`toZn$TP;AQX03FOTbzsRQ!JCVqwK1hlN%ks(lrK5&IL+}Pk5Db&W(`woXY84drjWQlEpPgiKnS^)PWkrCpA>Syuk(#2gC*oUr0?=xv@BpDjMBCwS!6bi_*mwL!>!|Dp2Fc_gHHZ5`?5m`oFqhj(x;^Nm^4fv`8rLY<@A&;zEd_BQ)0>Q*P{!7S3Tteomsa^He%31AmZINwGBO7~pD}4785wgCZYnB3w4ZZ<+EPRUp~(emKf}@e;@=?r@gPM#TE9Sc?J@f|3V-0tuN&r5PIcI%<<$&lszNm0>7ap&-p8jBP{6URyRwvKPnqXA^YS(|twWNAof&&nr1zgRCMo{u&%gctFMspvZ@>MQD<AV2Szl`RwQ70V_*knJE{h!Z+0J&RMxDxl^$K0h9QUHkEi-B2`(o@&YGW`)exb7-io`{seX*pDn+ir8)zj&CCoI%CQLVGJff{gJ>!<^@f>+&SHMQ#*sAp`e9S4Ft4mYh^)YiV7m;qbPsVzx3nc^)D!M<H~CuNCXIzknPsgfP;3M``6=oed6H*DX28J8x)-wULDhhD82pgETIZN}`DPMuV`?_5yCHDQ(|Z#p~V$iDekrGz*dXhSN*r@Zjn_w>!->FJZ*zNha!dehTaMy<1JYGvF~HwV^ISH75*y6<n|wyCd%0Jqfr%yy8O3MVafWt45HdjXA`{>Z0S`xUFh+vG98-(9#({dU3cZ8|HkCcE;*JiH{Nw<Sn|g)KpnPbwXPAoQj{Nu$^gS_*&WI(e>1#%)^t$~g0QlhEjGj|5P9lPHX%4Bc<<D)c^+{2tYi$VXd3Gcw3w1_e{a^nQz=?)zTvg4n|*#9G74Lc`&g&67>Sp0_;`V?yOj@LXp={0hi{*cV_oWNmE9LL0Yc2p!aG-aF3w#CZQAOO(??bV-e#mW=5&Zfu>(vA!m1tDxY$9iTA(9TWJMASS2?^$wA;KY836zz<+C@4X0eAZ`zpm931-_B-6{HxH^^UQPv22=#uAu;tN(|4pw9AD;ro;J_k>l?Id*%fnL6{af$x0W40aA%!pSQC1+HYqYG77@E40Qx?*wF`Hq3v7$eQg@am)E9~<;+IMD>Osix08I1WYAB~j0xKfO|9I&hz4Q;!ra?_+}u;ue;-Q$rph}fDXDh9UMx0b>_0=DD?vp~4o=d()1<&1;naNKf4P(Y@r8r(q_YDBxeomf4FE{J(YiLMYEH0uJ}udhx8HIHqZjA*ymZ9;&BC0Yp^b+RH3qfG6HfD5vbO8q<uV-zMpM5RYrpt{qjXB2UqVjGX?n9B2rBM{UtK+{2oWgT#|LkA|F1RO6)*rWBhMS!+_ZehW`oy^`v=sXJ%c$WY>B`0gyHg49*g@WaL!SNR?zSaFy;vnD#%mB(+E}K15u~0(a%rBx2PTIE51?3>4amVJIPdYZ=^X&3JIh<5iJ)`yyb1U%UzPYnZY?Dh5lCaPy2c6+O2FT;er|eJiO9Q1M0u@#e<*=wAdOpIksQfeo%yX|cY?yLjWl>po=N+Xzdvc>uu(B0X&vY-ow|V*T;c0wfD{gY&6*u{5pO<5#wNg2d#$E!@t{Cc}&<nURKtHBRq_`&gd1J-QO1K)zYV8_GP*Y-=1;_)^msz*Zjtjm7A{{D!fOwX1B~<ojl~6gbN~nisumnaak0S`f)cj~XJZEG%DRs($l{zU476~J5nbV+Kj8zrYXbD=umU}2(Rb0uGO)F|>2g05ZAYYSp%Xx<-3~Z^{n;U1CQ4N<QWq($Zlmo3>7&ML<!A8&pXN5`=1LP5Y)n!mp(_>{~y=ScNxO^#l-tKKQy76bYPfhFFlWN*F6ms;(sCMT?F*#ajBs4Nv$U#s0a&=p9ls#+Wr+MwSyhgf0uB^SZSm}(t{h;aOPwJQk(-zhugG}3$d&zH4d(+NO*kc=(4Q3#4)`yc4CAHNoa~R4~=!AEbc8Z%A)E5l0YH;Ba_mxUHu#Q*SXf^DEpw4;PQ+31-*oksp7^c3I<_qnFYnhaShLwS8)GG`Nr42hj&@@EU!djt@Js09SvU2wJmlor^uU1k)Q^APAYNZ@lwUXM)n6ww#^H4~I8&Y1Xlt+pzt$SYV^m7wH5Wy9U+O8x@8HPYZmz`$BohTrNS6VHlwyZ*7+SNgQ5xZ7uCxuSR=$8`<`QF!_<lGiCy^;9b+HM@Nx&!};O0e~5FIBVKmo^OvlC%Z`^V_kVo6P6!HP*R8G++JvFBJTmMuC1=S4;t5EQ4~`HvG!9$Y|UhKG&1(@b^3?4ZmdQI;U03LBlT@bx<Bw%h8QNjZE7<NhU*2t^q1q@7vSAGn=g1mm}9a`yTWoXKW2+Eu=G-UWVKatE`{==L>1Sb^Qn@t14?XFVhv+nM!b|sIsfRtpP#rDf#W2?z&B2&5tLS$tAIxkD7K}OTeaGGQ%$CRo~{Npud>lVBZT6YTNe$<kO3}vD5YGc$xFjm9bjpOMrk8yG)Wr)_`15!B>47Sk9GkHJkU{0Rb;OJ8aN3%4R@c3aa9LU;+=zzd(6Z*HfRCtGSTNT7&jQs(o$6h7FGMgc)|b((>om>KUk1G@DGRPv6X3$fd2Cd7~_VC{(*}D2Z5k>`N0`ujWFQQ4SrYlzIvqi$pjH{cAbuvZb{)9*7J0Sncs8Kov1I9<<5QeDD;80(+kbN$oSYno+h4r561%yXUM(`!Ijl$^%ikDJP}OiX#FBUK`h>%{UORnY6XiW`lGazc&Pw7*Zy}FSe+PN|Tih@I+%!SEPYQ9WwVKMA=8<mP23}kfo`4PLzS)Wn09d%!ecX(f25aa<}3jda#J$$R}yk3tMK_o*9}wVh1Q--8l+oEvP`|94D|}c)bcjD(heAiX4lM`%`I8x1BgV_IU#B@Jw-{4m`M+RJZ9a^%+|;E_hSZ_@n+!GFe15^Ywk7!Es9*hsw&=39n(>n@MQ$PP6c6YlJPDbiCvVL%VG$p=g!%mw!|UY^yTWhISgLdWOaYP{ze<HhP;$kZtv{(yN6)7PQg@OWD@W6z2qT+=D##lOE*vJSR<zWau&_A*0d(_$Qr-WavTiKvQMk0{orXBoDr{yXM)q^&V+B1zewxq*GAub1{twQ15d<YG(WZ*Ko&g!1`x1=$*9<>a4A|{084I{ea`gYghpLx9`qvv-;DyFgM)oTb4x?GBPjjCL}P~WJ2%!WjvV`9B21Fza?+1X7BG=SX=<59<8v%2<%}!0dA8>xt1Y4hI;2!H9%0;^S|W)0~Y#OJuo|nU@d9QCsaw*yLkhIu;e0aJV?z5Zky~2paGQz+_Fi8p@Bv$FRSg_^)K3}ebM{NDCrU_V+m((dS5jx5{PYbr}w#wlYtf#nRVT}c`q(YbqgzXdr7g9kNlJS1vHVMlC85o?xV#GXu7qsG{9e6+@@v5GZl-r@U1^hBy%gcptSd+_X9`8iqs%8MR;pYCTvl;ocyZVh{uwT%N2TVQE$GLy%4B(r?}9hO-4tEw#mS0Yt%Q^sDf@mdXsL<+JHNHqXBkE7D1PqQQkbZQ0<@!SkSf!BW1}V0UA^>^-j|bUH9cqr((m$ytuDSQiqQZipDI&8{~+T<o5-W{hrAyRsz$}9Zs?Je)OE7_Gjh_tj;>+>n*7dh1<$-IASFmXm0y%ticwtDO~+Fi>AY<MqThJZ`k|XWM{46nQy0lBb%U6&nO?A%16dVAWCl7D0&Y#K{xEDo$aTMy7sG_+-NQnGXZ`p9ayzI6C4M+L=T=`-dT-cvrk$D+t#A=$SQDjbWyM>p-L;g)%sQN*O#!Z+k|P$ninRhaTAmdQmA@ADOmkBIZC}@2Ta7jR=YqODurGiA6mpgUBEbj%AX<ou%fqP0F{H69|5(nU`4!dG|=F3(5Fg$62~Eb?$<fK)r4c?;x=Smih5m+xqxlsZQnb|C_9YFhs&20XT80;py>0KvoVe>YqH)L3UsoQWs2LkaWCQN7has-CX?^cyX0j!>A<d6e)g|1e^^4Cuk<}gUZ3tC$MMI=SqN`avV@l~c}4kR^NRQ4s0Kzp+1^eX<TQeO8<Wq73CtBTsPN_UaVmV_n9j?hk|vq3o1z}U750F-e|VvrCv>68hqno8!elXNNcpl$wguf8nKI0ChCP-zonU}UVE|*+lc2Jrkr@Fq!<zyUjYt(%L@FEseX+FxBk3Xm6@<JRo;Jb*G$B%(5Z6TBAUH2&YuN=sR7@mmz1V-Z$j`50X5E*xTJ#ZjM7%kjKk7oHx)6?Z!9k;{QJS~S&yXj+nQF`ib3mFb$<IOWDJ2!&O;WKl81Yaor^r`8Mg>R0gaSGb$wym_1gN+o5klV|6e<Z?)<x3$6X`D`jHsZQhBh<i8s#gSw%d-z;oZ`qIq|bYI&SuuO(sDxTBpL4mvq(;BG_AX@@v~&ZD68@Oe77rl<xaDk_XzojJ^cWMMQXFQXbm6HG;=NgcnVwZsJ|Yq!Afr$TImDXwMSi5UP373hKEfbBm2~A-{QI(B1^)L(hPkphg|GWg;f%7U+Sia#+Z*gHT<BD7P_ccq6JN@CC$Q?gNf9p^DqZ>K%1N(oS{(lT;XONd0TX$gMQJP2tI074?~^=Ew2PL;?a;>rA#`+l~goyi)6qA)gCcEc~meWf%EBd_vuhhP{W2O>paoFw7AlG_<_w&?~*pRB383{0PRAJpfA|QUWa!*0?6P;0#J2U#=D6DH@xEK|vyXt*~!+T~d?L85U}lR8I=E(n*tR8I?|9D*I#aXHHWlC6L3yr}Q-VDxt!|<Im6c-H2rQcab|>Nq37cn*m9cW<XM99V_G$YEh)IIXaw7jkG8dtY3T{HT^N-w?F;)9+Pk~BvqCSNtM6uc7sofw32D-JyE!$GPKlam!q4M7qvR;awHRgB-z6Xn>b1JEOGMC-!?$9RDOvv;r$YX|M;cN^yBYwg@<_gWD0u}%_1)A1BPOaJ1p}`jWtiwx)C5lHK{m7Kn5{YRTCW7KgWelX=vOT8Rc*-;iz+UCu&Qg+C)>Ledqz+Rut^1*8A-x#UNZ4s^O%dZ7@TT8j^sBg}Q$YT0eUb0PF>ulPM^8C&;E2Ni#XZ#!e%X8)x#43_E+$2q%k;st2{9yN%~YH&B_e`Hj@{<8DOSqN(xGluhsw<!E@~q2YnNDWIv7-hceg+=5e5M3&hWCv&K!(a!MVq!y^S6{xM)^sU$|cPLLBEO-E*>`vIr(1P00=9aaRHn_iCG%c(@)hnka$CfI&=qF#+I_9B&h|&ar3eb#shI|Blg<i~(DTvafsR#E`N6Q_kSYotnIxW??f@nd&<=*bd&lQ=8QSzK%(ex(*!U$4<imL6PE0$0db$}CSc6qDR=7ul}T4J4aI})1EU8rE&!Xb(Mx9GH^u}|#Vd%QYciyK^Q>QL#qTkR8$Ta}fzuQWQD(i}t<g3E_E2^Tu*D4FT2%~Gm3Cs0#JItPu~nz3);7rqzQvUE`3sPY8`gAPl{l=cN|yVm;Vh-3c}VX0HLpyd_&gv%6l0;6D%cgbB9RRjWnMsBGLWOMUqOSDz2n#sIOFg4z&3vqCXbfulv5NG(90Q!hdTML!vqsl<F7nh$yY{e63o=8j4$$E1OJ$Kc6lAfZJl=H*fD>GNN4adfu9fZSHt)(`1shYoZRAhR{=ej1#x@avm@^Yohq^5nt`%;69?)#Fp8V(*mlu_%v@Vm0=7dHgL)sx2$<%@az@cwem>fwWipAiQs-aV#z6ndKQ^YPXI)zB@%K`1F(J$ZjnzL@t1g)ZpTJy|N-L|-*clW*%>-+qFT{Knpqlux*rP0=MDJX-h}fAVOdjN3d~DC5kdg+kbud=nX7`WS0ebtBHaBq3t|OR3>!7nKrw>rj6F0!-lorwdiLQ_Ra>H`<v&hIE^T0&+lqj&jrWX(?H9hOZ}T6Hyi>0)E-No+xsXY=-thEZc;kC93(fP$qP8QN2#fdL}{kl>kk@0v}w|#;`2RPdYGwff&I1hC$rnL?q*azOok*wf!u|#vxH_8mKjG+?rM*0xwalDF{pes2ae>1>SGbR^TZ1w}V$00gV8@<`u@#YBp>&!->_5Y=4>4Lt0zr(m#cChfgU2%W$wygq7uOOWd-}yjck$g5VZ{;He-uDhS2FcNl>Z9N5IhtXqI^U+a7LO5$k8*)C^ZNtB<VH*Do+_EIW<mF&rLUcd4V{}Tt8B~~o}J+;K~NJ%3$WavRxLF%OxvPo{cMMuus$R1Y&3}l9dlyz1AEsJ_lLnfx~T$sT037i}%#L~gTi-<3KtFn4{5g@&C?gH@|>>Hs7ZRnnVI}t9QZWIR~*#oKS+4a=H$OU2vg2`Zg1^j~SxkJ*Z(-%=(IIL(iFQ5#PB1at;1)fsGftp@)9pZ#dI;TDj<x6Q3G<&JcM|PdGkks3mW9*E!{8{NyzaLc$#HgCyWFlSN*80BletYFDpG?##iGt+qn#aS34CS}>0aTU4s9~RL=|x84p6#Wd^lZQ9+2vPyIjOr-FztJr%bYeN^FR(Nr+OAnWn6XF^GQl(Kq#WcK><<E^m<{ZEw(kt<)pN(7gk#Lpk~YFI_sJ)zX6$*K6L0z4CqQL+<GDJ_{plfGPVcTYSTzP&nY3Z@&#VQ#bj3c*ARdk06j0-iS@UyYa?_8*B|=Z%Cnd-pwlkc1FJldN_4?cv9aUQF)LGRI@$U#r7(>!iu3_{KKfv*6kf>ZE`SGG6Nxp6gu}K-tY>v5M|oJe%(evw-GYOja<F+^7dCJ(QmYX5v;$Q<7Foc*4jPre%yp<IlV*M9tPi+gtLL+VtzKBcR?n(lgb6LUcrvnzusDFXkCe$$z4|hODcD5BV2aM{>6|7|JCuh6N4=9Kv8AG!Xf>2D+GNB!YkRIOO6Oa!C#<QUOSrZ}p0EbrJkv}qTu}2#&C_6`0@*L8P<{~9#1*jb;l{#PPU?!(F6p@qUB<LsH@I$$bB&+@dk>8!CR0UqaMBC=x-a<YrWZ7Jff{x|DtJ0Ti(@3p_|3snfor%J=ULTO+$a$XSlvMV$>7$m)W+?xz~a~U1ve^CC>U~BaMKGbxKTcFqZFR|x`Ftj;AwY7G0K$+L^3V_JS|gEMzx&i+^%A!zis@}N&zXY!bzFQca>{=#N`S~)f_Z4*N@Y_Kx2q%6IvqEFO__`*3N6d*L4=XD5o+oMN1eg&sY6A91P@>ptA-iyqV&??f7<Z?tYI)A$|4I7O79~F1-@}`F&?s@#JGNaqK-gist2$jppT(jpkoyt7_sD_K0s>RT&q}(YipBz{Nem9bJo)j|E(dlaHtg`~C4k^UY*c2v!93Dl&OBN6_-SZo*Yf+`w8F$kga~XOxr5<-~Jg@I)BUt2HAL!v;@G-+0i_K#Ng16r;e!$gd>DuO%gLOp-`SW0Dexq+Gwx<L?>gBGd3rIA9YonyG<6+f9V0<+H$tLq328LA7%FN3O=5N<8WYtu-xBy4j5#poy7M*-4z%wYcJV-2#PIZU;wYqhh3^4JfX}%MtOii6AXQekDVm$xy$K#5|W2M<oSyKhnbB*TUd7@IsdO=X7LBq-lQpHNPF7+#ei5jeP86rM~ueU+<-U+aV<rKWej*DF^*@^fFt442rBY#+Sh?>#TtWHXmd{M~?%7)d;}X8c$o9(btsU7W$>G-G7ZoU6U=)H4^=jDYljVrZYPHk6(WG|NgiC>;L@SfB5ge^W-4wpZ@;WU;pt6Hl!oR{?tx}PIB`%|NMtP{@s85$KU_cpa1y^C4Y=7mx#>AXwO^I*Wy3My&Ybrd*}b~>mUF0pT8sSZmRH*aOnCq7`~?^O)wV}%+&bpgrP5%w^M%v;a2#m8q_Q>MHrY`zo?lY5^lLhAJ<@%wkH*WjmMSeip1op4}rnsDs$C)EKvMN%iVYGAf}suAIETJLFKTKHJ`?*7GfKy)J0s$`7VO1c!xHWSnNEmUsYr#O%~s^AIbFy{Lg?c1JaUIVLIGeP<;wn6sf{)k*RIOLbwB3<TFKp$E-@Y$-@yZ5KmhJNAZZjfP8+rZ$l*aR7ew|@6Ei=_kBa4cP`x5=X>|<^Zle#&iBsL$K+%4Adp3@{IXgM2YHrvwU^q^<~;YU0_`IxH=<&Kil&+-Ov$Y0zLjl(Ef<zzhAQ|XTMlw7FS7OaSt4dsY}5DUYzeogQI|VMr$OW;Z5)88$70V>-7R$+wxm<7(6a#+kzQ)=I(Z4HZ8tAWPUT#0Q(dg``M$q?CiPRPLmME)S=nuEfXtOWv;k5*n8Q(aRXlQ&pH#*#+Ap6K60{qt$T^^2-g5@@C4y|gvs#8$=*71jWqSo*PhkrS*c^tfK|`b{G2Jfxr$7Jp`@j6nufP5FU%ta$ix;-TqVbeoI65?5s_5ELtUbc|YC3(COjbE!%)jFCF8dC6{6O+h&U;ZNjsxvX3ED|@X%bc(slwZ%XjV}645PL+yKiY_Cz0n9{<?EBQ~hSHeLN_qG^B>JKX2w9)Kk85;ljx8>E!48$$^lZ)zt>gkE+0#RQx%~vJSW$;nfa}j5<G^jD!5LxdZc~iWMdme&_L{dt?U$Xlqn0*>u5SFd{vR5%GiuEkYxrPM00}rC!?3nGTGIaJD@a`HoFju`PKA;Mz-(+J<WmRh?5j5y9@a3a$>0M{N|X=mBc$`#qj(YfqcG@=wgQcapqh=Q@51+k5^N_TT>LFPC{xlkA_4_Q4$#QL8CCG&vu*!krs&2S&%M<nH7sc}co@=f#_kY)F7cOXy@f$mt(PXq|3k?%g-AAEyHYrSbF}j_28{JC!}B20pWtJk0WDnSFSlE1Jx(UZOxNr{yU~7;>cyKH~HpP{-NL(%1YI8aW}Qxv`@;<RE4AnzQfn8FD9R+{q<XuTte>iO|SwO1>^GQry7foiH;%tf(j;S5(0urzWPndK3XindEV5XB2|4!0!e=ZGc}<C&G<ll#}pR5GNhDm|7bhwK_gaMvpSklsRh_Bo1YfN7>SjP<0%NW@`c{U2uBk3=9byNB9R)K0T)yK6tz@rFeS+K7{?IqvnfvKS@zWq?7$5rQ3z@q2L`sL0GZbS8JYBI^Aocyx6rEPK?Q?Wc<GS(*-~uy;db?>3y=p9N@~wXk16IF8E!x!t??a9o|Dyob!XwRsM`4nMgb?nba5_SBzt;f%bS~N>RDrKh3;owvqI{{p84x3V2W9ru+qIIN8V^p^NK-Zy8ri-VYJ+TK`D{OdEC5k8@Bm7reEk_X)qqG+eb2J<@P#kU2W#w^adoTV-!z-$ocRPoOKL#R|#6kU@{|KVxxISj~4I)3cT0Ppy>pv?)zS<MS6^wvRxBai0A-jUJ6pYCfwzBN}_n{xeONXHp^p8iXUIs+!CQK3$9UlTE5L^}b@X;QxYRooD@QH}RsMfCvP%>_l54p$Bm46xN<%ojq21B?8M0w7fl~XP;?6&9n6bb|y<zCl(kln|T^hrqrDLS0-J<>FZzq^rt^w9VtE&RWXN-t#Rbb4#Gq`LU^?(h_n=$r~UC&sGLW0%M}#dzz|*((1z(I*|kW)^)Fx2`Jm8<)<+q1)bD9lHk)jDP6&Oj7_O=71^^DD*-nk!&Ddb|>YAtD^<<Oje+}jLm?4_oyu3|!6G|YZahCTc>cSB#RUENJZcEMj=xte?;>fJFwUxGsWe?c3WE_`7qLWvC(gV%ABvPV`Ydb!;mm83Dmmy|u@um(hcP8d5V%Hqc)>{whS4kG7ytM&k<+&>cXJqOxpvnl8LCl+*s`4qArU2SdmqWggcg6wq*2tAA4}Ll(YL!}SdN6gV)W>h?L00PPI>R8NS8YV28ntZbp;oR3k-i%J-Ub;s-gO^D_{Cn%xjx;~1}O!MV92I(;E3~P)U{k3-?25C`D19wsKeg}plPZ33vdbh+v2gUl(Ty&FiRtZlh${y3O~b!Vt6;}rgzkOoNaWW`Iq7I)i?965d}UdEmSl8*tFnyC^$Dv;fS8^i<O>{D^gA;gq2<%k))0HdR8(P4;hsZ?XJc8xEL3g*`@Bf?jjzF0p2%WYBvWT86H{cIZHjEY4h-P-jP)S3t$V9C|^(@5RG;mCXygg7IEoSD#CV>W><twV{(@a{YAk8k#UUnoyxPcI4H!MdE^<Sp1Usl@jF^vtCevzBG7O9j-3IJoBjn`8C$NP1*7h*%uU(ADa(wf9HSR(fNZBk02-S2G74|wh#iUK#(Ujx*j8@|Kp-<P(11Ara>ieAiSo_yYiL-zN<Www{BykS>AC)MFn*6+rKYkPl~#_DUU!o=3vlJ9tlI0&J>bi=LSFaS_eW4q)S9j}KBd@Rx274(x4mgiV?HHwH^gW5OtSo_*efYMi@2OzQvcxf_N>~DyXI|T%p=D#z)#skZzC>&;qvU=ja&iv0ba?dwbdvl5sFEW%8Q09>1SY_S}9qc`xP}j=XoSNPb)fkOsC-dh{#NY%?*2z22?Kb`PlQmVVz7;K;gqZ$pvc|VV!9ZP1LK!C_?gF^Tx4T&rAcG%o`a3f0RLefW{?F9fA-pZnNh6qhjweDJ=6rPa@4vM{Lrj@tNkPDWA|3m=5TH+}J$4#;2|i_&-CFT=1q;Y5444Yhz^=Gq|^bIooMQ2NsA2f&02)<i_b|ew!4qHV2WL0}pY%R-C$jugqpS+$C1d>AOn=KegR9_o*JEYJys2mwklY%e6VHm{s<sl-Df)neFh89#^`z#}hi4{POER1gVm#hZK)UD6W~xHX#<0lhJkWZKZ8ZV^X8i`W~;jb<9Uy@U=U?J72%;qGK6-xqdr!#hHJ*_U-nN`T^45V3*0yY61Il&zEex#^*}`_X@jQES%d~LXk<jJx&BuX~>j)PH$h0rK^~p%jrQXl>)m5>r`&gZ9rLLQ@{n-u6p4`Mzc7=XfJej<<$iwH4$8v?&|!62&2?p1w5^F6O`aYD*OctPBjTOO@usxGXHqzKRirG_TuR)(dCehp3C>+JX9hq5nPb(s;43o>1whydet}I8Hmw{C#Yq!3n^K6@)n-m%XhK^C(NT@{orUib^)pATs8U#)JiqX(X-Gtkt64(CdivzPDzKOe3I%pkBz(Ec(CcMU2TMrw(1YqDRP1>$X1iQ(Mb3a3BG4+cBqC8L^1hSy?7WaS%9JQ1pRE{v-n(C2y%fsVVnYeOY$=$<#GDGfH;O;653++q8c8N<6ycr>Z$XD;%?`iJb0y#l?!+oD-I59vB%~nR#@PtJ+_De%&V@9%J-Q|2si#=Ji*BHrP1s4HAbi2WpaC8xk#6qU7_JSdY2O|=_Dumj9O!(;0xGSE|K}l<tgG0DPmvw`R&>g?IG2pn)Panw97~dyU``8U@L+j!$fL{ERp)mXPxioO9NdaKR7&%vgUNA!Xck{<|V1ymXWNpbBLcwc5Zq}DhBnCM%AX26-q@ar2L8`cxrF!SoGW#=jN2`MJmw+e<`N>(r|e58TUMSH|L%opiQ$ct!fRY_DUqR&RXRomBfO-EST1<AE*f1Ptt+qErD-jm7UY8q_CWft2W(Y5i%lnb*XuKj9}Nf+<kw#DbvCN@Da^UHCdJ9VyC#o*(shSF-imW?`vtF4>7|C;rU6mF^>{T4{hg06jW_5wC^_3P@){T!R;qBwh_r7*-%d^Xn!uIrh!hZT1euE?7ZqOHc*y1P|F<6(*ast0v3i{=%W;*F3R+TvduKgLgOx)r15}mJ#R9}froZ~oosq19pkrvW*nB3$gUs*x^K-?!<whyL`qa7agvtC$3{QO$TzAA5!#`<-6935jzFzV)PX-@4>XkYwnHbwv^&;rLL!QNq0>fmfHN>fQ<i{Rogp@-n{J0xNc#xoPwoH9fX>qJ=fvS#s9sGt_`3R1gzm9|*^9xl@;V+=raK}QU5kftaqf<T4I%CccdZd6^2Y>J%O5(`Jn&lWVa*;nYJ=!G6Zb93LX&QLWmC`cj$V~O>ruP}T8}DruIa9f1`^+B49(nc8^2t?t?**fXT-kQ#)vvwp&i^2`pkqM7!*jB)z%|<BY~u!6zDvVm@;dDB$^2N`I4+uHeHn;z^ALJqr;ZD)uWfZ1?ISki=T1eAm@S8zWyVh><e-l1&__P5~PBWdpnBXUi^;_@yoFqrb&0QQx+Tx>&5ZD)T+vxdPtVHKtjNJpvw4UK+!sIT6ak6$G&;Shd32I?1Vfbbr~K?M?xN%kehd<K5KPSNMf-yzq@cs(kD2s*}E0{PSn%BK&NS%@d2YUu$3xqJW)tnrVAhgH2uCZM&T~_G*angr3#ZUuGwbql_EGUmvw?=r^@xv;3bS(H-X5z5!5E~<caL36DXT;=bst6iA9=p=&gNR9qLzxr#O!_YQ|HyXs<xO8U>S6zIJjeUhn)%*KrW=%&nk50-2oY4N^;e=m+Gt_x{S{U+aZwy(Nn8;}?`~@6yDoXV^1aK@{(E2)|j$J`JLc?Gy(*lu<AM4VHTzaZkOQ7iB*#nRjsXl6hRx;1bQ#U3xD{ShA};4z;3mk)+OwDSDk*9IJUYYn1sF2QLunX{d5%ATnZVFi(k%)Pq0Dn}o(-0V(&|_7-RKK^m9$ZK!pR-rP2oQOi(EMl}oH6ly6TJMP0By(gj8{pI?thoRPI#6Hv-QHN`1b4GW4x&aTY8^mYko>Ax}kS#;6k=zkMmgM2HS&KeH9(xtXA&)}H5PL4D@rwsh<_FX{%3O{!F`$sd#DMZ8nOEs<Fz*;J!cWD#NhhD|;h}u8FT81zr14rbVEHCq6gt@RN4-vl=O0=p3YOSSSS!mXd47!wN0CRp=n#7zsgWq~Tth2oSx7>lV&53M17UXqZ=VUnx;fp`IMfM;oeq=};+sHFFs~+As)2dlH&{hxn!|C!;cSi%gk;?uoM=G$SpE&T6bYBA$%SYx1!iocb1+`i8d0gG9b*#tjfu##-R}g-3U1M8S*lE_qw_Fy)cQ~lE$A5LXuU~PuE^z%TNo|?!$CZWz}N|UqRMyabKePRC$_qn+~A>{dHAb~2623yj?2t}eeD~l4M8pl()2!_mFIxvxzL+Odc#j#Kr;+qwT`tz0SyZQjceEuU<C%LfFyWBPUvUX#PuK=MR@HcJ`!;1It;icxqxeT5mUgT_@+8_lJuJ3mZXjQKRNc}v5<TzbN+eUtl)2K7FKc7yMqig@GIv<;wp-J1B~eXc@)IRaLp6;u~#fII__7EWsbdsT=Bi^w+Oi6_TG0Kfx>TjT&v+&D`t7O3cvI58F3J64X74?>b1nlQz4(J@VS<N5=}rC-|LSBf5|2zq5(U(hc18xlcdn>OnV|F;~B>+ENnP5c<_iOzKYq*x&%L)?1q4EOTgt*Gv{BLejSGbgX}<bg2{#eTCVZ2ha?KJ;7%O;LF6JKZl!|d2|1fN{nL=0T$s}`=T~%!L>nrW6?>UQLl)%i*bObz{ukdH)Q;-eeBlk+r$FSyZSh}|Fm3#AB~R0tjMk4iZcx1LR6pkHc2Gaymv==&>uchC;?fV|9gZx7gSgzv<~aotqd<|)h~Pd}{*J9TQuxxFHi1*brvyGPFGAg`++L4I6mP~ee~t5eRSw8+!hDP-s8ia+4~=BYC>!7OVO`t!@bS6*9_Jf&Kqk|Pu*6NA_^vo#lG|E52X*b5%HKVaJjr0ir=>xR&pnj3u-}yld%*UyiUSNxU^6c5>!HO6%T}}m1uWZT<4`L)m%SrfoIq6fQABaOLxikGEn8N~sDncU1tfmHEav`J%C2UM<81ihvd?U<=qI!eI55c19l4lJUN!rGF}HRGuA-uN#Gpju>gGP59ZW#pLR1+1e!Ryvlf^WwkT20VwE4ZWS0TY*lK%MwQiabakl|1m;OE|6G1<73#VHT}U|ig|+(qAqq#W^_BlvYWp)SbJ4|H;D-jf&RMruSNgO$qQoFdNpM!09haF7@<tM`2J4(0#L^D<KWUVt;TP+EE`mR@@^NYgiR`WDzYQ>e44ankZt59KQnYTK&ciEiFxm_D=Kl&i2&r#6(6C#DQ#Bb2juHZ)NK`2<S%G{L7Xty|MOIb%u`+QO)IZd5C$er7;-Db?^$cy)_Lpn44p?YF>f#n$X#n_q1vmo8n=@B4){9S;m6J|D=Po(~L!Z_8g-dkm{3%2A2R9yU7Gn_)PSwHLz$_}IDx23nXvTLRD|)CbZqltVIUxi+C@GX^6enJvt33v8MwRo;%LJI&TVy;jTPYTN@b?{|F0)bSxkAl8}sIfam?nou)$0k^D)qg_G2>+*pR*ljP_By!5zmnIOqbU|K6$p1Z@-Dm=*=S$s$zvb!s6muKlnrAX?8o=tSuqBz8P;s-bxtTFH*8x|c?mxjWZ34xYR%QQYKy1$~^H}iffU(70^=p!O;8{qEyR(p}CRlcKlTqNZ)T}Kn9S5TAy^^<@RRi#iNb|w87j5_ND!wxt<JNSWfdXiIEfKeUhBb{NUZUD#6tzUcQM#3oM|Ya;qfxk2!0Al$0-5d&(}z9n2YUCORx-{2v^dik>rhMP_Rur~>iPBgStn_P7HL&mi)tgms?#NwW(ZFYX9A$WQH<pQ_}!)*gU|{@A{KlkRrMsT($ZX`HH*uOA3$PP*4L71q{bu*h60Lvo^a25d$^|XZ?Gq;)*Vt9{TY(RM_Xp1fc#90Dt3vCUxkX>*Y?f9vBIb06Ha9%3e}vQkPiOQKm6g3|LN=6wfok&-M!n}Nx+kdK`E!^T&J9?4j+puD^rfG%<2_5gx_9_12;g8i!jrm2HvxkkKUn#d3)~J$LddxX#qVJn^>h+K146x+E6UVo<8PrPjSH>rj3<KU$93FEzVEiAcmwZLy-1@E0%&9sEQqBIxv}z7+d3AX^9L-&zn8BZ_z}QSX>fpx_sb@`q342<oM_j5L>C-bmxaaoDcG}j!au@GD)%2Q6H}65pS>+I3i%SCRuqZfhw-O#0ww=zk6>U&>g}&RQ*~DZ;z4{5z0h_y{!n`by+5H+S>rfotP4;G!++Aw`gt-AHsnad3%*GrKouC16fKnZ6Buvn^-+||1wqS=B8zSa!0h*);{Dhn$!&`78bvGTtuuqO^<z>pW4Z%JVi4dKG-hISSfF3HR?%v?5V`lu<;-?FPlTS_OwokZ7SAY%LIB5Wc2SLIZp^Zf2s2=K%F7*+^*TDX4MVPL3q6_C23FFn%L4dZ<Ab;(ffuh_vlSS78$in)X1o`&Z`79bdy(!BR;ryOLDAt%lpM|Q$2be+~?&p+rA)nq$q@@m}C0u)4ljf3z*L$xKvhvT;4;}3@sSQ_hqM7o<Be986MMX45sRI@OyJtP{1|?1@a|H>I6(^UF92~J8@Ovr!FxtnDTq>m<W>H!B`f^;+lb*Yke|qQ*a>T-o0;0CGhd36C#Fvc~cX^!*EwvSLmI@&yX~(PKTh&ega^ZM2dDhFS5LDCuQc;l@bwPPDTo+!<_Y$FQ!OBz9fmlA+%Xyw0}=gZ%|_g+EC6rM!9$pzK_-_Qfn27L8#OqOsNb(shN@ige{S@3$Jugqdh8dJW}FH32mRE7MN{jMzcI{miNC(CB96Loay;46R#&0DVeGtfETt$f!d=+Ur-fu(M^I5p=aj45S;5M=M&@4O!$2ky~)SD%?l?s&+U*{33A1#7>CRt1QfARSD{c>;ol&;X(PMguaVuhZJsaA(WYu%tN)me(mOz-#;Xy=Hd9mq$bwMAy^;U}8Jjw1Q=_y7R~2tQ{QxRC2TS_(?zzh5Xw%tFtW7heJqTD!z2rQs&(;oI!itehosu?iiBr`t?ZX9BfQ<rmB$B90WbPA>zP*lbMdV+Au|@V!5H3)s`gZI?r9*uRScD6`Rj$qcSw#5=1Q5#$pLB4U6@U!zj+ER<lK;@mEySnIS!khAr>lJ<nz~SqEpsl)<nh7ut>W_H8bAnae*T?!et}=$qb*~O1Aci+y_mZ~c@+tAj9C|;^(VZLv`_JzapEWS$D`2af_~r7D#akU?i*U&qfsGIivHkIwM?+QR4t>booh}Rz3_Y7>*@jwr>3G;ej>u=nijXg`iwZpL=6NhkYKhRMXw%CQc*FmR8;ij*0vyT-Za)^37jnP;MTSPW=o8;yrez-%qz%(nJxa5shg><&<G@)J&K;(^_CSkFCq)l#T1<gWcK=veCnpiLIa&~mM41BwHTqZ1o|ybPzE*z3Hh2y&paQ!ZL_W+FDF@w7)WbmP5ey7)vd^FUE~<#Jl=DX*RcW!U>>Y@K1g>YdY7q0H_8Hg>qv`x-*CsnuNRu_pbxX~$J|c``~g7ND@I!EXTM1Cpu?-{qi`RHRoX<8N(mZKPkSqAq<`38M_A()tO*WYVAo1tvC>~92{^!sZ_^@jjrSgMLEsN=x@+aFSb1M~426<O?mkFR$snaFnsVXbDeX}@BHd%KJQP!?H_Aiez{NX-Hzh6x1Hsg}n_?5CE+N62^4b$>beEVi7lU3Os2IAOt&z^~;=7jRMm?CgQj&6Tzg>%HJN8>Tv+T>PiShyh!sr6Jj$NqMGnuRH%J~g#d?IvY>@}j}<ceZ_K&=1#HoEOKb@9|T&y;E#>sA{@LZ}YM_?8NB>P9vHxbBajpP_xVOxQL$PPxeFeY2{2^sWTp8MO|vo>6UkD_@2l+?UV@;YL>}vqo3<m+QB<(bZ?fK{Pdx39g;d33V<i!8*Dh`RQtrVqqPJ<@Ywcdca<v^bdTC2yELm;D!ucJdjTv)d%FKKTV4DBzDZE;}^i(77OG|8Vk!8n5t2%2#^)9ut9ODorIma%qRN*gw3r3nZ))F(7f?0-Z&;m&K~7IKlC0|L@2HjJD&4VlVU;3R-p?B_9BJiKyo-At~9t{$V@%27XSHxN|D$R62oGIhs3r8!$9FiB`o=qq_fhRvQUgb6r&R6+gr&m)b?J7hB};tZ@G}B5`afrrAP$O7YD$WY7e{>JHcJ)YsD;F3k?4V+e~PhH$roJxmqi6St@bh3`sa-Rhwj`3LH=DlIgHK?k1fv$1?%5R}VBk83&<C?JHG;L=~YC9ks>QBfmVC6Z@Q=Mq_$n2=DUsM2S%EWtqfw9sv4bBJP}}<iIVqht7@H$*V=98Summq(d_h%~|EJ$2Y!l7Ha1_<?n@LgB9ST0(m5GyyJzC-gdkg1<!2+Z^gC5xYl85xb`lWq2?fwk#4YkgBA8+h8XA#0<s%n#tv4(*0|cT&X*e59~7Qz84e2>j$A(j*H1^ipBz>Pg6%uDW_W@=7{qw!p}B=Kz-)Dn`+}ngL4_V?-c-EDF)|Csq6$Ro_UeGtT#)1ulKHpm4225A(moV#;6}r{M|f0krAW5#0+^Z;wCX-X&>TH^t^MTW^_gJ#aIcKooV@Cxn>>SFdvmbu)zDo^B8(JlI3-a#OG!Lmz}fFZ&yyPq0&X~^!Ub-}S&-UKvLMZ=bI1Zg&n5`_;`>>=xRbO%bL>dDcGfmROJc(0&L&=ZrUR$V_32}jia!bao12ZxmV9+XKBe95?ac%FTU?9Fo8q2+?y!f!{rN&Q;B)EPS<`Mn_L;bO6Bs^}14q`itAnoyKQ)`psC~ZPVb#k?q6bpyTSOXGq>A`7d{Cne5dnjDN9Bz+mPEKgvoi19@-4utyBg<2?@2uH+Y<k(8-g-3=!sM{$)qrWZXA?gt22~V=aZU%!4k2Bf=yWsS^=d1q@AknlgaFqr=n9)^~CeB*_4!`MLD_cFj%+^iva|Mc4hedKIP%jY{X7yPdi7^^()b>Qna{+Vdo$>+IbW4Z*TCZ+(*c+p^TXdy=RPWI59N1D&Z$Bf3@i?Wq~`hHV&P^wWrNoDjny12Kx%XfDBZnZDs)$fU4-t?U&@<CVjME)}>%pcak+3><|MalP3G=3s4=aV6X)t4J<@Gnk@mc%%;Cq<N(rHUq|bJ6t<^|wz^YpNx6WqeL#dHqImpUL_Sfic0{W$+Jv!S0|<Q}LZ5dnTL9+BAeF^N{AH|L$$7+eA+^u<E9Nh|Vuwc{^6EVW9bC2rBF&aq4V;aO-N}O+OWL7y)V?V4A-zbrZl!kfV1o^l9NDBmrfD#Rj*75{B76awPwHTrZVeia{EdLMIoSgRiykxQX=%<q*Tgbby8s`JG#46;C=b)TJ>aZQtI_oBD6=bcQ99A6)4kw-Ux3$a{qPuiq=l4sZv7iRTduZ&?;>{;?2)aqgN>v-b|<dw>71Hs$G1o9`gntGXUnvGgVyYxCZehNZHd%98dmvC+kp&?+ZzxvG#x;?N&m^HvaJV_q4gZXeFs-f&;a|HW*1eRL!LF{Gr_&vwFujcekQ;Vjex07h#v7ICIxqYxj;(?T{SOMw*8xdP(50AEhrIiA*2GWT!lm?TPI)M`&6%veJ1R03(5*$xscEBr4yMtnzW`Mvgvjz6x*b`WSmWR$x;;*k_m#SX$is}eSN!ln6DRg3VcOH#A@@3il7!GuMK&wfSk9;&r)~YcdPIT6k$~`$@5X>D(7M(I#aPW74dlhO)IE0laDrx7eH{s5=0~OQ`M3Kv#}jK@*>Pia|%;yU|ndS;{rNWIB5m!l80IFu5Ea?)xdhFfm1l9H4rpt5$-hFdf^t}$EV;7%nJr~2Vap9fsCM!kB}d|Lan8BD!db*cCs3lvKoldxzO?OF&VuXj^R2$l+xLFxLR#VqZj#cH)UNfj~wmJ@$%S%8ZC`@ICz{!Z?$7^KbpGoSEx(C@?$(<S!t&dezETay6g7H-n)?rOjlKHg&LJ-+aE<Qo8W6VdOKSs7KAa;r0M~Uw<f6_n<Ty~ye}v%X@QM$-)uJl;&>4<!zXdH*A&<GC^D1dH)hm!@zHRVgZFT>eg$l1Y${RfSKM15(5pu86`t7DZ#IQe{i)0d*ea~W(o-*|69u<V10z6*TRGNhsZgr7?JGbMMtD#Qq%DNU;%BSK^v>0nM$0dmdm+%_!$Mkk9AQH=m2ZGU8=+l^NOo@fijWZ3)^+NM{Pd^~ii<iIo4nMJO621a9U75j7e=@M7b9p{Gj1y^L?$rVyWFF}qBM*L4<qRqDR9{cG$uYspww-p(?I{SqW`|(Yz|MylI${kC@6<|@KDe_k4`2ikb>@|!#dE)6w7|Z8sM^heMjarWn6;R`}z(5_>=V9<){=ub^BJ2Mlxc6Y*&x#lN+A#F|c0i<L7n(2OrT4mHMd9n&#@6OlPw{L3etpaJu)779h9n#xB46`Zx&03v>K5umH5F|M~zhbsJ&Q3#Uh~2FcItH9SBJi?28JPYPe}*t<XgTJUj~4hxO<^Z<x4R(i@xPg&{xNrp2t@@|kw=jM{0%)q;neWpqyqI8J58Ai>BXBY?gQjk{8v2D3FB4J_GIx`{*dA#q%{oNn_r~5<1?~V-Ibex+J)+B0^RH){dYk%7G1WYV@T?=5hVPjab(HuWtqV%=Eb88@AhsufGnJa+W)P$26Y)eQ$2lJ_$lkADl*r+SQAQ?C*)&r;m4%j<3TC9ndfa_@*x&j~h80|>d!`;Bav$lrKME7CnRn94!IAx~?N}#X=;$(CZyg#~NFJWmhX$vti4QpOhJt)Ia9*l4Bg&=J%>Y@Imh2;pua&&@J1LYrsRY=^pclh>?tZME!0_Nep*ApYIZj3=12Y2ugkKSM#Rtyk2E1xk@(05rkWx@P@WA@YoX`m)cD`cfS3m)F8(;Kog`4qKjrJqBO=ul$N1^8f)){%CiBfE<yV{8*5d{1bk$(ma>uN9t#lR2b=cZ9T??g;J7^)T%$dAuuENpcdCmC=kB*iSQcUfcrKCwqV+DswGV_C+G0&9~GRB-qR5+TrblD#PU`<Nmzy6`A<LwZdLJ0KXL#vbifEGE&yYGf{`s(>VEpd*3uQ=OCi9X`1?uh7}swAH2RS6D*siDxf0ngnF$8Z^Ox#Wb#JYv*(R(;I9R7kJQhI{e89r^z<my;pg+Q;}?=OlqbDZKU3k0Z-R|^um_ND{td{bWIx}Y0tlfNKljHArO4j-ks0i*0WEa}gPS&0CON3EyK?Ywk5wRu>t!}C@5ngY(`KZyTTz*P{2290B<?~I_hc1X+N((dlznenK2=okq82Ue8rTcBN%>_@9>tL_867a^Kr3mo=Z#VZ0?ySaN-OJ0TsdeZCv#(RUa49}@*~@+Mg!drZfgn90d&L>>YxW{<YO{1l;YH!AyLez8)gKCS3h`GM(|1|9vaNug07kAsD}df0WCRrZ)&t9@Jq1AciF3QCVymD+LEN5k~DdEiE7*%1KDTVVl&2dG1*H{<%rqu=)CDQEh!w_h8h(z9GUP&_nLrZe6eYMY0hklbc1r_=ja_4t#kp4bw)?o%J=XqiU&^d1RrS8_PQPFV^~}7uoPit?NWyKhP3J>EW&9M3VtEK)+q3TjaHL%B4;3Dst~CMmt(+GnA-u%Gdvp`JdGh9dfj&EYm_jVgRSBj;s-FTh7*fkAJ+snDDOfJbb|4~TsMhsF(Yn4nCvDXcb10F<nR6M0I6mIa5YcZ2Z^=F=zRy+do($DuVr`guBTX6C_JM!_cnqWy6+?_L-$XY$k2nPvzmsu>1?j7>8yMy=(xQ;t$K3C9ce#5KZso)WD=@Bc-WSWCtjb1xH*@TptKeil-5ko{%a=PScEj$c+<~xwj0Ym-34<!=*A*2FT1gfLK_JIaZi<Ng`0{E2bwjL$2<g4+r&fYmN)MGgP`qYD^q|3f6c6EihSzmyk1Fc#{p+$9ax17AQZJia*8a3t+<nDuCnf_BU>70OCXv~T1$L}yk`xGND}LHBA+|#Bp{zvpo@v)*;67S>484SASjrACZjqBs?G}$O<Y7B7g0~_Lpf<iD?$J&e+QwAL_SCpO`%gpN6@vHFc`Bc;%KwxqZda6xn#2vR*ttC=Q-~j=UrU!&MmBINjPM!nLIe64U8w~qP{u84p6aBvySuv6SaI2tSWm`vAxMA_)<p2?~RJ1dzXSAOIkU2qhwT;4hdzu;b>7y)G#pN0@)ZPL2Y3s70QHW7vdGZf1<5fI$<g(V>pzZhQnIrQZ_2)j&Q-W2hk=gkssNnA6mshlQgZY9S6=zSsRvl^rDLPSwZtPVKM4qBfqV-AhKp!wWNfqFZsA~0HuYGKlD4=q3gO#4_4C#d9@owf;ew>BfnMz0D}B&+5^&E$~45E6}@ZXXCv<`hs8Ac(D7=(%H2$k?UBlE6Wa=)2pd$4in(>4!U<11Xht;|b?)ia1RqJz(VF8?$CP$Z5xb)?S<MH}76@{Ad6N7_-L-6Ax+%`d=zSmCd-O>U3>mu2ddR4B0OUzy3mJNlpU}AD4z#(m4z%(GH?sIl{n$3#E%r0PK0|Rza6gkWB3R$U_q(+C$A>tU2M{EhW6$e+2I1#*1Vd0c(OIimfi;=nq4&9jz*vdirEGF8cj#SR-@u>HQNEz}9_0_TyNKftl0X+R*-JgL$}-ymI1Hu$S66zUUmPNoyRZod=^?=eH>$WL2W4)0pK(|(08Wv5=S2a4U*>nJy(^OA_tM9tCEp%n0m}f{+LW1yTODBB3;>vFlR>?kYb#Vk6fP@SARD2wT?OO2Nk|EM&HKfpu?jmikAwylG*l3xg6Mis5r>!$?gI6pM`ZxtE+U@n?b<vPYDNPQA@jcSXe<N#Q2~u^ghZA1Zs>0hwzyV5w-!MMuj=bvryOLWfG7cY3U8RxySiaSElu2D)9vkxK6I^&R973YHW&I&$6e1YN5nh*=8<b{UE>z#70^oq)ApMUZl|mLu1XC|r2au&ZQ}*&w{0zo@P)eH;6`)dhkNj916r}R$8{23OMS+)1JzN=I(qWyCD2B3@s9ODx;yqtlXe#Cp-yLN*ebO?1+>%9rp?ojAZ=zTLo_^X6`~Wlyr_2aN;4wNUcuYW?)lA-opRg>24lf`fNwo%ugGndwi(8M2l@77gYQQ?bVS*uNl&92xFb;6yrc4yGq&+BCQH6~9<kYHtu!|H8ES2s+bWJ(rQSv{hE^QZAX*j@YwWm^;Rmd>J#NQ#=`?z29Gt0a3R5yr`A<vbxmGx-nbOgm<Gw~%NT^PEjp>@k<f}>AGjDMRAJb8y%9H^O2_nA|l@4#f=)6`q7I8R3UK6e}(>7kQl^=CbBKYD{+`b`h2~X3Z;`}}t7!ogf`h46MJ;@ZyyD=K90P}PuM3SeIFQ|^_2J)IX!YtkA=LcCj1z<YK1%*Tkf@D2g5OiSzb7q2Ln!|DVl0ku!u*g;m$y&BK#{KESHJ@aPLgH;bw3MVBc{P4Bxe925A(K~AJ|XyZQ^uq5E3hm{h{`Y0eTF2M{}PB3s3Q@Gvq^dh#D(_3xEH-3udv2wl;#ai3%Oe}I&I?hkW?)a7CT#vttE0gf*hIY7&9BYawAkXw^M{(=&fpPJo-V|)Ts1vr3jHIcU>rVXVT(1jop^URItI>ydt)D2N!IFAf`@8D@n!blR?iiZO}Zm22_A9z`fihjz^MS*E-ynMC4a|Wk@wgjau9*6nA*wtdR^b=`wDjVJ(Ae!u&N7c|jIox@5Flf$W!_tXNHj+9>F5$pBj_H&K}x9G_0&`N1dzB1$iE;A5JjYi$=I=Yrcvp3Q_H#GyU(`QRBM?HKrtqL?IrmdHk30!K`rf`74zew)%P1j_{N+HSQIJ*lR?@Km@e49<ltyZHMHz%^5Y5ixRnhxeY!cTBwn&8^fuQ4AZ$u%863){!Q!B@3)3p4RH(sFpQQBq$%dsSZ+z1h<Z)f^u+8kgfMSw^WjADUU-|F#XPaGk*5@r0It6T0We|jEMqSOvE1E2T0Q1pj?o|H6g-$POI%nJ_$s_zO83TO-AQ!pNV@ks+K6Js$)J1Txtgwh%`_I$I_{?SUOeGXF|T%_n2?suLUcPu~R*Xu~TCYj2zI%kMt=B`U}K%627O#!uM272Zrg3d6Y%I*e7}gF?1>M0|lvc&@}I?#f1Dmm@`0G*FFORXuYP<<}nu;XYV)w?7u1d&j&fPvlTn(Y1mVu!vVaN@HK1^^vMwNz0f_D`3GZv`_rHAg%WPWDaa`tX6$Umfnuy`+7gj8*~>zJs~lqUmWx(#PZ(w2#sEBAQGmnq?fMfqtHVhMJ}52}iG{?Q$6SQg_GAztXTRBF<@ei*?;sWzu5pU45$oFyhn+S$&g2FF8$f1!yr54fxq(6T8nZxCQ1CGE1(6F>Gc_49G3vk}>i%UY{rdJ+<kUghoN-8=D!Z8j$N;vQMs?T`DX*r%$Rx{-n5w=uf)|zrhxda65QtjFE&hNX=A9N<t4Xi72^Z8R6mj49;Yszc?c8qHleEBKr~*-Px0i_B*4(I9P;Ay@5E0MJyxVD>q9LMBJINg=^Dw74l&NbcrmmSsI|c*Y*|#9QX03s~oG#NDMcb!NMYf~zB`trEZ8a}MD<w=0rw)`;l&}(-&MMl{OoaraM0jElJ@s3q?~ccNoM~Dz?tUFCi2AE&FV1a!5GU`(8<tDk9e?P5q!aOeap6#HnzW2t`i@7?=7-VX0m67wWvW>j<-xkXTLTKUV>C~&<I3o%GW(_`UTRB*9acozqRAwrN}flN0JNG?QSEx9BLNEL#U4%Z_km>=gC1oFQr+JlN^O3Rbu}u2el~iuCKT%?C!~Pfcl<0h$mk9qSSi&XJg{=lLn<EX+kh(Vr&#mg1vtCy11mD8&Dd1GsD7wVAEA={_R$nsB%)G+8s;}GW(Z6dmHW%JJbo+~Fy)ct>S>uo_2#wN=|`q-ihKb_($&u|%9>A2?96SVetd`|GgCc%O6C4`5d=SeEO71;7ge|TON3XbXN!D%aWZ~x^?ExjT&NOzA4OJ)HuVJ9w?uK%=0(PVb4SZR^T}5ABMx#BffSD7az1!vMG!D|ZA3jlsz*ufoRK+{zyjYx5eWnVnc`en*nmLnljGcRoI8ba2jo^1b`>WEmBA@gZ_K+VqhSf?%lq`_WFo*jJQ~i1lYGh!loKTZ>4WN3UFVLG2Pzl{wLm6m5Kg~TAb9Ln!`ya+6BS#gqk5hCcBC`?Uq>Svj?9mvyJodD2Gw+fUD{!PV2B!A;zN((;PWfmz|3dhR($B%yg`Bt0i`V3OmPK~o=laRsikxWVy4o<OclO~1O{e+PpW8pQxEmn5k{CdRkT$~)GD=w0##~RJ7m^{X@pO$$dc$m6|GEZZAj=Y*EUK5PGCj}tJGSQbnsS--liMYB9O`k%-dPobTY2m%8E+6G$TR~I$q?+@Ro~k*uEc#79e6p6{x`XR<r`OLj{W5k|pv<!G<NI!gpE5D5Z0E!ecMQ^b&akJqP->$czfy6(8HdYcGIsRK?8OE~5q7#JU4g%YAGiCH>AcMQ$WLbtjI<4Oaa&FWNloGOF;F7RB81sBcH$Nc6XxqJu93E+F5+RyZw3zN7X8HRvaE+Cpm*quRa)Z|OzAkNX0eUTCWnMd4@E^34{#GVWYkI_q3}f4P2(o6~+q92C3^_`tPotB>oGT<$O6(*@T_*V@neq{^k|8L}1p=D`(#KiR|f{`OHa@5Fp&B(J&3??9bF&vW+^M3PGDWcu4HD`7gAmssQrdH_ZyM7045BHR=g2;Q1~VN<Bn%h4+>GS0T#)j}7@C)-L_KA|LuA_H!hD-=$si$#Ci;LYg|3oG~?aORa1705GuunCYf>wVB{j$Tg@aWNUxp2>?a+CrFK#9ECU;R$+VLPP6M0_eejM4~tqD~|0TtX14EI1m>cXjIHp*Q0o(E0x-bgqja1iELaVJwe%aiXA!ScGN)PgkDS5JdWZ_`L)okX;o0Wg+T<<N(<cvYYcnB<urrsgkOS*T)S=n+Sq2*77`g264|*#W?U>YI1hnr%gazzNpV|j%u5kwdzyVwQ|qmRl(?`hCuK2%MF~HHA=sD;(L?07DnP58W;3;DE7On&b&5^x421Js55hvjJAvgwrNM`5v@Qg!3!5ixg#Oh=2U;;Q7l)3ERFncID*S;;X9bVOYIEb5NI3AsoT6lRxLQT&YC4hEu!+XI?n~YY?YciHMfpy3jZd(3-6#gk@0||pdtt2&dQtD|F#WLS{9Qda(y6%gqZVt*DlCrPWkpYbxfYx{tHK3qa6;pgH#hY7c5pPP$M?~Fd1?C@^oB2kb6)+^jH9}fhac|se%ZN6GA@9+d4VUI2=#{N7VpeJ_0o8}kf{^s1|T1^i4bMoV&XBq?#cV3BZ<Nm1n{wdI}P{83ygSBA31WMLu8{l{?+vNkp8GVSUxr5>1gVu0}TaWW5Ee4)_cnOV&XG^7x>+a8D>cy_t7<O*~FHk{4LfgIK4UY4YM?Z4hDi>HAz*?RL_}uQp>EF8dps9&^l?XmY`$4`4v6eZAm;eQrY+f8vTBdLD%R9&Ns*T<|ux}9Ghx+?!?O3_*vm3of}O3gWgEOijR)-(NR7YaOYxVa$GT)+e`1q(>pN3ri$X-W~&beM}fleWb!MT(D;h#=f^=5HgQ{Z2JckBIWH3C^8oo0>6b*mWV%kFXjb~Ak=g$BfBcXC4~Me9`2')).decode())
_V18_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_V18_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_V18_URGENT = {"DIG", "PLANT", "WATER", "FEED", "CARE", "PLACE"}
_V18_STATE = {
    0: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
    1: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
}

def _v18_step(obs):
    return int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)

def _v18_positions(obs):
    farm = obs["farms"][_seat(obs)]
    return [tuple(map(int, farm["farmer"])), *[tuple(map(int, p)) for p in (farm.get("hands") or [])]]

def _v18_inventories(obs, n):
    values = [dict(v or {}) for v in (obs.get("private", {}).get("inventories", []) or [])]
    values.extend({} for _ in range(max(0, n - len(values))))
    return values[:n]

def _v18_tile(obs, pos):
    x, y = pos
    grid = obs["farms"][_seat(obs)]["tiles"]
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]

def _v18_valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _v18_positions(obs)
    if actor >= len(positions):
        return False
    pos = positions[actor]
    tile = _v18_tile(obs, pos)
    inv = _v18_inventories(obs, len(positions))[actor]
    op = str(order[0])
    if op in _V18_MOVES:
        dx, dy = _V18_MOVES[op]
        grid = obs["farms"][_seat(obs)]["tiles"]
        return 0 <= pos[0] + dx < len(grid) and 0 <= pos[1] + dy < len(grid)
    if op == "DIG":
        return tile not in (None, "LOCKED") and not (isinstance(tile, dict) and tile.get("animal"))
    if op == "PLANT":
        return tile is None and len(order) > 1 and int(obs["private"]["seeds"].get(order[1], 0) or 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if op == "HARVEST":
        return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
    if op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return tile is None
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
    if op == "PICKUP":
        return pos in _V18_ACCESS and len(order) > 2 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
    if op == "DROP":
        return pos in _V18_ACCESS and sum(int(v or 0) for v in inv.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inv.get(order[1], 0) or 0) > 0
    return True

def _v18_toward(src, dst):
    if src[0] < dst[0]: return ["EAST"]
    if src[0] > dst[0]: return ["WEST"]
    if src[1] < dst[1]: return ["SOUTH"]
    if src[1] > dst[1]: return ["NORTH"]
    return ["PASS"]

def _v18_cap_pickups(obs, orders):
    remaining = {k: max(0, int(v or 0)) for k, v in obs["private"]["shed"].items()}
    result = []
    for raw in orders:
        order = list(raw or ["PASS"])
        if len(order) >= 3 and order[0] == "PICKUP":
            item = order[1]
            requested = max(0, int(order[2] or 0))
            executable = min(requested, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - executable)
            order = ["PASS"] if executable <= 0 else ["PICKUP", item, executable]
        result.append(order)
    return result

def _v18_transition_failed(before, action, after):
    old_pos, new_pos = _v18_positions(before), _v18_positions(after)
    old_inv = _v18_inventories(before, len(old_pos))
    new_inv = _v18_inventories(after, len(new_pos))
    same_day = int(before.get("day", 0) or 0) == int(after.get("day", 0) or 0)
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    failed = []
    for actor, order in enumerate(orders):
        if actor >= len(old_pos) or not order or order[0] == "PASS": continue
        op, pos = str(order[0]), old_pos[actor]
        if op not in _V18_URGENT | {"HARVEST", "PICKUP", "BUILD_COOP", "BUILD_PASTURE"}: continue
        old_tile, new_tile = _v18_tile(before, pos), _v18_tile(after, pos)
        ok = True
        if op == "DIG": ok = new_tile != old_tile
        elif op == "PLANT": ok = isinstance(new_tile, dict) and new_tile.get("kind") == "PLANT" and new_tile.get("crop") == order[1]
        elif op == "WATER": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("watered_today")))
        elif op == "HARVEST":
            oy = int(old_tile.get("yield_units", 0) or 0) if isinstance(old_tile, dict) else 0
            ny = int(new_tile.get("yield_units", 0) or 0) if isinstance(new_tile, dict) else 0
            ok = ny < oy or new_tile is None
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}: ok = isinstance(new_tile, dict) and new_tile.get("kind") == op.replace("BUILD_", "")
        elif op == "FEED": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("fed_today")))
        elif op == "CARE": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("cared_today")))
        elif op == "PLACE":
            item = order[1]
            if item in {"COW", "SHEEP", "GOOSE"}:
                animal = new_tile.get("animal") if isinstance(new_tile, dict) else None
                kind = animal.get("kind") if isinstance(animal, dict) else animal
                ok = kind == item
            else: ok = actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) < int(old_inv[actor].get(item, 0) or 0)
        elif op == "PICKUP":
            item = order[1]
            ok = (not same_day) or (actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) > int(old_inv[actor].get(item, 0) or 0))
        if not ok:
            failed.append([actor, list(pos), list(order), int(before.get("day", 0) or 0) * 24 + 23, 200])
    return failed

def _v18_jobs(route, step, horizon=8):
    jobs = []
    table = _V18_DAG[route]
    for future in range(step, min(719, step + max(6, min(12, horizon)))):
        jobs.extend(table.get(str(future), []))
    return jobs

def _v18_first_order(obs, actor, job):
    _source_actor, target, order, _deadline, _value = job
    pos = _v18_positions(obs)[actor]
    target = tuple(target)
    op = order[0]
    inv = _v18_inventories(obs, len(_v18_positions(obs)))[actor]
    need = "WHEAT" if op == "FEED" else order[1] if op == "PLACE" and len(order) > 1 else None
    if need and int(inv.get(need, 0) or 0) <= 0:
        shed = int(obs["private"]["shed"].get(need, 0) or 0)
        if shed <= 0: return None
        if pos in _V18_ACCESS: return ["PICKUP", need, min(6, shed)]
        gate = min(_V18_ACCESS, key=lambda p: abs(pos[0] - p[0]) + abs(pos[1] - p[1]))
        return _v18_toward(pos, gate)
    return list(order) if pos == target else _v18_toward(pos, target)

def _v18_beam(obs, route, actors, missed):
    step, positions = _v18_step(obs), _v18_positions(obs)
    jobs = list(missed) + _v18_jobs(route, step, 8)
    choices = {}
    for actor in actors:
        rows = []
        for index, job in enumerate(jobs):
            order = _v18_first_order(obs, actor, job)
            if not order or not _v18_valid(obs, actor, order): continue
            target, deadline, value = tuple(job[1]), int(job[3]), float(job[4])
            dist = abs(positions[actor][0] - target[0]) + abs(positions[actor][1] - target[1])
            score = value - 4.0 * dist - 100.0 * max(0, step + dist + 1 - deadline)
            rows.append((score, index, order))
        choices[actor] = sorted(rows, reverse=True)[:6]
    beam = [(0.0, frozenset(), {})]
    for actor in actors:
        expanded = list(beam)
        for total, used, first in beam:
            for value, index, order in choices.get(actor, []):
                if index not in used: expanded.append((total + value, used | {index}, dict(first, **{str(actor): order})))
        beam = sorted(expanded, key=lambda row: row[0], reverse=True)[:32]
    return {int(k): v for k, v in beam[0][2].items()} if beam and beam[0][0] > 0 else {}

def _v18_needed(obs, job):
    _actor, target, order, _deadline, _value = job
    tile, op = _v18_tile(obs, tuple(target)), order[0]
    if op == "HARVEST": return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FEED": return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today")
    if op == "PLANT": return tile is None and int(obs["private"]["seeds"].get(order[1], 0) or 0) > 0
    if op == "PLACE" and order[1] in {"COW", "SHEEP", "GOOSE"}: return isinstance(tile, dict) and tile.get("kind") in {"PASTURE", "COOP"} and not tile.get("animal")
    return False

__version__ = "v18-p0b-task-dag-rc1"
del agent
def agent(obs, configuration=None):
    try:
        action = _V18_PARENT(obs, configuration)
        seat, step = _seat(obs), _v18_step(obs)
        state = _V18_STATE[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.update(last=step, route="default", prev_obs=None, prev_action=None)
        state["last"] = step
        if step >= 72:
            shops = list((_get(obs, "town", {}) or {}).get("unlocked_shops", []) or [])
            state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
        missed = []
        if state.get("prev_obs") is not None and state.get("prev_action") is not None:
            missed = _v18_transition_failed(state["prev_obs"], state["prev_action"], obs)
        positions = _v18_positions(obs)
        orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        orders.extend([["PASS"]] * max(0, len(positions) - len(orders)))
        orders = _v18_cap_pickups(obs, orders[:len(positions)])
        broken = sorted({int(j[0]) for j in missed if int(j[0]) < len(positions) and orders[int(j[0])][0] == "PASS"})
        for actor, order in _v18_beam(obs, state["route"], broken, missed).items():
            if _v18_valid(obs, actor, order): orders[actor] = order
        current = _V18_DAG[state["route"]].get(str(step), [])
        for job in current:
            if job[2][0] not in {"HARVEST", "FEED", "PLACE", "PLANT"} or not _v18_needed(obs, job): continue
            target = tuple(job[1])
            for actor, pos in enumerate(positions):
                if pos == target and orders[actor][0] == "PASS" and _v18_valid(obs, actor, job[2]):
                    orders[actor] = list(job[2]); break
        for job in _v18_jobs(state["route"], step, 8):
            op, deadline, target = job[2][0], int(job[3]), tuple(job[1])
            if op not in {"DIG", "WATER", "FEED", "CARE"} or deadline - step > 2: continue
            for actor, pos in enumerate(positions):
                if pos != target or orders[actor][0] != "PASS": continue
                if op == "DIG":
                    tile = _v18_tile(obs, pos)
                    if not (isinstance(tile, dict) and tile.get("kind") == "WEED"): continue
                if _v18_valid(obs, actor, job[2]): orders[actor] = list(job[2])
        action = copy.deepcopy(action)
        action["farmer"], action["hands"] = orders[0], orders[1:len(positions)]
        state["prev_obs"], state["prev_action"] = copy.deepcopy(obs), copy.deepcopy(action)
        return action
    except Exception:
        return _V18_PARENT(obs, configuration)
