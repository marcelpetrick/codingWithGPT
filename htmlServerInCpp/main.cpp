/**
 * @file main.cpp
 * @brief Minimal C++ Webserver serving a base64-encoded homepage.
 *
 * Built for Linux (requires root for port 80). No external libraries.
 */

#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <netinet/in.h>
#include <unistd.h>

constexpr int PORT = 80;

/**
 * @class WebContent
 * @brief Responsible for storing and decoding base64 homepage content.
 */
class WebContent {
public:
    /**
     * @return The homepage content, base64-encoded.
     */
    static std::string getHomepageBase64() {
        return  "PCFET0NUWVBFIEhUTUwgUFVCTElDICItLy9XM0MvL0RURCBIVE1MIDQuMDEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvVFIvaHRtbDQvc3RyaWN0LmR0ZCI+CjxodG1sPgogICA8aGVhZD4KICAgPHRpdGxlPgogICAgICAgICB+IG1hcmNlbHBldHJpY2suaXQgfgogICAgICA8L3RpdGxlPgogICAgICA8TUVUQSBuYW1lPSJkZXNjcmlwdGlvbiIgY29udGVudD0ibWFyY2VscGV0cmljay5pdCI+PE1FVEEgbmFtZT0ia2V5d29yZHMiIGNvbnRlbnQ9Im1hcmNlbHBldHJpY2suaXQgTWFyY2VsIFBldHJpY2sgSVQgY29tcHV0ZXIgc2NpZW5jZSI+CiAgIDwvaGVhZD4KCiAgIDxib2R5IHN0eWxlPSJiYWNrZ3JvdW5kLWNvbG9yOiBibGFjazsiPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlIb21lcGFnZSBvZiBNYXJjZWwgUGV0cmljay48L2JyPgoJCS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS08L2JyPgoJCUNvbnRhY3QgbWUgdmlhIG1haWw6IGFkZCA8Yj5tYWlsPC9iPiBwbHVzIDxiPkA8L2I+IHBsdXMgPGI+bWFyY2VscGV0cmljay5pdDwvYj48L2JyPgoJCS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS08L2JyPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlteSBibG9nIGZvciBzdHVmZiByZWxhdGVkIHRvIGNvbXB1dGUgc2NpZW5jZSwgSVQgYW5kIChhbmFsb2d1ZSkgcGhvdG9ncmFwaHk6IDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUiPiJzb2x1dGlvbnMgbm90IGNvZGUiPC9hPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlnaXRodWItYWNjb3VudDogPGEgaHJlZj0iaHR0cHM6Ly9naXRodWIuY29tL21hcmNlbHBldHJpY2siPmh0dHBzOi8vZ2l0aHViLmNvbS9tYXJjZWxwZXRyaWNrPC9hPgoJPC9wPgoJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlTaG9ydGN1dHMgdG8gcHVibGljbHkgYWNjZXNzaWJsZSBzbmlwcGV0cyAobWlub3JpdHkgb2YgdGhlbSAtIG1vc3QgaXMgaG9zdGVkIG9uIGdpdGh1Yik6PC9icj4KCQkqIFF0LXVpLWZpbGUtc29ydGVyOiA8YSBocmVmPSJ3cF9zb2x1dGlvbnNub3Rjb2RlLz9wYWdlX2lkPTEyMSI+cmlrdGlRdCBydXRtJm91bWw7bnN0ZXI8L2E+PC9icj4KCQkqIDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUvP3BhZ2VfaWQ9NDQ2Ij5RdFNjcm9iYmxlcjwvYT4tcG9ydCB0byBRdDU8L2JyPgoJCSogPGEgaHJlZj0id3Bfc29sdXRpb25zbm90Y29kZS8/cGFnZV9pZD0yMjciPmNvbnRhY3Qgc2hlZXQtY3JlYXRvcjwvYT4gKGJhc2gpIC8vIDxhIGhyZWY9IndwX3NvbHV0aW9uc25vdGNvZGUvP3BhZ2VfaWQ9NTc5Ij5kb0Vpcy5zaDwvYT4gKGNvbnZlcnQgYWxsIFRJRi1uZWdhdGl2ZXM7IGJhc2gpPC9icj4KCQk8L3A+CgkJPHAgc3R5bGU9ImNvbG9yOiB3aGl0ZTsgZm9udC1zaXplOiAxMnB0OyBmb250LWZhbWlseTogQXJpYWwsIHNhbnMtc2VyaWY7Ij4KCQlmbGlja3I6IHNlbGVjdGlvbiBvZiBzb21lIDxhIGhyZWY9Imh0dHBzOi8vd3d3LmZsaWNrci5jb20vcGhvdG9zL2V1ZGFpbW9uaWUvIj5waG90b3M8L2E+Cgk8L3A+Cgk8cCBzdHlsZT0iY29sb3I6IHdoaXRlOyBmb250LXNpemU6IDEycHQ7IGZvbnQtZmFtaWx5OiBBcmlhbCwgc2Fucy1zZXJpZjsiPgoJCVBob3RvIFNwaGVyZSBWaWV3ZXI6IDxhIGhyZWY9Imh0dHA6Ly9tYXJjZWxwZXRyaWNrLmJwbGFjZWQubmV0L1Bob3RvU3BoZXJlVmlld2VyLyI+aW50ZXJhY3RpdmUgcGFub3JhbWEtZXhhbXBsZXMgb2Ygc29tZSBldXJvcGVhbiB0b3duczwvYT4KCTwvcD4KCTwvYm9keT4KPC9odG1sPgo=";
    }

    /**
     * @param input Base64-encoded string.
     * @return Decoded plain string.
     */
    static std::string decodeBase64(const std::string& input) {
        std::string output;
        std::vector<int> T(256, -1);
        for (int i = 0; i < 64; i++)
            T["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[i]] = i;

        int val = 0, valb = -8;
        for (unsigned char c : input) {
            if (T[c] == -1) break;
            val = (val << 6) + T[c];
            valb += 6;
            if (valb >= 0) {
                output.push_back(char((val >> valb) & 0xFF));
                valb -= 8;
            }
        }
        return output;
    }
};

/**
 * @class WebServer
 * @brief Simple single-threaded HTTP server on localhost:80
 */
class WebServer {
public:
    void run() {
        setupSocket();
        std::cout << "Web server started at http://localhost:" << PORT << std::endl;

        while (true) {
            sockaddr_in client_addr;
            socklen_t addrlen = sizeof(client_addr);
            int client_socket = accept(server_fd_, (sockaddr*)&client_addr, &addrlen);
            if (client_socket >= 0)
                std::thread(&WebServer::handleClient, this, client_socket).detach();
        }
    }

private:
    int server_fd_ = -1;

    void setupSocket() {
        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ < 0) {
            perror("socket");
            exit(EXIT_FAILURE);
        }

        int opt = 1;
        if (setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)) < 0) {
            perror("setsockopt");
            exit(EXIT_FAILURE);
        }

        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(PORT);

        if (bind(server_fd_, (sockaddr*)&address, sizeof(address)) < 0) {
            perror("bind");
            exit(EXIT_FAILURE);
        }

        if (listen(server_fd_, 3) < 0) {
            perror("listen");
            exit(EXIT_FAILURE);
        }
    }

    void handleClient(int client_socket) {
        char buffer[1024] = {0};
        read(client_socket, buffer, sizeof(buffer));
        std::cout << "Received request:\n" << buffer << std::endl;

        std::string html = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n";
        html += WebContent::decodeBase64(WebContent::getHomepageBase64());

        send(client_socket, html.c_str(), html.size(), 0);
        close(client_socket);
        std::cout << "Response sent and connection closed.\n";
    }
};

/**
 * @brief Entry point.
 */
int main() {
    WebServer server;
    server.run();
    return 0;
}
