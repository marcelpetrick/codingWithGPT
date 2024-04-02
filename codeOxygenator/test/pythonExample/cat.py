from animal import Animal

class Cat(Animal):
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed

    def purr(self):
        print(f"{self.name}, the {self.breed}, is purring.")

if __name__ == "__main__":
    my_cat = Cat("Whiskers", "Siamese")
    my_cat.eat()
    my_cat.purr()
    my_cat.sleep()
