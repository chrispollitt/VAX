/* LIFE.C - Conway's Game of Life for VT100 terminals.
 *
 * Written for DEC C V6.4 on OpenVMS VAX V7.3 (ANSI C89), but also
 * builds with "gcc -ansi -pedantic" for testing elsewhere.
 *
 * Usage:  LIFE [generations] [R]
 *   generations  how many generations to run (default 500)
 *   R            start from the R-pentomino instead of a random soup
 *
 * The world is a 22 x 78 torus, so gliders wrap around the edges.
 * It stops early if the world dies out or settles into a still
 * life or a period-2 oscillator.  Any key (the space bar, say)
 * stops it too; Ctrl-Y aborts at any time.
 */
#ifndef __VMS
#define _POSIX_C_SOURCE 200112L         /* termios, for the key check */
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#ifdef __VMS
#include <descrip.h>
#include <iodef.h>
#include <lib$routines.h>
#include <ssdef.h>
#include <starlet.h>
#else
#include <signal.h>
#include <termios.h>
#include <unistd.h>
#endif

#define ROWS     22
#define COLS     78
#define DEF_GENS 500

static char cur[ROWS][COLS];    /* current generation          */
static char nxt[ROWS][COLS];    /* scratch for the next one    */
static char old[ROWS][COLS];    /* generation before cur       */
static char old2[ROWS][COLS];   /* generation before old       */

/* A key typed while it runs stops the game.  key_init() once at the start; key_pressed() says whether any
 * key has been typed since the last call (and swallows it, so it does not reach whatever runs next).
 * Without a terminal on the input it never reports a key. */
#ifdef __VMS
static unsigned short tt_chan;
static int have_tt;

static void key_init(void)
{
    $DESCRIPTOR(tt, "SYS$COMMAND");     /* the terminal, even when run from a command procedure */

    have_tt = (sys$assign(&tt, &tt_chan, 0, 0) & 1);
}

static int key_pressed(void)
{
    struct {
        unsigned short count;           /* characters waiting in the type-ahead buffer */
        char first;
        char reserved;
        unsigned long more;
    } tah;
    unsigned short iosb[4];
    char buf[80];
    unsigned n;

    if (!have_tt)
        return 0;
    if (!(sys$qiow(0, tt_chan, IO$_SENSEMODE | IO$M_TYPEAHDCNT, iosb, 0, 0, &tah, 8, 0, 0, 0, 0) & 1))
        return 0;
    if (tah.count == 0)
        return 0;
    n = tah.count > sizeof buf ? (unsigned) sizeof buf : tah.count;
    sys$qiow(0, tt_chan, IO$_READVBLK | IO$M_TIMED | IO$M_NOECHO, iosb, 0, 0, buf, n, 0, 0, 0, 0);
    return 1;
}
#else
static struct termios saved_tio;
static int tio_saved;

static void key_restore(void)
{
    if (tio_saved) {
        tcsetattr(0, TCSANOW, &saved_tio);
        tio_saved = 0;
    }
}

static void on_signal(int sig)
{
    key_restore();
    _exit(128 + sig);
}

static void key_init(void)
{
    struct termios raw;

    if (!isatty(0) || tcgetattr(0, &saved_tio) != 0)
        return;
    raw = saved_tio;
    raw.c_lflag &= ~(tcflag_t) (ICANON | ECHO);
    raw.c_cc[VMIN] = 0;                 /* read() returns at once, with or without a key */
    raw.c_cc[VTIME] = 0;
    if (tcsetattr(0, TCSANOW, &raw) == 0) {
        tio_saved = 1;
        atexit(key_restore);
        signal(SIGINT, on_signal);
        signal(SIGTERM, on_signal);
    }
}

static int key_pressed(void)
{
    char ch;
    int got = 0;

    if (!tio_saved)
        return 0;
    while (read(0, &ch, 1) == 1)
        got = 1;
    return got;
}
#endif

static void pause_for(double secs)
{
#ifdef __VMS
    float s = (float) secs;

    lib$wait(&s);
#else
    clock_t end = clock() + (clock_t) (secs * CLOCKS_PER_SEC);

    while (clock() < end)
        ;
#endif
}

static void pause_frame(void)
{
    pause_for(0.08);
}

static int neighbours(int r, int c)
{
    int dr, dc, n = 0;

    for (dr = -1; dr <= 1; dr++)
        for (dc = -1; dc <= 1; dc++)
            if (dr || dc)
                n += cur[(r + dr + ROWS) % ROWS][(c + dc + COLS) % COLS];
    return n;
}

/* Advance one generation; returns the new population. */
static int step(void)
{
    int r, c, n, pop = 0;

    for (r = 0; r < ROWS; r++)
        for (c = 0; c < COLS; c++) {
            n = neighbours(r, c);
            nxt[r][c] = cur[r][c] ? (n == 2 || n == 3) : (n == 3);
            pop += nxt[r][c];
        }
    memcpy(old2, old, sizeof cur);
    memcpy(old, cur, sizeof cur);
    memcpy(cur, nxt, sizeof cur);
    return pop;
}

static int seed(int rpent)
{
    int r, c, pop = 0;

    memset(cur, 0, sizeof cur);
    if (rpent) {
        /* .##
         * ##.
         * .#.   centred on the screen
         */
        cur[10][40] = 1; cur[10][41] = 1;
        cur[11][39] = 1; cur[11][40] = 1;
        cur[12][40] = 1;
    } else {
        srand((unsigned) time(NULL));
        for (r = 0; r < ROWS; r++)
            for (c = 0; c < COLS; c++)
                cur[r][c] = rand() < RAND_MAX / 4;
    }
    for (r = 0; r < ROWS; r++)
        for (c = 0; c < COLS; c++)
            pop += cur[r][c];
    return pop;
}

static void draw(int gen, int pop)
{
    char line[COLS + 1];
    int r, c;

    fputs("\033[H", stdout);
    for (r = 0; r < ROWS; r++) {
        for (c = 0; c < COLS; c++)
            line[c] = cur[r][c] ? '#' : ' ';
        line[COLS] = '\0';
        fputs(line, stdout);
        fputs("\n", stdout);
    }
    printf("Generation %5d   Population %5d   (any key to quit)\n", gen, pop);
}

int main(int argc, char *argv[])
{
    int gens = DEF_GENS, rpent = 0, gen, pop, i;
    const char *why = "reached the generation limit";

    for (i = 1; i < argc; i++) {
        if (isdigit((unsigned char) argv[i][0]))
            gens = atoi(argv[i]);
        else if (toupper((unsigned char) argv[i][0]) == 'R')
            rpent = 1;
    }

    pop = seed(rpent);
    key_init();
    /* The Enter that started the game can still be on its way (a telnet Enter is a CR and then another character),
     * so wait a moment and swallow whatever has arrived: only keys typed after the start stop the game. */
    pause_for(0.4);
    (void) key_pressed();
    fputs("\033[2J", stdout);

    for (gen = 0; gen < gens; gen++) {
        draw(gen, pop);
        fflush(stdout);
        pause_frame();
        if (key_pressed()) {
            why = "you pressed a key";
            break;
        }
        pop = step();
        if (pop == 0) {
            why = "everything died";
            gen++;
            break;
        }
        if (gen > 0 && !memcmp(cur, old, sizeof cur)) {
            why = "settled into a still life";
            gen++;
            break;
        }
        if (gen > 0 && !memcmp(cur, old2, sizeof cur)) {
            why = "settled into a period-2 oscillator";
            gen++;
            break;
        }
    }
    draw(gen, pop);
    printf("Finished after %d generations: %s.\n", gen, why);
    return 0;
}
