#ifndef LIBRARYSYSTEM_H
#define LIBRARYSYSTEM_H

#include "Library.h"
#include <string>

class LibrarySystem {
public:
    LibrarySystem();
    void BorrowBook(const std::string& title);
    void ReturnBook(const std::string& title);
    void ListAvailableBooks() const;
private:
    Library library;
    std::vector<Book> borrowedBooks;
};

#endif // LIBRARYSYSTEM_H
