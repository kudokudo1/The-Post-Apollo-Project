/*
 * Disposable source-level native C5-H2 client protocol regression.
 * Only a local SOCK_SEQPACKET socketpair, no real issuer, key or Room DB.
 */
#define PA_HOSPITAL_CLIENT_UNIT_TEST 1
#include "../../services/hospital/native/hospital_room_request_client.c"
#include <assert.h>
#include <sys/wait.h>

static void one_case(const char *ready, const char *result, int expected) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sockets) == 0);
    pid_t pid = fork();
    assert(pid >= 0);
    if (pid == 0) {
        close(sockets[0]);
        if (ready)
            assert(send_exact_packet(sockets[1], ready));
        char request[512];
        if (expected == 0 || (ready && strcmp(ready, READY_FRAME) == 0)) {
            int got = packet_read(sockets[1], request, sizeof(request));
            assert(got > 0);
            assert(strcmp(request, "{\"action\":\"TRASH\",\"roomId\":\"room_1\",\"schema\":\"postapollo.connections.hospital.native-request.v1\"}") == 0);
            if (result)
                assert(send_exact_packet(sockets[1], result));
        }
        close(sockets[1]);
        _exit(0);
    }
    close(sockets[1]);
    char response[MAX_PACKET + 1];
    int rc = perform_exchange(sockets[0], "TRASH", "room_1",
                              response, sizeof(response));
    assert((rc == 0) == (expected == 0));
    if (expected == 0)
        assert(strstr(response, "\"roomId\":\"room_1\""));
    close(sockets[0]);
    int child_status=0;
    assert(waitpid(pid, &child_status, 0) == pid);
    assert(WIFEXITED(child_status) && WEXITSTATUS(child_status) == 0);
}
int main(void) {
    assert(valid_room("a1.2:/-test"));
    assert(!valid_room(""));
    assert(!valid_room("space id"));
    assert(!valid_room("not\"escaped"));
    assert(!valid_room("new\nline"));
    char overlong[200];
    memset(overlong, 'x', sizeof(overlong));
    overlong[sizeof(overlong) - 1] = 0;
    assert(!valid_room(overlong));

    const char *committed =
        "{\"action\":\"TRASH\",\"burnAllowed\":false,\"originalPreserved\":true,"
        "\"revision\":2,\"roomId\":\"room_1\","
        "\"schema\":\"postapollo.connections.hospital-native-issuer-response.v1\","
        "\"status\":\"COMMITTED\"}";
    one_case(READY_FRAME, committed, 0);
    one_case("{\"status\":\"READY\"}", NULL, -1);
    one_case(READY_FRAME,
        "{\"schema\":\"postapollo.connections.hospital-native-issuer-response.v1\","
        "\"status\":\"REFUSED\"}", -1);

    /* These unit tests never install the pinned root-only executable.
     * Native production main and all root trust gates remain unchanged. */
    assert(!installed_client_trusted());
    assert(!installed_issuer_socket_trusted());
    puts("HOSPITAL C5-H2 NATIVE CLIENT // PASS // SEQPACKET READY, exact request, receipt, refusal");
    return 0;
}
