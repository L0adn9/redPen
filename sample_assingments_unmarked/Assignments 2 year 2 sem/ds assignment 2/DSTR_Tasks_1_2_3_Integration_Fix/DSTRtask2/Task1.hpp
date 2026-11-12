/*
 * ============================================================================
 *  Module  : Task 1 - Parcel Intake, Sorting and Processing Module
 *  Member 1 - Pwint Yati Oo(TP101449)
 *  Data structures declared here:
 *   1. ParcelList  - singly linked list = MASTER RECORD STORE of every parcel
 *   2. ParcelQueue - linked-list QUEUE (FIFO) of Parcel pointers, used for
 *                    the pending queue and the 5 routing queues
 * ============================================================================
 */
#ifndef TASK1_H
#define TASK1_H

#include "Common.hpp"

 // ---------------------------------------------------------------------------
 // Master list node: stores the Parcel record itself.
 // ---------------------------------------------------------------------------
struct ParcelNode {
    Parcel      data;
    ParcelNode* next;
    ParcelNode(const Parcel& p) : data(p), next(nullptr) {}
};

// ---------------------------------------------------------------------------
// ParcelList : singly linked list with head AND tail pointers.
//   add()      O(1)  (append at tail)
//   findByID() O(n)  (linear search)
// Nodes are never deleted while the program runs, so Parcel* pointers handed
// out remain valid. This lets the queues share ONE copy of each record, which
// keeps the data consistent (a status change is visible everywhere).
// ---------------------------------------------------------------------------
class ParcelList {
private:
    ParcelNode* head;
    ParcelNode* tail;
    int         count;
    int         idCounter;      // used to auto-generate IDs: P001, P002, ...

public:
    ParcelList();
    ~ParcelList();
    ParcelList(const ParcelList&) = delete;             // prevent shallow copies
    ParcelList& operator=(const ParcelList&) = delete;

    Parcel* add(const Parcel& p);
    Parcel* findByID(const string& parcelID) const;
    string      generateUniqueID();
    int         getCount() const { return count; }
    ParcelNode* getHead() const { return head; }
};

// ---------------------------------------------------------------------------
// Queue node: holds a POINTER to a parcel in the master list.
// ---------------------------------------------------------------------------
struct QueueNode {
    Parcel* parcel;
    QueueNode* next;
    QueueNode(Parcel* p) : parcel(p), next(nullptr) {}
};

// ---------------------------------------------------------------------------
// ParcelQueue : linked-list queue (First-In-First-Out).
//   enqueue() O(1)   dequeue() O(1)   peek() O(1)   isEmpty() O(1)
//   remove()  O(n)   (needed when a waiting parcel is cancelled/missing)
// A linked list is used instead of a fixed array so the queue can never be
// "full" during peak periods when hundreds of parcels arrive.
// ---------------------------------------------------------------------------
class ParcelQueue {
private:
    QueueNode* front;
    QueueNode* rear;
    int        count;

public:
    ParcelQueue();
    ~ParcelQueue();
    ParcelQueue(const ParcelQueue&) = delete;
    ParcelQueue& operator=(const ParcelQueue&) = delete;

    void    enqueue(Parcel* p);
    Parcel* dequeue();                       // returns nullptr if empty
    Parcel* peek() const;                    // returns nullptr if empty
    bool    isEmpty() const { return count == 0; }
    int     size() const { return count; }
    bool    remove(const string& parcelID);  // true if the parcel was found
    void    display() const;
};

// ---------------------------------------------------------------------------
// Public interface of Task 1 (other modules may call these)
// ---------------------------------------------------------------------------
void    runTask1Menu();                                   // Task 1 sub-menu
Parcel* findParcel(const string& parcelID);               // NULL if not found
bool    isValidTransition(ParcelStatus from, ParcelStatus to);

// Change status WITH validation (e.g. called by Task 2 when a request ends).
bool    updateParcelStatus(const string& parcelID, ParcelStatus newStatus);

// Change status WITHOUT transition rules (e.g. called by Task 4 "undo" to
// restore a previous status). Queues are re-synchronised automatically.
bool    forceParcelStatus(const string& parcelID, ParcelStatus newStatus);

// Save every parcel to task1_parcels.txt (also called automatically after every
// change, and parcels are loaded automatically the first time they are needed).
void    saveParcels();

#endif // TASK1_H
