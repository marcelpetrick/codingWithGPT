def check():
    for v in range(10):
        if v == 3:
            print("three")
        else:
            if v < 3:
                print("small")
            else:
                if v != 7:
                    print("big")
                else:
                    print("seven")


check()
