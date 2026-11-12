/*
 * ============================================================================
 * Module  : Task 1 - Parcel Intake, Sorting and Processing Module
 * Member 1 - Pwint Yati Oo(TP101449)
 * WORKFLOW IMPLEMENTED
 *    Register -> PENDING QUEUE -> Process (sort/route) -> ROUTING QUEUES
 *    (Collection / Delivery / Special Handling / Return / Hold)
 * ============================================================================
 */

#include "Common.hpp"
#include "Task1.hpp"
#include "Task2.hpp"
#include "Task3.hpp"
#include "Task4.hpp"
#include "Task5.hpp"
#include <iomanip>
#include <fstream>

  // ============================================================================
  //  SECTION 1 : DATA STRUCTURE IMPLEMENTATION
  // ============================================================================

  // ---------------------------- ParcelList -----------------------------------
ParcelList::ParcelList() : head(nullptr), tail(nullptr), count(0), idCounter(0) {}

ParcelList::~ParcelList() {
    while (head != nullptr) {          // free every node
        ParcelNode* temp = head;
        head = head->next;
        delete temp;
    }
}

// Append a copy of p at the tail. O(1). Returns a stable pointer to the stored record.
Parcel* ParcelList::add(const Parcel& p) {
    ParcelNode* node = new ParcelNode(p);
    if (head == nullptr) {             // empty list
        head = tail = node;
    }
    else {
        tail->next = node;
        tail = node;
    }
    count++;
    return &(node->data);
}

// Linear search by Parcel ID. O(n). Returns nullptr if not found.
Parcel* ParcelList::findByID(const string& parcelID) const {
    ParcelNode* cur = head;
    while (cur != nullptr) {
        if (cur->data.parcelID == parcelID) return &(cur->data);
        cur = cur->next;
    }
    return nullptr;
}

// Generate the next unused ID (P001, P002, ...). The loop skips IDs that were
// already typed in manually, so the generated ID is always unique.
string ParcelList::generateUniqueID() {
    string id;
    do {
        idCounter++;
        string num = to_string(idCounter);
        while (num.size() < 3) num = "0" + num;     // zero-pad to 3 digits
        id = "P" + num;
    } while (findByID(id) != nullptr);
    return id;
}

// ---------------------------- ParcelQueue ----------------------------------
ParcelQueue::ParcelQueue() : front(nullptr), rear(nullptr), count(0) {}

ParcelQueue::~ParcelQueue() {
    while (front != nullptr) {
        QueueNode* temp = front;
        front = front->next;
        delete temp;                    // only the node; the Parcel is owned by ParcelList
    }
}

// Add to the REAR. O(1).
void ParcelQueue::enqueue(Parcel* p) {
    QueueNode* node = new QueueNode(p);
    if (rear == nullptr) {              // queue was empty
        front = rear = node;
    }
    else {
        rear->next = node;
        rear = node;
    }
    count++;
}

// Remove from the FRONT. O(1). Returns nullptr when the queue is empty
// (caller must check, this prevents "processing an empty queue" crashes).
Parcel* ParcelQueue::dequeue() {
    if (isEmpty()) return nullptr;
    QueueNode* temp = front;
    Parcel* p = temp->parcel;
    front = front->next;
    if (front == nullptr) rear = nullptr;   // queue became empty
    delete temp;
    count--;
    return p;
}

// Look at the front parcel without removing it. O(1).
Parcel* ParcelQueue::peek() const {
    return isEmpty() ? nullptr : front->parcel;
}

// Remove a specific parcel from anywhere in the queue. O(n).
// Needed when a WAITING parcel is cancelled / reported missing / put on hold.
bool ParcelQueue::remove(const string& parcelID) {
    QueueNode* prev = nullptr;
    QueueNode* cur = front;
    while (cur != nullptr) {
        if (cur->parcel->parcelID == parcelID) {
            if (prev == nullptr) front = cur->next;     // removing the front node
            else                 prev->next = cur->next;
            if (cur == rear) rear = prev;               // removing the rear node
            delete cur;
            count--;
            return true;
        }
        prev = cur;
        cur = cur->next;
    }
    return false;
}

// ============================================================================
//  SECTION 2 : MODULE-LEVEL STORAGE
//  One master list + one pending queue + five routing queues (one per next
//  action). Each queue holds parcels waiting for the next stage.
// ============================================================================
static ParcelList  masterList;        // ALL parcels ever registered
static ParcelQueue pendingQueue;      // registered, waiting to be processed (FIFO)
static ParcelQueue collectionQueue;   // routed -> recipient collection
static ParcelQueue deliveryQueue;     // routed -> campus delivery
static ParcelQueue specialQueue;      // routed -> special handling
static ParcelQueue returnQueue;       // routed -> return to sender
static ParcelQueue holdQueue;         // routed -> on hold for investigation

// ============================================================================
//  SECTION 3 : DISPLAY HELPERS
// ============================================================================
static void printParcelHeader() {
    cout << left
        << setw(8) << "ID"
        << setw(12) << "Recipient"
        << setw(22) << "Name"
        << setw(16) << "Company"
        << setw(18) << "Type"
        << setw(21) << "Arrival"
        << "Status\n";
    cout << string(115, '-') << "\n";
}

static void printParcelRow(const Parcel& p) {
    cout << left
        << setw(8) << p.parcelID
        << setw(12) << p.recipientID
        << setw(22) << p.recipientName.substr(0, 21)
        << setw(16) << p.deliveryCompany.substr(0, 15)
        << setw(18) << typeToString(p.type)
        << setw(21) << p.arrivalDateTime
        << statusToString(p.status) << "\n";
}

static void printParcelDetails(const Parcel& p) {
    cout << "\n  ---------- Parcel Details ----------\n"
        << "  Parcel ID        : " << p.parcelID << "\n"
        << "  Recipient ID     : " << p.recipientID << "\n"
        << "  Recipient Name   : " << p.recipientName << "\n"
        << "  Delivery Company : " << p.deliveryCompany << "\n"
        << "  Parcel Type      : " << typeToString(p.type) << "\n"
        << "  Arrival Date/Time: " << p.arrivalDateTime << "\n"
        << "  Current Status   : " << statusToString(p.status) << "\n"
        << "  Routed To        : " << routeToString(p.route) << "\n"
        << "  ------------------------------------\n";
}

// Print a queue with a title (used by "view routing queues").
static void printQueue(const string& title, const ParcelQueue& q) {
    cout << "\n  >> " << title << " (" << q.size() << " parcel(s))\n";
    if (q.isEmpty()) { cout << "     (empty)\n"; return; }
    q.display();
}

// Defined here because it needs printParcelHeader/Row above.
void ParcelQueue::display() const {
    printParcelHeader();
    QueueNode* cur = front;
    int position = 1;
    while (cur != nullptr) {
        cout << position++ << ". ";            // queue position (1 = next to be served)
        printParcelRow(*(cur->parcel));
        cur = cur->next;
    }
}

// ============================================================================
//  SECTION 4 : VALIDATION HELPERS
// ============================================================================

// Recipient ID: 5-12 letters/digits (e.g. TP012345). Not empty.
static bool isValidRecipientID(const string& s) {
    return s.size() >= 5 && s.size() <= 12 && isAlphanumeric(s);
}

// Recipient name: 2-50 chars, letters, spaces and . ' - / only, at least one letter.
static bool isValidName(const string& s) {
    if (s.size() < 2 || s.size() > 50) return false;
    bool hasLetter = false;
    for (size_t i = 0; i < s.size(); i++) {
        unsigned char c = (unsigned char)s[i];
        if (isalpha(c)) hasLetter = true;
        else if (!(c == ' ' || c == '.' || c == '\'' || c == '-' || c == '/')) return false;
    }
    return hasLetter;
}

// Delivery company: 2-40 chars, letters/digits/space and & . - only.
static bool isValidCompany(const string& s) {
    if (s.size() < 2 || s.size() > 40) return false;
    for (size_t i = 0; i < s.size(); i++) {
        unsigned char c = (unsigned char)s[i];
        if (!(isalnum(c) || c == ' ' || c == '&' || c == '.' || c == '-')) return false;
    }
    return true;
}

// Parcel ID typed manually: 'P' followed by 3-6 digits (e.g. P015).
static bool isValidParcelID(const string& s) {
    if (s.size() < 4 || s.size() > 7 || s[0] != 'P') return false;
    for (size_t i = 1; i < s.size(); i++)
        if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

// Ask for one text field and keep asking until it is valid.
// Returns false if the user types 0 (cancel).
static bool promptValidated(const string& label, const string& hint,
    bool (*isValid)(const string&), string& value) {
    while (true) {
        string in = trim(readLine("  " + label + " (0 to cancel): "));
        if (in == "0") return false;
        if (in.empty()) {                                   // MISSING INFORMATION
            cout << "  [Error] " << label << " cannot be empty.\n";
            continue;
        }
        if (!isValid(in)) {                                 // INVALID INFORMATION
            cout << "  [Error] Invalid " << label << ". " << hint << "\n";
            continue;
        }
        value = in;
        return true;
    }
}

// A parcel is "final" when nothing more can happen to it.
static bool isFinalStatus(ParcelStatus s) {
    return s == STATUS_COLLECTED || s == STATUS_RETURNED || s == STATUS_CANCELLED;
}

// ============================================================================
//  SECTION 5 : STATUS TRANSITION RULES  (prevents invalid operations)
//
//   Received  -> Pending, Missing, Cancelled
//   Pending   -> Processing, On Hold, Missing, Cancelled
//   Processing-> Ready for Collection, Out for Delivery, On Hold, Returned,
//                Missing, Cancelled
//   Ready for Collection -> Collected, Returned, Missing, Cancelled
//   Out for Delivery     -> Collected (= delivered), Returned, Missing
//   On Hold   -> Pending (released), Returned, Missing, Cancelled
//   Missing   -> Pending (parcel found again)
//   Collected / Returned / Cancelled -> FINAL (no further change)
// ============================================================================
bool isValidTransition(ParcelStatus from, ParcelStatus to) {
    switch (from) {
    case STATUS_RECEIVED:
        return to == STATUS_PENDING || to == STATUS_MISSING || to == STATUS_CANCELLED;
    case STATUS_PENDING:
        return to == STATUS_PROCESSING || to == STATUS_ON_HOLD ||
            to == STATUS_MISSING || to == STATUS_CANCELLED;
    case STATUS_PROCESSING:
        return to == STATUS_READY_FOR_COLLECTION || to == STATUS_OUT_FOR_DELIVERY ||
            to == STATUS_ON_HOLD || to == STATUS_RETURNED ||
            to == STATUS_MISSING || to == STATUS_CANCELLED;
    case STATUS_READY_FOR_COLLECTION:
        return to == STATUS_COLLECTED || to == STATUS_RETURNED ||
            to == STATUS_MISSING || to == STATUS_CANCELLED;
    case STATUS_OUT_FOR_DELIVERY:
        return to == STATUS_COLLECTED || to == STATUS_RETURNED || to == STATUS_MISSING;
    case STATUS_ON_HOLD:
        return to == STATUS_PENDING || to == STATUS_RETURNED ||
            to == STATUS_MISSING || to == STATUS_CANCELLED;
    case STATUS_MISSING:
        return to == STATUS_PENDING;
    default:                    // Collected, Returned, Cancelled = final
        return false;
    }
}

// Name of the activity recorded in Task 4's history for a given new status.
static string activityTypeFor(ParcelStatus newStatus) {
    switch (newStatus) {
    case STATUS_COLLECTED: return "Collection Confirmation";
    case STATUS_CANCELLED: return "Cancellation";
    case STATUS_RETURNED:  return "Return Processing";
    case STATUS_MISSING:   return "Missing Report";
    default:               return "Status Change";
    }
}

// ============================================================================
//  SECTION 6 : CORE STATUS / QUEUE LOGIC (single place that changes a status)
// ============================================================================

// Remove a parcel from every queue it might be waiting in. O(n) worst case.
static void removeFromAllQueues(const string& id) {
    pendingQueue.remove(id);
    collectionQueue.remove(id);
    deliveryQueue.remove(id);
    specialQueue.remove(id);
    returnQueue.remove(id);
    holdQueue.remove(id);
}

// Keep the queues consistent with a parcel's new status.
static void syncQueues(Parcel* p, ParcelStatus newStatus) {
    switch (newStatus) {
    case STATUS_PENDING:            // (re)join the end of the pending queue
        removeFromAllQueues(p->parcelID);
        p->route = ROUTE_NONE;
        pendingQueue.enqueue(p);
        break;
    case STATUS_ON_HOLD:            // move to the hold queue
        removeFromAllQueues(p->parcelID);
        p->route = ROUTE_HOLD;
        holdQueue.enqueue(p);
        break;
    case STATUS_COLLECTED:          // parcel leaves every queue
    case STATUS_RETURNED:
    case STATUS_CANCELLED:
    case STATUS_MISSING:
        removeFromAllQueues(p->parcelID);
        break;
    default:                        // Processing etc.: handled by routeParcel()
        break;
    }
}

// Validated status change. Returns true on success, prints a message on failure.
static bool changeStatus(Parcel* p, ParcelStatus newStatus, const string& activityType) {
    if (p == nullptr) return false;

    if (isFinalStatus(p->status)) {                                     // already completed
        cout << "  [Error] Parcel " << p->parcelID << " is already "
            << statusToString(p->status) << ". A completed parcel cannot be changed.\n";
        return false;
    }
    if (p->status == newStatus) {
        cout << "  [Error] Parcel " << p->parcelID << " already has status '"
            << statusToString(newStatus) << "'.\n";
        return false;
    }
    if (!isValidTransition(p->status, newStatus)) {                     // illegal step
        cout << "  [Error] Invalid operation: cannot change '" << statusToString(p->status)
            << "' to '" << statusToString(newStatus) << "'.\n";
        return false;
    }

    ParcelStatus oldStatus = p->status;
    p->status = newStatus;
    syncQueues(p, newStatus);

    // ---- Integration hooks ----
    logActivity(p->parcelID, activityType, statusToString(oldStatus),
        statusToString(newStatus), g_staffID);                  // Task 4
    updateParcelInTree(p);                                              // Task 5
    return true;
}

// ============================================================================
//  SECTION 6B : SAVING AND LOADING  (text file, so data survives a restart)
//
//  File : task1_parcels.txt  - one parcel per line, fields separated by '|'
//  The pending / routing queues are NOT stored. They are rebuilt on load from
//  each parcel's status and route (registration order is kept).
//  Loading happens automatically the first time any module needs parcels;
//  saving happens after every change.
// ============================================================================
static const char* PARCEL_FILE = "task1_parcels.txt";
static bool   parcelsLoaded = false;
static string parcelLoadNotice;
static bool   parcelNoticeShown = false;

static void ensureParcelsLoaded();

static bool isDigitsOnly(const string& s) {
    if (s.empty() || s.size() > 9) return false;
    for (size_t i = 0; i < s.size(); i++)
        if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

void saveParcels() {
    ensureParcelsLoaded();                 // never overwrite the file before it was read
    ofstream out(PARCEL_FILE);
    if (!out) return;                      // read-only folder: skip silently
    out << "TASK1_PARCELS_V1\n";
    for (ParcelNode* n = masterList.getHead(); n != nullptr; n = n->next) {
        const Parcel& p = n->data;
        out << p.parcelID << '|' << p.recipientID << '|' << p.recipientName << '|'
            << p.deliveryCompany << '|' << (int)p.type << '|' << p.arrivalDateTime << '|'
            << (int)p.status << '|' << (int)p.route << '\n';
    }
}

// Read the save file. Every line is validated with the same rules as
// registration; damaged lines are skipped.
static void loadParcels() {
    ifstream in(PARCEL_FILE);
    if (!in) return;                       // first run: nothing saved yet
    string line;
    if (!getline(in, line) || trim(line) != "TASK1_PARCELS_V1") {
        parcelLoadNotice = string("  [Warning] ") + PARCEL_FILE + " is not a valid save file and was ignored.\n";
        return;
    }
    int loaded = 0, skipped = 0;
    while (getline(in, line)) {
        line = trim(line);
        if (line.empty()) continue;
        string f[8];
        int n = 0;
        size_t start = 0;
        for (size_t i = 0; i <= line.size(); i++) {
            if (i == line.size() || line[i] == '|') {
                if (n < 8) f[n] = line.substr(start, i - start);
                n++;
                start = i + 1;
            }
        }
        bool ok = (n == 8) && isValidParcelID(f[0]) && isValidRecipientID(f[1]) &&
            isValidName(f[2]) && isValidCompany(f[3]) &&
            isDigitsOnly(f[4]) && isDigitsOnly(f[6]) && isDigitsOnly(f[7]) &&
            f[5].size() == 19 && masterList.findByID(f[0]) == nullptr;
        int type = 0, status = 0, route = 0;
        if (ok) {
            type = atoi(f[4].c_str());
            status = atoi(f[6].c_str());
            route = atoi(f[7].c_str());
            ok = type >= TYPE_MIN && type <= TYPE_MAX && status >= 0 && status < STATUS_COUNT &&
                route >= ROUTE_NONE && route <= ROUTE_HOLD;
        }
        if (!ok) { skipped++; continue; }

        Parcel p;
        p.parcelID = f[0];
        p.recipientID = f[1];
        p.recipientName = f[2];
        p.deliveryCompany = f[3];
        p.type = (ParcelType)type;
        p.arrivalDateTime = f[5];
        p.status = (ParcelStatus)status;
        p.route = (RouteAction)route;

        // Make status and route agree (same rules as syncQueues / registration).
        if (p.status == STATUS_ON_HOLD) p.route = ROUTE_HOLD;
        else if (p.route == ROUTE_HOLD) p.route = ROUTE_NONE;
        if (p.status == STATUS_PENDING) p.route = ROUTE_NONE;
        if (p.status == STATUS_PROCESSING && p.route == ROUTE_NONE)
            p.status = STATUS_PENDING;     // was being processed when the program closed

        Parcel* stored = masterList.add(p);

        // Rebuild queue membership (completed / missing parcels are in no queue).
        if (!isFinalStatus(stored->status) && stored->status != STATUS_MISSING) {
            if (stored->status == STATUS_PENDING) pendingQueue.enqueue(stored);
            else if (stored->status == STATUS_ON_HOLD) holdQueue.enqueue(stored);
            else {
                switch (stored->route) {
                case ROUTE_COLLECTION:       collectionQueue.enqueue(stored); break;
                case ROUTE_DELIVERY:         deliveryQueue.enqueue(stored);   break;
                case ROUTE_SPECIAL_HANDLING: specialQueue.enqueue(stored);    break;
                case ROUTE_RETURN:           returnQueue.enqueue(stored);     break;
                default: break;
                }
            }
        }
        insertParcelToTree(stored);        // Task 5: keep its structure in step with the records
        loaded++;
    }
    if (loaded > 0 || skipped > 0) {
        parcelLoadNotice = "  [Info] Loaded " + to_string(loaded) + " parcel(s) from " + PARCEL_FILE +
            (skipped ? " (" + to_string(skipped) + " damaged line(s) skipped)" : "") + ".\n";
    }
}

static void ensureParcelsLoaded() {
    if (!parcelsLoaded) {
        parcelsLoaded = true;              // set first: loading must not re-enter itself
        loadParcels();
    }
}

// ============================================================================
//  SECTION 7 : PUBLIC FUNCTIONS FOR OTHER MODULES
// ============================================================================
Parcel* findParcel(const string& parcelID) {
    ensureParcelsLoaded();
    return masterList.findByID(parcelID);
}

bool updateParcelStatus(const string& parcelID, ParcelStatus newStatus) {
    ensureParcelsLoaded();
    Parcel* p = masterList.findByID(parcelID);
    if (p == nullptr) {
        cout << "  [Error] Parcel " << parcelID << " does not exist.\n";
        return false;
    }
    bool changed = changeStatus(p, newStatus, activityTypeFor(newStatus));
    if (changed) saveParcels();                                         // keep the file up to date
    return changed;
}

bool forceParcelStatus(const string& parcelID, ParcelStatus newStatus) {
    ensureParcelsLoaded();
    Parcel* p = masterList.findByID(parcelID);
    if (p == nullptr || newStatus < 0 || newStatus >= STATUS_COUNT) return false;
    p->status = newStatus;
    syncQueues(p, newStatus);
    updateParcelInTree(p);
    saveParcels();                                                      // keep the file up to date
    return true;
}

// ============================================================================
//  SECTION 8 : FUNCTIONAL REQUIREMENT 1 - REGISTER A NEW PARCEL
// ============================================================================
static void registerParcel() {
    printTitle("REGISTER NEW PARCEL");

    Parcel p;
    string recipientID, recipientName, company, manualID;

    // ---- collect and validate every field (prevents incomplete registration) ----
    if (!promptValidated("Recipient ID", "Use 5-12 letters/digits (e.g. TP012345).",
        isValidRecipientID, recipientID)) {
        cout << "  Registration cancelled.\n"; return;
    }
    if (!promptValidated("Recipient Name", "Use 2-50 letters/spaces only.",
        isValidName, recipientName)) {
        cout << "  Registration cancelled.\n"; return;
    }
    if (!promptValidated("Delivery Company", "Use 2-40 letters/digits (e.g. DHL, J&T Express).",
        isValidCompany, company)) {
        cout << "  Registration cancelled.\n"; return;
    }

    cout << "  Parcel types: 1.Standard  2.Large  3.Fragile  4.Document  5.Special Handling\n";
    int typeChoice = readInt("  Parcel Type (1-5, 0 to cancel): ", 0, TYPE_MAX);
    if (typeChoice == 0) { cout << "  Registration cancelled.\n"; return; }

    // ---- Parcel ID: auto-generated, or typed manually (courier tracking no.) ----
    while (true) {
        manualID = toUpperStr(trim(readLine("  Parcel ID (press Enter to auto-generate, 0 to cancel): ")));
        if (manualID == "0") { cout << "  Registration cancelled.\n"; return; }
        if (manualID.empty()) {                                    // auto-generate
            p.parcelID = masterList.generateUniqueID();
            break;
        }
        if (!isValidParcelID(manualID)) {
            cout << "  [Error] Invalid Parcel ID. Use 'P' followed by 3-6 digits (e.g. P015).\n";
            continue;
        }
        if (masterList.findByID(manualID) != nullptr) {            // DUPLICATE ID
            cout << "  [Error] Duplicate Parcel ID: " << manualID << " is already registered.\n";
            continue;
        }
        p.parcelID = manualID;
        break;
    }

    // ---- build the record ----
    p.recipientID = toUpperStr(recipientID);
    p.recipientName = recipientName;
    p.deliveryCompany = company;
    p.type = (ParcelType)typeChoice;
    p.arrivalDateTime = getCurrentDateTime();
    p.status = STATUS_PENDING;   // registered parcels go straight to the pending queue

    Parcel* stored = masterList.add(p);   // 1) master record (O(1))
    pendingQueue.enqueue(stored);         // 2) wait for processing (O(1))

    // ---- Integration hooks ----
    logActivity(stored->parcelID, "Parcel Registration", "-",
        statusToString(stored->status), g_staffID);     // Task 4
    insertParcelToTree(stored);                                  // Task 5

    cout << "\n  [Success] Parcel registered and added to the pending queue.";
    printParcelDetails(*stored);
    cout << "  Parcels waiting in queue: " << pendingQueue.size() << "\n";
}

// ============================================================================
//  SECTION 9 : FUNCTIONAL REQUIREMENT 2 - MAINTAIN AND LOCATE PARCEL RECORDS
// ============================================================================
static void displayAllParcels() {
    printTitle("ALL PARCEL RECORDS");
    cout << "  Total: " << masterList.getCount() << "\n\n";
    if (masterList.getCount() == 0) {
        cout << "  No parcels have been registered yet.\n";     // empty collection
        return;
    }
    printParcelHeader();
    for (ParcelNode* cur = masterList.getHead(); cur != nullptr; cur = cur->next)
        printParcelRow(cur->data);
}

static void displayPendingParcels() {
    printTitle("PENDING PARCELS");
    if (pendingQueue.isEmpty()) {
        cout << "  The pending queue is empty. No parcels are waiting.\n";
        return;
    }
    cout << "  (1 = next parcel to be processed)\n\n";
    pendingQueue.display();
}

static void searchParcelByID() {
    printTitle("SEARCH BY PARCEL ID");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID: ")));
    if (id.empty()) { cout << "  [Error] Parcel ID cannot be empty.\n"; return; }

    Parcel* p = masterList.findByID(id);
    if (p == nullptr) cout << "  [Not Found] No parcel with ID " << id << " exists.\n";
    else              printParcelDetails(*p);
}

static void searchParcelsByRecipient() {
    printTitle("SEARCH BY RECIPIENT ID");
    string rid = toUpperStr(trim(readLine("  Enter Recipient ID: ")));
    if (rid.empty()) { cout << "  [Error] Recipient ID cannot be empty.\n"; return; }

    int found = 0;
    cout << "\n";
    for (ParcelNode* cur = masterList.getHead(); cur != nullptr; cur = cur->next) {
        if (toUpperStr(cur->data.recipientID) == rid) {
            if (found == 0) printParcelHeader();
            printParcelRow(cur->data);
            found++;
        }
    }
    if (found == 0) cout << "  [Not Found] No parcels for recipient " << rid << ".\n";
    else            cout << "\n  " << found << " parcel(s) found.\n";
}

// ============================================================================
//  SECTION 10 : FUNCTIONAL REQUIREMENT 3 - SORT AND PROCESS INCOMING PARCELS
// ============================================================================

// ROUTING RULE (based on what each parcel type needs):
//   Missing/invalid recipient info -> On Hold   (cannot be delivered safely)
//   Fragile / Special Handling     -> Special Handling counter (needs care)
//   Large                          -> Campus Delivery (too bulky to carry away)
//   Document / Standard            -> Recipient Collection (small, quick pickup)
static RouteAction suggestRoute(const Parcel& p, string& reason) {
    if (!isValidRecipientID(p.recipientID) || !isValidName(p.recipientName)) {
        reason = "recipient information is incomplete/invalid";
        return ROUTE_HOLD;
    }
    switch (p.type) {
    case TYPE_FRAGILE:
    case TYPE_SPECIAL_HANDLING:
        reason = "fragile/special items need careful handling";
        return ROUTE_SPECIAL_HANDLING;
    case TYPE_LARGE:
        reason = "large parcels are too bulky for recipients to carry";
        return ROUTE_DELIVERY;
    default:
        reason = "small parcels/documents are quick to collect at a counter";
        return ROUTE_COLLECTION;
    }
}

// Move a processed parcel to the queue of its next stage.
static void routeParcel(Parcel* p, RouteAction route) {
    switch (route) {
    case ROUTE_COLLECTION:
        if (changeStatus(p, STATUS_READY_FOR_COLLECTION, "Status Change")) {
            p->route = route;
            collectionQueue.enqueue(p);
        }
        break;
    case ROUTE_DELIVERY:            // stays 'Processing' until Task 3 assigns a driver
        p->route = route;
        deliveryQueue.enqueue(p);
        break;
    case ROUTE_SPECIAL_HANDLING:
        p->route = route;
        specialQueue.enqueue(p);
        break;
    case ROUTE_RETURN:
        p->route = route;
        returnQueue.enqueue(p);
        break;
    case ROUTE_HOLD:               // changeStatus() puts it in the hold queue
        changeStatus(p, STATUS_ON_HOLD, "Status Change");
        break;
    default:
        return;
    }
    logActivity(p->parcelID, "Parcel Routing: " + routeToString(route),
        statusToString(p->status), statusToString(p->status), g_staffID);   // Task 4
    if (route != ROUTE_HOLD)
        createServiceRequest(p, route);                                             // Task 2
}

// Process ONE parcel that has already been removed from the pending queue.
static void processParcel(Parcel* p) {
    if (!changeStatus(p, STATUS_PROCESSING, "Status Change")) {
        pendingQueue.enqueue(p);        // could not process; put it back in the queue
        return;
    }
    printParcelDetails(*p);

    // Rule-based suggestion; staff may override after inspecting the parcel.
    string reason;
    RouteAction suggested = suggestRoute(*p, reason);
    cout << "  Suggested route : " << routeToString(suggested) << "  (" << reason << ")\n";
    cout << "  Routes: 1.Collection  2.Campus Delivery  3.Special Handling  4.Return to Sender  5.Hold\n";

    RouteAction chosen = suggested;
    while (true) {
        string in = trim(readLine("  Press Enter to accept, or type 1-5 to override: "));
        if (in.empty()) break;
        if (in.size() == 1 && in[0] >= '1' && in[0] <= '5') {
            chosen = (RouteAction)(in[0] - '0');    // ROUTE_COLLECTION(1) .. ROUTE_HOLD(5)
            break;
        }
        cout << "  [Error] Press Enter, or type a number from 1 to 5.\n";
    }

    routeParcel(p, chosen);
    cout << "\n  [Success] Parcel " << p->parcelID << " routed to: " << routeToString(p->route)
        << "  | New status: " << statusToString(p->status) << "\n";
}

// Process the parcel at the FRONT of the pending queue (first come, first served).
static void processNextParcel() {
    printTitle("PROCESS NEXT PARCEL");
    if (pendingQueue.isEmpty()) {                              // EMPTY COLLECTION
        cout << "  [Error] No pending parcels to process. The queue is empty.\n";
        return;
    }
    Parcel* p = pendingQueue.dequeue();
    cout << "  Parcel selected for processing: " << p->parcelID << "\n";
    processParcel(p);
}

// Process a chosen parcel by ID (with all safety checks).
static void processParcelByID() {
    printTitle("PROCESS A SPECIFIC PARCEL");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID: ")));
    if (id.empty()) { cout << "  [Error] Parcel ID cannot be empty.\n"; return; }

    Parcel* p = masterList.findByID(id);
    if (p == nullptr) { cout << "  [Not Found] No parcel with ID " << id << " exists.\n"; return; }

    if (isFinalStatus(p->status)) {                            // ALREADY COMPLETED
        cout << "  [Error] Parcel " << id << " is already " << statusToString(p->status)
            << ". A completed parcel cannot be processed again.\n";
        return;
    }
    if (p->status != STATUS_PENDING) {
        cout << "  [Error] Parcel " << id << " is '" << statusToString(p->status)
            << "', not waiting in the pending queue.\n";
        return;
    }
    pendingQueue.remove(id);           // take it out of the queue (O(n))
    processParcel(p);
}

// ============================================================================
//  SECTION 11 : FUNCTIONAL REQUIREMENT 4 - UPDATE PARCEL RECORDS
// ============================================================================

// Edit parcel details (name, company, recipient ID, type).
static void updateParcelDetails() {
    printTitle("UPDATE PARCEL DETAILS");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID: ")));
    Parcel* p = masterList.findByID(id);
    if (p == nullptr) { cout << "  [Not Found] Cannot update: parcel '" << id << "' does not exist.\n"; return; }
    if (isFinalStatus(p->status)) {
        cout << "  [Error] Parcel is already " << statusToString(p->status) << " and cannot be updated.\n";
        return;
    }

    printParcelDetails(*p);
    cout << "  1.Recipient ID  2.Recipient Name  3.Delivery Company  4.Parcel Type  0.Cancel\n";
    int choice = readInt("  Field to update: ", 0, 4);
    string value;

    switch (choice) {
    case 1:
        if (!promptValidated("New Recipient ID", "Use 5-12 letters/digits.", isValidRecipientID, value)) return;
        p->recipientID = toUpperStr(value);
        break;
    case 2:
        if (!promptValidated("New Recipient Name", "Use 2-50 letters/spaces only.", isValidName, value)) return;
        p->recipientName = value;
        break;
    case 3:
        if (!promptValidated("New Delivery Company", "Use 2-40 letters/digits.", isValidCompany, value)) return;
        p->deliveryCompany = value;
        break;
    case 4: {
        if (p->status != STATUS_PENDING) {          // type decides routing, so lock it after processing
            cout << "  [Error] Parcel type can only be changed while the parcel is Pending.\n";
            return;
        }
        cout << "  1.Standard  2.Large  3.Fragile  4.Document  5.Special Handling\n";
        int t = readInt("  New Parcel Type (1-5, 0 to cancel): ", 0, TYPE_MAX);
        if (t == 0) return;
        p->type = (ParcelType)t;
        break;
    }
    default:
        cout << "  Update cancelled.\n";
        return;
    }

    logActivity(p->parcelID, "Parcel Update", statusToString(p->status),
        statusToString(p->status), g_staffID);          // Task 4
    updateParcelInTree(p);                                       // Task 5
    cout << "  [Success] Parcel updated.";
    printParcelDetails(*p);
}

// Change status: collection, delivery, return, cancellation, etc.
static void changeParcelStatusMenu() {
    printTitle("UPDATE PARCEL STATUS");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID: ")));
    Parcel* p = masterList.findByID(id);
    if (p == nullptr) { cout << "  [Not Found] Parcel '" << id << "' does not exist.\n"; return; }

    cout << "  Current status: " << statusToString(p->status) << "\n";
    if (isFinalStatus(p->status)) {
        cout << "  [Error] Parcel is already " << statusToString(p->status)
            << ". No further changes are allowed.\n";
        return;
    }

    // Show only the statuses that are legal from the current status.
    cout << "  Allowed next statuses:\n";
    for (int s = 0; s < STATUS_COUNT; s++)
        if (isValidTransition(p->status, (ParcelStatus)s))
            cout << "    " << (s + 1) << ". " << statusToString((ParcelStatus)s) << "\n";

    int choice = readInt("  Choose status number (see list, 0 to cancel): ", 0, STATUS_COUNT);
    if (choice == 0) { cout << "  Update cancelled.\n"; return; }
    ParcelStatus newStatus = (ParcelStatus)(choice - 1);

    if (newStatus == STATUS_CANCELLED) {                       // confirm destructive action
        string yn = toUpperStr(trim(readLine("  Cancel this parcel permanently? (Y/N): ")));
        if (yn != "Y") { cout << "  Cancellation aborted.\n"; return; }
    }
    if (changeStatus(p, newStatus, activityTypeFor(newStatus)))
        cout << "  [Success] Parcel " << p->parcelID << " is now: " << statusToString(p->status) << "\n";
}

// A parcel reported as missing.
static void reportMissingParcel() {
    printTitle("REPORT MISSING PARCEL");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID: ")));
    Parcel* p = masterList.findByID(id);
    if (p == nullptr) { cout << "  [Not Found] Parcel '" << id << "' does not exist.\n"; return; }
    if (p->status == STATUS_MISSING) { cout << "  [Error] Parcel is already reported as missing.\n"; return; }

    if (changeStatus(p, STATUS_MISSING, "Missing Report"))
        cout << "  [Success] Parcel " << id << " marked as MISSING and removed from all queues.\n";
}

// ============================================================================
//  SECTION 12 : EXTRA FEATURES (innovation): routing queues, merge sort, stats
// ============================================================================
static void viewRoutingQueues() {
    printTitle("ROUTING QUEUES");
    printQueue("Recipient Collection", collectionQueue);
    printQueue("Campus Delivery", deliveryQueue);
    printQueue("Special Handling", specialQueue);
    printQueue("Return to Sender", returnQueue);
    printQueue("On Hold", holdQueue);
}

// ---- Merge sort on an array of Parcel pointers: O(n log n), stable ----
static bool comesBefore(const Parcel* a, const Parcel* b, int key) {
    switch (key) {
    case 1: if (a->type != b->type) return a->type < b->type; break;
    case 2: {
        string x = toUpperStr(a->recipientName), y = toUpperStr(b->recipientName);
        if (x != y) return x < y;
        break;
    }
    case 3: if (a->arrivalDateTime != b->arrivalDateTime) return a->arrivalDateTime < b->arrivalDateTime; break;
    case 4: if (a->status != b->status) return a->status < b->status; break;
    }
    return a->parcelID < b->parcelID;      // tie-breaker
}

static void mergeSort(Parcel** arr, Parcel** tmp, int lo, int hi, int key) {
    if (lo >= hi) return;                  // 0 or 1 element is already sorted
    int mid = lo + (hi - lo) / 2;
    mergeSort(arr, tmp, lo, mid, key);     // sort left half
    mergeSort(arr, tmp, mid + 1, hi, key); // sort right half
    int i = lo, j = mid + 1, k = lo;       // merge the two sorted halves
    while (i <= mid && j <= hi) {
        if (comesBefore(arr[j], arr[i], key)) tmp[k++] = arr[j++];
        else                                   tmp[k++] = arr[i++];
    }
    while (i <= mid) tmp[k++] = arr[i++];
    while (j <= hi)  tmp[k++] = arr[j++];
    for (k = lo; k <= hi; k++) arr[k] = tmp[k];
}

static void displaySortedParcels() {
    printTitle("DISPLAY PARCELS SORTED");
    int n = masterList.getCount();
    if (n == 0) { cout << "  No parcels to sort.\n"; return; }

    cout << "  Sort by: 1.Parcel Type  2.Recipient Name  3.Arrival Time  4.Status  0.Cancel\n";
    int key = readInt("  Choice: ", 0, 4);
    if (key == 0) return;

    // Copy the pointers to a plain array (not an STL container), then sort it.
    Parcel** arr = new Parcel * [n];
    Parcel** tmp = new Parcel * [n];
    int i = 0;
    for (ParcelNode* cur = masterList.getHead(); cur != nullptr; cur = cur->next)
        arr[i++] = &(cur->data);

    mergeSort(arr, tmp, 0, n - 1, key);

    cout << "\n";
    printParcelHeader();
    for (i = 0; i < n; i++) printParcelRow(*arr[i]);
    delete[] arr;
    delete[] tmp;
}

static void showStatistics() {
    printTitle("PARCEL STATISTICS");
    int byStatus[STATUS_COUNT] = { 0 };
    int byType[TYPE_MAX + 1] = { 0 };
    for (ParcelNode* cur = masterList.getHead(); cur != nullptr; cur = cur->next) {
        byStatus[cur->data.status]++;
        byType[cur->data.type]++;
    }
    cout << "  Total registered parcels: " << masterList.getCount() << "\n\n  By status:\n";
    for (int s = 0; s < STATUS_COUNT; s++)
        cout << "    " << left << setw(22) << statusToString((ParcelStatus)s) << byStatus[s] << "\n";
    cout << "\n  By type:\n";
    for (int t = TYPE_MIN; t <= TYPE_MAX; t++)
        cout << "    " << left << setw(22) << typeToString((ParcelType)t) << byType[t] << "\n";
    cout << "\n  Queue sizes -> Pending: " << pendingQueue.size()
        << " | Collection: " << collectionQueue.size()
        << " | Delivery: " << deliveryQueue.size()
        << " | Special: " << specialQueue.size()
        << " | Return: " << returnQueue.size()
        << " | Hold: " << holdQueue.size() << "\n";
}

// ============================================================================
//  TASK 1 MENU
// ============================================================================
void runTask1Menu() {
    ensureParcelsLoaded();
    if (!parcelLoadNotice.empty() && !parcelNoticeShown) {     // tell staff once what was restored
        parcelNoticeShown = true;
        cout << parcelLoadNotice;
        pressEnterToContinue();
    }
    int choice;
    do {
        clearScreen();
        printTitle("PARCEL INTAKE & PROCESSING");
        cout << "  REGISTRATION\n"
            << "    [1]  Register new parcel\n"
            << "\n  SEARCH & VIEW\n"
            << "    [2]  Display all parcels\n"
            << "    [3]  Display pending parcels (queue)\n"
            << "    [4]  Search by Parcel ID\n"
            << "    [5]  Search by Recipient ID\n"
            << "    [11] View routing queues\n"
            << "    [12] Display parcels sorted\n"
            << "\n  PROCESSING\n"
            << "    [6]  Process next parcel\n"
            << "    [7]  Process a specific parcel\n"
            << "\n  UPDATES\n"
            << "    [8]  Update parcel details\n"
            << "    [9]  Update parcel status\n"
            << "    [10] Report missing parcel\n"
            << "\n  REPORTS\n"
            << "    [13] Parcel statistics\n"
            << "\n    [0]  Back to main menu\n";
        printLine('-');
        choice = readInt("  Enter your choice: ", 0, 13);

        if (choice == 0) break;          // go back before the "press Enter" pause

        clearScreen();                   // show only the result of the chosen action
        switch (choice) {
        case 1:  registerParcel();           break;
        case 2:  displayAllParcels();        break;
        case 3:  displayPendingParcels();    break;
        case 4:  searchParcelByID();         break;
        case 5:  searchParcelsByRecipient(); break;
        case 6:  processNextParcel();        break;
        case 7:  processParcelByID();        break;
        case 8:  updateParcelDetails();      break;
        case 9:  changeParcelStatusMenu();   break;
        case 10: reportMissingParcel();      break;
        case 11: viewRoutingQueues();        break;
        case 12: displaySortedParcels();     break;
        case 13: showStatistics();           break;
        }
        saveParcels();                   // save after every action (register, process, update ...)
        syncRequestsWithParcels();       // Task 2: close requests of parcels now Collected / Returned / Cancelled / Missing
        refreshResourceAssignments();    // Task 3: free their counters / delivery staff straight away
        saveServiceRequests();           // routing creates Task 2 requests, so save those too
        pressEnterToContinue();
    } while (choice != 0);
}