#define R E(0)
#define Y X(i+1,e)
#define K break;
char S[9999],D[999],*T[999],*p,*O="=!<>+-*/%";int N,A[128];
E(k){int v=0,w,l,q,i,c=*p;char*o;
if(c==40){p++;v=E(0);p++;}
else if(c<58)v=strtol(p,&p,10);
else{while(*p>96)p++;v=A[c];}
while(*p&&(o=strchr(O,*p))&&(i=o-O,l=1+(i>3)+(i>5))>k){
p++;if(q=*p==61||*p==47)p++;w=E(l);
v=i?i-1?i-2?i-3?i-4?i-5?i-6?i-7?v%w:v/w:v*w:v-w:v+w:v>w-q:v<w+q:v!=w:v==w;}
return v;}
B(i){int j=i;while(D[++j]>D[i]);return j;}
X(i,h){int e,a,k,t,g;char*s;
while(i<h){s=T[i];e=B(i);switch(*s){
case 100:A[s[3]]=i;K
case 105:p=s+2;a=e<h&&*T[e]==101?B(e):e;if(R)Y;else if(a>e)X(e+1,a);e=a;K
case 119:while(p=s+5,R)Y;K
case 102:p=strchr(s,40)+1;t=R;k=0;g=1;if(*p++==44){k=t;t=R;}if(*p++==44)g=R;
for(;k<t;k+=g){A[s[3]]=k;Y;}K
case 112:p=s+6;if(*p==34){while(*++p-34)putchar(*p);puts("");}else printf("%d\n",R);K
default:k=A[*s];p=s+strcspn(s,"=(");*p==40?X(k+1,B(k)):(p++,A[*s]=R);}
i=e;}}
main(){char*w=S;int d,q;p=S;read(0,S,9998);
while(*p){p+=d=strspn(p," ");T[N]=w;q=0;
while(*p&&*p-10){if(*p==34)q^=1;if(*p==35&&!q)q=2;if(q-2&&(q||*p-32))*w++=*p;p++;}
p++;if(w>T[N]){*w++=0;D[N++]=d;}}X(0,N);}
