/* ARTY.C - artillery duel against a CPU gunner, for VT100 terminals.
 *
 * Written for DEC C V6.4 on OpenVMS VAX V7.3 (ANSI C89); also builds
 * with "gcc -ansi -pedantic ... -lm" for testing elsewhere.
 *
 * You are (P) on the left, the CPU is (C) on the right.  Each turn
 * you pick a weapon, an angle (1-89 degrees) and a power (1-100).
 * Shells fly in a parabola and are pushed around by the wind.  Every
 * blast digs a crater, and a tank whose ground disappears drops down.
 *
 * Winning a round pays $1000 (the loser still gets $300), and there
 * is a shop between rounds:
 *    Big shell   bigger blast
 *    MIRV        splits into three shells at the top of its arc
 *    Dirt bomb   builds a hill instead of digging a crater
 *    Shield      absorbs one blast (the tank is drawn as [P])
 * First to WINS rounds takes the match.  Q at a prompt quits.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <time.h>
#ifdef __VMS
#include <lib$routines.h>
#endif

#define COLS   78
#define ROWS   18               /* playfield rows              */
#define TOP    2                /* screen line of top row      */
#define PI     3.14159265
#define GRAV   1.0
#define DT     0.05
#define WINS   3

#define NW     4                /* weapons: baby, big, mirv, dirt */
#define W_BABY 0
#define W_BIG  1
#define W_MIRV 2
#define W_DIRT 3
#define SHIELD_PRICE 400
#define START_CASH   600
#define WIN_PAY      1000
#define LOSE_PAY     300

static const char *wname[NW] = { "Baby shell", "Big shell", "MIRV", "Dirt bomb" };
static const int wprice[NW] = { 0, 300, 500, 150 };

static int h[COLS];             /* ground height (rows) per column */
static int tx[2];               /* tank columns: 0 = you, 1 = CPU  */
static int alive[2];
static int shield[2];
static int cash[2];
static int inv[2][NW];
static int score[2];
static int wind;                /* -9 .. 9                         */
static int fast;                /* no delays (for testing)         */

/* result of the last shot */
static int last_impact, last_off;

/* CPU gunner's memory */
static int cpu_ang, cpu_pow, cpu_have, cpu_impact, cpu_off;

static const char *taunt[] = {
    "Is that all you've got?",
    "Nice try, rookie.",
    "My grandmother shoots better.",
    "Is this thing even loaded?",
    "Eat dirt!",
    "Tick tock, tick tock.",
    "You call that artillery?"
};
#define NTAUNT ((int) (sizeof taunt / sizeof taunt[0]))

static int rnd(int n)
{
    return (int) ((double) rand() / ((double) RAND_MAX + 1.0) * n);
}

static void pause_s(double s)
{
    if (fast)
        return;
#ifdef __VMS
    {
        float f = (float) s;

        lib$wait(&f);
    }
#else
    {
        clock_t end = clock() + (clock_t) (s * CLOCKS_PER_SEC);

        while (clock() < end)
            ;
    }
#endif
}

static void goto_rc(int r, int c)
{
    printf("\033[%d;%dH", TOP + ROWS - 1 - r, c + 1);
}

static void goto_line(int line)
{
    printf("\033[%d;1H\033[K", line);
}

/* What is drawn at playfield row r, column x? */
static char cell(int r, int x)
{
    static const char *sprite[2] = { "(P)", "(C)" };
    static const char *shielded[2] = { "[P]", "[C]" };
    int k;

    if (r < h[x])
        return '#';
    for (k = 0; k < 2; k++)
        if (alive[k] && r == h[tx[k]] && abs(x - tx[k]) <= 1)
            return (shield[k] ? shielded : sprite)[k][x - tx[k] + 1];
    return ' ';
}

static void render(void)
{
    char arrows[12];
    int r, x, n;

    n = abs(wind);
    memset(arrows, wind < 0 ? '<' : '>', n);
    arrows[n] = '\0';
    printf("\033[H");
    printf("ARTILLERY    You %d   CPU %d   (first to %d)    Wind %-9s %+d\033[K\n",
           score[0], score[1], WINS, arrows, wind);
    for (r = ROWS - 1; r >= 0; r--) {
        for (x = 0; x < COLS; x++)
            putchar(cell(r, x));
        putchar('\n');
    }
    printf("$%d  Shield:%s  Weapons: 1 Baby  2 Big(%d)  3 MIRV(%d)  4 Dirt(%d)\033[K",
           cash[0], shield[0] ? "yes" : "no",
           inv[0][W_BIG], inv[0][W_MIRV], inv[0][W_DIRT]);
    fflush(stdout);
}

static void new_round(void)
{
    double p1 = rnd(628) / 100.0, p2 = rnd(628) / 100.0;
    double f1 = 0.08 + rnd(8) / 100.0, f2 = 0.22 + rnd(15) / 100.0;
    double a1 = 2.5 + rnd(20) / 10.0, a2 = 1.0 + rnd(15) / 10.0;
    int x, v, k;

    for (x = 0; x < COLS; x++) {
        v = (int) floor(6.5 + a1 * sin(x * f1 + p1) + a2 * sin(x * f2 + p2) + 0.5);
        if (v < 2)
            v = 2;
        if (v > 13)
            v = 13;
        h[x] = v;
    }
    tx[0] = 5 + rnd(10);
    tx[1] = COLS - 6 - rnd(10);
    for (k = 0; k < 2; k++) {
        for (x = tx[k] - 2; x <= tx[k] + 2; x++)
            h[x] = h[tx[k]];
        alive[k] = 1;
    }
    wind = rnd(19) - 9;
    cpu_have = 0;
}

/* Flight of one shell from (x0,y0) with velocity (vx,vy).  Returns
 * 1 off the map, -1 direct tank hit, 0 ground, or 2 when a MIRV
 * reaches the top of its arc.  *ex,*ey is where it ended and *evx the
 * horizontal speed there (wind included). */
static int fly(double x0, double y0, double vx, double vy, int mirv,
               double *ex, double *ey, double *evx)
{
    double wa = wind * 0.012;
    double t = 0.0, x, y;
    int col, row, pr = -1, pc = -1, k, res = 0;

    for (;;) {
        t += DT;
        x = x0 + vx * t + 0.5 * wa * t * t;
        y = y0 + vy * t - 0.5 * GRAV * t * t;
        col = (int) floor(x + 0.5);
        if (col < 0 || col >= COLS) {
            res = 1;
            break;
        }
        if (mirv && vy - GRAV * t <= 0.0) {
            res = 2;
            break;
        }
        if (y < 0.0 || y < 2.0 * h[col])
            break;
        for (k = 0; k < 2; k++)
            if (alive[k] && abs(col - tx[k]) <= 1 && y < 2.0 * h[tx[k]] + 2.0)
                res = -1;
        if (res)
            break;

        row = (int) floor(y / 2.0);
        if (row != pr || col != pc) {
            if (pr >= 0) {
                goto_rc(pr, pc);
                putchar(cell(pr, pc));
            }
            if (row >= ROWS) {
                row = ROWS - 1;         /* off the top: show a marker */
                goto_rc(row, col);
                putchar('^');
            } else {
                goto_rc(row, col);
                putchar('*');
            }
            fflush(stdout);
            pr = row;
            pc = col;
            pause_s(0.02);
        }
    }
    if (pr >= 0) {
        goto_rc(pr, pc);
        putchar(cell(pr, pc));
    }
    *ex = x;
    *ey = y < 0.0 ? 0.0 : y;
    *evx = vx + wa * t;
    return res;
}

/* Blast animation, kills and crater (or dirt pile).  Returns a bitmask
 * of destroyed tanks; a shield soaks up one blast instead. */
static int boom(double ex, double ey, double radius, double killr, int dirt)
{
    int rad, maxrad, r, c, k, dead = 0, lo, hi, nh;
    double dx, dy, edge;

    maxrad = (int) ceil(radius);
    for (rad = 1; rad <= maxrad; rad++) {
        for (r = 0; r < ROWS; r++)
            for (c = 0; c < COLS; c++) {
                dx = c - ex;
                dy = 2.0 * r + 1.0 - ey;
                if (dx * dx + dy * dy <= (double) (rad * rad)) {
                    goto_rc(r, c);
                    putchar(dirt ? 'o' : '*');
                }
            }
        fflush(stdout);
        pause_s(0.12);
    }

    if (!dirt)
        for (k = 0; k < 2; k++) {
            dx = tx[k] - ex;
            dy = 2.0 * h[tx[k]] + 1.0 - ey;
            if (alive[k] && dx * dx + dy * dy <= killr * killr) {
                if (shield[k])
                    shield[k] = 0;
                else
                    dead |= 1 << k;
            }
        }

    lo = (int) floor(ex - radius);
    hi = (int) ceil(ex + radius);
    for (c = lo; c <= hi; c++) {
        if (c < 0 || c >= COLS)
            continue;
        dx = c - ex;
        if (dx * dx > radius * radius)
            continue;
        edge = sqrt(radius * radius - dx * dx);
        if (dirt) {
            nh = (int) floor((ey + edge) / 2.0);
            if (nh > ROWS - 3)
                nh = ROWS - 3;
            if (nh > h[c])
                h[c] = nh;
        } else if (2.0 * h[c] > ey - edge) {
            nh = (int) floor((ey - edge) / 2.0);
            h[c] = nh < 0 ? 0 : nh;
        }
    }
    return dead;
}

static int col_of(double x)
{
    int c = (int) floor(x + 0.5);

    if (c < 0)
        c = 0;
    if (c >= COLS)
        c = COLS - 1;
    return c;
}

/* Fire a shot for 'who'; returns the mask of destroyed tanks and sets
 * last_impact / last_off (for a MIRV, those of the middle shell). */
static int shoot(int who, int ang, int pw, int wp)
{
    double v = pw / 10.0, a = ang * PI / 180.0;
    double ex, ey, evx, cx, cy, cvx;
    int res, r2, k, dead = 0;
    double radius = wp == W_BIG ? 5.0 : (wp == W_DIRT ? 4.0 : 3.0);
    double killr = wp == W_BIG ? 7.0 : 4.5;

    res = fly(tx[who], 2.0 * h[tx[who]] + 2.2, (who ? -1.0 : 1.0) * v * cos(a),
              v * sin(a), wp == W_MIRV, &ex, &ey, &evx);
    if (res == 2) {
        for (k = 0; k < 3; k++) {
            r2 = fly(ex, ey, evx + (k - 1) * 1.2, 0.0, 0, &cx, &cy, &cvx);
            if (r2 <= 0)
                dead |= boom(cx, cy, radius, killr, 0);
            if (k == 1) {
                last_impact = col_of(cx);
                last_off = r2 > 0;
            }
        }
    } else {
        last_impact = col_of(ex);
        last_off = res > 0;
        if (res <= 0)
            dead = boom(ex, ey, radius, killr, wp == W_DIRT);
    }
    return dead;
}

static int ask(int line, const char *prompt, int def, int lo, int hi, int *out)
{
    char buf[80];
    int v;

    for (;;) {
        goto_line(line);
        printf("%s (%d-%d) [%d]: ", prompt, lo, hi, def);
        fflush(stdout);
        if (!fgets(buf, sizeof buf, stdin))
            return -1;
        if (toupper((unsigned char) buf[0]) == 'Q')
            return -1;
        if (buf[0] == '\n' || buf[0] == '\0') {
            *out = def;
            return 0;
        }
        v = atoi(buf);
        if (v >= lo && v <= hi) {
            *out = v;
            return 0;
        }
    }
}

/* The shop.  Returns -1 if input ended. */
static int shop(void)
{
    char buf[80];
    int c;

    for (;;) {
        printf("\033[2J\033[H\n  S H O P          You have $%d\n\n", cash[0]);
        printf("  1) Big shell   $%-4d  bigger blast            (you own %d)\n",
               wprice[W_BIG], inv[0][W_BIG]);
        printf("  2) MIRV        $%-4d  splits into three shells (you own %d)\n",
               wprice[W_MIRV], inv[0][W_MIRV]);
        printf("  3) Dirt bomb   $%-4d  builds a hill            (you own %d)\n",
               wprice[W_DIRT], inv[0][W_DIRT]);
        printf("  4) Shield      $%-4d  absorbs one blast        (%s)\n\n",
               SHIELD_PRICE, shield[0] ? "you have one" : "you have none");
        printf("  Buy which (1-4), or Enter to fight: ");
        fflush(stdout);
        if (!fgets(buf, sizeof buf, stdin))
            return -1;
        if (buf[0] == '\n' || buf[0] == '\0' || toupper((unsigned char) buf[0]) == 'Q')
            return 0;
        c = atoi(buf);
        if (c >= 1 && c <= 3 && cash[0] >= wprice[c]) {
            cash[0] -= wprice[c];
            inv[0][c]++;
        } else if (c == 4 && !shield[0] && cash[0] >= SHIELD_PRICE) {
            cash[0] -= SHIELD_PRICE;
            shield[0] = 1;
        }
    }
}

static void cpu_shop(void)
{
    int tries;

    for (tries = 0; tries < 3; tries++) {
        if (cash[1] >= wprice[W_MIRV] && rnd(2)) {
            cash[1] -= wprice[W_MIRV];
            inv[1][W_MIRV]++;
        } else if (cash[1] >= wprice[W_BIG] && rnd(2)) {
            cash[1] -= wprice[W_BIG];
            inv[1][W_BIG]++;
        } else if (!shield[1] && cash[1] >= SHIELD_PRICE && rnd(3) == 0) {
            cash[1] -= SHIELD_PRICE;
            shield[1] = 1;
        }
    }
}

static int cpu_weapon(void)
{
    if (inv[1][W_MIRV] > 0 && rnd(2)) {
        inv[1][W_MIRV]--;
        return W_MIRV;
    }
    if (inv[1][W_BIG] > 0 && rnd(2)) {
        inv[1][W_BIG]--;
        return W_BIG;
    }
    return W_BABY;
}

static void cpu_choose(void)
{
    int d = abs(tx[1] - tx[0]);
    double s, err, r, adj;

    if (!cpu_have) {
        cpu_ang = 35 + rnd(30);
        s = sin(2.0 * cpu_ang * PI / 180.0);
        cpu_pow = (int) (10.0 * sqrt(d / s));
    } else {
        err = cpu_impact - tx[0];       /* > 0: fell short of you */
        r = abs(tx[1] - cpu_impact);
        if (cpu_off) {                  /* way too hard: back off a lot */
            cpu_pow -= cpu_pow / 8;
        } else if (err > 0.0 && r < 12.0) {
            cpu_ang += 8;               /* hit a hill by its own gun: lob it */
        } else {
            adj = err * cpu_pow / (2.0 * r);
            if (adj > 30.0)
                adj = 30.0;
            if (adj < -30.0)
                adj = -30.0;
            cpu_pow += (int) adj;
        }
        cpu_ang += rnd(3) - 1;
    }
    cpu_pow += cpu_pow * (rnd(11) - 5) / 100;   /* the gunner is not perfect */
    if (cpu_ang < 10)
        cpu_ang = 10;
    if (cpu_ang > 85)
        cpu_ang = 85;
    if (cpu_pow < 5)
        cpu_pow = 5;
    if (cpu_pow > 100)
        cpu_pow = 100;
}

static void intro(void)
{
    char buf[80];

    printf("\033[2J\033[H");
    printf("\n  A R T I L L E R Y\n\n");
    printf("  You are (P) on the left; the CPU gunner is (C) on the right.\n\n");
    printf("  Each turn you pick a WEAPON, an ANGLE (1-89 degrees) and a POWER\n");
    printf("  (1-100).  Shells fly in an arc and are pushed by the WIND shown at\n");
    printf("  the top (arrows point the way it blows; more arrows = stronger).\n\n");
    printf("  Every blast digs a crater.  A tank caught in a blast is destroyed,\n");
    printf("  and a tank whose ground is blown away drops into the hole.\n\n");
    printf("  Win a round: $%d.  Lose: $%d.  Spend it in the shop on big shells,\n",
           WIN_PAY, LOSE_PAY);
    printf("  MIRVs, dirt bombs and shields -- the CPU shops too.\n\n");
    printf("  A shell that flies off the top shows as ^ along the top row.\n");
    printf("  Press Enter at a prompt to repeat your last value; Q quits.\n\n");
    printf("  First to %d rounds wins.  Press Enter to begin: ", WINS);
    fflush(stdout);
    fgets(buf, sizeof buf, stdin);
}

int main(void)
{
    char buf[80];
    int who, ang = 45, pw = 50, wsel = 1, wp, dead, d, k, i;
    int impact;

    fast = getenv("ARTY_FAST") != NULL;
    srand(getenv("ARTY_SEED") ? (unsigned) atoi(getenv("ARTY_SEED"))
                              : (unsigned) time(NULL));
    intro();

    for (;;) {
        score[0] = score[1] = 0;
        for (k = 0; k < 2; k++) {
            cash[k] = START_CASH;
            shield[k] = 0;
            for (i = 0; i < NW; i++)
                inv[k][i] = 0;
        }
        while (score[0] < WINS && score[1] < WINS) {
            if (shop() < 0)
                return 0;
            cpu_shop();
            new_round();
            who = (score[0] + score[1]) % 2;
            while (alive[0] && alive[1]) {
                printf("\033[2J");
                render();
                if (who == 0) {
                    for (;;) {
                        if (ask(21, "Weapon", wsel, 1, NW, &wsel) < 0)
                            goto quit;
                        if (wsel == 1 || inv[0][wsel - 1] > 0)
                            break;
                        goto_line(21);
                        printf("You have no %s -- pick another.", wname[wsel - 1]);
                        fflush(stdout);
                        pause_s(1.2);
                        wsel = 1;
                    }
                    wp = wsel - 1;
                    if (wp != W_BABY)
                        inv[0][wp]--;
                    if (ask(22, "Angle", ang, 1, 89, &ang) < 0 ||
                        ask(23, "Power", pw, 1, 100, &pw) < 0)
                        goto quit;
                    if (wp != W_BABY && inv[0][wp] == 0)
                        wsel = 1;
                    dead = shoot(0, ang, pw, wp);
                } else {
                    cpu_choose();
                    wp = cpu_weapon();
                    goto_line(22);
                    printf("CPU fires a %s: angle %d, power %d", wname[wp],
                           cpu_ang, cpu_pow);
                    fflush(stdout);
                    pause_s(1.0);
                    dead = shoot(1, cpu_ang, cpu_pow, wp);
                    cpu_have = 1;
                    cpu_impact = last_impact;
                    cpu_off = last_off;
                }
                impact = last_impact;
                goto_line(21);
                if (!dead) {
                    if (last_off) {
                        printf("The shell sails off the map.");
                    } else if (who == 0) {
                        d = impact - tx[1];
                        if (d < 0)
                            printf("Your shell landed %d columns short.", -d);
                        else if (d > 0)
                            printf("Your shell landed %d columns long.", d);
                        else
                            printf("Right on the column, but not close enough!");
                    } else {
                        d = impact - tx[0];
                        if (d > 0)
                            printf("The CPU's shell landed %d columns short of you.", d);
                        else if (d < 0)
                            printf("The CPU's shell landed %d columns long.", -d);
                        else
                            printf("The CPU's shell landed right on your column!");
                    }
                    if (rnd(2)) {
                        printf("\033[22;1H\033[KCPU: \"%s\"", taunt[rnd(NTAUNT)]);
                    }
                    fflush(stdout);
                    pause_s(1.5);
                }
                if (dead & 1)
                    alive[0] = 0;
                if (dead & 2)
                    alive[1] = 0;
                who ^= 1;
                wind += rnd(3) - 1;
                if (wind > 9)
                    wind = 9;
                if (wind < -9)
                    wind = -9;
            }
            printf("\033[2J");
            render();
            goto_line(21);
            if (!alive[0] && !alive[1]) {
                printf("Mutual destruction - round drawn.  Both get $%d.", LOSE_PAY);
                cash[0] += LOSE_PAY;
                cash[1] += LOSE_PAY;
            } else if (!alive[1]) {
                printf("*** The CPU is destroyed!  You win $%d. ***", WIN_PAY);
                printf("\033[22;1H\033[KCPU: \"I'll be back.\"");
                score[0]++;
                cash[0] += WIN_PAY;
                cash[1] += LOSE_PAY;
            } else {
                printf("*** You have been destroyed!  The CPU wins $%d. ***", WIN_PAY);
                score[1]++;
                cash[1] += WIN_PAY;
                cash[0] += LOSE_PAY;
            }
            printf("\033[23;1HPress Enter: ");
            fflush(stdout);
            if (!fgets(buf, sizeof buf, stdin))
                return 0;
        }
        printf("\033[2J\033[H\n  %s  Final score: You %d, CPU %d.\n",
               score[0] > score[1] ? "YOU WIN THE MATCH!" : "The CPU wins the match.",
               score[0], score[1]);
        printf("\n  Play again (Y/N)? ");
        fflush(stdout);
        if (!fgets(buf, sizeof buf, stdin) || toupper((unsigned char) buf[0]) != 'Y')
            break;
    }
quit:
    printf("\033[24;1H\n");
    return 0;
}
