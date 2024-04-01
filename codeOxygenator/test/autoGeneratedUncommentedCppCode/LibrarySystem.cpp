#include "LibrarySystem.h"
#include <iostream>

LibrarySystem::LibrarySystem() {
    // Pre-populate the library with some books
    library.AddBook(Book("The Great Gatsby", "F. Scott Fitzgerald"));
    library.AddBook(Book("1984", "George Orwell"));
}

void LibrarySystem::BorrowBook(const std::string& title) {
    for (const auto& book : library.GetBooks()) {
        if (book.GetTitle() == title) {
            borrowedBooks.push_back(book);
            std::cout << "Borrowed: " << title << std::endl;
            return;
        }
    }
    std::cout << "Book not found: " << title << std::endl;
}

void LibrarySystem::ReturnBook(const std::string& title) {
    borrowedBooks.erase(std::remove_if(borrowedBooks.begin(), borrowedBooks.end(), [&](const Book& book) {
        return book.GetTitle() == title;
    }), borrowedBooks.end());
    std::cout << "Returned: " << title << std::endl;
}

void LibrarySystem::ListAvailableBooks() const {
    std::cout << "Available books:" << std::endl;
    for (const auto& book : library.GetBooks()) {
        std::cout << "- " << book.GetTitle() << " by " << book.GetAuthor() << std::endl;
    }
}
