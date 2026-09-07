#include <stdio.h>
#include <string.h>
char S[65536],*T[999],M[99][16];
int D[999],N,V[99],F[99],K;
int I(char*a,int n){int i;
 for(i=0;i<K;i++)if(!strncmp(M[i],a,n)&&!M[i][n])return i;
 memcpy(M[K],a,n);return K++;}
int C(char c){return c>96&&c<123||c>64&&c<91||c>47&&c<58||c==95;}
int E(char**,int);
int P(char**p){char*a=*p;int v=0;
 if(*a=='('){(*p)++;v=E(p,0);(*p)++;return v;}
 if(*a=='-'){(*p)++;return -P(p);}
 if(*a>47&&*a<58){while(**p>47&&**p<58)v=v*10+*(*p)++-48;return v;}
 while(C(**p))(*p)++;return V[I(a,*p-a)];}
int L(char c){return c=='='||c=='!'||c=='<'||c=='>'?1:
 c=='+'||c=='-'?2:c=='*'||c=='/'||c=='%'?3:0;}
int E(char**p,int k){int v=P(p),w,l,q;char c;
 while((l=L(**p))>k){c=*(*p)++;q=**p=='='||**p=='/';if(q)(*p)++;w=E(p,l);
  v=c=='+'?v+w:c=='-'?v-w:c=='*'?v*w:c=='/'?v/w:c=='%'?v%w:
    c=='='?v==w:c=='!'?v!=w:c=='<'?v<w+q:v>w-q;}
 return v;}
int B(int i,int h){int j=i+1;while(j<h&&D[j]>D[i])j++;return j;}
void X(int l,int h){int i=l,e,a,d,k,t,f,g;char*s,*p;
 while(i<h){s=T[i];e=B(i,h);
  if(!strncmp(s,"def",3)){F[I(s+3,strcspn(s+3,"("))]=i;i=e;}
  else if(!strncmp(s,"if",2)){p=s+2;t=E(&p,0);a=e;
   if(e<h&&*T[e]=='e')a=B(e,h);
   if(t)X(i+1,e);else if(a>e)X(e+1,a);i=a;}
  else if(!strncmp(s,"while",5)){for(;;){p=s+5;if(!E(&p,0))break;X(i+1,e);}i=e;}
  else if(!strncmp(s,"for",3)){p=strstr(s,"range(");d=I(s+3,p-s-5);p+=6;
   f=0;g=1;t=E(&p,0);
   if(*p==','){p++;f=t;t=E(&p,0);}
   if(*p==','){p++;g=E(&p,0);}
   for(k=f;g>0?k<t:k>t;k+=g){V[d]=k;X(i+1,e);}i=e;}
  else if(!strncmp(s,"print",5)){p=s+6;
   if(*p=='"'||*p==39){for(k=*p++;*p!=k;)
    if(*p=='\\'&&p[1]=='n'){putchar(10);p+=2;}else putchar(*p++);}
   else if(*p!=')')printf("%d",E(&p,0));
   putchar(10);i++;}
  else{k=strcspn(s,"=(");d=I(s,k);p=s+k+1;
   if(s[k]=='(')X(F[d]+1,B(F[d],N));else V[d]=E(&p,0);
   i++;}}}
int main(){char*p=S,*w=S;int d,q;
 S[fread(S,1,65535,stdin)]=0;
 while(*p){
  for(d=0;*p==32||*p==9;p++)d++;
  T[N]=w;q=0;
  while(*p&&*p!=10){
   if(*p=='"'||*p==39)q=!q;
   if(*p=='#'&&!q){while(*p&&*p!=10)p++;break;}
   if(q||*p!=32&&*p!=9)*w++=*p;
   p++;}
  if(*p)p++;
  if(w>T[N]){*w++=0;D[N++]=d;}}
 X(0,N);return 0;}
