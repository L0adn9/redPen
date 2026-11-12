/* Task4.h - Parcel Activity and Record Management (TASK 4 OWNER completes this) */
#ifndef TASK4_H
#define TASK4_H
#include "Common.hpp"

void runTask4Menu();
// Called by every module whenever something important happens.
// Task 4 owner: push an activity record onto your stack here.
void logActivity(const string& parcelID, const string& activityType,
    const string& previousStatus, const string& newStatus,
    const string& staffID);
#endif
