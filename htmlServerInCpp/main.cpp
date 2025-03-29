// File: main.cpp
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <netinet/in.h>
#include <unistd.h>

const int PORT = 80;

std::string getHomepageSourceAsBase64() {
    std::ostringstream source;
    source << "PCFET0NUWVBFIEhUTUwgUFVCTElDICItLy9XM0MvL0RURCBIVE1MIDQuMDEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvVFIvaHRtbDQvc3RyaWN0LmR0ZCI+CjxodG1sPgogICA8aGVhZD4KICAgPHRpdGxlPgogICAgICAgICB+IG1hcmNlbHBldHJpY2suaXQgfgogICAgICA8L3RpdGxlPgogICAgICA8TUVUQSBuYW1lPSJkZXNjcmlwdGlvbiIgY29udGVudD0ibWFyY2VscGV0cmljay5pdCI+PE1FVEEgbmFtZT0ia2V5d29yZHMiIGNvbnRlbnQ9Im1hcmNlbHBldHJpY2suaXQgTWFyY2VsIFBldHJpY2sgSVQgY29tcHV0ZXIgc2NpZW5jZSI+CiAgIDwvaGVhZD4KCiAgIDxib2R5IHN0eWxlPSJiYWNrZ3JvdW5kLWNvbG9yOiBibGFjazsiPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlIb21lcGFnZSBvZiBNYXJjZWwgUGV0cmljay48L2JyPgoJCS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS08L2JyPgoJCUNvbnRhY3QgbWUgdmlhIG1haWw6IGFkZCA8Yj5tYWlsPC9iPiBwbHVzIDxiPkA8L2I+IHBsdXMgPGI+bWFyY2VscGV0cmljay5pdDwvYj48L2JyPgoJCS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS08L2JyPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlteSBibG9nIGZvciBzdHVmZiByZWxhdGVkIHRvIGNvbXB1dGUgc2NpZW5jZSwgSVQgYW5kIChhbmFsb2d1ZSkgcGhvdG9ncmFwaHk6IDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUiPiJzb2x1dGlvbnMgbm90IGNvZGUiPC9hPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlnaXRodWItYWNjb3VudDogPGEgaHJlZj0iaHR0cHM6Ly9naXRodWIuY29tL21hcmNlbHBldHJpY2siPmh0dHBzOi8vZ2l0aHViLmNvbS9tYXJjZWxwZXRyaWNrPC9hPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlTaG9ydGN1dHMgdG8gcHVibGljbHkgYWNjZXNzaWJsZSBzbmlwcGV0cyAobWlub3JpdHkgb2YgdGhlbSAtIG1vc3QgaXMgaG9zdGVkIG9uIGdpdGh1Yik6PC9icj4KCQkqIFF0LXVpLWZpbGUtc29ydGVyOiA8YSBocmVmPSJ3cF9zb2x1dGlvbnNub3Rjb2RlLz9wYWdlX2lkPTEyMSI+cmlrdGlRdCBydXRtJm91bWw7bnN0ZXI8L2E+PC9icj4KCQkqIDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUvP3BhZ2VfaWQ9NDQ2Ij5RdFNjcm9iYmxlcjwvYT4tcG9ydCB0byBRdDU8L2JyPgoJCSogPGEgaHJlZj0id3Bfc29sdXRpb25zbm90Y29kZS8/cGFnZV9pZD0yMjciPmNvbnRhY3Qgc2hlZXQtY3JlYXRvcjwvYT4gKGJhc2gpIC8vIDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUvP3BhZ2VfaWQ9NTc5Ij5kb0Vpcy5zaDwvYT4gKGNvbnZlcnQgYWxsIFRJRi1uZWdhdGl2ZXM7IGJhc2gpPC9icj4KCQk8L3A+CgkJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlmbGlja3I6IHNlbGVjdGlvbiBvZiBzb21lIDxhIGhyZWY9Imh0dHBzOi8vd3d3LmZsaWNrci5jb20vcGhvdG9zL2V1ZGFpbW9uaWUvIj5waG90b3M8L2E+Cgk8L3A+Cgk8cCBzdHlsZT0iY29sb3I6IHdoaXRlOyBmb250LXNpemU6IDEycHQ7IGZvbnQtZmFtaWx5OiBBcmlhbCwgc2Fucy1zZXJpZjsiPgoJCVBob3RvIFNwaGVyZSBWaWV3ZXI6IDxhIGhyZWY9Imh0dHA6Ly9tYXJjZWxwZXRyaWNrLmJwbGFjZWQubmV0L1Bob3RvU3BoZXJlVmlld2VyLyI+aW50ZXJhY3RpdmUgcGFub3JhbWEtZXhhbXBsZXMgb2Ygc29tZSBldXJvcGVhbiB0b3duczwvYT4KCTwvcD4KCTwvYm9keT4KPC9odG1sPgo=";
    return source.str();
}

std::string base64_decode(const std::string &in) {
    std::string out;
    std::vector<int> T(256, -1);
    for (int i = 0; i < 64; i++) {
        T["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[i]] = i;
    }
    int val = 0, valb = -8;
    for (unsigned char c : in) {
        if (T[c] == -1) break;
        val = (val << 6) + T[c];
        valb += 6;
        if (valb >= 0) {
            out.push_back(char((val >> valb) & 0xFF));
            valb -= 8;
        }
    }
    return out;
}

std::string create_homepage() {
    std::ostringstream html;
    html << "HTTP/1.1 200 OK\r\n";
    html << "Content-Type: text/html\r\n\r\n";
    std::string base64 = getHomepageSourceAsBase64();
    html << base64_decode(base64);
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
