/* demonstrate the width of the boolean type on your system.
 * note: this is a C++ program; gcc does not seem to know about the "bool" type in C.
 */

#include <stdio.h>

int main() {
  printf("The size of a bool on your platform is: %d\n", sizeof(bool));
  return 0;
}