def grid():
    for r in range(3):
        for c in range(3):
            if r % 2 == 0:
                print(r * 10 + c)
            else:
                print("odd")


grid()
