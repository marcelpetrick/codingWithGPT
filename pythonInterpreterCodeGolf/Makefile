CC     = gcc
CFLAGS = -std=gnu89 -w -O1

all: bin/pygolf bin/pygolf-min

bin/pygolf: src/pygolf_v9.c          # full subset, 1021 bytes
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $@ $<

bin/pygolf-min: src/pygolf_v11.c     # FizzBuzz only, 644 bytes
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $@ $<

reference: src/pygolf_v1.c           # readable version, with warnings on
	@mkdir -p build
	$(CC) -O2 -Wall -Wextra -o build/pygolf_v1 $<

test: all
	./run_tests.sh

clean:
	rm -rf build

.PHONY: all reference test clean
