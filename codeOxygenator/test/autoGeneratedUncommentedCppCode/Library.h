#include "Library.h"

void Library::AddBook(const Book& book) {
    books.push_back(book);
}

const std::vector<Book>& Library::GetBooks() const {
    return books;
}
