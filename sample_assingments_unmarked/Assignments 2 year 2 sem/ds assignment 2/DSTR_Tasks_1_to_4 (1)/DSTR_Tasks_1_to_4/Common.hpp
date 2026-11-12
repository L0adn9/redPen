/*
 * ============================================================================
 *  Smart Campus Parcel Management System
 *  File    : Common.hpp
 *  Purpose : Shared definitions used by ALL modules (Task 1 - Task 5):
 *            enums, the Parcel record, and small helper functions.
 *
 *  TEAM RULE: Do NOT rename or delete anything in this file.
 *             You may only ADD new items (and note it in the change log).
 * ============================================================================
 */
#ifndef COMMON_H
#define COMMON_H

#include <iostream>
#include <string>
#include <ctime>
#include <cctype>
#include <cstdlib>
using namespace std;

// ---------------------------------------------------------------------------
// Parcel types (values start at 1 so they match the menu choices 1-5)
// ---------------------------------------------------------------------------
enum ParcelType {
    TYPE_STANDARD = 1,
    TYPE_LARGE,
    TYPE_FRAGILE,
    TYPE_DOCUMENT,
    TYPE_SPECIAL_HANDLING
};
const int TYPE_MIN = 1;
const int TYPE_MAX = 5;

// ---------------------------------------------------------------------------
// Parcel statuses. STATUS_COUNT is a sentinel (= number of statuses) that
// lets us loop over every status and size the statistics array.
// ---------------------------------------------------------------------------
enum ParcelStatus {
    STATUS_RECEIVED = 0,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_READY_FOR_COLLECTION,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_COLLECTED,
    STATUS_RETURNED,
    STATUS_MISSING,
    STATUS_CANCELLED,
    STATUS_ON_HOLD,
    STATUS_COUNT
};

// ---------------------------------------------------------------------------
// Next required action (the "route") decided when a parcel is sorted.
// ---------------------------------------------------------------------------
enum RouteAction {
    ROUTE_NONE = 0,
    ROUTE_COLLECTION,        // recipient collects at a counter
    ROUTE_DELIVERY,          // campus delivery
    ROUTE_SPECIAL_HANDLING,  // fragile / special items
    ROUTE_RETURN,            // return to sender
    ROUTE_HOLD               // on hold for investigation
};

// ---------------------------------------------------------------------------
// The shared Parcel record (fields required by the assignment brief).
// ---------------------------------------------------------------------------
struct Parcel {
    string       parcelID;
    string       recipientID;
    string       recipientName;
    string       deliveryCompany;
    ParcelType   type;
    string       arrivalDateTime;
    ParcelStatus status;
    RouteAction  route;          // where the parcel was routed (Task 1)

    Parcel() : type(TYPE_STANDARD), status(STATUS_RECEIVED), route(ROUTE_NONE) {}
};

// Staff ID of the person currently logged in (defined in main.cpp).
extern string g_staffID;

// ---------------------------------------------------------------------------
// Enum -> text helpers
// ---------------------------------------------------------------------------
inline string typeToString(ParcelType t) {
    switch (t) {
    case TYPE_STANDARD:         return "Standard Parcel";
    case TYPE_LARGE:            return "Large Parcel";
    case TYPE_FRAGILE:          return "Fragile Parcel";
    case TYPE_DOCUMENT:         return "Document";
    case TYPE_SPECIAL_HANDLING: return "Special Handling";
    default:                    return "Unknown";
    }
}

inline string statusToString(ParcelStatus s) {
    switch (s) {
    case STATUS_RECEIVED:             return "Received";
    case STATUS_PENDING:              return "Pending";
    case STATUS_PROCESSING:           return "Processing";
    case STATUS_READY_FOR_COLLECTION: return "Ready for Collection";
    case STATUS_OUT_FOR_DELIVERY:     return "Out for Delivery";
    case STATUS_COLLECTED:            return "Collected";
    case STATUS_RETURNED:             return "Returned";
    case STATUS_MISSING:              return "Missing";
    case STATUS_CANCELLED:            return "Cancelled";
    case STATUS_ON_HOLD:              return "On Hold";
    default:                          return "Unknown";
    }
}

inline string routeToString(RouteAction r) {
    switch (r) {
    case ROUTE_COLLECTION:       return "Recipient Collection";
    case ROUTE_DELIVERY:         return "Campus Delivery";
    case ROUTE_SPECIAL_HANDLING: return "Special Handling";
    case ROUTE_RETURN:           return "Return to Sender";
    case ROUTE_HOLD:             return "On Hold (Investigation)";
    default:                     return "Not routed yet";
    }
}

// ---------------------------------------------------------------------------
// General helpers
// ---------------------------------------------------------------------------

// Current system date/time as "YYYY-MM-DD HH:MM:SS".
inline string getCurrentDateTime() {
    time_t now = time(nullptr);
    tm t;
#ifdef _WIN32
    localtime_s(&t, &now);      // thread-safe version on Windows
#else
    localtime_r(&now, &t);      // thread-safe version on Linux/Mac
#endif
    char buf[20];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &t);
    return string(buf);
}

// Remove leading/trailing spaces.
inline string trim(const string& s) {
    size_t start = 0;
    while (start < s.size() && isspace((unsigned char)s[start])) start++;
    size_t end = s.size();
    while (end > start && isspace((unsigned char)s[end - 1])) end--;
    return s.substr(start, end - start);
}

// Convert to upper case (used for case-insensitive comparison).
inline string toUpperStr(string s) {
    for (size_t i = 0; i < s.size(); i++) s[i] = (char)toupper((unsigned char)s[i]);
    return s;
}

// True if the string is non-empty and every character is a letter/digit.
inline bool isAlphanumeric(const string& s) {
    if (s.empty()) return false;
    for (size_t i = 0; i < s.size(); i++)
        if (!isalnum((unsigned char)s[i])) return false;
    return true;
}

// Read a whole line. Exits cleanly if the input stream is closed (avoids
// infinite loops on end-of-file).
inline string readLine(const string& prompt) {
    cout << prompt;
    string line;
    if (!getline(cin, line)) {
        cout << "\n[Input closed] Exiting program.\n";
        exit(0);
    }
    return line;
}

// Read an integer between minV and maxV. Keeps asking until valid, so letters
// or blank input can never crash the program.
inline int readInt(const string& prompt, int minV, int maxV) {
    while (true) {
        string in = trim(readLine(prompt));
        bool ok = !in.empty() && in.size() <= 6;
        for (size_t i = 0; i < in.size(); i++)
            if (!isdigit((unsigned char)in[i])) ok = false;
        if (ok) {
            int v = atoi(in.c_str());
            if (v >= minV && v <= maxV) return v;
        }
        cout << "  [Error] Please enter a number between " << minV << " and " << maxV << ".\n";
    }
}

// ---------------------------------------------------------------------------
// Screen / layout helpers (shared so every menu looks the same)
// ---------------------------------------------------------------------------
const int SCREEN_WIDTH = 60;

// Clear the console screen.
inline void clearScreen() {
#ifdef _WIN32
    system("cls");
#else
    system("clear");
#endif
}

// Print a horizontal line, e.g. ======== or --------
inline void printLine(char ch = '=') {
    cout << string(SCREEN_WIDTH, ch) << "\n";
}

// Print a title banner with the text centred between two lines.
inline void printTitle(const string& title) {
    int pad = (SCREEN_WIDTH - (int)title.size()) / 2;
    if (pad < 0) pad = 0;
    printLine('=');
    cout << string(pad, ' ') << title << "\n";
    printLine('=');
}

// Wait for the user so the result stays on screen before the menu redraws.
inline void pressEnterToContinue() {
    readLine("\n  Press Enter to continue...");
}

#endif // COMMON_H