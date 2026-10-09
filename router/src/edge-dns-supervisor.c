#define _POSIX_C_SOURCE 200809L
#define _GNU_SOURCE
#include <errno.h>
#include <dirent.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;

static void signal_received(int signo) { interrupted = signo; }

static int64_t monotonic_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) return -1;
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void pause_ms(long milliseconds) {
    struct timespec t = { .tv_sec = milliseconds / 1000,
                          .tv_nsec = (milliseconds % 1000) * 1000000 };
    while (nanosleep(&t, &t) < 0 && errno == EINTR && !interrupted) {}
}

/* Linux subreaper adopts orphaned descendants, even after setsid().
 * Enumerate only our direct children in /proc: never signal unrelated PIDs.
 * The caller must retain the original leader as a zombie until group cleanup.
 */
static int signal_direct_children(int signo) {
    DIR *dir = opendir("/proc");
    if (!dir) {
        perror("supervisor: open /proc");
        return -1;
    }
    int failed = 0;
    struct dirent *entry;
    pid_t self = getpid();
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] < '0' || entry->d_name[0] > '9') continue;
        char *endptr;
        errno = 0;
        long number = strtol(entry->d_name, &endptr, 10);
        if (errno || *endptr || number <= 0 || number > INT_MAX || number == self)
            continue;

        char path[64];
        if (snprintf(path, sizeof(path), "/proc/%ld/status", number) >= (int)sizeof(path))
            continue;
        FILE *status = fopen(path, "r");
        if (!status) continue;   /* The process may have exited mid-scan. */
        long parent = -1;
        char line[256];
        while (fgets(line, sizeof(line), status)) {
            if (strncmp(line, "PPid:", 5) == 0) {
                char *tail;
                errno = 0;
                parent = strtol(line + 5, &tail, 10);
                if (errno || tail == line + 5) parent = -1;
                break;
            }
        }
        fclose(status);
        if (parent != (long)self) continue;
        if (kill((pid_t)number, signo) != 0 && errno != ESRCH) {
            perror("supervisor: signal adopted child");
            failed = 1;
        }
    }
    if (closedir(dir) != 0) failed = 1;
    return failed ? -1 : 0;
}

static int reap_available(pid_t leader, int *status, int *leader_reaped,
                          int *children_alive) {
    for (;;) {
        int tmpstatus;
        pid_t reaped = waitpid(-1, &tmpstatus, WNOHANG);
        if (reaped > 0) {
            if (reaped == leader) {
                *status = tmpstatus;
                *leader_reaped = 1;
            }
            continue;
        }
        if (reaped == 0) {
            *children_alive = 1;
            return 0;
        }
        if (errno == EINTR) continue;
        if (errno == ECHILD) {
            *children_alive = 0;
            return 0;
        }
        perror("supervisor: waitpid");
        return -1;
    }
}

static int supervised_cleanup(pid_t group, pid_t leader, int *status) {
    if (kill(-group, SIGTERM) < 0 && errno != ESRCH)
        perror("supervisor: SIGTERM process group");
    pause_ms(200);
    if (kill(-group, SIGKILL) < 0 && errno != ESRCH)
        perror("supervisor: SIGKILL process group");

    int64_t start = monotonic_ms();
    if (start < 0) return 1;
    int64_t end = start + 3000;
    int leader_reaped = 0;
    for (;;) {
        /* A detached descendant might be adopted only after its parent dies.
         * Rescan each iteration and reap adopted children before completion.
         */
        if (signal_direct_children(SIGKILL) != 0) return 1;
        int children_alive = 0;
        if (reap_available(leader, status, &leader_reaped, &children_alive) != 0)
            return 1;
        if (!children_alive) return leader_reaped ? 0 : 1;
        int64_t now = monotonic_ms();
        if (now < 0 || now >= end) {
            fputs("supervisor: children not reaped within cleanup deadline\n", stderr);
            return 1;
        }
        pause_ms(25);
    }
}

int main(int argc, char **argv) {
    if (argc < 4 || strcmp(argv[2], "--") != 0 || argv[3][0] != '/') {
        fputs("usage: edge-dns-supervisor SECONDS -- /absolute/command [args...]\n", stderr);
        return 2;
    }
    char *endptr = NULL;
    errno = 0;
    long seconds = strtol(argv[1], &endptr, 10);
    if (errno || !endptr || *endptr || seconds < 1 || seconds > 120) {
        fputs("supervisor: timeout must be 1..120 seconds\n", stderr);
        return 2;
    }
    if (prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0) {
        perror("supervisor: subreaper required");
        return 125;
    }
    struct sigaction action = {0};
    sigemptyset(&action.sa_mask);
    action.sa_handler = signal_received;
    if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL) ||
        sigaction(SIGHUP, &action, NULL)) {
        perror("supervisor: sigaction");
        return 125;
    }
    int ready_pipe[2];
    if (pipe(ready_pipe) != 0) { perror("supervisor: pipe"); return 125; }
    pid_t parent_pid = getpid();
    pid_t child = fork();
    if (child < 0) { perror("supervisor: fork"); return 125; }
    if (child == 0) {
        close(ready_pipe[0]);
        struct sigaction restore = {0};
        restore.sa_handler = SIG_DFL;
        sigemptyset(&restore.sa_mask);
        sigaction(SIGINT, &restore, NULL);
        sigaction(SIGTERM, &restore, NULL);
        sigaction(SIGHUP, &restore, NULL);
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) != 0 ||
            getppid() != parent_pid || setsid() < 0) _exit(126);
        char token = 'R';
        if (write(ready_pipe[1], &token, 1) != 1) _exit(126);
        close(ready_pipe[1]);
        close(9);  /* The Guard must obtain its own flock descriptor. */
        execv(argv[3], &argv[3]);
        perror("supervisor: execv");
        _exit(127);
    }
    close(ready_pipe[1]);
    char token = 0;
    ssize_t got;
    do { got = read(ready_pipe[0], &token, 1); } while (got < 0 && errno == EINTR);
    close(ready_pipe[0]);
    int failed_setup = (got != 1 || token != 'R');
    int64_t start = monotonic_ms();
    int timed_out = 0;
    int status = 0;
    if (start < 0) failed_setup = 1;
    while (!failed_setup && !interrupted) {
        siginfo_t info = {0};
        if (waitid(P_PID, child, &info, WEXITED | WNOHANG | WNOWAIT) != 0) {
            if (errno == EINTR) continue;
            perror("supervisor: waitid");
            failed_setup = 1;
            break;
        }
        if (info.si_pid == child) break;
        if (monotonic_ms() - start >= seconds * 1000) {
            timed_out = 1;
            break;
        }
        pause_ms(25);
    }
    /* Leader is intentionally not reaped until after process-group signals. */
    if (failed_setup && got != 1) {
        kill(child, SIGKILL);
        if (waitpid(child, &status, 0) < 0) return 125;
        return 125;
    }
    if (supervised_cleanup(child, child, &status) != 0) return 125;
    if (timed_out) { fputs("SUPERVISOR=TIMEOUT\n", stderr); return 124; }
    if (interrupted) { fputs("SUPERVISOR=INTERRUPTED\n", stderr); return 128 + interrupted; }
    if (failed_setup) { fputs("SUPERVISOR=SETUP_FAILED\n", stderr); return 125; }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return 125;
}
