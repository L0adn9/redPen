/*
 * ============================================================================
 *  Module  : Task 3 - Collection Counter and Delivery Resource Management
 *  Member 3 - Thu Thu San
 *  Data structures used in Task3.cpp:
 *   1. ResourceList          - singly linked list = master store of resources
 *   2. ResourceCircularQueue - CIRCULAR QUEUE (one per resource type) holding
 *                              the AVAILABLE resources -> round-robin allocation
 *   3. WaitList              - linked-list FIFO queue of parcels waiting for a
 *                              resource (used when everything is occupied)
 * ============================================================================
 */
#ifndef TASK3_H
#define TASK3_H
#include "Common.hpp"

void runTask3Menu();

// ---------------------------------------------------------------------------
// OPTIONAL hooks for other modules (nothing in Task 1 / 2 / 4 / 5 has to call
// them - Task 3 also keeps itself consistent by checking parcel statuses).
// ---------------------------------------------------------------------------

// Allocate a resource to a parcel using Task 3's round-robin rule.
// Returns true if a resource was assigned immediately (false = queued/rejected).
bool requestResourceForParcel(Parcel* parcel, const string& requestID = "");

// Release whatever resource is handling this parcel (e.g. Task 4 undo).
// completed = true counts the job as a handled transaction.
// Returns false if the parcel was not assigned to any resource.
bool releaseResourceOfParcel(const string& parcelID, bool completed = false);

// ID of the resource currently handling this parcel, or "" if none.
string getAssignedResourceID(const string& parcelID);

// Re-check every assignment against the parcels' current status (e.g. a parcel
// was set to Collected in Task 1): frees finished resources and serves waiting
// parcels. Returns true if anything changed.
bool refreshResourceAssignments();
#endif
