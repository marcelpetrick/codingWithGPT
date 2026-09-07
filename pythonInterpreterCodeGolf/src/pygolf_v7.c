#define R E(&p,0)
#define Y X(i+1,e)
char S[9999],*T[999],*O="=!<>+-*/%";int D[999],N,A[128];
E(char**p,int k){int v=0,w,l,q,i,c=**p;char*o;
if(c==40){++*p;v=E(p,0);++*p;}
else if(c<58){while(**p>47&&**p<58)v=v*10+*(*p)++-48;}
else{while(**p>96)++*p;v=A[c];}
while(**p&&(o=strchr(O,**p))&&(i=o-O,l=1+(i>3)+(i>5))>k){
++*p;if(q=**p==61||**p==47)++*p;w=E(p,l);
v=i?i-1?i-2?i-3?i-4?i-5?i-6?i-7?v%w:v/w:v*w:v-w:v+w:v>w-q:v<w+q:v!=w:v==w;}
return v;}
B(int i){int j=i;while(D[++j]>D[i]);return j;}
X(int i,int h){int e,a,k,t,g;char*s,*p;
while(i<h){s=T[i];e=B(i);switch(*s){
case 100:A[s[3]]=i;i=e;break;
case 105:p=s+2;t=R;a=e;if(e<h&&*T[e]==101)a=B(e);
if(t)Y;else if(a>e)X(e+1,a);i=a;break;
case 119:while(p=s+5,R)Y;i=e;break;
case 102:p=strchr(s,40)+1;t=R;k=0;g=1;
if(*p==44){++p;k=t;t=R;}if(*p==44){++p;g=R;}
for(;k<t;k+=g){A[s[3]]=k;Y;}i=e;break;
case 112:p=s+6;if(*p==34){for(++p;*p-34;)putchar(*p++);puts("");}
else printf("%d\n",R);i++;break;
default:p=s+strcspn(s,"=(");if(*p==40){k=A[*s];X(k+1,B(k));}else{++p;A[*s]=R;}i++;}}}
main(){char*p=S,*w=S;int d,q;read(0,S,9998);
while(*p){p+=d=strspn(p," ");T[N]=w;q=0;
while(*p&&*p-10){if(*p==34)q^=1;if(*p==35&&!q)q=2;if(q-2&&(q||*p-32))*w++=*p;p++;}
p++;if(w>T[N]){*w++=0;D[N++]=d;}}X(0,N);}
