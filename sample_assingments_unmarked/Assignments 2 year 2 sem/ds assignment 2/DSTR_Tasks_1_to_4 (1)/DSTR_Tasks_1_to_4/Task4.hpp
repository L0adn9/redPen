/*
 * ============================================================================
 *  Module  : Task 4 - Parcel Activity and Record Management
 *  Member 4 - (your name / TP number here)
 *  Data structures used in Task4.cpp:
 *   1. ActivityHistory - doubly linked list, keeps EVERY activity (audit log)
 *   2. UndoStack       - linked-list STACK (LIFO) of the activities that can
 *                        still be undone. Undo always pops the top.
 * ============================================================================
 */
#ifndef TASK4_H
#define TASK4_H
#include "Common.hpp"

void runTask4Menu();

// Called by every module whenever something important happens.
// Task 4 stores the record and, if it is a status change, pushes it on the undo stack.
void logActivity(const string& parcelID, const string& activityType,
    const string& previousStatus, const string& newStatus,
    const string& staffID);

// Save the activity history to task4_activities.txt (also called automatically
// after every change; the file is loaded automatically the first time it is needed).
void saveActivities();

#endif
