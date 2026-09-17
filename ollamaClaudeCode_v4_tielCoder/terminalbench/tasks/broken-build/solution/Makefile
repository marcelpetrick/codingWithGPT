CFLAGS = -Wall -Werror -std=c11
app: main.o strutil.o
	$(CC) $(CFLAGS) -o app main.o strutil.o
main.o: main.c strutil.h
	$(CC) $(CFLAGS) -c main.c
strutil.o: strutil.c strutil.h          # BUG: typo'd source name
	$(CC) $(CFLAGS) -c strutil.c
clean:
	rm -f app *.o
