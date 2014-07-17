/* program to demonstrate that C's invert operator has the same weird behaviour as python's
 from http://bytes.com/topic/python/answers/714382-bit-wise-unary-operator

 */

#include <stdio.h>
int main(void)
{
int a = 7978;
a = ~a;
printf("%d\n", a);

int ua = 7978;
ua = ~ua;
printf("%u\n", ua);
return 0;
}