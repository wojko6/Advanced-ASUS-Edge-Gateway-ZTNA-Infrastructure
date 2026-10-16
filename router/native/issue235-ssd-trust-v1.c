/*
 * Issue #235 / JFFS-13 — native mount identity probe v1 (READ ONLY).
 *
 * This is a fail-closed diagnostic prototype, NOT a deployable mode repair.
 * It has no chmod/fchmod, mount, or filesystem-write code path.
 * Any success still exits 2 (HOLD); exit 3 denotes rejected evidence.
 *
 * Production CLI: issue235-ssd-trust-v1 --check ROUTER_DATA|ENTWARE
 * Lab-only CLI (compile with ISSUE235_TEST_BUILD):
 *   issue235-ssd-trust-v1 --lab-check /absolute/fixture /fixture/mountinfo
 *
 * The lab flag never exists in the normal build.
 */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define TARGET_DATA "/tmp/mnt/ROUTER_DATA"
#define TARGET_ENTWARE "/tmp/mnt/ENTWARE"
#define PROC_MOUNTINFO "/proc/self/mountinfo"
#define HOLD 2
#define REJECT 3

struct handles {
    int root, tmp, mnt, leaf;
};

static void close_handles(struct handles *h) {
    if (h->leaf >= 0) close(h->leaf);
    if (h->mnt >= 0) close(h->mnt);
    if (h->tmp >= 0) close(h->tmp);
    if (h->root >= 0) close(h->root);
}

static bool same_inode(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static bool rooted_dir(const struct stat *st) {
    return S_ISDIR(st->st_mode) && st->st_uid == 0 && st->st_gid == 0;
}

static bool leaf_owner_ok(const struct stat *st, bool synthetic) {
#ifdef ISSUE235_TEST_BUILD
    if (synthetic) return S_ISDIR(st->st_mode) &&
        st->st_uid == geteuid() && st->st_gid == getegid();
#else
    (void)synthetic;
#endif
    return rooted_dir(st);
}

static bool no_world_write(const struct stat *st) {
    return (st->st_mode & S_IWOTH) == 0;
}

static bool valid_absolute(const char *p) {
    if (!p || p[0] != '/' || p[1] == '\0') return false;
    if (strlen(p) >= PATH_MAX) return false;
    if (strstr(p, "//") || strchr(p, '\n') || strchr(p, '\r')) return false;
    /* No components that can silently change traversal semantics. */
    const char *cur = p + 1;
    while (*cur) {
        const char *end = strchr(cur, '/');
        size_t len = end ? (size_t)(end - cur) : strlen(cur);
        if (len == 0 || (len == 1 && cur[0] == '.') ||
            (len == 2 && cur[0] == '.' && cur[1] == '.')) return false;
        if (!end) return true;
        cur = end + 1;
    }
    return false;
}

static int open_chain(const char *path, struct handles *h,
                      struct stat *parent, struct stat *leaf) {
    char copy[PATH_MAX];
    if (!valid_absolute(path)) return -1;
    memcpy(copy, path, strlen(path) + 1);
    int base = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (base < 0) return -1;
    h->root = base;
    char *save = NULL;
    char *tok = strtok_r(copy + 1, "/", &save);
    int depth = 0;
    int prev = base;
    struct stat st;
    while (tok) {
        int fd = openat(prev, tok, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        if (fd < 0 || fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode)) {
            if (fd >= 0) close(fd);
            return -1;
        }
        depth++;
        char *next = strtok_r(NULL, "/", &save);
        if (next) {
            if (depth == 1) h->tmp = fd;
            else if (depth == 2) h->mnt = fd;
            else { close(fd); return -1; }
        } else {
            if (depth != 3) { close(fd); return -1; }
            h->leaf = fd;
            *leaf = st;
            if (fstat(prev, parent) != 0) return -1;
        }
        prev = fd;
        tok = next;
    }
    if (depth != 3 || h->leaf < 0 || h->tmp < 0 || h->mnt < 0) return -1;
    return 0;
}

static bool read_fd_mnt_id(int fd, uint64_t *out) {
    char name[80];
    if (snprintf(name, sizeof(name), "/proc/self/fdinfo/%d", fd) >= (int)sizeof(name))
        return false;
    FILE *f = fopen(name, "r");
    if (!f) return false;
    char *line = NULL;
    size_t capacity = 0;
    bool found = false, valid = true;
    while (getline(&line, &capacity, f) >= 0) {
        if (strncmp(line, "mnt_id:", 7) != 0) continue;
        if (found) { valid = false; break; }
        char *p = line + 7, *end = NULL;
        errno = 0;
        unsigned long long v = strtoull(p, &end, 10);
        if (errno || p == end || v == 0) { valid = false; break; }
        while (end && (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n')) end++;
        if (!end || *end != '\0') { valid = false; break; }
        *out = (uint64_t)v;
        found = true;
    }
    free(line);
    if (ferror(f)) valid = false;
    fclose(f);
    return found && valid;
}

static bool parse_u64(const char *s, uint64_t *v) {
    if (!s || *s < '0' || *s > '9') return false;
    char *end = NULL;
    errno = 0;
    unsigned long long n = strtoull(s, &end, 10);
    if (errno || !end || *end != '\0') return false;
    *v = (uint64_t)n;
    return true;
}

static bool parse_dev(const char *s, const struct stat *st) {
    char tmp[64];
    size_t n = strlen(s);
    if (n == 0 || n >= sizeof(tmp)) return false;
    memcpy(tmp, s, n + 1);
    char *colon = strchr(tmp, ':');
    if (!colon || strchr(colon + 1, ':')) return false;
    *colon++ = '\0';
    uint64_t maj = 0, min = 0;
    if (!parse_u64(tmp, &maj) || !parse_u64(colon, &min)) return false;
    return maj == (uint64_t)major(st->st_dev) &&
           min == (uint64_t)minor(st->st_dev);
}

static bool has_rw_token(const char *s) {
    if (!s) return false;
    const char *p = s;
    while (*p) {
        const char *e = strchr(p, ',');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        if (len == 2 && p[0] == 'r' && p[1] == 'w') return true;
        if (!e) break;
        p = e + 1;
    }
    return false;
}

static bool mount_record_matches(char *line, uint64_t want_id,
                                 const char *target, const struct stat *st,
                                 bool *matched_id, bool *matched_path) {
    char *fields[96] = {0};
    int count = 0;
    char *save = NULL;
    for (char *p = strtok_r(line, " \t\r\n", &save); p;
         p = strtok_r(NULL, " \t\r\n", &save)) {
        if (count == 96) return false;
        fields[count++] = p;
    }
    if (count < 10) return false;
    uint64_t id = 0;
    if (!parse_u64(fields[0], &id)) return false;
    if (id == want_id) *matched_id = true;
    if (strcmp(fields[4], target) == 0) *matched_path = true;
    if (id != want_id || strcmp(fields[4], target) != 0) return false;
    int separator = -1;
    for (int i = 6; i < count; i++) {
        if (strcmp(fields[i], "-") == 0) { separator = i; break; }
    }
    if (separator < 0 || separator + 3 >= count) return false;
    if (strcmp(fields[3], "/") != 0 || strcmp(fields[separator + 1], "ext4") != 0)
        return false;
    if (!has_rw_token(fields[5]) || !has_rw_token(fields[separator + 3]))
        return false;
    if (strncmp(fields[separator + 2], "/dev/", 5) != 0)
        return false;
    return parse_dev(fields[2], st);
}

static bool verify_mountinfo(const char *file, uint64_t id, const char *target,
                             const struct stat *st) {
    FILE *f = fopen(file, "r");
    if (!f) return false;
    char *line = NULL;
    size_t cap = 0;
    unsigned target_records = 0, id_records = 0, good_records = 0;
    bool valid = true;
    ssize_t count;
    while ((count = getline(&line, &cap, f)) >= 0) {
        if (count > 65535) { valid = false; break; }
        bool matches_id = false, matches_path = false;
        bool good = mount_record_matches(line, id, target, st,
                                         &matches_id, &matches_path);
        target_records += matches_path;
        id_records += matches_id;
        good_records += good;
        if (target_records > 1 || id_records > 1) { valid = false; break; }
    }
    if (ferror(f)) valid = false;
    free(line);
    fclose(f);
    return valid && target_records == 1 && id_records == 1 && good_records == 1;
}

static int run(const char *target, const char *mountinfo, bool synthetic) {
    struct handles h = {-1, -1, -1, -1};
    struct stat parent = {0}, before = {0}, after = {0}, reopened = {0};
    struct stat root_st = {0}, tmp_st = {0}, mnt_st = {0};
    int check = REJECT;
    printf("=== ISSUE235 / NATIVE SSD TRUST V1 READ-ONLY ===\n");
    if (open_chain(target, &h, &parent, &before) != 0 ||
        fstat(h.root, &root_st) != 0 || fstat(h.tmp, &tmp_st) != 0 ||
        fstat(h.mnt, &mnt_st) != 0) {
        printf("PINNED_DIRECTORY_CHAIN=REJECT\n");
        goto finish;
    }
    if (!rooted_dir(&root_st) || !rooted_dir(&tmp_st) ||
        !leaf_owner_ok(&mnt_st, synthetic) || !leaf_owner_ok(&before, synthetic)) {
        printf("OWNER_TYPE_IDENTITY=REJECT\n");
        goto finish;
    }
    printf("PINNED_DIRECTORY_CHAIN=PASS\n");
    const bool ancestor_safe = no_world_write(&tmp_st) &&
                               no_world_write(&mnt_st) && no_world_write(&root_st);
    printf("ANCESTOR_WORLD_WRITE=%s\n", ancestor_safe ? "ABSENT" : "PRESENT");
    printf("SSD_ROOT_MODE=%04o\n", (unsigned)(before.st_mode & 07777));
    if ((before.st_mode & 07777) != 0777 && (before.st_mode & 07777) != 0755) {
        printf("SSD_ROOT_EXPECTED_MODE=REJECT\n");
        goto finish;
    }
    uint64_t first_id = 0, second_id = 0;
    if (!read_fd_mnt_id(h.leaf, &first_id) ||
        !verify_mountinfo(mountinfo, first_id, target, &before)) {
        printf("PINNED_MOUNTINFO_IDENTITY=REJECT\n");
        goto finish;
    }
    printf("PINNED_MOUNTINFO_IDENTITY=PASS\n");
    if (fstat(h.leaf, &after) != 0 || !same_inode(&before, &after)) {
        printf("FD_IDENTITY_RECHECK=REJECT\n");
        goto finish;
    }
    /* Reopen the existing parent entry without following aliases. */
    const char *leaf_name = strrchr(target, '/');
    if (!leaf_name || !leaf_name[1]) goto finish;
    int second = openat(h.mnt, leaf_name + 1,
                        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (second < 0) {
        printf("ENTRY_IDENTITY_RECHECK=REJECT\n");
        goto finish;
    }
    bool good_second = fstat(second, &reopened) == 0 &&
                       read_fd_mnt_id(second, &second_id) &&
                       same_inode(&before, &reopened) && first_id == second_id;
    close(second);
    if (!good_second) {
        printf("ENTRY_IDENTITY_RECHECK=REJECT\n");
        goto finish;
    }
    printf("ENTRY_IDENTITY_RECHECK=PASS\n");
    if (!synthetic && parent.st_dev == before.st_dev) {
        printf("SEPARATE_DEVICE_BOUNDARY=REJECT\n");
        goto finish;
    }
    printf("SEPARATE_DEVICE_BOUNDARY=%s\n", synthetic ? "NOT_PROVEN_SYNTHETIC" : "PASS");
    printf("SNAPSHOT_MOUNT_IDENTITY=PASS\n");
    check = HOLD;
finish:
    close_handles(&h);
    printf("UUID_BINDING=NOT_IMPLEMENTED\n");
    printf("CONCURRENT_NAMESPACE_EXCLUSION=NOT_PROVEN\n");
    printf("FCHMOD_IMPLEMENTED=NO\n");
    printf("PRODUCTION_ACTIONS_IMPLEMENTED=NO\n");
    printf("EVIDENCE_SOURCE=%s\n", synthetic ? "SYNTHETIC" : "LIVE_POINT_IN_TIME");
    printf("DEPLOYMENT_GATE=HOLD\n");
    printf("ISSUE235_NATIVE_SSD_TRUST_V1=%s\n", check == HOLD ? "SNAPSHOT_ONLY" : "REJECTED");
    return check;
}

int main(int argc, char **argv) {
    const char *target = NULL, *mountinfo = PROC_MOUNTINFO;
    bool synthetic = false;
    if (argc == 3 && strcmp(argv[1], "--check") == 0) {
        if (strcmp(argv[2], "ROUTER_DATA") == 0) target = TARGET_DATA;
        else if (strcmp(argv[2], "ENTWARE") == 0) target = TARGET_ENTWARE;
    }
#ifdef ISSUE235_TEST_BUILD
    else if (argc == 4 && strcmp(argv[1], "--lab-check") == 0) {
        target = argv[2];
        mountinfo = argv[3];
        synthetic = true;
    }
#endif
    if (!target) {
        fprintf(stderr, "USAGE=--check ROUTER_DATA|ENTWARE\n");
        return REJECT;
    }
    return run(target, mountinfo, synthetic);
}