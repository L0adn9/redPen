/*
 * ============================================================================
 *  Module  : Task 4 - Parcel Activity and Record Management
 *  Member 4 - (HTET HTET NAING / TP - 098108)
 *
 *  What this module does
 *   - Every other module calls logActivity() when something happens
 *     (register, route, status change, service request, resource assign...).
 *   - ALL activities are kept in ActivityHistory (a doubly linked list) so
 *     staff can view / search the full record.
 *   - Activities that changed a parcel's status are ALSO pushed onto the
 *     UndoStack. Undo pops the top of the stack (LIFO) and puts the parcel
 *     back to its previous status.
 *   - After an undo, Task 1 (status + queues), Task 2 (service requests),
 *     Task 3 (counters / delivery staff) are updated too.
 *   - Everything is saved to task4_activities.txt so it survives a restart.
 *
 *  Complexity
 *   logActivity  O(1)    push / pop / peek  O(1)    search by parcel  O(n)
 * ============================================================================
 */
#include "Task4.hpp"
#include "Task1.hpp"
#include "Task2.hpp"
#include "Task3.hpp"
#include <iomanip>
#include <fstream>
#include <cstdio>

namespace {

// ============================================================================
//  SECTION 1 : DATA STRUCTURES
// ============================================================================

enum ActivityState {
    ACT_ACTIVE = 0,     // normal record
    ACT_UNDONE = 1,     // reversed by an undo
    ACT_SKIPPED = 2     // could not be reversed any more (parcel changed since)
};

struct Activity {
    string        activityID;       // A001, A002, ...
    string        parcelID;
    string        activityType;
    string        previousStatus;
    string        newStatus;
    string        timestamp;
    string        staffID;
    ActivityState state;

    Activity() : state(ACT_ACTIVE) {}
};

// ---- history list node + list -------------------------------------------
struct HistoryNode {
    Activity     data;
    HistoryNode* next;
    HistoryNode* prev;
    HistoryNode(const Activity& a) : data(a), next(nullptr), prev(nullptr) {}
};

// Doubly linked list with head and tail. add() is O(1). The tail is the newest
// record, so we can walk backwards to show "most recent first".
class ActivityHistory {
private:
    HistoryNode* head;
    HistoryNode* tail;
    int          count;
    int          nextID;

public:
    ActivityHistory() : head(nullptr), tail(nullptr), count(0), nextID(1) {}
    ~ActivityHistory() {
        while (head != nullptr) {
            HistoryNode* old = head;
            head = head->next;
            delete old;
        }
    }
    ActivityHistory(const ActivityHistory&) = delete;
    ActivityHistory& operator=(const ActivityHistory&) = delete;

    // The returned pointer stays valid because nodes are never deleted while
    // the program runs, so the undo stack can safely point at them.
    Activity* add(const Activity& a) {
        HistoryNode* node = new HistoryNode(a);
        if (tail == nullptr) head = tail = node;
        else {
            node->prev = tail;
            tail->next = node;
            tail = node;
        }
        count++;
        return &node->data;
    }

    string makeID() {
        char buf[16];
        snprintf(buf, sizeof(buf), "A%03d", nextID++);
        return string(buf);
    }

    // When loading from file, make sure new IDs continue after the biggest one.
    void noteLoadedID(const string& id) {
        int value = atoi(id.c_str() + 1);
        if (value >= nextID) nextID = value + 1;
    }

    HistoryNode* getHead() const { return head; }
    HistoryNode* getTail() const { return tail; }
    int          size() const { return count; }
};

// ---- undo stack ---------------------------------------------------------
struct UndoNode {
    Activity* activity;
    UndoNode* next;
    UndoNode(Activity* a) : activity(a), next(nullptr) {}
};

// LIFO stack made from a singly linked list. The top is the newest activity.
class UndoStack {
private:
    UndoNode* topNode;
    int       count;

public:
    UndoStack() : topNode(nullptr), count(0) {}
    ~UndoStack() {
        while (topNode != nullptr) {
            UndoNode* old = topNode;
            topNode = topNode->next;
            delete old;
        }
    }
    UndoStack(const UndoStack&) = delete;
    UndoStack& operator=(const UndoStack&) = delete;

    void push(Activity* a) {
        UndoNode* node = new UndoNode(a);
        node->next = topNode;
        topNode = node;
        count++;
    }

    Activity* pop() {                       // nullptr if empty
        if (topNode == nullptr) return nullptr;
        UndoNode* old = topNode;
        Activity* a = old->activity;
        topNode = old->next;
        delete old;
        count--;
        return a;
    }

    Activity* peek() const { return topNode == nullptr ? nullptr : topNode->activity; }
    bool      isEmpty() const { return topNode == nullptr; }
    int       size() const { return count; }
    UndoNode* first() const { return topNode; }   // for display only
};

// ============================================================================
//  SECTION 2 : MODULE DATA
// ============================================================================
ActivityHistory history;
UndoStack       undoStack;

const char* ACTIVITY_FILE = "task4_activities.txt";
bool   activitiesLoaded = false;
string activityLoadNotice;
bool   activityNoticeShown = false;

// true while an undo is running. The other modules log their own side effects
// (e.g. "Resource Release") while we re-sync them; we ignore those and write
// one clean "Undo" record instead.
bool   undoRunning = false;

// ============================================================================
//  SECTION 3 : HELPERS
// ============================================================================

// '|' separates fields in the save file, so it must never appear inside one.
string cleanField(string s) {
    for (size_t i = 0; i < s.size(); i++)
        if (s[i] == '|' || s[i] == '\r' || s[i] == '\n') s[i] = ' ';
    s = trim(s);
    return s.empty() ? string("-") : s;
}

// "Collected" -> STATUS_COLLECTED. false if the text is not a parcel status.
bool parseStatus(const string& text, ParcelStatus& out) {
    for (int i = 0; i < STATUS_COUNT; i++) {
        if (statusToString((ParcelStatus)i) == text) {
            out = (ParcelStatus)i;
            return true;
        }
    }
    return false;
}

// These are the activity names Task 1 uses when it really changes a status.
// (Service request / resource records also contain words like "Pending", so
//  the status text alone is NOT enough to decide - the type must match too.)
bool isStatusChangeType(const string& type) {
    return type == "Status Change" || type == "Collection Confirmation" ||
        type == "Cancellation" || type == "Return Processing" ||
        type == "Missing Report";
}

// An activity can be undone only if it changed the parcel from one valid
// status to a different one.
bool canUndo(const Activity& a) {
    ParcelStatus from, to;
    return isStatusChangeType(a.activityType) &&
        parseStatus(a.previousStatus, from) &&
        parseStatus(a.newStatus, to) &&
        from != to;
}

string stateText(ActivityState s) {
    switch (s) {
    case ACT_UNDONE:  return "UNDONE";
    case ACT_SKIPPED: return "SKIPPED";
    default:          return "";
    }
}

bool startsWith(const string& s, const string& prefix) {
    return s.compare(0, prefix.size(), prefix) == 0;
}

// Ask Y/N until the answer is valid.
bool askYesNo(const string& prompt) {
    while (true) {
        string in = toUpperStr(trim(readLine(prompt)));
        if (in == "Y" || in == "YES") return true;
        if (in == "N" || in == "NO")  return false;
        cout << "  [Error] Please enter Y or N.\n";
    }
}

// ============================================================================
//  SECTION 4 : SAVING AND LOADING
//
//  File : task4_activities.txt   (oldest record first, one per line)
//    id|parcelID|type|previousStatus|newStatus|timestamp|staffID|state
//  The undo stack is NOT stored. It is rebuilt on load by pushing every
//  undoable record that is still ACTIVE, oldest first, so the newest ends up
//  on top again.
// ============================================================================
void loadActivities() {
    ifstream in(ACTIVITY_FILE);
    if (!in) return;                                   // first run: nothing saved yet
    string line;
    if (!getline(in, line) || trim(line) != "TASK4_ACTIVITIES_V1") {
        activityLoadNotice = string("  [Warning] ") + ACTIVITY_FILE +
            " is not a valid save file and was ignored.\n";
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

        bool ok = (n == 8) && f[0].size() >= 2 && f[0][0] == 'A';
        for (size_t i = 1; ok && i < f[0].size(); i++)
            if (!isdigit((unsigned char)f[0][i])) ok = false;
        for (int i = 1; ok && i < 7; i++)
            if (f[i].empty()) ok = false;
        ok = ok && f[5].size() == 19 && f[7].size() == 1 && f[7][0] >= '0' && f[7][0] <= '2';
        if (!ok) { skipped++; continue; }

        Activity a;
        a.activityID = f[0];
        a.parcelID = f[1];
        a.activityType = f[2];
        a.previousStatus = f[3];
        a.newStatus = f[4];
        a.timestamp = f[5];
        a.staffID = f[6];
        a.state = (ActivityState)(f[7][0] - '0');

        history.noteLoadedID(a.activityID);
        Activity* stored = history.add(a);
        if (stored->state == ACT_ACTIVE && canUndo(*stored))
            undoStack.push(stored);
        loaded++;
    }
    if (loaded > 0 || skipped > 0) {
        activityLoadNotice = "  [Info] Loaded " + to_string(loaded) + " activity record(s) from " +
            ACTIVITY_FILE + (skipped ? " (" + to_string(skipped) + " damaged line(s) skipped)" : "") + ".\n";
    }
}

void ensureLoaded() {
    if (!activitiesLoaded) {
        activitiesLoaded = true;           // set first so loading cannot re-enter itself
        loadActivities();
    }
}

// ============================================================================
//  SECTION 5 : DISPLAY
// ============================================================================

// Two lines per record so it fits the 60-80 column console.
void printActivity(const Activity& a) {
    cout << "  " << left << setw(6) << a.activityID << setw(8) << a.parcelID
         << a.timestamp << "  " << a.staffID;
    if (a.state != ACT_ACTIVE) cout << "  [" << stateText(a.state) << "]";
    cout << "\n        " << a.activityType << " : ";
    if (a.previousStatus == a.newStatus) cout << "status stays " << a.newStatus;
    else                                 cout << a.previousStatus << " -> " << a.newStatus;
    cout << "\n";
}

// Show records from newest to oldest, pausing every 8 so long lists can be read.
// parcelFilter = "" means show everything. Returns how many were shown.
int printHistoryBackwards(int maxCount, const string& parcelFilter) {
    int shown = 0;
    for (HistoryNode* cur = history.getTail(); cur != nullptr && shown < maxCount; cur = cur->prev) {
        if (!parcelFilter.empty() && cur->data.parcelID != parcelFilter) continue;
        if (shown > 0 && shown % 8 == 0)
            readLine("  -- press Enter for more --");
        printActivity(cur->data);
        shown++;
    }
    return shown;
}

// ============================================================================
//  SECTION 6 : UNDO
// ============================================================================

// After the parcel status is restored, bring Task 2 and Task 3 back in line.
void resyncOtherModules(Parcel* p, ParcelStatus restored) {
    syncRequestsWithParcels();         // Task 2: close requests of parcels that are still finished
    refreshResourceAssignments();      // Task 3: free resources that no longer match

    string activeRequest = getActiveRequestID(p->parcelID);

    // Does this parcel (status + route) need an open service request?
    bool needsRequest =
        (restored == STATUS_READY_FOR_COLLECTION && p->route == ROUTE_COLLECTION) ||
        (restored == STATUS_PROCESSING && (p->route == ROUTE_DELIVERY ||
            p->route == ROUTE_SPECIAL_HANDLING || p->route == ROUTE_RETURN));

    if (activeRequest.empty() && needsRequest) {
        // The old request was closed when the parcel finished, so open a new one.
        createServiceRequest(p, p->route);
    }
    else if (!activeRequest.empty() && !needsRequest) {
        cout << "  [Note] Service request " << activeRequest << " is still open for this parcel.\n"
             << "         Cancel it in Service Requests if it is no longer needed.\n";
    }
    else if (activeRequest.empty() && restored == STATUS_OUT_FOR_DELIVERY) {
        cout << "  [Note] The delivery request was already closed. Create a Re-delivery request\n"
             << "         in Service Requests if the parcel still needs to be delivered.\n";
    }
    saveServiceRequests();
}

// Pop stale records off the top until we find one that can really be undone.
// A record is stale when the parcel no longer has the status it was changed to
// (e.g. the save files were edited by hand), so reversing it would be wrong.
Activity* nextUndoable(Parcel*& parcelOut) {
    while (!undoStack.isEmpty()) {
        Activity* a = undoStack.peek();
        ParcelStatus oldStatus, newStatus;
        parseStatus(a->previousStatus, oldStatus);
        parseStatus(a->newStatus, newStatus);

        Parcel* p = findParcel(a->parcelID);
        string problem;
        if (p == nullptr)
            problem = "parcel " + a->parcelID + " no longer exists";
        else if (p->status != newStatus)
            problem = "parcel " + a->parcelID + " is now '" + statusToString(p->status) +
                "' (expected '" + a->newStatus + "')";

        if (problem.empty()) { parcelOut = p; return a; }

        cout << "  [Skipped] " << a->activityID << " cannot be undone: " << problem << ".\n";
        a->state = ACT_SKIPPED;
        undoStack.pop();
        saveActivities();
    }
    return nullptr;
}

void undoLastActivity() {
    printTitle("UNDO LAST ACTIVITY");
    if (undoStack.isEmpty()) {
        cout << "  [Info] Nothing to undo. No reversible activity is stored.\n";
        return;
    }

    Parcel* parcel = nullptr;
    Activity* a = nextUndoable(parcel);
    if (a == nullptr) {
        cout << "  [Info] Nothing left that can be undone.\n";
        return;
    }

    ParcelStatus oldStatus, newStatus;
    parseStatus(a->previousStatus, oldStatus);
    parseStatus(a->newStatus, newStatus);

    cout << "\n  Most recent reversible activity:\n";
    printLine('-');
    cout << "  Activity ID : " << a->activityID << "  (" << a->activityType << ")\n"
         << "  Parcel      : " << parcel->parcelID << "  (" << parcel->recipientName << ")\n"
         << "  Done on     : " << a->timestamp << " by " << a->staffID << "\n"
         << "  Undo will   : change status '" << a->newStatus << "' back to '"
         << a->previousStatus << "'\n";
    printLine('-');

    if (!askYesNo("  Undo this activity? (Y/N): ")) {
        cout << "  Undo cancelled. Nothing was changed.\n";
        return;
    }

    undoRunning = true;                              // ignore logs from the modules we re-sync
    bool ok = forceParcelStatus(parcel->parcelID, oldStatus);   // Task 1
    if (ok) resyncOtherModules(parcel, oldStatus);              // Task 2 + Task 3
    undoRunning = false;

    if (!ok) {
        cout << "  [Error] Could not change the parcel status. Nothing was undone.\n";
        return;
    }

    undoStack.pop();                                 // the stack top is the activity we just reversed
    a->state = ACT_UNDONE;

    Activity record;                                 // keep a record that the undo happened
    record.activityID = history.makeID();
    record.parcelID = a->parcelID;
    record.activityType = "Undo: " + a->activityType;
    record.previousStatus = a->newStatus;
    record.newStatus = a->previousStatus;
    record.timestamp = getCurrentDateTime();
    record.staffID = cleanField(g_staffID);
    history.add(record);
    saveActivities();

    cout << "\n  [Success] Parcel " << parcel->parcelID << " is back to '"
         << statusToString(oldStatus) << "'.\n";
    if (newStatus == STATUS_COLLECTED || newStatus == STATUS_RETURNED || newStatus == STATUS_CANCELLED)
        cout << "  [Note] Any counter / delivery person that handled it was already released in\n"
             << "         Task 3. Assign a resource again there if the parcel needs one.\n";
    cout << "  Undo stack now holds " << undoStack.size() << " reversible activit"
         << (undoStack.size() == 1 ? "y" : "ies") << ".\n";
}

// ============================================================================
//  SECTION 7 : VIEW / SEARCH / SUMMARY
// ============================================================================
void viewUndoStack() {
    printTitle("UNDO STACK (TOP = NEXT UNDO)");
    if (undoStack.isEmpty()) {
        cout << "  [Info] The undo stack is empty.\n";
        return;
    }
    cout << "  " << undoStack.size() << " reversible activit"
         << (undoStack.size() == 1 ? "y" : "ies") << ", newest first.\n";
    printLine('-');
    int position = 1;
    for (UndoNode* cur = undoStack.first(); cur != nullptr; cur = cur->next) {
        if (position > 1 && (position - 1) % 8 == 0)
            readLine("  -- press Enter for more --");
        cout << "  #" << position << (position == 1 ? "  <- next to undo" : "") << "\n";
        printActivity(*cur->activity);
        position++;
    }
}

void viewRecentActivities() {
    printTitle("RECENT ACTIVITY (LAST 10)");
    if (history.size() == 0) { cout << "  [Info] No activity recorded yet.\n"; return; }
    printLine('-');
    printHistoryBackwards(10, "");
}

void viewFullHistory() {
    printTitle("FULL ACTIVITY HISTORY");
    if (history.size() == 0) { cout << "  [Info] No activity recorded yet.\n"; return; }
    cout << "  " << history.size() << " record(s), newest first.\n";
    printLine('-');
    printHistoryBackwards(history.size(), "");
}

void searchByParcel() {
    printTitle("SEARCH HISTORY BY PARCEL");
    string id = toUpperStr(trim(readLine("  Enter Parcel ID (0 to cancel): ")));
    if (id == "0") return;
    if (!isAlphanumeric(id)) {
        cout << "  [Error] Parcel ID must contain letters and digits only.\n";
        return;
    }
    Parcel* p = findParcel(id);
    if (p != nullptr)
        cout << "\n  Parcel " << p->parcelID << " | " << p->recipientName
             << " | current status: " << statusToString(p->status) << "\n";
    printLine('-');
    int found = printHistoryBackwards(history.size(), id);
    if (found == 0) cout << "  [Not Found] No activity recorded for parcel " << id << ".\n";
    else            cout << "\n  " << found << " record(s) found (newest first).\n";
}

void showSummary() {
    printTitle("ACTIVITY SUMMARY");
    int total = 0, registration = 0, routing = 0, updates = 0, statusChanges = 0,
        requests = 0, resources = 0, undos = 0, other = 0, undone = 0, skipped = 0;

    for (HistoryNode* cur = history.getHead(); cur != nullptr; cur = cur->next) {
        const Activity& a = cur->data;
        total++;
        if (a.state == ACT_UNDONE)  undone++;
        if (a.state == ACT_SKIPPED) skipped++;

        if (a.activityType == "Parcel Registration")      registration++;
        else if (startsWith(a.activityType, "Parcel Routing")) routing++;
        else if (a.activityType == "Parcel Update")       updates++;
        else if (isStatusChangeType(a.activityType))      statusChanges++;
        else if (startsWith(a.activityType, "Service Request")) requests++;
        else if (startsWith(a.activityType, "Resource"))  resources++;
        else if (startsWith(a.activityType, "Undo"))      undos++;
        else                                              other++;
    }

    cout << "  Total activity records   : " << total << "\n";
    printLine('-');
    cout << "  Parcel registrations     : " << registration << "\n"
         << "  Parcel routing           : " << routing << "\n"
         << "  Parcel detail updates    : " << updates << "\n"
         << "  Parcel status changes    : " << statusChanges << "\n"
         << "  Service request activity : " << requests << "\n"
         << "  Resource assign/release  : " << resources << "\n"
         << "  Undo actions             : " << undos << "\n";
    if (other > 0) cout << "  Other                    : " << other << "\n";
    printLine('-');
    cout << "  Still on the undo stack  : " << undoStack.size() << "\n"
         << "  Already undone           : " << undone << "\n"
         << "  Skipped (could not undo) : " << skipped << "\n";
}

} // end anonymous namespace

// ============================================================================
//  SECTION 8 : PUBLIC FUNCTIONS (called by the other modules)
// ============================================================================
void logActivity(const string& parcelID, const string& activityType,
    const string& previousStatus, const string& newStatus,
    const string& staffID) {
    ensureLoaded();                        // never write the file before it was read
    if (undoRunning) return;               // side effects of an undo are covered by the Undo record

    Activity a;
    a.activityID = history.makeID();
    a.parcelID = cleanField(toUpperStr(parcelID));
    a.activityType = cleanField(activityType);
    a.previousStatus = cleanField(previousStatus);
    a.newStatus = cleanField(newStatus);
    a.timestamp = getCurrentDateTime();
    a.staffID = cleanField(staffID);

    Activity* stored = history.add(a);     // 1) full history, O(1)
    if (canUndo(*stored))
        undoStack.push(stored);            // 2) reversible? then it goes on the stack, O(1)
    saveActivities();
}

void saveActivities() {
    ensureLoaded();                        // never overwrite the file before it was read
    ofstream out(ACTIVITY_FILE);
    if (!out) return;                      // read-only folder: skip silently
    out << "TASK4_ACTIVITIES_V1\n";
    for (HistoryNode* n = history.getHead(); n != nullptr; n = n->next) {
        const Activity& a = n->data;
        out << a.activityID << '|' << a.parcelID << '|' << a.activityType << '|'
            << a.previousStatus << '|' << a.newStatus << '|' << a.timestamp << '|'
            << a.staffID << '|' << (int)a.state << '\n';
    }
}

void runTask4Menu() {
    ensureLoaded();
    if (!activityLoadNotice.empty() && !activityNoticeShown) {   // tell staff once what was restored
        activityNoticeShown = true;
        cout << activityLoadNotice;
        pressEnterToContinue();
    }

    int choice;
    do {
        clearScreen();
        printTitle("ACTIVITY HISTORY & UNDO");
        cout << "  Records: " << history.size() << "   Can undo: " << undoStack.size()
             << "   (staff " << g_staffID << ")\n";
        printLine('-');
        cout << "  [1] Undo last activity\n"
             << "  [2] View undo stack\n"
             << "  [3] Recent activity (last 10)\n"
             << "  [4] Full activity history\n"
             << "  [5] Search history by Parcel ID\n"
             << "  [6] Activity summary\n"
             << "  [0] Back to main menu\n";
        printLine('-');
        choice = readInt("  Enter your choice: ", 0, 6);
        if (choice == 0) break;

        clearScreen();
        switch (choice) {
        case 1: undoLastActivity();    break;
        case 2: viewUndoStack();       break;
        case 3: viewRecentActivities(); break;
        case 4: viewFullHistory();     break;
        case 5: searchByParcel();      break;
        case 6: showSummary();         break;
        }
        pressEnterToContinue();
    } while (choice != 0);
}
