#include <iostream>

void printLength(const char* str) {
    // Attempting to dereference str without checking if it's null
    int length = 0;
    while (*str != '\0') {
        ++length;
        ++str;
    }
    std::cout << "Length of the string is: " << length << std::endl;
}

int main() {
    const char* myString = nullptr; // Initialize pointer to null

    // This will lead to a crash due to null pointer dereference
    printLength(myString);

    return 0;
}
