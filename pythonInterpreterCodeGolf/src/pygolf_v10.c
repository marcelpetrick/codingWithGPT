#define Y X(i+1,e)
char S[999],D[99],*T[99],*p,*w;int N,A[128],j;
V(){return *p<58?strtol(p,&p,10):A[*p++];}
E(){int v=V();while(*p==37){p++;v%=V();}if(*p==61){p+=2;v=v==E();}return v;}
B(i){j=i;while(D[++j]>D[i]);return j;}
X(i,h){int e,k,t;char*s;while(i<h){s=T[i];e=B(i);
if(*s==100)A[s[3]]=i;
else if(*s==105){t=e<h&&*T[e]==101?B(e):e;p=s+2;if(E())Y;else X(e+1,t);e=t;}
else if(*s==102){p=s+12;t=E();for(k=0;k<t;k++){A[s[3]]=k;Y;}}
else if(*s==112){p=s+6;*p?printf("%d\n",E()):puts(p+1);}
else X(A[*s]+1,B(A[*s]));
i=e;}}
main(){p=w=S;read(0,S,998);while(*p){p+=D[N]=strspn(p," ");T[N]=w;
while(*p>10){if(*p-32)*w++=*p-34?*p:0;p++;}p++;if(w-T[N])N++,*w++=0;}X(0,N);}
