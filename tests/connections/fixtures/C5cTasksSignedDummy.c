/* C5c CI-only TASKS dummy client. No TASKS data, file or keys. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2) return 4;
    char *end = NULL;
    long fd = strtol(argv[1], &end, 10);
    if (!end || *end || fd < 3 || fd > 100000) return 4;
    char *line = NULL;
    size_t size = 0;
    char reply[2048];
    int status = 0;
    while (getline(&line, &size, stdin) != -1) {
        size_t n = strlen(line);
        if (n && line[n - 1] == '\n') --n;
        if (!n || n > 1024) { status = 5; break; }
        if (send((int)fd, line, n, 0) != (ssize_t)n) {
            status = 6; break;
        }
        ssize_t received = recv((int)fd, reply, sizeof reply - 1, 0);
        if (received <= 0) { status = 7; break; }
        reply[received] = 0;
        if (fputs(reply, stdout) == EOF || fputc('\n', stdout) == EOF
                || fflush(stdout) == EOF) {
            status = 8; break;
        }
    }
    free(line);
    return status;
}
