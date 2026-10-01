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
    0: {"last_step": -1, "dues": {}},
    1: {"last_step": -1, "dues": {}},
}
_PREEMPT_ENABLED = True
_PREEMPT_FRACTION = 2.0
_PREEMPT_MAX_BATCH = 30
_PREEMPT_MAX_CLONE_DISTANCE = 6
_PREEMPT_MIN_PRICE_RATIO = 0.0
_PREEMPT_MIN_FUTURE_QUANTITY = 4
_PREEMPT_START = 120
_PREEMPT_STOP = 716
_PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")
_V32_PREEMPT_HORIZON = 23
_V32_STATS = {
    0: {"events": 0, "units": 0, "horizons": {}, "late_events": 0},
    1: {"events": 0, "units": 0, "horizons": {}, "late_events": 0},
}
_V45_TERMINAL_STATS = {
    0: {"last_step": -1, "events": 0, "units": 0},
    1: {"last_step": -1, "events": 0, "units": 0},
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
        state = {"last_step": step, "dues": {}}
        _SHIFT_STATE[seat] = state
        _V32_STATS[seat] = {"events": 0, "units": 0, "horizons": {}, "late_events": 0}
    state["last_step"] = step
    return state


def _repay_shift(obs, action, step):
    if not _PREEMPT_ENABLED:
        return action
    state = _shift_state(obs, step)
    dues = state.get("dues") or {}
    due = {
        item: max(0, int(quantity))
        for item, quantity in dict(dues.pop(step, {}) or {}).items()
    }
    state["dues"] = dues
    if not due:
        return action
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
    return action


def _future_sells(step):
    if step >= len(_ACTIONS):
        return {}
    result = {}
    for raw in (_ACTIONS[step].get("market") or []):
        if len(raw) >= 3 and raw[0] == "SELL" and raw[1] in _PREMIUM:
            result[raw[1]] = result.get(raw[1], 0) + max(0, int(raw[2]))
    return result


def _v33_known_demand_before(obs, item, step, future_step):
    """Fail closed when known demand could restore price before a future sale."""
    town = _get(obs, "town", {}) or {}
    shops = list(_get(town, "unlocked_shops", []) or [])
    for demand_step in range(step, future_step):
        # A new shop identity is not public before its unlock; do not cross it.
        if demand_step > step and demand_step % 72 == 0:
            return True
        if item != "FERTILIZER" and demand_step % 24 == 0:
            return True
        if demand_step % 4 != 0:
            continue
        for shop in shops:
            products = _SHOP_PRODUCTS.get(shop, ())
            if item in products:
                return True
    return False


def _preempt_shift(obs, action, step):
    if not _PREEMPT_ENABLED or not (_PREEMPT_START <= step < _PREEMPT_STOP):
        return action
    state = _shift_state(obs, step)
    if _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
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
    dues = state.get("dues") or {}
    shifted_total = 0
    shifted_horizons = []
    for horizon in range(1, _V32_PREEMPT_HORIZON + 1):
        future_step = step + horizon
        # Keep every repayment before terminal liquidation begins.
        if future_step >= 716:
            continue
        future = _future_sells(future_step)
        if not future:
            continue
        owed = dict(dues.get(future_step) or {})
        shifted = {}
        for item in _PREMIUM:
            # V33 already proved horizon 4. For every farther sale, wait whenever
            # town/shop demand could restore price, or an unknown shop may unlock.
            if horizon >= 4 and _v33_known_demand_before(obs, item, step, future_step):
                continue
            future_quantity = max(0, int(future.get(item, 0) or 0)) - max(0, int(owed.get(item, 0) or 0))
            if future_quantity < _PREEMPT_MIN_FUTURE_QUANTITY:
                continue
            base_price = float(_MARKET_PARAMS[item][0])
            current_price = float(_get(prices, item, 0) or 0)
            if current_price <= _PRICE_FLOOR or current_price < base_price * _PREEMPT_MIN_PRICE_RATIO:
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
            shifted[item] = shifted.get(item, 0) + target
            shifted_total += target
        if shifted:
            shifted_horizons.append(horizon)
            for item, quantity in shifted.items():
                owed[item] = max(0, int(owed.get(item, 0) or 0)) + quantity
            dues[future_step] = owed
    if shifted_total:
        action["market"] = market[:10]
        state["dues"] = dues
        stats = _V32_STATS[_seat(obs)]
        stats["events"] += 1
        stats["units"] += shifted_total
        if step >= 680:
            stats["late_events"] += 1
        for horizon in shifted_horizons:
            stats["horizons"][str(horizon)] = stats["horizons"].get(str(horizon), 0) + 1
    return action


def _v45_terminal_inventory_front_run(obs, action, step):
    """Sell every executable liquidation item one step before liquidation."""
    seat = _seat(obs)
    state = _V45_TERMINAL_STATS[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state.clear()
        state.update(last_step=step, events=0, units=0)
    state["last_step"] = step
    if step != 715 or _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        return action
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    remaining = _projected_shed(obs, action)
    for raw in market:
        if _is_sell(raw):
            item = str(raw[1])
            remaining[item] = max(0, int(remaining.get(item, 0) or 0) - max(0, int(raw[2] or 0)))
    shifted = 0
    for item in _LIQUIDATION_ORDER:
        quantity = max(0, int(remaining.get(item, 0) or 0))
        if quantity <= 0:
            continue
        existing = next((order for order in market if _is_sell(order) and str(order[1]) == item), None)
        if existing is not None:
            existing[2] = max(0, int(existing[2] or 0)) + quantity
        elif len(market) < 10:
            market.append(["SELL", item, quantity])
        else:
            continue
        shifted += quantity
    if shifted:
        action["market"] = market[:10]
        state["events"] += 1
        state["units"] += shifted
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
def _v66_swap_margin_gain(obs, buy, sell):
    """Exact two-slot clone forecast under the official per-unit market rules."""
    if not (
        isinstance(buy, list) and len(buy) >= 3 and buy[0] == "BUY_PRODUCT"
        and isinstance(sell, list) and len(sell) >= 3 and sell[0] == "SELL"
        and str(buy[1]) != str(sell[1])
    ):
        return float("-inf")
    buy_item, sell_item = str(buy[1]), str(sell[1])
    buy_units = max(0, int(buy[2] or 0))
    projected = _projected_shed(obs, {"farmer": ["PASS"], "hands": [], "market": []})
    sell_units = min(max(0, int(sell[2] or 0)), max(0, int(projected.get(sell_item, 0) or 0)))
    if buy_units <= 0 or sell_units <= 0:
        return float("-inf")
    inventory = _get(_get(obs, "market", {}) or {}, "inventory", {}) or {}

    # Original clone slot: both BUY in lockstep and pay the same sequence.
    buy_inv = int(_get(inventory, buy_item, 10000) or 0)
    for _ in range(buy_units):
        buy_inv -= 2

    # Swapped slots: opponent buys first, then candidate buys from lower stock.
    buy_inv = int(_get(inventory, buy_item, 10000) or 0)
    opponent_buy_cost = 0.0
    for _ in range(buy_units):
        opponent_buy_cost += _market_price(buy_item, buy_inv - 1)
        buy_inv -= 1
    candidate_buy_cost = 0.0
    for _ in range(buy_units):
        candidate_buy_cost += _market_price(buy_item, buy_inv - 1)
        buy_inv -= 1

    # Original clone SELL is symmetric.  After the swap candidate sells first
    # and the opponent sells the same amount from the resulting inventory.
    sell_inv = int(_get(inventory, sell_item, 10000) or 0)
    candidate_revenue = 0.0
    for _ in range(sell_units):
        price = _market_price(sell_item, sell_inv)
        candidate_revenue += price
        if price > _PRICE_FLOOR:
            sell_inv += 1
    opponent_revenue = 0.0
    for _ in range(sell_units):
        price = _market_price(sell_item, sell_inv)
        opponent_revenue += price
        if price > _PRICE_FLOOR:
            sell_inv += 1
    return (candidate_revenue - opponent_revenue) + (opponent_buy_cost - candidate_buy_cost)


def _bubble_sells_over_fixed_spends(action, obs=None):
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    safe = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"}
    for i in range(1, len(market)):
        if not _is_sell(market[i]):
            continue
        j = i
        while j > 0:
            prev = market[j - 1]
            positive_cross_product_swap = (
                obs is not None
                and _clone_distance(obs) <= _PREEMPT_MAX_CLONE_DISTANCE
                and _v66_swap_margin_gain(obs, prev, market[j]) > 0
            )
            if not (isinstance(prev, list) and prev and (prev[0] in safe or positive_cross_product_swap)):
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
        action = _v45_terminal_inventory_front_run(obs, action, step)
        action = _v17_r5_counter(obs, action, step)
        action = _v17_md_counter(obs, action, step)
        action = _v17_room_guard(obs, action, step)
        action = _terminal_liquidation(obs, action, step)
        action = _fulfill_planned_sell_from_idle_carrier(obs, action)
        action = _rank_sell_slots(obs, action, None)
        action = _bubble_premium_over_non_sells(action)
        action = _bubble_sells_over_fixed_spends(action, obs)
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


# --- V19 hierarchical MoE: safe V17 prefix + step-360 route suffix ---
_V19_ROUTES = {
    'default': json.loads(zlib.decompress(base64.b85decode('c-rk<O>ZMva{Mnk^B`6gNy)d~Zmy@XJ)?nIZDKtj1_O8v1IGF=_Ra8rw_4&yu`)6;GG9^Kv$Llb*iy0HSH8^1$jG1m_vYV!`Sq`V`Ss?Xe!BVb-RI9Y`^C+F{PJJ__TSGRJpcIDUw-}1zx>bh&p+M#;me<Y{_*kQ!<Y9@H;bFyciVT*{|@`bPdDFveB9n#{P6X6KX11mo`3QC?WczyZWf!#$A`aP9Y22e!^iL6eR}?n&);pgKYo4i{{I#iFZc2NpT7J!{)O|4{&ch3etvrS<{us&pT4`<k6+z;(0K^rgWNfoe8V5UeEjs`=jYjc`tmX#qsJefs=er^ckj2S0be}k`M-X6I!&(jxIccK_{*`rd)hv}{PpB{<SFmp`9nH9kNoxVcN>R7Cb%*tGSR2)5Rc8y@9_;@_sPpsULKd4UOS+}<8ssd`QeMaN@RNNY8@V2oZiCVz&_R&$<D7`q<BQf$%G?`|NQX2cy*#30=~PlD8Jbww0##$(DW7?59oFIi<g6N6|C?rx7-H<y?nI2PtnEdJ$pKYCB5Gydkd`6X;CkKU=Mlt^lAJ4>E}OgAD=#c`uMLeOVavgz|s|7&F(w%4&Tl^)n1L<yyvr3v4za7$QVUnnO_g`=!fv^M{{Q%Su*zaF`;3xHXl3$ynXA7g;NG>u6f9Z$A=&3LtejyKjig?OH228`{}FCKN|2?bA`-YADOw{b4rf~4}Cv0;@$MCUWd<*&iM=N_v8W)&n42Qu%Arf=cmVayFY9nAO8%l3oy9jij7{ynLFhR_;8hdqQ9~J5dEU}Ze!goO$B}0?VX5s$)%LK+oJ0mSbclfsYec6SG9XjyPhh6LuoB4lURwWXK{j#255A=$98G*acK@~u0k-2=V&T}P0*n3{GdvBcQ#9TM1bA$nMqUb`2svq@u>1%TD*ES4<zMNXf6%3Z<$+no;$3;0~?O+gBeD@|2D7Ugu5eM)8RRI+Za3XVsen3xU|H(xNyNB^FP;2#kY|hXETRJxQZu#U36PU0mgOj-{w7bzJAR`oV(}HgW^##boKmGXqBitaJX%R$B=86y^L#s7wQc|u4=e|!dS>1t51k{#~yB$1Z*(N)#O}=Z*%eX->8>xt^4|v^L_uYldkI1Hy{2W72ohX8~pG5QTB}3Z|1^e@nPo1WS7!R7kDO>_f~T?O_e?G;&+e#(wNnH$(DWH#uuYLJ=lfXPKl;)P7hyOOR`3jd-%GM;V%W)qbtxuR8u#74L<=dHeTWLOTy);&;Tkc!koAHPR;aDN(zBGy}7eOV~t9B%K9wGF2v8FV>}%K0USE~5j+Hm=S=Ubm3s*TN8=?;efWHQ-;w(|AA0vK2>C(`RqJU85m;XoFLK=-pdVc$)GrPx1p`zE#mGI^TABGrQGxl1yHZ@8vE>C;*!{G!O1V^lz4qN-m<!c7IV{HLi}!l8rYGBd`oRga?JuH9NVz?yC!Ksg1bJj8RYYU#SQ1wl_>Spchd&kQ4bt16wo7|9!<`xno4^50Z|YQb-?~31VCDQ4;3MUIDEv}`dEh5t2{O!)p^mC7G)4`4oBMsjV@tjQoDpYB%sqU|1)6Tq?usLCf){0Qs*-1_5kKt<ci8uROESq~wiH&@wF=#wv&X`b4(?60dvIrW!un6>qe9jKJ7+uBUn_cUj+eqivnJw<@k16Y5v5%6a912bw%x<SvvFE`W0?Y2!G-hsGz-5)l!n90nET4l4sv>_Yl+q(x(<>#2m(L7!uhREd;j!*4s0p;2^Xuh>^$hlQeJ2lOJLJZmUP*9uQq=F@cl4wXnrCu(%}Uha)8FkCK4xC@~}oPRZF`8r_xWz1`ft)lfakp9gmk8Tt%;C=PYFUJV$OHZj$~EJ!WLNLNjQOv=?90o=<9q$QSuWSEwg?&5+P9%0Ul_kE`?yYpUj=oO&-WovUghog&}ht0#o}l+%8&bZ_FaJ9f6)*Xo5q;4yYCw#N9H->>ip?U4s=gnf&~%Axb0pG+ol4yPudxf~H$PHJafU$0_kfV+c+=$y!~9Efq@JjceNec6B@Sx02;jNLE@HGP{+<P1ApS!qX|U0M7s=!N1MQejUyL6;xX<(HLhF<=`)eqp7A55+Vj8=lBH6T`<s@&r6h?>!zBgUT&~^5idKwxhSx1OTg0JHKe%KHBGl3=1Mm8XG>Zm4q&k^R6|UNOKfrBg~Q^p)mv-9Ys-2>D59bBT_=FOB=adh`{GjxR*?vg89K=&M_=<_0Iw*m<$)n^=kSeofvJGd?oLtE8b;TB}1J;Li7zbBAx|sbP{y0G^czevkcUV8GCO5@5knIOP;$3@u5pv{JjvbC#RMA)!;IzNGF-2nsB@#U_2AbYXTDu>5F<*07#x#Z=y74yZuh9Iz~xBq*W@J0beJtp!1tf3Z_Ls$*(F3ykyAcsT=`|a)L;V`LcyVFB4}W@1Gik&{MTLdxo=aotc8r2XKVIgEjt8>WjgJqTs-l3THq(0^S&9JV~(dv;YL{v2zUM1N#~3FHf{MTgN8Jrj()_kBLgURZ?M?_tPd`X1AFIgQv8kc>w9luxCN4?6@RMVz7Xmf*@eA+^;xr{*^k-s&wYU5!}sADqpM7YOdOA@Gu?ti||7^Bv`o;G881W!OF?1xlsbjp2Xh?0+JvyfFG9fe)hltrw}+UG+w9}SDhAfnlAlMS~9JKg|i@aSxJU>>^-989s8&V)Rzf8#Dmnm_tT$z`1sGz!OZPL{3U1_;)}VR^-eW^1e9qRFuJ6}YHOLSDYBGm5LN00Vv>Qt6%HW2$Y2Vbp(oS-!%!nL8Fm4pq63x_0d}=gV8@VhLQBfH<jR)<qewl~N=*diw?b>EP>V{Kjcg5da#O5yF4JT^8of{^qYzkLiD630A_|qpw4w<y5dy~Y%UOP*-NZDw0Bpp*`K40DB)ot-42PD^^{v0I=lu@}S_})0v|y?(B&rwfHl|T<JQZgr;_?JP00N|uxOhRYr@52LFnZj5Vi*@Zzig!{otCkx=rDcCg;v-kE@=fcSjLP7r7~nOpGGHzf@#%i=+*Kh-h}jA#h8hkLvsoX$ElpNbj3R4U~9tHjo{moDjdO*BhLWUE$Tcj;3%>Kd9Wn*8b?ls@wLGDIlVm*L3OI6tg8xMQ)9Qv1wkxNXh;JxOC}>bN2<#JI^gkgg|{O`^QD|?a3Ey>3Cuj2)APpK^7Bdz;9(oBh1&!~S8xW;t7Tu%-{e7cirMb31sRLdK%$KwOeYvW`GJBx4Kmr*yo)4WwiuZNk+mpMsAnS>E4dZ2pUDIZ8)&^xlr7TR#Ati5G(W-&lcgxKb>UaK-Q{RI0~@2>MV?=)B)$mfhi35fa?CWLKV<n>-{i!{G=Ism!VwWXPOu+qoNjt|+7k>>X^<S1)oneH>V98UO5&0jlY<>fMAR;^ODzRE7(~M*wvU!iNGcOitz8oVv7h8iES9gRLRgqFMsvS4EM~aNgE1?Yvx+V&0$7}$Va#(0oze38&#U(M@O1cF(i#*u9S!c2<FDQ}<2(%Bp(c>n@Mz*y8iCjRr*^3ZxDee_vVTTqCD8?uKt`qnMymiOvXG0kdY?=N*$icjiRL{~kX{)#SQ`eC_@k0Rsi>@no<d%F6i$FFLjx{hU^y~HAbLniS39G)ubiQ5#hY<64yzcS9oxio^vB9c>f28e5Ao7VAeQ}`)6?(EQr7|D<UF|u2PGHXIA*jDa|_H<z9D1jQVavl`0*tVPDXU@?5`zU$1XZVTzM0`1NaDTD=zP;-$M0>)iC=<uZ#xC%YIqF3Z};hL5l~h%Q=OKIsrCJZe6(90F$6s0SS35?&T40VtjDio&ruLB%_6*qFh>{mKDMSPt^vaC@g|=zusgZbP8)(3Ik)KLPe^C%&7L_DUKVeGcs=mRs^t!oYtr{iZKaNEQoI2;d~9o*Ra=FwJb=$Am!Ltk=G%cEmWnmhhV+0w5+sgR7y8eYEBC3aNZD@vT(=%7L=N@t5FhM29cg$6{HBm2GgFewi@0Jms1NQbWT(NcglE>TmkNbb3#jPyQA5)%7&4Yt@Ynp0kVKjTA@gVbA__XxLT1C)Gf8n08;@F!&3^{yi!43xOLs7X}>AAfF-I`0pZx`U#F7i;VnuT3ko8a0%q7bq$E8YA-1$NJ3C|OJh7M;mXpO{q2gcMY9}k$f3%1!;_XE}ye7NxwvO>!)U-tIMNpT3q6@htRReX82me|WT`H2Y#)h*o@UnaHfs(hmYi9>&w=syMz|yl_YTuRUVzD5Wl^8|Pf2{nV<`#s5LnrhS&Gvh(R9*1IVV26Bh_bJ@IoJC{rh|oLT!KrDis<HC?{&c$UW-x?N>JpJ!z4BB)4_-ytYgb=>uP;yf)7cq*0i$XF4qdiCF%}wNsbihp9U@KO_0PoJ~d-P!uKCP{R!|1tuDG<OdCOywM=yxKE9OUN34eY`VE2tMSd+M_#i80Eys{{dF-m#HzYN0W=GA}75Z<;T!IM6JUk`JIfzBA1*wZ!nLh;T@G=RNOicqxr#zu~U_)qg#Ha;a_YNh-Bu$AcQf@deqrGd-^$9gREy+q5fX5l;Tr|Fnili_UY^J(HR_&w`kHk#poA6oqn~FK#RK4oeIW3gyMYj@}j7GwW_Wky^{19(W8VWm0c@$IM$;)<j$(-5z5S-gAXXb}c6kE!CleaH%I~XOIy-x(|wRX{E5La^UY#Le5SKl{q9}K{lo8p}Y?NV@AdHoQKi3GlglxV4LkO-#|Cj<nEU{YPYq^h{dB@Ynaz?a{de9{KRh$N)cWRrK7#d{?6%MA61uSEzjqQ+I01*5BEDmgn)J{j(Y7UUqLIj-LhIhaY`bcj{@qgtjw@!kSA=zls*{9m1lwF3%w6^e#*%V$uI28%Q!RU^lA&`Na_@3pLXhR^~{P)7+m!$n!U*MUV7z{yKxnd_0eCdcEww;V`NkbwjX9AeOuCwdxHJH{MjP)Y%+j(K!8X)s1H9GaLG>lR1~FlatOtKUQ#NUrEWkAitoPtYR*Z}rPuHsK59y$m85Kx1~V(?kMZ)43~Z!|qY$%yOG1lc?<=Z{`yMLkmA{4HJ<7igg-Y2PLMQI+>-wIa|wfixzRr8>gj~V(S-RzaX71K+>6wz?y{QnqXup066$ZYpl&X-k8>0UPJqeww}@2kRtCY<T>HvGi229C2W#GB4Ub$M#@9x0@QIHR(V15iUIi%Z*v`7qdtYsIn2>`bbTw11tIew@}=}zzqO)I$XIxEp~34mu+0D;MS6V>{m>*g8i2^Ui-<LvK_r~n(+^gV*aq8HsR&eaf#32L2Q*y_#6>QpqR*cnWnGrW7wPxkPOT4Ktzk|<<e>P+!Id;9s}Zi6EQ<<L^)7eO9OPxYz%u3H(o?R$dZC>cu`2O>S<2PNg2?Of+93u$N1>mhUM;ZJT=k}Yu5uz<w~_S|ovF|Zy13a>KXYe>q-o+<U)I5vS|))3=-6})*ziIUwpEjA&feuk`yY^ED3ueWb<8e+0>iSU1Zu3AHHAG$EJH_gxpvZqasg{_R+cf;k)RljR7?yMvdqw?B5;xFrM?WKOZiv{qTNOE9$jTN7_ztl1=43C-&KM?{u5K*SIT1UV^hEiEW;Zq#Fw{mk%`?s_7i_RwJR9FH%yG_yp1l6LmJ6W(e!LPYg*{ZcM>}hQd?$9+5=&Au&-!?5w14{K=RPbdEHXJrCx1>2+H0u$zEw}8ZdC{LAheJ%xKu|C&;n$rqP|PplxZ`14;~wSc^8M!fBAa1(`JWl8Pg%&M_&+PL4FoSmS<rSM713o4c%lZO`o<7}}-TOs-jkRjpQWRaAso3;q+ySHvOOBuyTn8ty0OAvc!4p@a;iv{-bGg0IM52z$@l^|BOoQe?<|6aZ>eF1){IJs*fR^)aN^i>M!I>uk62!gRA@#`?ni-BxI4U=vqqX99+KWeuP#(?&v0tQi`QZzWV%`&Vk3lxEos(9@*3Ek0^|$=uGvJ!3Tcv{Ro?inyaGFw$fXAO51IN0lfN3ENS5=qc0sq<#GICD4s*wXFbTT@J1gmWy2;c7gyHa2<JyK~)GAQ=9mX&@k=0*=0lpAJbnvfi-4YH#;)qJV3C90M##17)}RJv{A(|Z(j@FBxgVc#z|tL2p<pY_UjV8l^2bPEi<%@)r;qBEf|*6F{5(q;T$+&Ta4ckdJRCwc!!RlWvqpYatW__Zc((wwh4ZYa_bCIa>(MNydNxeoLz+~+HlwI>w3?5oe!1}1LHw^p>Ig^mQ3M^XC2)*EQOx?xJHNd#wnbD6EWKup7StS!ZXNG$w1dsGa{kDHLGGabeZ1u2$QhyOBI|MgC?B+Wv3RZRp;8rN6tw}_gB)Z@tapxBEni(>FKP-lC|7wh2!g9T6vL0*UTJaP*k#Io7AA~P1~@^RFmzz$W2M)Nn-Wq#-SA6uG+P8)TU6h@Kk~Yt?xtpd@!_DA)U}e<+xKGVkn72xsqS96igr&e$`En=LX9R=b@T71h$e2oWY_U1KN{HW3_r$fOHtvo9immhnnAv|K=@euB{#7^Mno~nEHrHLGeT-$`+F9DJl$Y<V2;s@TtO|>a{8*OTgo2i2@qXi{c#jI;my_%>Z*8nIEOkx=Soc)*1^(nTh*pdTj|jE3!yoA(Dm<S^XH59pZNv_QZ}e;yekNDK;u5ox`GR_g3-fKABO{v<&iGPVWvzD7GQUjnW}TgP6l(meE`uczKQIBG6d#w2dw-y=U)BLq$EmCn#-ML1{!pk6Xo2FINR|JhIeMD7_EP(6E_{d(%sBEfLJ(nS(-3!mgo}bC=#{d@oI&6(03_VJ)(sr<o_;8ox`#%zRke7qA!6p$@wW4s03C5m>Lg*usmD8Rcx`AVO8riMtz@jGI*vEJFqomcfV$-8p46?P%%I#5k$yCg{}W-NemMfVD0MBLwvfl7M&I#41(}v+td$j>9p1EK9AGWQr?NM*Vhj%OjCN7s=rWEE8Q?8@&qsPfdrPW;QSYaF?^OaKkh47;)nyDx(Y%a90kWEtv=xC;<?L>s^hCI)Z3NIlyQ(>yV!+@6X!N&!<Rc3A>Wc6WjZWHh!tSGvYbenmekp2oW>ZM{c*x;sJwFE2%VoPVFUHDS12#V2wPcRUE!>Lq&>xt+|34MwxDnkrs{88IAF-0Iw>%sMW4BN$}fKvJ<j3NxqiMB^NJDhrFkWdo5y-GMT~^T5)0&JqBVzf|880FViiFzIxnaN2v@*v3vpX?(j*e-90ZRVY+LAp_5%TAxfd=J6gFw9Fjg;y`6eR94$IXzyxUIFsAtCS1U5m@iyLKjC^Qelrdams~e>bnW8>g<U1TK!ql6%r#P#(*c^Xd?*Gm>YrcS4$Y!f5sP(h{PZvUXK`GhG?pXr40S{}hqJ3JAXx95pmRRewR7ADkp;!GvYZel^Yc(BE;I>!~I+C>VhDLr;0M<=8^amJTqNku&BRK7)jR!4S;}s3$6!8v!nsl5^FDD4<Qd8|Mio`mw<463p+7^v!C)>*Bq|+6bC}~?Tt_>FCGt$_&)?Te7@+YK)HO}2?H52D9;Fsd5VtgW^vabM&Ei^iQv_k}xES+HcYP34o69S~jB5g^Mfl3Ih^@;OugA~x9%on`(2A3~UcVAv7*abv6wQVc@>z$zZRrLyx5ze5X!N7Ml@i(1pr`3|uq!)b0O8{5d`pXobF7z_w+W$b9zOi~d<8&=+TsuirhNw-k`#&fcCcxloR{EXRf?o6n;^rY@eTui-W!4_4Dv5hFgzXj*D!TUx`W{UTAgX6v+DPuW63f*cmdeD7E+aqqXAnc=+r^dQecW7tkoLebK^`7!h!XkgV%EggLZ&)+4!>cvug|gX(y-iB5W+4jPgn52USM2aux@X!3i+|iC08$AlV!thH~{lFw=Et|gX<{K@r2ldX*YmBDXDwdOUo%h%YYA&TDAWbnI4}*y~ig86i{fc$U{lMN>O4hEQ;}<IO^!}W)@W-PNpS!YmTtFtyT>eVByNy=xWrYD5%ZX^Z8&;?9$x=m#*GUl<*FmE#wiIaGo9-g@VQ(Rad$&VPR#NLUfY_-*q&FvvwE)#{-(+Y6*52J}9^Q_6yO*F?{ADSvxm*mpd{p@?ZxI+9&F{t}uZ{b)IRtb)MwcVUnNSYE*{f2uxh2pPlA_(Md_5+Ut~@qUHQSD4SPfQ|_$R>De&glv0q+r2+PL)v_LBxSb3%jSFJDzrthc?-HGrqST9=pJ35JN~3O;N)nlC##7^3QC75DZGd`L?svezSmq#!O;mNY333YYX<Ntb4`@l!P7%)r=%E)xsZ=xo`1R|2iQq7?CD2F!S{-B(Ty*#Gb@W83JO_Zb8uv15&MqxXg77+IA36f7e42$I{U=jie#d<lSkBqSSL8|1RO;519tqi&rc#QFR~RqfvTZ`783yj>te8Qn4XX7A=_aD^3U)N|U9bD)bw#U!N?Unhk{t%(XscK9yx_`=Rh%f{UWuzjaICAGdBJbxXp+2QT3M2Z^Z71#bo|A#h(IHa!ncZ2+I@>>&Lc-veUm{OCHEX0qwc=WQHAkfOaGg?+Fe+GWPQ6Z%aJ*A{04Fva3IrvVEp8Z0#`ych%<K7L_>|3fx~gutTEfxR%a8yM+{%IM&aE?t$(m)7#7`!{Z_X^<BhPvuLgZzWOqAZBX}ZA=gDf8yk!F2TAL+7AidISrW59Ys;j`8z(WCjO*aaa(ukN}?BO9%6q<@nuqz!MyC__tw1abvo-r+Kk7$@_cfr5getP)9-&aEQ5z4*<x^qkylRBz|v&@9~U&q+%x@_HQuFw_09L(?IrzU3~cs=Dh;oVX{NJVXkoy@AbEtT6~d>Dp$@#wsfCpM@j@jIpOYd{vCRwHZK2V5lH3(Nq9<bre;)4tqI8RFnrOgebXs%W~FI}#)skaUh5lU1XQxyQkZXBsgmK9u5H(X+$0%jwJm<6`GVZBv=sD4vNZv^oBL>Nqaj@MN1*TP|sv-os74Of>3U78Arl@mvmH7iKXmrWS!{S=cegK6(5v@cZ%_HkL1HJ>X<pjZ~%4U5+QJ7pOAoM4qZkQ88~Qv#~@~mZBu8ROE+72#zZJlqj){PpB+U2c`q&B!ZrTlz5ydElr8jA#%4`=%HTYA-p}=>+2czx&;UIca*rU#hoq)s!G?Ak6SX^6mEJ>;H0&MxfT<WaARWA&mp;H*_=VnCqTud(sp+MIx`d8Upj}A1tpBW^s?RB>6yS;2pj=?W?4@brRI|sp)oF|!#H$LOc3zL%9srhz^c8|ARMmVw_A#e!4#$FZ|-ObC>A!23;Ye%JVylo6jRJyO5H#dTSvBp2XZ$YaFlJz(I#w21p&)9^Wf9#a5>(38~?oBW@vb%>ynmcZ<j8#tan$RZ9Fp@AzR~p?oJh_Yoe{pxSG%hG5v!tz)oBT@cKvL?A-~Q$Vp(?Jpx*-P*F&_{<b-bMefBxF4sxw|3D9$L)7_);G<frJ&5R3sAX7by0wu}Jes;=J(cD3_Z-FIyKM#&)X<zc8Y72NkSsf0?%A94k2USOKt9j>k97kQg|VwQ5QL1Y`G}{i^-gw2Q{%)XDoI;vn2Vx~6#k9~v$Vd;p`sw=3VpNl&L?^KrKa}fL!Xmpv{lk^O&8Ic^)^INQy+|`7I1__$K5v7WIH2~FpuJ*Zy%#ZMU;nCQ&j|4DDC$_6|4#(q(eqXmEf1oDRsp9q^ggY1_`!#L+|3KAvD)ZW!qke{?)tG?ve<!V4V{fDm#m6A}H|JRXac!O2Dp2XAsxc+|Mkg$e?X8zHVfF4Ksa?3Ucn}7hYr(9&{p=a`G8v6s00AhzeNzIo_tNYKV+I1#m8fYPZ|!to#(1-fv3MiITjd9icC3nXE}G_b86sZ9q&i*aT|~JZ0I^vNW$xtS*Td_qgY+jqOE7Kr>F>UHWw~|4>6T95zAXP^=X0D8c+bn2-n$^?<9k2F6K!!(EnUvJI+xFN5Q*3StEUh_uKg5QFj#b{>#xZBa}@{AprKLg+%D%Fje?h8!5+NG4W#8AmB$Ll2M9ug&mg-HpxLMG=*T@U_z|6XJ^cS_GBNJpMI|kcKYEF~}Y8LD=Mn?OZ5f1fQ?2*esdh<8h~n@dj1umg%AD$^f~A4pE1I2;*c-BwCwZZ<;L0D(W0y5g})b7tyK;tW<V>Gx-RybT7}gaxbmh8k04rlArjgjYQ#&sz7fA{)gR5(eV+8e(g<`0pKUVv3Z?BKoN?L(#&0zX-%k?c3^|cUqiOxeW1vyGXAMwpy*(VH3K-T>TS^wYFvI-=K$yH546_4ioi&2{4`<#SPsu|Wi?R*?L~<qkK{bm?$JT@1T2pNRm#R(BK!uQvUL%34~d!#pe5cB^Pwh~Vh$}#j+Ch;o`5qd4Y`xLOvgj%7y%8be=a;#WyPL?Q^5&(7Dc3hD9@FOWIY#s?9=ScZyc4hape^&Y2!{#TJE97du!m`rn@i;=sGJH$yM8WKa?F(jZ>rw=aXVuQT0n%FPZOHXgj084e1)o2Jx%)at1yA$XTbnHp+^~Dc2n<+jai?T2efVDNTi%!U)vWqTVEu&N39h+m3=-*HxYIGzzB<`kt(5GaikNWortND^VeG=7W@oX(a`E#XPzrzD~1drw*MntP)H?&CO0M4zIG4EIxT%qNl~0zDTrav2I&A4x2<lAha&5XjmiFDd;G#o=8X_*#U<|g(?W|62C+xwD~Iu^<Gx2Kq5@<MP4X?s6nBoWfKNXX*{%@R|n%`uo7T($kPgoWHst9g_Cp@(Vliga0hGneZ1hA_H`o^F7Qiw@8LBoH4S(qm=YL;209U)$$140Z)25izxFmoPq#4*3fPEf8-d*lB=uDv*Ldpn(H1jO)w;C`Bf0~#EZja(0^H|HfX}k3wtP3Y$o?)Vi*tHauT-?t?g~t&I}XWib8$<!$%`<wyQ8B9-F_YJ$M0HwFN+zbhBrdDpZCY(!_yJc1NwX`dW9-Maerk&J|+|=Y4o`dPiaVIWeG(<&IbAvi3}i{T$yj8RJkuhbI0rRuoL4Z(r}0>gDAV`qLdU@4b-UuU@}Ie_lbPh=$C+KqS6edDm*3AQNsSLgl04v9{*1jabYW6BYp%S4y9GmUOc|U)0_lRn(zR5|3u$iAMzWmoJ>O$rK;xXW6jYdOA3&AzltMe9VXX>T3w~xHCHxd#}CX=+#n-U+}3m`8R9t_jRx-M+gXcjPZ4U0nw2fAHp@~`=L}ZxEu|N=Rf%MGcZ_p4dQMto4@eX=NH{tw#B;TIR}wOCQmwsUJAApXX+WZ?glUE#vAm3gkdb7`lrmJib?+41-QG$pJOXvHf_1v{6Z6*+jm)vpqh40k<{4*EF>A1Gmj3#ZlK6^d<-@E3WYUVbEL*qHQ?PwH=cHrLQcpHsJI?c<RvS?7&@@jPi**#EcRN%6Q}e)dyI}p5b*<C%F6;;`%K>ONp0uE#&9*fU91aD*_OPyMTUv-4{2u^zpb-%_h+r{1%W#;1C7(avybfyLG9r;_`{#%ZTuWZ2$s<q`rSGs_nvNy^$iTAz;JsB-55K2w>RQWZuCoyf1I$I#wd$H2dcJB~cGkuuE4ec4uhN`dZhFd7WYV}Ad$VKL!$k6Ozlw@3=9_hAx490#hXov+eSos#fO!oZ*ei8%X9c#@ajCE=lUQ;?TX(JonJ<pi2)svQKU+_CU<ZQ`MIyfPRGX;VIbU0MRxV4r6mSeNrL9$#^9;}gn<GorpvF11l!fv3XIlq%ksG^Jq^y(6=?$o*Ejy)&O09EQ9I4cCE}Q$RtKI7g)Y*_L2ac5#j@n*wEuGUvStF_UslOxI6Dw--bK`x{21ye6SsKh+cQa?rx0zLmS{J9QAMYfzV5PI(2N%k|6C{Y_2I#D48OS!WI;ZKeN_9I5W&?b5cbigTvc*^=loIQhNts2Z)l(;A-bnj%8ueME$gX!TB+?<}ur~@KMbuiDYwl9IOg%`E<9m74*r}Yg_yNmF==_rAfN!<dGXA#P7JHCWSzNnXfFO)ys>8wdrS9OOny;^pV6j<kg<iR>x14!Ht3o$gf=~eTD6;*#=0(S9o&~{Huo^4AaG+DU$qS{x^rc)H$?CKzmDjzK3kA@3`ztgn&uJp*La6Pc0g4g=$A4TWFDh!rvUmNp+Lo);K^k06#U%T;=vN*9h*XbD7{qdajTYuQ>q7u==mxt=Lvv+PL(ZX0#@{ScG~lh;TqJ6hg3uhg9qD0MmJb7}KIKT0Qt%O1&|im~%OM~7Q-a<vN*>bI<)LmPH>HVK=Y9s+8_S*zm~m8Hjkk%4K}b6!y_Gq5oe~Q+V9_<moOUs)$k?k<JppTDSJC01h3rg-W0&9c87+?Wrsy=o8Mnq!G&(u1sMPy*MT1Q5lV$P~SD=xkKqD7L6@g_2MdRF>5_8H6Ns0S!#ir;glaTEdS@f*jf6T|#<uwvO+EfO2v={No9x{wjhN7#;B5lE?Es@mE7@fZ%N9_bUv=XzEwO(sj*A3@j`XBXDqM@r2LGQq7lxW5x36ufGU|lA^M3a+4sTDeyd3O&c13jMK{~Pc+Lj$eQ5EZ@9c)q(jD~08K8K+;On0OnfBwHAWgj4CB1mSC&P?!mnVdkPJQm1vHOhc%{n51h9^%OREQrrBp3iT9#F-S(cMWxsseONpcFl#8{p+qkNOaE;)C$HTWwRl-&fu50!AX-s!NR=PS_?q^uL&8cLfr_bF8R1`rQ+HO%-^!gu+(RPnc<TidMu}dj(&yM(5rxkGK{eI9?qYd`w(}_hU}fitb-YZfGO|Xyxwe@WW9Y{!5}8|NW&w|#u}?|mU9wScHR$SRQ6Zo~I4z7r53g~$M1PhsPf(^j7H>fpSK2FZ&tadaW~A91{qhYr;3f$_ju&Lzek!}feVK7oSZQpSVMy);uZ-Tdtai_Qmo<VjdZn!Dl~oP{j4E#6+NJAXsS5!bzL0K1U^J)yi!^W91~{oL-s<(^iH+ZIA<*ACy|$o6>a!_rrF!_wbb|novRlzprD&up+Uefs0d6Wy>0t)Yl+N-4-ItxB-5b<xm3Lg9E^i+hvi<)9n{Z&0')).decode()),
    'bakery_brunch': json.loads(zlib.decompress(base64.b85decode('c-rk<U2j}ha{MoRo(IniNhx`grP)|m*)%9AgN;EL26lr0!REoqTaf=Aik#2e)m7Df?$GwyPa;O-oqImJySlpihyT6$_n&_L``>=P`sW|6zJK%a<JH6B>OX$^ufP8H;|GsF{{5$)|MPGE^Z4@*S6_er%a7mR-@W_%_S4nkYWvOR&Evn<4~rkJzIlJYxjOsd%kO^NY~DTo;<uX*ci&wtUQIsU{r%1U<2T>E|Mty?$N%{F&1Uocmj^%m-{S1$-oO3x=kHH{;rOCITx~ZWKRtc(cX#)nzPWlhef8`?$03*xO6Oqm4PSqL|KZ(_kF)vd^V58sJbw37??pendAm6b`0O!{|MlIc!{mC8`_q?+KOgIxPn-Lvzn(mgJmu}1d`P?Jk-y&m?%+_!1b4<nCi<`)^w{G3?%&{fpFBO~>2am$jRV>}t~Sjd?>^hBM5Z^c*6zX0>1_-S>|=kC;{3)%(j(eWCLD?W^WFR6)loYHe0OJ2ezQkt^F~b2)QX)B=y~~@#=$TJH`vN8AH+b<A06!}GOXFNr$bm$`)1v@;8r>;>iG}sA$K1>Y~FtQ@lTukPwzjx|F@?l8GSQw(=}c#?z`{~zn*#Oy&AE+$FtSB3z=I{xfH?8{Ctp4evoHh&0TzC>#~oJkrzw6^T9*F+mF7OoHB6dhKIbnzx$p(<oR3pL!N&)zv(`1K78@{PX_$ux<c37T3vJN%qiU;JoNqW5?@Wf>UsG5=p4T=eorj`$y_3T3fGe<{P^kq&Gzff{rz8nxd4OPuh_|}By;C{0UxfjPy9FbAL1MO%o_V{X({OQtal;aB}S=a+m!hRw|=yB?vVrLs%Q5+^VA6(T5Hjn#7<N_ixafJfKHD0>Af`hxHX48S3%6;F`BAi6EvthKByDk9j~Q2BEYPCWzrlw-+(7N9#!2-)2r9>KuSJ^=hDFYtzvcOv0(!q*!A9h2*X%E{5nl>!QHXUv^)nd8)Fw<%nq^(M$5Ft4FiL&|G8#LTO&KpW)6*EiYI^FbX!gWjLX{J;XQUVzrhgK>>PTK9wkFpk3Y#<iMj(jYhyfym|gZV=>@!SEetW$Z~=|65F6`Hh-qVYmgQpMV1hlojD=nQO5K4=8RkQB_wC)*vdM>U-u*!-km1G|{O|nX^o$^H#WJ!$uwojS^_j_1S8{eQHCNM|*yApKbN{b{>8q!-*q3d5HtNHJQ%voUQId1I``TVMRZZ^h>rQU?RwR95>oVxHWYT*;33##76+XTsT%Jz8zq2CDOPlZ1OdsXs3aEEmJ1aD(=;WcIbAs*#{Tw>R!yzzGpxqzALr{3m)Lz}BMi@96Px<KG=co3L*z0<Xy&i$W7iLV_&o`I|`l4ybeRqI<bcvY0Iiym&-yIZV@my+U<{w1|&nNCmb9GK{UT_PipLSNMmJ^6(KmCQd;ERL95-xqyuB$aY+}(#Cl6X4)BASGf+jDr*!RJHRMrBe>*d>moV8Xz6O#fQ`)Zj5#Z-3Y><7ta@Y9c-Y2Q;<Rr8ItYe+~%B@h!kdK2f9x+`v!3Tvxat*M0b8;c;XVXR6?u6<-0)NV4{G4?nVdraN(U!I2LEhBgY-$sF~lobiQM*vWlKddOn7q*T?1lK#xmHQ|s3cbmptwWHq<9VPTpBM*VSux;v?HC?pC9pN$95EUjk91E6Oa*Pe!6?-&odw2JEIo)PsnIcuf;Ow7PB`NG)CfKVy-^U4~=}mNN!ssA9gRt(yD;(eIu=fxDm*A6D&g5*Bma7coi6j=9mooUVlO=t93Vu9&vdZ4|bU^ZjF=QBiifenme%Hq9(cAuTNfP(A;c`jm0yvL(hE@0%$CF%2$30Epje4s%L6W)i7@)noDtbHgkdd{KmtZ{5Ss2lKKB)mBUzA_DMt#t8B7}ZX4PhvJ+@)K@i)t<kY4-BgvFhfuDZmZBdP1Ntx$OIk?j;=d6*iNrhhF_J2s=()i%qy`!|!)^f$_)#CnCPZU?tG;&kt87at)_fz;JmXx;g1R^Za_9dj>c=Xo$&)l;u5)+m^XC35_d;1I4<ac+bQQgTT?3*+j{(<;q$+>gdSgZ$U4lYeJ1Zm4sY*L|0!{w#C5RAo+rwk~|dAkfe7ZwM;HP7LXTEXlnO(ObjZq0>)D}#B4`zrZ_*VI6J;*|9*_m2Z<C!fDCu|ytgEDfs%La-H9|6(Y}OP&O=^?V56fT$}6R!MAnoAaz5e0w}C|j1yKp+@5&USEKbe$JScRO3zB*->n05tZHsyZ?zzjos*psk`-~8xOYq7>tpHk1g6kX4`M$A918${Dv`@gxiRsyvhi(FS$QYZyCsBEFTB-jGj7CTDC>+&-gQei_O33aBLkuJ-`fPrXB8gr@YtV7~9ai-e`UDYGtJDR2oxOs|ZzhSB5#gh}8c2A<ket&w0ujvw5f}4W8wFY+o<d$ey%3~F8h7>#XFWPI4S^2e2!RKCbfD4~1B2q=y`9Qrz#{_Q7$q>3xFh>|4z$OPu}%))SD3s!dy;IOm<pRRgle=TD#g}GcwrjPnCMvCW)bwAvWVsZp3lRZ1*wkXQZ9wT0tyO(dd)Ju=D_(^`edrsnUf=UJv&D{OYyBAhKjeYGwcTbBK*(}32sv97Yc^PVC8VDrBMRPlIZUQ0f~qV;D@dJUOaHXDFluSjTbtXt51G8Oqc&BBN<h~wONodt0G}rdyi;&PkmGb-rKYt;z9b}`{7UCz5f^JVAl2_{t`3|+Axok*r`^Jfif)xZ_7HYu{0@OMUf#5qDsHs%eo+N!2*acDwqQ2;n{3{8ERA}BQAidAz--=aIbdi<rpGPxJDJ1-1$;)DN;|hQ{q5btnfB;C`2vH#=Z@G5|dUax5=;>S>C96afm9<{I9i<vQVMYDSc={KZJm>y^3+m(og~r3fJXVn9R?zR0+bXuVwJFOpLYvx|y$kT_C%#P{<3N`f{Is#qD6y1V>Lg7okfI@^A-GL3BZaUnBF{Dy>-K9ue0~{wrff(Lv?339mHCT)++>u+*#sr?z7;pKd0Fd1-;E^jLX<j&r1K{Ft~fG+(et9L70|PolF8wkCXC1<kgU+6YdptUf9+^to8T31kOycW>M}{zGu1!0|b}Jkcdh%ABGX8sF06r`iQQECU$m05;F1A_PaO!$91hF>8&tBh~G#Y^pepHZ%lg9?j`-Uv2nl?NtARC<)Hjac$!3<U3lFj!gIVbN$3Zo=_jTi>QM}VK&;wp_t8pN_D)+P0lS_i%Om+ULPuAi=jyr!jfcVGQrmVDbyHJ!x0p>ShgNPf5plX`zqnqJMMC{oxz1-+MUdUb<$S^x<eCqcsF)2p+96<)%3#AhqP`_S(S&002e5XJpwj0lkxmQXc=TU+tRYGMiCdIm>gcI*-*Dr204~oWwdy~Qg~36ZbP)d^(2cC5q3wBA%cH;{eLOUq>PN*q;yeaU<jUYct*HWTTqFYQh!{U`@2uOza`x?ai7kP;;n>S7}7#7DRRrINp`dKS#O-4)e{g6-9NVfL}sPXB#@vtp`yeqs3l^Gi?ZfjBeGQ45mR`gH9D{Yb3#6<@P!^MUYsLGYp)0}l;AR`lu!6k99`PVnmEUzS`!vrf!!+V;}F|+p8WBwhl9sX<%w>VzuPj-f_-tEF9aMCb95Sc#fPO;)g_mVQC2AufTnl<k~_1nj#B)!g2%Q}=Yp$Bf_DHP!9B#KD?7GMQG4Typ`q}KRu<lYNeEKLtwmaP>yO!(`0c=tJs7cH<znP=xO+tm{OMUpCGeAUz>Jq#<a*NJf)#WF7cqu)Ez0EnTu@jirsf%^5{e~_y=94(g-T<>Yk)}x#FwNCXO9(29R3Ixhj%y{D{U;ZCZ6qDc?O^A`-i*^*;#&nU8@ITOafA7j8hEJZQje|Y9$ZV&;_baa7)D(gh+X9iX%cQ=D1$-bNzDM9hau>b9Dr~XTv3S9deFS84a1^j%LP>4WlTLn!mM!^8i(@MyUj6wNzDDy;2#dkr|CSt3@}1K=z6|iei~zS~BM>nd&OicBuKNVnsO|W;i_*;joiM31T?d8tHy@^q9~IVc{bzQ_`_lRW(*^DO!T0m|@#WX}6DnoRvQ)A3#vpkqd7(BN||W@u1lYNLz<CUKTv#kJmW!%jZBMiiQ!yDPVzn>PIa2V+AG(zSedBE<SFY1v-1@h-}_CqwD$>&ZkxE;_J6EOrAwJTxQ9QIeH2ryxgEs`R?f6dY&NT0<g{*+f6Fc;8p66(Q|lTj+AwIt!pW)xc4wbTNYr^?TH#!BSwv6F-q-PzkUDV&wwu?daT0ftWUfZ3|EDK?T9E&e4Ow2hNQA6EdP9sbAQ2FoeL6BXzE!D0vqxHv(h|B;GUt^o$SB>BcnZ`^)TIN5W|wrTuTfkV>)&EBPnFFKgw8FlTr2r&u%fQIB?B|9I-kuz+jr0O1N0*h|4mWt9gvS^Z5Ii3BvX{9_BAlst(;8WZ;A31n>LfZ{^X=oRkB0I_fZ6L+w%R%{h~~V{PpV042DQtdyw#s$L$S@jlu6DBNijhGXbVaqeQ~v6INOLGju|Zasu?W^p^EKSY!cTlG*x*O3^15O0AQOi_XEobjq{ly%P4K_;Kf2RM{wl)RuVAacpsm1r00h!Z&szAT@U%mIa7a(zd_YAJzn`*LCROoEEnS{7VYa0rR*h-#q!S$S&X?o^x>^PM+8YHTyh6jvaC`R<sJtb8r0UGFoWEaI!S$Px;&J(Uk9e3Ogf6la$blKnuppiyBv>ofo-4ml6M+x-+tF3vlcJOFPHsBM2(oi-ZqP<+ErWs=mAP^qVtJ!Zy#mf(?BHwfi;ynD}coP_OBcLhidG7WVz{rLi#<kJ+~X1)8Y4rHcGCehn2+06IFNdTCbw5b*4Z=9W0<s>C;$HLo1Ixn&``#FFc1#+1L?n`tNo*8Y|g^QcfT0l&mpNvz%&C`7queM9b-q3y$UJpU!!PK}aOxW7O-56Y8rVX0*#|JzZ5uN6$_(h)VTpv=RhTA86)z}%nfDH#l(1|xWFFKjR`niEwqss|i%3=Q`$NaV=0LrJ3b*!&5o+z=x7E2@)#KR9!95hCqQFsItrGVec76P<86M6&ZvaQF@_o@!dhhIrG!;E^PqJ|;COgxxo5Q@oGD+OYnw{E_oqZ|uLW2A@Ffu|az09%w4RdbM(U5;s#$=xAo2wWEx9XZmlb!t+#0wVI#s}5H(UUn-Vub>6}EW6s$D~u!ybbM>8##+ro^ve>^v=+=~emvWIMeWnfn9wVUlyA7S53hG@p&3G@Xya78W*X3w0D!*p`3hOvW-%883?c#)>n|&u7lnRN$-t-ST#fiFj0<&^=S8+9h6}Xs^%%#D@S{565&wy4O_yvkE8LPcLc*LI&7qHbWdF%L1`wbSOdI96G0qQi8Bgssr;pe~9e`td+-ez0c~v0D6nlsY<a7BK0M$z0;d%QQ#u!}s#b!NhtQcg>V8_-7YoFL*;ZlOdYb7m9m)y|irf}2(1^;T0IvQCecf`JJ7|lnOn0V3}CR?~J`wzA_zsO+o@zZ;-xMoS+ORNb|P^#g_5U^Z_HIu9<8O$1l@TIaIg!4l-Ld26OG>B}q<Ojx;h^$^x7RCJo5XW~6&_A;31_W5v8nIfNpcZKXx(K~c*eA(WcZfk?uXc$+1`>B+L5?bOqKy39P>3+2Kjnt6OdE=+Z0O+8G|E`lRf8VH*ve&(*~R3?IYYLq41dv+dnvHzWoMEM1Z0ADw4u}dz^C97Z4C70d~oGh)^BjY95W7jyZV+k#`jgvj~<rNGaR{mISg7)=(q_raO=?`D%GHvlaDQUqtZazx)%sp2HQn(35s3=&+B#zeRUSRm^$m;?rCN&YUhS30n70w!A^&V2sVe;nnktui-<{a$IN2r(01Asm>Jd7L`3{}hd%0)riw777KrxAvl%=Ep&cILHgx6HTQUh2p2bSTnQs4Iib#3EH%<&}G!_+ofF$Chd?3)8F1)r;fHy1<#C2-o%Tb+CMw+N&U)}l3VSr<HEB%$x8UF1FqYz!3st#&ZA|+xdyasEwHpO(ydX>^nhnyGfgJTm3`t%!*IOynKSVZUAIA#^Ua9eoLs<t92W-;n-$m&|@({V7R9#OaST2f&hTjhbO&t7;N<GI1Amvv;K;M1RBgVw&LT|zwWAcjy@v*53#JuL-f88s<eqcqA*gtR18Bl=@tnpIMr;$cppX{20B%m><YgNp0mV}d_z6g0#GEPB#AOgq6Dsir`e`Vcc0j5#mvJSL@Oi+ZJ&aX6VImZynS0BO`6BWo=@&?9O^xNLx=r(#8Iqo4%CUY%)Sup;c!d*jyS$D+hB1OAb-aCl8H7*mMa7?AeTGa3+00D(94SPceYu%4t}$?{wFzBIUMB!!~*DWdP{zB|-cEJ8gCS(aO*EOn_9YYRWL`XlFZ7$qYcmn-TATkmsfB__|32h}P6s(xN(6#UxgIVKjA<E*)^vI&r^lJ4#pj#G04*S&`k(L8+(=<-xmSo>tuV7iA6p_>m@1(*V|H3cH?Ao*VVX_hX{1-Xq#iA&I~3lNlVOITJn7LlowN@WiYdbN_OS2Wg~WE<z&+6^j9(vwoTFsKE-8Z3Gh`k$Wi^IX!Va1S$02y=V%>p|=QGm=7Z4F&)nxUkF#&0WL~&Y470*N3@W*=W`pcRuN#NRG4=S=e@V6q<`E?^rxUb;uw}#M<>Rg)M9+uQh6D(<$-ppygfr-3?|vqs)x9QzkWs@wS0tBbA<3Tw<cYlmSc_X*TUf&o!)8RgAA5N(395g=^ZVgj3bh)Ui1?@<t^WR7L_T=&q45t=o(@BJ->JC^-CSg99~7=>tu+3t2JN%qzX3>dNW#SgQ3A!fEu`uB9mRzrg|a*gQ-?DKD=gPV$Y;bu;=`#0^gIiCB$gH4!rvh!jJ7f5aC?G2B8zSFt#?l$QIgk&kjcAxTT>3L33v{hyV@tc+?I6SDFeR<f2mwvN%t1IoLdqcV~|WpWq9jRup&r{-nqjw+d%Y-r@CIpSXcL=_q~WhG40j-GgE=B;@H;vA<=zmFC9Bx_L)S5h}`(xJc}K4Bg8Hk~Tt8ms%U&WkR^@U~l_Nmv=O^%~u@1he!Vy1XD&O7Q&fv@p^LQDk;7u@UwYKdchOBg<smTs<}v)DH)_7^TTZQXMV1^t_w~G?B?Ql(Qk&RjzGflpr{{?dy`x<n`w5wwXpZWd+F-1K&1LcAF&S6}Hjr3Vg?N5VG5LNE&>*R#<2q4_2VszK+L|vV<at1Pn8~q8`y4@N<lOGr*<ty5gGVS<A_n7ILM*4VQvNDEM0HTdH;In}Be!C{~TAc)BQy7$To=*rZh{dy$95EcjL)RqdWg&||{D0xJSZRZJjXdBY~0AJ0aq5!&@{7|B}Ks8nUh=_2UYN-`oHY|E~8n-%k7Mxj=s+LK7a-Y-D2I73N~XTXWGNL7YQ&kDf7pOlPEQhHN~)s+Nm{uP&KiG~Ak6v{fvE*9u8+$~sTPcvMm5SG^}XqFHCzQTBc5jwT;%7FyFJIqE=abdk|$?MRaCA!)>KTlXEn<C?`-~=x`(+vqNs*G}W1IgN&T0eQAY2<?soZ7)KC>||{`@hn%uVI^Fkih3xDM_V?q>digQYWtq*%z78p^B!o^0Us=T4APE+&r{se;>!k+AxsQS9`yyF;9tG5QpWpp_IF5U9C~3IjgsvqumX>Sd%;^b*?oc-Jq`I{V`M`z(&iNJ3XQT)nnV+R3e^c^=eVn_KShr>$apeLmio8Vm6!eOV-Wf6Lp<wA;#8`cLgX}7Ic`|^4pqnc5<8n5env+&-yv!vQ$(T$v{P?pA4)S#N~OZWDbac<vYxR$UC`|v4`KWk~hm=n%&gNaH`b#sO3^^2WKT*c&+2|C55?_+)v(h-8M3%7IM)GqkDxS45DARCX37}LL;gG?ddP-S~v2Dq9J=BvA%I6Xll8`)+w&EwAM*;qvMs8&#82VQwQ24n+ts-ib>8?WXj_#SHg}(_buOdfJ_L3sF5xReeJ12eMT~D(&^VYMchiH#3qn6-myNs^OSXh;I8D_k!g2BPv8_B6)wUSjdi00^JoY(8Hr(7$Sb?lZ48}u+5FH0XV1h`Rz`uux%$em>?6~c_4;QRn!Tpfj3cD9a`UV3w$5;^Tz840d^D)!CRT24TRy^X{pELESSiP!rlpT%NZ|rt8-mg!;*E_Udm-z@G~=jiM@XPd<$3er?z=)8?{26DqIc#M@ts^dvPu0T@$snd;DQe1imK`+-6rSkdj4Xyc|$FHmmSoloQ`*bV>>N=tfSl@<x5e--F-oY;I>oFEZEo+@%H&-`wDXMt7#kQX_6;MCTd!ySf`3ax8q;bRo@Ehe>kWh!5Qbq?bl`Pfj?Bsoc@4)XfkG3mfa+tD8Z>AtHz)k#Z_ZEWEv>r;ikcQstZU&VqA3PiX!PfCCpyo8p~AInTM_Z?mar3OUJSVNxCX80t0YGQwp_r!yq-)5QCVsXrM&tlw-n6h<@ra&Rr{512!AmHzG#<3t0@l=H@jd{Vd~=gIVluk^7ia)o6)QO*7om8Jm%}1|m-;9IkRI=rg^KeG(clDL!3|`Q(i6@w9`+nP|XD3k!^oA=Axws=+8+!`NsE9V<NqB1+XtZuPje+-C`n$#3&%MSfr&>a+`j%*bXs!pyUd1t!wuT$kK!^G|%UN!I+S^jtd;p&f{Gwb9j&CZ3ly?%L&;R&(%`NIwfN;W?Kmmy>(&I+-<VzOE&si}BZ>-49(0&#JaDC;9o0<Xv*D7a8c@Q^7L2fKe$wg1qLd1C7z!0*<@z(vN?Lk-4>&*CrYxRk}u-ne&T)_Ecbv8&@w`1-ji-FffltHAkaHDRRcritX-#MYq(`a1t_7;eVpB{zatDbOjLcPz$(SlSNc0C>tqGZ0eCw1Xqy;X&FgE0zk#&{{H2X^>v98@7R@;$6`sOE*c^7huN}UMrB!tL}n{d&Y>BCJ33-w`6Z@0Lr_jjPcRJFIjY@Gbzcg&96476luJ%mB28s+&^1S_-%U|9o#aA(Y$JEN$SBNPf#ch}Xi?aW@j#wd>G~z}Af_XzPo)LRph_5nX3dDyBj02so4G!}fS?%TU!W7_REqAudIotgs~iLd*AYFPW7~0+FGhU<c#p$wYP8FvLA|92W@(efVdRQzgT*Z{&R0Gw;FE-yopmpq5)#MiTVfAZMn@)n7NbRRK_g$Ue*K4<SELvj5?yAo;EM8V|4B>;Six6aRknFly0%rq0V|A%VdJWc*a#UfN_-b;DcLEmqfevl5=rno&9zu?l)Oh?J(Qy4ME9%HR#BxL1B13lV3?!PVt5r5nRw9EI6JPO5av(3sAS|ZW8e`CG-T8mtzZ$b$(O49zQ&W;w~>LkT15PG8#=X%vj}1bObp3FD~OI!QfT36zkj184(9VSO@NoJl;YPkNQCT2R<LukmS~uE<M9q_YRQG4>Y_Eb593@!VD;nXQ0Kv*aE-Tn1mKndGuAb@09QnvjhWj%+Wm#y!ObQI=<=$mg?1#{OlGzYJ$GTws^1v0&gk}<4?0EvwXssq9{?RZ=Tg-v@S5Cf>yJw8-Tsz>kB)oU$12Eh0Y=cHhZ%3}j_CjaBW?<FW+o8YAUFp0HtUy2Mb5TX&rA8*w~Se4Xw|_x5A0^n#)^;`MfrHnZBCGFcCy_s0l~#6?1EK&x{rpTuF)nr4X#}D0U52nRt%W^(01-TzKE-hOltkwiV@B_B}$(S`F|(yF4v1Sbgk=(%gVc@#3Y(Br;26I-rdq(B*(-VY?VfJl!73=@UMOJ2{O&!#*zyw9j_=f#U)z8F@kO!YaWS569c_DB+X_%8ilZ~uyqWTugf%zq>bbybg0+F^H>WD!7GWZOSwdyvZVJd3aVLCTEk&!H83k^^jJ}TBemO6bq!e_<-)=#fyWdOn!hH>?+3z2<T8h(whzElLCIO9eu>rq8UD)(7xkM#s*Nn_^Z1n%Bk>jP*80*8bSz$YNqgE5G7k79=j3K2f~<GlZ8p3~q@_G;pV`Z#b3~iITE$$c6lx_J@S?bf2qdxYygq6l>(~4W%?OdWqORq>@m10z+J&<eC?0kFVsT+@+46NSH6C5-ibPCv+P@-b_v|faijPab^)<aUz&(<bg8Z&UtE%u;X?Q1i>!Bb0Dv`C~I=o)-@MVRum|&Bom6bkRZuRRXoD`#4ilYg9qE=H_z}xzm)81<BwwG>2NqdGXa!73@OOjlEY8VXpgfBeN);aklpgZOW($A}VBzwXUQpm|z_<y?i!caLL%<7B4fRbQn^MhQOWln}3Mc_dSxX|k_2eVFAuE!9YryC|mNMaV)rdK*{jqR4r(KM5*hOq+$=0gjcSL$?zju}JjPDbNF8U6<KqP|1)R^r%Ht2o25bY$*IeSqhXHS^|P2~Tbr5$fbQWlgK=c8ktLb91ituTDAuPGGzN*q&WJ^yJkLb$g0g7naiOOf1px3g5fi3Uuq>#?hv*Py-b48TZZW3+b`dNW7{|NLMlas179W+1b_FuoY!>jEoUK>69q%q}NFd{0iY6W`&kag80y>)u)D6s`6A@l<8{s!)WGJShE&tewk#Kn`$K6rPc0oE89}qCB~kiDlgl$1MS`D_S&v+TtsNW|FKTNR<lpMm1Vj3jnQd?-HqX+iXdI=kzi6FBS(}bEkM18vuV=J0fxQg9~u17<yXJwZmeFHNnVk!%Z)G0h@7#BtJfxcb5Y1wBt7kpZ9HpZjcc%zD>nEc#I;4zXYKUR>*X5p_*@<xjv+q4*;n8OObK8~%vbOG%4+$jYtSLN4Y!%Fo4|5KwR+i>#h%Q}biV^ExY>lOZ}Aa_8#{NJz_M~ZBA3lUvH6o$BBqY{nNlU3&gYcwhiu1<^?NmmiB41W>e6Kc8foH68GTlBKo)zI?k~}v)on4<;4(_86Y#}f>p*R!0jnuRVzq?J*LWP~cbljNpNBTiu$ZUY`8536ZBbb-P<AcIj`Gz4t=Bwm&Lqsw*f^8FmMH_f=_)Ic1o~&JxMO-$jHVa%EG$b}DY4pw1R!SZB;li%2AUmVkoF<1SZS;j!I8MOwGhLHKjqDf^69;Ps-6Q=E{(0Q=8Jt(S^o#HXoMea)huV%#dgzdj!LB-<2(b7CX!N>16a4(m6{5bc`bDW61`b}q8F}d6<Ty%(uOXn^L+bTEwFx32CA00Ye*J?S?2`P!;<y#rNwG$%9>0~Va<;jszWZ9VAI+zQ}b`U@YpGt=Fmp!N0FPv5Q*${Uv<kLJOKBF+pY?<i;CdTIZyn}Svs-$seS{SsBD>e`m#EcD!E{i3`+@@8&`E+Y3L)Mf^NDw_BSembDJ_dQb+A#+ZGR!!x{9a0yo-}38NiYrJ@<X3TN!U$~qDV&JtBF;!Qs4!lQ*_)gl}Ue$#-Y-%4X(j3}sx*PEe!(~R*4E(cbHzpd}%P6L?4BZc!CFE#VBsPXd7kd>@B|E5^J7h4PFpZIAq<r%o*hU_}<xQw*E^!i~$K6+#Jc6Iq&Y+qbTW{9RvIQ4E*V%0i*Bh1=uM!sXPt_y$B4l0{w5$$r6L<ck!Ee;*)hf`c9L5lM}T3dv%RhM&T<iI@grpd!&&?Z=y$uH4l7w-wnX`Eg{r5G>q4Dc^Nxsw;JLnd<+_Z%K%o43I7h>Q<ykr1+N(xUkZfm^EDQ6TxK=7_hB7F}zHJ6lQyRd^bN@R`q;l`)Ll7m?M?dXms$@>l*kIV2fbNg-$!6gF@gpc>5Qm)UK+*3^`zWNd9eai*Y4Q=DYRUeA)pP{wLHN5GeRKB_ivY$f`1*Vnf2YsYVJHVEh8C?Zt;gL`T62x57GX1XOBm%W>O?f_!Wn{9B%_6+wm#Win>%ur!FI8H|WBjrOp|GwybWLyNTYG)eC(y|})@X~!&rS&kX0_`j9u|F)bpuV?AK^DzG__j{(viW4n7q(Supc7k1zn?9cqBVJoo0aSC`*zmGnr{`i)U9Y)Sdkv9X9RdoZD)Dqdc{bC^`HQwIsBiJhGZMyAbIu`hlr|2qkX}9zjb(RLlQ9O$i@0u`O9>J0E+JF#s-;IMS<XzVNWC<)|k@W44^5U<p;ViSB@N}V7;|>+`3$idvcLI{6BL>nTr')).decode()),
    'yarn': json.loads(zlib.decompress(base64.b85decode('c-rM%O>Y}nlKd|^^I(#aEbmQibEbvSScW7oF>4Tw26hGmEM^Zqb6f0xUs)oHRh5yEk@+6gw)fO*imrO!FEcVS^2`66{q5J^{_)q}&i?Jo*{AD=hqK+{?C-z+_kaHL>5He2|M>N{|N85{o<4s$`|0yve))8N_u=#V$Fs%R_UFy@(|^x*i!WzC-`sD`CLg~3_F=R6@btq!Z*K2Co-N+azTW@)i^JE~A8-DAef#u>ho3i_PhTIr``^W+aX0V(^!d~H2ginfIooa?9-rU*@$UZd=d<0o>E45mT@WASj=}5=KYhNr{qW1vXg+>^9*@!E_fORtdVBqTGjw?Jn5RE|d>jT>d)yzs4*ayQ*N>a~=YKtW9(l_9YrjkT=aGMX_-$iX$N*RRL<V|T4sqY?_#RsDvQD0#^8C2e@Y)XTAD0{Ehr7@6ERo^0v$cP4ad-=z1M66yBs;!#lHwj61{3xq{^$Gl;@OE-2zYm8Qoh?Qw7CujXnu>0JM=RB#mhms3NG+1x7-CCoj%&$r|4q!o;~lvlHPC9c?(XZVN$0b*hB7aZ#VBBfBD1a{_*Da=0BdNq_t(>q$@Pdt~=9)Z)copO(Qq&ac@=5LS|NE4n=S>zii~uhj8ylV`m>(I_&LZ!h^-0`QRa-^{ovHhYXy#<{=;M?>^Coyu5`!<mJQkq<h%hezo~W9sYV;p<`|x9dm2XC_QXE^nQ4Vuja3M=|0~&#~0f7<Qx#sB+`d)JsZM@$NTH;Pn-MuzkurkbnY-?qoz1xr@Vl7S6L@|i}i=-7rl2I>t<=n>C<lSguhEJrPSRPUEko;w|AYo<-m1SyZ5x~sp2@4=Atr)6|cIB5p+0!M%#OQF3r9!jbY7H2uAVfO=YkN>eL+{RB`W)$5I{<V7Gi`(3E?=08dmbs=SpJ&tA;}N!b*dNdwQf%&pt!4r{Q$&JX5;>Bf5ZZC=F*b4R+S!+r3&K6avEvXh;-w8Xo(aKWJCzt>2`w~_2;GlNFBif8}2Xts<TjMLt~&1>v<{hEt7ch8{*#l2+c>hV)}Dp7M_f7=L;A=hrAG34Hbvmrc^T$p<A#0ztOO(ZVNPB)E%Fucw^x_0l;Z`B+))x|snci-P_r8{|e^Zp;C92tH&gTMB7r#phYnVXS0f|;w4-9DXe>P*b;wZ>{56MI_4*Z2S47`}QAi+x?jlU@%Gb}_Xfq7;tl{<XDeYBad}*NrZPk|#a7>pbW*b*0yU640>m3?CZ_r>7F{ugnOu()#V1`J<Fr0kv*(dxbg`l{l2OXVAG2KZo{l*aQL!wEstN6C|E9zppObOL%XB9PYK}iw&41D|}BY9~>w9vIPrYh)${BmuetFgw_|u8(y~)=vSw3_KRIg0Rh!cF?!FbW~P5HDnLK6V~VpgK9a%l?0#FBrChMU+5_$nz+Hk2rPZ#4b`187xg$g~Ae!mns2@H!9=rV^8k&@qG(2fA5fK!U0arwn#`Yy~<AHa~|8@AOKzoo{KP;E_D2F>V7J*SZWbK~;bvZs4e5Jpk2KK;j!02VjAgellvd~B}b8G6n#n8B@w@e)<*1q%3qZP7&I`*GHZ53jWj9OJ9O*QJLZSV@)#IH#wS#%3xWlgKl%sE;t90K9iRJ#RtG#sq`guW`oEwFL6b?vpH<>uHU++}N`&KQeh!9r2W-2_*~0e#!v-Q9lmQk}lck*(m^Jv=Q-YS=f%TyK7SkP}SZlW2`$cXMfi2oS=?hbA0bHLU&NZw{U*MPDYfv|M?ZkR`p)(3ilcolWVL*RmPnz?+8wMf1td<b1Xkv*w-W@QmR|B-U)&%oy;NC(q==S-hYm8+Z6%4U1^gG0@LCKj3fEK+}0)`4VFN%%vq0VcT=eEiAB$U;{XyIeZ9t2H{x@kWbcQ%4S%Ys7%TQ0=)vK{kSd1a1GCPqT}mlR?K>7XoZvSUKVa{q|r4hV=%||7V;T@ONlU*49Ya!o$CnsHdkxfuAgTiuc9pE6}G2=58`}DOdL1IEah%#$a?`^n6J|XG{f6sO4uMlUuH~TDL;F#aR5S?1m>nuV4RqUO_|6vuf(K}2cYr(GJGxO>VX@#Ja}|{40GeZv3VUhGjn)zC8M7#gz&{~l(ZI8>F?axWpz9j<l{yp<NN4+#cZ-?ob5u#Ss|I+^NSeUEpB8a?y8jj9R(_=Q==~ZI8=~7GuWXQSw)SDpTRUN22x+6fKLhz^yCOK2?)))i${;?n;0tUER8coU)<Yj%Umx1x(iQY|FE~dg{g5Q4I`4kHWwb4gnmcwFKAj{`n=XRk!`wiVB5`n@1qNSleSScQ?Z9lY2OX*CK`6G<T!=5QNo<4^pV&MWs8CwJ$AhSn=>N?<y}hs=T3&*$M|7H8Q^r%jB*o;DYT`((9q2AM}V59z=wHU9#2?;!wO#E%mKIsouB52B@AJ~AhR2Zs*y%q7UrVH<5pCucv!2rI4l$nR$zs53VLMM8ueD1j>E`4ALb@pk1_Ydx7FB{-HDoW^uFu}x{-yHMAQ-O31UhBNRIgs_I1I`&BA`UWHE+O#<=O5ao}lWyw)t?BDxB#MUak!g<jC_;Fo#u)kL7|X+v}>FjgvqBJ6e*#-R^*O7320b`lu1(&5mI#oX2o)~|#XCV)H*(9zFfd&>bZqGBZj)74yZ_7d<dvXqS)4IWx)k)akxFgGp`i0l+-vNuYP0LE@~o!hx>l7U3l%EslxX1YrjaWIrquE>=%+cB5tYFFk+;b<#jjTDy#BToTv44v-41KVm`9YvOj#(Kc+Y!od#QjZ*EQ03^&_(wLxj%j(!H=0|IJ#0m5BD$J)+NLxw1_6Ef<Vm2k=DjXme8N0~5%#n&kEK~z7MN)uHZToj?F^RfUb8OGa@RDdqlu<HliOK#NE)3CQK~QJW?ZP4@r65rA_-ddLY6e|aV;iIP&n5I<iUZ@{#_@pCV=W?pua|%uA=+YHNy8uN2e$QB_|9VaL-oUMu4QSbu{h_W%E_AU0`jKg&#(ahr^cag5l`g7swEhg<&-f&(HYT3o++EY#8uXM4nQ5`9XYm<FAOK;Jq=}7;lu?-&JWY#jiiM<-^S%9k*W1tZ4H3Lk<O4mcx>DbCUfGpm0UXumL`D^W+{;5mjHElujEw9fY?ST0s|U5u^Z5k6Z<I)^{TDk%8es8PlMI!$@|r9IuHMB-}UfrmToElE9)(dW#n4(eGeCY~1bkZP7B^Y7V>tn0U=(Vq74cMA=&|v{wu99xWNm<#JO|))@G!w20z5UJf))UytTDGfo!jiLe(SnTY&9&~8GWYjChzg!(!<*gyeWj>##3y7A9U(g(BM7{zVBkC!V)H|d=VzntTecjsOu3zkDig5TLxYMT61Q2M6Wvi5%IQ;($V00>t`&HJVYX^44iod43R3PKSNaF>#p%bi+rY`zXI5Krj#mST@3MmR(+Ffcq+8L$eWDzdu4dXvK$DZ3K1&Dsu~7Fi~3iIIzBQ<0v;*r~0AzR5}p{QQldO3^M{6wVq7{S&7Gn7I{}pX@zpt#XMB$*iS~qZ~!5fdsx6?^aH<4N1==usANl6>X@voSX0I`7x_CJ~%Rpb2@)QmS9wc%b12NXrW%A(}pn84Ix@Iz(*_9YzfeW@PY*~YhV4pK{6hs3es$-;f2=qcB{9h!stvi&n>YGX#}YJn^TFdU6p>mT3~!!_QJt<r`vb&dcLy|qb+*UYuA(ZHHdML)wtJcme>oCSS#+3bb4WZFP6|uf?O0=sXM{^vMfo;LWwKU;k73K$?_m!^Zr(&<_Wh3vzRv`(1gVW*CfkO&M*)DRw_S~b4F04nTKmnwwzF0N0U0x2`eOJDhfMD(}SFV3KqbyIm+g!Rb?arV@sis7fO=@tsXg~VwIE!*FyzZ2=&p`(+0kg7*QBX<1^@=ojGgPE+%>^vq@_!g%ho+^0q5f0fQsX2*I(|bPs1Y6Sf8oiEqGsaWm?O19u3lvMG35@yIw-VT0G!IRpL@lSsyl=4c*~O1MA_X3CN$VL8Wo59fG*Pt@?%$}M9S?}`k=?;ExC)!EKtl{=C3d<e<j-2Q2=H!@q%i{#q5Ot_o?W@7{*-Eb7$Nfc)Q=e9JI&7#&!+pjVPddw<N0R;Nn6~%H|>Q05;TP07Vnr<?C%r`Q+t_<o3mdXwmG&ewClMF*;b+Y9^tLG$TE69OVWlwXDu2V=-$Y@FHyEHrht~|*?t)?f{av(uSn7J~^UcHFO<b-p0ctV1ri|GnDQx)Xf%@%(R2S5t)C<3X65M_yXn${{q2YOOJyRbV}aR=Zst(By=fw)k>My`kk<$Nbp3Balv*c7bs$rCEIkVBZsEJl&4v@apJI&K9g*f6B2spiNo6FUE?w$$s4U*x15FHX*QMO6TlnB0ZyGO?SXf1EDmfnH{#m`Y7Y8jjTJ6T!h)7Y%P7cod_0{f>Md-_t@doJHEi+6Q60Oj)G%+_aQoTyo=Hqv)u%30li4=mpi;0;8$HEGSSjI_wG~%F#--tRg7TzNDn)j=<(d&NQ+_=>n>$Ik)hpwFTr8;p!#d34Xxoaj?#iGG+OIQX!Vi{zk5|q7IQxoMvB<Gq+--M(dI3^-v`putTSTBV`q6HEwea0_-;-@to5005uyLt7uKx25N;@;q<=UDFvwK)&7_c2N<n52QgEdjF)F~v6oEj)V6a%7Z8TKhZSn$Yrt2}lR4Rt9|A*RVOt@Txz?sWTR4~kPC<oS)WTr{4qYlFr<UsrU+84c-;q!YUGq5WAqZ=(<5(v_P^~tfan<2p&dI+adt#mT=Fh{@6}7sPT9PH9ziCX~JP@<w_4Xp4tF3*KtctZtr^be6yR;Q<4v}{r1f%hmX>Ssv2RYDSF$tVrQU;B-z1_WrMGvCkjx$HOo>nFJ>Pu}RWeTRq9%sN7HV$5R2g7Q_9Rb!K0ZtMjLT-)Z_mo>BI-$<y=__H~x%Sm8WaKR){DWw@&en@V?@V3@c8LVJz4Tafw`RlIA+0vH24iGUeHjF(<O21vZMDSnYi~G>+$^P0=EG}ttAa~KrhQ=g^K_Z?&4vIce&%wa`6Gl+(?Tmx=;JelC?@N*QWa<zohwlmM2PYV_#jY7LknCytY1Qd<-LsQoKl%4DM6lU`ry-*@nk4FW{GLUP-vCv$wkzjtDUYu%X0uZb6Z#7AnBJHr+d=BRb5on5<1|V*gwG?Fv#_deC11t=k%@N96d$1)*Rj7Rs{t-*1__hC|SRencwRG#8@uPqb^HX$kuojZwgYZ!3TG`<s<VfzfB|*_L|~cksZZdx5n}kFpmlvet~yDvR;2riUT|YW0%n-nfGHnfUkh;g!yI~%*BpaF}L2D1fvguEgu34owK0{4~NNs6WiXiy?WHA6>fIb`5ybc6d|j!P1D6>$cECw@(NML1Uoef2q~@3HW_ET5iBN*kz!0kq>V(S6hh=VRe6mT4JqjEaVUd>A7cHcOu_=Z<S3L&op6YI)R2O5$pGK<;y!vMDcsLS3xuJ3=+kE+rEXnFce2fd0{!grn6Hh{oHv0)tY{Okp|(s|fQ%-9r;P(K4{J2s$QV%_26=i80n7lT;DFq3IsL_if`bg(^GpJQM?`>`z|>|Z^XJc+j$PSK0Dg!~!`JN+i#5b7mUTS%?6&7A?>rkDZ6QeIa>sstE1xn;{+ohPDp~L{1W-!{ymYXUD~A$tY0iO_1D>=c&#Ps)N|-}Er9O*<bQJwj((I*@Wx2sRLGHaq<4p`5Q7Q*lV!E_4O^j(I+Gik_Ef33YPXG;2#uFHn&_t<JHHr!_AtwZx&G_$%=bYFC)HR|Sa{k#;Tl&!&Ytg0f@QT`QVB&-tv7JE^J#{P+#nGvsD2|ydZox{M>rk_-vCT3OYz;&ucubw&TJp7AIzXw0m6Xi!MKG|B$8;PSIB_yrj8HzrwwNjSC&o_E5MX;P+95f2Yi#?T?-J7eRuoQ3Uj{|KNWQ?-L)R0iSsidd4I!EO@dAtm*VZ{X1c;3=Wdp0=;J7xr=g-tEK<0$c;y28LCT;W|qHb3#ZzG}$`9z3I$LsYN1b}QX&5W3VHvJ{cv#kDV@=*^}b0^@^Cx@d&>73^4M`X>8N_w0~5YPj}l0y{-ObES(W(1E4@vbSRa=uy_C-!rcB5yJ)U;tf^kw;7Xw!Rtoph7O^FA$bvPy8vY$z|7~hb&+aL&sO7LT1!E+^RqZugYH1*@*^{pPMx7?<W+rN(xF^j@}#-MT_*66CE}|sFcNaDGi`wLO`aJG(S7RDF8=4<v+Mp){?a>q-9WI0!4@e6F;S(xOHAdTCCvQKs-WH%%!EY5_+;apBrOK^f+R<`H5J=G^~0R=?>{4tHj9$wW=74-pK|)ys33u8Gs+-u?D)uZ4%DyI#nycg?3;=iF|{aqhQ1EZ)16hK)Db4#9YEo6Y_vobW#$1_5ULh9|(U4C`4MG!Oxu_d;BeB<=C_cLCc{Xy4Wh^I=GXXAw4)F-5&oZwO<yLFiVN*ClTJatwL(dDNV<du>>{_%V<e_9BezX|Ldf)fo2}aTkDzjaV|LQM-5nL1!&lc4mwgs>bSW<T~Cr=AypQTglsYx9y%>}W_W1M7WU>g@1t6Xhi4?%^E&E?wp3_o1>1~rER#A8L7se5-NpduQ*v&CBeNw|O;v6-^!==eL*dNG?7FDL+sJ)8&m`MuD)mIR!y)RnR4_698qtGUU+6I&XuU+HA&ZIwT)~L&Sgn%qtfz$xsuHWnmP*<*E2idw2fRt~gKT9jahHWZ(C$stv1%>P!bGEj^rP@#Dv(mpDPs`@sl<gNS7a~Y7%T;Q4>mMVfdpe63Kr3WzDW*f9b$|iB;|94B7#t%P$bNQ0*I3;T4Nh6)#CWZv6*ze3v&|)C_q>vBZ(v|1y0F%hDEmG0u>_|he=bsNwB?~^F=CD82_k9`E|z{ID0v)g-Xrz&@T24MMBw#s3WZraT5HjvcF>;z$^n?mZ$KHI}uouR3R#>mlNXca*aLv&?4+okpq};WUU75h;4(>MAcHO3w5TcPjU%b8AWMfv`AvWH}+fjL_#veLd?F{LakI!PNj2-1uNL8fF4OYM^N>H_^|k><ni%Le!hHgHXr}~f>bnfDoO*}4RzOqDOFh?%^8@$E7IM%yo_*Z#WG8P*JBd13`H{i)h<;tBvS3tD(&D?LAv{499$?M!s$=ZHl-RUr7BchXP;ER5)?!NeaebOMI*zg9)g)m#`(y}BXOO0d_36#8-76@BCaH)9)%J4MC~GQ?6^$%bu6f{tPOvA)st_yGRWirl52y+1%QJBf`kn+9_34%wsQDpe{{UV!(!2h%M(=lh;rP0Tq0Vmr!E8%DWvn%p2TrlEDIvlTMYTU9m|8jv==;LX|{2*prgGY1y)6%G!WGd$y}+b%^FJ*ZsH0H%vA(~pNn3RVj`eO7}Y!(5vFhcSX<1o3fAWK?xUm#>`<9}pH`WQ&@ic$0+nSgbQKjIU37oeBatCGfWeT1r54v-?Xqyd<s<9Gh>X4%kjzBx7!VB%7y>vkH#DwNa|!@O+MZlRqgTyTrey?Q%q@LtpLdaz0G3duun5;{mKkz!KgflXX)jH@)zV(o*x^#h-V5~;#M&ebkwC<%M6$i-*;4F<K!;kbv5ivbggIXAI|D40V`WapfOW_fwo5Z1%6LUpbUhivi>pXV!aA{aBW;{%PDV|Y1PpArza(4D!d6~Us~rAopBt!3GE0o4q~%Qe?=MT}qEOy-9i1deL5}f0eTNLlMVJn>c23ueN<NRx4;JMxo0PLK1p{Qkq2ER9<6_~{ynJFEhDk+*gX$z8`yiLE-c~TSV5}q(Xt#aYDjNNR5>eDBbxqs`#QW`@4Gf2q*A@XQF3USkpkXEH8mx6sg==a67tLk~)jI9)iG`E<>w<v6NmXZ|bp1A(yD!VhiqtgMG;L<LkBW9%QEXzFWyXyZ@^CzLRav(>Y^<hY2w3yDQ0O~_i8@!iO6AY33L8i=ccK?}5&LX1)T<!?99c>io$=)6m-Q&O){k(xryc6mP8YBNFaR1vyq1AHNY&?8a=1XHRpkFLyhY2rfFz@8)v#FhHNt^rLK?*+A<-RYa-vpz^t;Od5!E>ud7@pPV^vV@Shql&%Qbi2N4Ogl=vZUc#Z@Ow4%yX9B>UABHpI$PuP&&;GFO|%s+V*IwZVK5jW++C#ikNz_fZydle%WqjA#||*lN$}0xUpHqNlnlO0DJqC(~*>M5)KwxeAR3sE4it^C6mdN3%ploJZ1Uw=gv(hfU#fn)+g?1dtY|+J-TDfJ&UsPmAkn$xOwH92OMO6%CYPo~_a+lwuJowl?w4fdelHPlc6ZBXyI|S#O4uoCN=ryh&UOmGnu7xUvWcFM!HLqMB2^pbbj-VC3pkxg8go`W>qDk%+ls+mW;Osk$s7Yw%eF0=Ho;a!P=&GBikr40qw_@K$RufA2*<eE&Nv2O{L2P_MA+wZBzrevG2*N}|N-O~Pk)WE*(;0571Kk35Q=yds@(%$3@6vg0&=O4TY7`lTERN>PO_>OeFvjB!R%kYWHKrx(yBBuanB(5t7Jp$Gb-iZW<gp8s2{qZmkHn3>l~hlJS`r>QI|v9R&DvW}jDF~F=Uj!8s_1+4FJ3ZyQI+~n+WlHXE-P@w<GOFvNJ4JA#qtanYEkBXL3)-%fzYT_e=j<%S_B$DGB8AbYP4#jID7nxDEd+3SKC|?+d6cXQfcD%kVw?40nV68!JzTJn12E|8DRd2$=IfR2FoexZZNQuMGIT07RRK0M$AZU`pr{Irbbp|bC;-n;y=x_)$I9c6_VyPuq&xdRfX6iBxJiUBLA^*eXxN6sFay%n$6VdAOj`biiPthH0!Yf1;ulx!v)JqgQBL?H}L!j_s85!8(kR~RD|NJOKj-VEf6q_R%6n;jNmlk1FFjgM>qHm3qKtjK7HFBAaQ4%CMH5DT${w3vkbaC_8@?JU?f?T|{sagpL5WtjSCHhljJv1;fLZXIBENHA6T;37T7HVgTa3KjU??z@ip}ZiYd`xLH$m6d{p){peaKwmVF~o6iMKof~7C}5FtB9PcA;75X86>OIroir-q}wQ^<Mr4X#H(lGjTFCX;)$Sb7s2wHEa$eRMowZIXw?zR*%eEx*uIKA>uE)n%czbMJgRL?O)Y`NORXpd#huEbc#qLL5IRa3$<sJ*e-+h*CVSuJxsy7({d`P%@!2-b?USbAI`^&$+j{HnMjdNNNC|fw6F(SMBj;>@L&A2A@`{YNxckwR54I^4%e5}+sEY7TPv8A8udz!{IT%md=Kk(c6VahKqFr5#qm<<^Xn;^wC&8DpSn4V{ipp4DsxNaRBHd?-#h2WPD5zDfVBkk-7}2_`-Wh%oMaB2m=zd#8vWvayZGhKOOP>orf~RqAI4s7qs|uu1Q7}@OW2>=`Bht%OAxD+mQJ)P(inAOhp)Umk0Ei^|2v@V`V$N21b7f&W^>jglp**w*b!YR?PAUp?0>CUETBKIl+@7G4NXWua*$QSj%OJB17cg8Rbca*kxo}`e!f)U>4oc|K!n(+H6HbaOz^2H2S_0fgNQ}?{wi#<gC}QmmjL_=-Y9{n*){kile$jI}-gYcSUxGK4ZvcQ3Z7iY@F+79Py#xCV(jf+)SKn1Ycfr&=wY#1rb%bX#XfT7mbU_PNM>G%^V0sNm^I-}qBm^7Ig&YgcJz%;Q;8z-H;m51dvCY#IG?+t#z}`_ERv!;J)(>UXLRYN?Iw<c5BE30wfChTx%X7d?zGVH8O!Q1D$pOUlS;jmgCl|OMx-ON==M{MD)X?itgsB~L;e_i7J+`2Wu4!vi%S2xb%-tv6GSvp)rQ`~JaUfp8U_fg=`_$VmTSkWfRniSY7jhe@TWyR~Pg2zRl2WD=#Fx^nfHPV;T9b8{)B9;tsAsJMzd*t>wY6$`5Tv>VFSMj?ph$eTV|5E~xa964Du2sp>rJIC7=evxQcCQ*d|lAOishsj$wSv94itq-A;%(!=GYpNRJzik&if1?v7n@7Nw3S|32a}Al_tsTNjHjC27&>a=y-<8pyG73(OhU?)&u0w2!lKZmswI3Q(=WkLOn}`F8!lcoX|-Y3He}|b}>Q|d^XNF*~jj%DGej5r_985xaLn)Au^va$N3X#sY;P&(Jzl8pndR41!_3GwLS#^M3j`mtyCPWhuM4@u)*i26pd=iIf_Ly#Cb0l)dsr-1m}Vl1wpco8AwEif}T#TIRbKwI4*diZs36PP|d!GR3(D=aAL(4vZl1sJQ@+dmscF|?_mm@o(|`St@=lW?e@{UOiGGwDs~a%4~iOuFzTV~6jt;?&bz23U=+E7ye79UDIU}t-}H)Q6u1TihVnd7Vn$BHC#LYn!a*0Rt~QMzhzX4DhAc8Ew5SH71Qzlym>WvFS|6l}VF?(`07$Uja)3c(zy&!(ASzx0h6*VmIjgkIvME-VLSl&Li6+r2LMB-{?(ZpZ0-fMmQb`B^0N&r}5$DkpvL~75&1bXGS(i-v159JNOG)I5rlQNTXFI~ew#(DaOpz>`u9uLT8QX2zNpLNo6_;_GzSa4PYCT4RK8=&Ku5X`G(F0m8BNixc>49vWDe`zF@4MXeN(Ke<ZVCD8RPE(1PtY=Lg>+sI8O2&sq~bLegQ`QsATS|O_5?#qJ$Mle<4q1-pd4rw-#+4OH)wlO=$T>eER^E3OFlKl1Qzls)h?Dv&OA~%A*V1_piRKdVh)#&POAIz#b8;fI~8aR_;LyaW=Sova%;cC0p2f4)MBersDGeo6vjsKXz7+>{?azo+LjNnwTIOH)mz{@EM>^x-BTZS{|6BQA_)')).decode())
}
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

class _V19Proxy:
    _market_price = staticmethod(_market_price)
_V19_PROXY = _V19Proxy()
_V19_CORE = _CORE_AGENT
_V19_STATE = {0: {"last": -1, "route": None}, 1: {"last": -1, "route": None}}
_V19_ROUTER_STEP = 72
_V19_SUFFIX_STEP = 360
__version__ = "v19-hierarchical-moe-step360-rc1"

del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V19_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, route=None)
    state["last"] = step
    if state.get("route") is None and step >= _V19_ROUTER_STEP:
        town = _get(obs, "town", {}) or {}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    if state.get("route") == "default" and step >= _V19_SUFFIX_STEP:
        state["route"] = "bakery_brunch"
    _ACTIONS = _V19_ROUTES[str(state.get("route") or "default")]
    action = _V19_CORE(obs)
    action = _cap_fixed_purchases(obs, action, _V19_PROXY)
    return _fail_closed_units(obs, action)


# --- V20 product-level sell controller: shift 25% past same-step town demand ---
_V20_PARENT_AGENT = agent
_V20_DELAY_FRACTION = 0.25
_V20_DELAY_START = 360
_V20_DELAY_STOP = 672
_V20_SHED_GUARD = 80
_V20_STATE = {
    0: {"last": -1, "due_step": -1, "due": {}},
    1: {"last": -1, "due_step": -1, "due": {}},
}
__version__ = "v20-demand-timing-hierarchical-moe-rc1"


def _v20_town_demand(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 != 0:
        return demand
    town = _get(obs, "town", {}) or {}
    for shop in list(_get(town, "unlocked_shops", []) or []):
        products = _SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += 2 if len(products) == 1 else 1
    return demand


def _v20_delay_sales(obs, action, step):
    seat = _seat(obs)
    state = _V20_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, due_step=-1, due={})
    state["last"] = step
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    due_step = int(state.get("due_step", -1))
    due = {str(item): max(0, int(quantity or 0)) for item, quantity in dict(state.get("due") or {}).items()}
    if due and due_step <= step:
        for item, quantity in due.items():
            if quantity <= 0:
                continue
            existing = next((order for order in market if _is_sell(order) and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = max(0, int(existing[2] or 0)) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
            else:
                state["due_step"] = step + 1
                action["market"] = market[:10]
                return action
        state["due_step"] = -1
        state["due"] = {}

    can_delay = (
        _V20_DELAY_START <= step < _V20_DELAY_STOP
        and not due
        and market
        and all(_is_sell(order) for order in market)
    )
    if can_delay:
        private = _get(obs, "private", {}) or {}
        shed = dict(_get(private, "shed", {}) or {})
        shed_total = sum(max(0, int(value or 0)) for value in shed.values())
        next_market = list((_ACTIONS[step + 1] or {}).get("market") or []) if step + 1 < len(_ACTIONS) else []
        delayed = {}
        if shed_total < _V20_SHED_GUARD:
            for order in market:
                item = str(order[1])
                quantity = max(0, int(order[2] or 0))
                next_has_room = len(next_market) < 10 or any(_is_sell(future) and str(future[1]) == item for future in next_market)
                if quantity <= 0 or _v20_town_demand(obs, item, step) <= 0 or not next_has_room:
                    continue
                shift = min(quantity, max(1, int(round(quantity * _V20_DELAY_FRACTION))))
                order[2] = quantity - shift
                delayed[item] = delayed.get(item, 0) + shift
        if delayed:
            market = [order for order in market if max(0, int(order[2] or 0)) > 0]
            state["due_step"] = step + 1
            state["due"] = delayed
    action["market"] = market[:10]
    return _rank_sell_slots(obs, action, None)


del agent
def agent(obs, configuration=None):
    action = _V20_PARENT_AGENT(obs, configuration)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    return _v20_delay_sales(obs, action, step)


# --- V21 top-meta MoE: causal late production expert behind the V20 router ---
_V21_LUCASKNA_ROUTE = json.loads(zlib.decompress(base64.b85decode('c-rk<O^+K_lKd}y=Al_d_Q&32iL(|)b{nnM5VHbd7}!}Xu$Vn~_qLe-zHK!>ij|R(k@+6mvd1S8C3f+Bzs$(U$j|?G^&da|{P(~8eDyD%uYP#*@#EEQarK`+{rA8B&+~)lkAMH^=l}ZK|2}{IeD%$zzyA2c<HNg8Z=bFfSKDtlZ=U~M?G~S}zJ33=xjOss%XdF+Ht(Ll_}%8i!}nK<+u7s&->(mk-+cf6yEh-6|KsDgo6QgO#ikLryWKw)XB~O}_RpVwID6T#Q=hN4n~zUlUiSUN<I}faKJ9yc_%Q9b_v+IClwa+R>FhVZ`Skw7yC0wb{^`?~VVL~j>32$<`S9lL<~U4eFMj^7@1Ks-SN(xM{W96-BlPBJ^Z4?|<`<6d-TxGM@!L24NSuDcj1GC@;k(_(fXtpW7%yw8HjBsgIQb=gknQXpn)$L)PpwN0h@Cq-4yPYD4f)51Px(3A|50@a$mH26JN;IdEyzaY_yh5vfIZl>D(v*x=7Euj8+!O7I0U6P?mLQ?Lw@0c2KHG5tw%&W62&tjJbRQQV)G_F(sN5>+PMAt>vd@h7xEh0F3Vjo80W9H#tbr-ym!yLu#D`E%0@mdh4T;WB@Z7yY~DWo_@~X|)B6wa|Lw~pwYChL<AtW#wTY~yuVkERO(RCj<gW0J=c3_e4&~fsalUJh=R?ET*;ke>8~d7<)~7BQ@DkAa)`o>c2F_*kl6Q{}KhT%#4{rJr<kfuKeE7wan{@b>;|d*fV|2`oo{fKgdkcs7F#oBS?(?lPxA*IgVQ9;RLpaWc@Z;0to9#E7$H%{d>jHG{c&E><c{_H>5Ag0P>qKwyB`$jJHr9>j%sDOI-t%|YE~V7n7G2-q)VFt?y5+!iRlE1J>uLX~@oK-&Ack$blo50|fF|2}dM?c#m&UMWDg>i=a;yy0Q*|mc*aExi9aN-v%V!2nx#wfsR4~%o=MOY2oV}U_lCmi@lLnq|nOnCP!d$k%RxW%#?!L~eIAQKc*K`b|zN(L%XqfC|CoV1VE-qX!==kq7Qt@ph``OH(5w7CdUl+}miGy+3`?q<GovvSV5$EnX^rE<z49cBDu2pkj22|FrUDg=)0A8p!47sY|1PXm2cdR}j;vKucSuW-dI@rVO+_2+UY7SiLVm^lK-#%=mJNfv_`#(rIGW>D||J&c4?g;W`Zbs$^X0Aqd`*gag=dq-(VXWrCwdYm*=J79jL!k%#C7AZhGCu3|@x?Btc8n;6W4ixY0v$FC?lFdTJmE{8^yIGdpwrZqUIR)%!=^KQY9ySV3g@9RBg{(cw`)K!H;fff>o&Jns8dmiLs{bloeL#q2(bGE6lniPa1$inGrzCa?j;NijW6-&{qyO4NAByqk3F_P;S13xt;ZWg1btDw$aQmoKDvZYU+hxK->-Ixag8oDGyQu}!Sgx&urfQ-lNX%A?$Z`tpB59a*S`COUhu`yU_p#9<zA2G^muk3KREuh{UREKl-YB9)6wQb*hXehMcBpmC2@s;-<bb(_^H5SkXnCSF706pcW5B9&30&hQ>ViC*8DjlD5q9{M><iY2He0WV5~D-kX0Q%S!f&?$Cyf(X2~YN5pm|eclRy3XTB1L3--JTFqBcKO5~_U<+KeRu#x+k^pHijpj6g|3hkMbX~H3m)~pQ~=m3r}dQ^x*U@L6v8fHZk%`r!~57tD5L8%jdXi2$j;Ho&FY1@Z~=fmm7>&qOe3ND<(+p;8uePhgh<;VLtVbnc|ZbTRzgl7=eJx}0(M0p3Flwu}lv$PyMjK`8#Xk1F*$Ihm7dF?fA+WxS87$G#D>{Oml*D8lo98W-EyGr)d%UBE(Ac)SMwI%#~8f-{1bK<mdQ_;6C1GtV_Wrr*z>OA{n@2--@4c${@w!$;d?qAPqsJ)-$4v`=7Pgo&|=q2t!e<%kiBpz4U74}@}#TfM(FKw%82%F;B;HL}OZs+@S^*Z+XfN#ZNS4+bNUdGgt*qF1|e7`~iv|Aq747L@Gi9e@5KOULL5}Y3a&1s3~<fP}!OY<t{46tob7o8m$X7eyAn`gy1tSxK(C)0rJIb#<L!a`qX5jousXI5HKC%YB@3TjX|x5}DwJS^XV%TFs?V&H5D>4B9DJmkQT7<VF)Ob$Nge<wg^dhc-;7$ja9NGE?0vlYFW!}=`2?9|Zu`Dot{;wFgiXwLAyrzA9ioVM1^L>hT0AHpoe5gvwMp(7_s%bcRTRhRT}KH!0E19Juvav03s4I_qOE~>xgL0)4xA+Gf@7FoY&S>zLL&rR+j!wFf{2_Qs<;8p~w060#Z>$PTluVs#an%H9RCt&5+Xl%(s7jZju8H?WwL3pxTsr?KtjZ`$l+o}lzD?+<7F1w}!(GZiUllMVH#99rdPTS>ooYg7x2|TJ&W()W^c?O+tI&qb-=aO0)hx3hT0=YPqEnv}1;BhgVwUCcx{3&GR(*q&2NbSn*u-C0IQ_$l8h7fqM#{NnDFt|_@ytk5w3}{2Z8l!xr6jkJqzJb=*$=C4#{0woI$5Wi8V<TU4LQsx{M0MpV@h!~SX%jTF%glnlbJ9>B;Q8FWS&(EnuH2I7EMS}<s8`I&D|Vd!q|Tix?YXcAcik!BUWjkpHRWopJnRO35k8b%g0-vkLcvh$tQ=1@*GoWAlK3})LlSrf@L?&wXEz)$3W4E5{e{Zms&ieA!=?X8OGK4WYZfG{D#_1|tw%JyQyUe5_cBX|SdhB)e*BYn@BbAVn7MU`e*_Ifd@;9k)~Pg)fHExunwGR#Z6=aEiYy@-c$Ip3mvlhj`~=`%WH1FzyOYWLp{tP@3_Af)$^eUffOEBy9>)-I!amBF<jRkNLy=mlm5c^TT7{=!L5WtwY~<5WCo#pc@G|$+<Hid~E(%fQh5t1QA&baWn$m}6Y(oeb%Z*zOF%(Rl3qUa(n;VtM1mW4&p*OU2Zg0J{p7Fm*uwR&Or1?^HxlcXgwlRt#7OfcbDF?p)1Gph^LV}(nb0?)%jJWbgl_JZiQnXV(k3vgL5+|^N5G-Swf|A>zeySPys8ux8G&E+lEL=lwu7b?O&Y?ktg=1BgoM}0)5R5x-cLd}r$vicDIkFZ|CZf*a0>-0sQti)~8^r)Ib{H6<V=st~sgoAPoP66}jp{0=0<mDCVHU`gnM$4yOE3dig2&bsn#mL7TVl1r_LYGrFn(y5Pm6BDcQ^A;!!3cZHtV0kQ9aF|Z7SUgEY32`*I1NVA8mzTG(o4y2eLmp$zj`DL1g=~x$t*R%0P&mM(Yb%>8)^4lQCzF57!P$Z={!z5&L4y0R%(RE;kqu*2;lKg53&e&4Y7DO0%5aWu85)MArzih{p8TN_KjoKLj8Y%Gq>o>Uc}%FKd>KA|ll}s%3K`g0MB=-iOFI2+&6CO*b{uPEYz;2Ytgv?b(?Ss!;H`Qg@cyE5r^a2Pw_okQ6P1RKM_iiwTnBES_Uy4T=<ng+W{RC%-mqw7k#bMr)T{i|#;zwjAGK&iE3Lq%jbl=kM|1Y5%vRf-J608(d0<QC&BKR1BM<2PL@xqJdWl4_-B)+RYq*T69gx_8%FQCL<OQ)lxahM1FFSRtc18D|Xk*U>J?iBBY?wZ!k9$;B$K=gJw~p5#5D687dqASp^5&%i!e5q^sy&ES>F)guk+fvN?Fh^4QN}ymxFB)X5(!JL$H4Cvnd)Jq4l=f!RH`yRxKqK#e&KE<$I?MK|?8?aSPh_mq{$_{0<}fu*4Ljocd<(Y~`^OPG#Bw28RFCujqB1eX;@N%dQ3U3Pa(4#K3#sFOSqnR&Zlcu-wxWrHP+!bC;`>n1;4_^|;7LC3&_fE%~+h&3_YIBx9%CoYpwXHhXTEy~PN^MR#m-BJ(nw!X@B2CApnm}Ofq-YgWvO30aN4NtN0P)3w#8JH2kcXDd2*2vJrNwH|XX~XFnjIUv@RBKrxfg#oLVMUrl7F#HaXDKoFyGjjA8`P!DC?z|lAWr9Xfhib=TxCH!Dmxn`VQ1j!`T0wVE^RREd0cMwdbpgL%AwP@0^n1|gXCOwADk0vblVlpu2t5Jq-w6;Y6Zvw%58;o8cuJ@3iE2|R8Th68UswPKy*)IR@Tywg<Yo!$|<veMZ{J8;@IdPt}{{k@D`=a2nCT#0W)kLQZ^p;5L?Qpos2QGpP0`J6W?ODQ1M^yw4D{KKbr0q5e%bRVKW!>u8#4XW#2^RMUX*(ybHPXRRf`rJO7#&T}tP&hYcrr;A!{#17)q=v{MVT+ZcFKVCv~A71%a*C?wu1a`RZPdk}JkjY9|Y9L@G?x>QZ@#AcQfvxwHPw>Ve3M5KecWn3&w^@`}?6cSYUWd%H1S<*ofbk@vQ#_?bkV741qeMFO>Xd`y<`Z6x{cNOOZN&fq>i?ZGY376x&FvMc(cA~5oOy((7k@&m!AN~w!L(8OyG9LZ>JV_3JRuEhE`s`%bIj}7x33X<*^s5*BD{_q>rqPF4L|Fo{Ft#A0(Uq%1zzGlguf$dwXf@>l%|j7FT_i>Z;F@|UlqKm^c<^!8(7sqOC|Tym;KjGSDKI>c$nqV4jTlBrG=__ceK6drQ*t9ql2WNcVr<e|rt6-|l($rj(x%d5XA5}UorOZ#S#&9h`8frOiT3;UTfS4)lQ_cmQXY5ISMu1-2k9Aq58<?N?9Aw(xU&?iCao{AF&K%MwI>4Nx@9X-4J)awHt?%Qn3oM~1p^7@hIp%iv2^_^%@5&|NIZ<ll=`VZHBnY#ga9WI462KKRMkAWt^#5R_|iVJCk>#A8*{tgwG1|CyDSVODQmjTP0vLL38LaxmbaoSa4JzYkUkl%h8E-?L~?Fk4>{<how|xE07ThGfttPrZqWY>T44coD5f~vd7ZPuGLvrk49d|D=4~NY<hTi1a*Z&Fw`DywgcfM}J&MyAPKuw7Y{SK1=cVGpb<bT|Yi_$`M}mS3#981FgB}La1E1P9<{*PY-me<w(cYxa7{zdCC|Qhtlb~Ht*n;M(iNuXu^jr6Wc^Xboe*!P{^XM~S_~fk&A_YKwcCU&>0$$VECTfN6Nu12Gk!FLatsrmYb$*h6uq*1CP95wZ1(Z`8vlKOFA$dlS4N?|l5tm{S8E{%bx?6yovlHP9MRJw66d0KazzhCHnyUOxm!UlzFQJA-i`Zy|OOY)V@{n-ruQNLP5)#P(5HTP_uaN7^b*G~`EHi>e5d(4}UgkQKMlA@P6PTmf==xS1`9a5n$Y)CE(J2fo#*(8G4Vv4)218tvRZ72@4>)q_K?g)uTtu4D4n)FfJ$|s-#@4mADnq_XjfI!&<bd*x;No2hq96y^mF4d1$-HqCPC5!H2bnkyWTc@~jYyO?UoH;yvZzO44R|A&Ce~11EZxxxU{}x`l?9klni2`7mXvjQ9uI?+Bd1Q0!PZt24l@kBQhRI;Mb;*ChC)xSLPuQwnL9Eh026!hvW#|4A=y343F@4KEIjvvEma@%f}QXVFIqN%BqphBAFa-I#ofPeNk^LMSIq$p;<wP=oX?%KpcXE=z5sGh^UG;yAP-FxMGWk*%n+g?*pNAJ-lBAO93#w~1>w=fW!)T$2q?1Ttt7gNTgN{!fqr2t3G!$xvoXAWLYR0HXLlS{{DM4jyHmSv0W8BrkWP!}{2)l<(J8W>EqF~6EcrTO`#~z)OsRLkT@IENtxCdmo&eMxS~M>!%0HEbPzAV7lEu{6C}2F+Lud<qU*XYkpAg&bCRx@rtPv$TK&*tDq=A0G=a?(#UQn?QH8=;#q0%Fb6xR5gcHX$vm#)16Ry{xUK-bO>&8%*HfIwNDC7an4A<=@RM4}L}Gd2r#lYWkLZMt3N32P{*0!b(qVWR*lG7Z8?^mcYEshlJMa&rWL6_v~F_pF%%QKT_O>P8XFBSoGUrjQkTa#;QaJ{VZ5RX&)2Kwel*Crg1z!&_^5=6I|(|DH^<#VpML8jmy##d}@nybGi-#(z)S>G}AD+nWMaOg7r#7d2_8MD|8lOUeU3nQSJl;+M}&ZlsZI1RUzTa|K5mW7l_yS~JWZ<Pic@Y*$7&ug!6FBSO-5-4!_n!_l8SfzD;>H9LylGjAX~2vA}X#np67MC%o;(bnRVNydPRYm>M_5&a$3?bju0mFHrK)hD!tHH!OeEgUSVZAO*N!!dAtu^5sgOc(%o@nRQ2!B`9b<l<F*Zc((vHVG<?a_bCIY{x>Ly!0zIoL#XeT4YxUY3h4drfwy4wYYCyD8Ui6l8GqsprPxBr2ugsz8J7{w@`GG+p?mN(Bya&1Dcfe1xlWp9toMJX+g02OvQQxJ=peAF=R%75yrpMkosuHDVXSfB|YfBd1WIaY?T#j&T1Ul1Da<Twvx6OjFhZgCe<l>)oNri%VX0Qbtx$)N#yxlKco_I&3ZIyX(XD=DIt2+Y#}Cke{Gu3w&aLW9vmp?Ex9UMvbsv3nSIeEkH-dU?dCz2*m+&%$Rye(pmmuvHYvu5#I3NrtT=lpd(CKP-h}2VyA3hB%o=)N<Re-G#Q_!XSRj(6SShrY5!J@RdkR0*;|({JbAbE367w=(`osa}F=<P|Q-E25%!blO-DP<slXr!!%+&HU0ki}T6`e?7u8)T6SV0z*s^J&d6(bK+?Ixky#CpZFXqb0AJ%DcXoDr#$G@63UmSfXF2Sp+NR41ML0(cu9$%{tdK-)DEN|^B?P$-5lah)}f`h<EAPQc2o95W(&$EDGzL7PXqg1mKadsxPrI}}wK%qT&sL~V+r`-QlHokFX8F12TR2hH9U?&~Ogqvet05+}c=B*_-Q%ZHwQ^>+~k8n9X5V2;rk!FjI%VU$IYL-SPiBW_5Xb70m*2n?NuFw;a7v+g4zM%^6ZCrrbfZpcinOie6^k~jv12ZEddN$NT-&?IPVwIrKiUp>}u)-oK$`6y#~Te+H#$Y_g{WCYfSu0f5OLjO|}tfwIek%G=oSh(Jq?uxi@63Is~rCfH4Ex8Bh00D4?3qwsZCjvJ{*}!Nt>rkGmgU>3h_ml3j1X@WViLHG_M7~sd0`U%PS{s!kgh&`Gk+$6={ru%h$wsuDlPR}&EzxAe!(IS$<T0OOSA`!`B%9VAS5W>ZQ;3kuxFiTqfY21)$Z8#yBzlefEMxrRowLdjrDPJfcr!YzIZXh|Zk1J;I~5++<n;5Xe+f}W($BHXb0mu6an%`xlAq(Z)pKts4I&T`WHlJw6HT?rMnP<l?(b;k0s%$(ZuJ@(du$|d1Zb=*ri$ig0}|tY4c1(O^k<=wDFkDa2c_bVqJ&tKh;TR%7O8wrZ?2PBy}xx5nJ@bl(#xv4V`JC<8A4bNrEt|yIjvAJD`zHaiw#<QpjyJu%NwC=|AgRJP3#ib9oE*3w4A)IkxxpnXjyjB0oax(ljmjE%?mo?PK)R1nz~$yWQ9LWIwGbM@q>)cRK<oOu??*F34g4%M5C<3w!|}Ocg4v)+7gVjYK1}(X%Jhh7*<lZi_c<F!3A`)#(E3*op`7iqlXB`E6`sHk&SQd5UV6pC!BpXVjC=T076-js3M6JC1|ee#QwKl2B^8^tGaug%O`icjn^q|0aZ<{M2i1<E686}tpaoiXYk6P<J+1Nnof7qvM_0Q3byeaYE_p0kYcojR)(B4AE>W4=3OU@E@=dqA}5n$A>vEy{tr@Z2|Bh08Uu9-oK{s`v<Bh|86xWEIBzO(j^uE}<p;tF0*PB^NHFLqj*qyNac&^F(JHLc)OJFsN_6x1o<749B10|)oW}~h45sAx2vXr#iI2!I7h@dOH%(QbT>XZ@xiLq8OQUEP0rZBD+p55IW0m081mm#_BbPm06Dh-{H2~;1uPp9QgE=Ts;RJtyDH(u2krJ=Mo5{)Q%HRo+7_<KqnM#yHnd*Qc0_1EfQb`h2(p)S)iZpvTQvx{1C1ovl^|JDK$`RVO(K5^ebUP_J!Vtk=>C2gLK1id4`N}Kb5AHjQ!lMP@U^v|61qC~*9dvdkh51(sZA?}u*AWj+jbSJmcSC}!B3MnBm~g*qzu>I*!ACw4ZF2)`6*)eD4vd1dOd=i?2DzwMF-=O&Q|1OtnX^lc3RN7y1M3$8{zJ4=ie)S)gAU@#JUN+CPPIzHhEJv>9T8GpHR=veXeS&@4f+^-FR_Ad6ZL(fIEWl9U}k+vYOPBGhRodJacV7-DO#=8fxIhg@iSzUSv_Le&Po*@^IYWMS@Cz8$g@>6paHn&xj!Nk;Re#~LgbW-@H=M&AgRHq{#n@>Uky$ad~+zEGULq7BMd+Ayj&m00aJSHa}an_$$Pth;t~KX+Uueq@*wa{qR97Wi)BhNB%WBid`(6FNE8d)x!Dx{RDn%v<I%N3(GF}p=(-Jk)t7?IQhE53688~!12#9f*kb7+N-|g6968ug*u{c%$$=bscC=I+4@mP3<!D2TsQ`hn7sW@@dpg($(2G+=AsL=fGL;*Mn$QnxDW6goT}$NEINc^i(}i8cZwZ$M1_I!F+KaZIyb?05tBU)MYA~ptDliI8aw=wt+GJvasEBR@1y=1T2@}4<YML9N2t!z_RRfC8)O-eER?p>sn)OndVzX9WM-avqwT=|wuR#q9!_(SB&3sKTiXl=Ll3%eYtrFT%y~LniQe}t?e;Q3cC4`v+fGr3OQ5?>Ifz5}9@1?v@6l@6e$(UFoH3SKbRt5P%lEtc*X9t{pW<>FYpWER)Bkv|*DpC_f#V*K6*P`_`UC66?mSJDd3?F?*<uj$)X240FXRT^uCMI5iKsLiDLBxj19B$`CWU%^YB^J6$S1ub0K@5%zk5w0qnXJLYW<>QB`z0@Hm{=9Z9Sn{NJ2q;$KxsYvA;G5<F0DhKHrTVQ(gK5os2p-Dbh@Ck(k7}G199A)6&PN5VG+w0w5DRRR6$AvHpdgxa}HSmKF`#oc+RC+f+|Z*(z&VX3I%Y4s>PE?nrz0)sURMN$AkK6ly@4BFJk~A0<X&1S1-&Q##&gu7QE6MBoP~ni&xO6l<pZHS7WD5xQ;o4k0yZSl=vkby!IqTrfJ9I_@nR+dKRx^ooxp$8J(BM%y-6A`LcrADR<yP4=!uG4Ouk`CD)GT12Nj2LoRbSLEr($+JS<r)LKLh_DL@%EIEl_9P$hhg6@RXuYzly)d3MvEakZ5hMd0Rixu$tNA-OLPXv-6O4ugOHf8b2fz}%L3iXw#Q>03a7JKcb)TV?%v@(Sq$^zh}$%u3C-Zv#l&)_*szJB?mid^hXJnx_c1QoWUb83r5SnOErO$H-gXpzuA6zbG$)s+a`gwk!5%#9oRM1e||QB~IAHS=h<n+#m0Ass!cu!hQaEW%l?5SlbgHL0#ZEzJCny{r@YwD+%|e-|f45!+R()av%8#(qj9<+UVu7B%W9G8~Z|X$Fl$UO>6~`eNrL8S-i~O|_DTo17Y*O*oCSW{9+=w;+ld;Gj1(w;-gnZ8xc!zHLZKMPSZ9AEOE?l(|zAkpovKEkr;id<vS2LuP*xB+%KVjy9RZ!H+p|V406~CAp{qEtiL6%U<x&)w|TLk_cL0O79H$>>?5ea;0@i1K?Z|_$iWA!^{7=vvwSVk43LpBN=&lxxJnvYRYwgnK?!=K^s!Z*X<}8CuP(?1i+%c@hWXqgJbL-fKw@quSUw7zw?&2CFwXx-p=;Wm+%wyeBD;7xq^|k4Hz~Cnqb9A=bTPaK5aUQcL`0nxTZEQuWIix5g=2t9i092Ppk&V6EKHL)}|-z_CmwH4+aFx;B8gauaC;xHcPi)87kHf9;$d%AOlA;5CRDuZxiRSx7H%5#G9W-nj|nTJVtK)i|IP&_dCjQm2#?4Jk~IhW1!3S=3*6AP3t1(NdxoRNrwrMIejjI1XS+o8qP&SCDs_v4j30~@WVnCl#&7W*KM(0D?`F#3H|B%RB}<-p1Lg~;T9uA%I6W7$(TMgwYXlkRg$99iLfFR&gL$nEfu(#Z1-jY4`TjTp3UT4S*u-%=$VrPPkhSj8v)gyRR=mVus!TbiZ+ixqiZkn3UECEb<GRD0lrSOkvbQ9l?#@uoy%WA%UpF=ne<Lg0!27bq|IZ%ZnVj;03l!2Yr*Cj_*%VDMK2=Ped?<K#D)j5vJw}9gq=ilM(PY|N!uWQ0Hz0l%vW<*T9l@SpNGsy2DTFWhgnH8e6Ue82&`>Z^ptAmZKYziVY6=-6A-B)E=1L3cs_z<&N*}z{G&J~k8p}`p^|ReoizDtfQi;aykH_{Tz^IoYzfF}%QT5?QN^lQdPFY&)B8|15H%`~D*a8;J4IQgwi#+KgrWHU>Ab&!Y<pfdJhG4}XN)oqs0iMRA-JS+qgiuFpavDP+#<wO^D4_*pJ42~HIf2d$L%F-BWT{STCcb_)>-VKlGk}_BwRyD5qqhIp)OOk)k$CG+@l1CPP1ea6TvgWq(eEC1T0mSkO;$KZm<F<WaNtAdBIXvHM*GsC-S_4L8k)Q4u?r`Dr)UgqC`om{+V!kaU7O95JtlyLlJ<wAkonB?1IV{9z4y{Rq-|$1t1zyn8GAajTB2U7+rjEq}Gz#Swnr}$+@%~6k#`kFDZN9qguRl&}JXqd)=FPagp_|Q?!{9Q&0?3wFt*tt#9jOAP<VDYq4_Ld9t<zW^7`kp3Q4f7*&f{%d|1;s)dfK;5F_j@dVeCM5Rqm%}uhuO2}=zj)`k_mN8N6&_qzpU7KPTuMaoYom7eHcgxZHbzrqr_a^x7^ZIyvcsium0|m8pL#nwWHQiZ*jcJ2PvTW|l!==6|!dTXurubcei{x@r6M40Dtm|;c?Uz?v3>J1#Wx-@;65gmcIrTR^-VMfL!qA?HHch?+wC|Ln3z|aQO_@>=R%IkanMv>Xf2t4&o97yNA@DgUF^HD@@I`=n5*%re07S17)i!;+Z8CE*j}BKV+g+qkEk}23WLu`KDyESYx3*6b3DW5jw_MDQZ9XtWvGji?4XbHOG5~VY8x3pG7qjMQdODn(U6joLHq%m3UkqkYQ%db3!>3J3B%Qitq_N3+(i&_imA+g~*AbHKRoGdHgupSirv*(Z*wqvQ5u<(%*C%FItT`SA0x~rGYT4ec0)pEsiFrF9pHn!S?pzM>-G#&kb5!c698a~>z)AYb?&gIZq)V$4;_I0uxw7PiSxM6HOuKWu_*;(H&|qj7{?TDzsYDddaONRND@&)BqUjS+Vs(<}z0UOL)Q~J)E*N)S*J{vi!&<R&(z<rvNfY{Vwu6g(U8>vSj*%*>Xz^$8f2;zyRFxMmd_hGa9+TAJx=Ls>+F~OjuhcSfX#fYL?dS_>DRq0v9|>&TTv+4xRyJ8H2g}7B;&gP4epTj~cC5C{YDFmG9X$Z;AlxgLR^%}$sb7sHm$7+ZJZ-szK-ZEfwW7;5+Ta%tfPJtpP}UVV0X=H4=T7DeG_#aUYA#f$gURV_sMgGd0`m!V8Yk7crt77e!O0dl1`^A&xdMBoS~E+eBx3R$o9iEv3!HKrWJ;wX#zCpn`QWX%w!+LJ-E*Vp7AL39>rhLzWy*Y%%5pM)EOmYbb(GawT?Ni(D4jndFlSMyLN8ZJ7Nu&W+KT=hw}%_lYRAUrp=D(xhVHhXuw=P@F)PE%j)kb;X*%ugPV$@A=y)XLY>e6nfeN`4GRsv3Dtj!OX1<G36_6udx_xw?($cXRKg3-T(^m=ezf}EMh(D3i$kem4P>P-IoI{cWP$<}ncmcJ#$C|m5&Q1=(#F+hX-&o$5RapVkNf_o*rn!GYje-RyRxYMurFK>TyA^2%hn*TrHHAfuRX_RNf|S}!d?8u}921&hm>^XHgZ<_Y?yg8NWhgt9%LH??MibGCeVfdGr+icQ;>_7d`vrV~%E&nZ8eMO)Jyl#ua_6v#YluaOuRU0@mBe1ochz9y%TQkv#gPNljY=O0eOT@;Q7>61C<qt{U0xTdo~#UNNR5;E;yJGBMy=HlRh~dd3SEsUD@Wc6C}UAA$gXH%iKSIKF-SQALq8=L=%Tb7EvX#J<MDH}V?kwB*(2a-QE4k)S|_iLo7iY2`ei`iYS4!qV%Uz+CL<R6rm28D<3EDKfyps!^Xs@$cF8ex;kepEO*|}eT*NbY$IFjhQ@750vXq|ak-f->Pz5pBaiH-xO)@bhFr+ljH)647m6pcV#ijJ7XtalO3pXi_aZ29Ju0(89-DT*742f3ZIa+mSQ%rasq!j4898C~ta!M>gR%@zZT30+U;XfKBtbVAn3hyd4pdoOlF%22$3g%_@rOGf5!8rTG)ZAIZBig?Lg)lsg6>^-S%NWO!hdK{~#YGt#Tq0F?OQ%Fz4CIli{z`(hv`GkuM1mikSozfETqwg3$m69Mz&574ihUooiYd!#P5}z5S{NZ8aagX>X(s{8ghCLC9GpP>ex1e1Gk!(QQ$|+TV|x)|Dk{(Dh2Y)Yav!%kWO$?@p_rz$Oq^}^!ufns6yL}d72HiCu6S$n`itjISWld_6w$`~59*Q36;|78Wv3`^mGvYFQ!*97=#1I+T|9|xu+mc#6$%iQQiNS+BubKqmCG9%tA5kiB_*A@(KLYyy}U+k5{*<w%%DZ)HU5i4yTlVyMmV&nx_+aE3viu;58INXT1>(5CSiTBOvw=SPp$<otJ+^9qnIt2yntAqBTESdfKgmia!6-9(!C5SSCFD9pf|_=i*!ZVR30_)uJy#=#A<Ii+Ud8B%@#BxeR`lxK@Pu67YN!5YYLbuI@F3jwf8(g*Q6ocj{q9dE+4`pW&o`mR$yFr|JeOM3mD90')).decode())
_V21_ROUTER_STEP = 72
_V21_EXPERT_STEP = 216
_V21_STATE = {0: {"last": -1, "route": None}, 1: {"last": -1, "route": None}}
_V51_POST_STATS = {
    0: {"last_step": -1, "events": 0, "units": 0, "by_item": {}},
    1: {"last_step": -1, "events": 0, "units": 0, "by_item": {}},
}
_V52_ROUTE_STATE = {
    0: {"last_step": -1, "actor": None, "events": 0, "units": 0},
    1: {"last_step": -1, "actor": None, "events": 0, "units": 0},
}
_V53_ACCESS_STATS = {
    0: {"last_step": -1, "events": 0, "units": 0},
    1: {"last_step": -1, "events": 0, "units": 0},
}
_V54_WATER_STATE = {
    0: {"last_step": -1, "actor": None, "pending_units": 0, "events": 0, "units": 0},
    1: {"last_step": -1, "actor": None, "pending_units": 0, "events": 0, "units": 0},
}
__version__ = "v54-terminal-water-bypass-rc1"


def _v54_terminal_water_bypass(obs, action, step):
    """Bypass a terminal WATER action for a carrier already committed to shed return."""
    seat = _seat(obs)
    state = _V54_WATER_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state.clear()
        state.update(last_step=step, actor=None, pending_units=0, events=0, units=0)
    state["last_step"] = step
    if _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        state["actor"] = None
        state["pending_units"] = 0
        return action

    action = _align_hands(action, obs)
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    inventories = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    orders = [list(action.get("farmer", ["PASS"])), *[list(value or ["PASS"]) for value in action.get("hands", [])]]
    access = _shed_access(len(_get(farm, "tiles", []) or []) or 10)

    if step == 712:
        state["actor"] = None
        state["pending_units"] = 0
        for actor, (position, inventory, order) in enumerate(zip(positions, inventories, orders)):
            distance = min(abs(int(position[0]) - x) + abs(int(position[1]) - y) for x, y in access)
            carried = sum(max(0, int(inventory.get(item, 0) or 0)) for item in _SELLABLE)
            if distance not in (3, 4) or carried <= 0 or not order or order[0] != "WATER":
                continue
            orders[actor] = _v52_move_to_access(position, access)
            state["actor"] = actor
            state["pending_units"] = carried
            action["farmer"], action["hands"] = orders[0], orders[1:]
            return action
        return action

    if 713 <= step <= 718 and state.get("actor") is not None:
        actor = int(state["actor"])
        if actor >= len(positions) or actor >= len(inventories):
            state["actor"] = None
            state["pending_units"] = 0
            return action
        if tuple(positions[actor]) in access:
            carried = sum(max(0, int(inventories[actor].get(item, 0) or 0)) for item in _SELLABLE)
            if carried > 0:
                orders[actor] = ["DROP"]
                action["farmer"], action["hands"] = orders[0], orders[1:]
                state["events"] = int(state.get("events", 0)) + 1
                state["units"] = int(state.get("units", 0)) + carried
            state["actor"] = None
            state["pending_units"] = 0
            return action
        orders[actor] = _v52_move_to_access(positions[actor], access)
        action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def _v53_terminal_access_flush(obs, action, step):
    """Flush carried goods instead of collecting one final fertilizer at step 716."""
    seat = _seat(obs)
    stats = _V53_ACCESS_STATS[seat]
    if step == 0 or step < int(stats.get("last_step", -1)):
        stats.clear()
        stats.update(last_step=step, events=0, units=0)
    stats["last_step"] = step
    if step != 716 or _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        return action

    action = _align_hands(action, obs)
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    inventories = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    orders = [list(action.get("farmer", ["PASS"])), *[list(value or ["PASS"]) for value in action.get("hands", [])]]
    access = _shed_access(len(_get(farm, "tiles", []) or []) or 10)
    for actor, (position, inventory, order) in enumerate(zip(positions, inventories, orders)):
        if tuple(position) not in access or not order or order[0] != "COLLECT_FERTILIZER":
            continue
        carried = sum(max(0, int(inventory.get(item, 0) or 0)) for item in _SELLABLE)
        if carried <= 0:
            continue
        orders[actor] = ["DROP"]
        action["farmer"], action["hands"] = orders[0], orders[1:]
        stats["events"] = int(stats.get("events", 0)) + 1
        stats["units"] = int(stats.get("units", 0)) + carried
        break
    return action


def _v52_move_to_access(position, access):
    x, y = int(position[0]), int(position[1])
    target = min(access, key=lambda tile: (abs(x - tile[0]) + abs(y - tile[1]), tile[1], tile[0]))
    if target[0] > x:
        return ["EAST"]
    if target[0] < x:
        return ["WEST"]
    if target[1] > y:
        return ["SOUTH"]
    if target[1] < y:
        return ["NORTH"]
    return ["PASS"]


def _v52_terminal_route_acceleration(obs, action, step):
    """Trade one terminal fertilizer collection for an earlier carried-goods sale."""
    seat = _seat(obs)
    state = _V52_ROUTE_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state.clear()
        state.update(last_step=step, actor=None, events=0, units=0)
    state["last_step"] = step
    if _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        state["actor"] = None
        return action

    action = _align_hands(action, obs)
    farm = _farm(obs, seat)
    private = _get(obs, "private", {}) or {}
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    inventories = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    orders = [list(action.get("farmer", ["PASS"])), *[list(value or ["PASS"]) for value in action.get("hands", [])]]
    access = _shed_access(len(_get(farm, "tiles", []) or []) or 10)

    if step == 714:
        state["actor"] = None
        for actor, (position, inventory, order) in enumerate(zip(positions, inventories, orders)):
            if not (isinstance(position, (list, tuple)) and len(position) >= 2):
                continue
            distance = min(abs(int(position[0]) - x) + abs(int(position[1]) - y) for x, y in access)
            carried = sum(max(0, int(inventory.get(item, 0) or 0)) for item in _SELLABLE)
            if distance != 1 or carried <= 0 or not order or order[0] != "COLLECT_FERTILIZER":
                continue
            orders[actor] = _v52_move_to_access(position, access)
            state["actor"] = actor
            state["units"] = int(state.get("units", 0)) + carried
            action["farmer"], action["hands"] = orders[0], orders[1:]
            return action
        return action

    if step == 715 and state.get("actor") is not None:
        actor = int(state["actor"])
        state["actor"] = None
        if actor >= len(positions) or actor >= len(inventories) or tuple(positions[actor]) not in access:
            return action
        carried = sum(max(0, int(inventories[actor].get(item, 0) or 0)) for item in _SELLABLE)
        if carried <= 0:
            return action
        orders[actor] = ["DROP"]
        action["farmer"], action["hands"] = orders[0], orders[1:]
        state["events"] = int(state.get("events", 0)) + 1
    return action


def _v51_post_action_terminal_sell(obs, action, step):
    """Sell inventory deposited by this turn's terminal DROP/PLACE action."""
    seat = _seat(obs)
    stats = _V51_POST_STATS[seat]
    if step == 0 or step < int(stats.get("last_step", -1)):
        stats.clear()
        stats.update(last_step=step, events=0, units=0, by_item={})
    stats["last_step"] = step
    if step < 715 or step > 718:
        return action

    action = _copy_action(action)
    action = _align_hands(action, obs)
    market = [list(order) for order in (action.get("market") or [])]
    projected = _projected_shed(obs, action)
    planned = {item: 0 for item in _SELLABLE}
    for order in market:
        if _is_sell(order):
            item = str(order[1])
            planned[item] = planned.get(item, 0) + max(0, int(order[2] or 0))

    added = {}
    for item in _LIQUIDATION_ORDER:
        extra = max(0, int(projected.get(item, 0) or 0) - int(planned.get(item, 0) or 0))
        if extra <= 0:
            continue
        existing = next((order for order in market if _is_sell(order) and str(order[1]) == item), None)
        if existing is not None:
            existing[2] = max(0, int(existing[2] or 0)) + extra
        elif len(market) < 10:
            market.append(["SELL", item, extra])
        else:
            continue
        planned[item] = planned.get(item, 0) + extra
        added[item] = added.get(item, 0) + extra

    if not added:
        return action
    action["market"] = market[:10]
    stats["events"] = int(stats.get("events", 0)) + 1
    stats["units"] = int(stats.get("units", 0)) + sum(added.values())
    by_item = stats.setdefault("by_item", {})
    for item, quantity in added.items():
        by_item[item] = int(by_item.get(item, 0)) + quantity
    action = _rank_sell_slots(obs, action, None)
    action = _bubble_premium_over_non_sells(action)
    action = _bubble_sells_over_fixed_spends(action, obs)
    return _merge_duplicate_sells(action)


def model_status():
    return {
        "kind": "v54_terminal_water_bypass",
        "model_id": "v54_terminal_water_bypass",
        "parent": "v53_terminal_access_flush",
        "horizon": _V32_PREEMPT_HORIZON,
        "stats": copy.deepcopy(_V32_STATS),
        "terminal_stats": copy.deepcopy(_V45_TERMINAL_STATS),
        "post_action_stats": copy.deepcopy(_V51_POST_STATS),
        "route_acceleration_stats": copy.deepcopy(_V52_ROUTE_STATE),
        "access_flush_stats": copy.deepcopy(_V53_ACCESS_STATS),
        "terminal_water_stats": copy.deepcopy(_V54_WATER_STATE),
    }


del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V21_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, route=None)
    state["last"] = step
    if state.get("route") is None and step >= _V21_ROUTER_STEP:
        town = _get(obs, "town", {}) or {}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    route = str(state.get("route") or "default")
    if route != "yarn" and step >= _V21_EXPERT_STEP:
        _ACTIONS = _V21_LUCASKNA_ROUTE
    else:
        _ACTIONS = _V19_ROUTES[route]
    action = _V19_CORE(obs)
    action = _v20_delay_sales(obs, action, step)
    action = _cap_fixed_purchases(obs, action, _V19_PROXY)
    action = _fail_closed_units(obs, action)
    action = _v52_terminal_route_acceleration(obs, action, step)
    action = _v53_terminal_access_flush(obs, action, step)
    action = _v54_terminal_water_bypass(obs, action, step)
    return _v51_post_action_terminal_sell(obs, action, step)


_V66_AGENT = agent
_V66_PARENT_STATUS = model_status
__version__ = "v66-margin-gated-sell-bubble-rc1"


def model_status():
    status = _V66_PARENT_STATUS()
    status.update({
        "kind": "v66_margin_gated_sell_bubble",
        "model_id": "v66_margin_gated_sell_bubble",
        "parent": "v54_terminal_water_bypass",
        "margin_gated_sell_bubble": True,
    })
    return status


del agent
def agent(obs, configuration=None):
    return _V66_AGENT(obs, configuration)


_V76_PARENT_AGENT = agent
_V76_PARENT_STATUS = model_status
__version__ = "v76-adjacent-safe-buy-lead-rc1"


def _v76_adjacent_safe_buy_lead(obs, action):
    """Keep V73's merge, then lead one dynamic buy across a safe fixed order."""
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    if _clone_distance(obs) > _PREEMPT_MAX_CLONE_DISTANCE:
        return action
    for index in range(len(market) - 1):
        first, second = market[index], market[index + 1]
        if not (
            isinstance(first, list) and len(first) >= 3
            and isinstance(second, list) and len(second) >= 3
            and first[0] == second[0] == "BUY_PRODUCT"
            and str(first[1]) == str(second[1]) == "WHEAT"
        ):
            continue
        later = max(0, int(second[2] or 0))
        if later <= 0:
            continue
        shifted = later
        first[2] = max(0, int(first[2] or 0)) + shifted
        second[2] = later - shifted
        action["market"] = market[:10]
        break
    safe = {"HIRE", "BUY_LAND", "BUY_SEED"}
    for index in range(1, len(market)):
        previous, current = market[index - 1], market[index]
        if not (
            isinstance(previous, list) and previous and str(previous[0]) in safe
            and isinstance(current, list) and len(current) >= 3
            and str(current[0]) == "BUY_PRODUCT"
            and str(current[1]) in {"WHEAT", "FERTILIZER"}
            and int(current[2] or 0) > 0
        ):
            continue
        market[index - 1], market[index] = current, previous
        action["market"] = market[:10]
        break
    return action


def model_status():
    status = _V76_PARENT_STATUS()
    status.update({
        "kind": "v76_adjacent_safe_buy_lead",
        "model_id": "v76_adjacent_safe_buy_lead",
        "parent": "v73_duplicate_wheat_buy_full_merge",
        "duplicate_wheat_buy_shift_fraction": 1.0,
        "adjacent_safe_buy_lead": True,
    })
    return status


del agent
def agent(obs, configuration=None):
    return _v76_adjacent_safe_buy_lead(obs, _V76_PARENT_AGENT(obs, configuration))


# --- V78 public-opponent-belief Hierarchical MoE ---
_V78_PARENT_AGENT = agent
_V78_PARENT_STATUS = model_status
_V78_OUTPUT = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
_V78_STATE = {
    0: {"last_step": -1, "day": -1, "expert": "fallback", "product": None, "confidence": 0.0, "events": 0},
    1: {"last_step": -1, "day": -1, "expert": "fallback", "product": None, "confidence": 0.0, "events": 0},
}
__version__ = "v78-opponent-belief-hierarchical-moe-rc1"


def _v78_public_supply_belief(obs):
    """Shallow belief over the opponent's next sale product using public state."""
    seat = _seat(obs)
    farms = list(_get(obs, "farms", []) or [])
    opponent = farms[1 - seat] if len(farms) >= 2 else {}
    scores = {item: 0.0 for item in _SELLABLE}
    for row in list(_get(opponent, "tiles", []) or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            crop = str(tile.get("crop", "") or "")
            if crop in scores:
                scores[crop] += 1.0 + max(0.0, float(tile.get("yield_units", 0) or 0))
                if bool(tile.get("watered_today")):
                    scores[crop] += 0.25
            animal = str(tile.get("animal", "") or "")
            product = _V78_OUTPUT.get(animal)
            if product:
                scores[product] += 2.5
    town = _get(obs, "town", {}) or {}
    for shop in list(_get(town, "unlocked_shops", []) or []):
        products = _SHOP_PRODUCTS.get(str(shop), ())
        weight = 0.5 if len(products) > 1 else 1.0
        for product in products:
            scores[product] = scores.get(product, 0.0) + weight
    ranked = sorted(scores.items(), key=lambda value: (-value[1], value[0]))
    top_item, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    total = sum(scores.values())
    confidence = top_score / total if total > 0 else 0.0
    supported = top_score >= 3.0 and top_score - second_score >= 1.0 and confidence >= 0.24
    return (top_item if supported else None), confidence, scores


def _v78_route(obs, step):
    seat = _seat(obs)
    day = int(_get(obs, "day", step // 24) or 0)
    state = _V78_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "day": -1, "expert": "fallback", "product": None, "confidence": 0.0, "events": 0}
        _V78_STATE[seat] = state
    state["last_step"] = step
    if step >= 72 and day != int(state.get("day", -1)):
        product, confidence, _ = _v78_public_supply_belief(obs)
        state["day"] = day
        state["product"] = product
        state["confidence"] = confidence
        state["expert"] = "product_front_run" if product else "fallback"
    return state


def _v78_product_front_run(obs, action, step):
    state = _v78_route(obs, step)
    if state.get("expert") != "product_front_run":
        return action
    product = str(state.get("product") or "")
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    for index, order in enumerate(market):
        if not (_is_sell(order) and str(order[1]) == product and index > 0):
            continue
        start = index
        while start > 0 and _is_sell(market[start - 1]):
            start -= 1
        if start < index:
            selected = market.pop(index)
            market.insert(start, selected)
            state["events"] = int(state.get("events", 0)) + 1
        break
    action["market"] = market[:10]
    return action


def model_status():
    status = _V78_PARENT_STATUS()
    status.update({
        "kind": "v78_opponent_belief_moe",
        "model_id": "v78_opponent_belief_moe",
        "parent": "v76_adjacent_safe_buy_lead",
        "lineage": "opponent-belief-best-response",
        "experts": ["fallback", "product_front_run"],
        "belief_state": copy.deepcopy(_V78_STATE),
    })
    return status


del agent
def agent(obs, configuration=None):
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    return _v78_product_front_run(obs, _V78_PARENT_AGENT(obs, configuration), step)
