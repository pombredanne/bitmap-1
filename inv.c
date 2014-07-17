/* program to demonstrate that C's invert operator has the same weird behaviour as python's
 from http://bytes.com/topic/python/answers/714382-bit-wise-unary-operator

 */

#include <stdio.h>
int main(void)
{
int a = 7978;
a = ~a;
printf("%d\n", a);
return 0;
}