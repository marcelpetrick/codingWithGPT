#include "LibrarySystem.h"
#include <iostream>

int main() {
    LibrarySystem librarySystem;

    std::cout << "Initial list of available books:" << std::endl;
    librarySystem.ListAvailableBooks();

    std::cout << "\nBorrowing 'The Great Gatsby':" << std::endl;
    librarySystem.BorrowBook("The Great Gatsby");

    std::cout << "\nList of available books after borrowing one:" << std::endl;
    librarySystem.ListAvailableBooks();

    std::cout << "\nReturning 'The Great Gatsby':" << std::endl;
    librarySystem.ReturnBook("The Great Gatsby");

    std::cout << "\nFinal list of available books:" << std::endl;
    librarySystem.ListAvailableBooks();

    return 0;
}
