// File: main.cpp
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <netinet/in.h>
#include <unistd.h>

const int PORT = 80;

std::string create_homepage() {
    std::ostringstream html;
    html << "HTTP/1.1 200 OK\r\n";
    html << "Content-Type: text/html\r\n\r\n";
    html << "<html><head><title>My Homepage</title></head>";
    html << "<body><h1>titelzeile</h1><p>foo</p></body></html>";
    return html.str();
}

void handle_client(int client_socket) {
    char buffer[1024] = {0};
    read(client_socket, buffer, sizeof(buffer));
    std::cout << "Received request:\n" << buffer << std::endl;

    std::string response = create_homepage();
    send(client_socket, response.c_str(), response.size(), 0);
    close(client_socket);
    std::cout << "Response sent and connection closed.\n";
}

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    // Creating socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Socket failed");
        exit(EXIT_FAILURE);
    }

    // Forcefully attaching socket to the port 80
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Bind the socket to localhost port 80
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Bind failed (do you have root privileges?)");
        exit(EXIT_FAILURE);
    }
    std::cout << "Web server started on http://localhost:" << PORT << std::endl;

    if (listen(server_fd, 3) < 0) {
        perror("Listen");
        exit(EXIT_FAILURE);
    }

    while (true) {
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
            perror("Accept");
            continue;
        }
        std::thread(handle_client, new_socket).detach();
    }

    return 0;
}
