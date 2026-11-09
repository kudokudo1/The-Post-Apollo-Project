/* C3e-M: disposable signed NATIVE test host. No production service/keys.
 * A deliberately fixed, synthetic read-only status is emitted. This fixture
 * does NOT read the C3e-F SQLite witness, authorize supersession or release
 * credentials. It exists solely for kernel ELF + signed-role identity tests.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

static int decimal(const char *s, long maximum, long *out) {
    char *end = NULL;
    long n;
    if (s == NULL || s[0] == '\0') return 0;
    errno = 0;
    n = strtol(s, &end, 10);
    if (errno || end == s || *end != '\0' || n < 1 || n > maximum) return 0;
    *out = n;
    return 1;
}

static int digest(const char *s) {
    if (s == NULL || strlen(s) != 64) return 0;
    for (size_t i = 0; i < 64; i++) {
        if (!((s[i] >= '0' && s[i] <= '9') ||
              (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    }
    return 1;
}

static int same_credential(struct ucred a, long pid, long uid, long gid) {
    return a.pid == pid && a.uid == uid && a.gid == gid;
}

static void reply_one(int client, long pid, long uid, long gid,
                      const char *identity, long epoch, long sequence) {
    const char *request = "WITNESS-FLOOR-READ-V1";
    char payload[96] = {0};
    struct iovec iov = {.iov_base = payload, .iov_len = sizeof(payload)};
    char control[CMSG_SPACE(sizeof(struct ucred))] = {0};
    struct msghdr msg = {0};
    struct ucred connecting = {0};
    struct ucred sending = {0};
    socklen_t cred_size = sizeof(connecting);
    int sender_found = 0;
    int bad = 0;

    const char *failure = "{\"error\":\"REFUSED\",\"authorized\":false}";
    if (setsockopt(client, SOL_SOCKET, SO_PASSCRED, &(int){1}, sizeof(int)) != 0)
        bad = 1;
    if (getsockopt(client, SOL_SOCKET, SO_PEERCRED, &connecting, &cred_size) != 0
            || cred_size != sizeof(connecting))
        bad = 1;
    if (!same_credential(connecting, pid, uid, gid)) bad = 1;

    iov.iov_len = sizeof(payload);
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = control;
    msg.msg_controllen = sizeof(control);
    ssize_t received = recvmsg(client, &msg, 0);
    if (received < 0 || (msg.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) != 0)
        bad = 1;
    if (received != (ssize_t)strlen(request)
            || memcmp(payload, request, strlen(request)) != 0) bad = 1;

    for (struct cmsghdr *c = CMSG_FIRSTHDR(&msg); c != NULL;
         c = CMSG_NXTHDR(&msg, c)) {
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_CREDENTIALS
                && c->cmsg_len >= CMSG_LEN(sizeof(struct ucred))) {
            memcpy(&sending, CMSG_DATA(c), sizeof(sending));
            sender_found++;
        }
    }
    if (sender_found != 1 || !same_credential(sending, pid, uid, gid))
        bad = 1;

    char output[440] = {0};
    if (bad) {
        snprintf(output, sizeof(output), "%s", failure);
    } else {
        int count = snprintf(output, sizeof(output),
            "{\"schema\":\"postapollo.connections.c3ej.witness-read.v1\","
            "\"minimum_policy_epoch\":%ld,\"minimum_release_sequence\":%ld,"
            "\"enrollment_sha256\":\"%s\",\"authorized\":false,"
            "\"writable\":false}",
            epoch, sequence, identity);
        if (count < 0 || (size_t)count >= sizeof(output))
            snprintf(output, sizeof(output), "%s", failure);
    }
    (void)send(client, output, strlen(output), MSG_NOSIGNAL);
}

int main(int argc, char **argv) {
    long pid, uid, gid, epoch, sequence;
    struct sockaddr_un address = {0};
    int fd = -1;
    int client = -1;
    int result = 3;
    int has_socket = 0;

    if (argc != 9 || geteuid() != 0 || getuid() != 0 ||
            !decimal(argv[3], INT_MAX, &pid) ||
            !decimal(argv[4], INT_MAX, &uid) ||
            !decimal(argv[5], INT_MAX, &gid) ||
            !decimal(argv[7], INT_MAX, &epoch) ||
            !decimal(argv[8], INT_MAX, &sequence) ||
            !digest(argv[6]))
        return 2;
    if (strstr(argv[1], "/run/c3ek-ci-") != argv[1] ||
            strlen(argv[1]) >= sizeof(address.sun_path) ||
            strlen(argv[1]) < strlen("/run/c3ek-ci-123/public/witness.sock") ||
            strcmp(argv[1] + strlen(argv[1]) - strlen("/public/witness.sock"),
                   "/public/witness.sock") != 0)
        return 2;
    struct stat st;
    if (lstat(argv[1], &st) == 0 || errno != ENOENT)
        return 2;
    fd = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (fd < 0) goto done;
    if (setsockopt(fd, SOL_SOCKET, SO_PASSCRED, &(int){1}, sizeof(int)) != 0)
        goto done;
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, argv[1], strlen(argv[1]) + 1);
    if (bind(fd, (struct sockaddr *)&address, sizeof(address)) != 0)
        goto done;
    has_socket = 1;
    if (chown(argv[1], 0, (gid_t)gid) != 0 || chmod(argv[1], 0660) != 0)
        goto done;
    if (listen(fd, 1) != 0) goto done;
    struct timeval timeout = {.tv_sec = 9, .tv_usec = 0};
    (void)setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    puts("C3EM_READY // SIGNED_NATIVE_SYNTHETIC_READ_ONLY");
    fflush(stdout);
    client = accept4(fd, NULL, NULL, SOCK_CLOEXEC);
    if (client < 0) goto done;
    (void)setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    reply_one(client, pid, uid, gid, argv[6], epoch, sequence);
    result = 0;
done:
    if (client >= 0) close(client);
    if (fd >= 0) close(fd);
    if (has_socket) unlink(argv[1]);
    return result;
}
