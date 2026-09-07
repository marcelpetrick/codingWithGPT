#define R E(0)
#define Y X(i+1,e)
#define K break;
char S[9999],D[999],*T[999],*p,*w,*o,*O="=!<>+-*/%";int N,A[128],q,j;E(k){int v=0,x,l,i,c=*p;if(c==40){p++;v=E(0);p++;}else if(c<58)v=strtol(p,&p,10);else{while(*++p>96);v=A[c];}while(*p&&(o=strchr(O,*p))&&(i=o-O,l=1+(i>3)+(i>5))>k){p++;p+=q=*p==61||*p==47;x=E(l);v=i?i-1?i-2?i-3?i-4?i-5?i-6?i-7?v%x:v/x:v*x:v-x:v+x:v>x-q:v<x+q:v!=x:v==x;}return v;}B(i){j=i;while(D[++j]>D[i]);return j;}X(i,h){int e,k,t,g;char*s;while(i<h){s=T[i];e=B(i);switch(*s){case 100:A[s[3]]=i;K
case 105:p=s+2;t=e<h&&*T[e]==101?B(e):e;if(R)Y;else X(e+1,t);e=t;K
case 119:while(p=s+5,R)Y;K
case 102:p=strchr(s,40)+1;t=R;k=0;g=1;if(*p++==44){k=t;t=R;}if(*p++==44)g=R;for(;k<t;k+=g){A[s[3]]=k;Y;}K
case 112:p=s+6;*p?printf("%d\n",R):puts(p+1);K
default:p=strchr(s,61);p?(p++,A[*s]=R):X(A[*s]+1,B(A[*s]));}i=e;}}main(){p=w=S;read(0,S,9998);while(*p){p+=D[N]=strspn(p," ");T[N]=w;q=0;while(*p>10){q^=*p==34;if(*p==35&&!q)q=2;if(q-2&&(q||*p-32))*w++=*p-34?*p:0;p++;}p++;if(w-T[N])N++,*w++=0;}X(0,N);}
