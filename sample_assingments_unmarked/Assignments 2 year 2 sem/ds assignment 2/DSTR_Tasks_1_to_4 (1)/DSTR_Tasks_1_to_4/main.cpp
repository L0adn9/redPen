
#include "Common.hpp"
#include "Task1.hpp"
#include "Task2.hpp"
#include "Task3.hpp"
#include "Task4.hpp"

string g_staffID = "";     // staff who is logged in (used in the activity log)

// Login screen: ask for a staff ID (3-10 letters/digits).
static void login() {
    clearScreen();
    printTitle("SMART CAMPUS PARCEL MANAGEMENT SYSTEM");
    cout << "\n  Staff Login\n";
    printLine('-');

    while (true) {
        g_staffID = toUpperStr(trim(readLine("  Staff ID: ")));
        if (isAlphanumeric(g_staffID) && g_staffID.size() >= 3 && g_staffID.size() <= 10)
            break;
        cout << "  [Error] Staff ID must be 3-10 letters or digits.\n";
    }
}

// Draw the main menu.
static void showMainMenu() {
    clearScreen();
    printTitle("SMART CAMPUS PARCEL MANAGEMENT SYSTEM");
    cout << "  Logged in as: " << g_staffID << "\n";
    printLine('-');
    cout << "  [1] Parcel Intake & Processing\n"
        << "  [2] Service Requests\n"
        << "  [3] Counters & Delivery Resources\n"
        << "  [4] Activity History & Undo\n"
        << "  [0] Exit\n";
    printLine('-');
}

int main() {
    login();

    int choice;
    do {
        showMainMenu();
        choice = readInt("  Enter your choice: ", 0, 4);

        switch (choice) {
        case 1: runTask1Menu(); break;
        case 2: runTask2Menu(); break;
        case 3: runTask3Menu(); break;
        case 4: runTask4Menu(); break;
        case 0:
            clearScreen();
            cout << "\n  Thank you for using the system. Goodbye!\n\n";
            break;
        }
    } while (choice != 0);

    return 0;
}