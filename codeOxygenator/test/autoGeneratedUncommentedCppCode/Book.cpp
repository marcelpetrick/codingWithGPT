#include "Book.h"

Book::Book(const std::string& title, const std::string& author)
    : title(title), author(author) {}

std::string Book::GetTitle() const {
    return title;
}

std::string Book::GetAuthor() const {
    return author;
}
