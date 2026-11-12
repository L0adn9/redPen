/* Task5.h - Parcel Category Organisation (TASK 5 OWNER completes this) */
#ifndef TASK5_H
#define TASK5_H
#include "Common.hpp"

void runTask5Menu();
// Called by Task 1 when a parcel is registered / updated.
void insertParcelToTree(Parcel* parcel);
void updateParcelInTree(Parcel* parcel);
#endif
