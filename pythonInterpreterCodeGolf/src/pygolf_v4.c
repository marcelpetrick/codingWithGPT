char S[9999],*T[999];int D[999],N,V[128],F[128];
P(char**p){char*a=*p;int v=0;
 if(*a==40){++*p;v=E(p,0);++*p;return v;}
 if(*a==45){++*p;return-P(p);}
 if(*a>47&&*a<58){while(**p>47&&**p<58)v=v*10+*(*p)++-48;return v;}
 while(**p>96)++*p;return V[*a];}
E(char**p,int k){int v=P(p),w,l,q;char c;
 while((l=(c=**p)==61||c==33||c==60||c==62?1:c==43||c==45?2:
  c==42||c==47||c==37?3:0)>k){
  ++*p;q=**p==61||**p==47;if(q)++*p;w=E(p,l);
  v=c==43?v+w:c==45?v-w:c==42?v*w:c==47?v/w:c==37?v%w:
   c==61?v==w:c==33?v!=w:c==60?v<w+q:v>w-q;}
 return v;}
B(int i,int h){int j=i+1;while(j<h&&D[j]>D[i])j++;return j;}
X(int i,int h){int e,a,k,t,f,g;char*s,*p;
 while(i<h){s=T[i];e=B(i,h);
  if(*s==100){F[s[3]]=i;i=e;}
  else if(*s==105){p=s+2;t=E(&p,0);a=e;
   if(e<h&&*T[e]==101)a=B(e,h);
   if(t)X(i+1,e);else if(a>e)X(e+1,a);i=a;}
  else if(*s==119){for(;;){p=s+5;if(!E(&p,0))break;X(i+1,e);}i=e;}
  else if(*s==102){p=strchr(s,40)+1;f=0;g=1;t=E(&p,0);
   if(*p==44){++p;f=t;t=E(&p,0);}
   if(*p==44){++p;g=E(&p,0);}
   for(k=f;g>0?k<t:k>t;k+=g){V[s[3]]=k;X(i+1,e);}i=e;}
  else if(*s==112){p=s+6;
   if(*p==34||*p==39)for(k=*p++;*p!=k;)
    if(*p==92&&p[1]==110){putchar(10);p+=2;}else putchar(*p++);
   else if(*p!=41)printf("%d",E(&p,0));
   putchar(10);i++;}
  else{p=s+strcspn(s,"=(");
   if(*p==40)X(F[*s]+1,B(F[*s],N));else{++p;V[*s]=E(&p,0);}
   i++;}}}
main(){char*p=S,*w=S;int d,q;read(0,S,9998);
 while(*p){
  for(d=0;*p==32;p++)d++;
  T[N]=w;q=0;
  while(*p&&*p!=10){
   if(*p==34||*p==39)q=!q;
   if(*p==35&&!q){while(*p&&*p!=10)p++;break;}
   if(q||*p!=32)*w++=*p;
   p++;}
  if(*p)p++;
  if(w>T[N]){*w++=0;D[N++]=d;}}
 X(0,N);}
