/*
 * Post Apollo Hospital // native Room authorization request client
 *
 * This deliberately small client is the executable that a ROOT-OWNED
 * C5-H2 issuer must pin by its real /proc/<pid>/exe SHA-256. Quickshell never
 * sees a grant or private key and cannot choose a socket, writer, or policy.
 *
 * SOURCE ONLY. The fixed installed executable and issuer service do not exist
 * on user hosts until separately approved native installation.
 * Copyright: project source; no third-party JSON dependency.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#define CLIENT_PATH "/usr/libexec/post-apollo/hospital/hospital-room-request"
#define ISSUER_SOCKET "/run/post-apollo/hospital/issuer.sock"
#define READY_FRAME "{\"schema\":\"postapollo.connections.hospital-native-ready.v1\",\"status\":\"READY\"}"
#define CLIENT_SCHEMA "postapollo.connections.hospital.native-request.v1"
#define MAX_PACKET 4096

static int refused(const char *code) {
    fprintf(stderr, "HOSPITAL_BACKEND_NOT_READY // %s\n", code);
    return 2;
}

static int secure_root_directory(const char *path) {
    struct stat st;
    return lstat(path, &st) == 0 && S_ISDIR(st.st_mode)
        && st.st_uid == 0 && (st.st_mode & (S_IWGRP | S_IWOTH)) == 0;
}

static int installed_client_trusted(void) {
    struct stat installed, running;
    if (!secure_root_directory("/usr")
        || !secure_root_directory("/usr/libexec")
        || !secure_root_directory("/usr/libexec/post-apollo")
        || !secure_root_directory("/usr/libexec/post-apollo/hospital"))
        return 0;
    if (lstat(CLIENT_PATH, &installed) != 0
        || !S_ISREG(installed.st_mode)
        || installed.st_uid != 0
        || (installed.st_mode & (S_IWGRP | S_IWOTH)) != 0
        || (installed.st_mode & S_IXUSR) == 0
        || stat("/proc/self/exe", &running) != 0)
        return 0;
    return installed.st_dev == running.st_dev && installed.st_ino == running.st_ino;
}

static int installed_issuer_socket_trusted(void) {
    struct stat st;
    if (!secure_root_directory("/run")
        || !secure_root_directory("/run/post-apollo")
        || !secure_root_directory("/run/post-apollo/hospital"))
        return 0;
    return lstat(ISSUER_SOCKET, &st) == 0
        && S_ISSOCK(st.st_mode) && st.st_uid == 0
        && (st.st_mode & S_IWOTH) == 0;
}

static int valid_room(const char *id) {
    size_t n;
    if (!id || (n = strlen(id)) == 0 || n > 160)
        return 0;
    for (size_t i = 0; i < n; ++i) {
        const char c = id[i];
        if (!((c >= 'A' && c <= 'Z')
            || (c >= 'a' && c <= 'z')
            || (c >= '0' && c <= '9')
            || c == '.' || c == '_' || c == ':'
            || c == '/' || c == '-'))
            return 0;
    }
    return 1;
}

static int packet_read(int fd, char *dst, size_t capacity) {
    struct iovec iov = { .iov_base = dst, .iov_len = capacity - 1 };
    struct msghdr msg;
    memset(&msg, 0, sizeof(msg));
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    ssize_t n = recvmsg(fd, &msg, 0);
    if (n <= 0 || (msg.msg_flags & (MSG_TRUNC | MSG_CTRUNC))
        || (size_t)n >= capacity)
        return -1;
    for (ssize_t i = 0; i < n; ++i) {
        if ((unsigned char)dst[i] < 0x20
            || (unsigned char)dst[i] > 0x7e)
            return -1;
    }
    dst[n] = '\0';
    return (int)n;
}

static int send_exact_packet(int fd, const char *text) {
    size_t n = strlen(text);
    return n > 0 && n < MAX_PACKET
        && send(fd, text, n, MSG_NOSIGNAL) == (ssize_t)n;
}

/* Caller must establish root-owned endpoint and kernel UID BEFORE this step.
 * The test fixture uses a socketpair here; production main does not.
 */
static int perform_exchange(int fd, const char *action, const char *room,
                            char *response, size_t response_size) {
    char incoming[MAX_PACKET + 1];
    char request[512];
    if ((!strcmp(action, "TRASH") && valid_room(room))
        || (!strcmp(action, "RESTORE") && valid_room(room))) {
        /* permitted verb */
    } else {
        return -1;
    }
    if (packet_read(fd, incoming, sizeof(incoming)) < 0
        || strcmp(incoming, READY_FRAME) != 0)
        return -1;
    int n = snprintf(request, sizeof(request),
        "{\"action\":\"%s\",\"roomId\":\"%s\",\"schema\":\"%s\"}",
        action, room, CLIENT_SCHEMA);
    if (n <= 0 || (size_t)n >= sizeof(request)
        || !send_exact_packet(fd, request))
        return -1;
    if (packet_read(fd, response, response_size) < 0)
        return -1;
    /* The trusted issuer returns a minimal, source-verified COMMITTED JSON
     * receipt. The QML consumer separately validates the exact room, action,
     * revision, no-Burn status and original preservation before UI refresh.
     */
    if (response[0] != '{'
        || !strstr(response, "\"status\":\"COMMITTED\"")
        || !strstr(response, "\"schema\":\"postapollo.connections.hospital-native-issuer-response.v1\""))
        return -1;
    return 0;
}

#ifndef PA_HOSPITAL_CLIENT_UNIT_TEST
int main(int argc, char **argv) {
    if (argc != 2 && argc != 3)
        return refused("EXPECTED_ACTION_AND_EXACT_ROOM");
    if (!installed_client_trusted())
        return refused("PINNED_NATIVE_EXECUTABLE_NOT_INSTALLED");
    if (!installed_issuer_socket_trusted())
        return refused("TRUSTED_ISSUER_SOCKET_UNAVAILABLE");

    if (argc == 2 && strcmp(argv[1], "--check") == 0) {
        puts("{\"schema\":\"postapollo.hospital.native-client.v1\",\"status\":\"INSTALLED\"}");
        return 0;
    }
    if (argc != 3
        || (strcmp(argv[1], "TRASH") && strcmp(argv[1], "RESTORE"))
        || !valid_room(argv[2]))
        return refused("INVALID_ROOM_OR_ACTION");

    int sock = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (sock < 0)
        return refused("SEQPACKET_NOT_AVAILABLE");
    struct timeval timeout = { .tv_sec = 65, .tv_usec = 0 };
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) != 0
        || setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) != 0) {
        close(sock);
        return refused("SOCKET_TIMEOUT_UNAVAILABLE");
    }
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (strlen(ISSUER_SOCKET) >= sizeof(addr.sun_path)) {
        close(sock);
        return refused("ISSUER_PATH_INVALID");
    }
    memcpy(addr.sun_path, ISSUER_SOCKET, strlen(ISSUER_SOCKET) + 1);
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        close(sock);
        return refused("PROTECTED_ISSUER_UNAVAILABLE");
    }
    struct ucred peer;
    socklen_t peer_size = sizeof(peer);
    if (getsockopt(sock, SOL_SOCKET, SO_PEERCRED,
                   &peer, &peer_size) != 0 || peer_size != sizeof(peer)
        || peer.uid != 0 || peer.pid <= 1) {
        close(sock);
        return refused("NONROOT_ISSUER_PEER");
    }

    char result[MAX_PACKET + 1];
    int okay = perform_exchange(sock, argv[1], argv[2], result, sizeof(result));
    struct ucred after;
    socklen_t after_size = sizeof(after);
    if (okay == 0 && (getsockopt(sock, SOL_SOCKET, SO_PEERCRED,
                  &after, &after_size) != 0 || after_size != sizeof(after)
                  || after.pid != peer.pid || after.uid != peer.uid
                  || after.gid != peer.gid))
        okay = -1;
    close(sock);
    if (okay != 0)
        return refused("AUTHORIZATION_REFUSED_OR_UNVERIFIED");
    puts(result);
    return 0;
}
#endif
