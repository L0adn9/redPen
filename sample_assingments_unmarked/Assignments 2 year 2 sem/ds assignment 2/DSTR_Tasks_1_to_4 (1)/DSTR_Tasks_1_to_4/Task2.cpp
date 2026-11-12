#include "Task2.hpp"
#include "Task1.hpp"
#include "Task3.hpp"
#include "Task4.hpp"
#include <iomanip>
#include <fstream>

using namespace std;

enum ServiceType {
    SERVICE_COLLECTION = 1,
    SERVICE_DELIVERY,
    SERVICE_SPECIAL,
    SERVICE_RETURN,
    SERVICE_REDELIVERY
};

enum ServiceStatus {
    SERVICE_PENDING,
    SERVICE_PROCESSING,
    SERVICE_COMPLETED,
    SERVICE_CANCELLED,
    SERVICE_RETURNED
};

struct ServiceRequest {
    string requestID;
    string parcelID;
    string recipientID;
    string recipientName;
    ServiceType type;
    ServiceStatus status;
    string requestDateTime;
    string finishedDateTime;
    int priority;
    unsigned long sequence;
    ServiceRequest* next;

    ServiceRequest() : type(SERVICE_COLLECTION), status(SERVICE_PENDING),
        priority(0), sequence(0), next(nullptr) {}
};

struct ServiceQueueNode {
    ServiceRequest* request;
    ServiceQueueNode* next;
    ServiceQueueNode(ServiceRequest* r) : request(r), next(nullptr) {}
};

class ServicePriorityQueue {
private:
    ServiceQueueNode* head;
    int count;
public:
    ServicePriorityQueue() : head(nullptr), count(0) {}
    ~ServicePriorityQueue() {
        while (head != nullptr) {
            ServiceQueueNode* old = head;
            head = head->next;
            delete old;
        }
    }
    ServicePriorityQueue(const ServicePriorityQueue&) = delete;
    ServicePriorityQueue& operator=(const ServicePriorityQueue&) = delete;

    bool isEmpty() const { return head == nullptr; }
    int size() const { return count; }
    ServiceQueueNode* first() const { return head; }
    ServiceRequest* peek() const { return head == nullptr ? nullptr : head->request; }

    void enqueue(ServiceRequest* request) {
        ServiceQueueNode* node = new ServiceQueueNode(request);
        if (head == nullptr || request->priority > head->request->priority) {
            node->next = head;
            head = node;
        }
        else {
            ServiceQueueNode* current = head;
            while (current->next != nullptr && current->next->request->priority >= request->priority)
                current = current->next;
            node->next = current->next;
            current->next = node;
        }
        count++;
    }

    ServiceRequest* dequeue() {
        if (head == nullptr) return nullptr;
        ServiceQueueNode* old = head;
        ServiceRequest* value = old->request;
        head = old->next;
        delete old;
        count--;
        return value;
    }

    bool remove(const string& requestID) {
        ServiceQueueNode* previous = nullptr;
        ServiceQueueNode* current = head;
        while (current != nullptr) {
            if (current->request->requestID == requestID) {
                if (previous == nullptr) head = current->next;
                else previous->next = current->next;
                delete current;
                count--;
                return true;
            }
            previous = current;
            current = current->next;
        }
        return false;
    }
};

class ServiceRequestStore {
private:
    ServiceRequest* head;
    ServiceRequest* tail;
    int count;
    int nextID;
    unsigned long nextSequence;
public:
    ServiceRequestStore() : head(nullptr), tail(nullptr), count(0), nextID(0), nextSequence(0) {}
    ~ServiceRequestStore() {
        while (head != nullptr) {
            ServiceRequest* old = head;
            head = head->next;
            delete old;
        }
    }
    ServiceRequestStore(const ServiceRequestStore&) = delete;
    ServiceRequestStore& operator=(const ServiceRequestStore&) = delete;

    ServiceRequest* first() const { return head; }
    int size() const { return count; }
    ServiceRequest* find(const string& id) const {
        ServiceRequest* current = head;
        while (current != nullptr) {
            if (current->requestID == id) return current;
            current = current->next;
        }
        return nullptr;
    }
    ServiceRequest* activeForParcel(const string& id) const {
        ServiceRequest* current = head;
        while (current != nullptr) {
            if (current->parcelID == id &&
                (current->status == SERVICE_PENDING || current->status == SERVICE_PROCESSING))
                return current;
            current = current->next;
        }
        return nullptr;
    }
    ServiceRequest* append(const Parcel& parcel, ServiceType type, int priority) {
        ServiceRequest* request = new ServiceRequest();
        nextID++;
        string serial = to_string(nextID);
        while (serial.size() < 3) serial = "0" + serial;
        request->requestID = "SR" + serial;
        request->parcelID = parcel.parcelID;
        request->recipientID = parcel.recipientID;
        request->recipientName = parcel.recipientName;
        request->type = type;
        request->priority = priority;
        request->requestDateTime = getCurrentDateTime();
        request->sequence = ++nextSequence;
        if (tail == nullptr) head = tail = request;
        else {
            tail->next = request;
            tail = request;
        }
        count++;
        return request;
    }

    // Re-create a request read from the save file (keeps its ID and sequence).
    ServiceRequest* appendRestored(const ServiceRequest& source) {
        ServiceRequest* request = new ServiceRequest(source);
        request->next = nullptr;
        int number = atoi(source.requestID.c_str() + 2);       // "SR" + digits
        if (number > nextID) nextID = number;                  // never re-issue an old ID
        if (source.sequence > nextSequence) nextSequence = source.sequence;
        if (tail == nullptr) head = tail = request;
        else {
            tail->next = request;
            tail = request;
        }
        count++;
        return request;
    }
};

static ServicePriorityQueue waitingRequests;
static ServiceRequestStore requestStore;
static ServiceRequest* currentRequest = nullptr;

static string serviceTypeText(ServiceType type) {
    switch (type) {
    case SERVICE_COLLECTION: return "Recipient Collection";
    case SERVICE_DELIVERY: return "Campus Delivery";
    case SERVICE_SPECIAL: return "Special Handling";
    case SERVICE_RETURN: return "Return to Sender";
    case SERVICE_REDELIVERY: return "Re-delivery";
    default: return "Unknown";
    }
}

static string serviceStatusText(ServiceStatus status) {
    switch (status) {
    case SERVICE_PENDING: return "Pending";
    case SERVICE_PROCESSING: return "Processing";
    case SERVICE_COMPLETED: return "Completed";
    case SERVICE_CANCELLED: return "Cancelled";
    case SERVICE_RETURNED: return "Returned";
    default: return "Unknown";
    }
}

static int priorityForService(ServiceType type) {
    switch (type) {
    case SERVICE_SPECIAL: return 5;
    case SERVICE_RETURN: return 4;
    case SERVICE_REDELIVERY: return 3;
    case SERVICE_DELIVERY: return 2;
    case SERVICE_COLLECTION: return 1;
    default: return 0;
    }
}

static bool isFinalParcel(ParcelStatus status) {
    return status == STATUS_COLLECTED || status == STATUS_RETURNED ||
        status == STATUS_CANCELLED || status == STATUS_MISSING;
}

static bool matchesRoute(const Parcel& parcel, ServiceType type) {
    if (isFinalParcel(parcel.status) || parcel.status == STATUS_ON_HOLD ||
        parcel.status == STATUS_PENDING || parcel.status == STATUS_RECEIVED)
        return false;
    switch (type) {
    case SERVICE_COLLECTION:
        return parcel.route == ROUTE_COLLECTION && parcel.status == STATUS_READY_FOR_COLLECTION;
    case SERVICE_DELIVERY:
        return parcel.route == ROUTE_DELIVERY && parcel.status == STATUS_PROCESSING;
    case SERVICE_SPECIAL:
        return parcel.route == ROUTE_SPECIAL_HANDLING && parcel.status == STATUS_PROCESSING;
    case SERVICE_RETURN:
        return parcel.route == ROUTE_RETURN && parcel.status == STATUS_PROCESSING;
    case SERVICE_REDELIVERY:
        return parcel.route == ROUTE_DELIVERY &&
            (parcel.status == STATUS_PROCESSING || parcel.status == STATUS_OUT_FOR_DELIVERY);
    default:
        return false;
    }
}

// ============================================================================
//  SAVING AND LOADING  (text file, so requests survive a restart)
//
//  File : task2_requests.txt - one request per line, fields separated by '|'
//  The priority queue is NOT stored: waiting requests are put back into it on
//  load (priority comes from the service type, equal priority = oldest first).
//  A request that was 'Processing' stays the current request.
//  Requests whose parcel no longer exists are skipped.
// ============================================================================
static const char* REQUEST_FILE = "task2_requests.txt";
static bool   requestsLoaded = false;
static string requestLoadNotice;
static bool   requestNoticeShown = false;

static void ensureRequestsLoaded();

static bool isDigitsOnly(const string& s) {
    if (s.empty() || s.size() > 9) return false;
    for (size_t i = 0; i < s.size(); i++)
        if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

void saveServiceRequests() {
    ensureRequestsLoaded();                // never overwrite the file before it was read
    ofstream out(REQUEST_FILE);
    if (!out) return;                      // read-only folder: skip silently
    out << "TASK2_REQUESTS_V1\n";
    for (ServiceRequest* r = requestStore.first(); r != nullptr; r = r->next) {
        out << r->requestID << '|' << r->parcelID << '|' << r->recipientID << '|'
            << r->recipientName << '|' << (int)r->type << '|' << (int)r->status << '|'
            << r->requestDateTime << '|' << r->finishedDateTime << '|' << r->sequence << '\n';
    }
}

static void loadServiceRequests() {
    ifstream in(REQUEST_FILE);
    if (!in) return;                       // first run: nothing saved yet
    string line;
    if (!getline(in, line) || trim(line) != "TASK2_REQUESTS_V1") {
        requestLoadNotice = string("  [Warning] ") + REQUEST_FILE + " is not a valid save file and was ignored.\n";
        return;
    }
    int loaded = 0, skipped = 0;
    while (getline(in, line)) {
        line = trim(line);
        if (line.empty()) continue;
        string f[9];
        int n = 0;
        size_t start = 0;
        for (size_t i = 0; i <= line.size(); i++) {
            if (i == line.size() || line[i] == '|') {
                if (n < 9) f[n] = line.substr(start, i - start);
                n++;
                start = i + 1;
            }
        }
        bool ok = (n == 9) && f[0].size() >= 3 && f[0].size() <= 8 && f[0][0] == 'S' && f[0][1] == 'R' &&
            isDigitsOnly(f[0].substr(2)) && !f[1].empty() && !trim(f[2]).empty() && !trim(f[3]).empty() &&
            isDigitsOnly(f[4]) && isDigitsOnly(f[5]) && f[6].size() == 19 &&
            (f[7].empty() || f[7].size() == 19) && isDigitsOnly(f[8]) &&
            requestStore.find(f[0]) == nullptr && findParcel(f[1]) != nullptr;     // parcel must still exist
        int type = 0, status = 0;
        if (ok) {
            type = atoi(f[4].c_str());
            status = atoi(f[5].c_str());
            ok = type >= SERVICE_COLLECTION && type <= SERVICE_REDELIVERY &&
                status >= SERVICE_PENDING && status <= SERVICE_RETURNED;
        }
        if (!ok) { skipped++; continue; }

        ServiceRequest r;
        r.requestID = f[0];
        r.parcelID = f[1];
        r.recipientID = f[2];
        r.recipientName = f[3];
        r.type = (ServiceType)type;
        r.status = (ServiceStatus)status;
        r.requestDateTime = f[6];
        r.finishedDateTime = f[7];
        r.priority = priorityForService(r.type);
        r.sequence = (unsigned long)atol(f[8].c_str());

        if (r.status == SERVICE_PROCESSING && currentRequest != nullptr)
            r.status = SERVICE_PENDING;    // only ONE request can be processing at a time

        ServiceRequest* stored = requestStore.appendRestored(r);
        if (stored->status == SERVICE_PENDING) waitingRequests.enqueue(stored);
        else if (stored->status == SERVICE_PROCESSING) currentRequest = stored;
        loaded++;
    }
    if (loaded > 0 || skipped > 0) {
        requestLoadNotice = "  [Info] Loaded " + to_string(loaded) + " service request(s) from " + REQUEST_FILE +
            (skipped ? " (" + to_string(skipped) + " skipped: damaged or parcel missing)" : "") + ".\n";
    }
}

static void ensureRequestsLoaded() {
    if (!requestsLoaded) {
        requestsLoaded = true;             // set first: loading must not re-enter itself
        loadServiceRequests();
    }
}

// Public lookup for Task 3 (shows which request a resource is handling).
string getActiveRequestID(const string& parcelID) {
    ensureRequestsLoaded();
    ServiceRequest* request = requestStore.activeForParcel(parcelID);
    return request == nullptr ? string("") : request->requestID;
}

// Task 3 link: free the counter / delivery person that was handling a parcel.
// counted = true when the job really finished (completed or returned).
static void releaseResourceFor(const string& parcelID, bool counted) {
    string resourceID = getAssignedResourceID(parcelID);
    if (resourceID.empty()) return;                     // no resource was assigned
    releaseResourceOfParcel(parcelID, counted);
    cout << "  [Resource] " << resourceID << " released"
         << (counted ? " (job counted)." : ".") << "\n";
}

static void showRequest(const ServiceRequest& request) {
    printLine('-');
    cout << "  Request ID       : " << request.requestID << "\n"
         << "  Parcel ID        : " << request.parcelID << "\n"
         << "  Recipient ID     : " << request.recipientID << "\n"
         << "  Recipient Name   : " << request.recipientName << "\n"
         << "  Service Type     : " << serviceTypeText(request.type) << "\n"
         << "  Requested On     : " << request.requestDateTime << "\n"
         << "  Request Status   : " << serviceStatusText(request.status) << "\n"
         << "  Priority         : " << request.priority << "\n";
    if (!request.finishedDateTime.empty())
        cout << "  Closed On        : " << request.finishedDateTime << "\n";
    Parcel* parcel = findParcel(request.parcelID);
    if (parcel != nullptr) cout << "  Parcel Status    : " << statusToString(parcel->status) << "\n";
    printLine('-');
}

static void showTableHeader() {
    cout << left << setw(9) << "Request" << setw(9) << "Parcel"
         << setw(14) << "Recipient" << setw(23) << "Service"
         << setw(13) << "Status" << setw(10) << "Priority" << "Requested On\n";
    printLine('-');
}

static void showTableRow(const ServiceRequest& request) {
    cout << left << setw(9) << request.requestID
         << setw(9) << request.parcelID
         << setw(14) << request.recipientID.substr(0, 13)
         << setw(23) << serviceTypeText(request.type)
         << setw(13) << serviceStatusText(request.status)
         << setw(10) << request.priority
         << request.requestDateTime << "\n";
}

static ServiceRequest* addRequest(Parcel* parcel, ServiceType type) {
    if (parcel == nullptr || findParcel(parcel->parcelID) != parcel) {
        cout << "  [Error] Registered parcel not found.\n";
        return nullptr;
    }
    if (trim(parcel->recipientID).empty() || trim(parcel->recipientName).empty()) {
        cout << "  [Error] Recipient information is incomplete.\n";
        return nullptr;
    }
    if (!matchesRoute(*parcel, type)) {
        cout << "  [Error] Service does not match the parcel route or current status.\n";
        return nullptr;
    }
    ServiceRequest* existing = requestStore.activeForParcel(parcel->parcelID);
    if (existing != nullptr) {
        cout << "  [Error] Active request " << existing->requestID
             << " already exists for this parcel.\n";
        return nullptr;
    }
    ServiceRequest* request = requestStore.append(*parcel, type, priorityForService(type));
    waitingRequests.enqueue(request);
    logActivity(parcel->parcelID, "Service Request Creation", "-", "Pending", g_staffID);
    cout << "  [Success] Service request " << request->requestID
         << " created. Priority: " << request->priority << "\n";
    saveServiceRequests();                                  // keep the file up to date
    return request;
}

void createServiceRequest(Parcel* parcel, RouteAction route) {
    ensureRequestsLoaded();
    ServiceType type;
    switch (route) {
    case ROUTE_COLLECTION: type = SERVICE_COLLECTION; break;
    case ROUTE_DELIVERY: type = SERVICE_DELIVERY; break;
    case ROUTE_SPECIAL_HANDLING: type = SERVICE_SPECIAL; break;
    case ROUTE_RETURN: type = SERVICE_RETURN; break;
    default: return;
    }
    addRequest(parcel, type);
}

static void manuallyCreateRequest() {
    printTitle("CREATE SERVICE REQUEST");
    string parcelID = toUpperStr(trim(readLine("  Parcel ID (0 to cancel): ")));
    if (parcelID == "0") return;
    Parcel* parcel = findParcel(parcelID);
    if (parcel == nullptr) {
        cout << "  [Error] Parcel ID not found. Register the parcel in Task 1 first.\n";
        return;
    }
    cout << "  Parcel: " << parcel->parcelID << " | " << parcel->recipientName
         << " | " << statusToString(parcel->status) << "\n";
    cout << "  1. Recipient Collection\n  2. Campus Delivery\n"
         << "  3. Special Handling\n  4. Return to Sender\n  5. Re-delivery\n";
    int selection = readInt("  Service type (0 to cancel): ", 0, 5);
    if (selection == 0) return;
    addRequest(parcel, static_cast<ServiceType>(selection));
}

static void viewPendingRequests() {
    printTitle("ACTIVE SERVICE REQUESTS - PRIORITY ORDER");
    cout << "  Waiting: " << waitingRequests.size()
         << " | Processing: " << (currentRequest == nullptr ? 0 : 1) << "\n";
    if (currentRequest != nullptr) {
        cout << "\n  Currently processing:\n";
        showRequest(*currentRequest);
    }
    if (waitingRequests.isEmpty()) {
        cout << "\n  No pending service requests.\n";
        return;
    }
    cout << "\n  Waiting priority queue:\n";
    showTableHeader();
    ServiceQueueNode* node = waitingRequests.first();
    while (node != nullptr) {
        showTableRow(*node->request);
        node = node->next;
    }
}

static void viewAllRequests() {
    printTitle("ALL SERVICE REQUESTS");
    if (requestStore.size() == 0) {
        cout << "  No service requests recorded.\n";
        return;
    }
    showTableHeader();
    ServiceRequest* request = requestStore.first();
    while (request != nullptr) {
        showTableRow(*request);
        request = request->next;
    }
}

static void searchRequest() {
    printTitle("FIND SERVICE REQUEST");
    string id = toUpperStr(trim(readLine("  Request ID: ")));
    ServiceRequest* request = requestStore.find(id);
    if (request == nullptr) {
        cout << "  [Not Found] Request " << id << " does not exist.\n";
        return;
    }
    showRequest(*request);
}

static void processNextRequest() {
    printTitle("PROCESS HIGHEST-PRIORITY REQUEST");
    if (currentRequest != nullptr) {
        cout << "  [Error] Finish the request currently processing first: "
             << currentRequest->requestID << "\n";
        return;
    }
    if (waitingRequests.isEmpty()) {
        cout << "  [Error] No pending service requests.\n";
        return;
    }
    ServiceRequest* next = waitingRequests.peek();
    Parcel* parcel = findParcel(next->parcelID);
    if (parcel == nullptr || !matchesRoute(*parcel, next->type)) {
        cout << "  [Error] Parcel status/route changed; request " << next->requestID
             << " is no longer eligible. Use option [5] to cancel it, then try again.\n";
        return;
    }
    // Reserve a suitable resource BEFORE changing the request to Processing.
    // If resources are busy, Task 3 queues the parcel; the service remains Pending.
    string assigned = getAssignedResourceID(next->parcelID);
    if (assigned.empty()) {
        cout << "  [Resource] Checking for an available suitable resource...\n";
        if (!requestResourceForParcel(parcel, next->requestID)) {
            cout << "  [Waiting] Request " << next->requestID
                 << " remains Pending until a suitable resource is assigned.\n";
            return;
        }
        assigned = getAssignedResourceID(next->parcelID);
    }
    if (assigned.empty()) {
        cout << "  [Error] Resource allocation could not be confirmed. Request remains Pending.\n";
        return;
    }
    next = waitingRequests.dequeue();
    next->status = SERVICE_PROCESSING;
    currentRequest = next;
    logActivity(next->parcelID, "Service Request Processing", "Pending", "Processing", g_staffID);
    cout << "  [Selected] Highest priority request:\n";
    showRequest(*next);
    cout << "  [Resource] Assigned to " << assigned << ".\n";
}

static ParcelStatus completedParcelStatus(const ServiceRequest& request) {
    switch (request.type) {
    case SERVICE_COLLECTION: return STATUS_COLLECTED;
    case SERVICE_SPECIAL: return STATUS_READY_FOR_COLLECTION;
    case SERVICE_RETURN: return STATUS_RETURNED;
    case SERVICE_DELIVERY:
    case SERVICE_REDELIVERY: return STATUS_COLLECTED;
    default: return STATUS_PROCESSING;
    }
}

static void finishCurrentRequest() {
    printTitle("FINISH SERVICE REQUEST");
    if (currentRequest == nullptr) {
        cout << "  [Error] No request is currently processing.\n";
        return;
    }
    ServiceRequest* request = currentRequest;
    showRequest(*request);
    cout << "  [1] Complete request\n  [2] Cancel request\n  [3] Mark returned\n";
    int selection = readInt("  Action (0 to back): ", 0, 3);
    if (selection == 0) return;
    Parcel* parcel = findParcel(request->parcelID);
    if (parcel == nullptr) {
        cout << "  [Error] Associated parcel no longer exists.\n";
        return;
    }
    ParcelStatus destination = STATUS_PROCESSING;
    ServiceStatus result = SERVICE_COMPLETED;
    if (selection == 1) destination = completedParcelStatus(*request);
    else if (selection == 2) {
        destination = STATUS_CANCELLED;
        result = SERVICE_CANCELLED;
    }
    else {
        destination = STATUS_RETURNED;
        result = SERVICE_RETURNED;
    }
    if (selection == 1 &&
        (request->type == SERVICE_DELIVERY || request->type == SERVICE_REDELIVERY) &&
        parcel->status == STATUS_PROCESSING) {
        if (!updateParcelStatus(parcel->parcelID, STATUS_OUT_FOR_DELIVERY)) {
            cout << "  [Error] Cannot advance parcel to Out for Delivery.\n";
            return;
        }
    }
    if (!isValidTransition(parcel->status, destination)) {
        cout << "  [Error] Parcel cannot transition from " << statusToString(parcel->status)
             << " to " << statusToString(destination) << ".\n";
        return;
    }
    if (!updateParcelStatus(parcel->parcelID, destination)) return;
    string old = serviceStatusText(request->status);
    request->status = result;
    request->finishedDateTime = getCurrentDateTime();
    currentRequest = nullptr;
    logActivity(request->parcelID, "Service Request " + serviceStatusText(result),
        old, serviceStatusText(result), g_staffID);
    cout << "  [Success] Request " << request->requestID << " is now "
         << serviceStatusText(result) << ".\n";
    releaseResourceFor(request->parcelID, selection != 2);       // Task 3: free the resource
}

static void cancelPendingRequest() {
    printTitle("CANCEL PENDING SERVICE REQUEST");
    string id = toUpperStr(trim(readLine("  Request ID (0 to cancel): ")));
    if (id == "0") return;
    ServiceRequest* request = requestStore.find(id);
    if (request == nullptr) {
        cout << "  [Not Found] Request does not exist.\n";
        return;
    }
    if (request->status != SERVICE_PENDING) {
        cout << "  [Error] Only pending requests can be cancelled here.\n";
        return;
    }
    Parcel* parcel = findParcel(request->parcelID);
    bool cancelParcel = (parcel != nullptr && isValidTransition(parcel->status, STATUS_CANCELLED));
    if (cancelParcel) {
        if (!updateParcelStatus(parcel->parcelID, STATUS_CANCELLED)) return;
    }
    else {      // e.g. parcel reported Missing in Task 1: cancel only the request so the queue is not blocked
        cout << "  [Info] Parcel " << request->parcelID << " is "
             << (parcel == nullptr ? string("not found") : statusToString(parcel->status))
             << ", so only the request is cancelled (parcel status unchanged).\n";
    }
    waitingRequests.remove(request->requestID);
    request->status = SERVICE_CANCELLED;
    request->finishedDateTime = getCurrentDateTime();
    logActivity(request->parcelID, "Service Request Cancellation", "Pending", "Cancelled", g_staffID);
    cout << "  [Success] Request " << id << " cancelled.\n";
    releaseResourceFor(request->parcelID, false);                // Task 3: free the resource, if any
}

// A parcel can be finished directly in Task 1 (Collected / Returned / Cancelled) or
// reported Missing. Its open request must not stay Pending / Processing forever,
// and a stale request at the head of the queue would block every request behind it.
bool syncRequestsWithParcels() {
    ensureRequestsLoaded();
    bool changed = false;
    for (ServiceRequest* r = requestStore.first(); r != nullptr; r = r->next) {
        if (r->status != SERVICE_PENDING && r->status != SERVICE_PROCESSING) continue;
        Parcel* parcel = findParcel(r->parcelID);
        if (parcel == nullptr) continue;
        ServiceStatus result = SERVICE_COMPLETED;
        if (parcel->status == STATUS_COLLECTED) result = SERVICE_COMPLETED;
        else if (parcel->status == STATUS_RETURNED) result = SERVICE_RETURNED;
        else if (parcel->status == STATUS_CANCELLED || parcel->status == STATUS_MISSING) result = SERVICE_CANCELLED;
        else continue;                                           // parcel still in progress

        string old = serviceStatusText(r->status);
        if (r == currentRequest) currentRequest = nullptr;
        else waitingRequests.remove(r->requestID);
        r->status = result;
        r->finishedDateTime = getCurrentDateTime();
        logActivity(r->parcelID, "Service Request " + serviceStatusText(result), old,
            serviceStatusText(result), g_staffID);
        if (!changed) cout << "\n  [Auto-sync] Requests updated from parcel changes made elsewhere:\n";
        changed = true;
        cout << "    - " << r->requestID << " is now " << serviceStatusText(result)
             << " because parcel " << r->parcelID << " is " << statusToString(parcel->status) << ".\n";
        releaseResourceFor(r->parcelID, result != SERVICE_CANCELLED);   // Task 3: free its resource
    }
    if (changed) saveServiceRequests();
    return changed;
}

// Task 1 may have corrected a parcel's recipient ID / name after the request was
// created. Copy the current values so Task 2 never shows outdated details.
static void refreshRecipientDetails() {
    for (ServiceRequest* r = requestStore.first(); r != nullptr; r = r->next) {
        Parcel* parcel = findParcel(r->parcelID);
        if (parcel == nullptr) continue;
        r->recipientID = parcel->recipientID;
        r->recipientName = parcel->recipientName;
    }
}

void runTask2Menu() {
    ensureRequestsLoaded();
    if (!requestLoadNotice.empty() && !requestNoticeShown) {   // tell staff once what was restored
        requestNoticeShown = true;
        cout << requestLoadNotice;
        pressEnterToContinue();
    }
    int choice = 0;
    do {
        if (syncRequestsWithParcels()) pressEnterToContinue();   // parcels finished in Task 1
        clearScreen();
        printTitle("PARCEL SERVICE & COLLECTION MANAGEMENT");
        cout << "  Staff: " << g_staffID << "\n";
        printLine('-');
        cout << "  [1] Create service request\n"
             << "  [2] Display active requests (priority order)\n"
             << "  [3] Process next highest-priority request\n"
             << "  [4] Complete / cancel / return current request\n"
             << "  [5] Cancel a pending request\n"
             << "  [6] Search by Request ID\n"
             << "  [7] Display all requests (history)\n"
             << "  [0] Return to main menu\n";
        printLine('-');
        choice = readInt("  Enter your choice: ", 0, 7);
        clearScreen();
        refreshRecipientDetails();          // keep recipient details in step with Task 1
        switch (choice) {
        case 1: manuallyCreateRequest(); break;
        case 2: viewPendingRequests(); break;
        case 3: processNextRequest(); break;
        case 4: finishCurrentRequest(); break;
        case 5: cancelPendingRequest(); break;
        case 6: searchRequest(); break;
        case 7: viewAllRequests(); break;
        default: break;
        }
        if (choice != 0) {
            saveServiceRequests();          // save after every action (parcel changes save themselves)
            pressEnterToContinue();
        }
    } while (choice != 0);
}
