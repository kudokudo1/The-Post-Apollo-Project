/* Disposable V2 lease continuation. Not an admission or production entrypoint. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

static int send_all(const char *p, size_t n) {
    while (n) {
        ssize_t w = write(STDOUT_FILENO, p, n);
        if (w < 0 && errno == EINTR) continue;
        if (w <= 0) return -1;
        p += w;
        n -= (size_t)w;
    }
    return 0;
}
int main(int argc, char **argv) {
    struct stat held, named, input;
    char *end;
    char byte;
    const char *gate = getenv("POST_APOLLO_GIT_MAP_SMOKE");
    if (argc != 4 || !gate || strcmp(gate, "CI_DISPOSABLE_ONLY")) return 1;
    errno = 0;
    long number = strtol(argv[1], &end, 10);
    if (errno || !*argv[1] || *end || number <= 2 || number > INT_MAX) return 1;
    int fd = (int)number;
    /* Python has already validated the database and obtained this very
       open file description. Never close/reopen the generation here. */
    if (fstat(fd, &held) || lstat(argv[2], &named) ||
        !S_ISDIR(held.st_mode) || !S_ISDIR(named.st_mode) ||
        held.st_uid != getuid() || named.st_uid != getuid() ||
        ((held.st_mode | named.st_mode) & 077) ||
        held.st_dev != named.st_dev || held.st_ino != named.st_ino ||
        fstat(STDIN_FILENO, &input) || !S_ISFIFO(input.st_mode) ||
        flock(fd, LOCK_SH | LOCK_NB)) return 1;
    size_t len = strlen(argv[3]);
    if (!len || len > 4096 || send_all(argv[3], len) || send_all("\n", 1)) return 1;
    ssize_t n;
    do { n = read(STDIN_FILENO, &byte, 1); } while (n < 0 && errno == EINTR);
    /* EOF releases the inherited descriptor at process exit. */
    return n == 0 ? 0 : 1;
}
