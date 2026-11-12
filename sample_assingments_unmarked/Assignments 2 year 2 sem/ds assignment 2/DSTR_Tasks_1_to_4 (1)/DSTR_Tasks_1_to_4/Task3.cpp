/*
 * ============================================================================
 *  Module  : Task 3 - Collection Counter and Delivery Resource Management
 *  Member 3 - Thu Thu San
 *
 *  WORKFLOW IMPLEMENTED
 *    Register resources -> AVAILABLE pool (circular queue per resource type)
 *    Parcel (routed by Task 1) -> allocate next resource (round-robin)
 *        -> resource OCCUPIED -> release (transaction counted) -> back to the
 *           REAR of the circular queue.
 *    No resource free -> parcel joins the WAIT LIST (FIFO) and is dispatched
 *    automatically the moment a suitable resource becomes available.
 *
 *  DATA STRUCTURES (all hand-written, no STL containers)
 *    ResourceList          singly linked list   master record of every resource
 *    ResourceCircularQueue circular array queue available resources, one queue
 *                                               per type -> fair round-robin
 *    WaitList              linked-list queue    parcels waiting for a resource
 *
 *  WHY A CIRCULAR QUEUE?
 *    The brief asks for "repeated or cyclic processing". A resource that has
 *    just finished a job is re-inserted at the REAR, so the resource that has
 *    been idle the longest is always served next (FRONT). Jobs therefore
 *    rotate evenly over all counters/staff (no counter is overloaded while
 *    another sits idle). Array slots are re-used by wrapping the indices with
 *    modulo, so no memory is wasted and no element is ever shifted on
 *    enqueue/dequeue.
 *
 *  KEY COMPLEXITIES  (n = resources, w = waiting parcels, CAP = 10)
 *    allocate next resource (dequeue)    O(1)
 *    release resource (enqueue)          O(1)
 *    take a chosen resource out of pool  O(CAP)  = O(1) because CAP is a constant
 *    find resource by ID / by parcel     O(n)
 *    dispatch waiting parcels            O(w x 2)  (one pass over the wait list)
 *    utilisation ranking (insertion sort)O(n^2) for n <= 40
 *
 *  SAVING   : resources, current assignments and the wait list are written to
 *             task3_resources.txt after every action and read back at the next
 *             start (Task 1 and Task 2 save their own data the same way).
 *
 *  INTEGRATION (no other member's file is modified)
 *    Task 1 : uses findParcel() and the Parcel route/status fields to decide
 *             which resource type a parcel needs and whether it is eligible.
 *             Task 3 NEVER changes a parcel's status (Task 1/2 own that), so the
 *             existing Task 1/2 workflow is not disturbed.
 *    Task 2 : Task 2 calls Task 3 when a request starts processing (resource
 *             assigned) and when it ends (resource released). Task 3 reads the
 *             parcel's Request ID with getActiveRequestID().
 *    Task 4 : logActivity() is called for every assignment and release.
 *    Auto-sync: before each operation Task 3 compares every assignment with the
 *             current parcel status. If Task 2 already completed / cancelled the
 *             parcel (Collected, Returned, Cancelled, Missing ...) the resource
 *             is released automatically, so resource data never goes stale.
 * ============================================================================
 */

#include "Task3.hpp"
#include "Task1.hpp"
#include "Task2.hpp"
#include "Task4.hpp"
#include <iomanip>
#include <fstream>

namespace {   // everything below is private to this file

// ============================================================================
//  SECTION 1 : TYPES AND CONSTANTS
// ============================================================================
enum ResourceType {
    RES_COLLECTION_COUNTER = 0,
    RES_DELIVERY_DESK,
    RES_SPECIAL_COUNTER,
    RES_DELIVERY_PERSONNEL,
    RES_TYPE_COUNT                // sentinel = number of types
};

enum ResourceStatus {
    RES_AVAILABLE = 0,
    RES_OCCUPIED,
    RES_UNAVAILABLE,
    RES_MAINTENANCE
};

const int MAX_PER_TYPE = 10;                       // capacity of each circular queue
const int MAX_RESOURCES = MAX_PER_TYPE * RES_TYPE_COUNT;

string typeToText(ResourceType t) {
    switch (t) {
    case RES_COLLECTION_COUNTER:  return "Collection Counter";
    case RES_DELIVERY_DESK:       return "Delivery Desk";
    case RES_SPECIAL_COUNTER:     return "Special-Handling Counter";
    case RES_DELIVERY_PERSONNEL:  return "Delivery Personnel";
    default:                      return "Unknown";
    }
}

// Prefix used when a Resource ID is generated (CC01, DD01, SH01, DP01 ...).
string typePrefix(ResourceType t) {
    switch (t) {
    case RES_COLLECTION_COUNTER:  return "CC";
    case RES_DELIVERY_DESK:       return "DD";
    case RES_SPECIAL_COUNTER:     return "SH";
    case RES_DELIVERY_PERSONNEL:  return "DP";
    default:                      return "XX";
    }
}

string resStatusToText(ResourceStatus s) {
    switch (s) {
    case RES_AVAILABLE:    return "Available";
    case RES_OCCUPIED:     return "Occupied";
    case RES_UNAVAILABLE:  return "Unavailable";
    case RES_MAINTENANCE:  return "Maintenance";
    default:               return "Unknown";
    }
}

// ---------------------------------------------------------------------------
// One counter / desk / delivery person.
// ---------------------------------------------------------------------------
struct Resource {
    string         id;
    ResourceType   type;
    string         location;           // "-" when not applicable
    ResourceStatus status;
    string         currentParcelID;    // "" when not occupied
    string         currentRequestID;   // "" when none / not supplied
    int            transactions;       // jobs completed by this resource
    long           busySeconds;        // total time spent occupied (finished jobs)
    time_t         assignedAt;         // start of the current job
    time_t         registeredAt;
    Resource*      next;

    Resource() : type(RES_COLLECTION_COUNTER), status(RES_AVAILABLE),
        transactions(0), busySeconds(0), assignedAt(0), registeredAt(0), next(nullptr) {}
};

// ============================================================================
//  SECTION 2 : DATA STRUCTURE 1 - ResourceList (singly linked list)
//  Master record of all resources. Nodes stay in memory until the resource is
//  de-registered, so the Resource* held by the circular queues stay valid.
// ============================================================================
class ResourceList {
private:
    Resource* head;
    Resource* tail;
    int       count;
    int       idCounter[RES_TYPE_COUNT];     // never re-used -> IDs stay unique

public:
    ResourceList() : head(nullptr), tail(nullptr), count(0) {
        for (int i = 0; i < RES_TYPE_COUNT; i++) idCounter[i] = 0;
    }
    ~ResourceList() {
        while (head != nullptr) {
            Resource* temp = head;
            head = head->next;
            delete temp;
        }
    }
    ResourceList(const ResourceList&) = delete;
    ResourceList& operator=(const ResourceList&) = delete;

    int       size() const { return count; }
    Resource* first() const { return head; }

    int countOfType(ResourceType t) const {
        int n = 0;
        for (Resource* cur = head; cur != nullptr; cur = cur->next)
            if (cur->type == t) n++;
        return n;
    }

    // Append a new resource with an auto-generated unique ID. O(1).
    Resource* add(ResourceType t, const string& location) {
        Resource* r = new Resource();
        idCounter[t]++;
        string num = to_string(idCounter[t]);
        while (num.size() < 2) num = "0" + num;
        r->id = typePrefix(t) + num;
        r->type = t;
        r->location = location;
        r->status = RES_AVAILABLE;
        r->registeredAt = time(nullptr);
        if (head == nullptr) head = tail = r;
        else { tail->next = r; tail = r; }
        count++;
        return r;
    }

    // Re-create a resource read from the save file (keeps its old ID). O(1).
    Resource* addRestored(const string& id, ResourceType t, const string& location,
        ResourceStatus st, int transactions, long busy) {
        Resource* r = new Resource();
        r->id = id;
        r->type = t;
        r->location = location;
        r->status = st;
        r->transactions = transactions;
        r->busySeconds = busy;
        r->registeredAt = time(nullptr);
        int number = atoi(id.c_str() + 2);              // IDs are 2 letters + digits
        if (number > idCounter[t]) idCounter[t] = number;   // never re-issue an old ID
        if (head == nullptr) head = tail = r;
        else { tail->next = r; tail = r; }
        count++;
        return r;
    }

    // Linear search by Resource ID. O(n).
    Resource* findByID(const string& id) const {
        for (Resource* cur = head; cur != nullptr; cur = cur->next)
            if (cur->id == id) return cur;
        return nullptr;
    }

    // Which resource is currently handling this parcel? O(n).
    Resource* findByParcel(const string& parcelID) const {
        for (Resource* cur = head; cur != nullptr; cur = cur->next)
            if (cur->status == RES_OCCUPIED && cur->currentParcelID == parcelID) return cur;
        return nullptr;
    }

    // Unlink and delete a resource. O(n).
    bool remove(Resource* target) {
        Resource* prev = nullptr;
        Resource* cur = head;
        while (cur != nullptr && cur != target) { prev = cur; cur = cur->next; }
        if (cur == nullptr) return false;
        if (prev == nullptr) head = cur->next; else prev->next = cur->next;
        if (cur == tail) tail = prev;
        delete cur;
        count--;
        return true;
    }
};

// ============================================================================
//  SECTION 3 : DATA STRUCTURE 2 - ResourceCircularQueue (array based)
//  Holds the AVAILABLE resources of ONE type, in the order they became free.
//    front = index of the next resource to serve
//    items are stored at (front + i) % MAX_PER_TYPE   (wrap-around)
//  Full / empty are told apart by the separate 'count' field.
// ============================================================================
class ResourceCircularQueue {
private:
    Resource* items[MAX_PER_TYPE];
    int       front;
    int       count;

public:
    ResourceCircularQueue() : front(0), count(0) {
        for (int i = 0; i < MAX_PER_TYPE; i++) items[i] = nullptr;
    }

    bool isEmpty() const { return count == 0; }
    bool isFull()  const { return count == MAX_PER_TYPE; }
    int  size()    const { return count; }

    // i-th resource from the front (0 = next to be served). O(1).
    Resource* at(int i) const { return (i < 0 || i >= count) ? nullptr : items[(front + i) % MAX_PER_TYPE]; }
    Resource* peek() const { return at(0); }

    // Insert at the REAR, wrapping around the array. O(1). false if full.
    bool enqueue(Resource* r) {
        if (isFull()) return false;
        items[(front + count) % MAX_PER_TYPE] = r;
        count++;
        return true;
    }

    // Remove from the FRONT. O(1). nullptr when empty.
    Resource* dequeue() {
        if (isEmpty()) return nullptr;
        Resource* r = items[front];
        items[front] = nullptr;
        front = (front + 1) % MAX_PER_TYPE;
        count--;
        return r;
    }

    // Take a specific resource out of the middle of the queue (e.g. it was
    // chosen manually, or it became unavailable). Later items shift one step
    // forward, the wrap-around is preserved. O(CAP) = constant.
    bool remove(const Resource* target) {
        int pos = -1;
        for (int i = 0; i < count; i++)
            if (at(i) == target) { pos = i; break; }
        if (pos < 0) return false;
        for (int i = pos; i < count - 1; i++)
            items[(front + i) % MAX_PER_TYPE] = items[(front + i + 1) % MAX_PER_TYPE];
        items[(front + count - 1) % MAX_PER_TYPE] = nullptr;
        count--;
        return true;
    }

    bool contains(const Resource* target) const {
        for (int i = 0; i < count; i++)
            if (at(i) == target) return true;
        return false;
    }
};

// ============================================================================
//  SECTION 4 : DATA STRUCTURE 3 - WaitList (linked-list FIFO queue)
//  Parcels that need a resource but none is free. First come, first served.
//  A parcel that LOST its resource half way (resource broke down) jumps ahead of
//  the normal waiting parcels (but stays behind earlier displaced ones) so it is
//  not punished with a second long wait.
// ============================================================================
struct WaitNode {
    string    parcelID;
    string    requestID;
    string    queuedAt;
    bool      displaced;       // true = lost a resource during processing
    WaitNode* next;
    WaitNode() : displaced(false), next(nullptr) {}
};

class WaitList {
private:
    WaitNode* head;
    WaitNode* tail;
    int       count;

public:
    WaitList() : head(nullptr), tail(nullptr), count(0) {}
    ~WaitList() {
        while (head != nullptr) {
            WaitNode* temp = head;
            head = head->next;
            delete temp;
        }
    }
    WaitList(const WaitList&) = delete;
    WaitList& operator=(const WaitList&) = delete;

    bool      isEmpty() const { return count == 0; }
    int       size() const { return count; }
    WaitNode* first() const { return head; }

    void enqueue(const string& parcelID, const string& requestID, bool displaced) {   // O(1)
        WaitNode* n = new WaitNode();
        n->parcelID = parcelID;
        n->requestID = requestID;
        n->queuedAt = getCurrentDateTime();
        n->displaced = displaced;
        if (displaced) {                       // priority: behind other displaced parcels, ahead of the rest
            WaitNode* prev = nullptr;
            WaitNode* cur = head;
            while (cur != nullptr && cur->displaced) { prev = cur; cur = cur->next; }
            n->next = cur;
            if (prev == nullptr) head = n; else prev->next = n;
            if (cur == nullptr) tail = n;
        }
        else {                                 // normal: insert at the rear
            if (tail == nullptr) head = tail = n;
            else { tail->next = n; tail = n; }
        }
        count++;
    }

    WaitNode* find(const string& parcelID) const {                                     // O(w)
        for (WaitNode* cur = head; cur != nullptr; cur = cur->next)
            if (cur->parcelID == parcelID) return cur;
        return nullptr;
    }

    int positionOf(const string& parcelID) const {                                     // 1-based, 0 = absent
        int pos = 1;
        for (WaitNode* cur = head; cur != nullptr; cur = cur->next, pos++)
            if (cur->parcelID == parcelID) return pos;
        return 0;
    }

    bool remove(const string& parcelID) {                                              // O(w)
        WaitNode* prev = nullptr;
        WaitNode* cur = head;
        while (cur != nullptr && cur->parcelID != parcelID) { prev = cur; cur = cur->next; }
        if (cur == nullptr) return false;
        if (prev == nullptr) head = cur->next; else prev->next = cur->next;
        if (cur == tail) tail = prev;
        delete cur;
        count--;
        return true;
    }
};

// ============================================================================
//  SECTION 5 : MODULE-LEVEL STORAGE
// ============================================================================
ResourceList          resources;                         // every registered resource
ResourceCircularQueue availablePool[RES_TYPE_COUNT];     // available resources per type
WaitList              waitList;                          // parcels waiting for a resource

// ============================================================================
//  SECTION 6 : ALLOCATION RULES AND VALIDATION
//
//  RULE 1 (suitability)  ONE route -> ONE resource type
//     Recipient Collection -> Collection Counter
//     Campus Delivery      -> Delivery Personnel   (door-to-door delivery)
//     Special Handling     -> Special-Handling Counter (fragile items never go
//                             to an ordinary counter)
//     Return to Sender     -> Delivery Desk
//  RULE 2 (fairness)     inside one type the resource at the FRONT of the
//                        circular queue (idle the longest) is taken first.
//  RULE 3 (waiting)      nobody free -> parcel joins the FIFO wait list and is
//                        dispatched automatically when a resource is freed.
// ============================================================================

// Fills 'out' with the resource type allowed for a route; returns how many (1, or 0
// when the route needs no resource). Kept as a list so more types could be added.
int suitableTypes(RouteAction route, ResourceType out[2]) {
    switch (route) {
    case ROUTE_COLLECTION:       out[0] = RES_COLLECTION_COUNTER; return 1;
    case ROUTE_DELIVERY:         out[0] = RES_DELIVERY_PERSONNEL; return 1;
    case ROUTE_SPECIAL_HANDLING: out[0] = RES_SPECIAL_COUNTER;    return 1;
    case ROUTE_RETURN:           out[0] = RES_DELIVERY_DESK;      return 1;
    default:                                                       return 0;
    }
}

bool isSuitableType(RouteAction route, ResourceType t) {
    ResourceType types[2];
    int n = suitableTypes(route, types);
    for (int i = 0; i < n; i++)
        if (types[i] == t) return true;
    return false;
}

string suitableTypesText(RouteAction route) {
    ResourceType types[2];
    int n = suitableTypes(route, types);
    string text;
    for (int i = 0; i < n; i++) {
        if (i > 0) text += " / ";
        text += typeToText(types[i]);
    }
    return text.empty() ? "none" : text;
}

// A parcel may only use a resource while its route/status say it still needs
// one. Returns false (with a reason) for unrouted, on-hold, missing, finished...
bool checkEligibility(const Parcel& p, string& reason) {
    switch (p.status) {
    case STATUS_COLLECTED: case STATUS_RETURNED: case STATUS_CANCELLED:
        reason = "parcel is already completed (" + statusToString(p.status) + ")";
        return false;
    case STATUS_MISSING:
        reason = "parcel is reported Missing";
        return false;
    default:
        break;
    }
    if (p.route == ROUTE_NONE) {
        reason = "parcel has not been sorted/routed yet (process it in Task 1 first)";
        return false;
    }
    if (p.route == ROUTE_HOLD || p.status == STATUS_ON_HOLD) {
        reason = "parcel is on hold for investigation";
        return false;
    }
    bool ok = false;
    ParcelStatus s = p.status;
    switch (p.route) {
    case ROUTE_COLLECTION:       ok = (s == STATUS_READY_FOR_COLLECTION); break;
    case ROUTE_DELIVERY:         ok = (s == STATUS_PROCESSING || s == STATUS_OUT_FOR_DELIVERY); break;
    case ROUTE_SPECIAL_HANDLING: ok = (s == STATUS_PROCESSING || s == STATUS_READY_FOR_COLLECTION); break;
    case ROUTE_RETURN:           ok = (s == STATUS_PROCESSING); break;
    default: break;
    }
    if (!ok) {
        reason = "status '" + statusToString(s) + "' is not valid for route '" + routeToString(p.route) + "'";
        return false;
    }
    return true;
}

// ---- text validation ------------------------------------------------------

// Location: 1-30 chars: letters, digits, space and - . , # ( )
bool isValidLocation(const string& s) {
    if (s.empty() || s.size() > 30) return false;
    for (size_t i = 0; i < s.size(); i++) {
        unsigned char c = (unsigned char)s[i];
        if (!(isalnum(c) || c == ' ' || c == '-' || c == '.' || c == ',' || c == '#' || c == '(' || c == ')'))
            return false;
    }
    return true;
}

// Request ID typed by staff: "SR" followed by 1-6 digits (format used by Task 2).
bool isValidRequestID(const string& s) {
    if (s.size() < 3 || s.size() > 8 || s[0] != 'S' || s[1] != 'R') return false;
    for (size_t i = 2; i < s.size(); i++)
        if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

string formatDuration(long seconds) {
    if (seconds < 0) seconds = 0;
    long h = seconds / 3600, m = (seconds % 3600) / 60, s = seconds % 60;
    string out;
    char buf[40];
    snprintf(buf, sizeof(buf), "%02ld:%02ld:%02ld", h, m, s);
    out = buf;
    return out;
}

// Total busy time including the job that is still running.
long totalBusySeconds(const Resource& r) {
    long total = r.busySeconds;
    if (r.status == RES_OCCUPIED) total += (long)difftime(time(nullptr), r.assignedAt);
    return total;
}

// ============================================================================
//  SECTION 7 : CORE OPERATIONS (the only code that changes resource state)
// ============================================================================

void dispatchWaiting();     // forward declaration (used by release/update code)

// Put resource 'r' to work on a parcel. Resource must NOT be in the pool.
void assignTo(Resource* r, Parcel* parcel, const string& requestID) {
    r->status = RES_OCCUPIED;
    r->currentParcelID = parcel->parcelID;
    // Request ID comes from Task 2 automatically when the caller did not supply one.
    r->currentRequestID = requestID.empty() ? getActiveRequestID(parcel->parcelID) : requestID;
    r->assignedAt = time(nullptr);
    string st = statusToString(parcel->status);     // parcel status is NOT changed by Task 3
    logActivity(parcel->parcelID, "Resource Assignment", st, st, g_staffID);
}

// Free an occupied resource.
//   counted   : true  -> job finished normally, transactions++
//   newStatus : RES_AVAILABLE re-inserts it at the REAR of the circular queue,
//               anything else keeps it out of the pool.
void releaseResource(Resource* r, bool counted, ResourceStatus newStatus) {
    string parcelID = r->currentParcelID;
    r->busySeconds += (long)difftime(time(nullptr), r->assignedAt);
    if (counted) r->transactions++;
    r->currentParcelID.clear();
    r->currentRequestID.clear();
    r->assignedAt = 0;
    r->status = newStatus;
    if (newStatus == RES_AVAILABLE) availablePool[r->type].enqueue(r);
    Parcel* p = findParcel(parcelID);
    string st = (p != nullptr) ? statusToString(p->status) : "-";
    logActivity(parcelID, "Resource Release", st, st, g_staffID);
}

// Take the next available suitable resource (RULE 1 + RULE 2). nullptr if none.
Resource* tryAllocate(RouteAction route) {
    ResourceType types[2];
    int n = suitableTypes(route, types);
    for (int i = 0; i < n; i++)
        if (!availablePool[types[i]].isEmpty())
            return availablePool[types[i]].dequeue();
    return nullptr;
}

// Explain WHY nothing could be allocated (all occupied / out of service / none registered).
string explainNoResource(RouteAction route) {
    ResourceType types[2];
    int n = suitableTypes(route, types);
    int registered = 0, occupied = 0, outOfService = 0;
    for (Resource* r = resources.first(); r != nullptr; r = r->next) {
        for (int i = 0; i < n; i++) {
            if (r->type != types[i]) continue;
            registered++;
            if (r->status == RES_OCCUPIED) occupied++;
            else if (r->status != RES_AVAILABLE) outOfService++;
        }
    }
    string head;
    if (registered == 0)               head = "No suitable resource is registered";
    else if (occupied == registered)   head = "All suitable resources are occupied";
    else if (outOfService == registered) head = "All suitable resources are unavailable / under maintenance";
    else                               head = "No suitable resource is free right now";
    return head + " (needs: " + suitableTypesText(route) + "; registered " + to_string(registered)
        + ", occupied " + to_string(occupied) + ", out of service " + to_string(outOfService) + ").";
}

enum AssignResult { ASSIGN_DONE, ASSIGN_QUEUED, ASSIGN_REJECTED };

// Automatic allocation: validate -> allocate -> otherwise wait list.
AssignResult autoAssign(Parcel* parcel, const string& requestID) {
    if (parcel == nullptr) {
        cout << "  [Error] Invalid parcel.\n";
        return ASSIGN_REJECTED;
    }
    string reason;
    if (!checkEligibility(*parcel, reason)) {
        cout << "  [Error] Cannot assign parcel " << parcel->parcelID << ": " << reason << ".\n";
        return ASSIGN_REJECTED;
    }
    Resource* current = resources.findByParcel(parcel->parcelID);
    if (current != nullptr) {                                       // DUPLICATE ACTIVE ASSIGNMENT
        cout << "  [Error] Parcel " << parcel->parcelID << " is already assigned to "
            << current->id << " (" << typeToText(current->type) << ").\n";
        return ASSIGN_REJECTED;
    }
    if (waitList.find(parcel->parcelID) != nullptr) {
        cout << "  [Error] Parcel " << parcel->parcelID << " is already in the wait list (position "
            << waitList.positionOf(parcel->parcelID) << ").\n";
        return ASSIGN_REJECTED;
    }
    Resource* r = tryAllocate(parcel->route);
    if (r != nullptr) {
        assignTo(r, parcel, requestID);
        cout << "  [Success] Parcel " << parcel->parcelID << " assigned to " << r->id << " ("
            << typeToText(r->type) << ", " << r->location << ").\n";
        return ASSIGN_DONE;
    }
    waitList.enqueue(parcel->parcelID, requestID, false);           // NO SUITABLE RESOURCE
    cout << "  [Waiting] " << explainNoResource(parcel->route) << "\n"
        << "            Parcel " << parcel->parcelID << " added to the wait list (position "
        << waitList.positionOf(parcel->parcelID) << "). It will be assigned automatically.\n";
    return ASSIGN_QUEUED;
}

// Give free resources to waiting parcels, oldest first. One pass, O(w).
// A parcel that cannot be served yet is skipped so it never blocks a parcel
// behind it that needs a different type of resource.
void dispatchWaiting() {
    WaitNode* cur = waitList.first();
    while (cur != nullptr) {
        WaitNode* nextNode = cur->next;                 // saved: 'cur' may be deleted
        Parcel* p = findParcel(cur->parcelID);
        string reason;
        string id = cur->parcelID;
        if (p == nullptr || !checkEligibility(*p, reason)) {
            waitList.remove(id);                        // no longer needs a resource
        }
        else {
            Resource* r = tryAllocate(p->route);
            if (r != nullptr) {
                assignTo(r, p, cur->requestID);
                cout << "  [Auto-dispatch] Waiting parcel " << id << " assigned to " << r->id
                    << " (" << typeToText(r->type) << ").\n";
                waitList.remove(id);
            }
        }
        cur = nextNode;
    }
}

// Keep Task 3 consistent with Task 1/2: release resources whose parcel is
// finished (or no longer eligible) and drop such parcels from the wait list.
bool syncWithParcels() {
    bool header = false;
    for (Resource* r = resources.first(); r != nullptr; r = r->next) {
        if (r->status != RES_OCCUPIED) continue;
        Parcel* p = findParcel(r->currentParcelID);
        string reason;
        if (p != nullptr && checkEligibility(*p, reason)) continue;
        if (!header) { cout << "\n  [Auto-sync] Updating resources from parcel status changes:\n"; header = true; }
        bool counted = (p != nullptr && (p->status == STATUS_COLLECTED || p->status == STATUS_RETURNED));
        string pid = r->currentParcelID;
        releaseResource(r, counted, RES_AVAILABLE);
        cout << "    - " << r->id << " released: parcel " << pid << " - "
            << (p == nullptr ? string("no longer exists") : reason)
            << (counted ? " (transaction counted)." : " (not counted).") << "\n";
    }
    WaitNode* cur = waitList.first();
    while (cur != nullptr) {
        WaitNode* nextNode = cur->next;
        Parcel* p = findParcel(cur->parcelID);
        string reason;
        if (p == nullptr || !checkEligibility(*p, reason)) {
            if (!header) { cout << "\n  [Auto-sync] Updating resources from parcel status changes:\n"; header = true; }
            cout << "    - Parcel " << cur->parcelID << " removed from wait list: "
                << (p == nullptr ? string("no longer exists") : reason) << ".\n";
            waitList.remove(string(cur->parcelID));
        }
        cur = nextNode;
    }
    size_t before = (size_t)waitList.size();
    dispatchWaiting();
    bool changed = header || before != (size_t)waitList.size();
    if (changed) cout << "\n";
    return changed;                                    // true = something was printed / changed
}

// ============================================================================
//  SECTION 8 : SAVING AND LOADING  (plain text file, survives a restart)
//
//  File : task3_resources.txt
//    one line per resource : id|type|location|status|jobs|busySeconds|parcel|request
//    one line per waiting parcel : WAIT|parcel|request|priority(0/1)
//  Parcels are now saved by Task 1, so current assignments and the wait list
//  can be restored too. On load every assignment is re-checked: if its parcel
//  no longer exists or is finished, the resource simply comes back Available.
// ============================================================================
const char* SAVE_FILE = "task3_resources.txt";
bool   dataLoaded = false;
string resourceLoadNotice;
bool   resourceNoticeShown = false;

void saveResources() {
    ofstream out(SAVE_FILE);
    if (!out) return;                                   // read-only folder: skip silently
    out << "TASK3_RESOURCES_V2\n";
    for (Resource* r = resources.first(); r != nullptr; r = r->next) {
        out << r->id << '|' << (int)r->type << '|' << r->location << '|' << (int)r->status << '|'
            << r->transactions << '|' << totalBusySeconds(*r) << '|'
            << r->currentParcelID << '|' << r->currentRequestID << '\n';
    }
    for (WaitNode* w = waitList.first(); w != nullptr; w = w->next)
        out << "WAIT|" << w->parcelID << '|' << w->requestID << '|' << (w->displaced ? 1 : 0) << '\n';
}

bool isDigits(const string& s) {
    if (s.empty() || s.size() > 9) return false;
    for (size_t i = 0; i < s.size(); i++)
        if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

// Split a line on '|' into at most 'maxFields' fields. Returns the real field count.
int splitFields(const string& line, string* f, int maxFields) {
    int n = 0;
    size_t start = 0;
    for (size_t i = 0; i <= line.size(); i++) {
        if (i == line.size() || line[i] == '|') {
            if (n < maxFields) f[n] = line.substr(start, i - start);
            n++;
            start = i + 1;
        }
    }
    return n;
}

// Read the save file. Every line is validated; damaged lines are skipped.
void loadResources() {
    ifstream in(SAVE_FILE);
    if (!in) return;                                    // first run: nothing saved yet
    string line;
    if (!getline(in, line)) return;
    line = trim(line);
    bool v2 = (line == "TASK3_RESOURCES_V2");
    if (!v2 && line != "TASK3_RESOURCES_V1") {
        resourceLoadNotice = string("  [Warning] ") + SAVE_FILE + " is not a valid save file and was ignored.\n";
        return;
    }
    int loaded = 0, skipped = 0, resumed = 0, waiting = 0;
    while (getline(in, line)) {
        line = trim(line);
        if (line.empty()) continue;
        string f[8];
        int n = splitFields(line, f, 8);

        if (f[0] == "WAIT") {                           // a parcel that was waiting for a resource
            Parcel* p = (n == 4) ? findParcel(f[1]) : nullptr;
            string reason;
            bool ok = p != nullptr && checkEligibility(*p, reason) &&
                resources.findByParcel(f[1]) == nullptr && waitList.find(f[1]) == nullptr &&
                (f[2].empty() || isValidRequestID(f[2])) && (f[3] == "0" || f[3] == "1");
            if (ok) { waitList.enqueue(f[1], f[2], f[3] == "1"); waiting++; }
            else skipped++;
            continue;
        }

        bool ok = (n == (v2 ? 8 : 6)) && isDigits(f[1]) && isDigits(f[3]) && isDigits(f[4]) && isDigits(f[5]);
        int type = 0, status = 0;
        if (ok) {
            type = atoi(f[1].c_str());
            status = atoi(f[3].c_str());
            ok = type >= 0 && type < RES_TYPE_COUNT && status >= 0 && status <= 3;
        }
        if (ok) {
            string prefix = typePrefix((ResourceType)type);
            ok = f[0].size() > prefix.size() && f[0].compare(0, prefix.size(), prefix) == 0 &&
                isDigits(f[0].substr(prefix.size()));
        }
        if (ok) ok = isValidLocation(f[2]);
        if (ok) ok = resources.findByID(f[0]) == nullptr && resources.countOfType((ResourceType)type) < MAX_PER_TYPE;
        if (!ok) { skipped++; continue; }

        // An Occupied resource is only restored if its parcel still needs it.
        bool resume = false;
        if (status == RES_OCCUPIED) {
            Parcel* p = (v2 ? findParcel(f[6]) : nullptr);
            string reason;
            resume = p != nullptr && checkEligibility(*p, reason) &&
                resources.findByParcel(f[6]) == nullptr && isSuitableType(p->route, (ResourceType)type) &&
                (f[7].empty() || isValidRequestID(f[7]));
        }
        Resource* r = resources.addRestored(f[0], (ResourceType)type, f[2],
            resume ? RES_OCCUPIED : (status == RES_OCCUPIED ? RES_AVAILABLE : (ResourceStatus)status),
            atoi(f[4].c_str()), atol(f[5].c_str()));
        if (resume) {
            r->currentParcelID = f[6];
            r->currentRequestID = f[7];
            r->assignedAt = time(nullptr);
            resumed++;
        }
        else if (r->status == RES_AVAILABLE) {
            availablePool[type].enqueue(r);
        }
        loaded++;
    }
    if (loaded > 0 || skipped > 0 || waiting > 0) {
        resourceLoadNotice = "  [Info] Loaded " + to_string(loaded) + " resource(s) from " + SAVE_FILE +
            " (" + to_string(resumed) + " busy, " + to_string(waiting) + " parcel(s) waiting)" +
            (skipped ? "; " + to_string(skipped) + " damaged/outdated line(s) skipped" : "") + ".\n";
    }
}

void ensureLoaded() {
    if (!dataLoaded) { dataLoaded = true; loadResources(); }
}

// ============================================================================
//  SECTION 9 : INPUT HELPERS
// ============================================================================

// Ask for a parcel ID. Returns nullptr when cancelled or invalid (message shown).
Parcel* promptParcel() {
    string id = toUpperStr(trim(readLine("  Parcel ID (0 to cancel): ")));
    if (id == "0") return nullptr;
    if (id.empty()) { cout << "  [Error] Parcel ID cannot be empty.\n"; return nullptr; }
    Parcel* p = findParcel(id);
    if (p == nullptr) cout << "  [Error] Parcel ID '" << id << "' not found. Register it in Task 1 first.\n";
    return p;
}

// ============================================================================
//  SECTION 10 : DISPLAY HELPERS
// ============================================================================
void printResourceHeader() {
    cout << left << setw(6) << "ID" << setw(25) << "Type" << setw(16) << "Location"
        << setw(12) << "Status" << setw(8) << "Parcel" << setw(9) << "Request"
        << setw(21) << "Parcel status" << "Jobs\n";
    cout << string(100, '-') << "\n";
}

void printResourceRow(const Resource& r) {
    Parcel* p = r.currentParcelID.empty() ? nullptr : findParcel(r.currentParcelID);   // live status from Task 1
    cout << left << setw(6) << r.id << setw(25) << typeToText(r.type)
        << setw(16) << r.location.substr(0, 15) << setw(12) << resStatusToText(r.status)
        << setw(8) << (r.currentParcelID.empty() ? "-" : r.currentParcelID)
        << setw(9) << (r.currentRequestID.empty() ? "-" : r.currentRequestID)
        << setw(21) << (p != nullptr ? statusToString(p->status) : string("-"))
        << r.transactions << "\n";
}

void printResourceDetails(const Resource& r) {
    cout << "\n  ---------- Resource Details ----------\n"
        << "  Resource ID      : " << r.id << "\n"
        << "  Type             : " << typeToText(r.type) << "\n"
        << "  Location         : " << r.location << "\n"
        << "  Status           : " << resStatusToText(r.status) << "\n"
        << "  Current Parcel   : " << (r.currentParcelID.empty() ? "-" : r.currentParcelID) << "\n"
        << "  Current Request  : " << (r.currentRequestID.empty() ? "-" : r.currentRequestID) << "\n"
        << "  Jobs completed   : " << r.transactions << "\n"
        << "  Total busy time  : " << formatDuration(totalBusySeconds(r)) << "\n"
        << "  --------------------------------------\n";
}

void printWaitList() {
    cout << left << setw(5) << "Pos" << setw(9) << "Parcel" << setw(22) << "Route"
        << setw(40) << "Needs" << "Waiting since\n";
    cout << string(88, '-') << "\n";
    int pos = 1;
    for (WaitNode* n = waitList.first(); n != nullptr; n = n->next, pos++) {
        Parcel* p = findParcel(n->parcelID);
        cout << left << setw(5) << pos << setw(9) << n->parcelID
            << setw(22) << (p ? routeToString(p->route) : "?")
            << setw(40) << (p ? suitableTypesText(p->route) : "?")
            << n->queuedAt << (n->displaced ? "  (priority: lost its resource)" : "") << "\n";
    }
}

bool requireResources() {
    if (resources.size() == 0) {                                  // EMPTY STRUCTURE
        cout << "  [Info] No counters or delivery staff yet. Use [5] Manage resources to add some\n"
            << "         or to load the sample set.\n";
        return false;
    }
    return true;
}

// ---- numbered pick lists: staff choose a NUMBER, no need to remember IDs ----
void printPickHeader() {
    cout << left << setw(5) << "No." << setw(7) << "ID" << setw(26) << "Type" << setw(18) << "Location"
        << setw(13) << "Status" << "Parcel\n";
    cout << string(80, '-') << "\n";
}

void printPickRow(int no, const Resource& r) {
    cout << left << setw(5) << no << setw(7) << r.id << setw(26) << typeToText(r.type)
        << setw(18) << r.location.substr(0, 17) << setw(13) << resStatusToText(r.status)
        << (r.currentParcelID.empty() ? "-" : r.currentParcelID) << "\n";
}

// Collect all resources (or only the occupied ones) into 'out'. Returns the count.
int collectResources(Resource** out, bool occupiedOnly) {
    int n = 0;
    for (Resource* r = resources.first(); r != nullptr && n < MAX_RESOURCES; r = r->next)
        if (!occupiedOnly || r->status == RES_OCCUPIED) out[n++] = r;
    return n;
}

// Show a numbered list and let staff pick one. nullptr = cancelled.
Resource* chooseFromList(Resource** list, int n, const string& prompt) {
    printPickHeader();
    for (int i = 0; i < n; i++) printPickRow(i + 1, *list[i]);
    int c = readInt(prompt, 0, n);
    return (c == 0) ? nullptr : list[c - 1];
}

// ============================================================================
//  SECTION 11 : MENU FUNCTIONS  (6 menu items, each one a complete task)
// ============================================================================

// Choose a resource type. Returns false if cancelled.
bool chooseType(ResourceType& t) {
    cout << "  [1] Collection Counter\n  [2] Delivery Desk\n"
        << "  [3] Special-Handling Counter\n  [4] Delivery Personnel\n";
    int c = readInt("  Resource type (0 to cancel): ", 0, 4);
    if (c == 0) return false;
    t = (ResourceType)(c - 1);
    return true;
}

// ---------------------------------------------------------------------------
// MENU 1 : Assign a parcel (automatic OR pick from a list of free resources)
// ---------------------------------------------------------------------------
void assignParcel() {
    printTitle("ASSIGN A PARCEL");
    Parcel* p = promptParcel();
    if (p == nullptr) return;
    string activeRequest = getActiveRequestID(p->parcelID);
    cout << "  Parcel " << p->parcelID << " | " << p->recipientName << " | "
        << statusToString(p->status) << " | route: " << routeToString(p->route)
        << " | request: " << (activeRequest.empty() ? "-" : activeRequest) << "\n";

    string reason;
    if (!checkEligibility(*p, reason)) {                                // not routed / finished / missing ...
        cout << "  [Error] Cannot assign parcel " << p->parcelID << ": " << reason << ".\n";
        return;
    }
    Resource* current = resources.findByParcel(p->parcelID);            // DUPLICATE ACTIVE ASSIGNMENT
    if (current != nullptr) {
        cout << "  [Error] Parcel " << p->parcelID << " is already assigned to " << current->id << " ("
            << typeToText(current->type) << ", " << current->location << ").\n"
            << "          Use [2] Finish a job first if you want to move it.\n";
        return;
    }
    if (waitList.find(p->parcelID) != nullptr) {
        cout << "  [Error] Parcel " << p->parcelID << " is already waiting (position "
            << waitList.positionOf(p->parcelID) << "). It will be assigned automatically.\n";
        return;
    }

    // Free resources of the type this parcel's route needs.
    Resource* choices[MAX_RESOURCES];
    int n = 0;
    ResourceType types[2];
    int typeCount = suitableTypes(p->route, types);
    for (int t = 0; t < typeCount; t++)
        for (int i = 0; i < availablePool[types[t]].size(); i++)
            choices[n++] = availablePool[types[t]].at(i);

    Resource* chosen = nullptr;
    if (n == 0) {
        cout << "  [Info] " << explainNoResource(p->route) << "\n";
        if (readInt("  [1] Put the parcel on the wait list   [0] Cancel: ", 0, 1) == 0) return;
    }
    else {
        cout << "\n  Free resources for this parcel (needs: " << suitableTypesText(p->route) << "):\n";
        printPickHeader();
        for (int i = 0; i < n; i++) printPickRow(i + 1, *choices[i]);
        cout << "  No. 1 is next in the fair rotation.\n";
        while (true) {
            string in = trim(readLine("  Press Enter = automatic (recommended), a number = choose, 0 = cancel: "));
            if (in.empty()) break;                                      // automatic
            if (in == "0") return;
            if (isDigits(in) && atoi(in.c_str()) >= 1 && atoi(in.c_str()) <= n) {
                chosen = choices[atoi(in.c_str()) - 1];
                break;
            }
            cout << "  [Error] Enter a number from 1 to " << n << ", press Enter, or 0 to cancel.\n";
        }
    }
    string requestID = getActiveRequestID(p->parcelID);               // from Task 2, no typing needed

    if (chosen != nullptr) {
        availablePool[chosen->type].remove(chosen);                     // leave the pool
        assignTo(chosen, p, requestID);
        cout << "  [Success] Parcel " << p->parcelID << " assigned to " << chosen->id << " ("
            << typeToText(chosen->type) << ", " << chosen->location << ").\n";
    }
    else {
        autoAssign(p, requestID);                                       // round-robin, or wait list
    }
}

// ---------------------------------------------------------------------------
// MENU 2 : Finish a job (release a busy resource)
// ---------------------------------------------------------------------------
void finishJob() {
    printTitle("FINISH A JOB");
    if (!requireResources()) return;
    Resource* busy[MAX_RESOURCES];
    int n = collectResources(busy, true);
    if (n == 0) {                                                       // INVALID RELEASE
        cout << "  [Info] Nobody is busy right now, so there is no job to finish.\n";
        return;
    }
    cout << "  Busy resources:\n";
    Resource* r = chooseFromList(busy, n, "  Choose a number (0 to cancel): ");
    if (r == nullptr) return;
    cout << "  [1] Job finished (counts as a completed job)\n"
        << "  [2] Release without finishing (not counted)\n";
    int c = readInt("  Choice (0 to cancel): ", 0, 2);
    if (c == 0) return;
    string pid = r->currentParcelID;
    releaseResource(r, c == 1, RES_AVAILABLE);
    cout << "  [Success] " << r->id << " is free again (parcel " << pid << " released"
        << (c == 1 ? ", jobs completed: " + to_string(r->transactions) : "") << ").\n";
    dispatchWaiting();                                                  // serve anyone waiting
}

// ---------------------------------------------------------------------------
// MENU 3 : Dashboard (availability + assignments + wait list on ONE screen)
// ---------------------------------------------------------------------------
void dashboard() {
    printTitle("DASHBOARD");
    if (!requireResources()) return;
    cout << left << setw(27) << "  Type" << setw(11) << "Free" << setw(10) << "Busy"
        << setw(13) << "Unavailable" << setw(13) << "Maintenance" << "Next in rotation\n";
    cout << string(88, '-') << "\n";
    int totals[4] = { 0, 0, 0, 0 };
    for (int t = 0; t < RES_TYPE_COUNT; t++) {
        int c[4] = { 0, 0, 0, 0 };
        for (Resource* r = resources.first(); r != nullptr; r = r->next)
            if (r->type == (ResourceType)t) c[r->status]++;
        Resource* nextR = availablePool[t].peek();
        cout << left << "  " << setw(25) << typeToText((ResourceType)t)
            << setw(11) << c[0] << setw(10) << c[1] << setw(13) << c[2] << setw(13) << c[3]
            << (nextR != nullptr ? nextR->id : string("-")) << "\n";
        for (int k = 0; k < 4; k++) totals[k] += c[k];
    }
    cout << string(88, '-') << "\n";
    cout << left << "  " << setw(25) << "TOTAL" << setw(11) << totals[0] << setw(10) << totals[1]
        << setw(13) << totals[2] << totals[3] << "\n\n";

    printResourceHeader();
    for (Resource* r = resources.first(); r != nullptr; r = r->next) printResourceRow(*r);

    cout << "\n  Parcels waiting for a resource: " << waitList.size() << "\n";
    if (!waitList.isEmpty()) printWaitList();
}

// ---------------------------------------------------------------------------
// MENU 4 : Change the status of a resource
// ---------------------------------------------------------------------------
void changeStatus() {
    printTitle("CHANGE STATUS");
    if (!requireResources()) return;
    Resource* all[MAX_RESOURCES];
    int n = collectResources(all, false);
    Resource* r = chooseFromList(all, n, "  Choose a number (0 to cancel): ");
    if (r == nullptr) return;
    printResourceDetails(*r);
    cout << "  [1] Available (free)\n  [2] Occupied (assign a parcel to it)\n"
        << "  [3] Unavailable\n  [4] Maintenance\n";
    int c = readInt("  New status (0 to cancel): ", 0, 4);
    if (c == 0) return;
    ResourceStatus target = (ResourceStatus)(c - 1);
    if (target == r->status) {
        cout << "  [Error] " << r->id << " is already " << resStatusToText(target) << ".\n";
        return;
    }

    if (target == RES_AVAILABLE) {
        if (r->status == RES_OCCUPIED) {                                // finish the job
            string pid = r->currentParcelID;
            releaseResource(r, true, RES_AVAILABLE);
            cout << "  [Success] Job on parcel " << pid << " finished (counted). " << r->id << " is free.\n";
        }
        else {                                                          // back in service
            r->status = RES_AVAILABLE;
            availablePool[r->type].enqueue(r);
            cout << "  [Success] " << r->id << " is back in service (rear of the "
                << typeToText(r->type) << " rotation).\n";
        }
        dispatchWaiting();
        return;
    }

    if (target == RES_OCCUPIED) {
        if (r->status != RES_AVAILABLE) {
            cout << "  [Error] " << r->id << " is " << resStatusToText(r->status)
                << ". Make it Available before assigning a parcel.\n";
            return;
        }
        Parcel* p = promptParcel();
        if (p == nullptr) return;
        string reason;
        if (!checkEligibility(*p, reason)) {
            cout << "  [Error] Cannot assign parcel " << p->parcelID << ": " << reason << ".\n";
            return;
        }
        Resource* current = resources.findByParcel(p->parcelID);
        if (current != nullptr) {
            cout << "  [Error] Parcel " << p->parcelID << " is already assigned to " << current->id << ".\n";
            return;
        }
        if (waitList.find(p->parcelID) != nullptr) {
            cout << "  [Error] Parcel " << p->parcelID << " is already in the wait list.\n";
            return;
        }
        if (!isSuitableType(p->route, r->type)) {
            cout << "  [Error] " << typeToText(r->type) << " cannot handle route '"
                << routeToString(p->route) << "'. Use: " << suitableTypesText(p->route) << ".\n";
            return;
        }
        availablePool[r->type].remove(r);
        assignTo(r, p, getActiveRequestID(p->parcelID));
        cout << "  [Success] " << r->id << " is now Occupied with parcel " << p->parcelID << ".\n";
        return;
    }

    // target is Unavailable or Maintenance
    if (r->status == RES_OCCUPIED) {                                    // BREAKS DOWN DURING PROCESSING
        string pid = r->currentParcelID;
        string rid = r->currentRequestID;
        releaseResource(r, false, target);
        cout << "  [Warning] " << r->id << " became " << resStatusToText(target)
            << " while handling parcel " << pid << ".\n";
        Parcel* p = findParcel(pid);
        string reason;
        if (p != nullptr && checkEligibility(*p, reason)) {
            waitList.enqueue(pid, rid, true);                           // priority in the wait list
            dispatchWaiting();
            Resource* now = resources.findByParcel(pid);
            if (now != nullptr)
                cout << "  [Reassigned] Parcel " << pid << " moved to " << now->id << ".\n";
            else
                cout << "  [Waiting] No other suitable resource is free. Parcel " << pid
                << " is first in the wait list (position " << waitList.positionOf(pid) << ").\n";
        }
    }
    else {
        availablePool[r->type].remove(r);                               // leaves the rotation
        r->status = target;
    }
    cout << "  [Success] " << r->id << " is now " << resStatusToText(target) << ".\n";
}

// ---------------------------------------------------------------------------
// MENU 5 : Manage resources (add / edit location / remove / sample set / reset)
// ---------------------------------------------------------------------------
void addResource() {
    printTitle("ADD A RESOURCE");
    ResourceType t;
    if (!chooseType(t)) return;
    if (resources.countOfType(t) >= MAX_PER_TYPE) {
        cout << "  [Error] Limit reached: at most " << MAX_PER_TYPE << " " << typeToText(t)
            << " resources can be registered.\n";
        return;
    }
    string location;
    while (true) {
        string in = trim(readLine(t == RES_DELIVERY_PERSONNEL
            ? "  Delivery zone, e.g. 'Block A-C' (press Enter to skip, 0 to cancel): "
            : "  Location, e.g. 'Level 1 Lobby' (0 to cancel): "));
        if (in == "0") return;
        if (in.empty() && t == RES_DELIVERY_PERSONNEL) { location = "-"; break; }
        if (in.empty()) { cout << "  [Error] Location cannot be empty for a counter/desk.\n"; continue; }
        if (!isValidLocation(in)) {
            cout << "  [Error] Invalid location (1-30 letters, digits, space and - . , # ( ) only).\n";
            continue;
        }
        location = in;
        break;
    }
    Resource* r = resources.add(t, location);
    availablePool[t].enqueue(r);
    cout << "  [Success] Added " << r->id << " - " << typeToText(t) << ". "
        << (t == RES_DELIVERY_PERSONNEL ? "Zone: " : "Location: ")
        << (location == "-" ? string("not set") : location) << ". Status: Available.\n";
    dispatchWaiting();                                  // a waiting parcel may be served at once
}

void editLocation() {
    printTitle("EDIT LOCATION");
    Resource* all[MAX_RESOURCES];
    int n = collectResources(all, false);
    Resource* r = chooseFromList(all, n, "  Choose a number (0 to cancel): ");
    if (r == nullptr) return;
    while (true) {
        string in = trim(readLine("  New location (0 to cancel): "));
        if (in == "0") return;
        if (in.empty() || !isValidLocation(in)) {
            cout << "  [Error] Invalid location (1-30 letters, digits, space and - . , # ( ) only).\n";
            continue;
        }
        r->location = in;
        cout << "  [Success] Location of " << r->id << " changed to " << in << ".\n";
        return;
    }
}

void removeResource() {
    printTitle("REMOVE A RESOURCE");
    Resource* all[MAX_RESOURCES];
    int n = collectResources(all, false);
    Resource* r = chooseFromList(all, n, "  Choose a number (0 to cancel): ");
    if (r == nullptr) return;
    if (r->status == RES_OCCUPIED) {                          // invalid operation
        cout << "  [Error] " << r->id << " is handling parcel " << r->currentParcelID
            << ". Finish the job or mark it Unavailable first.\n";
        return;
    }
    string id = r->id;
    availablePool[r->type].remove(r);
    resources.remove(r);
    cout << "  [Success] Resource " << id << " has been removed.\n";
}

// Adds a ready-made set so the system can be tested straight away.
void addSampleResources() {
    struct Sample { ResourceType type; const char* location; };
    static const Sample samples[] = {
        { RES_COLLECTION_COUNTER, "Level 1 Lobby" }, { RES_COLLECTION_COUNTER, "Level 1 Lobby" },
        { RES_COLLECTION_COUNTER, "Student Centre" }, { RES_DELIVERY_DESK, "Delivery Centre" },
        { RES_SPECIAL_COUNTER, "Counter S1" },        { RES_SPECIAL_COUNTER, "Counter S2" },
        { RES_DELIVERY_PERSONNEL, "Block A-C" },      { RES_DELIVERY_PERSONNEL, "Block D-F" },
        { RES_DELIVERY_PERSONNEL, "Hostel Zone" }
    };
    int added = 0, skipped = 0;
    for (size_t i = 0; i < sizeof(samples) / sizeof(samples[0]); i++) {
        if (resources.countOfType(samples[i].type) >= MAX_PER_TYPE) { skipped++; continue; }
        Resource* r = resources.add(samples[i].type, samples[i].location);
        availablePool[samples[i].type].enqueue(r);
        added++;
    }
    cout << "  [Success] " << added << " resource(s) added"
        << (skipped ? ", " + to_string(skipped) + " skipped (type full)" : "") << ".\n";
    dispatchWaiting();
}

void resetAllResources() {
    printTitle("REMOVE ALL RESOURCES");
    if (resources.size() == 0) { cout << "  [Info] There is nothing to remove.\n"; return; }
    for (Resource* r = resources.first(); r != nullptr; r = r->next)
        if (r->status == RES_OCCUPIED) {
            cout << "  [Error] " << r->id << " is still handling parcel " << r->currentParcelID
                << ". Finish all jobs first.\n";
            return;
        }
    if (readInt("  Remove ALL " + to_string(resources.size()) + " resources?  [1] Yes   [0] Cancel: ", 0, 1) == 0)
        return;
    while (resources.first() != nullptr) {
        Resource* r = resources.first();
        availablePool[r->type].remove(r);
        resources.remove(r);
    }
    cout << "  [Success] All resources removed.\n";
}

void manageResources() {
    printTitle("MANAGE RESOURCES");
    cout << "  [1] Add a counter / delivery person\n  [2] Edit a location\n  [3] Remove a resource\n"
        << "  [4] Add the sample set (3 collection, 1 desk, 2 special, 3 delivery)\n"
        << "  [5] Remove all resources (reset)\n";
    int c = readInt("  Choice (0 to cancel): ", 0, 5);
    if (c == 0) return;
    clearScreen();
    if (c != 1 && c != 4 && !requireResources()) return;
    switch (c) {
    case 1: addResource();          break;
    case 2: editLocation();         break;
    case 3: removeResource();       break;
    case 4: printTitle("SAMPLE SET"); addSampleResources(); break;
    case 5: resetAllResources();    break;
    }
}

// ---------------------------------------------------------------------------
// MENU 6 : Reports (utilisation ranking, find who handles a parcel)
// ---------------------------------------------------------------------------
void utilisationReport() {
    printTitle("UTILISATION REPORT");
    Resource* ranked[MAX_RESOURCES];
    int n = collectResources(ranked, false);

    // Insertion sort: most jobs first; ties -> longer busy time first.
    for (int i = 1; i < n; i++) {
        Resource* key = ranked[i];
        int j = i - 1;
        while (j >= 0 && (ranked[j]->transactions < key->transactions ||
            (ranked[j]->transactions == key->transactions &&
                totalBusySeconds(*ranked[j]) < totalBusySeconds(*key)))) {
            ranked[j + 1] = ranked[j];
            j--;
        }
        ranked[j + 1] = key;
    }

    int totalTx = 0;
    for (int i = 0; i < n; i++) totalTx += ranked[i]->transactions;

    cout << left << setw(6) << "Rank" << setw(7) << "ID" << setw(26) << "Type" << setw(11) << "Jobs done"
        << setw(11) << "Busy time" << "Share of all jobs\n";
    cout << string(88, '-') << "\n";
    for (int i = 0; i < n; i++) {
        Resource* r = ranked[i];
        int pct = (totalTx == 0) ? 0 : (r->transactions * 100) / totalTx;
        cout << left << setw(6) << (i + 1) << setw(7) << r->id << setw(26) << typeToText(r->type)
            << setw(11) << r->transactions << setw(11) << formatDuration(totalBusySeconds(*r))
            << string((size_t)(pct / 5), '#') << " " << pct << "%\n";
    }
    cout << string(88, '-') << "\n";
    cout << "  Total jobs completed : " << totalTx << "\n"
        << "  Average per resource : " << fixed << setprecision(1) << (double)totalTx / n << "\n";
    cout.unsetf(ios::fixed);
    cout << "  Busiest resource     : " << ranked[0]->id << " (" << ranked[0]->transactions << ")\n"
        << "  Least used           : " << ranked[n - 1]->id << " (" << ranked[n - 1]->transactions << ")\n";
    if (totalTx > 0 && ranked[0]->transactions - ranked[n - 1]->transactions >= 3)
        cout << "  [Note] Load is uneven - check whether some resources are often out of service.\n";
}

void findParcelAssignment() {
    printTitle("FIND A PARCEL");
    Parcel* p = promptParcel();
    if (p == nullptr) return;
    cout << "  Parcel " << p->parcelID << " | " << p->recipientName << " | parcel status: "
        << statusToString(p->status) << "\n";
    Resource* r = resources.findByParcel(p->parcelID);
    if (r != nullptr) {
        cout << "  It is being handled by:\n";
        printResourceDetails(*r);
    }
    else if (waitList.find(p->parcelID) != nullptr) {
        cout << "  Parcel " << p->parcelID << " is waiting for a resource (position "
            << waitList.positionOf(p->parcelID) << ").\n";
    }
    else {
        cout << "  Parcel " << p->parcelID << " is not assigned to any resource"
            << ((p->status == STATUS_COLLECTED || p->status == STATUS_RETURNED || p->status == STATUS_CANCELLED)
                ? " (its job is finished: " + statusToString(p->status) + ")." : ".") << "\n";
    }
}

void reportsMenu() {
    printTitle("REPORTS");
    cout << "  [1] Utilisation report (which resources did the most work)\n"
        << "  [2] Find a parcel (which resource is handling it?)\n";
    int c = readInt("  Choice (0 to cancel): ", 0, 2);
    if (c == 0) return;
    clearScreen();
    if (c == 1) {
        if (requireResources()) utilisationReport();
    }
    else {
        findParcelAssignment();
    }
}

// Count free / busy resources for the menu header.
void countFreeAndBusy(int& freeCount, int& busyCount) {
    freeCount = 0;
    busyCount = 0;
    for (Resource* r = resources.first(); r != nullptr; r = r->next) {
        if (r->status == RES_AVAILABLE) freeCount++;
        else if (r->status == RES_OCCUPIED) busyCount++;
    }
}

} // end anonymous namespace

// ============================================================================
//  SECTION 12 : PUBLIC INTERFACE
// ============================================================================
bool requestResourceForParcel(Parcel* parcel, const string& requestID) {
    ensureLoaded();
    bool done = (autoAssign(parcel, requestID) == ASSIGN_DONE);
    saveResources();
    return done;
}

bool releaseResourceOfParcel(const string& parcelID, bool completed) {
    ensureLoaded();
    Resource* r = resources.findByParcel(parcelID);
    if (r == nullptr) return false;
    releaseResource(r, completed, RES_AVAILABLE);
    dispatchWaiting();
    saveResources();
    return true;
}

bool refreshResourceAssignments() {
    ensureLoaded();
    bool changed = syncWithParcels();
    if (changed) saveResources();
    return changed;
}

string getAssignedResourceID(const string& parcelID) {
    ensureLoaded();
    Resource* r = resources.findByParcel(parcelID);
    return r == nullptr ? string("") : r->id;
}

void runTask3Menu() {
    ensureLoaded();
    if (!resourceLoadNotice.empty() && !resourceNoticeShown) {   // tell staff once what was restored
        resourceNoticeShown = true;
        cout << resourceLoadNotice;
        pressEnterToContinue();
    }

    static bool welcomed = false;                        // first visit with nothing saved
    if (!welcomed && resources.size() == 0) {
        welcomed = true;
        clearScreen();
        printTitle("WELCOME");
        cout << "  No counters or delivery staff are registered yet.\n"
            << "  [1] Load the sample set (recommended for testing)\n"
            << "  [2] Start empty and add my own\n";
        if (readInt("  Choice: ", 1, 2) == 1) {
            addSampleResources();
            saveResources();
            pressEnterToContinue();
        }
    }

    int choice = 0;
    do {
        if (syncWithParcels()) {                         // parcels finished elsewhere (Task 1 / 2)
            saveResources();
            pressEnterToContinue();                      // let staff read what was updated
        }
        int freeCount, busyCount;
        countFreeAndBusy(freeCount, busyCount);
        clearScreen();
        printTitle("COUNTERS & DELIVERY RESOURCES");
        cout << "  Free: " << freeCount << "   Busy: " << busyCount
            << "   Parcels waiting: " << waitList.size() << "   (staff " << g_staffID << ")\n";
        printLine('-');
        cout << "  [1] Assign a parcel to a counter / delivery person\n"
            << "  [2] Finish a job (free up a counter / delivery person)\n"
            << "  [3] Dashboard (who is free, busy or waiting)\n"
            << "  [4] Change status (free / busy / unavailable / maintenance)\n"
            << "  [5] Manage resources (add, edit, remove, sample set)\n"
            << "  [6] Reports (utilisation, find a parcel)\n"
            << "  [0] Back to main menu\n";
        printLine('-');
        choice = readInt("  Enter your choice: ", 0, 6);
        clearScreen();
        switch (choice) {
        case 1: assignParcel();      break;
        case 2: finishJob();         break;
        case 3: dashboard();         break;
        case 4: changeStatus();      break;
        case 5: manageResources();   break;
        case 6: reportsMenu();       break;
        default: break;
        }
        if (choice != 0) {
            saveResources();                             // keep the file up to date
            pressEnterToContinue();
        }
    } while (choice != 0);
}
