#define main submitted_main
#include "submission.c"
#undef main
#include <time.h>
#include <errno.h>
static void judge_digest(const uint32_t *h, unsigned char *d) {
    unsigned char raw[B*((W+7)/8)];
    for(int b=0;b<B;b++) for(int k=0;k<(W+7)/8;k++) raw[b*((W+7)/8)+k]=(h[b]>>(8*k))&255;
    sha256(d,raw,sizeof raw);
}
int main(int argc,char **argv) {
    if(argc!=4) return 64;
    unsigned long long start=strtoull(argv[1],0,16);
    int count=atoi(argv[2]), full=atoi(argv[3]);
    if(count<1 || count>100000) return 64;
    uint32_t *states=calloc((size_t)count*B,sizeof(uint32_t));
    unsigned char *digests=calloc((size_t)count,32);
    if(!states || !digests) return 70;
    { uint32_t serial_warm[B]; hash_state(start,serial_warm); }
    /* Per-thread initialization occurs before timing; every measured nonce still calls hash_state. */
    #pragma omp parallel
    { uint32_t warm[B]; hash_state(start,warm); unsigned char d[32]; judge_digest(warm,d); }
    struct timespec a,z; clock_gettime(CLOCK_MONOTONIC,&a);
    #pragma omp parallel for schedule(static)
    for(int i=0;i<count;i++) {
        hash_state(start+i,states+(size_t)i*B);
#ifdef JUDGE_CORRUPT_CELL
        states[(size_t)i*B] ^= 1u;
#endif
        judge_digest(states+(size_t)i*B,digests+32*(size_t)i);
    }
    clock_gettime(CLOCK_MONOTONIC,&z);
    fprintf(stderr,"JUDGE_SECONDS %.9f\n",(z.tv_sec-a.tv_sec)+(z.tv_nsec-a.tv_nsec)*1e-9);
    for(int i=0;i<count;i++) {
        printf("%016llx ",start+i);
        for(int k=0;k<32;k++) printf("%02x",digests[32*(size_t)i+k]);
        if(full) {
            uint32_t words[(B*W+31)/32]; memset(words,0,sizeof words);
            uint32_t *h=states+(size_t)i*B;
            for(int b=0;b<B;b++) for(int c=0;c<W;c++) if((h[b]>>c)&1) {int p=b*W+c;words[p/32]|=1u<<(p%32);}
            uint32_t fold=0; for(unsigned k=0;k<sizeof words/sizeof *words;k++) fold^=words[k];
            printf(" %08x ",fold);
            for(int b=B-1;b>=0;b--) printf("%0*x",(W+3)/4,h[b]);
        }
        puts("");
    }
    free(states); free(digests); return 0;
}
