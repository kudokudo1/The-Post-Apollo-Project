/* C5d disposable REVIEWER only. Receives commands on stdin from a
   CI fixture; THIS IS NOT HUMAN CONSENT. Does not touch actual keys or TASKS. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int review_command(const char *line) {
    const char *commands[] = {
        "\"op\":\"bindClient\"", "\"op\":\"approve\"",
        "\"op\":\"revoke\"", "\"op\":\"shutdown\""
    };
    for (size_t i = 0; i < sizeof(commands) / sizeof(commands[0]); i++)
        if (strstr(line, commands[i])) return 1;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) return 4;
    char *end = NULL;
    long fd = strtol(argv[1], &end, 10);
    if (!end || *end || fd < 3 || fd > 100000) return 4;
    char *line = NULL;
    size_t capacity = 0;
    char response[2048];
    int status = 0;
    while (getline(&line, &capacity, stdin) != -1) {
        size_t n = strlen(line);
        if (n && line[n-1] == '\n') --n;
        if (n == 0 || n > 1024 || !review_command(line)) {
            status = 5; break;
        }
        if (send((int)fd, line, n, 0) != (ssize_t)n) {
            status = 6; break;
        }
        ssize_t len = recv((int)fd, response, sizeof(response)-1, 0);
        if (len <= 0) { status = 7; break; }
        response[len] = 0;
        if (fputs(response, stdout) == EOF || fputc('\n', stdout) == EOF
                || fflush(stdout) == EOF) {
            status = 8; break;
        }
    }
    free(line);
    return status;
}
