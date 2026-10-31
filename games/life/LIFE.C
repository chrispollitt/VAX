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
 * life or a period-2 oscillator.  Ctrl-Y aborts at any time.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#ifdef __VMS
#include <lib$routines.h>
#endif

#define ROWS     22
#define COLS     78
#define DEF_GENS 500

static char cur[ROWS][COLS];    /* current generation          */
static char nxt[ROWS][COLS];    /* scratch for the next one    */
static char old[ROWS][COLS];    /* generation before cur       */
static char old2[ROWS][COLS];   /* generation before old       */

static void pause_frame(void)
{
#ifdef __VMS
    float secs = 0.08f;

    lib$wait(&secs);
#else
    clock_t end = clock() + CLOCKS_PER_SEC / 12;

    while (clock() < end)
        ;
#endif
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
    printf("Generation %5d   Population %5d   (Ctrl-Y to quit)\n", gen, pop);
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
    fputs("\033[2J", stdout);

    for (gen = 0; gen < gens; gen++) {
        draw(gen, pop);
        pause_frame();
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
