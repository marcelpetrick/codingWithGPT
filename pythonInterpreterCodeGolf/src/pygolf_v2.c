#include <stdio.h>
#include <string.h>
char S[65536],*T[999],M[99][16];
int D[999],N,V[99],F[99],K;
int E(char**);
void W(char**p){while(**p==32||**p==9)(*p)++;}
int C(char c){return c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_';}
int A(char**p,char*w){int n=strlen(w);W(p);
 if(strncmp(*p,w,n)||C(w[n-1])&&C((*p)[n]))return 0;*p+=n;return 1;}
int I(char*a,int n){int i;
 for(i=0;i<K;i++)if(strlen(M[i])==n&&!strncmp(M[i],a,n))return i;
 memcpy(M[K],a,n);M[K][n]=0;F[K]=-1;return K++;}
int R(char**p){char*a;W(p);a=*p;while(C(**p))(*p)++;return I(a,*p-a);}
int P(char**p){int v=0;W(p);
 if(**p=='('){(*p)++;v=E(p);A(p,")");return v;}
 if(**p=='-'){(*p)++;return -P(p);}
 if(**p>='0'&&**p<='9'){while(**p>='0'&&**p<='9')v=v*10+*(*p)++-48;return v;}
 return V[R(p)];}
int Q(char**p){int v=P(p);for(;;){W(p);
 if(**p=='*'){(*p)++;v*=P(p);}
 else if(**p=='/'){(*p)++;if(**p=='/')(*p)++;v/=P(p);}
 else if(**p=='%'){(*p)++;v%=P(p);}
 else return v;}}
int U(char**p){int v=Q(p);for(;;){W(p);
 if(**p=='+'){(*p)++;v+=Q(p);}
 else if(**p=='-'){(*p)++;v-=Q(p);}
 else return v;}}
int E(char**p){int v=U(p);for(;;){
 if(A(p,"=="))v=v==U(p);else if(A(p,"!="))v=v!=U(p);
 else if(A(p,"<="))v=v<=U(p);else if(A(p,">="))v=v>=U(p);
 else{W(p);
  if(**p=='<'){(*p)++;v=v<U(p);}
  else if(**p=='>'){(*p)++;v=v>U(p);}
  else return v;}}}
int B(int i,int h){int j=i+1;while(j<h&&D[j]>D[i])j++;return j;}
void G(char*p){W(&p);
 if(*p=='"'||*p==39){char q=*p++;
  while(*p&&*p!=q)if(*p=='\\'&&p[1]=='n'){putchar(10);p+=2;}else putchar(*p++);}
 else if(*p!=')')printf("%d",E(&p));
 putchar(10);}
void X(int l,int h){int i=l;
 while(i<h){char*s=T[i];int b=i+1,e=B(i,h);
  if(A(&s,"def")){F[R(&s)]=i;i=e;}
  else if(A(&s,"if")){int t=E(&s)!=0,a=e;
   if(e<h&&!strncmp(T[e],"else",4))a=B(e,h);
   if(t)X(b,e);else if(a>e)X(e+1,a);i=a;}
  else if(A(&s,"while")){char*c=s;while(E(&s)){X(b,e);s=c;}i=e;}
  else if(A(&s,"for")){int d=R(&s),f=0,t,p=1,k;
   A(&s,"in");A(&s,"range");A(&s,"(");t=E(&s);
   if(A(&s,",")){f=t;t=E(&s);}
   if(A(&s,","))p=E(&s);
   for(k=f;p>0?k<t:k>t;k+=p){V[d]=k;X(b,e);}i=e;}
  else if(A(&s,"print")){A(&s,"(");G(s);i++;}
  else{int d=R(&s);W(&s);
   if(*s=='(')X(F[d]+1,B(F[d],N));else{s++;V[d]=E(&s);}
   i++;}}}
int main(){char*p=S,*c;int q;
 S[fread(S,1,65535,stdin)]=0;
 while(*p){char*l=p;int d=0;
  while(*p&&*p!=10)p++;
  if(*p)*p++=0;
  while(*l==32||*l==9){l++;d++;}
  for(c=l,q=0;*c;c++){if(*c=='"'||*c==39)q=!q;if(*c=='#'&&!q)break;}
  *c=0;
  if(*l){T[N]=l;D[N++]=d;}}
 X(0,N);return 0;}
