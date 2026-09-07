#define R E(0)
#define Y X(i+1,e)
#define W while
#define K break;case 
char S[9999],D[999],*T[999],*p=S,*w=S,*o,*O="=!<>+-*/%";int N,A[128],q,j;E(k){int v,x,l,i,c=*p;W(c>96&&*++p>96);v=c==40?(p++,x=E(0),p++,x):c<58?strtol(p,&p,0):A[c];W(*p&&(o=strchr(O,*p))&&(i=o-O,l=1+(i>3)+(i>5))>k){p++;p+=q=*p==61|*p==47;x=E(l);v=i?i-1?i-2?i-3?i-4?i-5?i-6?i-7?v%x:v/x:v*x:v-x:v+x:v>x-q:v<x+q:v!=x:v==x;}return v;}B(i){j=i;W(D[++j]>D[i]);return j;}X(i,h){int e,k,t,g;char*s;W(i<h){s=T[i];e=B(i);switch(*s){default:k=A[*s],p=strchr(s,61);p?(p++,A[*s]=R):X(k+1,B(k));K 100:A[s[3]]=i;K 105:p=s+2;t=e<h&&*T[e]==101?B(e):e;R?Y:X(e+1,t);e=t;K 119:W(p=s+5,R)Y;K 102:p=strchr(s,40)+1;k=0;g=1;t=R;*p++==44&&(k=t,t=R);*p++==44&&(g=R);for(;k<t;k+=g)A[s[3]]=k,Y;K 112:p=s+6;*p?printf("%d\n",R):puts(p+1);}i=e;}}main(){read(0,S,9998);W(*p){p+=D[N]=strspn(p," ");T[N]=w;q=0;W(*p>10){q^=*p==34;if(*p==35&&!q)q=2;if(q-2&&(q|*p-32))*w++=*p-34?*p:0;p++;}p++;if(w-T[N])N++,*w++=0;}X(0,N);}
